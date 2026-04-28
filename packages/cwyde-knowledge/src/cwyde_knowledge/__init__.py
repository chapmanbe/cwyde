"""cwyde-knowledge — path resolver for clinical NLP knowledge bases."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def data_root() -> Path:
    return Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def default_interaction_rules():
    from cwyde.kb import load_interaction_rules
    return load_interaction_rules(data_root() / "core" / "interaction_rules.yaml")


@lru_cache(maxsize=1)
def default_medspacy_category_map():
    from cwyde.kb import load_medspacy_category_map
    return load_medspacy_category_map(data_root() / "core" / "medspacy_category_map.yaml")


@lru_cache(maxsize=1)
def default_section_assertions():
    from cwyde.kb import load_section_assertions
    return load_section_assertions(data_root() / "core" / "section_assertions.yaml")


def default_indication_patterns(lang: str = "en"):
    from cwyde.kb import load_patterns
    path = data_root() / "lang" / lang / "indication_patterns.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No indication patterns for lang={lang!r} at {path}")
    return load_patterns(path)
