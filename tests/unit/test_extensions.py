"""Unit tests for cwyde spaCy extension attribute registration."""

import spacy
from cwyde.extensions import register_extensions


def test_span_belief_agent_registered():
    register_extensions()
    from spacy.tokens import Span
    assert Span.has_extension("cwyde_belief_agent")


def test_doc_author_registered():
    register_extensions()
    from spacy.tokens import Doc
    assert Doc.has_extension("cwyde_author")


def test_doc_authored_at_registered():
    register_extensions()
    from spacy.tokens import Doc
    assert Doc.has_extension("cwyde_authored_at")


def test_span_belief_agent_default():
    register_extensions()
    nlp = spacy.blank("en")
    doc = nlp("test")
    # Need at least one token span to check the default
    span = doc[0:1]
    assert span._.cwyde_belief_agent == "clinician"


def test_doc_author_default_none():
    register_extensions()
    nlp = spacy.blank("en")
    doc = nlp("test")
    assert doc._.cwyde_author is None


def test_doc_authored_at_default_none():
    register_extensions()
    nlp = spacy.blank("en")
    doc = nlp("test")
    assert doc._.cwyde_authored_at is None
