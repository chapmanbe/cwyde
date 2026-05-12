"""
cwyde_category_mapper — reads ent._.modifiers from medspaCy ConText and maps
to cwyde AssertionCategory via the medspacy_category_map.yaml table.

Runs first in the cwyde pipeline, before all other cwyde components.
"""

from __future__ import annotations

import logging
from typing import Any

from spacy.language import Language
from spacy.tokens import Doc

from cwyde.categories import AssertionCategory
from cwyde.formal.translator import category_to_formula

logger = logging.getLogger(__name__)


@Language.factory(
    "cwyde_category_mapper",
    default_config={"category_map": None},
)
def create_category_mapper(nlp: Language, name: str, category_map):
    return CategoryMapperComponent(category_map=category_map)


class CategoryMapperComponent:
    def __init__(self, category_map=None):
        self._map = category_map  # MedSpaCyCategoryMapFile, injected or loaded lazily

    def _ensure_map(self):
        if self._map is None:
            from cwyde_knowledge import default_medspacy_category_map
            self._map = default_medspacy_category_map()

    def __call__(self, doc: Doc) -> Doc:
        self._ensure_map()
        lookup = {e.medspacy_category: e.cwyde_category for e in self._map.mappings}
        default = self._map.unmapped_default

        doc_agent = doc._.cwyde_author or "clinician"

        for ent in doc.ents:
            ent._.cwyde_belief_agent = doc_agent
            modifiers = getattr(ent._, "modifiers", None) or []
            if not modifiers:
                ent._.cwyde_assertion_category = AssertionCategory.DEFINITE_EXISTENCE
                ent._.cwyde_modal_formula = category_to_formula(
                    AssertionCategory.DEFINITE_EXISTENCE, ent.text, agent=doc_agent
                )
                ent._.cwyde_resolution_trace = [
                    {"step": "category_mapper", "result": AssertionCategory.DEFINITE_EXISTENCE, "reason": "no modifiers"}
                ]
                continue

            categories = []
            trace = []
            for mod in modifiers:
                medspacy_cat = getattr(mod, "category", str(mod))
                cwyde_cat = lookup.get(medspacy_cat)
                if cwyde_cat is None:
                    logger.warning("Unknown medspaCy category %r; defaulting to %s", medspacy_cat, default)
                    cwyde_cat = default
                categories.append(cwyde_cat)
                trace.append({"step": "category_mapper", "medspacy": medspacy_cat, "cwyde": cwyde_cat})

            if len(categories) == 1:
                final = categories[0]
            else:
                final = AssertionCategory.UNRESOLVED  # conflict_resolver handles multi-modifier

            ent._.cwyde_assertion_category = final
            ent._.cwyde_modal_formula = (
                category_to_formula(final, ent.text, agent=doc_agent)
                if final != AssertionCategory.UNRESOLVED else None
            )
            ent._.cwyde_resolution_trace = trace

        return doc
