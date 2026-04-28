"""Unit tests for modal formula dataclasses."""

import pytest
from cwyde.formal.modal import (
    Atom, Not, And, Or, Box, Diamond, Past, Indication, Knowledge
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
    assert f.to_tree_json() == {"type": "past", "operand": {"type": "atom", "name": "pe"}}


def test_and_tree():
    f = And(Diamond(Atom("x")), Diamond(Not(Atom("x"))))
    tree = f.to_tree_json()
    assert tree["type"] == "and"
    assert tree["left"]["type"] == "diamond"
    assert tree["right"]["type"] == "diamond"
