"""
Unit tests for pseudo-trigger suppression (Issue #3).

Pseudo-triggers contain trigger words ("no", "history", "if", ...) but must
NOT act as contextual modifiers. They are loaded as TERMINATE rules so that
medspaCy's longest-match pruning suppresses the shorter trigger whenever the
multi-token pseudo-trigger phrase is matched.

These are integration-style unit tests that build a minimal pipeline to verify
the end-to-end suppression behaviour without depending on the full test suite
infrastructure.
"""

import pytest
import medspacy
from medspacy.target_matcher import TargetRule

from cwyde.pipeline import add_to
from cwyde.categories import AssertionCategory


@pytest.fixture(scope="module")
def nlp():
    pipeline = medspacy.load()
    pipeline.add_pipe("medspacy_sectionizer")
    tm = pipeline.get_pipe("medspacy_target_matcher")
    tm.add([TargetRule("PE", "CONDITION")])
    tm.add([TargetRule("pulmonary embolism", "CONDITION")])
    add_to(pipeline, lang="en")
    return pipeline


def _category(nlp, text: str) -> AssertionCategory | None:
    """Return the assertion category of the first entity in *text*, or None."""
    doc = nlp(text)
    if not doc.ents:
        return None
    return doc.ents[0]._.cwyde_assertion_category


# ---------------------------------------------------------------------------
# Negation pseudo-triggers
# ---------------------------------------------------------------------------

class TestNegationPseudoTriggers:
    def test_no_increase_not_negated(self, nlp):
        """'no increase in PE burden' — 'no increase' is a pseudo-trigger;
        the finding PE should NOT be negated."""
        cat = _category(nlp, "No increase in PE burden since prior study.")
        # PE is still present (DEFINITE_EXISTENCE baseline); if ConText erroneously
        # fires on "no", it would produce DEFINITE_NEGATED_EXISTENCE.
        assert cat != AssertionCategory.DEFINITE_NEGATED_EXISTENCE, (
            f"PE was incorrectly negated by 'no increase'; got {cat}"
        )

    def test_no_evidence_is_negated(self, nlp):
        """'No evidence of PE' — this is real negation, not a pseudo-trigger."""
        cat = _category(nlp, "No evidence of PE.")
        assert cat == AssertionCategory.DEFINITE_NEGATED_EXISTENCE, (
            f"Expected DEFINITE_NEGATED_EXISTENCE; got {cat}"
        )

    def test_no_change_not_negated(self, nlp):
        """'No change' is a pseudo-trigger; the entity following should not be negated."""
        cat = _category(nlp, "No change in PE since the last study.")
        assert cat != AssertionCategory.DEFINITE_NEGATED_EXISTENCE, (
            f"PE was incorrectly negated by 'no change'; got {cat}"
        )


# ---------------------------------------------------------------------------
# Historical pseudo-triggers
# ---------------------------------------------------------------------------

class TestHistoricalPseudoTriggers:
    def test_history_and_physical_not_historical(self, nlp):
        """'History and physical exam showed PE' — 'history and physical' is a
        section/documentation phrase; PE should NOT be marked HISTORICAL."""
        cat = _category(nlp, "History and physical exam showed PE.")
        assert cat != AssertionCategory.HISTORICAL, (
            f"PE was incorrectly marked HISTORICAL by 'history and physical'; got {cat}"
        )

    def test_history_of_pe_is_historical(self, nlp):
        """'History of PE' — this is real historical; should fire HISTORICAL."""
        cat = _category(nlp, "Patient has a history of PE.")
        assert cat == AssertionCategory.HISTORICAL, (
            f"Expected HISTORICAL; got {cat}"
        )
