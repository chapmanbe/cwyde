# Doxastic Semantics in cwyde (v0.3)

cwyde's assertion taxonomy is grounded in **doxastic modal logic** — the logic of belief states. Each `AssertionCategory` has a precise doxastic reading; findings that require formal reasoning are translated to `ModalFormula` trees and submitted to [gamen-hs](~/Code/Haskell/gamen-hs) for consistency checking.

The v0.1 encoding used alethic operators (□/◇). That was a category mistake: clinical assertion categories are claims about the *author's belief state*, not metaphysical necessity. See `docs/doxastic-foundations.md` for the full argument.

v0.2 introduced `Belief(agent, operand)` but collapsed DEFINITE and PROBABLE into the same formula. v0.3 encodes the full graded scale using Spohn's (1988) ordinal conditional functions (OCFs), implemented in gamen-hs as `RankedBelief`.

---

## Category → Doxastic Reading

The five existence-axis categories form an ordered scale of the clinician's graded belief in the finding. The grade is encoded in the signed rank integer τ:

| Category | Formula | τ | Reading |
|---|---|---|---|
| `DEFINITE_EXISTENCE` | τ_clinician(X) = 2 | +2 | _Clinician firmly believes X is present_ |
| `PROBABLE_EXISTENCE` | τ_clinician(X) = 1 | +1 | _Clinician tentatively believes X is present_ |
| `AMBIVALENT_EXISTENCE` | τ_clinician(X) = 0 | 0 | _Clinician is genuinely neutral — neither X nor ¬X is disbelieved_ |
| `PROBABLE_NEGATED_EXISTENCE` | τ_clinician(X) = -1 | -1 | _Clinician tentatively disbelieves X (believes ¬X at firmness 1)_ |
| `DEFINITE_NEGATED_EXISTENCE` | τ_clinician(X) = -2 | -2 | _Clinician firmly disbelieves X (believes ¬X at firmness 2)_ |

The signed-int encoding builds in Spohn's Theorem 2(a): κ(X) = 0 ∨ κ(¬X) = 0. A positive τ means κ(¬X) = τ, κ(X) = 0; a negative τ means κ(X) = |τ|, κ(¬X) = 0; τ = 0 means both are 0 (genuine neutrality). There is no model state where X and ¬X are both positively disbelieved.

The threshold N=2 separating DEFINITE from PROBABLE is a cwyde policy choice; gamen-hs is agnostic about it.

The off-axis categories:

| Category | Formula | Axis | Reading |
|---|---|---|---|
| `INDICATION` | ¬K_clinician(X) ∧ ¬K_clinician(¬X) | epistemic | _Clinician is investigating X; neither asserts nor denies it_ |
| `HISTORICAL` | B_clinician(P(X)) | temporality | _Clinician believes X was the case at some past time_ |
| `HYPOTHETICAL` | B_clinician(X) | temporality | _Clinician believes X in a conditional/hypothetical context_ |
| `FAMILY` | B_clinician(X_family) | experiencer | _Clinician believes X holds of a family member (sortal restriction)_ |
| `UNRESOLVED` | ⊥ | — | _Conflict not resolvable; explicit non-answer_ |

Off-axis categories use ungraded `Belief` because graded firmness is not the relevant dimension: HISTORICAL has a temporal operator (Past), FAMILY has a sortal restriction, HYPOTHETICAL marks conditional context, and INDICATION is already a distinct epistemic operator. Graded ranking is on the roadmap for HYPOTHETICAL (via accessibility operators) but not yet implemented.

### INDICATION is already correct

`INDICATION` is the one category that v0.1 encoded correctly. The formula ¬K_a(X) ∧ ¬K_a(¬X) — from B&D's epistemic logic — captures the clinician's ignorance of both X and its negation. No change in v0.3.

### HISTORICAL: belief scoped over a past operator

`HISTORICAL` encodes that the clinician believes the finding *was* the case: B_clinician(P(X)). The doxastic wrapper is important: a clinician can be wrong about history.

### FAMILY: sortal restriction via atom name

`FAMILY` uses **sortal atomisation**: the atom name gains a `_family` suffix — `B_clinician(X_family)` rather than `B_clinician(X)`. This keeps the patient-entity and family-entity distinct in any downstream belief context.

### HYPOTHETICAL: conditionality in the category, not the formula

`HYPOTHETICAL` produces `B_clinician(X)`. The conditional framing is preserved in the `AssertionCategory` value. A full encoding using a hypothetical-world accessibility operator is on the v0.4+ roadmap.

---

## Why Doxastic, Not Alethic

The key failure of alethic encodings is the **T axiom**: □φ → φ (necessity entails truth). An alethic encoding of "no PE" as □¬PE commits to PE being false in the world — but clinicians can be wrong. Under the doxastic encoding, the same assertion becomes `RankedBelief("clinician", -2, Atom("pe"))`, which makes no truth claim about PE itself.

The practical payoff appears in **multi-author consistency**. Two reports that disagree about PE produce:

```
RankedBelief("radA", 2, pe) ∧ RankedBelief("radB", -2, pe)   — consistent
```

Two belief states from different agents can disagree without contradiction. This is consistent by construction because the agents are distinct; gamen-hs's KD45 axiom D (¬(B_a(φ) ∧ B_a(¬φ))) applies per-agent only.

---

## ModalFormula Dataclass Tree

`cwyde.formal.modal` defines fourteen dataclasses mirroring gamen-hs's 26-constructor JSON format. Unimplemented constructors raise `NotImplementedError`.

| Dataclass | Symbol | gamen-hs `type` |
|---|---|---|
| `Atom(name)` | p | `"atom"` |
| `Not(φ)` | ¬φ | `"not"` |
| `And(φ, ψ)` | φ ∧ ψ | `"and"` |
| `Or(φ, ψ)` | φ ∨ ψ | `"or"` |
| `Implies(φ, ψ)` | φ → ψ | `"implies"` |
| `Box(φ)` | □φ | `"box"` |
| `Diamond(φ)` | ◇φ | `"diamond"` |
| `Past(φ)` | P(φ) | `"past_diamond"` |
| `FutureBox(φ)` | [F]φ | `"future_box"` |
| `FutureDiamond(φ)` | ⟨F⟩φ | `"future_diamond"` |
| `Knowledge(agent, φ)` | K_a(φ) | `"knowledge"` |
| `Belief(agent, φ)` | B_a(φ) | `"belief"` |
| `RankedBelief(agent, rank, φ)` | τ_a(φ) = n | `"ranked_belief"` |
| `Indication(φ, agent)` | ?(φ) | _expands to And/Not/Knowledge_ |

`RankedBelief` is new in v0.3. It implements Spohn's OCF signed-rank semantics and corresponds to gamen-hs's 26th constructor (added in gamen-hs issue #10). `Belief` is retained for off-axis categories and direct use. `Box` and `Diamond` are retained but not generated by the translator for clinical categories.

`Indication` is a cwyde extension not in base B&D. In `to_tree_json()` it expands to `¬K_a(X) ∧ ¬K_a(¬X)` so gamen-hs receives only standard constructors.

Each dataclass implements:

- `to_tree_json()` — full recursive tree for the gamen-validate wire protocol
- `to_flat_extraction()` — compact single-level dict for LLM-extracted formula output

---

## Category → Formula Translation

`cwyde.formal.translator.category_to_formula(category, atom, *, agent="clinician")` produces the canonical formula:

```python
from cwyde.formal.translator import category_to_formula
from cwyde.categories import AssertionCategory

# Definite negation: τ_clinician(pe) = -2
f = category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "pulmonary_embolism")
# RankedBelief("clinician", -2, Atom("pulmonary_embolism"))

f.to_tree_json()
# {
#   "type": "ranked_belief",
#   "agent": "clinician",
#   "rank": -2,
#   "operand": {"type": "atom", "name": "pulmonary_embolism"}
# }

# Probable existence: τ_clinician(pe) = 1
p = category_to_formula(AssertionCategory.PROBABLE_EXISTENCE, "pulmonary_embolism")
# RankedBelief("clinician", 1, Atom("pulmonary_embolism"))

# Ambivalent: τ_clinician(pe) = 0 — genuinely neutral
a = category_to_formula(AssertionCategory.AMBIVALENT_EXISTENCE, "pulmonary_embolism")
# RankedBelief("clinician", 0, Atom("pulmonary_embolism"))

# Historical: B_clinician(P(PE)) — still plain Belief with Past
h = category_to_formula(AssertionCategory.HISTORICAL, "pulmonary_embolism")
# Belief("clinician", Past(Atom("pulmonary_embolism")))

# Custom agent
r = category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe", agent="radiologist")
# RankedBelief("radiologist", 2, Atom("pe"))
```

`UNRESOLVED` has no modal encoding; calling `category_to_formula` with it raises `ValueError`.

---

## Wire Protocol: Sending to gamen-validate

gamen-hs has supported `RankedBelief` since gamen-hs issue #10. The JSON wire format:

**Tree format** — full constructor tree, used by cwyde:
```json
{
  "type": "ranked_belief",
  "agent": "clinician",
  "rank": 2,
  "operand": {"type": "atom", "name": "fever"}
}
```

**Flat extraction format** — compact single-level dict, used for LLM output:
```json
{"op": "ranked_belief", "agent": "clinician", "rank": 2, "operand": {"op": "atom", "atom": "fever"}}
```

Consistency checking:

```python
from cwyde_haskell_bridge import GamenBridge
from cwyde.formal.translator import category_to_formula
from cwyde.categories import AssertionCategory

bridge = GamenBridge()

# Two authors disagree — doxastically consistent (different agents)
formulas = [
    category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe", agent="radiologist_a"),
    category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "pe", agent="radiologist_b"),
]
result = bridge.check_consistency(formulas)
# result.consistent → True

# Same author, contradictory ranks — inconsistent by KD45 axiom D
formulas = [
    category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe", agent="clinician"),
    category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "pe", agent="clinician"),
]
result = bridge.check_consistency(formulas)
# result.consistent → False  (τ=2 and τ=-2 for the same (agent, atom) pair)
```

---

## Formal Properties of the Ranked Doxastic Scale

For reference during interpretation and consistency checking:

- τ_a(X) = n and τ_a(X) = m with n ≠ m is inconsistent — τ is a function (one value per (agent, atom) pair). gamen-hs tableau exposes this as a functionality closure rule.
- τ_a(X) = n and τ_a(¬X) = m with n > 0 and m > 0 is inconsistent — Spohn's Theorem 2(a) forbids both sides being positively disbelieved.
- `RankedBelief("radA", 2, pe)` and `RankedBelief("radB", -2, pe)` is consistent — different agents.
- `Belief(a, P(X))` does not imply `RankedBelief(a, 2, X)` — historical belief does not imply current belief.
- `RankedBelief(a, n, X)` does not entail X for any n — the T axiom fails for belief, which is the point.
- INDICATION (¬K_a(X) ∧ ¬K_a(¬X)) is compatible with any RankedBelief value — being under investigation is orthogonal to the existence axis.

These properties inform the `interaction_rules.yaml` overrides and explain which co-occurring modifier pairs are flagged `submit_to_gamen=True` for formal verification.

---

## Connection to gamen-hs

gamen-hs (at `~/Code/Haskell/gamen-hs`) implements a multi-modal logic framework covering STIT, XSTIT, deontic, epistemic, and doxastic operators. The `RankedBelief` constructor and `Gamen.RankingTheory` module (KappaModel, conditionalize, applyEvidence) were added in issue #10. The design split: gamen-hs provides the OCF primitives; cwyde decides aggregation policy (what counts as independent evidence, and the N=2 threshold for DEFINITE vs PROBABLE).

The consistency check invoked by `cwyde_consistency_checker` shares the gamen-validate binary with guideline-validation and guideline-cds-simulation.
