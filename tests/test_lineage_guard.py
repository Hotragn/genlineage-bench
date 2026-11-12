"""Checks of the survival gate (edit_survives) against every task's reference and generated-only fixes.
Expectation: a generated-only fix to a regenerated region is reverted (gate rejects);
every edit in the reference fix that touches a generated file (preserved-region edits) survives (gate accepts).
Run: python tests/test_lineage_guard.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from genlineage.lineage import edit_survives
B = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bench", "tasks")
def edited(repo, rel, pairs):
    s = open(os.path.join(repo, rel)).read(); o = s
    for a, b in pairs: assert a in s, (rel, a); s = s.replace(a, b)
    return o, s
fails, n = [], 0
for tid in sorted(os.listdir(B)):
    tj = os.path.join(B, tid, "task.json")
    if not os.path.exists(tj): continue
    t = json.load(open(tj)); repo = os.path.join(B, tid, "repo")
    for which, expect_any in (("gen_only_fix", None), ("ref_fix", True)):
        for rel, pairs in (t.get(which) or {}).items():
            if rel not in t["generated"]: continue
            old, new = edited(repo, rel, pairs); ok, detail = edit_survives(repo, t["gen_cmd"], rel, new, old); n += 1
            exp = expect_any if expect_any is not None else (t["kind"] == "inregion")
            print(f"{tid:24s} {which:12s} {rel:34s} survives={ok} expected={exp}")
            if ok != exp: fails.append((tid, which, rel, detail))
print(f"{n} checks, {len(fails)} failures"); [print("FAIL", f) for f in fails]
sys.exit(1 if fails else 0)
