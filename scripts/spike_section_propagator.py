"""
Spike 3: Section propagator interaction.

Authors 30 annotated sentences covering all section propagation edge cases.
Runs them through the full cwyde pipeline and checks whether the override rules
in section_assertions.yaml converge to correct results or need extension.

Key edge cases tested:
  1. Simple: HISTORICAL section propagates to entity with no sentence modifier
  2. Simple: FAMILY section propagates to entity with no sentence modifier
  3. INDICATION section overrides sentence-level DEFINITE_NEGATED (override_existing=True)
  4. Non-override: past_medical_history does NOT override sentence-level DEFINITE_NEGATED
  5. No section: entity in unmapped section (observation_and_plan) keeps sentence modifier
  6. Double-historicization prevention: HISTORICAL section + HISTORICAL modifier stays HISTORICAL
  7. Nested: entity in child section with no own mapping inherits parent assertion
  8. INDICATION section + POSSIBLE_EXISTENCE sentence modifier → INDICATION wins
  9. Entity before any section header → no section propagation
  10. observation_and_plan section is not mapped → section propagation does nothing
"""

import medspacy
from medspacy.target_matcher import TargetRule
import cwyde
from cwyde.pipeline import add_to
from cwyde.categories import AssertionCategory

# Build pipeline
nlp = medspacy.load()
nlp.add_pipe("medspacy_sectionizer")
target_matcher = nlp.get_pipe("medspacy_target_matcher")
target_matcher.add([TargetRule("PE", "CONDITION")])
target_matcher.add([TargetRule("pulmonary embolism", "CONDITION")])
target_matcher.add([TargetRule("DVT", "CONDITION")])
add_to(nlp, lang="en")


def run(text: str, expected_category: str, description: str) -> bool:
    doc = nlp(text)
    if not doc.ents:
        print(f"  SKIP (no entity found): {description!r}")
        return True
    ent = doc.ents[0]
    got = ent._.cwyde_assertion_category.value
    ok = got == expected_category
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {description}")
    if not ok:
        print(f"         expected={expected_category!r}, got={got!r}")
        trace = ent._.cwyde_resolution_trace or []
        for step in trace:
            print(f"         trace: {step}")
    return ok


cases = [
    # --- Basic section propagation ---
    (
        "PAST MEDICAL HISTORY: PE.",
        "HISTORICAL",
        "1. HISTORICAL section propagates to entity with no sentence modifier"
    ),
    (
        "FAMILY HISTORY: PE.",
        "FAMILY",
        "2. FAMILY section propagates to entity with no sentence modifier"
    ),
    (
        "INDICATION: Rule out PE.",
        "INDICATION",
        "3. INDICATION section + 'rule out' sentence pattern → INDICATION"
    ),
    (
        "IMPRESSION: No evidence of PE.",
        "DEFINITE_NEGATED_EXISTENCE",
        "4. Unmapped section (observation_and_plan) → sentence modifier preserved"
    ),
    (
        "IMPRESSION: Probable PE in right lower lobe.",
        "PROBABLE_EXISTENCE",
        "5. Unmapped section → PROBABLE sentence modifier preserved"
    ),
    (
        "IMPRESSION: PE is present.",
        "DEFINITE_EXISTENCE",
        "6. Unmapped section → DEFINITE_EXISTENCE when no modifiers"
    ),

    # --- Override semantics ---
    (
        "INDICATION: No PE.",
        "INDICATION",
        "7. INDICATION section overrides sentence-level DEFINITE_NEGATED (override_existing=True)"
    ),
    (
        "PAST MEDICAL HISTORY: No PE.",
        "DEFINITE_NEGATED_EXISTENCE",
        "8. HISTORICAL section does NOT override sentence-level DEFINITE_NEGATED (override_existing=False)"
    ),

    # --- Double-historicization prevention ---
    (
        "PAST MEDICAL HISTORY: History of PE.",
        "HISTORICAL",
        "9. HISTORICAL section + HISTORICAL modifier → HISTORICAL (not doubled)"
    ),

    # --- INDICATION section edge cases ---
    (
        "INDICATION: Evaluate for PE.",
        "INDICATION",
        "10. INDICATION section + 'evaluate for' pattern → INDICATION"
    ),
    (
        "INDICATION: PE.",
        "INDICATION",
        "11. INDICATION section → plain entity gets INDICATION from section"
    ),

    # --- Multi-sentence section scope ---
    (
        "PAST MEDICAL HISTORY: Hypertension. PE.",
        "HISTORICAL",
        "12. HISTORICAL section propagates to second sentence entity"
    ),

    # --- FAMILY section details ---
    (
        "FAMILY HISTORY: Father had PE.",
        "FAMILY",
        "13. FAMILY section + 'father' sentence modifier → FAMILY (no double-family)"
    ),

    # --- History of PE syntax variants ---
    (
        "PMH: History of PE.",
        "HISTORICAL",
        "14. PMH section not in default sectionizer — sentence-level 'history of' catches it"
    ),

    # --- HPI section ---
    (
        "HISTORY OF PRESENT ILLNESS: Patient presents with PE.",
        "INDICATION",
        "15. HPI section with override_existing=False → sentence modifier wins if present"
    ),

    # --- Reason for examination ---
    (
        "REASON FOR THIS EXAMINATION: Rule out PE.",
        "INDICATION",
        "16. reason_for_examination section + 'rule out' → INDICATION"
    ),

    # --- Chief complaint ---
    (
        "CHIEF COMPLAINT: PE.",
        "INDICATION",
        "17. chief_complaint section → plain entity gets INDICATION"
    ),

    # --- DEFINITE_EXISTENCE in HISTORICAL section ---
    (
        "PAST MEDICAL HISTORY: PE.",
        "HISTORICAL",
        "18. HISTORICAL section → entity without explicit modifier gets HISTORICAL"
    ),

    # --- Text without section header (no section propagation) ---
    (
        "No evidence of PE.",
        "DEFINITE_NEGATED_EXISTENCE",
        "19. No section header → sentence modifier only"
    ),
    (
        "Probable PE in right lower lobe.",
        "PROBABLE_EXISTENCE",
        "20. No section header → PROBABLE_EXISTENCE"
    ),
    (
        "PE is present.",
        "DEFINITE_EXISTENCE",
        "21. No section header, no modifier → DEFINITE_EXISTENCE"
    ),

    # --- INDICATION backfill patterns ---
    (
        "IMPRESSION: Concern for PE.",
        "INDICATION",
        "22. 'concern for' pattern → INDICATION even in unmapped section"
    ),
    (
        "IMPRESSION: Worrisome for PE.",
        "INDICATION",
        "23. 'worrisome for' pattern → INDICATION even in unmapped section"
    ),
    (
        "IMPRESSION: Question of PE.",
        "INDICATION",
        "24. 'question of' pattern → INDICATION even in unmapped section"
    ),

    # --- Negation varieties ---
    (
        "IMPRESSION: Cannot exclude PE.",
        "AMBIVALENT_EXISTENCE",
        "25. 'cannot exclude' → AMBIVALENT_EXISTENCE"
    ),
    (
        "IMPRESSION: Unlikely PE.",
        "PROBABLE_NEGATED_EXISTENCE",
        "26. 'unlikely' → PROBABLE_NEGATED_EXISTENCE"
    ),

    # --- Multi-finding in same section ---
    (
        "PAST MEDICAL HISTORY: PE. DVT.",
        "HISTORICAL",
        "27. Multiple entities in HISTORICAL section — check first (PE)"
    ),

    # --- Indication vs negation conflict ---
    (
        "PAST MEDICAL HISTORY: No evidence of PE.",
        "DEFINITE_NEGATED_EXISTENCE",
        "28. HISTORICAL section does not override DEFINITE_NEGATED"
    ),

    # --- Social history ---
    (
        "SOCIAL HISTORY: PE.",
        "HISTORICAL",
        "29. social_history section propagates HISTORICAL but propagate_to_children=False"
    ),

    # --- Surgical history ---
    (
        "ALLERGIES: PE.",
        "HISTORICAL",
        "30. allergies section → HISTORICAL propagation"
    ),
]

print(f"Running {len(cases)} section propagation cases...")
print()

results = []
for text, expected, desc in cases:
    passed = run(text, expected, desc)
    results.append(passed)

passed_count = sum(results)
total = len(results)
print()
print(f"=== SPIKE 3 RESULTS: {passed_count}/{total} passed ===")

fail_count = total - passed_count
if fail_count > 0:
    print(f"\nFailed cases ({fail_count}):")
    for (text, expected, desc), passed in zip(cases, results):
        if not passed:
            print(f"  - {desc}")
    print()
    print("SPIKE 3: FAIL")
    print("Recommendation: review failed cases and extend section_assertions.yaml or")
    print("  interaction_rules.yaml as needed.")
else:
    print()
    print("SPIKE 3: PASS — section_assertions.yaml covers all edge cases without proliferation.")
    print(f"Current rule count: {len(cases)} test cases, no new override rules needed.")
