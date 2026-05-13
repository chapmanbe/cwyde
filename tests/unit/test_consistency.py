"""
Unit tests for cwyde_consistency_checker — joint satisfiability check (Issue #1).

The component is tested with mock entities and a mock strategy so the tests
run without medspaCy or gamen-validate. The smoke test against a real
pipeline lives separately (see scripts/smoke_consistency.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cwyde.categories import AssertionCategory
from cwyde.components.consistency_checker import (
    ConsistencyCheckerComponent,
    Inconsistency,
)
from cwyde.formal.modal import Atom, RankedBelief
from cwyde.formal.strategy import ConsistencyResult


# ---------------------------------------------------------------------------
# Mock infrastructure
# ---------------------------------------------------------------------------

@dataclass
class _Ext:
    cwyde_modal_formula: object = None
    cwyde_consistent: object = None


@dataclass
class _Ent:
    text: str
    start: int
    end: int
    _: _Ext = field(default_factory=_Ext)


@dataclass
class _Section:
    category: str
    body_span: tuple[int, int]


@dataclass
class _DocExt:
    sections: list[_Section] | None = None
    cwyde_inconsistencies: list[Inconsistency] | None = None


class _Doc:
    """A minimal stand-in for a spaCy Doc — exposes .ents and ._.sections."""

    def __init__(self, ents: list[_Ent], sections: list[_Section] | None = None):
        self.ents = ents
        self._ = _DocExt(sections=sections)


def _ent(text: str, start: int, end: int | None = None, *, formula=None) -> _Ent:
    e = _Ent(text=text, start=start, end=end if end is not None else start + 1)
    e._.cwyde_modal_formula = formula
    return e


def _ranked(rank: int, atom: str) -> RankedBelief:
    return RankedBelief("clinician", rank, Atom(atom))


class _MockStrategy:
    """Records calls to check_consistency and returns scripted results.

    Default behavior: all groups consistent. To script a False, set
    `return_consistent_for_atoms` to a set of atom names — any call whose
    formula list contains atoms in that set returns consistent=False.
    """

    def __init__(self, available: bool = True, return_consistent_for_atoms: set[str] | None = None):
        self.available = available
        self.calls: list[list] = []
        self.return_consistent_for_atoms = return_consistent_for_atoms or set()

    def is_available(self) -> bool:
        return self.available

    def check_consistency(self, formulas: list) -> ConsistencyResult:
        self.calls.append(formulas)
        atoms = {f.operand.name for f in formulas if hasattr(f, "operand") and hasattr(f.operand, "name")}
        if atoms & self.return_consistent_for_atoms:
            return ConsistencyResult(consistent=False, explanation="mock contradiction")
        return ConsistencyResult(consistent=True, explanation="")


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestConfigValidation:
    def test_invalid_grouping_raises(self):
        with pytest.raises(ValueError, match="grouping must be"):
            ConsistencyCheckerComponent(grouping="sentence")

    def test_valid_groupings_accepted(self):
        for g in ("section", "document"):
            ConsistencyCheckerComponent(grouping=g)


# ---------------------------------------------------------------------------
# Skip-if-unavailable behavior
# ---------------------------------------------------------------------------

class TestSkipUnavailable:
    def test_skip_when_unavailable(self):
        strategy = _MockStrategy(available=False)
        comp = ConsistencyCheckerComponent(strategy=strategy, skip_if_unavailable=True)
        doc = _Doc([_ent("x", 0, formula=_ranked(2, "x"))])
        comp(doc)
        assert strategy.calls == []
        assert doc._.cwyde_inconsistencies is None

    def test_raise_when_unavailable_and_no_skip(self):
        strategy = _MockStrategy(available=False)
        comp = ConsistencyCheckerComponent(strategy=strategy, skip_if_unavailable=False)
        with pytest.raises(RuntimeError, match="no reasoner available"):
            comp(_Doc([]))


# ---------------------------------------------------------------------------
# Per-entity well-formedness pass
# ---------------------------------------------------------------------------

class TestPerEntityWellFormednessPass:
    def test_sets_consistent_on_each_entity(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        e1 = _ent("x", 0, formula=_ranked(2, "x"))
        e2 = _ent("y", 1, formula=_ranked(-2, "y"))
        doc = _Doc([e1, e2])
        comp(doc)
        assert e1._.cwyde_consistent is True
        assert e2._.cwyde_consistent is True

    def test_none_when_no_formula(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        e1 = _ent("x", 0, formula=None)
        doc = _Doc([e1])
        comp(doc)
        assert e1._.cwyde_consistent is None


# ---------------------------------------------------------------------------
# Section grouping
# ---------------------------------------------------------------------------

class TestSectionGrouping:
    def _build(self):
        """Two sections, one entity each, all with distinct atoms (consistent)."""
        findings = _Section(category="findings", body_span=(0, 10))
        impression = _Section(category="impression", body_span=(10, 20))
        e_find = _ent("PE finding", 3, formula=_ranked(2, "pe"))
        e_imp = _ent("PE impression", 13, formula=_ranked(2, "pe"))
        return _Doc([e_find, e_imp], sections=[findings, impression])

    def test_each_section_gets_its_own_joint_call(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        doc = self._build()
        comp(doc)
        # Pass 1: 2 per-entity calls; Pass 2: groups of size 1 are skipped, so 0 joint calls.
        # (A single-formula group is trivially satisfiable; the meaningful check needs ≥2.)
        assert len(strategy.calls) == 2

    def test_two_entities_in_one_section_trigger_joint_call(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        findings = _Section(category="findings", body_span=(0, 20))
        e1 = _ent("PE", 3, formula=_ranked(2, "pe"))
        e2 = _ent("no PE", 7, formula=_ranked(-2, "pe"))
        doc = _Doc([e1, e2], sections=[findings])
        comp(doc)
        # Pass 1: 2 per-entity; Pass 2: 1 joint over both formulas.
        assert len(strategy.calls) == 3
        joint = strategy.calls[-1]
        assert len(joint) == 2

    def test_entities_outside_any_section_grouped_as_document(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        # Only one section, but two entities outside it
        section = _Section(category="findings", body_span=(0, 5))
        e_in = _ent("x", 2, formula=_ranked(2, "x"))
        e_out_a = _ent("y", 10, formula=_ranked(2, "y"))
        e_out_b = _ent("z", 12, formula=_ranked(-2, "z"))
        doc = _Doc([e_in, e_out_a, e_out_b], sections=[section])
        comp(doc)
        # Pass 1: 3 per-entity; Pass 2: 1 joint call over the <document> bucket
        # (the lone "findings" entity gives a size-1 group, skipped).
        joint_calls = strategy.calls[3:]
        assert len(joint_calls) == 1
        assert len(joint_calls[0]) == 2

    def test_nested_sections_innermost_wins(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        outer = _Section(category="history", body_span=(0, 20))
        inner = _Section(category="family_history", body_span=(5, 15))
        e_outer = _ent("a", 2, formula=_ranked(2, "a"))
        e_inner_1 = _ent("b", 7, formula=_ranked(2, "b"))
        e_inner_2 = _ent("c", 12, formula=_ranked(-2, "b"))
        doc = _Doc([e_outer, e_inner_1, e_inner_2], sections=[outer, inner])
        comp(doc)
        # e_outer alone in 'history' (size-1, skipped);
        # e_inner_1 and e_inner_2 together in 'family_history' (size-2, joint check fires).
        joint_calls = strategy.calls[3:]
        assert len(joint_calls) == 1
        assert len(joint_calls[0]) == 2


# ---------------------------------------------------------------------------
# Inconsistency reporting
# ---------------------------------------------------------------------------

class TestInconsistencyReporting:
    def test_contradiction_in_section_produces_inconsistency(self):
        strategy = _MockStrategy(return_consistent_for_atoms={"pe"})
        comp = ConsistencyCheckerComponent(strategy=strategy)
        findings = _Section(category="findings", body_span=(0, 20))
        e1 = _ent("PE", 3, formula=_ranked(2, "pe"))
        e2 = _ent("no PE", 7, formula=_ranked(-2, "pe"))
        doc = _Doc([e1, e2], sections=[findings])
        comp(doc)

        report = doc._.cwyde_inconsistencies
        assert report is not None and len(report) == 1
        inc: Inconsistency = report[0]
        assert inc.scope == "section"
        assert inc.scope_id == "findings"
        assert {e[0] for e in inc.entities} == {"PE", "no PE"}
        assert len(inc.formulas) == 2
        assert inc.explanation == "mock contradiction"

    def test_no_inconsistency_when_all_groups_consistent(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        findings = _Section(category="findings", body_span=(0, 20))
        e1 = _ent("PE", 3, formula=_ranked(2, "pe"))
        e2 = _ent("DVT", 7, formula=_ranked(2, "dvt"))
        doc = _Doc([e1, e2], sections=[findings])
        comp(doc)
        assert doc._.cwyde_inconsistencies == []

    def test_empty_doc_no_inconsistencies(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy)
        doc = _Doc([])
        comp(doc)
        assert doc._.cwyde_inconsistencies == []


# ---------------------------------------------------------------------------
# grouping="document"
# ---------------------------------------------------------------------------

class TestDocumentGrouping:
    def test_document_grouping_ignores_sections(self):
        """grouping='document' should put all formulas in a single joint call,
        even when sections exist."""
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy, grouping="document")
        findings = _Section(category="findings", body_span=(0, 10))
        impression = _Section(category="impression", body_span=(10, 20))
        e_find = _ent("PE", 3, formula=_ranked(2, "pe"))
        e_imp = _ent("no PE", 13, formula=_ranked(-2, "pe"))
        doc = _Doc([e_find, e_imp], sections=[findings, impression])
        comp(doc)
        # Pass 1: 2 per-entity; Pass 2: 1 joint over both formulas (single 'document' group).
        joint_calls = strategy.calls[2:]
        assert len(joint_calls) == 1
        assert len(joint_calls[0]) == 2

    def test_document_grouping_with_no_sections(self):
        strategy = _MockStrategy()
        comp = ConsistencyCheckerComponent(strategy=strategy, grouping="document")
        e1 = _ent("PE", 3, formula=_ranked(2, "pe"))
        e2 = _ent("no PE", 7, formula=_ranked(-2, "pe"))
        doc = _Doc([e1, e2], sections=None)
        comp(doc)
        joint_calls = strategy.calls[2:]
        assert len(joint_calls) == 1
        assert len(joint_calls[0]) == 2


# ---------------------------------------------------------------------------
# HISTORICAL semantics (Past wrapping → consistent with current negation)
# ---------------------------------------------------------------------------

class TestHistoricalDoesNotContradict:
    """HISTORICAL(X) wraps the atom in Past, so it should NOT clash with a
    current DEFINITE_NEGATED_EXISTENCE(X). The component itself doesn't
    enforce this — gamen-hs does — but we verify the formulas reaching the
    strategy are structurally different and would be distinguishable by a
    Past-aware reasoner."""

    def test_historical_and_current_negation_use_distinct_inner_formulas(self):
        from cwyde.formal.translator import category_to_formula

        historical = category_to_formula(AssertionCategory.HISTORICAL, "hypertension")
        negated = category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "hypertension")

        # The atom is the same ('hypertension'), but the historical formula
        # wraps it in Past, so the joint conjunction is structurally
        # B(P(hypertension)) ∧ RankedBelief(-2, hypertension) — not a syntactic
        # contradiction. Verifying this here protects against a translator
        # regression that would silently make the joint check over-report.
        from cwyde.formal.modal import Past, Belief, RankedBelief
        assert isinstance(historical, Belief)
        assert isinstance(historical.operand, Past)
        assert isinstance(negated, RankedBelief)
        assert negated.rank == -2
