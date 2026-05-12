#!/usr/bin/env python3
"""
Extract negation and speculation cues from the NUBes corpus (BRAT standoff format)
and emit cwyde-compatible lexicon YAML files.

Cues are extracted from TRAINING FOLDS ONLY so that the dev and test partitions
remain unseen during KB development — preventing data leakage into evaluation.

NUBes is organised as ten sample directories (sample_0 … sample_9). Default split:
  train  folds 0–6   (70 %)
  dev    fold  7     (10 %)
  test   folds 8–9   (20 %)

Usage
-----
    python scripts/extract_nubes_cues.py /path/to/NUBes-corpus \\
        --train 0 1 2 3 4 5 6 \\
        --dev   7 \\
        --test  8 9 \\
        --out   packages/cwyde-knowledge/src/cwyde_knowledge/data/lang/es/lexicon \\
        --min-freq 3

Output files
------------
  negation_cues.yaml    NEG_CUE entries → DEFINITE_NEGATED_EXISTENCE
  speculation_cues.yaml SPEC_CUE entries → PROBABLE_EXISTENCE
                        (entries whose direction is ambiguous carry notes: "review direction")

Direction inference
-------------------
For each (cue surface form, doc) pair where a scope annotation exists, we compute the
relative position of the cue within its scope span:

    rel = (cue_start - scope_start) / max(scope_end - scope_start, 1)

Averaging rel across all training occurrences gives a per-cue score:
  mean_rel < 0.2  → forward
  mean_rel > 0.8  → backward
  otherwise       → bidirectional

NUBes BRAT annotation types used
---------------------------------
  T*  NEG_CUE   start end   surface_form
  T*  SPEC_CUE  start end   surface_form
  T*  NEG_SCOPE start end   …
  T*  SPEC_SCOPE start end  …
  R*  Has_scope / Cue_scope  Arg1:T_cue Arg2:T_scope
  (relation name varies across NUBes versions; we match any relation where
   one argument is a *_CUE and the other is a *_SCOPE)
"""

from __future__ import annotations

import argparse
import collections
import re
import statistics
import sys
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# BRAT parser
# ---------------------------------------------------------------------------

def parse_ann(ann_path: Path) -> tuple[dict, list]:
    """
    Parse a BRAT .ann file.

    Returns
    -------
    spans : dict[str, dict]  — {T_id: {type, start, end, text}}
    rels  : list[tuple]      — [(rel_type, arg1_id, arg2_id)]
    """
    spans: dict[str, dict] = {}
    rels: list[tuple[str, str, str]] = []

    for line in ann_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("T"):
            parts = line.split("\t", 2)
            if len(parts) < 3:
                continue
            t_id = parts[0]
            middle = parts[1]
            text = parts[2]
            m = re.match(r"(\S+)\s+(\d+)\s+(\d+)", middle)
            if not m:
                continue
            spans[t_id] = {
                "type": m.group(1),
                "start": int(m.group(2)),
                "end": int(m.group(3)),
                "text": text,
            }

        elif line.startswith("R"):
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            fields = parts[1].split()
            if len(fields) < 3:
                continue
            rel_type = fields[0]
            arg1 = fields[1].split(":", 1)[-1]
            arg2 = fields[2].split(":", 1)[-1]
            rels.append((rel_type, arg1, arg2))

    return spans, rels


# ---------------------------------------------------------------------------
# Per-document cue extraction
# ---------------------------------------------------------------------------

def extract_cues_from_ann(
    spans: dict,
    rels: list[tuple[str, str, str]],
) -> list[dict]:
    """
    Return a list of cue records extracted from one document's annotations.

    Each record: {surface, cue_type, rel_pos}
      surface   — lowercase stripped cue text
      cue_type  — "NEG_CUE" or "SPEC_CUE"
      rel_pos   — relative position of cue within its scope (0.0–1.0), or None
    """
    # Build cue_id → scope_id mapping from relations
    cue_to_scope: dict[str, str] = {}
    for _rel_type, arg1, arg2 in rels:
        a1 = spans.get(arg1, {})
        a2 = spans.get(arg2, {})
        a1t = a1.get("type", "")
        a2t = a2.get("type", "")
        if a1t.endswith("_CUE") and a2t.endswith("_SCOPE"):
            cue_to_scope[arg1] = arg2
        elif a2t.endswith("_CUE") and a1t.endswith("_SCOPE"):
            cue_to_scope[arg2] = arg1

    records = []
    for t_id, span in spans.items():
        if span["type"] not in ("NEG_CUE", "SPEC_CUE"):
            continue

        surface = span["text"].strip().lower()
        if not surface:
            continue

        rel_pos = None
        scope_id = cue_to_scope.get(t_id)
        if scope_id and scope_id in spans:
            scope = spans[scope_id]
            scope_len = max(scope["end"] - scope["start"], 1)
            cue_mid = (span["start"] + span["end"]) / 2
            rel_pos = (cue_mid - scope["start"]) / scope_len
            rel_pos = max(0.0, min(1.0, rel_pos))

        records.append({
            "surface": surface,
            "cue_type": span["type"],
            "rel_pos": rel_pos,
        })

    return records


# ---------------------------------------------------------------------------
# Direction inference
# ---------------------------------------------------------------------------

def infer_direction(rel_positions: list[float | None]) -> str:
    """
    Given all observed relative-position values for one cue surface form,
    return 'forward', 'backward', or 'bidirectional'.

    Observations with no scope annotation (None) are ignored.
    If no scope observations at all, default to 'forward'.
    """
    observed = [p for p in rel_positions if p is not None]
    if not observed:
        return "forward"
    mean_rel = statistics.mean(observed)
    if mean_rel < 0.2:
        return "forward"
    if mean_rel > 0.8:
        return "backward"
    return "bidirectional"


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def discover_samples(corpus_dir: Path) -> dict[int, Path]:
    """Return {fold_index: Path} for sample_0 … sample_9."""
    samples = {}
    for p in sorted(corpus_dir.iterdir()):
        m = re.match(r"sample_(\d+)$", p.name)
        if m and p.is_dir():
            samples[int(m.group(1))] = p
    return samples


def extract_from_folds(
    samples: dict[int, Path],
    folds: list[int],
) -> list[dict]:
    """Collect all cue records from the given folds."""
    records = []
    for fold in folds:
        sample_dir = samples.get(fold)
        if sample_dir is None:
            print(f"  WARNING: sample_{fold} not found in corpus directory", file=sys.stderr)
            continue
        ann_files = sorted(sample_dir.glob("*.ann"))
        for ann_path in ann_files:
            spans, rels = parse_ann(ann_path)
            records.extend(extract_cues_from_ann(spans, rels))
    return records


def aggregate(
    records: list[dict],
    min_freq: int,
) -> dict[str, dict]:
    """
    Aggregate records by (surface, cue_type).

    Returns {surface: {cue_type, count, direction, needs_review}}
    """
    counts: dict[tuple[str, str], int] = collections.Counter()
    positions: dict[tuple[str, str], list[float | None]] = collections.defaultdict(list)

    for r in records:
        key = (r["surface"], r["cue_type"])
        counts[key] += 1
        positions[key].append(r["rel_pos"])

    result = {}
    for (surface, cue_type), count in counts.items():
        if count < min_freq:
            continue
        direction = infer_direction(positions[(surface, cue_type)])
        # Flag for review: speculation cues whose direction is bidirectional —
        # they may belong to PROBABLE_NEGATED or AMBIVALENT rather than PROBABLE_EXISTENCE.
        needs_review = cue_type == "SPEC_CUE" and direction == "bidirectional"
        result[surface] = {
            "cue_type": cue_type,
            "count": count,
            "direction": direction,
            "needs_review": needs_review,
        }
    return result


# ---------------------------------------------------------------------------
# YAML output
# ---------------------------------------------------------------------------

NEG_CATEGORY = "DEFINITE_NEGATED_EXISTENCE"
SPEC_CATEGORY = "PROBABLE_EXISTENCE"


def build_entries(
    aggregated: dict[str, dict],
    cue_type_filter: str,
) -> list[dict]:
    entries = []
    for surface, info in sorted(aggregated.items(), key=lambda x: -x[1]["count"]):
        if info["cue_type"] != cue_type_filter:
            continue
        category = NEG_CATEGORY if cue_type_filter == "NEG_CUE" else SPEC_CATEGORY
        notes_parts = [f"NUBes train count: {info['count']}"]
        if info["needs_review"]:
            notes_parts.append(
                "review: bidirectional speculation cue — may be PROBABLE_NEGATED_EXISTENCE or AMBIVALENT_EXISTENCE"
            )
        entry: dict = {
            "lex": surface,
            "direction": info["direction"],
            "category": category,
            "source": "nubes",
            "notes": "; ".join(notes_parts),
        }
        entries.append(entry)
    return entries


def write_lexicon_yaml(path: Path, entries: list[dict], description: str) -> None:
    doc = {
        "schema_version": 1,
        "_comment": description,
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(doc, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"  Wrote {len(entries)} entries → {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract cwyde lexicon YAML from NUBes training folds (BRAT format)."
    )
    parser.add_argument("corpus_dir", type=Path, help="Root directory of NUBes corpus (contains sample_0 … sample_9)")
    parser.add_argument("--train", nargs="+", type=int, default=list(range(7)), metavar="FOLD",
                        help="Fold indices used for lexicon extraction (default: 0–6)")
    parser.add_argument("--dev", nargs="+", type=int, default=[7], metavar="FOLD",
                        help="Dev fold indices, held out during extraction (default: 7)")
    parser.add_argument("--test", nargs="+", type=int, default=[8, 9], metavar="FOLD",
                        help="Test fold indices, held out during extraction (default: 8–9)")
    parser.add_argument("--out", type=Path,
                        default=Path("packages/cwyde-knowledge/src/cwyde_knowledge/data/lang/es/lexicon"),
                        help="Output directory for generated YAML files")
    parser.add_argument("--min-freq", type=int, default=3, metavar="N",
                        help="Minimum training-set occurrences to include a cue (default: 3)")
    args = parser.parse_args()

    corpus_dir = args.corpus_dir.resolve()
    if not corpus_dir.is_dir():
        sys.exit(f"ERROR: corpus directory not found: {corpus_dir}")

    # Sanity check: no leakage — validate before touching the filesystem
    train_set = set(args.train)
    dev_set = set(args.dev)
    test_set = set(args.test)
    if train_set & dev_set:
        sys.exit(f"ERROR: train and dev folds overlap: {train_set & dev_set}")
    if train_set & test_set:
        sys.exit(f"ERROR: train and test folds overlap: {train_set & test_set}")
    if dev_set & test_set:
        sys.exit(f"ERROR: dev and test folds overlap: {dev_set & test_set}")

    samples = discover_samples(corpus_dir)
    if not samples:
        sys.exit(f"ERROR: no sample_* directories found in {corpus_dir}")

    all_folds = sorted(samples.keys())
    print(f"NUBes corpus: {corpus_dir}")
    print(f"Discovered folds: {all_folds}")
    print(f"Train folds : {args.train}")
    print(f"Dev folds   : {args.dev}  (held out)")
    print(f"Test folds  : {args.test}  (held out)")
    print(f"Min frequency: {args.min_freq}")
    print()

    print("Extracting cues from training folds …")
    records = extract_from_folds(samples, args.train)
    print(f"  {len(records)} raw cue occurrences in training folds")

    aggregated = aggregate(records, min_freq=args.min_freq)

    neg_entries = build_entries(aggregated, "NEG_CUE")
    spec_entries = build_entries(aggregated, "SPEC_CUE")
    needs_review = sum(1 for e in spec_entries if "review" in e.get("notes", ""))

    print(f"  {len(neg_entries)} negation cues  (≥{args.min_freq} occurrences)")
    print(f"  {len(spec_entries)} speculation cues (≥{args.min_freq} occurrences); {needs_review} flagged for direction review")
    print()

    out_dir = args.out.resolve()
    print(f"Writing to {out_dir} …")
    write_lexicon_yaml(
        out_dir / "nubes_negation_cues.yaml",
        neg_entries,
        "Negation cues extracted from NUBes training folds. "
        "Category: DEFINITE_NEGATED_EXISTENCE. Source: NUBes (Apache 2.0). "
        "AUTO-GENERATED by scripts/extract_nubes_cues.py — review before committing.",
    )
    write_lexicon_yaml(
        out_dir / "nubes_speculation_cues.yaml",
        spec_entries,
        "Speculation/uncertainty cues extracted from NUBes training folds. "
        "Category defaults to PROBABLE_EXISTENCE — entries with notes containing "
        "'review' should be manually reclassified as PROBABLE_NEGATED_EXISTENCE or "
        "AMBIVALENT_EXISTENCE where appropriate. Source: NUBes (Apache 2.0). "
        "AUTO-GENERATED by scripts/extract_nubes_cues.py — review before committing.",
    )

    print()
    print("Done. Next steps:")
    print("  1. Review nubes_speculation_cues.yaml entries flagged 'review direction'")
    print("     and reclassify as PROBABLE_NEGATED_EXISTENCE or AMBIVALENT_EXISTENCE where appropriate.")
    print("  2. Run cwyde KB validation:  python scripts/validate_kb.py")
    print("  3. Add 'es' language adapter to cwyde/lang/registry if not present.")
    print(f"  4. Evaluate on dev fold {args.dev} before touching test folds {args.test}.")
    print()
    print("Split summary (for paper methods section):")
    print(f"  Train : folds {sorted(train_set)} — used for lexicon extraction")
    print(f"  Dev   : folds {sorted(dev_set)}   — used for parameter tuning")
    print(f"  Test  : folds {sorted(test_set)}  — held out for final evaluation")


if __name__ == "__main__":
    main()
