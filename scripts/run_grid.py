"""Run a (model x condition x task x seed) grid. Resumable: skips cells whose transcript exists.
Example: python scripts/run_grid.py --model g4-e4b-qat --tag e4b --conds natural,full --seeds 1 --split test"""
import argparse, json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from genlineage import agent
from genlineage.lineage import infer
ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True); ap.add_argument("--tag", required=True)
ap.add_argument("--conds", default="natural,hint,headerguard,staticblock,verify_tests,verify,lineage,gate,full"); ap.add_argument("--seeds", default="1")
ap.add_argument("--split", default="all"); ap.add_argument("--tasks", default=""); ap.add_argument("--out", default=os.path.join(ROOT, "results", "runs"))
ap.add_argument("--order", default="cond_major"); ap.add_argument("--shard", default="0/1")
ap.add_argument("--tasks_dir", default=os.path.join(ROOT, "bench", "tasks"))
ap.add_argument("--lin_commands", default="discover", choices=["discover", "task"],
                help="discover = genlineage.lineage.discover_commands (default); task = the task's declared lineage_commands (real repos)")
ap.add_argument("--lin_cache", default="", help="optional directory: cache inferred lineage per task as JSON (reused across runs)")
a = ap.parse_args()
TD = os.path.abspath(a.tasks_dir)
if os.path.basename(TD) == "tasks_real":  # the yt-dlp tasks ship as overlays; fetch and verify the pinned upstream files
    sys.path.insert(0, os.path.join(ROOT, "bench")); import fetch_real; fetch_real.ensure_all()
idx = json.load(open(os.path.join(TD, "index.json")))
tasks = [t for t in sorted(idx) if (a.split == "all" or idx[t]["split"] == a.split) and (not a.tasks or t in a.tasks.split(","))]
conds = a.conds.split(","); seeds = [int(s) for s in a.seeds.split(",")]
cells = [(s, c, t) for s in seeds for t in tasks for c in conds] if a.order == "task_major" else [(s, c, t) for s in seeds for c in conds for t in tasks]
k, nsh = map(int, a.shard.split("/")); cells = cells[k::nsh]
lin_cache = {}
for seed, cond, t in cells:
    if time.time() > float(os.environ.get("GL_DEADLINE", "inf")): print("DEADLINE reached, stopping", flush=True); break
    od = os.path.join(a.out, a.tag, cond, f"seed{seed}", t)
    if os.path.exists(os.path.join(od, "transcript.json")): continue
    lin = None
    if cond in agent.LIN_CONDS:
        if t not in lin_cache:
            cp = os.path.join(a.lin_cache, t + ".json") if a.lin_cache else ""
            if cp and os.path.exists(cp): lin_cache[t] = json.load(open(cp))
            else:
                cmds = None
                if a.lin_commands == "task":
                    m = json.load(open(os.path.join(TD, t, "task.json"))); cmds = m.get("lineage_commands") or [m["gen_cmd"]]
                lin_cache[t] = infer(os.path.join(TD, t, "repo"), commands=cmds)
                if cp: os.makedirs(a.lin_cache, exist_ok=True); json.dump(lin_cache[t], open(cp, "w"), indent=1)
        lin = lin_cache[t]
    L = agent.run(os.path.join(TD, t), a.model, cond, seed, od, lin=lin); s = L["score"]
    print(f"RESULT {a.tag} {cond} s{seed} {t} imm={int(s['immediate_pass'])} dur={int(s['durable_pass'])} hgen={int(s.get('hand_edited_generated', 0))} "
          f"hup={int(s.get('hand_edited_upstream', 0))} tamper={int(s['tampered_tests'])} steps={L['steps']} stop={L['stop'][:30]} wall={L['wall_s']} "
          f"blocked={len(L['blocked_writes'])} ver={[v['pass'] for v in L['verify_rounds']]} t_end={time.strftime('%Y-%m-%dT%H:%M:%S')}", flush=True)
