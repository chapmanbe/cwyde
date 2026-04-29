# Section Propagation

Section propagation is cwyde's headline v0.1 contribution. pyConTextNLP and medspaCy's ConText operate sentence-by-sentence; they assign modifier context from local trigger words but have no mechanism for a section header to assert a default context for everything beneath it. Section propagation fills that gap.

**The clinical problem:** In a report like this —

```
PAST MEDICAL HISTORY:
  Hypertension. Type 2 diabetes.

CURRENT MEDICATIONS:
  Lisinopril 10 mg.
```

— "hypertension" and "diabetes" appear without any negation or uncertainty trigger. Sentence-level context alone assigns `DEFINITE_EXISTENCE`. But they are in the past medical history section, so they should be `HISTORICAL`. Section propagation reads the section header and promotes all findings in that section's body accordingly.

---

## Algorithm

`cwyde_section_propagator` runs last in the cwyde pipeline, after the sectionizer and all other cwyde components have run. Its input is `doc._.sections`, a list of medspaCy section objects with `category` and `body_span` attributes.

For each section in document order:

```
1. Look up section category in section_assertions.yaml
   → yields (assertion, propagate_to_children, override_existing) or None

2. Prune the ancestor stack — remove entries whose body_span.end ≤ current body_span.start
   (sequential non-nested sections must not inherit from their predecessor)

3. If no mapping found and stack is non-empty:
       walk stack from top, take first ancestor where propagate_to_children=True

4. Push (section, assertion, propagate_to_children, override_existing) onto stack

5. If no assertion (section unmapped and no inheritable ancestor): skip

6. For each entity whose ent.start falls within the current body span:
       apply section assertion (see resolution logic below)
       append step to ent._.cwyde_resolution_trace
```

### Resolution logic

When applying the section assertion to an entity:

| Entity's current category | `override_existing` | Action |
|---|---|---|
| `DEFINITE_EXISTENCE` | any | Apply section assertion — no sentence-level modifier was present |
| anything else | `True` | Apply section assertion — section wins unconditionally |
| anything else | `False` | Preserve sentence-level assertion; record section context in trace |

The intuition: `DEFINITE_EXISTENCE` is the "no modifier found" default. A section header is a stronger signal than that default, so it always wins. But if ConText already found a negation or uncertainty modifier, that sentence-level evidence is more specific than the section header and should be preserved — unless the section is marked `override_existing=True`.

`override_existing=True` is used for sections like INDICATION_FOR_STUDY or RULE_OUT, where the entire section's purpose is to list things being investigated, regardless of how individual sentences read.

---

## The Stack-Prune Ordering Bug

The critical correctness requirement is that the ancestor stack must be pruned **before** the ancestor-inheritance lookup, not after.

### What went wrong

The original implementation did:

```python
# WRONG ORDER
if assertion is None and section_stack:
    for anc_section, anc_assertion, ... in reversed(section_stack):
        if anc_assertion is not None and anc_propagates:
            assertion = anc_assertion
            break

# prune expired entries after the lookup
section_stack = [e for e in section_stack if e[0].body_span[1] > body_start]
```

Consider this document structure (token indices):

```
[0–50]   PAST MEDICAL HISTORY  →  assertion=HISTORICAL
[51–100] INTERPRETATION         →  no mapping in section_assertions.yaml
```

When processing INTERPRETATION (start=51):

1. Stack still contains PAST MEDICAL HISTORY (its body ends at 50, which is not > 51).
2. Inheritance lookup runs first → finds PAST MEDICAL HISTORY, sets `assertion=HISTORICAL`.
3. Pruning runs → correctly removes PAST MEDICAL HISTORY.

Result: INTERPRETATION's findings get promoted to `HISTORICAL`. Wrong.

### The fix

Prune first, then look for inheritable ancestors:

```python
# CORRECT ORDER
section_stack = [
    entry for entry in section_stack
    if entry[0].body_span[1] > body_start
]

if assertion is None and section_stack:
    for anc_section, anc_assertion, ... in reversed(section_stack):
        if anc_assertion is not None and anc_propagates:
            assertion = anc_assertion
            break
```

Now when processing INTERPRETATION: PAST MEDICAL HISTORY is pruned before the lookup, so the stack is empty and INTERPRETATION inherits nothing.

---

## Nested Sections

When sections are genuinely nested (child body span is contained within parent body span), the parent survives the prune step and the child can inherit from it.

```
[0–200]  FAMILY HISTORY       →  assertion=FAMILY, propagate_to_children=True
  [20–80]  Mother             →  no mapping
  [85–160] Father             →  no mapping
```

Processing Mother (start=20): FAMILY HISTORY body ends at 200 > 20, survives pruning. Mother inherits `assertion=FAMILY`.

Processing Father (start=85): FAMILY HISTORY body ends at 200 > 85, still on stack. Father inherits `assertion=FAMILY`.

A child's own mapping always wins over an inherited ancestor mapping. If "Mother" subsection had its own `section_assertions.yaml` entry, that would be used instead.

---

## section_assertions.yaml Schema

Each entry maps a medspaCy section category string to an assertion rule:

```yaml
section_assertions:
  past_medical_history:
    applies: HISTORICAL
    propagate_to_children: true
    override_existing: false

  indication_for_study:
    applies: INDICATION
    propagate_to_children: true
    override_existing: true      # section always wins, even over explicit negation

  family_history:
    applies: FAMILY
    propagate_to_children: true
    override_existing: false

  allergies:
    applies: DEFINITE_EXISTENCE  # present, not historical
    propagate_to_children: false
    override_existing: false
```

`labs_and_studies` maps to `INDICATION` because medspaCy's sectionizer maps "INDICATION:" headers to that category name. See `section_assertions.yaml` for the full table.

---

## Worked Example

Input document:

```
PAST MEDICAL HISTORY:
Hypertension. No diabetes.

ASSESSMENT:
Probable pneumonia.
```

After medspaCy sectionizer and ConText, before section propagation:

| Entity | Sentence modifier | `cwyde_assertion_category` |
|---|---|---|
| hypertension | none | `DEFINITE_EXISTENCE` |
| diabetes | NEGATION | `DEFINITE_NEGATED_EXISTENCE` |
| pneumonia | UNCERTAIN | `PROBABLE_EXISTENCE` |

Section propagation processes PAST MEDICAL HISTORY (assertion=`HISTORICAL`, override=`False`):

- **hypertension**: current category is `DEFINITE_EXISTENCE` → apply section assertion → `HISTORICAL` ✓
- **diabetes**: current category is `DEFINITE_NEGATED_EXISTENCE`, override=`False` → preserve → `DEFINITE_NEGATED_EXISTENCE` ✓ (sentence-level negation wins)

Section propagation processes ASSESSMENT (no mapping → no assertion):

- **pneumonia**: no section assertion → unchanged → `PROBABLE_EXISTENCE` ✓

Final output:

| Entity | `cwyde_assertion_category` | `cwyde_section_inherited` |
|---|---|---|
| hypertension | `HISTORICAL` | `True` |
| diabetes | `DEFINITE_NEGATED_EXISTENCE` | `False` |
| pneumonia | `PROBABLE_EXISTENCE` | `False` |

---

## Audit Trail

Every section-propagation decision is appended to `ent._.cwyde_resolution_trace`:

```python
# when section assertion changed the category
{"step": "section_propagator", "section": "past_medical_history",
 "section_assertion": "HISTORICAL", "previous": "DEFINITE_EXISTENCE",
 "result": "HISTORICAL", "override_existing": False}

# when sentence-level assertion was preserved
{"step": "section_propagator", "section": "past_medical_history",
 "section_assertion": "HISTORICAL", "result": "DEFINITE_NEGATED_EXISTENCE",
 "note": "sentence-level assertion preserved"}
```

`doc._.cwyde_section_assertions` holds the per-section assertion map for the document, keyed by section category string.
