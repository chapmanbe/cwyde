"""Unit tests for the RadGraph-XL evaluation script (no corpus required)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from evaluate_radgraph_xl import (
    parse_assertion_status,
    reconstruct_text,
    token_span_to_char_span,
    load_gold_entities,
    compute_f1,
    LABEL_TO_CWYDE,
    CWYDE_TO_RADGRAPH,
)
from cwyde.categories import AssertionCategory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RECORD = {
    "dataset": "mimic-chest-xr",
    "doc_key": 0,
    "sentences": [
        ["No", "evidence", "of", "pneumothorax", "."],
        ["Probable", "pleural", "effusion", "noted", "."],
    ],
    "ner": [
        [[3, 3, "Observation::definitely absent"]],   # "pneumothorax" → absent
        [[1, 2, "Observation::uncertain"]],            # "pleural effusion" → uncertain
    ],
    "relations": [[], []],
}


# ---------------------------------------------------------------------------
# Label parsing
# ---------------------------------------------------------------------------

def test_parse_assertion_status_with_type():
    assert parse_assertion_status("Observation::definitely present") == "definitely present"
    assert parse_assertion_status("Anatomy::definitely absent") == "definitely absent"
    assert parse_assertion_status("Observation::uncertain") == "uncertain"


def test_parse_assertion_status_bare():
    assert parse_assertion_status("uncertain") == "uncertain"


# ---------------------------------------------------------------------------
# Text reconstruction
# ---------------------------------------------------------------------------

def test_reconstruct_text_structure():
    text, offsets = reconstruct_text(SAMPLE_RECORD["sentences"])
    assert "pneumothorax" in text
    assert "pleural effusion" in text
    assert len(offsets) == 2
    assert offsets[0] == 0


def test_reconstruct_text_sentence_boundary():
    text, offsets = reconstruct_text(SAMPLE_RECORD["sentences"])
    sent0 = " ".join(SAMPLE_RECORD["sentences"][0])
    assert text[offsets[0]:offsets[0] + len(sent0)] == sent0


# ---------------------------------------------------------------------------
# Token → char span
# ---------------------------------------------------------------------------

def test_token_span_to_char_span_single_token():
    sents = [["No", "evidence", "of", "pneumothorax", "."]]
    _, offsets = reconstruct_text(sents)
    cs, ce = token_span_to_char_span(sents, offsets, 0, 3, 3)
    text, _ = reconstruct_text(sents)
    assert text[cs:ce] == "pneumothorax"


def test_token_span_to_char_span_multi_token():
    sents = [["Probable", "pleural", "effusion", "noted", "."]]
    _, offsets = reconstruct_text(sents)
    cs, ce = token_span_to_char_span(sents, offsets, 0, 1, 2)
    text, _ = reconstruct_text(sents)
    assert text[cs:ce] == "pleural effusion"


# ---------------------------------------------------------------------------
# Gold entity loading
# ---------------------------------------------------------------------------

def test_load_gold_entities_count():
    text, entities = load_gold_entities(SAMPLE_RECORD)
    assert len(entities) == 2


def test_load_gold_entities_labels():
    text, entities = load_gold_entities(SAMPLE_RECORD)
    statuses = {e["assertion_status"] for e in entities}
    assert "definitely absent" in statuses
    assert "uncertain" in statuses


def test_load_gold_entities_text_recovery():
    text, entities = load_gold_entities(SAMPLE_RECORD)
    entity_texts = {e["text"] for e in entities}
    assert "pneumothorax" in entity_texts
    assert "pleural effusion" in entity_texts


# ---------------------------------------------------------------------------
# Label mappings
# ---------------------------------------------------------------------------

def test_all_radgraph_labels_mapped():
    for label in ["definitely present", "definitely absent", "uncertain"]:
        assert label in LABEL_TO_CWYDE


def test_all_cwyde_categories_mapped():
    for cat in AssertionCategory:
        if cat == AssertionCategory.UNRESOLVED:
            continue
        assert cat in CWYDE_TO_RADGRAPH, f"{cat} missing from CWYDE_TO_RADGRAPH"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_compute_f1_perfect():
    results = [
        {"gold": "definitely present", "predicted": "definitely present"},
        {"gold": "definitely absent",  "predicted": "definitely absent"},
        {"gold": "uncertain",          "predicted": "uncertain"},
    ]
    m = compute_f1(results)
    assert m["micro"]["f1"] == pytest.approx(1.0)
    assert m["macro"]["f1"] == pytest.approx(1.0)


def test_compute_f1_all_wrong():
    results = [
        {"gold": "definitely present", "predicted": "definitely absent"},
        {"gold": "definitely absent",  "predicted": "uncertain"},
    ]
    m = compute_f1(results)
    assert m["micro"]["f1"] == pytest.approx(0.0)


def test_compute_f1_partial():
    results = [
        {"gold": "definitely present", "predicted": "definitely present"},
        {"gold": "definitely present", "predicted": "definitely absent"},
        {"gold": "definitely absent",  "predicted": "definitely absent"},
    ]
    m = compute_f1(results)
    assert 0.0 < m["micro"]["f1"] < 1.0
    assert m["micro"]["f1"] == pytest.approx(2 / 3)


def test_compute_f1_class_support():
    results = [
        {"gold": "definitely present", "predicted": "definitely present"},
        {"gold": "definitely present", "predicted": "definitely present"},
        {"gold": "definitely absent",  "predicted": "definitely absent"},
    ]
    m = compute_f1(results)
    assert m["definitely present"]["support"] == 2
    assert m["definitely absent"]["support"] == 1
    assert m["uncertain"]["support"] == 0
