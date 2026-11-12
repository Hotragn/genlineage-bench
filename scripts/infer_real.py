"""Lineage inference on the real-repo tasks with SUPPLIED commands (task.json lineage_commands), not discovery.
Writes results/lin_cache_real/<task>.json (the cache run_grid.py --lin_cache reuses) and prints a check per task:
are all declared generated files found as outputs, and which inputs are reported.
Usage: python scripts/infer_real.py [--tasks_dir bench/tasks_real] [--out results/lin_cache_real]"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from genlineage.lineage import infer, discover_commands
ap = argparse.ArgumentParser(); ap.add_argument("--tasks_dir", default=os.path.join(ROOT, "bench", "tasks_real"))
ap.add_argument("--out", default=os.path.join(ROOT, "results", "lin_cache_real")); ap.add_argument("--tasks", default="")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True); rows = []
prev = {r["task"]: r for r in json.load(open(os.path.join(a.out, "check.json")))} if a.tasks and os.path.exists(os.path.join(a.out, "check.json")) else {}
if os.path.basename(os.path.abspath(a.tasks_dir)) == "tasks_real":  # fetch and verify the pinned yt-dlp files first
    sys.path.insert(0, os.path.join(ROOT, "bench")); import fetch_real; fetch_real.ensure_all()
for t in sorted(json.load(open(os.path.join(a.tasks_dir, "index.json")))):
    if a.tasks and t not in a.tasks.split(","):
        if t in prev: rows.append(prev[t])
        continue
    m = json.load(open(os.path.join(a.tasks_dir, t, "task.json"))); repo = os.path.join(a.tasks_dir, t, "repo")
    lin = infer(repo, commands=m["lineage_commands"]); json.dump(lin, open(os.path.join(a.out, t + ".json"), "w"), indent=1)
    found = sorted(lin["outputs"]); row = {"task": t, "commands": lin["commands"], "declared_generated": m["generated"],
        "outputs_found": found, "all_found": set(m["generated"]) <= set(found), "extra_outputs": sorted(set(found) - set(m["generated"])),
        "inputs": {o: v["inputs"] for o, v in lin["outputs"].items()}, "line_map_entries": {o: len(v) for o, v in lin.get("line_map", {}).items()},
        "noisy_lines": {o: v["noisy_lines"] for o, v in lin["outputs"].items()}, "regen_runs": lin["regen_runs"], "seconds": lin["seconds"],
        "discovered_commands_for_reference": discover_commands(repo)}
    rows.append(row); print(json.dumps(row), flush=True)
json.dump(rows, open(os.path.join(a.out, "check.json"), "w"), indent=1)
print("ALL OUTPUTS FOUND" if all(r["all_found"] for r in rows) else "MISSING OUTPUTS")
