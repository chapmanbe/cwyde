"""
cwyde — formal semantics layer for clinical context classification.

Sits on top of medspaCy and provides:
  - Richer AssertionCategory taxonomy (DEFINITE vs PROBABLE, INDICATION as first-class)
  - Principled conflict resolution for co-occurring modifiers
  - Document-level section-context propagation
  - Optional formal consistency checking via gamen-hs
"""

from cwyde.version import __version__
from cwyde.categories import AssertionCategory

# Import component modules to trigger @Language.factory registration
import cwyde.components.category_mapper  # noqa: F401
import cwyde.components.indication_detector  # noqa: F401
import cwyde.components.conflict_resolver  # noqa: F401
import cwyde.components.section_propagator  # noqa: F401
import cwyde.components.consistency_checker  # noqa: F401

__all__ = ["__version__", "AssertionCategory", "load"]


def load(lang: str = "en"):
    """Return a medspaCy pipeline with all cwyde components added.

    Quick-start:
        import cwyde
        nlp = cwyde.load("en")
        doc = nlp("No evidence of pulmonary embolism.")
    """
    from cwyde.pipeline import build_pipeline
    return build_pipeline(lang=lang)
