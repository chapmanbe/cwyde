# Doxastic Foundations of cwyde (v0.2 Design Note)

> **Status:** design rationale for v0.2. v0.1 ships with the alethic encoding described in `modal-semantics.md`. This document explains why that encoding is a category mistake and how v0.2 will move to a doxastic foundation.

---

## The Category Mistake in v0.1

cwyde v0.1 encodes the existence-axis assertion categories using **alethic** modal logic — the modal logic of necessity and possibility (□, ◇). Convenient, but wrong. Clinical assertion categories are not claims about logical or metaphysical necessity; they are claims about the **belief state of the document's author**.

When a radiologist writes:

> *No evidence of pulmonary embolism.*

the proposition expressed is not "PE is necessarily false in all possible worlds" (□¬PE). It is "the radiologist believes PE is absent" — B_radiologist(¬PE). The difference matters formally because these two readings validate different axioms:

| Axiom | Alethic □ | Doxastic B_a |
|---|---|---|
| **T**: □φ → φ (necessity entails truth) | ✓ valid | ✗ invalid |
| **D**: □φ → ◇φ (consistency) | ✓ valid | ✓ valid (B_a(φ) → ¬B_a(¬φ)) |
| **4**: □φ → □□φ (positive introspection) | depends on system | typically ✓ for B_a |
| **5**: ¬□φ → □¬□φ (negative introspection) | depends on system | controversial |

The T axiom is the load-bearing failure. Treating clinical assertions as alethic builds an unwarranted truth claim into the formalism. A radiologist who reports "no PE" can be wrong; the formalism should not commit to the truth of the report.

---

## The Diagnosis, Category by Category

| Category | v0.1 encoding | What it actually expresses |
|---|---|---|
| `DEFINITE_EXISTENCE` | □X | B_clinician(X) — clinician believes X |
| `PROBABLE_EXISTENCE` | ◇X | graded belief, biased toward X but uncommitted |
| `AMBIVALENT_EXISTENCE` | ◇X ∧ ◇¬X | clinician uncommitted, balanced |
| `PROBABLE_NEGATED_EXISTENCE` | ◇¬X | graded disbelief in X |
| `DEFINITE_NEGATED_EXISTENCE` | □¬X | B_clinician(¬X) — clinician believes ¬X |
| `INDICATION` | ¬K_a(X) ∧ ¬K_a(¬X) | already epistemic ✓ |
| `HISTORICAL` | P(X) | B_clinician(P(X)) — temporal scoped under belief |
| `HYPOTHETICAL` | ◇X (placeholder) | B_clinician(X) under hypothetical accessibility |
| `FAMILY` | K_family(X) | sortal restriction on the bearer of X — currently dressed up as epistemic |
| `UNRESOLVED` | ⊥ | unchanged |

Two categories warrant comment:

- **INDICATION** is the only category v0.1 encodes correctly. It is genuinely epistemic — a claim about the clinician's *ignorance*, expressed as ¬K_a(X) ∧ ¬K_a(¬X). No revision needed.
- **FAMILY** is currently encoded as K_family(X), which is a hack. The "family member" dimension is not really an epistemic claim about a different agent; it is a *sortal restriction* on the bearer of the proposition. The clinician believes (about the family member, not the patient) that X. Properly: B_clinician(holds_for(X, family_member)) where `holds_for` is a sortal predicate. v0.2 should disentangle the experiencer axis from the modal operators.

---

## Why Multi-Agent Structure Matters

Clinical documents are layered. An admission note cites an outpatient clinic note that cites a discharge summary that cites a radiology read. Each layer is a different agent's belief at a different point in time. Reports often disagree.

Under the **alethic** encoding, two reports that disagree about PE produce:

```
□PE ∧ □¬PE  ⊥  (contradiction)
```

The formalism flags this as inconsistent. But the clinical situation is **not inconsistent**: it is just two authors who disagreed, and their disagreement is itself a piece of clinical information worth preserving.

Under the **doxastic** encoding:

```
B_admit(PE) ∧ B_clinic(¬PE)   consistent
```

— two distinct belief states, no contradiction, multi-agent structure preserved. Disagreement becomes a query result ("which entities have conflicting belief assertions across authors?") rather than a logical paradox.

This is the practical payoff of moving to doxastic logic, separate from the philosophical correctness argument.

---

## The Graded Scale Is Graded Belief, Not Graded Possibility

The five-point existence scale is not capturing graded alethic possibility (alethic ◇ has no internal grade — a proposition either is or is not possible in some accessible world). It is capturing **graded belief**: the clinician's confidence ranges from "essentially certain X" through "leaning toward X" through "balanced" through "leaning toward ¬X" to "essentially certain ¬X."

Spohn's ranking theory (1988) is the formal framework purpose-built for graded qualitative belief. The mapping is direct:

- `DEFINITE_EXISTENCE`: κ_clinician(¬X) ≥ N for some chosen threshold — strong rank-disbelief in ¬X
- `PROBABLE_EXISTENCE`: κ_clinician(¬X) = 0 and κ_clinician(X) = 0, with positive bias signal — neither X nor ¬X is surprising, but the agent leans toward X
- `AMBIVALENT_EXISTENCE`: balanced ranks; agent uncommitted
- `PROBABLE_NEGATED_EXISTENCE`, `DEFINITE_NEGATED_EXISTENCE`: symmetric

Combination of modifiers under independence is rank addition rather than the certainty-factor combinator that systems like MYCIN used (and that Heckerman 1986 showed silently assumes hidden conditional independence). This is the same correctness argument made in `mshi_ai_resources/future_revision/mycin-cf-vs-ranking-theory.md`, applied to cwyde's setting.

---

## Where Deontic Enters (And Why It Is Not Here)

A previous draft of cwyde's documentation claimed that cwyde uses deontic logic. It does not. `cwyde/formal/modal.py` has no `Ought` or `Permitted` constructor.

Deontic logic enters the **full clinical reasoning chain**, not at cwyde's extraction layer:

1. **cwyde** extracts what the clinician *believes* about the patient's state: `B_clinician(ASCVD)`.
2. **Clinical guidelines** express what *ought* to be done given those beliefs: `ASCVD → Ought_clinician(prescribe_statin)`.
3. **Downstream systems** (`guideline-validation`, `patient-agent-assistant`, `guideline-cds-simulation`) compose the doxastic facts from cwyde with the deontic rules from guidelines.

This is the right division of labour. cwyde stays in the doxastic-temporal-epistemic zone; gamen-hs's deontic operators do their work downstream of cwyde's output. v0.2 should preserve this separation explicitly.

---

## Proposed v0.2 Changes to cwyde

### Formal layer (`cwyde/formal/`)

1. **Add a `Belief` dataclass to `modal.py`**: non-factive, multi-agent, mirrors gamen-hs's `Belief` constructor (blocked on [chapmanbe/gamen-hs#2](https://github.com/chapmanbe/gamen-hs/issues/2)).

   ```python
   @dataclass
   class Belief(ModalFormula):
       """B_a(φ) — agent a believes φ. Non-factive."""
       agent: str
       operand: ModalFormula
   ```

2. **Rewrite `translator.py`**: the existence-axis categories serialise to `Belief("clinician", ...)` rather than to `Box`/`Diamond`. The graded categories (`PROBABLE_*`, `AMBIVALENT`) need a graded encoding — the cleanest option is a `RankedBelief(agent, rank, operand)` constructor backed by ranking theory, but a simpler v0.2 path is to keep the categorical doxastic encoding and defer the graded layer to v0.3.

3. **Fix `FAMILY`**: replace `Knowledge("family", X)` with a sortal-restricted predicate. The simplest path is to atomise `holds_for_family_member(X)` into the atom name itself (`X_family`), and let the doxastic operator wrap the sortal-restricted atom. A more principled path is to add a `HoldsFor(bearer, formula)` constructor; v0.2 can take the simpler path and revisit.

### Pipeline layer (`cwyde/components/`)

4. **Agent context as an entity attribute**: add `ent._.cwyde_belief_agent` (default `"clinician"`) so that document-level metadata can override it for multi-author corpora. Set in a new `cwyde_agent_resolver` component or as part of `category_mapper`.

5. **Document author/time metadata**: add `doc._.cwyde_author` and `doc._.cwyde_authored_at` to support multi-author and multi-document analyses. cwyde itself does not extract this from the text in v0.2; downstream systems supply it.

6. **`consistency_checker.py` becomes multi-agent-aware**: when joint consistency checks are added (per [chapmanbe/cwyde#1](https://github.com/chapmanbe/cwyde/issues/1)), formulas from different agents must be tagged with their agent so the checker recognises B_radA(PE) ∧ B_radB(¬PE) as consistent rather than as a contradiction.

### Knowledge base

7. `interaction_rules.yaml` does not change semantically — but the `rationale` fields should be re-stated in doxastic terms. Several existing rationales currently invoke "necessarily" and "possibly" framings that no longer fit.

8. `categories.yaml` adds an explicit `agent_scope` field per category (default `"clinician"`, except for `FAMILY` which stays as a marker for sortal restriction).

### Documentation

9. `modal-semantics.md` rewritten as `doxastic-semantics.md` with the new encodings as the primary presentation, and a brief "alethic encoding (v0.1)" appendix for historical reference.

10. `architecture.md` updated to reflect the agent-context attributes and the renamed translator behaviour.

---

## What Does Not Change

- The five-point existence scale (it is the right granularity).
- `INDICATION` as a first-class category.
- The pipeline-component structure and ordering.
- The KB file layout, lexicon adapter system, language plugin registry.
- The strategy pattern, the gamen bridge, the section propagator.
- All the integration tests except those that assert specific `to_tree_json()` output (those will need re-baselining once the doxastic encodings land).

The change is **interpretive and at the formal boundary**, not in the pipeline mechanics. cwyde's NLP layer continues to do the same work; its formal output just becomes more honest about what it is claiming.

---

## Dependencies

| Item | Tracked at | Status |
|---|---|---|
| Past-operator tableau rules in gamen-hs | [chapmanbe/gamen-hs#1](https://github.com/chapmanbe/gamen-hs/issues/1) | open |
| Belief operator in gamen-hs | [chapmanbe/gamen-hs#2](https://github.com/chapmanbe/gamen-hs/issues/2) | open |
| Span-level joint consistency checking in cwyde | [chapmanbe/cwyde#1](https://github.com/chapmanbe/cwyde/issues/1) | open |
| Doxastic redesign for cwyde v0.2 | this document; tracked at chapmanbe/cwyde#2 (to be opened) | planning |

The doxastic redesign is the largest of these and is gated on the gamen-hs Belief operator landing first. The other dependencies (past operators, joint consistency) compose cleanly with the doxastic redesign and can proceed in parallel.

---

## Paper Framing Implications

A v0.2 framing as **"graded doxastic semantics for clinical assertion classification"** is more theoretically defensible than the v0.1 alethic framing. It also positions the work more comfortably for formal-epistemology-aware reviewers (and avoids the awkwardness of defending □/◇ encodings of clinician belief states under peer review).

The connection to ranking theory provides a path from the categorical doxastic encoding (v0.2) to a fully graded doxastic encoding (v0.3 or beyond), and this trajectory is itself a publishable contribution: principled qualitative graded belief in clinical NLP, replacing the heuristic graduation of pyConTextNLP and the alethic encoding of v0.1.

---

## References

- Hintikka, J. (1962). *Knowledge and Belief: An Introduction to the Logic of the Two Notions*. Cornell University Press. (Foundational distinction between K and B.)
- Spohn, W. (1988). Ordinal conditional functions: a dynamic theory of epistemic states. (Graded belief.)
- Spohn, W. (2012). *The Laws of Belief: Ranking Theory and Its Philosophical Applications*. Oxford. (Comprehensive treatment.)
- Halpern, J. Y. (2003). *Reasoning About Uncertainty*. MIT Press. (Multi-agent doxastic logic, comparison of frameworks.)
- Fagin, Halpern, Moses, Vardi (1995). *Reasoning About Knowledge*. MIT Press. (KD45 and related systems.)
