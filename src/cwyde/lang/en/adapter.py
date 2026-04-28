"""English language plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Literal


class EnglishPlugin:
    code = "en"
    spacy_model = "en_core_web_sm"

    def _data_root(self) -> Path:
        from cwyde_knowledge import data_root
        return data_root() / "lang" / "en"

    def lexicon_paths(self) -> list[Path]:
        return list((self._data_root() / "lexicon").glob("*.yaml"))

    def indication_patterns(self) -> list[Path]:
        return [self._data_root() / "indication_patterns.yaml"]

    def backfill_patterns(self) -> list[Path]:
        return [self._data_root() / "backfill_patterns.yaml"]

    def scope_direction_model(self) -> Literal["ltr", "rtl"]:
        return "ltr"

    def negation_typology(self) -> Literal["simple", "discontinuous"]:
        return "simple"

    def script_direction(self) -> Literal["ltr", "rtl"]:
        return "ltr"

    def preprocess(self, text: str) -> str:
        return text
