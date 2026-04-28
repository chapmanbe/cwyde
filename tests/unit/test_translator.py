"""Unit tests for the category → modal formula translator."""

import pytest
from cwyde.categories import AssertionCategory
from cwyde.formal.translator import category_to_formula
from cwyde.formal.modal import Box, Diamond, And, Not, Past, Indication, Knowledge


@pytest.mark.parametrize("category,expected_type", [
    (AssertionCategory.DEFINITE_EXISTENCE, Box),
    (AssertionCategory.PROBABLE_EXISTENCE, Diamond),
    (AssertionCategory.PROBABLE_NEGATED_EXISTENCE, Diamond),
    (AssertionCategory.DEFINITE_NEGATED_EXISTENCE, Box),
    (AssertionCategory.HISTORICAL, Past),
    (AssertionCategory.INDICATION, Indication),
    (AssertionCategory.FAMILY, Knowledge),
])
def test_formula_types(category, expected_type):
    formula = category_to_formula(category, "x")
    assert isinstance(formula, expected_type), f"{category} should produce {expected_type.__name__}"


def test_ambivalent_is_and():
    formula = category_to_formula(AssertionCategory.AMBIVALENT_EXISTENCE, "x")
    assert isinstance(formula, And)


def test_definite_negated_wraps_not():
    formula = category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "x")
    assert isinstance(formula, Box)
    assert isinstance(formula.operand, Not)


def test_probable_negated_wraps_not():
    formula = category_to_formula(AssertionCategory.PROBABLE_NEGATED_EXISTENCE, "x")
    assert isinstance(formula, Diamond)
    assert isinstance(formula.operand, Not)


def test_unresolved_raises():
    with pytest.raises(ValueError, match="UNRESOLVED"):
        category_to_formula(AssertionCategory.UNRESOLVED, "x")


def test_all_resolvable_categories_round_trip():
    """Every category except UNRESOLVED produces valid tree JSON."""
    for cat in AssertionCategory:
        if cat == AssertionCategory.UNRESOLVED:
            continue
        formula = category_to_formula(cat, "test_atom")
        tree = formula.to_tree_json()
        assert isinstance(tree, dict)
        assert "type" in tree
