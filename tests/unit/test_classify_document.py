"""
Unit tests for classify_document() — Issue #8.

Uses lightweight mock objects rather than a full spaCy doc so the tests
run quickly and without network access. Each mock entity exposes the two
attributes that classify_document() reads: `.label_` and
`._.cwyde_assertion_category`.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from cwyde import classify_document
from cwyde.categories import AssertionCategory
from cwyde.models import DocumentClassification


# ---------------------------------------------------------------------------
# Minimal mock infrastructure
# ---------------------------------------------------------------------------

@dataclass
class _MockExt:
    cwyde_assertion_category: AssertionCategory


@dataclass
class _MockEnt:
    text: str
    label_: str
    _: _MockExt


class _MockDoc:
    """A minimal stand-in for a spaCy Doc with a list of entities."""

    def __init__(self, ents: list[_MockEnt]):
        self.ents = ents


def _make_ent(
    text: str,
    category: AssertionCategory,
    label: str = "CONDITION",
) -> _MockEnt:
    return _MockEnt(text=text, label_=label, _=_MockExt(cwyde_assertion_category=category))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestClassifyDocumentBasics:
    def test_single_definite_existence(self):
        """Single DEFINITE_EXISTENCE entity → tau=2, assertion=DEFINITE_EXISTENCE."""
        doc = _MockDoc([_make_ent("PE", AssertionCategory.DEFINITE_EXISTENCE)])
        result = classify_document(doc, "CONDITION")
        assert result.tau_combined == 2
        assert result.assertion == AssertionCategory.DEFINITE_EXISTENCE
        assert result.acuity == "acute"
        assert result.confidence == 1.0

    def test_single_definite_negated_existence(self):
        """Single DEFINITE_NEGATED_EXISTENCE entity → tau=-2."""
        doc = _MockDoc([_make_ent("PE", AssertionCategory.DEFINITE_NEGATED_EXISTENCE)])
        result = classify_document(doc, "CONDITION")
        assert result.tau_combined == -2
        assert result.assertion == AssertionCategory.DEFINITE_NEGATED_EXISTENCE
        assert result.acuity == "acute"

    def test_mixed_definite_plus_probable_negated(self):
        """DEFINITE_EXISTENCE(τ=2) + PROBABLE_NEGATED_EXISTENCE(τ=-1) → sum=1."""
        doc = _MockDoc([
            _make_ent("PE in RLL", AssertionCategory.DEFINITE_EXISTENCE),
            _make_ent("PE in LUL", AssertionCategory.PROBABLE_NEGATED_EXISTENCE),
        ])
        result = classify_document(doc, "CONDITION")
        assert result.tau_combined == 1
        assert result.assertion == AssertionCategory.PROBABLE_EXISTENCE
        assert result.acuity == "acute"

    def test_historical_entity_acuity(self):
        """HISTORICAL entity → tau=0 (no numeric rank), acuity='historical'."""
        doc = _MockDoc([_make_ent("PE", AssertionCategory.HISTORICAL)])
        result = classify_document(doc, "CONDITION")
        assert result.tau_combined == 0
        assert result.assertion == AssertionCategory.AMBIVALENT_EXISTENCE
        assert result.acuity == "historical"

    def test_no_matching_entities(self):
        """No entities matching target_type → tau=0, AMBIVALENT_EXISTENCE."""
        doc = _MockDoc([_make_ent("DVT", AssertionCategory.DEFINITE_EXISTENCE, label="OTHER")])
        result = classify_document(doc, "CONDITION")
        assert result.tau_combined == 0
        assert result.assertion == AssertionCategory.AMBIVALENT_EXISTENCE
        assert result.evidence == []

    def test_confidence_below_one_when_unresolved(self):
        """UNRESOLVED entity reduces confidence below 1.0."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.DEFINITE_EXISTENCE),
            _make_ent("DVT", AssertionCategory.UNRESOLVED),
        ])
        result = classify_document(doc, "CONDITION")
        # 1 resolved out of 2 total
        assert result.confidence == pytest.approx(0.5)


class TestClassifyDocumentAggregation:
    def test_max_aggregation(self):
        """aggregation='max' uses max(τᵢ) instead of sum."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.DEFINITE_NEGATED_EXISTENCE),  # τ=-2
            _make_ent("DVT", AssertionCategory.PROBABLE_EXISTENCE),          # τ=1
        ])
        result = classify_document(doc, "CONDITION", aggregation="max")
        assert result.tau_combined == 1
        assert result.assertion == AssertionCategory.PROBABLE_EXISTENCE

    def test_clamping_at_positive_2(self):
        """Sum that exceeds +2 is clamped to +2."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.DEFINITE_EXISTENCE),   # τ=2
            _make_ent("DVT", AssertionCategory.DEFINITE_EXISTENCE),  # τ=2
        ])
        result = classify_document(doc, "CONDITION")
        assert result.tau_combined == 2  # clamped from 4

    def test_clamping_at_negative_2(self):
        """Sum that goes below -2 is clamped to -2."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.DEFINITE_NEGATED_EXISTENCE),   # τ=-2
            _make_ent("DVT", AssertionCategory.DEFINITE_NEGATED_EXISTENCE),  # τ=-2
        ])
        result = classify_document(doc, "CONDITION")
        assert result.tau_combined == -2  # clamped from -4


class TestClassifyDocumentFiltering:
    def test_filter_by_target_type_case_insensitive(self):
        """target_type matching is case-insensitive."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.DEFINITE_EXISTENCE, label="CONDITION"),
            _make_ent("family hx", AssertionCategory.DEFINITE_NEGATED_EXISTENCE, label="OTHER"),
        ])
        result = classify_document(doc, "condition")  # lowercase
        assert len(result.evidence) == 1
        assert result.tau_combined == 2

    def test_empty_target_type_includes_all(self):
        """Empty target_type includes all entities."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.DEFINITE_EXISTENCE, label="CONDITION"),
            _make_ent("DVT", AssertionCategory.PROBABLE_NEGATED_EXISTENCE, label="OTHER"),
        ])
        result = classify_document(doc, "")
        assert len(result.evidence) == 2
        assert result.tau_combined == 1  # 2 + (-1)

    def test_none_target_type_includes_all(self):
        """None target_type includes all entities."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.DEFINITE_EXISTENCE, label="CONDITION"),
        ])
        result = classify_document(doc, None)
        assert len(result.evidence) == 1


class TestClassifyDocumentEvidence:
    def test_evidence_list_populated(self):
        """Evidence list captures mention text, category, and tau."""
        doc = _MockDoc([
            _make_ent("PE in right lower lobe", AssertionCategory.DEFINITE_EXISTENCE),
        ])
        result = classify_document(doc, "CONDITION")
        assert len(result.evidence) == 1
        ev = result.evidence[0]
        assert ev.mention == "PE in right lower lobe"
        assert ev.category == AssertionCategory.DEFINITE_EXISTENCE
        assert ev.tau == 2

    def test_historical_entity_has_none_tau(self):
        """Non-existence categories have tau=None in evidence."""
        doc = _MockDoc([_make_ent("PE", AssertionCategory.HISTORICAL)])
        result = classify_document(doc, "CONDITION")
        assert result.evidence[0].tau is None

    def test_hypothetical_entity_acuity(self):
        """HYPOTHETICAL entity → acuity='hypothetical' (when no HISTORICAL)."""
        doc = _MockDoc([_make_ent("PE", AssertionCategory.HYPOTHETICAL)])
        result = classify_document(doc, "CONDITION")
        assert result.acuity == "hypothetical"

    def test_historical_beats_hypothetical_for_acuity(self):
        """When both HISTORICAL and HYPOTHETICAL present, acuity='historical'."""
        doc = _MockDoc([
            _make_ent("PE", AssertionCategory.HISTORICAL),
            _make_ent("DVT", AssertionCategory.HYPOTHETICAL),
        ])
        result = classify_document(doc, "CONDITION")
        assert result.acuity == "historical"
