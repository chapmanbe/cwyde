"""
Pydantic v2 models for all cwyde YAML knowledge-base schemas.

Every model uses extra="forbid" on top-level types so unknown keys fail loudly.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from cwyde.categories import AssertionCategory


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

class _StrictModel(BaseModel):
    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# categories.yaml
# ---------------------------------------------------------------------------

class CategoryDef(_StrictModel):
    category: AssertionCategory
    modal_reading: str
    modal_formula: str
    agent_scope: str | None = None
    axis: Literal["existence", "temporality", "experiencer", "epistemic"]
    description: str
    overrides: list[AssertionCategory] = Field(default_factory=list)


class CategoriesFile(_StrictModel):
    schema_version: int
    categories: list[CategoryDef]


# ---------------------------------------------------------------------------
# modal_mapping.yaml
# ---------------------------------------------------------------------------

class ModalMappingEntry(_StrictModel):
    category: AssertionCategory
    format: Literal["flat", "tree"]
    formula: dict[str, Any]


class ModalMappingFile(_StrictModel):
    schema_version: int
    mappings: list[ModalMappingEntry]


# ---------------------------------------------------------------------------
# medspacy_category_map.yaml
# ---------------------------------------------------------------------------

class MedSpaCyCategoryEntry(_StrictModel):
    medspacy_category: str
    cwyde_category: AssertionCategory


class MedSpaCyCategoryMapFile(_StrictModel):
    schema_version: int
    mappings: list[MedSpaCyCategoryEntry]
    unmapped_default: AssertionCategory


# ---------------------------------------------------------------------------
# interaction_rules.yaml
# ---------------------------------------------------------------------------

class OverrideEntry(_StrictModel):
    modifiers: list[AssertionCategory]
    result: AssertionCategory
    submit_to_gamen: bool = False
    rationale: str = ""


class InteractionRulesFile(_StrictModel):
    schema_version: int
    precedence: list[AssertionCategory]
    overrides: list[OverrideEntry]
    unresolvable: list[list[AssertionCategory]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# section_assertions.yaml
# ---------------------------------------------------------------------------

class SectionAssertionEntry(_StrictModel):
    applies: AssertionCategory
    propagate_to_children: bool = True
    override_existing: bool = False


class SectionAssertionsFile(_StrictModel):
    schema_version: int
    section_assertions: dict[str, SectionAssertionEntry]


# ---------------------------------------------------------------------------
# fallback_table.yaml
# ---------------------------------------------------------------------------

class FallbackTableFile(_StrictModel):
    schema_version: int
    rules: list[OverrideEntry]


# ---------------------------------------------------------------------------
# Lexicon entry (shared across all lang/*/lexicon/*.yaml files)
# ---------------------------------------------------------------------------

class LexiconEntry(_StrictModel):
    lex: str
    # YAML parses bare 'no'/'yes' as booleans; coerce to str defensively
    model_config = {"extra": "forbid", "coerce_numbers_to_str": False}
    regex: str | None = None
    direction: Literal["forward", "backward", "bidirectional", "terminate"]
    category: AssertionCategory
    modal_override: dict[str, Any] | None = None
    notes: str = ""
    source: str = ""


class LexiconFile(_StrictModel):
    schema_version: int
    entries: list[LexiconEntry]


# ---------------------------------------------------------------------------
# indication_patterns.yaml / backfill_patterns.yaml
# ---------------------------------------------------------------------------

class PatternEntry(_StrictModel):
    pattern: str
    description: str = ""


class PatternFile(_StrictModel):
    schema_version: int
    patterns: list[PatternEntry]


# ---------------------------------------------------------------------------
# Language plugin config (lang/*/plugin.yaml)
# ---------------------------------------------------------------------------

class ReproCase(_StrictModel):
    text: str
    target: str
    expected_category: AssertionCategory
    note: str = ""


class ReproCasesFile(_StrictModel):
    schema_version: int
    source: str = ""
    cases: list[ReproCase]


# ---------------------------------------------------------------------------


class LanguagePluginConfig(_StrictModel):
    schema_version: int
    code: str
    spacy_model: str
    lexicon_paths: list[str]
    indication_patterns: list[str]
    backfill_patterns: list[str]
    scope_direction_model: Literal["ltr", "rtl"] = "ltr"
    negation_typology: Literal["simple", "discontinuous"] = "simple"
    script_direction: Literal["ltr", "rtl"] = "ltr"
