# cwyde

**Formal semantics layer for clinical context classification.**

cwyde (Old English: *utterance, assertion*) is a Python package that adds principled modifier interaction semantics to [medspaCy](https://github.com/medspacy/medspacy)'s ConText component. It does not replace medspaCy — it composes on top of it.

## The problem

medspaCy's ConText component identifies clinical context modifiers (negation, uncertainty, temporality, experiencer) but:

1. **Collapses the taxonomy**: rich pyConTextNLP categories like `PROBABLE_EXISTENCE` vs `DEFINITE_EXISTENCE` are flattened to a single `is_negated` boolean.
2. **Omits INDICATION**: "rule out PE" is not a negated finding — it means the clinician is investigating whether PE is present. Treating it as negation is a category error.
3. **No conflict resolution**: when multiple modifiers co-occur, they accumulate as an unresolved list. Downstream code must decide what to do.
4. **No document-level propagation**: section headers like "Past Medical History" should propagate a HISTORICAL assertion to all findings in the section, but medspaCy's ConText is sentence-scoped only.

## The approach

Clinical context modifier categories are **modal operators**. Their interaction rules are logical entailments, not empirical patterns:

| Category | Modal reading |
|---|---|
| `DEFINITE_NEGATED_EXISTENCE` | □¬X — necessarily absent |
| `PROBABLE_NEGATED_EXISTENCE` | ◇¬X — possibly absent |
| `AMBIVALENT_EXISTENCE` | ◇X ∧ ◇¬X — indeterminate |
| `PROBABLE_EXISTENCE` | ◇X — possibly present |
| `DEFINITE_EXISTENCE` | □X — necessarily present |
| `HISTORICAL` | P(X) — was the case |
| `INDICATION` | ?(X) — under investigation; neither asserted nor denied |

cwyde provides a YAML-driven interaction rules interpreter for pure-Python use and integrates with [gamen-hs](https://github.com/chapmanbe/gamen-hs) for formal modal consistency checking when available.

## Architecture

```
Clinical text
     │
     ▼
medspaCy pipeline
 ├── sentence splitter (PyRuSH)
 ├── NER / target extraction
 ├── ConText (base modifier matching)
 └── section detection
     │
     ▼
cwyde layer
 ├── category_mapper     — ConText categories → rich taxonomy
 ├── indication_detector — INDICATION as a first-class category
 ├── conflict_resolver   — co-occurring modifier resolution
 └── section_propagator  — section-level assertion inheritance
     │
     ▼ (optional)
gamen-hs bridge
 └── formal consistency checking via modal logic
```

## Quick start

```python
import cwyde

nlp = cwyde.load("en")
doc = nlp("No evidence of pulmonary embolism.")

for ent in doc.ents:
    print(ent.text, ent._.cwyde_assertion_category)
    # pulmonary embolism  AssertionCategory.DEFINITE_NEGATED_EXISTENCE
```

## Installation

```bash
# Engine + knowledge bases
pip install cwyde cwyde-knowledge

# With optional gamen-hs bridge
pip install cwyde cwyde-knowledge cwyde-haskell-bridge
```

## Packages

This monorepo contains three installable distributions:

- **`cwyde`** — the processing engine (spaCy components, formal logic, plugin API)
- **`cwyde-knowledge`** — clinical NLP knowledge bases (YAML lexicons, interaction rules, section assertions)
- **`cwyde-haskell-bridge`** — subprocess interface to the [gamen-validate](https://github.com/chapmanbe/gamen-hs) binary

## Relationship to pyConTextNLP and medspaCy

cwyde is the spiritual successor to [pyConTextNLP](https://github.com/chapmanbe/pyConTextNLP) in the narrow sense of providing the formal semantics that pyConTextNLP's rules engine always lacked. It does not revive pyConTextNLP. medspaCy handles all NLP infrastructure; cwyde adds the semantics layer on top.

## Part of the Gamen project family

cwyde connects to [gamen-hs](https://github.com/chapmanbe/gamen-hs), a Haskell modal logic framework implementing STIT, XSTIT, and deontic reasoning. The JSON Lines bridge interface is shared with [guideline-validation](https://github.com/chapmanbe/guideline-validation) and [patient-agent-assistant](https://github.com/chapmanbe/patient-agent-assistant).

## References

- Harkema H, et al. ConText: an algorithm for determining negation, experiencer, and temporal status from clinical reports. *J Biomed Inform.* 2009;42(5):839–51.
- Chapman BE, et al. Document-level classification of CT pulmonary angiography reports based on an extension of the ConText algorithm. *J Biomed Inform.* 2011;44(5):728–37.
- Eyre H, et al. Launching into clinical space with medspaCy. *AMIA Annu Symp Proc.* 2021.
