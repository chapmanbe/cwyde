"""
YAML knowledge-base loader following Buchanan's separation principle.

All loaders follow the pattern from patient-agent-assistant/src/patient_agent/kg_rules.py:
    raw = yaml.safe_load(path.read_text())
    return Model.model_validate(raw)
"""

from __future__ import annotations

from pathlib import Path
import yaml

from cwyde.exceptions import KBValidationError
from cwyde.models import (
    CategoriesFile,
    FallbackTableFile,
    InteractionRulesFile,
    LanguagePluginConfig,
    LexiconFile,
    MedSpaCyCategoryMapFile,
    ModalMappingFile,
    PatternFile,
    ReproCasesFile,
    SectionAssertionsFile,
)


def _load(path: Path, model):
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return model.model_validate(raw)
    except Exception as exc:
        raise KBValidationError(f"Failed to load {path}: {exc}") from exc


def load_categories(path: Path) -> CategoriesFile:
    return _load(path, CategoriesFile)


def load_modal_mapping(path: Path) -> ModalMappingFile:
    return _load(path, ModalMappingFile)


def load_medspacy_category_map(path: Path) -> MedSpaCyCategoryMapFile:
    return _load(path, MedSpaCyCategoryMapFile)


def load_interaction_rules(path: Path) -> InteractionRulesFile:
    return _load(path, InteractionRulesFile)


def load_section_assertions(path: Path) -> SectionAssertionsFile:
    return _load(path, SectionAssertionsFile)


def load_fallback_table(path: Path) -> FallbackTableFile:
    return _load(path, FallbackTableFile)


def load_lexicon(path: Path) -> LexiconFile:
    return _load(path, LexiconFile)


def load_patterns(path: Path) -> PatternFile:
    return _load(path, PatternFile)


def load_language_plugin_config(path: Path) -> LanguagePluginConfig:
    return _load(path, LanguagePluginConfig)


def load_repro_cases(path: Path) -> ReproCasesFile:
    return _load(path, ReproCasesFile)
