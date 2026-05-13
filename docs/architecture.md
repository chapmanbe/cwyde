# cwyde Architecture

cwyde is a clinical context-classification layer that sits on top of [medspaCy](https://github.com/medspacy/medspacy). It adds a richer assertion taxonomy, principled conflict resolution, document-level section-context propagation, and optional formal consistency checking via gamen-hs. It is designed to replicate and extend the capabilities of the retired pyConTextNLP.

---

## Monorepo Layout

```
cwyde/                          top-level repo
├── src/cwyde/                  main package — pipeline, components, formal semantics
├── packages/cwyde-knowledge/   YAML knowledge bases (categories, lexicons, rules)
└── packages/cwyde-haskell-bridge/  subprocess client for gamen-validate binary
```

All three packages are editable-installed into a shared `.venv`. Domain knowledge lives in `cwyde-knowledge`; runtime logic lives in `cwyde`. This follows Buchanan's separation principle: changing assertion rules, lexicon entries, or section mappings never requires editing Python code.

---

## Pipeline Ordering

cwyde components are added after medspaCy's core components:

```
medspacy_context          ← phrase/token matching; fills ent._.modifiers
medspacy_sectionizer      ← assigns section categories to spans
─────────────────────────── cwyde components ───────────────────────────
cwyde_category_mapper     ← maps medspaCy modifier categories → AssertionCategory
cwyde_indication_detector ← promotes entities to INDICATION (direct + backfill)
cwyde_conflict_resolver   ← resolves co-occurring modifier conflicts via YAML rules
cwyde_section_propagator  ← propagates section-level assertion context to findings
cwyde_consistency_checker ← optional; calls gamen-validate for formal consistency
```

Entry point:

```python
import cwyde
nlp = cwyde.load("en")          # builds medspaCy pipeline + all cwyde components
doc = nlp("No fever noted.")
```

---

## AssertionCategory Taxonomy

Ten categories with doxastic readings (v0.2). Each category encodes the clinician's belief state regarding the finding:

| Category | Doxastic Reading | Axis |
|---|---|---|
| `DEFINITE_EXISTENCE` | B_clinician(X) | existence |
| `PROBABLE_EXISTENCE` | B_clinician(X) | existence |
| `AMBIVALENT_EXISTENCE` | ¬B_clinician(X) ∧ ¬B_clinician(¬X) | existence |
| `PROBABLE_NEGATED_EXISTENCE` | B_clinician(¬X) | existence |
| `DEFINITE_NEGATED_EXISTENCE` | B_clinician(¬X) | existence |
| `INDICATION` | ¬K_clinician(X) ∧ ¬K_clinician(¬X) | epistemic |
| `HISTORICAL` | B_clinician(P(X)) | temporality |
| `HYPOTHETICAL` | B_clinician(X) | temporality |
| `FAMILY` | B_clinician(X_family) | experiencer |
| `UNRESOLVED` | ⊥ | — |

`DEFINITE_EXISTENCE` and `PROBABLE_EXISTENCE` produce the same formula; the grade is preserved in the category name. A v0.3 graded-belief encoding (Spohn ranking theory) will differentiate them at the formula level.

`INDICATION` is a first-class category (not present in pyConTextNLP, and not present as a named category in medspaCy's default ConText rules) encoding that the clinician is actively investigating whether X is present — they have neither asserted nor denied it. medspaCy's default rules map "rule out" to negation or uncertainty depending on context; cwyde treats it as a distinct epistemic state (¬K∧¬K¬).

`UNRESOLVED` is an explicit non-answer assigned when co-occurring modifiers cannot be resolved by the YAML rules and gamen-validate is unavailable.

See `docs/doxastic-semantics.md` for full encoding details and wire-protocol examples.

---

## Component Details

### cwyde_category_mapper

Reads `ent._.modifiers` from medspaCy ConText and translates each modifier's category string to an `AssertionCategory` using `medspacy_category_map.yaml`. When a single modifier is present, the entity gets that category directly. When multiple modifiers are present, the entity is tagged `UNRESOLVED` and passed to `cwyde_conflict_resolver`. Entities with no modifiers receive `DEFINITE_EXISTENCE`.

### cwyde_indication_detector

Two detection paths:

1. **Direct**: entity was already mapped to `INDICATION` by the category mapper (via a KB lexicon entry).
2. **Backfill**: runs language-specific regex patterns from `indication_patterns.yaml` against the entity's sentence span. Catches rule-out triggers that ConText's phrase-matcher misses (e.g., "evaluate for" patterns).

### cwyde_conflict_resolver

When `ent._.cwyde_assertion_category == UNRESOLVED`, this component recovers the list of per-modifier categories from the resolution trace and calls `strategy.resolve_conflict()`. The strategy consults `interaction_rules.yaml`, which defines:

- **`overrides`**: explicit (modifier-set → result) rules, e.g., `[FAMILY, HISTORICAL] → FAMILY`
- **`unresolvable`**: combinations that stay `UNRESOLVED` even after consulting the table
- **`precedence`**: linear fallback order for unrecognised combinations

### cwyde_section_propagator

The headline v0.1 contribution. Propagates a section's default assertion category to all findings within that section's body span. Algorithm:

1. Iterate sections from medspaCy's sectionizer in document order.
2. **Prune the ancestor stack** — remove any entries whose body span ended before the current section starts. This must happen _before_ ancestor-inheritance lookup; doing it after caused sequential non-nested sections (e.g., INTERPRETATION following PAST MEDICAL HISTORY) to incorrectly inherit the predecessor's assertion.
3. If the current section has no mapping in `section_assertions.yaml`, walk the pruned stack for the nearest ancestor that `propagate_to_children=True`.
4. For each entity in the section body: apply the section assertion when either (a) the entity has no sentence-level modifier (`DEFINITE_EXISTENCE`), or (b) `override_existing=True` on the section rule (used for INDICATION sections).
5. Record every decision in `ent._.cwyde_resolution_trace` for auditability.

### cwyde_consistency_checker

Optional final component. Collects all entities with modal formulas and submits them in batch to `GamenStrategy.check_consistency()`. If gamen-validate is unavailable, the component is silently skipped when `skip_if_unavailable=True` (the default when using `cwyde.load()`).

---

## Formal Semantics Layer

### Modal Formula Tree (`cwyde.formal.modal`)

Thirteen dataclasses mirroring the constructor subset of gamen-hs's 24-constructor JSON format. Each implements `to_tree_json()` (for the gamen-validate wire protocol) and `to_flat_extraction()` (for LLM-extracted formula output).

Implemented constructors: `Atom`, `Not`, `And`, `Or`, `Implies`, `Box`, `Diamond`, `Past`, `FutureBox`, `FutureDiamond`, `Knowledge`, `Belief`, `Indication`.

`Belief(agent, φ)` is new in v0.2. It is non-factive (KD45): `B_a(φ)` does not entail `φ`. It is the primary operator for clinical assertion categories. `Box` and `Diamond` are retained but no longer generated by the translator.

`Indication` is a cwyde extension not in base B&D. In `to_tree_json()` it expands to `¬K_a(X) ∧ ¬K_a(¬X)` so gamen-hs receives only standard constructors.

### Translator (`cwyde.formal.translator`)

Converts `AssertionCategory` values to `ModalFormula` instances, binding the entity text as the propositional atom. The optional `agent` keyword argument (default `"clinician"`) sets the belief agent for multi-author corpora.

### Strategy Pattern (`cwyde.formal.strategy`)

Three implementations of `ReasonerStrategy`:

| Class | Description |
|---|---|
| `FallbackStrategy` | Pure-Python YAML-table interpreter. Always available. |
| `GamenStrategy` | Delegates to gamen-validate via `cwyde-haskell-bridge`. Raises on binary unavailability. |
| `CompositeStrategy` | Tries `GamenStrategy`; falls back to `FallbackStrategy` on infrastructure failures (`GamenError`). Never falls back on `GamenSemanticError` (translator bug — surfaces immediately). |

`cwyde.load()` uses `CompositeStrategy` by default. Users requiring hard-failure on missing binary pass `GamenStrategy` directly; users requiring pure-Python pass `FallbackStrategy` directly.

---

## Knowledge Base Structure

```
packages/cwyde-knowledge/src/cwyde_knowledge/data/
├── core/
│   ├── categories.yaml           AssertionCategory definitions + modal formulas
│   ├── interaction_rules.yaml    Conflict-resolution rules (overrides, precedence)
│   ├── medspacy_category_map.yaml  medspaCy category string → AssertionCategory
│   └── section_assertions.yaml   Section name → default AssertionCategory
└── lang/
    └── en/
        ├── indication_patterns.yaml   Regex patterns for indication backfill
        ├── backfill_patterns.yaml     (reserved)
        └── lexicon/
            ├── negation.yaml
            ├── uncertainty.yaml
            ├── historical.yaml
            ├── hypothetical.yaml
            ├── family.yaml
            └── general_modifiers.yaml   ← loaded last; supersedes prior files
```

All files are Pydantic v2 validated at load time (`extra="forbid"` on all top-level models).

The lexicon load order matters: `general_modifiers.yaml` is always last in `lexicon_paths()`, so it wins over legacy KB files for any literal it defines. When `_load_lexicons_into_context()` injects lexicon entries into medspaCy's ConText component, it also removes any default medspaCy ConText rules whose literal appears in the cwyde lexicons, preventing duplicate match interference.

---

## Language Plugin System

Language-specific configuration is provided via `cwyde.lang.registry`. Each language has an adapter module (`cwyde/lang/{code}/adapter.py`) that returns lexicon paths in the correct load order. The registry is keyed by BCP 47 language code.

```python
from cwyde.lang.registry import get_plugin
plugin = get_plugin("en")
plugin.lexicon_paths()   # ordered list of Path objects
```

The Spanish skeleton (`cwyde/lang/es/`) provides the same interface with stub lexicons for integration-testing the plugin boundary without English-specific KB content.

---

## spaCy Extension Attributes

All cwyde output is stored in spaCy `._` extension attributes registered at import time (`cwyde.extensions`):

| Attribute | Type | Description |
|---|---|---|
| `ent._.cwyde_assertion_category` | `AssertionCategory` | Final resolved category |
| `ent._.cwyde_modal_formula` | `ModalFormula \| None` | Formal formula for gamen-validate |
| `ent._.cwyde_belief_agent` | `str` | Belief agent for this entity (default `"clinician"`; inherits from `doc._.cwyde_author` if set) |
| `ent._.cwyde_resolution_trace` | `list[dict]` | Step-by-step audit trail |
| `ent._.cwyde_section_inherited` | `bool` | True if section propagation changed the category |
| `ent._.cwyde_is_indication` | `bool` | True if INDICATION was set by indication_detector |
| `doc._.cwyde_author` | `str \| None` | Document author identifier; set by caller before pipeline runs |
| `doc._.cwyde_authored_at` | `Any \| None` | Document authorship timestamp; set by caller, not extracted from text |
| `doc._.cwyde_section_assertions` | `dict[str, AssertionCategory]` | Per-section assertion map |
