"""
cwyde_consistency_checker — optional formal consistency checking via gamen-hs.

For each entity, submits the modal formula to gamen-validate and populates:
  ent._.cwyde_consistent     (True / False / None)
  doc._.cwyde_inconsistencies

Skipped entirely when no gamen bridge is configured and no GamenStrategy is available.
Runs last in the cwyde pipeline (after section_propagator).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from spacy.language import Language
from spacy.tokens import Doc

logger = logging.getLogger(__name__)


@dataclass
class Inconsistency:
    entity_text: str
    entity_start: int
    entity_end: int
    formula_json: dict
    explanation: str


@Language.factory(
    "cwyde_consistency_checker",
    default_config={"strategy": None, "skip_if_unavailable": True},
)
def create_consistency_checker(nlp: Language, name: str, strategy, skip_if_unavailable: bool):
    return ConsistencyCheckerComponent(strategy=strategy, skip_if_unavailable=skip_if_unavailable)


class ConsistencyCheckerComponent:
    def __init__(self, strategy=None, skip_if_unavailable: bool = True):
        self._strategy = strategy
        self._skip_if_unavailable = skip_if_unavailable

    def _ensure_strategy(self):
        if self._strategy is None:
            from cwyde.formal.strategy import default_strategy
            self._strategy = default_strategy()

    def __call__(self, doc: Doc) -> Doc:
        self._ensure_strategy()

        if not self._strategy.is_available():
            if not self._skip_if_unavailable:
                raise RuntimeError("cwyde_consistency_checker: no reasoner available")
            return doc

        inconsistencies: list[Inconsistency] = []

        for ent in doc.ents:
            formula = ent._.cwyde_modal_formula
            if formula is None:
                ent._.cwyde_consistent = None
                continue

            try:
                result = self._strategy.check_consistency([formula])
                ent._.cwyde_consistent = result.consistent
                if result.consistent is False:
                    inconsistencies.append(Inconsistency(
                        entity_text=ent.text,
                        entity_start=ent.start,
                        entity_end=ent.end,
                        formula_json=formula.to_tree_json(),
                        explanation=result.explanation,
                    ))
            except Exception as exc:
                logger.warning("Consistency check failed for %r: %s", ent.text, exc)
                ent._.cwyde_consistent = None

        doc._.cwyde_inconsistencies = inconsistencies
        return doc
