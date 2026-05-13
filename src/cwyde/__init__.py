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
from cwyde.models import DocumentClassification, EntityEvidence

# Import component modules to trigger @Language.factory registration
import cwyde.components.category_mapper  # noqa: F401
import cwyde.components.indication_detector  # noqa: F401
import cwyde.components.conflict_resolver  # noqa: F401
import cwyde.components.section_propagator  # noqa: F401
import cwyde.components.consistency_checker  # noqa: F401

__all__ = [
    "__version__",
    "AssertionCategory",
    "DocumentClassification",
    "EntityEvidence",
    "classify_document",
    "load",
]

# Rank map for Spohn's combineIndependent (Σ τᵢ).
# Categories without a numeric rank (HISTORICAL, HYPOTHETICAL, FAMILY,
# INDICATION, UNRESOLVED) return None — they contribute acuity/confidence
# information but not a numeric τ vote.
_RANK: dict[AssertionCategory, int] = {
    AssertionCategory.DEFINITE_EXISTENCE: 2,
    AssertionCategory.PROBABLE_EXISTENCE: 1,
    AssertionCategory.AMBIVALENT_EXISTENCE: 0,
    AssertionCategory.PROBABLE_NEGATED_EXISTENCE: -1,
    AssertionCategory.DEFINITE_NEGATED_EXISTENCE: -2,
}

_TAU_TO_CATEGORY: dict[int, AssertionCategory] = {
    2: AssertionCategory.DEFINITE_EXISTENCE,
    1: AssertionCategory.PROBABLE_EXISTENCE,
    0: AssertionCategory.AMBIVALENT_EXISTENCE,
    -1: AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
    -2: AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
}


def classify_document(
    doc,
    target_type: str,
    *,
    aggregation: str = "combine_independent",
) -> "DocumentClassification":
    """Aggregate entity-level assertions into a document-level classification.

    Uses Spohn's combineIndependent (Σ τᵢ) by default, clamped to [-2, +2].
    ``target_type`` filters entities by label (case-insensitive); pass an empty
    string or ``None`` to include all entities.

    Parameters
    ----------
    doc:
        A spaCy Doc with ``_.cwyde_assertion_category`` set on each entity.
    target_type:
        Entity label to filter on (e.g. ``"pe"``, ``"CONDITION"``).
        Case-insensitive. Pass ``""`` or ``None`` to include all entities.
    aggregation:
        ``"combine_independent"`` (default): Σ τᵢ clamped to [-2, +2].
        ``"max"``: max(τᵢ).
    """
    # Filter entities by label
    if target_type:
        ents = [e for e in doc.ents if e.label_.lower() == target_type.lower()]
    else:
        ents = list(doc.ents)

    # No matching entities → default ambivalent, unknown acuity
    if not ents:
        return DocumentClassification(
            target_type=target_type or "",
            tau_combined=0,
            assertion=AssertionCategory.AMBIVALENT_EXISTENCE,
            acuity="unknown",
            evidence=[],
            confidence=1.0,
        )

    evidence: list[EntityEvidence] = []
    resolved_count = 0

    for ent in ents:
        cat = ent._.cwyde_assertion_category
        tau = _RANK.get(cat)  # None for HISTORICAL, HYPOTHETICAL, etc.
        evidence.append(EntityEvidence(mention=ent.text, category=cat, tau=tau))
        if cat != AssertionCategory.UNRESOLVED:
            resolved_count += 1

    confidence = resolved_count / len(ents)

    # Acuity: first HISTORICAL wins, then HYPOTHETICAL, then "acute"
    categories = {ev.category for ev in evidence}
    if AssertionCategory.HISTORICAL in categories:
        acuity = "historical"
    elif AssertionCategory.HYPOTHETICAL in categories:
        acuity = "hypothetical"
    else:
        acuity = "acute"

    # Collect numeric τ values
    ranks = [ev.tau for ev in evidence if ev.tau is not None]

    if not ranks:
        tau_combined = 0
    elif aggregation == "max":
        tau_combined = max(ranks)
    else:
        # combine_independent: Σ τᵢ clamped to [-2, +2]
        tau_combined = max(-2, min(2, sum(ranks)))

    assertion = _TAU_TO_CATEGORY[tau_combined]

    return DocumentClassification(
        target_type=target_type or "",
        tau_combined=tau_combined,
        assertion=assertion,
        acuity=acuity,
        evidence=evidence,
        confidence=confidence,
    )


def load(lang: str = "en"):
    """Return a medspaCy pipeline with all cwyde components added.

    Quick-start:
        import cwyde
        nlp = cwyde.load("en")
        doc = nlp("No evidence of pulmonary embolism.")
    """
    from cwyde.pipeline import build_pipeline
    return build_pipeline(lang=lang)
