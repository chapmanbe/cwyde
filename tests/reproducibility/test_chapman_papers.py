"""
Reproducibility tests against Chapman 2011 and Harkema 2009 example sentences.

These are SOFT tests — they run as annotation-quality reports. Individual cases
may fail without failing the overall test suite, because:
  1. The original ConText papers had imperfect recall on their own examples.
  2. cwyde distinguishes DEFINITE vs PROBABLE (the papers used binary categories).
  3. Some cases require document-level context that sentence-level processing can't use.

The test produces a per-file report and asserts ≥80% agreement on the existence axis.
Use --report-only to print the report without assertions (useful for notebooks/CI).

Run:
    pytest tests/reproducibility/ -v               # soft: fails if <80% agreement
    pytest tests/reproducibility/ -v --report-only  # always passes, prints report
"""

from pathlib import Path
import textwrap
import pytest
import medspacy
from medspacy.target_matcher import TargetRule

from cwyde.pipeline import add_to
from cwyde.categories import AssertionCategory
from cwyde.kb import load_repro_cases

REPRO_DIR = Path(__file__).parent


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--report-only",
            action="store_true",
            default=False,
            help="Print reproducibility report without asserting agreement threshold",
        )
    except ValueError:
        pass  # already registered by another conftest


# ---------------------------------------------------------------------------
# Session-scoped pipeline — shared across both YAML files
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def repro_nlp():
    pipeline = medspacy.load()
    pipeline.add_pipe("medspacy_sectionizer")
    tm = pipeline.get_pipe("medspacy_target_matcher")
    for literal in ["PE", "DVT", "pulmonary embolism", "pneumonia",
                    "right heart strain", "chest pain"]:
        tm.add([TargetRule(literal, "CONDITION")])
    add_to(pipeline, lang="en")
    return pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_case(nlp, text: str, target: str):
    """Return the cwyde assertion category for `target` in `text`, or None."""
    doc = nlp(text)
    for ent in doc.ents:
        if ent.text.lower() == target.lower():
            return ent._.cwyde_assertion_category
    return None


def _existence_axis(cat: AssertionCategory) -> str:
    """Collapse to existence axis: positive / negative / uncertain / other."""
    if cat in (AssertionCategory.DEFINITE_EXISTENCE, AssertionCategory.PROBABLE_EXISTENCE,
               AssertionCategory.INDICATION):
        return "positive"
    if cat in (AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
               AssertionCategory.PROBABLE_NEGATED_EXISTENCE):
        return "negative"
    if cat == AssertionCategory.AMBIVALENT_EXISTENCE:
        return "uncertain"
    return "other"   # HISTORICAL, HYPOTHETICAL, FAMILY, UNRESOLVED


def _report(title: str, cases, results: list[tuple]) -> tuple[int, int]:
    """Print a formatted report; return (passed, total)."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    passed = 0
    for case, (got, axis_match) in zip(cases, results):
        exact = got == case.expected_category
        status = "PASS" if exact else ("AXIS" if axis_match else "FAIL")
        if exact:
            passed += 1
        mark = "✓" if exact else ("~" if axis_match else "✗")
        print(f"  [{mark}] {status:4s}  expected={case.expected_category.value}")
        print(f"           got={got.value if got else 'NO_ENTITY'}")
        print(f"           {textwrap.shorten(case.text, 70)}")
        if case.note and not exact:
            note = textwrap.shorten(case.note.strip(), 70)
            print(f"           note: {note}")
    print(f"\n  Exact match: {passed}/{len(cases)}")
    axis_passed = sum(1 for _, (_, am) in zip(cases, results) if am)
    print(f"  Axis  match: {axis_passed}/{len(cases)}")
    return passed, len(cases)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestChapman2011:
    def test_report(self, repro_nlp, request):
        path = REPRO_DIR / "chapman_2011_examples.yaml"
        cf = load_repro_cases(path)
        results = []
        for case in cf.cases:
            got = _run_case(repro_nlp, case.text, case.target)
            if got is None:
                got = AssertionCategory.DEFINITE_EXISTENCE  # no-entity default
            axis_match = _existence_axis(got) == _existence_axis(case.expected_category)
            results.append((got, axis_match))

        passed, total = _report("Chapman 2011 — CTPA reports", cf.cases, results)
        agreement = passed / total

        report_only = request.config.getoption("--report-only", default=False)
        if not report_only:
            assert agreement >= 0.75, (
                f"Chapman 2011 agreement {agreement:.0%} below 75% threshold "
                f"({passed}/{total} cases)"
            )


class TestHarkema2009:
    def test_report(self, repro_nlp, request):
        path = REPRO_DIR / "harkema_2009_examples.yaml"
        cf = load_repro_cases(path)
        results = []
        for case in cf.cases:
            got = _run_case(repro_nlp, case.text, case.target)
            if got is None:
                got = AssertionCategory.DEFINITE_EXISTENCE
            axis_match = _existence_axis(got) == _existence_axis(case.expected_category)
            results.append((got, axis_match))

        passed, total = _report("Harkema 2009 — ConText algorithm", cf.cases, results)
        agreement = passed / total

        report_only = request.config.getoption("--report-only", default=False)
        if not report_only:
            assert agreement >= 0.75, (
                f"Harkema 2009 agreement {agreement:.0%} below 75% threshold "
                f"({passed}/{total} cases)"
            )
