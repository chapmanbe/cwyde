# cwyde

**Formal semantics layer for clinical context classification.**

cwyde (Old English: *utterance, assertion*) is a Python package that adds principled modifier interaction semantics to [medspaCy](https://github.com/medspacy/medspacy)'s ConText component. It does not replace medspaCy — it composes on top of it.

## The problem

medspaCy's ConText component is a capable modifier-matching engine. By default, however, it leaves several clinically important problems unsolved:

1. **Taxonomy collapsed by default**: ConText exposes rich modifier categories (e.g. `POSSIBLE_EXISTENCE`, `NEGATED_EXISTENCE`) via `Span._.modifiers`, but the standard entity attributes flatten these to booleans (`is_negated`, `is_uncertain`). The distinction between *probable* and *definite* absence — clinically meaningful — is lost.
2. **No INDICATION category**: medspaCy classifies "rule out PE" as either negation or uncertainty depending on surrounding cues. This is a reasonable approximation but misses the semantic point: the clinician has committed to *neither* PE nor its absence and is actively investigating. cwyde adds `INDICATION` as a first-class category (¬K∧¬K¬) to model this correctly.
3. **No cross-modifier synthesis**: when multiple modifiers apply to the same entity (e.g. both `HISTORICAL` and `UNCERTAIN`), ConText correctly attaches both but does not synthesise them into a single assertion. Downstream code receives an unresolved list and must decide what to do.
4. **ConText is sentence-scoped by default**: medspaCy's sectionizer can propagate section-level attributes (e.g. marking all entities in a "Past Medical History" section as historical), but this requires explicit wiring between the two components. ConText alone does not cross sentence boundaries.

## The approach

Clinical context modifier categories are **modal operators**. Their interaction rules are logical entailments, not empirical patterns:

| Category | Modal reading (v0.3 Spohn OCF) |
|---|---|
| `DEFINITE_EXISTENCE` | τ_clinician(X) = +2 — firmly believed present |
| `PROBABLE_EXISTENCE` | τ_clinician(X) = +1 — probably believed present |
| `AMBIVALENT_EXISTENCE` | τ_clinician(X) = 0 — genuinely neutral |
| `PROBABLE_NEGATED_EXISTENCE` | τ_clinician(X) = −1 — probably believed absent |
| `DEFINITE_NEGATED_EXISTENCE` | τ_clinician(X) = −2 — firmly believed absent |
| `HISTORICAL` | B_clinician(P(X)) — believed to have been the case |
| `HYPOTHETICAL` | B_clinician(X) — believed in conditional context |
| `FAMILY` | B_clinician(X_family) — applies to family member |
| `INDICATION` | ¬K_clinician(X) ∧ ¬K_clinician(¬X) — under investigation |

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

### Development install (recommended for notebooks and research)

**Requires** conda or mamba ([Miniforge](https://github.com/conda-forge/miniforge) recommended).

```bash
# 1. Clone the repo
git clone https://github.com/chapmanbe/cwyde.git
cd cwyde

# 2. Create and activate the conda environment
conda env create -f environment.yml
conda activate cwyde

# 3. Install the three cwyde packages in editable mode
pip install -e packages/cwyde-knowledge
pip install -e packages/cwyde-haskell-bridge
pip install -e .
```

This installs medspaCy and all Python dependencies. The example notebooks
(`examples/01_basic_assertion.ipynb` through `04_section_propagation.ipynb`)
are fully functional at this point.

### Optional: gamen-validate (formal consistency checking)

Notebook 05 and the `cwyde_consistency_checker` pipeline component require
the `gamen-validate` binary from [gamen-hs](https://github.com/chapmanbe/gamen-hs).
This is a **Haskell** binary — Python-only environments work fine without it
(the pipeline falls back to the YAML precedence table).

**Requires** GHC ≥ 9.6, installed via [ghcup](https://www.haskell.org/ghcup/).

ghcup installs `cabal` and `ghc` into `~/.ghcup/bin`, which is not always
on `PATH` by default. Add it explicitly:

```bash
export PATH="$HOME/.ghcup/bin:$PATH"   # one-off
# or to make it permanent:
echo 'export PATH="$HOME/.ghcup/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
which cabal   # should resolve
```

```bash
# Clone and build — all cabal commands must run from the gamen-hs directory
git clone https://github.com/chapmanbe/gamen-hs.git
cd gamen-hs
cabal build gamen-validate

# Capture the binary path (still inside gamen-hs/)
export CWYDE_GAMEN_BIN=$(cabal list-bin gamen-validate)
```

`find_gamen_validate()` also checks `GAMEN_VALIDATE_BIN` (compatibility with
`guideline-validation`) and common build output paths before giving up.

### PyPI install (library use, no notebooks)

```bash
pip install cwyde cwyde-knowledge            # core
pip install cwyde cwyde-knowledge cwyde-haskell-bridge  # with bridge
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
