"""Unit tests for YAML knowledge base loaders."""

from pathlib import Path
import pytest
from cwyde.kb import (
    load_categories,
    load_medspacy_category_map,
    load_interaction_rules,
    load_section_assertions,
    load_patterns,
)
from cwyde.categories import AssertionCategory


DATA = Path(__file__).parent.parent.parent / "packages" / "cwyde-knowledge" / "src" / "cwyde_knowledge" / "data"
CORE = DATA / "core"
EN = DATA / "lang" / "en"


def test_load_categories():
    result = load_categories(CORE / "categories.yaml")
    assert result.schema_version == 3
    names = {c.category for c in result.categories}
    assert AssertionCategory.INDICATION in names
    assert AssertionCategory.DEFINITE_NEGATED_EXISTENCE in names
    assert len(result.categories) == len(AssertionCategory)


def test_load_medspacy_category_map():
    result = load_medspacy_category_map(CORE / "medspacy_category_map.yaml")
    assert result.schema_version == 1
    mapped = {e.medspacy_category for e in result.mappings}
    assert "NEGATED_EXISTENCE" in mapped
    assert "INDICATION" in mapped
    assert result.unmapped_default == AssertionCategory.UNRESOLVED


def test_load_interaction_rules():
    result = load_interaction_rules(CORE / "interaction_rules.yaml")
    assert result.schema_version == 1
    assert AssertionCategory.INDICATION in result.precedence
    assert result.precedence.index(AssertionCategory.INDICATION) == 0  # highest priority


def test_load_section_assertions():
    result = load_section_assertions(CORE / "section_assertions.yaml")
    assert result.schema_version == 1
    assert "past_medical_history" in result.section_assertions
    assert "indication" in result.section_assertions
    # indication section should override existing
    ind = result.section_assertions["indication"]
    assert ind.applies == AssertionCategory.INDICATION
    assert ind.override_existing is True


def test_load_indication_patterns_en():
    result = load_patterns(EN / "indication_patterns.yaml")
    assert result.schema_version == 1
    assert len(result.patterns) > 5
    patterns_text = [p.pattern for p in result.patterns]
    assert any("rule" in p for p in patterns_text)


def test_indication_patterns_compile():
    """All indication patterns must be valid regex."""
    import re
    result = load_patterns(EN / "indication_patterns.yaml")
    for p in result.patterns:
        re.compile(p.pattern)  # should not raise
