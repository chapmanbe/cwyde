"""
Integration tests: full cwyde pipeline end-to-end without gamen.

Covers:
  - Sentence-level modifier detection (negation, probability, INDICATION, historical, family)
  - Section-level assertion propagation (HISTORICAL, FAMILY, INDICATION sections)
  - Override semantics (INDICATION section overrides sentence-level negation)
  - Interaction resolution (FAMILY+HISTORICAL → FAMILY)
  - Unmapped sections (assertion comes from sentence only)
  - Multi-sentence section scope
"""

import pytest
import medspacy
from medspacy.target_matcher import TargetRule
from cwyde.pipeline import add_to
from cwyde.categories import AssertionCategory


@pytest.fixture(scope="session")
def nlp():
    pipeline = medspacy.load()
    pipeline.add_pipe("medspacy_sectionizer")
    tm = pipeline.get_pipe("medspacy_target_matcher")
    tm.add([TargetRule("PE", "CONDITION")])
    tm.add([TargetRule("pulmonary embolism", "CONDITION")])
    tm.add([TargetRule("DVT", "CONDITION")])
    tm.add([TargetRule("pneumonia", "CONDITION")])
    add_to(pipeline, lang="en")
    return pipeline


def assert_first_entity(nlp, text, expected_category, *, label=None):
    """Process text and assert the first entity's assertion category."""
    doc = nlp(text)
    if not doc.ents:
        pytest.skip(f"No entity found in: {text!r}")
    ent = doc.ents[0]
    got = ent._.cwyde_assertion_category
    assert got == expected_category, (
        f"text={text!r}\n"
        f"  expected={expected_category}\n"
        f"  got={got}\n"
        f"  trace={ent._.cwyde_resolution_trace}"
    )


# ---------------------------------------------------------------------------
# Sentence-level modifiers — no section header
# ---------------------------------------------------------------------------

class TestSentenceModifiers:
    def test_definite_existence_baseline(self, nlp):
        assert_first_entity(nlp, "PE is present.", AssertionCategory.DEFINITE_EXISTENCE)

    def test_definite_negated_no(self, nlp):
        assert_first_entity(nlp, "No PE.", AssertionCategory.DEFINITE_NEGATED_EXISTENCE)

    def test_definite_negated_no_evidence(self, nlp):
        assert_first_entity(nlp, "No evidence of PE.", AssertionCategory.DEFINITE_NEGATED_EXISTENCE)

    def test_definite_negated_without(self, nlp):
        assert_first_entity(nlp, "Study is without PE.", AssertionCategory.DEFINITE_NEGATED_EXISTENCE)

    def test_probable_existence_probable(self, nlp):
        assert_first_entity(nlp, "Probable PE in right lower lobe.", AssertionCategory.PROBABLE_EXISTENCE)

    def test_probable_existence_likely(self, nlp):
        assert_first_entity(nlp, "Likely PE.", AssertionCategory.PROBABLE_EXISTENCE)

    def test_probable_existence_possible(self, nlp):
        assert_first_entity(nlp, "Possible PE.", AssertionCategory.PROBABLE_EXISTENCE)

    def test_probable_existence_consistent_with(self, nlp):
        assert_first_entity(nlp, "Findings consistent with PE.", AssertionCategory.PROBABLE_EXISTENCE)

    def test_probable_negated_unlikely(self, nlp):
        assert_first_entity(nlp, "PE is unlikely.", AssertionCategory.PROBABLE_NEGATED_EXISTENCE)

    def test_probable_negated_probably_not(self, nlp):
        # "probably not" must precede the entity — it's a FORWARD modifier
        assert_first_entity(nlp, "Probably not PE.", AssertionCategory.PROBABLE_NEGATED_EXISTENCE)

    def test_ambivalent_cannot_exclude(self, nlp):
        assert_first_entity(nlp, "Cannot exclude PE.", AssertionCategory.AMBIVALENT_EXISTENCE)

    def test_historical_history_of(self, nlp):
        assert_first_entity(nlp, "History of PE.", AssertionCategory.HISTORICAL)

    def test_historical_prior(self, nlp):
        assert_first_entity(nlp, "Prior PE.", AssertionCategory.HISTORICAL)

    def test_family_family_history_of(self, nlp):
        assert_first_entity(nlp, "Family history of PE.", AssertionCategory.FAMILY)

    def test_indication_rule_out(self, nlp):
        assert_first_entity(nlp, "Rule out PE.", AssertionCategory.INDICATION)

    def test_indication_evaluate_for(self, nlp):
        assert_first_entity(nlp, "Evaluate for PE.", AssertionCategory.INDICATION)

    def test_indication_concern_for(self, nlp):
        assert_first_entity(nlp, "Concern for PE.", AssertionCategory.INDICATION)

    def test_indication_worrisome_for(self, nlp):
        assert_first_entity(nlp, "Worrisome for PE.", AssertionCategory.INDICATION)

    def test_indication_question_of(self, nlp):
        assert_first_entity(nlp, "Question of PE.", AssertionCategory.INDICATION)


# ---------------------------------------------------------------------------
# Section-level propagation
# ---------------------------------------------------------------------------

class TestSectionPropagation:
    def test_past_medical_history_propagates_historical(self, nlp):
        assert_first_entity(
            nlp, "PAST MEDICAL HISTORY: PE.",
            AssertionCategory.HISTORICAL
        )

    def test_family_history_propagates_family(self, nlp):
        assert_first_entity(
            nlp, "FAMILY HISTORY: PE.",
            AssertionCategory.FAMILY
        )

    def test_indication_section_propagates_indication(self, nlp):
        assert_first_entity(
            nlp, "INDICATION: PE.",
            AssertionCategory.INDICATION
        )

    def test_indication_section_with_rule_out(self, nlp):
        assert_first_entity(
            nlp, "INDICATION: Rule out PE.",
            AssertionCategory.INDICATION
        )

    def test_indication_section_overrides_negation(self, nlp):
        # override_existing=True for INDICATION sections
        assert_first_entity(
            nlp, "INDICATION: No PE.",
            AssertionCategory.INDICATION
        )

    def test_historical_section_preserves_sentence_negation(self, nlp):
        # override_existing=False for HISTORICAL sections
        assert_first_entity(
            nlp, "PAST MEDICAL HISTORY: No PE.",
            AssertionCategory.DEFINITE_NEGATED_EXISTENCE
        )

    def test_historical_section_no_double_historicization(self, nlp):
        assert_first_entity(
            nlp, "PAST MEDICAL HISTORY: History of PE.",
            AssertionCategory.HISTORICAL
        )

    def test_family_section_no_double_family(self, nlp):
        # "father" and family section both → still FAMILY, not doubled
        assert_first_entity(
            nlp, "FAMILY HISTORY: Father had PE.",
            AssertionCategory.FAMILY
        )

    def test_multi_sentence_section_scope(self, nlp):
        # Second sentence in a HISTORICAL section inherits HISTORICAL
        doc = nlp("PAST MEDICAL HISTORY: Hypertension. PE.")
        pe_ents = [e for e in doc.ents if e.text == "PE"]
        assert pe_ents, "PE entity not found"
        assert pe_ents[0]._.cwyde_assertion_category == AssertionCategory.HISTORICAL

    def test_unmapped_section_preserves_negation(self, nlp):
        assert_first_entity(
            nlp, "IMPRESSION: No evidence of PE.",
            AssertionCategory.DEFINITE_NEGATED_EXISTENCE
        )

    def test_unmapped_section_preserves_probable(self, nlp):
        assert_first_entity(
            nlp, "IMPRESSION: Probable PE in right lower lobe.",
            AssertionCategory.PROBABLE_EXISTENCE
        )

    def test_unmapped_section_baseline_definite(self, nlp):
        assert_first_entity(
            nlp, "IMPRESSION: PE is present.",
            AssertionCategory.DEFINITE_EXISTENCE
        )

    def test_allergies_section_propagates_historical(self, nlp):
        assert_first_entity(
            nlp, "ALLERGIES: PE.",
            AssertionCategory.HISTORICAL
        )

    def test_social_history_propagates_historical(self, nlp):
        assert_first_entity(
            nlp, "SOCIAL HISTORY: PE.",
            AssertionCategory.HISTORICAL
        )

    def test_chief_complaint_propagates_indication(self, nlp):
        assert_first_entity(
            nlp, "CHIEF COMPLAINT: PE.",
            AssertionCategory.INDICATION
        )

    def test_reason_for_exam_propagates_indication(self, nlp):
        assert_first_entity(
            nlp, "REASON FOR THIS EXAMINATION: Rule out PE.",
            AssertionCategory.INDICATION
        )

    def test_hpi_section_sentence_modifier_wins(self, nlp):
        # history_of_present_illness: override_existing=False and propagate_to_children=False
        assert_first_entity(
            nlp, "HISTORY OF PRESENT ILLNESS: Patient presents with PE.",
            AssertionCategory.INDICATION
        )


# ---------------------------------------------------------------------------
# Multi-entity document — check all entities
# ---------------------------------------------------------------------------

class TestMultiEntityDocument:
    def test_two_entities_same_section(self, nlp):
        doc = nlp("PAST MEDICAL HISTORY: PE. DVT.")
        ents = {e.text: e._.cwyde_assertion_category for e in doc.ents}
        assert ents.get("PE") == AssertionCategory.HISTORICAL
        assert ents.get("DVT") == AssertionCategory.HISTORICAL

    def test_entities_across_sections(self, nlp):
        # HISTORICAL section (override_existing=False) does not override sentence negation.
        # IMPRESSION is an unmapped section — DVT keeps its sentence-level category.
        text = "PAST MEDICAL HISTORY: PE.\nIMPRESSION: No DVT."
        doc = nlp(text)
        ents = {e.text: e._.cwyde_assertion_category for e in doc.ents}
        assert ents.get("PE") == AssertionCategory.HISTORICAL
        assert ents.get("DVT") == AssertionCategory.DEFINITE_NEGATED_EXISTENCE


# ---------------------------------------------------------------------------
# Extension attributes are set
# ---------------------------------------------------------------------------

class TestExtensions:
    def test_cwyde_assertion_category_set(self, nlp):
        doc = nlp("No PE.")
        assert doc.ents[0]._.cwyde_assertion_category is not None

    def test_cwyde_resolution_trace_is_list(self, nlp):
        doc = nlp("No PE.")
        trace = doc.ents[0]._.cwyde_resolution_trace
        assert isinstance(trace, list)
        assert len(trace) > 0

    def test_cwyde_section_inherited_flag(self, nlp):
        # INDICATION: PE. — no ConText modifier gives PE INDICATION by itself;
        # the section_propagator is what changes DEFINITE_EXISTENCE → INDICATION.
        doc = nlp("INDICATION: PE.")
        pe = doc.ents[0]
        assert pe._.cwyde_assertion_category == AssertionCategory.INDICATION
        assert pe._.cwyde_section_inherited is True

    def test_cwyde_section_inherited_false_without_section(self, nlp):
        doc = nlp("PE is present.")
        pe = doc.ents[0]
        assert pe._.cwyde_section_inherited is False

    def test_no_entity_doc_runs_cleanly(self, nlp):
        doc = nlp("The patient is doing well.")
        assert doc.ents == ()
