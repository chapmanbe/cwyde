"""
cwyde_conflict_resolver — resolves co-occurring modifiers on a single entity.

When category_mapper sets UNRESOLVED (multiple modifiers), this component
applies interaction_rules.yaml to determine the final AssertionCategory.
Entities flagged submit_to_gamen=True are passed to consistency_checker.

Runs third in the cwyde pipeline.
"""

from __future__ import annotations

import logging

from spacy.language import Language
from spacy.tokens import Doc

from cwyde.categories import AssertionCategory
from cwyde.formal.strategy import ReasonerStrategy

logger = logging.getLogger(__name__)


@Language.factory(
    "cwyde_conflict_resolver",
    default_config={"strategy": None, "rules": None},
)
def create_conflict_resolver(nlp: Language, name: str, strategy, rules):
    return ConflictResolverComponent(strategy=strategy, rules=rules)


class ConflictResolverComponent:
    def __init__(self, strategy: ReasonerStrategy | None = None, rules=None):
        self._strategy = strategy
        self._rules = rules

    def _ensure_strategy(self):
        if self._strategy is None:
            from cwyde.formal.strategy import default_strategy
            self._strategy = default_strategy()

    def __call__(self, doc: Doc) -> Doc:
        self._ensure_strategy()

        for ent in doc.ents:
            if ent._.cwyde_assertion_category != AssertionCategory.UNRESOLVED:
                continue

            # Recover the list of per-modifier categories from the trace
            categories = [
                t["cwyde"]
                for t in ent._.cwyde_resolution_trace
                if t.get("step") == "category_mapper" and "cwyde" in t
            ]

            if not categories:
                logger.warning("UNRESOLVED entity %r has no trace categories; leaving UNRESOLVED", ent.text)
                continue

            result = self._strategy.resolve_conflict(categories)
            ent._.cwyde_assertion_category = result
            if result != AssertionCategory.UNRESOLVED:
                from cwyde.formal.translator import category_to_formula
                ent._.cwyde_modal_formula = category_to_formula(result, ent.text)
            ent._.cwyde_resolution_trace.append(
                {"step": "conflict_resolver", "input": [c.value for c in categories], "result": result.value}
            )

        return doc
