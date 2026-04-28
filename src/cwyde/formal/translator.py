"""
Translates AssertionCategory values to ModalFormula trees.

The mapping is declarative (loaded from modal_mapping.yaml) but the translation
itself is deterministic Python code. HISTORICAL and INDICATION use tree format
because their flat encodings would lose semantic precision.
"""

from __future__ import annotations

from cwyde.categories import AssertionCategory
from cwyde.formal.modal import (
    Atom, Box, Diamond, And, Not, Past, Indication, Knowledge, ModalFormula
)


def category_to_formula(category: AssertionCategory, atom: str, *, agent: str = "clinician") -> ModalFormula:
    """Return a ModalFormula encoding the assertion of `atom` under `category`."""
    x = Atom(atom)
    match category:
        case AssertionCategory.DEFINITE_EXISTENCE:
            return Box(x)
        case AssertionCategory.PROBABLE_EXISTENCE:
            return Diamond(x)
        case AssertionCategory.AMBIVALENT_EXISTENCE:
            return And(Diamond(x), Diamond(Not(x)))
        case AssertionCategory.PROBABLE_NEGATED_EXISTENCE:
            return Diamond(Not(x))
        case AssertionCategory.DEFINITE_NEGATED_EXISTENCE:
            return Box(Not(x))
        case AssertionCategory.HISTORICAL:
            return Past(x)
        case AssertionCategory.HYPOTHETICAL:
            # treat as ◇X in an accessible hypothetical world — simplest encoding for v0.1
            return Diamond(x)
        case AssertionCategory.FAMILY:
            # family member epistemic state: another agent knows X
            return Knowledge("family", x)
        case AssertionCategory.INDICATION:
            return Indication(x, agent=agent)
        case AssertionCategory.UNRESOLVED:
            raise ValueError(
                f"UNRESOLVED has no modal encoding — resolve the conflict before translating"
            )
        case _:
            raise ValueError(f"Unknown AssertionCategory: {category}")
