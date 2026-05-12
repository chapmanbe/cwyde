"""
Modal formula dataclass tree mirroring gamen-hs's 26-constructor JSON format.

Implements the constructors needed for clinical assertion categories.
Stubbed constructors raise NotImplementedError to fail loudly rather than silently.

gamen-hs tree format reference: ~/Code/Haskell/gamen-hs/validate/Main.hs
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class ModalFormula:
    def to_tree_json(self) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} does not implement to_tree_json")

    def to_flat_extraction(self) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} does not implement to_flat_extraction")


@dataclass
class Atom(ModalFormula):
    name: str

    def to_tree_json(self):
        return {"type": "atom", "name": self.name}

    def to_flat_extraction(self):
        return {"op": "atom", "atom": self.name}


@dataclass
class Not(ModalFormula):
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "not", "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "not", "operand": self.operand.to_flat_extraction()}


@dataclass
class And(ModalFormula):
    left: ModalFormula
    right: ModalFormula

    def to_tree_json(self):
        return {"type": "and", "left": self.left.to_tree_json(), "right": self.right.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "and", "left": self.left.to_flat_extraction(), "right": self.right.to_flat_extraction()}


@dataclass
class Or(ModalFormula):
    left: ModalFormula
    right: ModalFormula

    def to_tree_json(self):
        return {"type": "or", "left": self.left.to_tree_json(), "right": self.right.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "or", "left": self.left.to_flat_extraction(), "right": self.right.to_flat_extraction()}


@dataclass
class Implies(ModalFormula):
    antecedent: ModalFormula
    consequent: ModalFormula

    def to_tree_json(self):
        return {"type": "implies", "antecedent": self.antecedent.to_tree_json(),
                "consequent": self.consequent.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "implies", "antecedent": self.antecedent.to_flat_extraction(),
                "consequent": self.consequent.to_flat_extraction()}


@dataclass
class Box(ModalFormula):
    """Necessity: □φ — necessarily the case."""
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "box", "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "box", "operand": self.operand.to_flat_extraction()}


@dataclass
class Diamond(ModalFormula):
    """Possibility: ◇φ — possibly the case."""
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "diamond", "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "diamond", "operand": self.operand.to_flat_extraction()}


@dataclass
class Past(ModalFormula):
    """P(φ) — was the case at some past time (existential past / PastDiamond in gamen-hs)."""
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "past_diamond", "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "past_diamond", "operand": self.operand.to_flat_extraction()}


@dataclass
class FutureBox(ModalFormula):
    """[F]φ — will necessarily be the case."""
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "future_box", "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "future_box", "operand": self.operand.to_flat_extraction()}


@dataclass
class FutureDiamond(ModalFormula):
    """<F>φ — might be the case in the future."""
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "future_diamond", "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "future_diamond", "operand": self.operand.to_flat_extraction()}


@dataclass
class Knowledge(ModalFormula):
    """K_a(φ) — agent a knows φ (epistemic operator)."""
    agent: str
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "knowledge", "agent": self.agent, "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "knows", "agent": self.agent, "operand": self.operand.to_flat_extraction()}


@dataclass
class Belief(ModalFormula):
    """B_a(φ) — agent a believes φ. Non-factive (KD45); B_a(φ) does not entail φ."""
    agent: str
    operand: ModalFormula

    def to_tree_json(self):
        return {"type": "belief", "agent": self.agent, "operand": self.operand.to_tree_json()}

    def to_flat_extraction(self):
        return {"op": "believes", "agent": self.agent, "operand": self.operand.to_flat_extraction()}


@dataclass
class RankedBelief(ModalFormula):
    """τ_a(φ) = n — agent a's doxastic rank for φ (Spohn 1988 OCF, signed-int encoding).

    n > 0: belief in φ at firmness n.
    n < 0: disbelief in φ at firmness |n| (equivalently, belief in ¬φ at firmness |n|).
    n = 0: explicit neutrality — neither φ nor ¬φ is disbelieved.

    Spohn's Theorem 2(a) is built in: the signed int encodes one side of the κ pair,
    so no separate closure rule is needed.
    """
    agent: str
    rank: int
    operand: ModalFormula

    def to_tree_json(self):
        return {
            "type": "ranked_belief",
            "agent": self.agent,
            "rank": self.rank,
            "operand": self.operand.to_tree_json(),
        }

    def to_flat_extraction(self):
        return {
            "op": "ranked_belief",
            "agent": self.agent,
            "rank": self.rank,
            "operand": self.operand.to_flat_extraction(),
        }


@dataclass
class Indication(ModalFormula):
    """?(φ) — under investigation; clinician is seeking to determine whether φ.

    Custom operator not in base B&D — encodes the INDICATION modifier category.
    Encoded as ¬K_a(φ) ∧ ¬K_a(¬φ) in tree form for gamen-hs compatibility.
    """
    operand: ModalFormula
    agent: str = "clinician"

    def to_tree_json(self):
        inner = self.operand.to_tree_json()
        return {
            "type": "and",
            "left": {"type": "not", "operand": {"type": "knowledge", "agent": self.agent, "operand": inner}},
            "right": {"type": "not", "operand": {"type": "knowledge", "agent": self.agent,
                       "operand": {"type": "not", "operand": inner}}},
        }

    def to_flat_extraction(self):
        inner = self.operand.to_flat_extraction()
        return {"op": "indication", "agent": self.agent, "operand": inner}
