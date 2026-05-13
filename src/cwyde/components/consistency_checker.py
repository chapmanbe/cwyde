"""
cwyde_consistency_checker — formal consistency checking via gamen-hs.

Two passes:
  1. Per-entity well-formedness — sets ent._.cwyde_consistent.
     A single well-formed formula is trivially satisfiable, so this only
     catches malformed formulas, not semantic contradictions.
  2. Joint satisfiability over a group of entities (the meaningful check).
     Default grouping is by section: entities in the same section are
     submitted to the reasoner as a conjunction. `grouping="document"`
     groups every entity in the doc together; useful for unsectioned docs.

Inconsistencies are reported in doc._.cwyde_inconsistencies as a list of
group-level records (scope, scope_id, implicated entities, formulas, explanation).

Runs last in the cwyde pipeline (after section_propagator). Skipped entirely
when no reasoner is available and skip_if_unavailable=True (the default).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from spacy.language import Language
from spacy.tokens import Doc

logger = logging.getLogger(__name__)

_VALID_GROUPINGS = ("section", "document")


@dataclass
class Inconsistency:
    scope: str                                          # "section" | "document"
    scope_id: str                                       # section category or "<document>"
    entities: list[tuple[str, int, int]]                # (text, start, end) per implicated entity
    formulas: list[dict] = field(default_factory=list)  # tree-JSON per formula in the group
    explanation: str = ""


@Language.factory(
    "cwyde_consistency_checker",
    default_config={"strategy": None, "skip_if_unavailable": True, "grouping": "section"},
)
def create_consistency_checker(nlp: Language, name: str, strategy, skip_if_unavailable: bool, grouping: str):
    return ConsistencyCheckerComponent(
        strategy=strategy, skip_if_unavailable=skip_if_unavailable, grouping=grouping,
    )


class ConsistencyCheckerComponent:
    def __init__(self, strategy=None, skip_if_unavailable: bool = True, grouping: str = "section"):
        if grouping not in _VALID_GROUPINGS:
            raise ValueError(f"grouping must be one of {_VALID_GROUPINGS}, got {grouping!r}")
        self._strategy = strategy
        self._skip_if_unavailable = skip_if_unavailable
        self._grouping = grouping

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

        # Pass 1: per-entity well-formedness. A single formula is trivially
        # satisfiable in the modal logics gamen-hs implements, so a False here
        # indicates a malformed formula (translator bug or upstream corruption).
        for ent in doc.ents:
            formula = ent._.cwyde_modal_formula
            if formula is None:
                ent._.cwyde_consistent = None
                continue
            try:
                result = self._strategy.check_consistency([formula])
                ent._.cwyde_consistent = result.consistent
            except Exception as exc:
                logger.warning("Well-formedness check failed for %r: %s", ent.text, exc)
                ent._.cwyde_consistent = None

        # Pass 2: joint satisfiability per group.
        inconsistencies: list[Inconsistency] = []
        groups = self._build_groups(doc)

        for scope, scope_id, group_ents in groups:
            paired = [
                (ent, ent._.cwyde_modal_formula)
                for ent in group_ents
                if ent._.cwyde_modal_formula is not None
            ]
            if len(paired) < 2:
                # Single formulas were already checked in pass 1; a group of 0 or 1
                # cannot exhibit a joint contradiction.
                continue

            formulas = [f for _, f in paired]
            try:
                result = self._strategy.check_consistency(formulas)
            except Exception as exc:
                logger.warning("Joint consistency check failed for %s/%s: %s", scope, scope_id, exc)
                continue

            if result.consistent is False:
                inconsistencies.append(Inconsistency(
                    scope=scope,
                    scope_id=scope_id,
                    entities=[(e.text, e.start, e.end) for e, _ in paired],
                    formulas=[f.to_tree_json() for _, f in paired],
                    explanation=result.explanation,
                ))

        doc._.cwyde_inconsistencies = inconsistencies
        return doc

    def _build_groups(self, doc: Doc) -> list[tuple[str, str, list]]:
        """Return [(scope, scope_id, entities), ...] for joint checking.

        grouping="document" → single ('document', '<document>', all entities) group.
        grouping="section"  → one group per section (innermost wins on nesting);
                              entities outside any section bucket under '<document>'.
        """
        if self._grouping == "document":
            return [("document", "<document>", list(doc.ents))]

        sections = getattr(doc._, "sections", None) or []
        section_spans = []
        for section in sections:
            category = getattr(section, "category", None)
            body_span = getattr(section, "body_span", None)
            if category is None or body_span is None:
                continue
            section_spans.append((category, body_span[0], body_span[1]))

        section_buckets: dict[str, list] = {}
        document_bucket: list = []

        for ent in doc.ents:
            # Innermost containing section = smallest span that contains ent.start.
            # Sequential (non-nested) sections are correctly disambiguated by the
            # `start <= ent.start < end` predicate.
            candidates = [
                (cat, start, end)
                for cat, start, end in section_spans
                if start <= ent.start < end
            ]
            if not candidates:
                document_bucket.append(ent)
                continue
            innermost = min(candidates, key=lambda s: s[2] - s[1])
            section_buckets.setdefault(innermost[0], []).append(ent)

        groups: list[tuple[str, str, list]] = [
            ("section", cat, ents) for cat, ents in section_buckets.items()
        ]
        if document_bucket:
            groups.append(("document", "<document>", document_bucket))
        return groups
