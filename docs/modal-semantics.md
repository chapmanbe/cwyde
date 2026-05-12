# Modal Semantics in cwyde (v0.1 — historical reference)

> **This document describes the v0.1 alethic encoding, retained for historical reference.**
> The v0.2 encoding replaces alethic operators (□/◇) with doxastic belief operators (B_a).
> See `docs/doxastic-semantics.md` for the current encoding and `docs/doxastic-foundations.md`
> for the rationale.

cwyde's assertion taxonomy is grounded in modal logic, using the [Boxes and Diamonds](https://bd.openlogicproject.org) (B&D) framework as the reference. Each `AssertionCategory` has a precise modal reading; findings that require formal reasoning are translated to `ModalFormula` trees and submitted to [gamen-hs](~/Code/Haskell/gamen-hs) for consistency checking.

---

## Category → Modal Reading

The five existence-axis categories form a scale from necessary presence to necessary absence:

| Category | Formula | Reading |
|---|---|---|
| `DEFINITE_EXISTENCE` | □X | _X is necessarily present_ |
| `PROBABLE_EXISTENCE` | ◇X | _X is possibly present_ |
| `AMBIVALENT_EXISTENCE` | ◇X ∧ ◇¬X | _X may be present or absent_ (genuine uncertainty) |
| `PROBABLE_NEGATED_EXISTENCE` | ◇¬X | _X is possibly absent_ |
| `DEFINITE_NEGATED_EXISTENCE` | □¬X | _X is necessarily absent_ |

The off-axis categories encode context that is orthogonal to certainty:

| Category | Formula | Axis | Reading |
|---|---|---|---|
| `INDICATION` | ¬K_a(X) ∧ ¬K_a(¬X) | epistemic | _Clinician a neither knows X nor knows ¬X_ |
| `HISTORICAL` | P(X) | temporality | _X was the case at some past time_ |
| `HYPOTHETICAL` | ◇X (hypothetical world) | temporality | _X holds in an accessible counterfactual world_ |
| `FAMILY` | K_family(X) | experiencer | _A family member is the bearer of X_ |
| `UNRESOLVED` | ⊥ | — | _Conflict not resolvable; explicit non-answer_ |

### Epistemic scale and negation

The existence axis is not symmetric. `PROBABLE_NEGATED_EXISTENCE` (◇¬X) is a positive epistemic claim — the clinician can imagine a world where X is absent. It differs from `DEFINITE_NEGATED_EXISTENCE` (□¬X), which rules out X in all accessible worlds. The distinction matters for clinical NLP: "no evidence to suggest PE" is ◇¬X (absence of an inferential sign), not □¬X (direct ruling out).

### INDICATION as a first-class category

pyConTextNLP and medspaCy have no equivalent of `INDICATION`. cwyde adds it to model sentences like "rule out PE" or "evaluated for DVT," where the clinician is investigating X but has committed to neither X nor ¬X. The formula ¬K_a(X) ∧ ¬K_a(¬X) (from B&D's epistemic logic) captures this: it asserts ignorance of both X and its negation.

In `to_tree_json()`, `Indication` expands to a standard And/Not/Knowledge tree so gamen-hs receives only constructors it already knows:

```json
{
  "type": "and",
  "left":  {"type": "not", "operand": {"type": "knowledge", "agent": "clinician",
             "operand": {"type": "atom", "name": "pe"}}},
  "right": {"type": "not", "operand": {"type": "knowledge", "agent": "clinician",
             "operand": {"type": "not", "operand": {"type": "atom", "name": "pe"}}}}
}
```

---

## ModalFormula Dataclass Tree

`cwyde.formal.modal` defines twelve dataclasses that mirror the constructor subset of gamen-hs's 24-constructor JSON format. Unimplemented constructors raise `NotImplementedError` to fail loudly rather than silently producing malformed trees.

| Dataclass | B&D symbol | gamen-hs `type` |
|---|---|---|
| `Atom(name)` | p | `"atom"` |
| `Not(φ)` | ¬φ | `"not"` |
| `And(φ, ψ)` | φ ∧ ψ | `"and"` |
| `Or(φ, ψ)` | φ ∨ ψ | `"or"` |
| `Implies(φ, ψ)` | φ → ψ | `"implies"` |
| `Box(φ)` | □φ | `"box"` |
| `Diamond(φ)` | ◇φ | `"diamond"` |
| `Past(φ)` | P(φ) | `"past"` |
| `FutureBox(φ)` | [F]φ | `"future_box"` |
| `FutureDiamond(φ)` | ⟨F⟩φ | `"future_diamond"` |
| `Knowledge(agent, φ)` | K_a(φ) | `"knowledge"` |
| `Indication(φ, agent)` | ?(φ) | _expands to And/Not/Knowledge_ |

Each dataclass implements two serialisation methods:

- `to_tree_json()` — full recursive tree for the gamen-validate wire protocol
- `to_flat_extraction()` — compact single-level dict for LLM-extracted formula output (same protocol as guideline-validation)

---

## Category → Formula Translation

`cwyde.formal.translator.category_to_formula(category, atom)` produces the canonical formula for a given assertion:

```python
from cwyde.formal.translator import category_to_formula
from cwyde.categories import AssertionCategory

f = category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "pulmonary_embolism")
# Box(Not(Atom("pulmonary_embolism")))
f.to_tree_json()
# {"type": "box", "operand": {"type": "not", "operand": {"type": "atom", "name": "pulmonary_embolism"}}}
```

Notes on specific categories:

- **HYPOTHETICAL** — encoded as ◇X (v0.1 simplification). A full encoding would use an indexed possibility operator scoped to a hypothetical accessibility relation; this is on the gamen-hs roadmap.
- **FAMILY** — encoded as K_family(X), using the K operator with agent `"family"`. This treats family history as an epistemic claim: a family member is the bearer of X.
- **UNRESOLVED** — has no modal encoding. Calling `category_to_formula` with `UNRESOLVED` raises `ValueError`; the caller must resolve the conflict first.

---

## Wire Protocol: Sending to gamen-validate

gamen-validate accepts JSON Lines on stdin. cwyde's `cwyde-haskell-bridge` package wraps the subprocess protocol. Two formats are supported (inherited from guideline-validation):

**Tree format** — full constructor tree, used by cwyde:
```json
{"type": "box", "operand": {"type": "not", "operand": {"type": "atom", "name": "fever"}}}
```

**Flat extraction format** — compact single-level dict, used for LLM output:
```json
{"op": "box", "operand": {"op": "not", "operand": {"op": "atom", "atom": "fever"}}}
```

Consistency checking submits a list of formulas and receives a boolean result:

```python
from cwyde_haskell_bridge import GamenBridge
bridge = GamenBridge()

formulas = [
    category_to_formula(AssertionCategory.DEFINITE_EXISTENCE, "pe"),
    category_to_formula(AssertionCategory.DEFINITE_NEGATED_EXISTENCE, "pe"),
]
result = bridge.check_consistency(formulas)
# result.consistent → False  (□pe ∧ □¬pe is inconsistent in normal modal logic)
```

---

## Connection to gamen-hs

gamen-hs (at `~/Code/Haskell/gamen-hs`) implements a multi-modal logic framework covering STIT, XSTIT, deontic, and epistemic operators over the full 24-constructor set. cwyde uses the same wire protocol but only requires the 12 constructors listed above.

The consistency check invoked by `cwyde_consistency_checker` is the same check used by guideline-validation for clinical guideline conflict detection and by guideline-cds-simulation for per-patient obligation sets. All three share the gamen-validate binary.

---

## Formal Properties of the Assertion Scale

For reference during interpretation and consistency checking:

- □X → ◇X (necessitation implies possibility; DEFINITE_EXISTENCE implies PROBABLE_EXISTENCE)
- □¬X → ◇¬X (DEFINITE_NEGATED implies PROBABLE_NEGATED)
- □X ∧ □¬X is inconsistent in any normal modal logic (DEFINITE_EXISTENCE and DEFINITE_NEGATED cannot co-occur)
- ¬K_a(X) ∧ ¬K_a(¬X) is consistent with ◇X and with ◇¬X (INDICATION is compatible with either existence outcome)
- P(X) does not imply □X (HISTORICAL does not assert current existence)

These properties inform the `interaction_rules.yaml` overrides and explain which co-occurring modifier pairs are flagged `submit_to_gamen=True` for formal verification.
