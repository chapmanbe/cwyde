"""
Pipeline integration — add cwyde components to a medspaCy pipeline.

Component ordering:
  medspacy_context → medspacy_sectionizer
  then:
    cwyde_category_mapper
    cwyde_indication_detector
    cwyde_conflict_resolver
    cwyde_section_propagator   ← headline contribution; must run after sectionizer
    cwyde_consistency_checker  ← optional; skipped when gamen unavailable
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)


def add_to(nlp, *, lang: str = "en", skip_consistency: bool = False) -> None:
    """Add all cwyde components to an existing medspaCy pipeline.

    Also loads cwyde-knowledge lexicons into medspaCy's ConText component,
    supplementing the default rules with domain-specific clinical modifiers.

    Idempotent for repeated calls — checks for existing components before adding.
    """
    from cwyde.extensions import register_extensions

    register_extensions()

    # Ensure medspacy_sectionizer exists before cwyde components
    if "medspacy_sectionizer" not in nlp.pipe_names and "sectionizer" not in nlp.pipe_names:
        logger.warning(
            "medspacy_sectionizer not found in pipeline; section_propagator will have no sections to process. "
            "Add medspacy's sectionizer before calling cwyde.pipeline.add_to()."
        )

    # Seed medspaCy's ConText with cwyde-knowledge lexicons for this language
    _load_lexicons_into_context(nlp, lang)

    _add_if_missing(nlp, "cwyde_category_mapper", config={})
    _add_if_missing(nlp, "cwyde_indication_detector", config={"lang": lang})
    _add_if_missing(nlp, "cwyde_conflict_resolver", config={})
    _add_if_missing(nlp, "cwyde_section_propagator", config={})

    if not skip_consistency:
        _add_if_missing(nlp, "cwyde_consistency_checker", config={"skip_if_unavailable": True})


def _load_lexicons_into_context(nlp, lang: str) -> None:
    """Load cwyde-knowledge lexicon entries into medspaCy's ConText component."""
    context_pipe = None
    for name in ("medspacy_context", "context"):
        if name in nlp.pipe_names:
            context_pipe = nlp.get_pipe(name)
            break
    if context_pipe is None:
        logger.warning("No medspaCy ConText component found; skipping lexicon load.")
        return

    try:
        from medspacy.context import ConTextRule
        from cwyde.lang.registry import get_plugin
        from cwyde.kb import load_lexicon

        plugin = get_plugin(lang)
        rules = []
        for lex_path in plugin.lexicon_paths():
            try:
                lexicon = load_lexicon(lex_path)
                for entry in lexicon.entries:
                    if entry.direction == "terminate":
                        continue  # terminate handled separately
                    rule = ConTextRule(
                        literal=entry.lex,
                        category=entry.category.value,
                        direction=entry.direction.upper(),
                        pattern=entry.regex or None,
                    )
                    rules.append(rule)
            except Exception as exc:
                logger.warning("Failed to load lexicon %s: %s", lex_path, exc)

        if rules:
            context_pipe.add(rules)
            logger.debug("Loaded %d ConText rules from cwyde-knowledge (%s)", len(rules), lang)
    except Exception as exc:
        logger.warning("Could not load cwyde lexicons into ConText: %s", exc)


def _add_if_missing(nlp, name: str, config: dict) -> None:
    if name not in nlp.pipe_names:
        nlp.add_pipe(name, config=config)


def build_pipeline(lang: str = "en"):
    """Build and return a full medspaCy + cwyde pipeline.

    For quick-start use: `import cwyde; nlp = cwyde.load("en")`
    """
    import medspacy

    nlp = medspacy.load(enable=["sectionizer", "context"])
    add_to(nlp, lang=lang)
    return nlp
