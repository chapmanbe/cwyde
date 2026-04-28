#!/usr/bin/env python3
"""
CI script: load every KB YAML in cwyde-knowledge and validate against schema.
Exits non-zero if any file fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
DATA = ROOT / "packages" / "cwyde-knowledge" / "src" / "cwyde_knowledge" / "data"

FAILURES: list[str] = []


def check(path: Path, loader_name: str) -> None:
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "packages" / "cwyde-knowledge" / "src"))

    from cwyde import kb  # noqa: F401

    loader = getattr(kb, loader_name)
    try:
        loader(path)
        print(f"  OK  {path.relative_to(ROOT)}")
    except Exception as exc:
        print(f"  FAIL {path.relative_to(ROOT)}: {exc}")
        FAILURES.append(str(path))


def main():
    print("Validating cwyde-knowledge YAML files...\n")

    core = DATA / "core"
    checks = [
        (core / "categories.yaml", "load_categories"),
        (core / "medspacy_category_map.yaml", "load_medspacy_category_map"),
        (core / "interaction_rules.yaml", "load_interaction_rules"),
        (core / "section_assertions.yaml", "load_section_assertions"),
    ]

    if (core / "fallback_table.yaml").exists():
        checks.append((core / "fallback_table.yaml", "load_fallback_table"))

    for path, loader_name in checks:
        if path.exists():
            check(path, loader_name)
        else:
            print(f"  MISSING {path.relative_to(ROOT)}")
            FAILURES.append(str(path))

    for lang_dir in (DATA / "lang").iterdir():
        if not lang_dir.is_dir():
            continue
        for lex_file in (lang_dir / "lexicon").glob("*.yaml"):
            check(lex_file, "load_lexicon")
        for pat_file in lang_dir.glob("*_patterns.yaml"):
            check(pat_file, "load_patterns")

    if FAILURES:
        print(f"\n{len(FAILURES)} validation failure(s). See above.")
        sys.exit(1)
    else:
        print(f"\nAll KB files valid.")


if __name__ == "__main__":
    main()
