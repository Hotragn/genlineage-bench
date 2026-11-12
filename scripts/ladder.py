"""Signal ladder (E4B, natural, box CPU): L0 no header/no AGENTS.md, L1 header, L2 header + AGENTS.md, on the 13 regen/mixed test tasks.
Reads results/runs_ladder/ladder_e4b/natural/seed*/<task>__L<k>/transcript.json; writes results/summary/ladder.json.
dur = durable_pass and not tampered (as in analyze.py); only complete (task, seed) triples enter the paired tests."""
import glob, json, math, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cells = {}
for p in glob.glob(os.path.join(ROOT, "results", "runs_ladder", "ladder_e4b", "natural", "seed*", "*", "transcript.json")):
    L = json.load(open(p)); base, lvl = L["task"].rsplit("__L", 1); s = L["score"]
    if str(L["stop"]).startswith("api_error"): continue
    reads = [c["function"].get("arguments", {}).get("path", "") for t in L["turns"] for c in (t.get("tool_calls") or [])
             if c.get("function", {}).get("name") == "read_file" and isinstance(c["function"].get("arguments"), dict)]
    cells[(base, L["seed"], int(lvl))] = dict(imm=int(s["immediate_pass"]), dur=int(s["durable_pass"] and not s["tampered_tests"]),
        lost=int(s["immediate_pass"] and not s["durable_pass"]), hgen=int(bool(s.get("hand_edited_generated"))), tamper=int(s["tampered_tests"]),
        read_agents=int(any(os.path.basename(r) == "AGENTS.md" for r in reads) or any("AGENTS.md" in c for c in L.get("commands", []))))
keys = sorted({(t, s) for t, s, _ in cells if all((t, s, l) in cells for l in (0, 1, 2))})
out = dict(complete_pairs=len(keys), seeds=sorted({s for _, s in keys}), tasks=len({t for t, _ in keys}), level={}, tests={})
for l in (0, 1, 2):
    R = [cells[(t, s, l)] for t, s in keys]
    out["level"][f"L{l}"] = {k: sum(r[k] for r in R) for k in ("imm", "dur", "lost", "hgen", "tamper", "read_agents")} | dict(n=len(R))
def mc(a, b):
    x = sum(1 for k in keys if cells[(*k, a)]["dur"] and not cells[(*k, b)]["dur"]); y = sum(1 for k in keys if cells[(*k, b)]["dur"] and not cells[(*k, a)]["dur"]); n = x + y
    return dict(a_only=x, b_only=y, p=round(min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n), 4) if n else 1.0)
for a, b in ((0, 1), (1, 2), (0, 2)): out["tests"][f"L{a}_vs_L{b}"] = mc(a, b)
os.makedirs(os.path.join(ROOT, "results", "summary"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "results", "summary", "ladder.json"), "w"), indent=1); print(json.dumps(out, indent=1))
