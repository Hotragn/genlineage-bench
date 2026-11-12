"""Validate the four real-repository tasks in place (run bench/fetch_real.py first) and compare with bench/validation_real.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from bench.build import validate
import fetch_real
OUT = os.path.join(HERE, "tasks_real"); KEYS = ("deterministic_regen", "none", "ref_fix", "gen_only_fix", "ref_fix_root_cause", "ok")
ref = {r["task"]: r for r in json.load(open(os.path.join(HERE, "validation_real.json")))}; bad = []
for t in sorted(json.load(open(os.path.join(OUT, "index.json")))):
    if t in fetch_real.ry_tasks() and fetch_real.check(t): bad.append(t); print(t, "not fetched; run bench/fetch_real.py"); continue
    r = validate(json.load(open(os.path.join(OUT, t, "task.json"))), os.path.join(OUT, t, "repo"))
    same = all(r.get(k) == ref[t].get(k) for k in KEYS); print(json.dumps(r), "matches validation_real.json" if same else "DIFFERS from validation_real.json")
    if not (r["ok"] and same): bad.append(t)
print("VALIDATE REAL ALL OK" if not bad else f"VALIDATE REAL FAILED: {bad}")
sys.exit(1 if bad else 0)
