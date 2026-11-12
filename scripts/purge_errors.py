"""Move transcripts of cells that ended with an API error (e.g. ollama 500 / OOM) out of the grid so the resumable
runner retries them. Moved to results/runs/_errors/<tag>/<cond>/seedN/<task>.<timestamp>. Prints the count.
Usage: python scripts/purge_errors.py results/runs/<tag> [--dry]"""
import json, os, shutil, sys, time
root = os.path.abspath(sys.argv[1]); dry = "--dry" in sys.argv; n = 0
errs = os.path.join(os.path.dirname(root), "_errors", os.path.basename(root))
for d, _, fs in os.walk(root):
    if "transcript.json" not in fs: continue
    try: stop = json.load(open(os.path.join(d, "transcript.json"))).get("stop", "")
    except Exception: stop = "api_error: unreadable"
    if stop.startswith("api_error"):
        n += 1; rel = os.path.relpath(d, root)
        if not dry:
            dst = os.path.join(errs, rel + "." + time.strftime("%Y%m%dT%H%M%S")); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.move(d, dst)
print(f"purged {n} api_error cells from {root}" + (" (dry run)" if dry else ""))
