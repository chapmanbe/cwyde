"""Integration tests for gamen-validate bridge.

These tests require a built gamen-validate binary.
They are skipped when the binary is not available (unless --require-gamen is set).
"""

import pytest
from cwyde.formal.modal import Atom, Box, Diamond, Not
from cwyde.formal.translator import category_to_formula
from cwyde.categories import AssertionCategory


pytestmark = pytest.mark.requires_gamen


def test_bridge_ping(gamen_available):
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    assert bridge.ping()


def test_validate_definite_existence(gamen_available):
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
    formula = category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe")
    result = bridge.validate_formula(formula)
    assert result.ok


def test_validate_indication(gamen_available):
    from cwyde_haskell_bridge import GamenBridge
    bridge = GamenBridge()
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
