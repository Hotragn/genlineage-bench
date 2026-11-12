"""Aggregate transcripts into metrics with task-clustered bootstrap CIs and paired tests.
Usage: python scripts/analyze.py [--runs results/runs] [--split test] [--out results/summary]"""
import argparse, glob, json, math, os, random, sys
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("--runs", default=os.path.join(ROOT, "results", "runs")); ap.add_argument("--split", default="test")
ap.add_argument("--out", default=os.path.join(ROOT, "results", "summary")); ap.add_argument("--B", type=int, default=5000)
a = ap.parse_args()
idx = json.load(open(os.path.join(ROOT, "bench", "tasks", "index.json")))
rows = []; infra = []
for p in glob.glob(os.path.join(a.runs, "*", "*", "seed*", "*", "transcript.json")):
    L = json.load(open(p)); tag = p.split(os.sep)[-5]; t = L["task"]
    if t not in idx or (a.split != "all" and idx[t]["split"] != a.split): continue
    if str(L.get("stop", "")).startswith("api_error"): infra.append(dict(model=tag, cond=L["cond"], seed=L["seed"], task=t, stop=L["stop"][:120])); continue
    s = L["score"]; k = idx[t]["kind"]
    cls = set((s.get("changed_files") or {}).values())
    if s["tampered_tests"] or s.get("build_tampered"): cat = "tamper"
    elif s["durable_pass"]: cat = "durable"
    elif s["immediate_pass"] and "generated" in cls and not cls & {"source", "generator"}: cat = "lost_generated_only"
    elif s["immediate_pass"]: cat = "lost_other"
    elif cls & {"source", "generator"}: cat = "fail_touched_upstream"
    elif cls: cat = "fail_other_edit"
    else: cat = "fail_no_edit"
    rows.append(dict(model=tag, cond=L["cond"], seed=L["seed"], task=t, kind=k, family=idx[t]["family"], header=idx[t]["header"], agents_md=idx[t]["agents_md"],
        imm=int(s["immediate_pass"]), dur=int(s["durable_pass"] and not s["tampered_tests"]), lost=int(s["immediate_pass"] and not s["durable_pass"]),
        strict=int(s["immediate_pass"] and s["durable_pass"] and not s["tampered_tests"]), latent=int(s["durable_pass"] and not s["immediate_pass"] and not s["tampered_tests"]),
        hgen=int(s.get("hand_edited_generated", False)), hup=int(s.get("hand_edited_upstream", False)), tamper=int(s["tampered_tests"]),
        build_tamper=int(s.get("build_tampered", False)), root=int(s.get("root_cause_fixed", False)) if k == "regen" else None,
        steps=L["steps"], wall=L["wall_s"], ptok=L.get("prompt_tokens", 0), gtok=L.get("gen_tokens", 0), stop=L["stop"],
        blocked=len(L.get("blocked_writes", [])), vrounds=len(L.get("verify_rounds", [])), cat=cat,
        lin_s=L.get("lineage_seconds", 0) or 0))
os.makedirs(a.out, exist_ok=True)
json.dump(rows, open(os.path.join(a.out, "rows.json"), "w")); json.dump(infra, open(os.path.join(a.out, "infra_errors.json"), "w"), indent=1)
def boot(rs, key, B=a.B, seed=0):
    """Task-clustered bootstrap: resample tasks with replacement, keep all seeds of a sampled task."""
    by = defaultdict(list)
    for r in rs:
        if r[key] is not None: by[r["task"]].append(r[key])
    ts = sorted(by); 
    if not ts: return (float("nan"),) * 3
    pt = sum(sum(v) for v in by.values()) / sum(len(v) for v in by.values())
    rnd = random.Random(seed); est = []
    for _ in range(B):
        smp = [rnd.choice(ts) for _ in ts]; n = sum(len(by[t]) for t in smp)
        est.append(sum(sum(by[t]) for t in smp) / n)
    est.sort(); return pt, est[int(0.025 * B)], est[int(0.975 * B) - 1]
def paired(rs, c1, c2, key):
    """Pairs (task, seed) across conditions; exact McNemar on discordant pairs + task-clustered bootstrap of the difference."""
    A = {(r["task"], r["seed"]): r[key] for r in rs if r["cond"] == c1}; Bm = {(r["task"], r["seed"]): r[key] for r in rs if r["cond"] == c2}
    ks = sorted(set(A) & set(Bm)); b = sum(1 for k in ks if A[k] and not Bm[k]); c = sum(1 for k in ks if Bm[k] and not A[k]); n = b + c
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n) if n else 1.0
    tasks = sorted({k[0] for k in ks}); rnd = random.Random(1); diffs = []
    if not tasks: return dict(n=0)
    for _ in range(a.B):
        smp = [rnd.choice(tasks) for _ in tasks]; num = den = 0
        for t in smp:
            for k in ks:
                if k[0] == t: num += Bm[k] - A[k]; den += 1
        diffs.append(num / den)
    diffs.sort(); d = sum(Bm[k] - A[k] for k in ks) / len(ks)
    # task-level sign-flip permutation test on per-task mean paired differences (seeds are not independent)
    td = [sum(Bm[k] - A[k] for k in ks if k[0] == t) / sum(1 for k in ks if k[0] == t) for t in tasks]
    obs = abs(sum(td)); nz = [x for x in td if x != 0]
    if len(nz) <= 15:
        import itertools
        pats = list(itertools.product((1, -1), repeat=len(nz))); perm_p = sum(1 for sg in pats if abs(sum(x * g for x, g in zip(nz, sg))) >= obs - 1e-12) / len(pats)
    else:
        rp = random.Random(2); perm_p = sum(1 for _ in range(20000) if abs(sum(x * rp.choice((1, -1)) for x in nz)) >= obs - 1e-12) / 20000
    return dict(n=len(ks), tasks=len(tasks), a_only=b, b_only=c, mcnemar_p=round(p, 4), perm_p=round(perm_p, 4), diff=round(d, 3),
                ci=[round(diffs[int(0.025 * a.B)], 3), round(diffs[int(0.975 * a.B) - 1], 3)], tasks_up=sum(1 for x in td if x > 0), tasks_down=sum(1 for x in td if x < 0))
summary = {}
for m in sorted({r["model"] for r in rows}):
    for c in sorted({r["cond"] for r in rows if r["model"] == m}):
        rs = [r for r in rows if r["model"] == m and r["cond"] == c]
        regen = [r for r in rs if r["kind"] in ("regen", "mixed")]; ctrl = [r for r in rs if r["kind"] == "control"]; inreg = [r for r in rs if r["kind"] in ("inregion", "mixed")]
        summary[f"{m}|{c}"] = dict(n=len(rs), seeds=sorted({r["seed"] for r in rs}),
            DRR_all=boot(rs, "dur"), ISR_all=boot(rs, "imm"),
            DRR_regen=boot(regen, "dur"), ISR_regen=boot(regen, "imm"), lost_regen=boot(regen, "lost"), strict_regen=boot(regen, "strict"), latent_regen=sum(r["latent"] for r in regen),
            DFR_regen=(sum(r["lost"] for r in regen) / max(1, sum(r["imm"] for r in regen))),
            hgen_regen=boot(regen, "hgen"), root_regen=boot([r for r in rs if r["kind"] == "regen"], "root"),
            DRR_control=boot(ctrl, "dur"), DRR_inregion=boot(inreg, "dur"),
            tamper=sum(r["tamper"] for r in rs), build_tamper=sum(r["build_tamper"] for r in rs),
            mean_steps=round(sum(r["steps"] for r in rs) / max(1, len(rs)), 1), mean_wall=round(sum(r["wall"] for r in rs) / max(1, len(rs)), 1),
            mean_tokens=round(sum(r["ptok"] + r["gtok"] for r in rs) / max(1, len(rs))))
json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
# failure taxonomy and reward mislabel (a test-on-tree reward pays for runs that regeneration then breaks)
tax = {}
for m in sorted({r["model"] for r in rows}):
    for c in sorted({r["cond"] for r in rows if r["model"] == m}):
        rs = [r for r in rows if r["model"] == m and r["cond"] == c and r["kind"] in ("regen", "mixed")]
        cnt = defaultdict(int)
        for r in rs: cnt[r["cat"]] += 1
        paid = sum(r["imm"] and not r["tamper"] for r in rs)
        tax[f"{m}|{c}"] = dict(n=len(rs), cats=dict(cnt), tree_reward_paid=paid, paid_but_lost=sum(r["lost"] and not r["tamper"] for r in rs))
json.dump(tax, open(os.path.join(a.out, "taxonomy.json"), "w"), indent=1)
# factor breakdowns on regen tasks: header present, AGENTS.md present, generator family
fac = {}
for m in sorted({r["model"] for r in rows}):
    for c in sorted({r["cond"] for r in rows if r["model"] == m}):
        rs = [r for r in rows if r["model"] == m and r["cond"] == c and r["kind"] in ("regen", "mixed")]
        for f in ("header", "agents_md", "family"):
            for v in sorted({str(r[f]) for r in rs}):
                sub = [r for r in rs if str(r[f]) == v]
                fac[f"{m}|{c}|{f}={v}"] = dict(n=len(sub), ISR=round(sum(r["imm"] for r in sub) / len(sub), 3), DRR=round(sum(r["dur"] for r in sub) / len(sub), 3))
json.dump(fac, open(os.path.join(a.out, "factors.json"), "w"), indent=1)
tests = {}
for m in sorted({r["model"] for r in rows}):
    rs = [r for r in rows if r["model"] == m and r["kind"] in ("regen", "mixed")]; conds = sorted({r["cond"] for r in rs})
    for c in conds:
        if c != "natural" and "natural" in conds: tests[f"{m}|natural_vs_{c}|dur"] = paired(rs, "natural", c, "dur")
    for c1, c2 in (("headerguard", "gate"), ("headerguard", "full"), ("staticblock", "gate"), ("verify_tests", "verify"), ("verify", "full"), ("hint", "full"), ("lineage", "gate")):
        if c1 in conds and c2 in conds: tests[f"{m}|{c1}_vs_{c2}|dur"] = paired(rs, c1, c2, "dur")
for m in sorted({r["model"] for r in rows}):
    prim = [k for k in (f"{m}|natural_vs_full|dur", f"{m}|headerguard_vs_full|dur", f"{m}|hint_vs_full|dur") if k in tests and tests[k].get("n")]
    order = sorted(prim, key=lambda k: tests[k]["mcnemar_p"]); run = 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * tests[k]["mcnemar_p"])); tests[k]["holm_p"] = round(run, 4); tests[k]["primary"] = True
json.dump(tests, open(os.path.join(a.out, "tests.json"), "w"), indent=1)
f = lambda x: f"{x[0]:.2f} [{x[1]:.2f},{x[2]:.2f}]" if isinstance(x, tuple) else str(x)
print(f"{'model|cond':34s} n  ISR_regen          DRR_regen          DRR_ctrl           DRR_inreg  hgen  DFR  tamper steps")
for k, v in summary.items():
    print(f"{k:34s} {v['n']:3d} {f(v['ISR_regen']):18s} {f(v['DRR_regen']):18s} {f(v['DRR_control']):18s} {v['DRR_inregion'][0]:.2f}  {v['hgen_regen'][0]:.2f}  {v['DFR_regen']:.2f} {v['tamper']}  {v['mean_steps']}")
for k, v in tests.items(): print(k, v)
