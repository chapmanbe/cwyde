"""Unit tests for the category → modal formula translator (v0.3 ranked-belief encoding)."""

import pytest
from cwyde.categories import AssertionCategory
from cwyde.formal.translator import category_to_formula
from cwyde.formal.modal import Atom, Past, Indication, Belief, RankedBelief


# ---------------------------------------------------------------------------
# Existence-axis categories → RankedBelief with signed rank
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category,expected_rank", [
    (AssertionCategory.DEFINITE_EXISTENCE,         2),
    (AssertionCategory.PROBABLE_EXISTENCE,         1),
    (AssertionCategory.AMBIVALENT_EXISTENCE,       0),
    (AssertionCategory.PROBABLE_NEGATED_EXISTENCE, -1),
    (AssertionCategory.DEFINITE_NEGATED_EXISTENCE, -2),
])
def test_existence_axis_is_ranked_belief(category, expected_rank):
    formula = category_to_formula(category, "x")
    assert isinstance(formula, RankedBelief)
    assert formula.agent == "clinician"
    assert formula.rank == expected_rank
    assert isinstance(formula.operand, Atom)
    assert formula.operand.name == "x"


def test_ambivalent_rank_zero_is_neutrality():
    # τ=0 encodes genuine neutrality — not 50/50, but neither X nor ¬X is disbelieved.
    formula = category_to_formula(AssertionCategory.AMBIVALENT_EXISTENCE, "x")
    assert formula.rank == 0


# ---------------------------------------------------------------------------
# Non-existence-axis categories stay as Belief
# ---------------------------------------------------------------------------

def test_historical_is_belief_of_past():
    formula = category_to_formula(AssertionCategory.HISTORICAL, "x")
    assert isinstance(formula, Belief)
    assert isinstance(formula.operand, Past)


def test_hypothetical_is_belief():
    formula = category_to_formula(AssertionCategory.HYPOTHETICAL, "x")
    assert isinstance(formula, Belief)
    assert formula.agent == "clinician"


def test_family_uses_sortal_atom():
    formula = category_to_formula(AssertionCategory.FAMILY, "diabetes")
    assert isinstance(formula, Belief)
    assert isinstance(formula.operand, Atom)
    assert formula.operand.name == "diabetes_family"


def test_indication_is_indication():
    formula = category_to_formula(AssertionCategory.INDICATION, "x")
    assert isinstance(formula, Indication)


# ---------------------------------------------------------------------------
# Agent kwarg propagation
# ---------------------------------------------------------------------------

def test_agent_kwarg_propagates_to_ranked_belief():
    formula = category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "x", agent="radiologist")
    assert isinstance(formula, RankedBelief)
    assert formula.agent == "radiologist"


def test_agent_kwarg_propagates_to_belief():
    formula = category_to_formula(AssertionCategory.HYPOTHETICAL, "x", agent="radiologist")
    assert isinstance(formula, Belief)
    assert formula.agent == "radiologist"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_unresolved_raises():
    with pytest.raises(ValueError, match="UNRESOLVED"):
        category_to_formula(AssertionCategory.UNRESOLVED, "x")


# ---------------------------------------------------------------------------
# Round-trip: every resolvable category produces valid tree JSON
# ---------------------------------------------------------------------------

def test_all_resolvable_categories_round_trip():
    for cat in AssertionCategory:
        if cat == AssertionCategory.UNRESOLVED:
            continue
        formula = category_to_formula(cat, "test_atom")
        tree = formula.to_tree_json()
        assert isinstance(tree, dict)
        assert "type" in tree
