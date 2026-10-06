# cwyde: Claude Code instructions

Principled clinical assertion/context infrastructure for clinical NLP, in the
line of pyConTextNLP (retired) and medspaCy. Brian Chapman. Part of the Gamen
project family (`~/Code/CLAUDE.md`, `~/Projects/Logic/CLAUDE.md`). Origin:
planned on 2026-04-28 from `~/Code/Python/pyConTextNLP/docs/cwyde-proposal.md`;
read that for the design rationale.

## Layout (three-package monorepo)

- `src/cwyde/`: spaCy pipeline components (`components/`), modal formula
  dataclasses and the category-to-formula translator (`formal/`), public API
  (`classify_document`), `pipeline.py`.
- `packages/cwyde-knowledge/`: the YAML knowledge bases (categories,
  interaction rules, section assertions, lexicons, e.g.
  `src/cwyde_knowledge/data/lang/en/lexicon/pseudo_triggers.yaml`).
- `packages/cwyde-haskell-bridge/`: subprocess client for `gamen-validate`.
  The name is historical: the binary is now gamen-lean's (see below).
- `decisions/`: ADRs (template in `decisions/README.md`). `docs/`: design notes.

## Run and test

- Python 3.13, `.venv/` (or the `cwyde` conda env from `environment.yml`).
- `python -m pytest` runs `tests/` (unit, integration, reproducibility).
- The gamen integration tests need a `gamen-validate` binary. Without one they
  skip; **`pytest --require-gamen` makes a missing binary a failure** (use it
  before trusting a green run).
- Binary discovery, in order: `$CWYDE_GAMEN_BIN`, `$GAMEN_VALIDATE_BIN`,
  `PATH`. There is no fallback to a gamen-hs build. Install gamen-lean's binary
  with `tools/install.sh` in `~/Projects/Logic/gamen-lean`; it prints the
  value to export (normally `~/.local/share/gamen-lean/gamen-validate`).
- The suite has a known failure on both the Haskell and Lean binaries:
  `test_gamen_bridge.py::test_consistency_indication_with_existence`
  (`unsupported operator: Knowledge`): `Indication` expands to
  `¬K(φ) ∧ ¬K(¬φ)`, and the prover's `kdt+doxasticD` fragment has no
  `Knowledge`. Not yet resolved; don't paper over it.

## Design decisions (don't relitigate without Brian)

- **Scope is general clinical assertion context, not PE.** PE (peFinder,
  `pitt_reports`) is the evaluation test case. The test for what belongs in
  cwyde: "is this a general property of clinical assertion context?" PE-flavored
  logic in `classify_document()` is a smell; the principled form is a pluggable
  document-resolution policy with a generic default. Frame capability questions
  as "does cwyde give application authors what they need?", not "does cwyde do X?"
- **Describe medspaCy fairly.** Always "by default" or "out of the box", never
  "medspaCy can't". cwyde adds the named INDICATION category, cross-modifier
  synthesis, and section-propagation wiring; medspaCy has the pieces.
- **Existence axis is Spohn ranked belief** (v0.3): DEFINITE ±2, PROBABLE ±1,
  AMBIVALENT 0 as `RankedBelief("clinician", rank, x)`. HISTORICAL is
  `Belief("clinician", Past(x))`; FAMILY is a sortal atom; INDICATION is
  `Indication(x)`. The DEFINITE/PROBABLE threshold at N=2 is a cwyde policy
  choice, not something gamen decides.
- **Scope directions are not modal logic.** FORWARD/BACKWARD/BIDIRECTIONAL/
  TERMINATE are positional predicates over text. KB consistency checking
  works on the categories the scope algorithm outputs.
- **Atoms are canonicalized at the translator boundary**
  (`cwyde.formal.canonical.canonicalise_atom`): lowercase and underscores by
  default; lemmatization is opt-in.
- `classify_document` aggregates with Spohn combineIndependent (sum of ranks,
  clamped to [-2, +2]); `aggregation="max"` is available.

## Conventions

- American English in prose and comments.
- Domain knowledge lives in YAML, not code (Buchanan's separation principle).
  Fix a KB error in the YAML and add a regression test.
- A formula sent to `gamen-validate` uses the tree format (`modal.py` mirrors
  gamen's constructors) or the flat format; the protocol is gamen-lean's
  `Gamen/Protocol.lean`, byte-compatible with gamen-hs for these requests.
- `resources/`, `*.sqlite` and `*.db` are gitignored because they may hold real
  clinical text. Keep it that way. The evaluation data is
  `resources/pitt_reports.sqlite` (peFinder reports; 1-250 dev, >250 test).
- Some `__pycache__/*.pyc` files are tracked even though `.gitignore` excludes
  them (committed before the rule). Don't add more; a test run dirties them
  unless you use `PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider`.

## Related projects

gamen-lean (`~/Projects/Logic/gamen-lean`, the binary's source and the
primary implementation since 2026-09-29); gamen-hs (frozen); pyConTextNLP
(predecessor); guideline-validation (shares the JSON Lines protocol).
Application paper target: JBI.
