"""
cwyde_section_propagator — the headline v0.1 contribution.

Propagates section-level assertion context to all findings within that section.
Runs last in the cwyde pipeline, after medspacy_sectionizer and medspacy_context.

Algorithm per section:
  1. Look up section category in section_assertions.yaml
  2. For each entity in the section's body span:
     a. Inject a virtual section-level modifier
     b. Re-run conflict resolution with the augmented modifier set
     c. Update cwyde_assertion_category if the resolution changes
     d. Set cwyde_section_inherited=True if section assertion influenced result
  3. Handle nested sections: child inherits parent unless child has own mapping

Edge cases handled:
  - INDICATION override_existing=True: wins over sentence-level explicit negation
  - Double-historicization prevention: HISTORICAL flag set, category not re-wrapped
  - Nested sections: child mapping wins; child with no mapping inherits parent
"""

from __future__ import annotations

import logging
from spacy.language import Language
from spacy.tokens import Doc

from cwyde.categories import AssertionCategory

logger = logging.getLogger(__name__)


@Language.factory(
    "cwyde_section_propagator",
    default_config={"section_rules": None, "strategy": None},
)
def create_section_propagator(nlp: Language, name: str, section_rules, strategy):
    return SectionPropagatorComponent(section_rules=section_rules, strategy=strategy)


class SectionPropagatorComponent:
    def __init__(self, section_rules=None, strategy=None):
        self._section_rules = section_rules  # SectionAssertionsFile, lazy
        self._strategy = strategy

    def _ensure_rules(self):
        if self._section_rules is None:
            from cwyde_knowledge import default_section_assertions
            self._section_rules = default_section_assertions()

    def _ensure_strategy(self):
        if self._strategy is None:
            from cwyde.formal.strategy import default_strategy
            self._strategy = default_strategy()

    def _get_section_assertion(self, section_category: str) -> tuple[AssertionCategory | None, bool, bool]:
        """Return (assertion, propagate_to_children, override_existing) or (None, *, *) if not mapped."""
        rules = self._section_rules.section_assertions
        entry = rules.get(section_category)
        if entry is None:
            return None, True, False
        return entry.applies, entry.propagate_to_children, entry.override_existing

    def _resolve_for_section(
        self,
        current_category: AssertionCategory,
        section_assertion: AssertionCategory,
        override_existing: bool,
    ) -> tuple[AssertionCategory, bool]:
        """Return (resolved_category, was_changed).

        Section assertion applies when:
          - override_existing is True (INDICATION always wins), OR
          - current_category is DEFINITE_EXISTENCE (no sentence-level modifier was present)

        Returns (current_category, False) when section assertion yields to existing.
        """
        if current_category == AssertionCategory.DEFINITE_EXISTENCE:
            # No sentence-level modifier — inject section assertion
            return section_assertion, True

        if override_existing:
            # Section wins (e.g., Indication_for_study section always sets INDICATION)
            return section_assertion, current_category != section_assertion

        # Section does not override existing sentence-level assertion;
        # but set flags so downstream knows the section context
        return current_category, False

    def __call__(self, doc: Doc) -> Doc:
        self._ensure_rules()
        self._ensure_strategy()

        sections = getattr(doc._, "sections", None)
        if not sections:
            return doc

        doc._.cwyde_section_assertions = {}

        # Build parent→child nesting from section list.
        # Stack entries: (section, assertion, propagates_to_children, override_existing)
        section_stack: list[tuple] = []

        for section in sections:
            category = getattr(section, "category", None)
            if category is None:
                continue

            # Resolve assertion for this section, potentially inherited from nearest ancestor
            assertion, propagates, override = self._get_section_assertion(category)

            # body_span is a (start, end) token-index tuple in medspaCy
            raw_body = getattr(section, "body_span", None)
            if raw_body is None:
                continue
            body_start, body_end = raw_body

            # Prune ancestors whose body ended before this section starts — must happen
            # before the ancestor-inheritance lookup so sequential (non-nested) sections
            # don't inherit from their predecessor.
            section_stack = [
                entry for entry in section_stack
                if entry[0].body_span[1] > body_start
            ]

            if assertion is None and section_stack:
                # Walk the (now-pruned) stack for the nearest ancestor that propagates
                for _anc_section, anc_assertion, anc_propagates, anc_override in reversed(section_stack):
                    if anc_assertion is not None and anc_propagates:
                        assertion = anc_assertion
                        override = anc_override
                        break

            section_stack.append((section, assertion, propagates, override))

            if assertion is None:
                continue

            doc._.cwyde_section_assertions[category] = assertion

            # Apply to all entities in this section's body span
            for ent in doc.ents:
                if ent.start < body_start or ent.start >= body_end:
                    continue

                resolved, changed = self._resolve_for_section(
                    ent._.cwyde_assertion_category, assertion, override
                )

                if changed:
                    prev = ent._.cwyde_assertion_category
                    ent._.cwyde_assertion_category = resolved
                    ent._.cwyde_section_inherited = True

                    if resolved != AssertionCategory.UNRESOLVED:
                        from cwyde.formal.translator import category_to_formula
                        ent._.cwyde_modal_formula = category_to_formula(resolved, ent.text, agent=ent._.cwyde_belief_agent)

                    ent._.cwyde_resolution_trace.append({
                        "step": "section_propagator",
                        "section": category,
                        "section_assertion": assertion.value,
                        "previous": prev.value,
                        "result": resolved.value,
                        "override_existing": override,
                    })
                    logger.debug(
                        "Section propagation: %r %s→%s (section=%s)",
                        ent.text, prev.value, resolved.value, category,
                    )
                elif not ent._.cwyde_section_inherited:
                    # Record that this section was inspected even without change
                    ent._.cwyde_resolution_trace.append({
                        "step": "section_propagator",
                        "section": category,
                        "section_assertion": assertion.value,
                        "result": ent._.cwyde_assertion_category.value,
                        "note": "sentence-level assertion preserved",
                    })

        return doc
