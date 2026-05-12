#!/usr/bin/env python3
"""
Evaluate cwyde assertion classification against the RadGraph-XL corpus
(Delbrouck et al., ACL 2024 Findings).

Data format: JSONL — one record per radiology report.
  sentences  : list[list[str]]   tokenised sentences
  ner        : list[list[triple]] [start_tok, end_tok, "Type::assertion_status"]
  relations  : list[list[5-tuple]] (not used here)

Assertion labels in RadGraph-XL:
  "Observation::definitely present"  →  cwyde DEFINITE_EXISTENCE
  "Observation::definitely absent"   →  cwyde DEFINITE_NEGATED_EXISTENCE
  "Observation::uncertain"           →  cwyde PROBABLE_EXISTENCE / AMBIVALENT_EXISTENCE
  "Anatomy::*"                       →  same mapping (anatomy treated as findings)

Evaluation protocol
-------------------
  Given-entity mode (default):
    Gold entity spans are injected as medspaCy target rules before the pipeline runs.
    This evaluates assertion classification in isolation, matching the i2b2 2010
    evaluation protocol (assertion given gold-standard named entities).

  Full-pipeline mode (--full-pipeline):
    cwyde's own lexicon-based target matcher finds entities. Gold spans are matched
    against cwyde's detected spans by character-level overlap. Tests end-to-end
    performance including entity detection.

Usage
-----
  # Given-entity mode (recommended for assertion classification evaluation)
  python scripts/evaluate_radgraph_xl.py /path/to/radgraph_xl/ --split test

  # Full pipeline mode
  python scripts/evaluate_radgraph_xl.py /path/to/radgraph_xl/ --split test --full-pipeline

  # Use dev split during development; never tune on test
  python scripts/evaluate_radgraph_xl.py /path/to/radgraph_xl/ --split dev

Output
------
  Per-class precision, recall, F1 and macro/weighted averages.
  Optional: per-report error analysis with --errors.

Split handling
--------------
  RadGraph-XL ships with a fixed 2320/290/290 train/dev/test split.
  The PhysioNet MIMIC-only release (300 reports) uses the same schema;
  split membership is determined by the source files (train.jsonl, dev.jsonl,
  test.jsonl) if present, or by --split-file override.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Iterator

import medspacy
from medspacy.target_matcher import TargetRule

import cwyde
from cwyde.categories import AssertionCategory


# ---------------------------------------------------------------------------
# RadGraph-XL label → cwyde category
# ---------------------------------------------------------------------------

LABEL_TO_CWYDE: dict[str, AssertionCategory] = {
    "definitely present": AssertionCategory.DEFINITE_EXISTENCE,
    "definitely absent":  AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
    "uncertain":          AssertionCategory.PROBABLE_EXISTENCE,
}

# For scoring: map cwyde categories to the 3-class RadGraph-XL scheme
CWYDE_TO_RADGRAPH: dict[AssertionCategory, str] = {
    AssertionCategory.DEFINITE_EXISTENCE:          "definitely present",
    AssertionCategory.PROBABLE_EXISTENCE:          "uncertain",
    AssertionCategory.AMBIVALENT_EXISTENCE:        "uncertain",
    AssertionCategory.PROBABLE_NEGATED_EXISTENCE:  "uncertain",
    AssertionCategory.DEFINITE_NEGATED_EXISTENCE:  "definitely absent",
    AssertionCategory.HISTORICAL:                  "definitely present",  # past finding still present
    AssertionCategory.HYPOTHETICAL:                "uncertain",
    AssertionCategory.FAMILY:                      "uncertain",
    AssertionCategory.INDICATION:                  "uncertain",
    AssertionCategory.UNRESOLVED:                  "uncertain",
}

RADGRAPH_CLASSES = ["definitely present", "definitely absent", "uncertain"]


# ---------------------------------------------------------------------------
# RadGraph-XL JSONL reader
# ---------------------------------------------------------------------------

def parse_assertion_status(label: str) -> str:
    """Extract assertion status from 'Type::assertion_status' label string."""
    if "::" in label:
        return label.split("::", 1)[1].strip()
    return label.strip()


def reconstruct_text(sentences: list[list[str]]) -> tuple[str, list[int]]:
    """
    Join tokenised sentences into a single string.
    Returns (text, sentence_start_char_offsets).
    Tokens are joined with a single space; sentences with a newline.
    """
    sent_texts = [" ".join(toks) for toks in sentences]
    text = "\n".join(sent_texts)
    offsets = []
    pos = 0
    for st in sent_texts:
        offsets.append(pos)
        pos += len(st) + 1  # +1 for the newline separator
    return text, offsets


def token_span_to_char_span(
    sentences: list[list[str]],
    sent_offsets: list[int],
    sent_idx: int,
    tok_start: int,
    tok_end: int,
) -> tuple[int, int]:
    """Convert token-level span to character-level span in the reconstructed text."""
    toks = sentences[sent_idx]
    sent_base = sent_offsets[sent_idx]
    # Compute char offset of tok_start within this sentence
    char_start = sum(len(toks[i]) + 1 for i in range(tok_start))  # +1 for spaces
    char_end = char_start + sum(len(toks[i]) + 1 for i in range(tok_start, tok_end + 1)) - 1
    return sent_base + char_start, sent_base + char_end


def iter_records(jsonl_path: Path) -> Iterator[dict]:
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_gold_entities(record: dict) -> tuple[str, list[dict]]:
    """
    Return gold entities from a record as:
      {text, char_start, char_end, assertion_status}
    """
    sentences = record["sentences"]
    text, sent_offsets = reconstruct_text(sentences)
    entities = []
    for sent_idx, sent_ner in enumerate(record.get("ner", [])):
        for span in sent_ner:
            tok_start, tok_end, label = span[0], span[1], span[2]
            assertion = parse_assertion_status(label)
            if assertion not in LABEL_TO_CWYDE:
                continue
            char_start, char_end = token_span_to_char_span(
                sentences, sent_offsets, sent_idx, tok_start, tok_end
            )
            span_text = text[char_start:char_end]
            entities.append({
                "text":             span_text,
                "char_start":       char_start,
                "char_end":         char_end,
                "assertion_status": assertion,
            })
    return text, entities


# ---------------------------------------------------------------------------
# Pipeline construction
# ---------------------------------------------------------------------------

def build_pipeline(lang: str = "en") -> object:
    nlp = medspacy.load()
    nlp.add_pipe("medspacy_sectionizer")
    cwyde.add_to(nlp, lang=lang)
    return nlp


def run_given_entity(nlp, text: str, gold_entities: list[dict]) -> list[dict]:
    """
    Inject gold entity surface forms as target rules, run the pipeline,
    match by character span, return per-entity results.
    """
    tm = nlp.get_pipe("medspacy_target_matcher")
    # Add gold entities as one-shot target rules for this document
    rules = [
        TargetRule(e["text"], "FINDING", pattern=[{"LOWER": tok.lower()} for tok in e["text"].split()])
        for e in gold_entities
    ]
    tm.add(rules)
    try:
        doc = nlp(text)
    finally:
        # Remove the temporary rules so they don't contaminate the next document
        for rule in rules:
            try:
                tm.remove(rule.literal)
            except Exception:
                pass

    # Build char-span → cwyde category lookup from pipeline output
    cwyde_map: dict[tuple[int, int], AssertionCategory] = {}
    for ent in doc.ents:
        cwyde_map[(ent.start_char, ent.end_char)] = ent._.cwyde_assertion_category

    results = []
    for gold in gold_entities:
        key = (gold["char_start"], gold["char_end"])
        cwyde_cat = cwyde_map.get(key)
        if cwyde_cat is None:
            # Fuzzy match: find overlapping entity
            for (cs, ce), cat in cwyde_map.items():
                if cs < gold["char_end"] and ce > gold["char_start"]:
                    cwyde_cat = cat
                    break
        predicted = CWYDE_TO_RADGRAPH.get(cwyde_cat, "uncertain") if cwyde_cat else "uncertain"
        results.append({
            "gold":      gold["assertion_status"],
            "predicted": predicted,
            "text":      gold["text"],
        })
    return results


def run_full_pipeline(nlp, text: str, gold_entities: list[dict]) -> list[dict]:
    """
    Run cwyde's own entity detection; match against gold spans by overlap.
    """
    doc = nlp(text)
    cwyde_spans = [(e.start_char, e.end_char, e._.cwyde_assertion_category) for e in doc.ents]

    results = []
    for gold in gold_entities:
        gs, ge = gold["char_start"], gold["char_end"]
        cwyde_cat = None
        for cs, ce, cat in cwyde_spans:
            if cs < ge and ce > gs:
                cwyde_cat = cat
                break
        predicted = CWYDE_TO_RADGRAPH.get(cwyde_cat, "uncertain") if cwyde_cat else "uncertain"
        results.append({
            "gold":      gold["assertion_status"],
            "predicted": predicted,
            "text":      gold["text"],
        })
    return results


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_f1(
    all_results: list[dict],
) -> dict:
    tp = collections.Counter()
    fp = collections.Counter()
    fn = collections.Counter()

    for r in all_results:
        g, p = r["gold"], r["predicted"]
        if g == p:
            tp[g] += 1
        else:
            fp[p] += 1
            fn[g] += 1

    metrics = {}
    total_tp = total_fp = total_fn = 0
    for cls in RADGRAPH_CLASSES:
        p = tp[cls] / max(tp[cls] + fp[cls], 1)
        r = tp[cls] / max(tp[cls] + fn[cls], 1)
        f = 2 * p * r / max(p + r, 1e-9)
        n = tp[cls] + fn[cls]
        metrics[cls] = {"precision": p, "recall": r, "f1": f, "support": n}
        total_tp += tp[cls]
        total_fp += fp[cls]
        total_fn += fn[cls]

    # Macro F1
    macro_f1 = sum(metrics[c]["f1"] for c in RADGRAPH_CLASSES) / len(RADGRAPH_CLASSES)

    # Weighted F1
    total_support = sum(metrics[c]["support"] for c in RADGRAPH_CLASSES)
    weighted_f1 = sum(metrics[c]["f1"] * metrics[c]["support"] for c in RADGRAPH_CLASSES) / max(total_support, 1)

    # Micro F1
    micro_p = total_tp / max(total_tp + total_fp, 1)
    micro_r = total_tp / max(total_tp + total_fn, 1)
    micro_f1 = 2 * micro_p * micro_r / max(micro_p + micro_r, 1e-9)

    metrics["macro"] = {"f1": macro_f1}
    metrics["weighted"] = {"f1": weighted_f1}
    metrics["micro"] = {"precision": micro_p, "recall": micro_r, "f1": micro_f1}
    return metrics


def print_metrics(metrics: dict) -> None:
    print(f"\n{'Class':<30} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    print("-" * 65)
    for cls in RADGRAPH_CLASSES:
        m = metrics[cls]
        print(f"{cls:<30} {m['precision']:>10.3f} {m['recall']:>10.3f} {m['f1']:>10.3f} {m['support']:>10}")
    print("-" * 65)
    print(f"{'Macro F1':<30} {'':>10} {'':>10} {metrics['macro']['f1']:>10.3f}")
    print(f"{'Weighted F1':<30} {'':>10} {'':>10} {metrics['weighted']['f1']:>10.3f}")
    m = metrics["micro"]
    print(f"{'Micro F1':<30} {m['precision']:>10.3f} {m['recall']:>10.3f} {m['f1']:>10.3f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def find_split_file(data_dir: Path, split: str) -> Path:
    candidates = [
        data_dir / f"{split}.jsonl",
        data_dir / f"radgraph_xl_{split}.jsonl",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fall back: single combined file
    combined = list(data_dir.glob("*.jsonl"))
    if len(combined) == 1:
        print(f"WARNING: no {split}.jsonl found; using {combined[0].name} (all records)")
        return combined[0]
    sys.exit(
        f"ERROR: cannot find {split}.jsonl in {data_dir}. "
        f"Files present: {[f.name for f in data_dir.glob('*.jsonl')]}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate cwyde assertion classification on RadGraph-XL."
    )
    parser.add_argument("data_dir", type=Path,
                        help="Directory containing RadGraph-XL JSONL files")
    parser.add_argument("--split", choices=["train", "dev", "test"], default="test",
                        help="Which split to evaluate (default: test; use dev during development)")
    parser.add_argument("--full-pipeline", action="store_true",
                        help="Use cwyde's own entity detection instead of gold spans")
    parser.add_argument("--lang", default="en",
                        help="cwyde language plugin (default: en)")
    parser.add_argument("--errors", action="store_true",
                        help="Print per-entity errors to stderr")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Evaluate on first N records only (for quick sanity checks)")
    args = parser.parse_args()

    if args.split != "test":
        print(f"NOTE: evaluating on '{args.split}' split — test split is held out for final reporting.")

    split_file = find_split_file(args.data_dir.resolve(), args.split)
    print(f"RadGraph-XL split file : {split_file}")
    print(f"Evaluation mode        : {'full pipeline' if args.full_pipeline else 'given-entity (gold spans)'}")
    print(f"Language               : {args.lang}")
    print()

    print("Building cwyde pipeline …")
    nlp = build_pipeline(args.lang)

    all_results = []
    n_records = 0

    for record in iter_records(split_file):
        if args.limit and n_records >= args.limit:
            break
        try:
            text, gold_entities = load_gold_entities(record)
        except Exception as e:
            print(f"  WARNING: skipping record {record.get('doc_key')}: {e}", file=sys.stderr)
            continue

        if not gold_entities:
            continue

        if args.full_pipeline:
            results = run_full_pipeline(nlp, text, gold_entities)
        else:
            results = run_given_entity(nlp, text, gold_entities)

        all_results.extend(results)
        n_records += 1

        if args.errors:
            for r in results:
                if r["gold"] != r["predicted"]:
                    print(f"  ERROR  gold={r['gold']:<20} pred={r['predicted']:<20} text={r['text']!r}",
                          file=sys.stderr)

    print(f"Evaluated {n_records} reports, {len(all_results)} entity assertions.")
    metrics = compute_f1(all_results)
    print_metrics(metrics)

    # Summary line for paper tables
    print(f"\ncwyde {args.lang} | given-entity={'yes' if not args.full_pipeline else 'no'} | "
          f"micro-F1={metrics['micro']['f1']:.3f} | "
          f"weighted-F1={metrics['weighted']['f1']:.3f} | "
          f"macro-F1={metrics['macro']['f1']:.3f}")


if __name__ == "__main__":
    main()
