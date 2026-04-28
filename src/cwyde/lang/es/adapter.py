"""Spanish language plugin — v0.1 skeleton.

Provides one indication pattern ('se descarta') to exercise the multilingual
plugin architecture. Proves the abstraction is real, not aspirational.
Full Spanish lexicons are v0.2+ scope.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal


class SpanishPlugin:
    code = "es"
    spacy_model = "es_core_news_sm"

    def _data_root(self) -> Path:
        from cwyde_knowledge import data_root
        return data_root() / "lang" / "es"

    def lexicon_paths(self) -> list[Path]:
        lexicon_dir = self._data_root() / "lexicon"
        paths = list(lexicon_dir.glob("*.yaml"))
        return paths

    def indication_patterns(self) -> list[Path]:
        return [self._data_root() / "indication_patterns.yaml"]

    def backfill_patterns(self) -> list[Path]:
        return []

    def scope_direction_model(self) -> Literal["ltr", "rtl"]:
        return "ltr"

    def negation_typology(self) -> Literal["simple", "discontinuous"]:
        return "simple"

    def script_direction(self) -> Literal["ltr", "rtl"]:
        return "ltr"

    def preprocess(self, text: str) -> str:
        return text
