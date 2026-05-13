"""
Unit tests for cwyde.formal.canonical.canonicalise_atom (Issue #11).

Covers level-1 (lowercase + whitespace) on strings and on Span-like inputs,
plus the level-2 (lemma) opt-in path.
"""

from __future__ import annotations

from dataclasses import dataclass

from cwyde.formal.canonical import canonicalise_atom


# ---------------------------------------------------------------------------
# Mock Span and Token
# ---------------------------------------------------------------------------

@dataclass
class _MockTok:
    text: str
    lemma_: str = ""


class _MockSpan:
    """Iterable like spacy.tokens.Span — yields _MockTok per token."""

    def __init__(self, text: str, tokens=None):
        self.text = text
        self._tokens = tokens or [_MockTok(text=text)]

    def __iter__(self):
        return iter(self._tokens)


# ---------------------------------------------------------------------------
# Level 1 — string input
# ---------------------------------------------------------------------------

class TestStringInput:
    def test_lowercases(self):
        assert canonicalise_atom("Pulmonary Embolism") == "pulmonary_embolism"

    def test_already_lowercase_unchanged(self):
        assert canonicalise_atom("pulmonary embolism") == "pulmonary_embolism"

    def test_uppercase_lowered(self):
        assert canonicalise_atom("PULMONARY EMBOLISM") == "pulmonary_embolism"

    def test_collapses_internal_whitespace_runs(self):
        assert canonicalise_atom("pulmonary  \t embolism") == "pulmonary_embolism"

    def test_strips_leading_and_trailing_whitespace(self):
        assert canonicalise_atom("  PE  ") == "pe"

    def test_lemmatize_flag_silently_ignored_for_strings(self):
        # Strings carry no lemma info; the flag has no effect.
        assert canonicalise_atom("PE", lemmatize=True) == "pe"

    def test_empty_string(self):
        assert canonicalise_atom("") == ""

    def test_single_word(self):
        assert canonicalise_atom("PE") == "pe"

    def test_newlines_treated_as_whitespace(self):
        assert canonicalise_atom("filling\ndefect") == "filling_defect"


# ---------------------------------------------------------------------------
# Level 1 — Span input (lemmatize=False or no lemma available)
# ---------------------------------------------------------------------------

class TestSpanInputLevel1:
    def test_span_text_canonicalised_when_lemmatize_false(self):
        span = _MockSpan("Pulmonary Embolism", [
            _MockTok(text="Pulmonary", lemma_="pulmonary"),
            _MockTok(text="Embolism",  lemma_="embolism"),
        ])
        assert canonicalise_atom(span) == "pulmonary_embolism"

    def test_lemmatize_true_uses_lemma_when_available(self):
        span = _MockSpan("filling defects", [
            _MockTok(text="filling", lemma_="filling"),
            _MockTok(text="defects", lemma_="defect"),
        ])
        # With lemma: "filling defect"; without: "filling defects"
        assert canonicalise_atom(span, lemmatize=True) == "filling_defect"
        assert canonicalise_atom(span, lemmatize=False) == "filling_defects"

    def test_lemmatize_true_falls_back_to_text_when_lemmas_missing(self):
        span = _MockSpan("PULMONARY EMBOLISM", [
            _MockTok(text="PULMONARY", lemma_=""),
            _MockTok(text="EMBOLISM",  lemma_=""),
        ])
        # All lemmas empty → fallback uses tok.text; result is same as level-1 on span.text.
        assert canonicalise_atom(span, lemmatize=True) == "pulmonary_embolism"


# ---------------------------------------------------------------------------
# Surface-form unification — the core motivating property
# ---------------------------------------------------------------------------

class TestSurfaceFormUnification:
    """The translator's joint check fails when surface variants produce
    distinct atoms. Canonicalisation must unify common variants into one
    atom name."""

    def test_casing_variants_unify(self):
        a = canonicalise_atom("Pulmonary Embolism")
        b = canonicalise_atom("pulmonary embolism")
        c = canonicalise_atom("PULMONARY EMBOLISM")
        assert a == b == c

    def test_whitespace_variants_unify(self):
        a = canonicalise_atom("pulmonary embolism")
        b = canonicalise_atom("pulmonary  embolism")
        c = canonicalise_atom("\tpulmonary\tembolism\n")
        assert a == b == c

    def test_distinct_lexical_items_stay_distinct(self):
        """Level 1 does NOT unify clinically-related-but-lexically-distinct
        items — that is a concept-normalisation concern (level 3, out of scope)."""
        assert canonicalise_atom("pulmonary embolism") != canonicalise_atom("filling defect")
        assert canonicalise_atom("PE") != canonicalise_atom("pulmonary embolism")
