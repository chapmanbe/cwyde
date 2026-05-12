"""Unit tests for modal formula dataclasses."""

from cwyde.formal.modal import (
    Atom, Not, And, Box, Diamond, Past, Indication, Belief, RankedBelief
)


def test_atom_round_trip():
    a = Atom("pe")
    tree = a.to_tree_json()
    assert tree == {"type": "atom", "name": "pe"}
    flat = a.to_flat_extraction()
    assert flat == {"op": "atom", "atom": "pe"}


def test_box_tree():
    f = Box(Atom("pe"))
    assert f.to_tree_json() == {"type": "box", "operand": {"type": "atom", "name": "pe"}}


def test_diamond_tree():
    f = Diamond(Atom("pe"))
    assert f.to_tree_json() == {"type": "diamond", "operand": {"type": "atom", "name": "pe"}}


def test_definite_negated_encoding():
    # □¬X
    f = Box(Not(Atom("pe")))
    tree = f.to_tree_json()
    assert tree["type"] == "box"
    assert tree["operand"]["type"] == "not"


def test_indication_encoding():
    # ?(X) = ¬K_a(X) ∧ ¬K_a(¬X)
    f = Indication(Atom("pe"))
    tree = f.to_tree_json()
    assert tree["type"] == "and"
    assert tree["left"]["type"] == "not"
    assert tree["right"]["type"] == "not"
    # Both sides should be negations of knowledge
    assert tree["left"]["operand"]["type"] == "knowledge"
    assert tree["right"]["operand"]["type"] == "knowledge"
    # One knows X, one knows ¬X
    right_inner = tree["right"]["operand"]["operand"]
    assert right_inner["type"] == "not"


def test_past_tree():
    f = Past(Atom("pe"))
    assert f.to_tree_json() == {"type": "past_diamond", "operand": {"type": "atom", "name": "pe"}}


def test_and_tree():
    f = And(Diamond(Atom("x")), Diamond(Not(Atom("x"))))
    tree = f.to_tree_json()
    assert tree["type"] == "and"
    assert tree["left"]["type"] == "diamond"
    assert tree["right"]["type"] == "diamond"


def test_belief_tree():
    f = Belief("clinician", Atom("pe"))
    tree = f.to_tree_json()
    assert tree == {"type": "belief", "agent": "clinician", "operand": {"type": "atom", "name": "pe"}}


def test_belief_flat():
    f = Belief("clinician", Atom("pe"))
    flat = f.to_flat_extraction()
    assert flat == {"op": "believes", "agent": "clinician", "operand": {"op": "atom", "atom": "pe"}}


def test_belief_wraps_not():
    # B_a(¬X) — belief in negation (DEFINITE_NEGATED_EXISTENCE encoding)
    f = Belief("clinician", Not(Atom("pe")))
    tree = f.to_tree_json()
    assert tree["type"] == "belief"
    assert tree["agent"] == "clinician"
    assert tree["operand"]["type"] == "not"


def test_belief_wraps_past():
    # B_a(P(X)) — HISTORICAL encoding
    f = Belief("clinician", Past(Atom("pe")))
    tree = f.to_tree_json()
    assert tree["type"] == "belief"
    assert tree["operand"]["type"] == "past_diamond"


def test_ranked_belief_positive_tree():
    # τ=2: DEFINITE_EXISTENCE encoding
    f = RankedBelief("clinician", 2, Atom("pe"))
    tree = f.to_tree_json()
    assert tree == {
        "type": "ranked_belief",
        "agent": "clinician",
        "rank": 2,
        "operand": {"type": "atom", "name": "pe"},
    }


def test_ranked_belief_negative_tree():
    # τ=-2: DEFINITE_NEGATED_EXISTENCE encoding
    f = RankedBelief("clinician", -2, Atom("pe"))
    tree = f.to_tree_json()
    assert tree["type"] == "ranked_belief"
    assert tree["rank"] == -2
    assert tree["agent"] == "clinician"


def test_ranked_belief_zero_tree():
    # τ=0: AMBIVALENT_EXISTENCE — explicit neutrality
    f = RankedBelief("clinician", 0, Atom("pe"))
    tree = f.to_tree_json()
    assert tree["type"] == "ranked_belief"
    assert tree["rank"] == 0


def test_ranked_belief_flat():
    f = RankedBelief("clinician", 1, Atom("pe"))
    flat = f.to_flat_extraction()
    assert flat == {
        "op": "ranked_belief",
        "agent": "clinician",
        "rank": 1,
        "operand": {"op": "atom", "atom": "pe"},
    }
