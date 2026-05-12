"""Probe script: findings/impression PE rank comparison on dev set (id <= 250)."""
import sys
import re
import sqlite3
from collections import Counter

sys.path.insert(0, "src")
from loguru import logger
logger.disable("PyRuSH")

import cwyde
from medspacy.target_matcher import TargetRule

RANK = {
    "DEFINITE_EXISTENCE": 2, "PROBABLE_EXISTENCE": 1, "AMBIVALENT_EXISTENCE": 0,
    "PROBABLE_NEGATED_EXISTENCE": -1, "DEFINITE_NEGATED_EXISTENCE": -2,
}
GOLD_RANK = {
    "Def. Pos": 2, "Prob. Pos": 1, "Inderterminate": 0,
    "Prob. Neg": -1, "Def. Neg": -2,
}


def sign(x):
    return 0 if x == 0 else (1 if x > 0 else -1)


def extract_findings(text):
    m = re.search(r"(?i)FINDINGS\s*:(.*?)(?=(?i:IMPRESSION)\s*:|$)", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def clean_impression(text):
    return re.sub(r"(?i)^IMPRESSION\s*:\s*", "", text.strip())


def get_ranks(nlp, text):
    if not text.strip():
        return []
    doc = nlp(text)
    out = []
    for ent in doc.ents:
        cat = str(ent._.cwyde_assertion_category).replace("AssertionCategory.", "")
        r = RANK.get(cat)
        out.append((ent.text, cat, r))
    return out


def main():
    nlp = cwyde.load("en")
    matcher = nlp.get_pipe("medspacy_target_matcher")
    matcher.add([
        TargetRule("pulmonary embolism", "CONDITION"),
        TargetRule("pulmonary emboli", "CONDITION"),
        TargetRule("pulmonary embolus", "CONDITION"),
        TargetRule("PE", "CONDITION"),
        TargetRule("filling defect", "CONDITION"),
        TargetRule("filling defects", "CONDITION"),
        TargetRule("clot", "CONDITION"),
        TargetRule("thrombus", "CONDITION"),
    ])

    con = sqlite3.connect("resources/pedocUpdate.db")
    rows = con.execute(
        "SELECT ps.id, ps.originalreport, ps.impression, cs.diseaseState "
        "FROM pesubject ps JOIN consensus_states cs ON cs.psid=ps.id "
        "WHERE ps.id <= 250"
    ).fetchall()

    results = []
    for rid, orig, imp_col, gold in rows:
        f_hits = get_ranks(nlp, extract_findings(orig))
        i_hits = get_ranks(nlp, clean_impression(imp_col))
        f_num = [r for _, _, r in f_hits if r is not None]
        i_num = [r for _, _, r in i_hits if r is not None]
        results.append({
            "id": rid, "gold": gold, "gold_rank": GOLD_RANK.get(gold),
            "f_hits": len(f_hits), "f_combined": sum(f_num) if f_num else None,
            "i_hits": len(i_hits), "i_tau": i_num[0] if len(i_num) == 1 else (sum(i_num) if i_num else None),
        })

    print(f"Dev set: {len(results)} reports")
    print(f"  FINDINGS has PE entity: {sum(1 for r in results if r['f_hits'] > 0)}")
    print(f"  Impression has PE entity: {sum(1 for r in results if r['i_hits'] > 0)}")

    both = [r for r in results if r["f_combined"] is not None and r["i_tau"] is not None]
    print(f"  Both sides numeric: {len(both)}")

    agree = sum(1 for r in both if sign(r["f_combined"]) == sign(r["i_tau"]))
    disagree = [r for r in both if sign(r["f_combined"]) != sign(r["i_tau"])]
    pct = 100 * agree // len(both) if both else 0
    print(f"  Sign agreement: {agree}/{len(both)} ({pct}%)")
    print(f"  Sign disagreements: {len(disagree)}")

    imp_gold = [r for r in results if r["i_tau"] is not None and r["gold_rank"] is not None]
    exact = sum(1 for r in imp_gold if r["i_tau"] == r["gold_rank"])
    sign_match = sum(1 for r in imp_gold if sign(r["i_tau"]) == sign(r["gold_rank"]))
    n = len(imp_gold)
    print(f"\nImpression tau vs gold (n={n}):")
    print(f"  Exact match: {exact} ({100*exact//n if n else 0}%)")
    print(f"  Sign match: {sign_match} ({100*sign_match//n if n else 0}%)")

    print("\nGold distribution in 'both' subset:")
    print(dict(Counter(r["gold"] for r in both)))

    print("\nSample disagreements (findings vs impression sign):")
    for r in disagree[:5]:
        print(f"  id={r['id']} gold={r['gold']} f_comb={r['f_combined']} i_tau={r['i_tau']}")


if __name__ == "__main__":
    main()
