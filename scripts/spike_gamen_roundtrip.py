"""
Spike 2: gamen-validate flat round-trip.

Translates all seven primary AssertionCategories to modal formulas and submits
them to gamen-validate. Checks which categories work cleanly in flat extraction
format vs. which require tree format (specifically HISTORICAL and INDICATION).

Key question: does our Indication(Atom) encoding (¬K∧¬K¬) round-trip through
gamen-validate without a semantic error?
"""
import json
import subprocess
from pathlib import Path

from cwyde.categories import AssertionCategory
from cwyde.formal.translator import category_to_formula
from cwyde_haskell_bridge.discovery import find_gamen_validate

GAMEN = find_gamen_validate()
if GAMEN is None:
    print("SPIKE 2: SKIP — gamen-validate binary not found")
    raise SystemExit(0)

print(f"Using gamen-validate: {GAMEN}")
print()


def gamen_call(request: dict) -> dict:
    payload = json.dumps(request) + "\n"
    result = subprocess.run(
        [str(GAMEN)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=5.0,
        check=False,
    )
    if result.returncode != 0:
        return {"ok": False, "error": f"exit {result.returncode}: {result.stderr.strip()}"}
    try:
        return json.loads(result.stdout.strip().splitlines()[0])
    except Exception as e:
        return {"ok": False, "error": f"parse error: {e}, stdout={result.stdout!r}"}


# First: check what actions gamen-validate supports
ping = gamen_call({"action": "ping"})
print("Ping:", ping)
print()

# Test formula validation for each category
categories = [
    AssertionCategory.DEFINITE_EXISTENCE,
    AssertionCategory.PROBABLE_EXISTENCE,
    AssertionCategory.AMBIVALENT_EXISTENCE,
    AssertionCategory.PROBABLE_NEGATED_EXISTENCE,
    AssertionCategory.DEFINITE_NEGATED_EXISTENCE,
    AssertionCategory.HISTORICAL,
    AssertionCategory.INDICATION,
    AssertionCategory.FAMILY,
    AssertionCategory.HYPOTHETICAL,
]

print("=== Tree format round-trip ===")
print(f"{'Category':<35} {'tree JSON (abbrev)':<50} {'gamen response'}")
print("-" * 100)

results = {}
for cat in categories:
    formula = category_to_formula(cat, "x")
    tree = formula.to_tree_json()
    tree_str = json.dumps(tree)[:50]

    resp = gamen_call({"action": "validate_formula", "formula": tree})
    ok = resp.get("ok", False)
    results[cat] = ok
    status = "OK" if ok else f"FAIL: {resp}"
    print(f"  {cat.value:<33} {tree_str:<50} {status}")

print()
print("=== Flat extraction format round-trip ===")
print(f"{'Category':<35} {'flat JSON (abbrev)':<50} {'gamen response'}")
print("-" * 100)

flat_results = {}
for cat in categories:
    formula = category_to_formula(cat, "x")
    try:
        flat = formula.to_flat_extraction()
        flat_str = json.dumps(flat)[:50]
        resp = gamen_call({"action": "validate_formula", "formula": flat})
        ok = resp.get("ok", False)
        flat_results[cat] = ok
        status = "OK" if ok else f"FAIL: {resp}"
    except NotImplementedError as e:
        flat_results[cat] = False
        flat_str = "(not implemented)"
        status = f"SKIP: {e}"
    print(f"  {cat.value:<33} {flat_str:<50} {status}")

print()
print("=== Consistency check (pair of formulas) ===")
# Test: Box(Atom(x)) and Box(Not(Atom(x))) should be inconsistent
from cwyde.formal.modal import Box, Atom, Not, Diamond
f1 = Box(Atom("x"))
f2 = Box(Not(Atom("x")))
resp = gamen_call({
    "action": "check_consistency",
    "formulas": [f1.to_tree_json(), f2.to_tree_json()]
})
print(f"  Box(x) + Box(¬x) consistency: {resp}")

f3 = Box(Atom("x"))
f4 = Diamond(Atom("x"))
resp2 = gamen_call({
    "action": "check_consistency",
    "formulas": [f3.to_tree_json(), f4.to_tree_json()]
})
print(f"  Box(x) + Diamond(x) consistency: {resp2}")

print()
print("=== SPIKE 2 CHECKS ===")
checks = [
    ("Tree format works for all categories", all(results.values())),
    ("HISTORICAL tree round-trips", results.get(AssertionCategory.HISTORICAL, False)),
    ("INDICATION tree round-trips (¬K∧¬K¬ encoding)", results.get(AssertionCategory.INDICATION, False)),
    ("FAMILY tree round-trips (Knowledge operator)", results.get(AssertionCategory.FAMILY, False)),
    ("gamen-validate responds to ping", ping.get("ok", False)),
]

all_pass = True
for desc, passed in checks:
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    print(f"  [{status}] {desc}")

print()
print("SPIKE 2:", "PASS" if all_pass else "FAIL — see above")
print()
print("=== Design decision from spike ===")
tree_fails = [cat for cat, ok in results.items() if not ok]
flat_fails = [cat for cat, ok in flat_results.items() if not ok]
if not tree_fails:
    print("  Tree format: ALL categories work. Use tree as default.")
else:
    print(f"  Tree format: fails for {[c.value for c in tree_fails]}")
if flat_fails:
    print(f"  Flat format: fails for {[c.value for c in flat_fails]} — use tree for these.")
else:
    print("  Flat format: ALL categories work in flat format too.")
