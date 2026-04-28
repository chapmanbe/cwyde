"""
Spike 1: Pipeline ordering.

Confirms:
- doc._.sections is populated by medspacy_sectionizer with correct body_span tuples
- ent._.modifiers is populated by medspacy_context with ConTextModifier objects
- Entity-to-section containment works via body_span token indices
- cwyde components add cleanly after medspaCy components
- section_propagator correctly propagates HISTORICAL to past_medical_history entities
- indication_detector correctly promotes POSSIBLE_EXISTENCE → INDICATION for "rule out"
"""
import medspacy
from medspacy.target_matcher import TargetRule

nlp = medspacy.load()
nlp.add_pipe("medspacy_sectionizer")

target_matcher = nlp.get_pipe("medspacy_target_matcher")
target_matcher.add([TargetRule("pulmonary embolism", "CONDITION")])

TEXT = """INDICATION: Rule out pulmonary embolism.

IMPRESSION: No evidence of pulmonary embolism. There is probable pulmonary embolism in the right lower lobe.

PAST MEDICAL HISTORY: History of pulmonary embolism."""

print("=== Pipeline order (before cwyde) ===")
print(nlp.pipe_names)

doc = nlp(TEXT)

print()
print("=== Sections ===")
for s in doc._.sections:
    bs, be = s.body_span
    body_text = doc[bs:be].text.strip()[:60]
    print(f"  category={s.category!r:35s} body[:60]={body_text!r}")

print()
print("=== Entities (medspaCy only) ===")
for ent in doc.ents:
    mods = ent._.modifiers
    sent_text = ent.sent.text.strip()[:80]
    print(f"  {ent.text!r:30s} negated={ent._.is_negated} historical={ent._.is_historical} uncertain={ent._.is_uncertain}")
    for m in mods:
        print(f"    modifier: category={m.category!r} span={doc[m.modifier_span[0]:m.modifier_span[1]].text!r}")

print()
print("=== Section membership ===")
for ent in doc.ents:
    for s in doc._.sections:
        bs, be = s.body_span
        if bs <= ent.start < be:
            print(f"  {ent.text!r} -> section {s.category!r}")
            break

print()
print("=== Now add cwyde components via pipeline.add_to() ===")
from cwyde.pipeline import add_to
add_to(nlp, lang="en")
print("Final pipe order:", nlp.pipe_names)

print()
print("=== Run through full cwyde pipeline ===")
doc2 = nlp(TEXT)
print()
print(f"{'Entity':<30} {'cwyde category':<35} inherited  indication")
print("-" * 85)
for ent in doc2.ents:
    cat = ent._.cwyde_assertion_category
    inherited = ent._.cwyde_section_inherited
    is_ind = ent._.cwyde_is_indication
    print(f"  {ent.text!r:<28} {cat.value:<35} {str(inherited):<10} {is_ind}")
    trace = ent._.cwyde_resolution_trace or []
    for step in trace:
        print(f"    trace: {step}")

print()
print("=== SPIKE 1 CHECKS ===")
results = {}
for ent in doc2.ents:
    sent = ent.sent.text.strip()
    cat = ent._.cwyde_assertion_category.value
    if "Rule out" in sent:
        results["rule_out"] = cat
    elif "No evidence" in sent:
        results["no_evidence"] = cat
    elif "probable" in sent:
        results["probable"] = cat
    elif "History of" in sent:
        results["history"] = cat

checks = [
    ("rule_out", "INDICATION", "POSSIBLE_EXISTENCE promoted to INDICATION"),
    ("no_evidence", "DEFINITE_NEGATED_EXISTENCE", "NEGATED_EXISTENCE maps to DEFINITE_NEGATED"),
    ("probable", "PROBABLE_EXISTENCE", "POSSIBLE_EXISTENCE maps to PROBABLE_EXISTENCE"),
    ("history", "HISTORICAL", "HISTORICAL maps correctly (possibly via section or modifier)"),
]
all_pass = True
for key, expected, desc in checks:
    got = results.get(key, "MISSING")
    status = "PASS" if got == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {desc}")
    if status == "FAIL":
        print(f"         expected={expected!r}, got={got!r}")

print()
print("SPIKE 1:", "PASS" if all_pass else "FAIL — see above")
