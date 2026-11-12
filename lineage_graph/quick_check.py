"""Quick reproducibility check of the lineage graph export: re-run lineage inference (executes each task's generator in
a sandbox copy) for the given tasks and compare node ids and typed edges with the committed graphs in out/.
Timing fields are ignored. Default: one test task per generator family. Use --all for all 19 test tasks.
Run (from build/): python -I lineage_graph/quick_check.py [--all] [task ...]"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); BUILD = os.path.dirname(HERE); BENCH = os.path.join(BUILD, "genlineage-bench")
sys.path.insert(0, HERE); sys.path.insert(0, BENCH)
from export import build_graph
from genlineage.lineage import infer
TASKS = os.path.join(BENCH, "bench", "tasks"); idx = json.load(open(os.path.join(TASKS, "index.json")))
DEFAULT = ["jj1_feature_typo", "lk1_decimal_token", "oa1_property_typo", "pb1_field_typo", "pr1_user_region"]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
tasks = sorted(t for t in idx if idx[t]["split"] == "test") if "--all" in sys.argv else (args or DEFAULT)
sig = lambda g: (sorted(n["id"] for n in g["nodes"]), sorted((l["source"], l["target"], l["type"]) for l in g["links"]))
bad = []
for t in tasks:
    g = build_graph(infer(os.path.join(TASKS, t, "repo")), t); ref = json.load(open(os.path.join(HERE, "out", f"{t}.json")))
    ok = sig(g) == sig(ref); print(f"{t:24s} nodes={len(g['nodes'])} edges={len(g['links'])} {'MATCH' if ok else 'DIFFERS'} ({g['graph']['inference_seconds']} s)")
    if not ok: bad.append(t)
print(f"lineage graph check: {len(tasks) - len(bad)}/{len(tasks)} match the committed export")
sys.exit(1 if bad else 0)
