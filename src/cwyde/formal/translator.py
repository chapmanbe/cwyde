"""
Translates AssertionCategory values to ModalFormula trees.

v0.3: existence-axis categories encode as RankedBelief(agent, rank, atom) using
Spohn (1988) signed-int OCF semantics. Grade is encoded in the rank integer:

    DEFINITE_EXISTENCE         → RankedBelief(a,  2, X)
    PROBABLE_EXISTENCE         → RankedBelief(a,  1, X)
    AMBIVALENT_EXISTENCE       → RankedBelief(a,  0, X)   # τ=0 = neutrality
    PROBABLE_NEGATED_EXISTENCE → RankedBelief(a, -1, X)
    DEFINITE_NEGATED_EXISTENCE → RankedBelief(a, -2, X)

The threshold N=2 separating DEFINITE from PROBABLE is a cwyde policy choice;
gamen-hs is agnostic about it.

HISTORICAL uses sortal atomisation: B_a(X_history).
FAMILY uses sortal atomisation: B_a(X_family).

HISTORICAL used to be B_a(P(X)), with P the past-diamond operator. gamen-hs
quarantines all temporal tableau operators (gamen-hs#25), so gamen-validate
rejects past_diamond in a consistency check. Before the quarantine, P(X) was
never decomposed, so a joint check containing it passed without any reasoning
about the past. The sortal atom keeps the distinction cwyde needs (a past
finding does not clash with a current negation) without temporal reasoning.
HYPOTHETICAL and INDICATION are unchanged from v0.2.
"""

from __future__ import annotations

from cwyde.categories import AssertionCategory
from cwyde.formal.modal import (
    Atom, Indication, Belief, RankedBelief, ModalFormula
)


def category_to_formula(category: AssertionCategory, atom: str, *, agent: str = "clinician") -> ModalFormula:
    """Return a ModalFormula encoding the assertion of `atom` under `category`."""
    x = Atom(atom)
    match category:
        case AssertionCategory.DEFINITE_EXISTENCE:
            return RankedBelief(agent, 2, x)
        case AssertionCategory.PROBABLE_EXISTENCE:
            return RankedBelief(agent, 1, x)
        case AssertionCategory.AMBIVALENT_EXISTENCE:
            # τ=0: neither X nor ¬X is disbelieved — genuine neutrality, not 50/50.
            return RankedBelief(agent, 0, x)
        case AssertionCategory.PROBABLE_NEGATED_EXISTENCE:
            return RankedBelief(agent, -1, x)
        case AssertionCategory.DEFINITE_NEGATED_EXISTENCE:
            return RankedBelief(agent, -2, x)
        case AssertionCategory.HISTORICAL:
            # Sortal restriction: clinician believes X was the case in the past.
            # Not Past(x): gamen-hs quarantines temporal operators (gamen-hs#25).
            return Belief(agent, Atom(f"{atom}_history"))
        case AssertionCategory.HYPOTHETICAL:
            # Belief in X scoped to a conditional/hypothetical context; category marks conditionality.
            return Belief(agent, x)
        case AssertionCategory.FAMILY:
            # Sortal restriction: clinician believes X holds of a family member, not the patient.
            return Belief(agent, Atom(f"{atom}_family"))
        case AssertionCategory.INDICATION:
            return Indication(x, agent=agent)
        case AssertionCategory.UNRESOLVED:
            raise ValueError(
                f"UNRESOLVED has no modal encoding — resolve the conflict before translating"
            )
        case _:
            raise ValueError(f"Unknown AssertionCategory: {category}")
