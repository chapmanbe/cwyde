"""
AssertionCategory enum — the core taxonomy for clinical context modifiers.

Modal readings (B&D notation):
  DEFINITE_EXISTENCE          □X   — necessarily present
  PROBABLE_EXISTENCE          ◇X   — possibly present
  AMBIVALENT_EXISTENCE        ◇X ∧ ◇¬X — indeterminate
  PROBABLE_NEGATED_EXISTENCE  ◇¬X  — possibly absent
  DEFINITE_NEGATED_EXISTENCE  □¬X  — necessarily absent
  INDICATION                  ?(X) — under investigation; neither asserted nor denied
  HISTORICAL                  P(X) — was the case
  HYPOTHETICAL                hyp(X) — in a hypothetical or conditional scenario
  FAMILY                      fam(X) — applies to family member, not patient
  UNRESOLVED                  ⊥    — conflict not resolvable; explicit non-answer
"""

from enum import Enum


class AssertionCategory(str, Enum):
    DEFINITE_EXISTENCE = "DEFINITE_EXISTENCE"
    PROBABLE_EXISTENCE = "PROBABLE_EXISTENCE"
    AMBIVALENT_EXISTENCE = "AMBIVALENT_EXISTENCE"
    PROBABLE_NEGATED_EXISTENCE = "PROBABLE_NEGATED_EXISTENCE"
    DEFINITE_NEGATED_EXISTENCE = "DEFINITE_NEGATED_EXISTENCE"
    INDICATION = "INDICATION"
    HISTORICAL = "HISTORICAL"
    HYPOTHETICAL = "HYPOTHETICAL"
    FAMILY = "FAMILY"
    UNRESOLVED = "UNRESOLVED"

    def is_negated(self) -> bool:
        return self in (
            AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
            AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
        )

    def is_uncertain(self) -> bool:
        return self in (
            AssertionCategory.PROBABLE_EXISTENCE,
            AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
            AssertionCategory.AMBIVALENT_EXISTENCE,
        )

    def is_existence_axis(self) -> bool:
        """True for the five certainty-of-existence categories."""
        return self in (
            AssertionCategory.DEFINITE_EXISTENCE,
            AssertionCategory.PROBABLE_EXISTENCE,
            AssertionCategory.AMBIVALENT_EXISTENCE,
            AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
            AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
        )
