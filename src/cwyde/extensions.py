"""
spaCy Span and Doc extension registration for cwyde.

All attributes are prefixed cwyde_ to coexist with medspaCy's is_negated, etc.
Call register_extensions() before adding cwyde components to a pipeline.
"""

from __future__ import annotations

from spacy.tokens import Span, Doc

from cwyde.categories import AssertionCategory


def register_extensions() -> None:
    """Idempotent — safe to call multiple times."""
    simple_span_attrs = [
        ("cwyde_assertion_category", AssertionCategory.DEFINITE_EXISTENCE),
        ("cwyde_modal_formula", None),
        ("cwyde_is_indication", False),
        ("cwyde_is_historical", False),
        ("cwyde_is_hypothetical", False),
        ("cwyde_is_family", False),
        ("cwyde_section_inherited", False),
        ("cwyde_consistent", None),
    ]

    for attr, default in simple_span_attrs:
        if not Span.has_extension(attr):
            Span.set_extension(attr, default=default)

    # Use a factory for cwyde_resolution_trace to avoid shared mutable default
    if not Span.has_extension("cwyde_resolution_trace"):
        Span.set_extension("cwyde_resolution_trace", default=None)

    doc_attrs = [
        ("cwyde_section_assertions", None),
        ("cwyde_inconsistencies", None),
    ]

    for attr, default in doc_attrs:
        if not Doc.has_extension(attr):
            Doc.set_extension(attr, default=default)
