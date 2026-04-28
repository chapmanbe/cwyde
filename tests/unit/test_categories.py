"""Unit tests for AssertionCategory."""

import pytest
from cwyde.categories import AssertionCategory


def test_all_categories_defined():
    expected = {
        "DEFINITE_EXISTENCE", "PROBABLE_EXISTENCE", "AMBIVALENT_EXISTENCE",
        "PROBABLE_NEGATED_EXISTENCE", "DEFINITE_NEGATED_EXISTENCE",
        "INDICATION", "HISTORICAL", "HYPOTHETICAL", "FAMILY", "UNRESOLVED",
    }
    assert {c.value for c in AssertionCategory} == expected


def test_is_negated():
    assert AssertionCategory.DEFINITE_NEGATED_EXISTENCE.is_negated()
    assert AssertionCategory.PROBABLE_NEGATED_EXISTENCE.is_negated()
    assert not AssertionCategory.DEFINITE_EXISTENCE.is_negated()
    assert not AssertionCategory.INDICATION.is_negated()
    assert not AssertionCategory.HISTORICAL.is_negated()


def test_is_uncertain():
    assert AssertionCategory.PROBABLE_EXISTENCE.is_uncertain()
    assert AssertionCategory.PROBABLE_NEGATED_EXISTENCE.is_uncertain()
    assert AssertionCategory.AMBIVALENT_EXISTENCE.is_uncertain()
    assert not AssertionCategory.DEFINITE_EXISTENCE.is_uncertain()
    assert not AssertionCategory.DEFINITE_NEGATED_EXISTENCE.is_uncertain()
    assert not AssertionCategory.INDICATION.is_uncertain()


def test_is_existence_axis():
    existence_axis = {
        AssertionCategory.DEFINITE_EXISTENCE,
        AssertionCategory.PROBABLE_EXISTENCE,
        AssertionCategory.AMBIVALENT_EXISTENCE,
        AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
        AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
    }
    for cat in existence_axis:
        assert cat.is_existence_axis(), f"{cat} should be on existence axis"

    non_existence = {
        AssertionCategory.INDICATION, AssertionCategory.HISTORICAL,
        AssertionCategory.HYPOTHETICAL, AssertionCategory.FAMILY,
        AssertionCategory.UNRESOLVED,
    }
    for cat in non_existence:
        assert not cat.is_existence_axis(), f"{cat} should not be on existence axis"


def test_string_value_matches_name():
    """Enum values are strings matching their names — safe to serialize to YAML."""
    for cat in AssertionCategory:
        assert cat.value == cat.name
