"""
Atom-name canonicalisation at the modal-translator boundary.

The translator emits `ModalFormula` atoms keyed by entity text. Without
canonicalisation, surface-form variation ("Pulmonary Embolism" /
"pulmonary embolism" / "PE") produces distinct atoms in gamen-hs, which
breaks joint consistency over what is clinically the same concept.

This module canonicalises atom names so surface-form variants unify into
one atom. Levels:

  Level 1 (default): lowercase + whitespace → single underscore.
  Level 2 (opt-in):  spaCy token lemmas joined under level 1. Requires a
                     Span input with lemma_ populated.
  Level 3:           concept-level normalisation (UMLS / CUI). Out of
                     scope — applications layer their own canonicaliser
                     on top of this module if they need it.

Issue #11.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from spacy.tokens import Span

_WHITESPACE = re.compile(r"\s+")


def canonicalise_atom(span_or_text: Union["Span", str], *, lemmatize: bool = False) -> str:
    """Return a canonical atom name for an entity span or raw text.

    Level 1 normalisation is always applied. Level 2 (lemma) is applied only
    when `lemmatize=True` AND the input is a Span with usable token lemmas.
    Strings cannot be lemmatised, so the flag is silently ignored on str input.
    """
    if isinstance(span_or_text, str):
        return _normalise(span_or_text)

    span = span_or_text
    if lemmatize:
        lemma_text = _lemma_text(span)
        if lemma_text is not None:
            return _normalise(lemma_text)
    return _normalise(span.text)


def _normalise(text: str) -> str:
    return _WHITESPACE.sub("_", text.strip().lower())


def _lemma_text(span) -> str | None:
    """Return space-joined token lemmas for the span, or None if unavailable.

    Falls back to None when any token lacks a lemma_ attribute or the joined
    result would be empty; callers then drop to surface-form canonicalisation.
    """
    try:
        parts = [tok.lemma_ if tok.lemma_ else tok.text for tok in span]
    except (AttributeError, TypeError):
        return None
    joined = " ".join(p for p in parts if p)
    return joined or None
