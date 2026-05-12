"""Unit tests for the NUBes cue extraction script (no corpus required)."""

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from extract_nubes_cues import parse_ann, extract_cues_from_ann, infer_direction, aggregate


# ---------------------------------------------------------------------------
# Minimal BRAT fixture
# ---------------------------------------------------------------------------

SAMPLE_ANN = textwrap.dedent("""\
    T1\tNEG_CUE 3 5\tno
    T2\tNEG_SCOPE 3 35\tno evidencia de neumonia
    R1\tHas_scope Arg1:T1 Arg2:T2
    T3\tSPEC_CUE 40 48\tprobable
    T4\tSPEC_SCOPE 40 65\tprobable efusion pleural
    R2\tHas_scope Arg1:T3 Arg2:T4
    T5\tNEG_CUE 70 73\tsin
    T6\tNEG_SCOPE 70 90\tsin fiebre ni tos
    R3\tCue_scope Arg1:T5 Arg2:T6
""")


@pytest.fixture
def parsed(tmp_path):
    ann = tmp_path / "doc.ann"
    ann.write_text(SAMPLE_ANN, encoding="utf-8")
    return parse_ann(ann)


def test_parse_ann_span_count(parsed):
    spans, rels = parsed
    assert len(spans) == 6
    assert len(rels) == 3


def test_parse_ann_neg_cue_text(parsed):
    spans, _ = parsed
    cues = {s["text"] for s in spans.values() if s["type"] == "NEG_CUE"}
    assert "no" in cues
    assert "sin" in cues


def test_extract_cues_returns_records(parsed):
    spans, rels = parsed
    records = extract_cues_from_ann(spans, rels)
    assert len(records) == 3  # two NEG_CUE, one SPEC_CUE


def test_extract_cues_neg_forward(parsed):
    spans, rels = parsed
    records = extract_cues_from_ann(spans, rels)
    no_rec = next(r for r in records if r["surface"] == "no")
    assert no_rec["cue_type"] == "NEG_CUE"
    # "no" starts at 3, scope starts at 3 — rel_pos should be ~0 (forward)
    assert no_rec["rel_pos"] is not None
    assert no_rec["rel_pos"] < 0.2


def test_extract_cues_spec_forward(parsed):
    spans, rels = parsed
    records = extract_cues_from_ann(spans, rels)
    spec_rec = next(r for r in records if r["surface"] == "probable")
    assert spec_rec["cue_type"] == "SPEC_CUE"
    assert spec_rec["rel_pos"] is not None
    assert spec_rec["rel_pos"] < 0.2


def test_infer_direction_forward():
    assert infer_direction([0.05, 0.10, 0.08]) == "forward"


def test_infer_direction_backward():
    assert infer_direction([0.92, 0.88, 0.95]) == "backward"


def test_infer_direction_bidirectional():
    assert infer_direction([0.1, 0.9, 0.5]) == "bidirectional"


def test_infer_direction_no_scope():
    assert infer_direction([None, None]) == "forward"


def test_aggregate_min_freq(parsed):
    spans, rels = parsed
    records = extract_cues_from_ann(spans, rels)
    # All cues appear once — min_freq=2 should drop everything
    result = aggregate(records, min_freq=2)
    assert result == {}


def test_aggregate_keeps_above_min_freq():
    records = [
        {"surface": "no", "cue_type": "NEG_CUE", "rel_pos": 0.05},
        {"surface": "no", "cue_type": "NEG_CUE", "rel_pos": 0.08},
        {"surface": "no", "cue_type": "NEG_CUE", "rel_pos": 0.06},
        {"surface": "sin", "cue_type": "NEG_CUE", "rel_pos": 0.10},
    ]
    result = aggregate(records, min_freq=3)
    assert "no" in result
    assert "sin" not in result
    assert result["no"]["direction"] == "forward"
    assert result["no"]["count"] == 3


def test_aggregate_needs_review_flag():
    records = [
        {"surface": "posible", "cue_type": "SPEC_CUE", "rel_pos": 0.1},
        {"surface": "posible", "cue_type": "SPEC_CUE", "rel_pos": 0.9},
        {"surface": "posible", "cue_type": "SPEC_CUE", "rel_pos": 0.5},
    ]
    result = aggregate(records, min_freq=2)
    assert result["posible"]["needs_review"] is True
    assert result["posible"]["direction"] == "bidirectional"


def test_leakage_guard(tmp_path):
    """Script should exit non-zero if train and test folds overlap."""
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "scripts/extract_nubes_cues.py",
         str(tmp_path), "--train", "0", "1", "--test", "1", "2"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parents[2])
    )
    assert result.returncode != 0
    assert "overlap" in result.stderr
