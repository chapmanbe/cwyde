"""Integration tests for gamen-validate bridge.

These tests require a built gamen-validate binary.
They are skipped when the binary is not available (unless --require-gamen is set).
"""

import pytest
from cwyde.formal.modal import Atom, Box
from cwyde.formal.translator import category_to_formula
from cwyde.categories import AssertionCategory


pytestmark = pytest.mark.requires_gamen


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------

def test_bridge_ping(gamen_available):
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    assert bridge.ping()


# ---------------------------------------------------------------------------
# validate_formula — all categories round-trip
# ---------------------------------------------------------------------------

def test_validate_definite_existence(gamen_available):
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    formula = category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe")
    result = bridge.validate_formula(formula)
    assert result.ok


def test_validate_indication(gamen_available):
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    # INDICATION expands to And(Not(K_a(X)), Not(K_a(Not(X)))) in tree format
    formula = category_to_formula(AssertionCategory.INDICATION, "pe")
    result = bridge.validate_formula(formula)
    assert result.ok


@pytest.mark.parametrize("category", [
    AssertionCategory.DEFINITE_EXISTENCE,
    AssertionCategory.PROBABLE_EXISTENCE,
    AssertionCategory.AMBIVALENT_EXISTENCE,
    AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
    AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
    AssertionCategory.HISTORICAL,
    AssertionCategory.INDICATION,
    AssertionCategory.FAMILY,
])
def test_all_categories_validate(category, gamen_available):
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    formula = category_to_formula(category, "finding")
    result = bridge.validate_formula(formula)
    assert result.ok, f"Category {category} formula failed validation"


# ---------------------------------------------------------------------------
# check_consistency — semantic correctness
# ---------------------------------------------------------------------------

def test_consistency_inconsistent_pair(gamen_available):
    """□X ∧ □¬X is inconsistent in any normal modal logic."""
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    formulas = [
        category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe"),
        category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "pe"),
    ]
    result = bridge.check_consistency(formulas)
    assert result.ok
    assert result.consistent is False


def test_consistency_consistent_pair(gamen_available):
    """Beliefs about distinct atoms are jointly satisfiable (OCF v0.3).

    RankedBelief(a, n, X) and RankedBelief(a, m, X) with n≠m violate the
    functionality rule (τ is a function). Using different atoms avoids that.
    """
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    formulas = [
        category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe"),
        category_to_formula(AssertionCategory.PROBABLE_EXISTENCE, "dvt"),
    ]
    result = bridge.check_consistency(formulas)
    assert result.ok
    assert result.consistent is True


def test_consistency_indication_with_existence(gamen_available):
    """INDICATION is compatible with DEFINITE_EXISTENCE (clinician can discover it's present)."""
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    formulas = [
        category_to_formula(AssertionCategory.INDICATION, "dvt"),
        category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "dvt"),
    ]
    result = bridge.check_consistency(formulas)
    assert result.ok
    assert result.consistent is True


def test_consistency_single_formula(gamen_available):
    """A single formula is trivially consistent."""
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    result = bridge.check_consistency([Box(Atom("x"))])
    assert result.ok
    assert result.consistent is True


# ---------------------------------------------------------------------------
# GamenStrategy integration
# ---------------------------------------------------------------------------

def test_gamen_strategy_is_available(gamen_available):
    from cwyde.formal.strategy import GamenStrategy
    strategy = GamenStrategy()
    assert strategy.is_available()


def test_gamen_strategy_check_consistency_inconsistent(gamen_available):
    from cwyde.formal.strategy import GamenStrategy
    strategy = GamenStrategy()
    formulas = [
        category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "fever"),
        category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "fever"),
    ]
    result = strategy.check_consistency(formulas)
    assert result.consistent is False


def test_gamen_strategy_check_consistency_consistent(gamen_available):
    from cwyde.formal.strategy import GamenStrategy
    strategy = GamenStrategy()
    formulas = [
        category_to_formula(AssertionCategory.PROBABLE_EXISTENCE, "hypertension"),
        category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "dvt"),
    ]
    # Different atoms — jointly satisfiable under OCF functionality rule.
    result = strategy.check_consistency(formulas)
    assert result.consistent is True


# ---------------------------------------------------------------------------
# Flat extraction format
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", [
    AssertionCategory.DEFINITE_EXISTENCE,
    AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
    AssertionCategory.HISTORICAL,
    AssertionCategory.INDICATION,
])
def test_flat_format_round_trip(category, gamen_available):
    """Flat extraction format (used by LLM output path) also validates."""
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    formula = category_to_formula(category, "finding")
    flat_tree = formula.to_flat_extraction()
    # Submit flat format directly via _call to test the protocol path
    resp = bridge._call({"action": "validate_formula", "formula": flat_tree})
    assert resp.get("ok", False), f"Flat format failed for {category}: {resp}"
