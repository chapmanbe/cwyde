#!/usr/bin/env python3
"""
Migrate pyConTextNLP YAML knowledge bases to cwyde-knowledge schema.

Usage:
    python scripts/migrate_pycontext_kb.py \\
        ~/Code/Python/pyConTextNLP/KB \\
        packages/cwyde-knowledge/src/cwyde_knowledge/data/lang/en/lexicon/

Legacy pyConTextNLP keys:
    Lex, Regex, Direction, Type, Comments

cwyde-knowledge keys:
    lex, regex, direction, category, notes, source
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


CATEGORY_MAP = {
    "DEFINITE_NEGATED_EXISTENCE": "DEFINITE_NEGATED_EXISTENCE",
    "PROBABLE_NEGATED_EXISTENCE": "PROBABLE_NEGATED_EXISTENCE",
    "AMBIVALENT_EXISTENCE": "AMBIVALENT_EXISTENCE",
    "PROBABLE_EXISTENCE": "PROBABLE_EXISTENCE",
    "DEFINITE_EXISTENCE": "DEFINITE_EXISTENCE",
    "INDICATION": "INDICATION",
    "HISTORICAL": "HISTORICAL",
    "HYPOTHETICAL": "HYPOTHETICAL",
    "FAMILY": "FAMILY",
    # pyConTextNLP aliases
    "POSSIBLE_EXISTENCE": "PROBABLE_EXISTENCE",
    "POSSIBLE_NEGATED_EXISTENCE": "PROBABLE_NEGATED_EXISTENCE",
}

DIRECTION_MAP = {
    "forward": "forward",
    "backward": "backward",
    "bidirectional": "bidirectional",
    "terminate": "terminate",
}


def migrate_file(src: Path, source_name: str) -> dict:
    """Convert a pyConTextNLP multi-document YAML file to cwyde LexiconFile dict."""
    raw = src.read_text(encoding="utf-8")
    docs = list(yaml.safe_load_all(raw))

    entries = []
    skipped = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue

        lex = doc.get("Lex") or doc.get("lex", "")
        regex = doc.get("Regex") or doc.get("regex") or None
        direction_raw = (doc.get("Direction") or doc.get("direction", "forward")).lower()
        type_raw = doc.get("Type") or doc.get("type") or doc.get("category", "")
        comments = doc.get("Comments") or doc.get("comments") or ""

        if not lex and not regex:
            continue

        direction = DIRECTION_MAP.get(direction_raw)
        if direction is None:
            skipped.append({"lex": lex, "reason": f"unknown direction {direction_raw!r}"})
            continue

        category = CATEGORY_MAP.get(type_raw)
        if category is None:
            skipped.append({"lex": lex, "reason": f"unknown category {type_raw!r}"})
            continue

        entry = {
            "lex": str(lex),
            "direction": direction,
            "category": category,
        }
        if regex and str(regex).strip():
            entry["regex"] = str(regex).strip()
        if comments and str(comments).strip():
            entry["notes"] = str(comments).strip()
        if source_name:
            entry["source"] = source_name

        entries.append(entry)

    if skipped:
        print(f"  Skipped {len(skipped)} entries from {src.name}:", file=sys.stderr)
        for s in skipped:
            print(f"    {s}", file=sys.stderr)

    return {"schema_version": 1, "entries": entries}


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <src_kb_dir> <dest_lexicon_dir>", file=sys.stderr)
        sys.exit(1)

    src_dir = Path(sys.argv[1]).expanduser()
    dest_dir = Path(sys.argv[2]).expanduser()
    dest_dir.mkdir(parents=True, exist_ok=True)

    kb_files = list(src_dir.glob("*.yml")) + list(src_dir.glob("*.yaml"))
    if not kb_files:
        print(f"No YAML files found in {src_dir}", file=sys.stderr)
        sys.exit(1)

    for kb_file in sorted(kb_files):
        dest_name = kb_file.stem.replace("-", "_") + ".yaml"
        dest_path = dest_dir / dest_name
        print(f"Migrating {kb_file.name} → {dest_path.name}")

        data = migrate_file(kb_file, source_name=f"pyConTextNLP/{kb_file.name}")
        with open(dest_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        print(f"  {len(data['entries'])} entries written")

    print(f"\nMigration complete. {len(kb_files)} files processed.")


if __name__ == "__main__":
    main()
