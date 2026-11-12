"""Every number in the merged paper, recomputed from raw transcripts and released artifacts.
Outputs results/summary/paper_stats.json (flat key -> display string) and results/summary/paper_stats_raw.json.
Metric definitions (PREREGISTRATION.md):
  DRR (primary, preregistered): original tests (restored, SHA-256 checked) pass after `make gen`, and no test file was modified.
       Immediate success is not required, so a latent fix (source fixed, outputs stale) counts as durable.
  strict DRR (secondary): immediate pass AND post-regeneration pass AND no test modification.
  DFR: immediate passes that fail after regeneration / immediate passes.  latent: post pass, no immediate pass, no tampering.
Primary scope: the 13 regen and mixed test tasks; balanced seeds 1 and 2 on all three models (E4B seed 3 = robustness).
Pooled tests: exact sign-flip permutation with tasks as units (unit difference = mean paired difference over models and seeds;
primary, conservative) and with model x task units (model-stratified). Intervals: bootstrap clustered by task."""
import csv, glob, json, math, os, random, re, statistics
from collections import defaultdict, Counter
from fractions import Fraction
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda p: json.load(open(os.path.join(ROOT, p)))
IDX = J("bench/tasks/index.json"); META = {t: J(f"bench/tasks/{t}/task.json") for t in IDX if IDX[t]["split"] == "test"}
MODELS = ["k_e2b", "k_e4b", "k_12b"]; MN = {"k_e2b": "E2B", "k_e4b": "E4B", "k_12b": "12B"}
RM = ("regen", "mixed")
def load_grid():
    rows, infra = [], []
    for p in sorted(glob.glob(os.path.join(ROOT, "results", "runs", "*", "*", "seed*", "*", "transcript.json"))):
        L = json.load(open(p)); tag = p.split(os.sep)[-5]; t = L["task"]
        if t not in META: continue
        if str(L.get("stop", "")).startswith("api_error"): infra.append((tag, L["cond"], L["seed"], t)); continue
        s = L["score"]; k = IDX[t]["kind"]; tt = bool(s["tampered_tests"])
        blocked = L.get("blocked_writes", []) or []
        rows.append(dict(m=tag, c=L["cond"], s=int(L["seed"]), t=t, k=k, header=bool(IDX[t]["header"]),
            imm=int(s["immediate_pass"]), post=int(s["durable_pass"]), tt=int(tt), bt=int(bool(s.get("build_tampered"))),
            dur=int(s["durable_pass"] and not tt), strict=int(s["immediate_pass"] and s["durable_pass"] and not tt),
            lost=int(s["immediate_pass"] and not s["durable_pass"]), latent=int(s["durable_pass"] and not s["immediate_pass"] and not tt),
            heg=int(bool(s.get("hand_edited_generated"))), steps=L["steps"], wall=L["wall_s"], tok=(L.get("prompt_tokens") or 0) + (L.get("gen_tokens") or 0),
            blocked_src=sum(1 for b in blocked if b not in META[t]["generated"]), blocked_n=len(blocked),
            cls=sorted(set((s.get("changed_files") or {}).values()))))
    return rows, infra
rows, infra = load_grid()
def sel(m=None, c=None, seeds=(1, 2), kinds=RM, f=None):
    return [r for r in rows if (m is None or r["m"] == m) and (c is None or r["c"] == c) and r["s"] in seeds and (kinds is None or r["k"] in kinds) and (f is None or f(r))]
def boot(rs, key, B=5000, seed=0):
    by = defaultdict(list)
    for r in rs: by[r["t"]].append(r[key])  # cluster = task (all models and seeds of a sampled task)
    ks = sorted(by); n = sum(len(v) for v in by.values()); pt = sum(sum(v) for v in by.values()) / n
    rnd = random.Random(seed); est = []
    for _ in range(B):
        smp = [rnd.choice(ks) for _ in ks]; est.append(sum(sum(by[k]) for k in smp) / sum(len(by[k]) for k in smp))
    est.sort(); return pt, est[int(0.025 * B)], est[int(0.975 * B) - 1]
def exact_signflip(d):
    """two-sided exact p for sum of unit differences under independent sign flips (d: list of Fractions)."""
    nz = [x for x in d if x != 0]
    if not nz: return 1.0
    L = 1
    for x in nz: L = L * x.denominator // math.gcd(L, x.denominator)
    ints = [abs(int(x * L)) for x in nz]; obs = abs(sum(int(x * L) for x in nz))
    dist = Counter({0: 1})
    for v in ints:
        nd = Counter()
        for s_, c_ in dist.items(): nd[s_ + v] += c_; nd[s_ - v] += c_
        dist = nd
    return sum(c_ for s_, c_ in dist.items() if abs(s_) >= obs) / 2 ** len(ints)
def mcnemar(b, c):
    n = b + c
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n) if n else 1.0
def contrast(base, treat, models=MODELS, seeds=(1, 2), kinds=RM, key="dur", f=None, B=5000):
    """treat minus base. Pairs = (model, task, seed) present in both."""
    A = {(r["m"], r["t"], r["s"]): r[key] for r in sel(c=base, seeds=seeds, kinds=kinds, f=f) if r["m"] in models}
    T = {(r["m"], r["t"], r["s"]): r[key] for r in sel(c=treat, seeds=seeds, kinds=kinds, f=f) if r["m"] in models}
    ks = sorted(set(A) & set(T)); unit = defaultdict(list)
    for k in ks: unit[k[:2]].append(Fraction(T[k] - A[k]))
    d = [sum(v) / len(v) for v in unit.values()]
    to = sum(1 for k in ks if T[k] and not A[k]); bo = sum(1 for k in ks if A[k] and not T[k])
    tasks = sorted({u[1] for u in unit}); byt = {t: [u for u in unit if u[1] == t] for t in tasks}; rnd = random.Random(1); diffs = []
    for _ in range(B):  # task-clustered bootstrap: resample tasks, keep every model and seed of a sampled task
        smp = [rnd.choice(tasks) for _ in tasks]; num = sum(sum(unit[u]) for t in smp for u in byt[t]); den = sum(len(unit[u]) for t in smp for u in byt[t]); diffs.append(float(num) / den)
    diffs.sort()
    return dict(pairs=len(ks), units=len(unit), treat=sum(T[k] for k in ks), base=sum(A[k] for k in ks), treat_only=to, base_only=bo,
                diff=(to - bo) / len(ks), ci=(diffs[int(0.025 * B)], diffs[int(0.975 * B) - 1]), p_perm=exact_signflip(d), p_mcnemar=mcnemar(to, bo))
def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); out = [0] * len(ps); run = 0
    for j, i in enumerate(order): run = max(run, min(1.0, (len(ps) - j) * ps[i])); out[i] = run
    return out
P = {}; RAW = {}
pc = lambda x: f"{100 * x:.0f}%"
pn = lambda x: f"{100 * x:.0f}"
def fp(p):
    if p < 0.001: return "<0.001"
    return f"{p:.2g}"
def frac(a, b): return f"{a} of {b}"
# ---------- run accounting ----------
P["runs.total"] = str(len(rows)); P["runs.infra"] = str(len(infra))
for m in MODELS:
    P[f"runs.{m}"] = str(sum(1 for r in rows if r["m"] == m))
P["runs.conds_e4b"] = str(len({r["c"] for r in rows if r["m"] == "k_e4b"})); P["runs.conds_small"] = str(len({r["c"] for r in rows if r["m"] == "k_e2b"}))
P["runs.e4b_seed3_tasks"] = str(len({r["t"] for r in rows if r["m"] == "k_e4b" and r["s"] == 3}))
P["runs.s12_units"] = str(len({(r["m"], r["t"]) for r in sel()}))
# ---------- per model x condition (seeds 1-2, regen+mixed) ----------
TAB = {}
for m in MODELS:
    for c in sorted({r["c"] for r in rows if r["m"] == m}):
        rs = sel(m, c); al = sel(m, c, kinds=None); n = len(rs); imm = sum(r["imm"] for r in rs); lost = sum(r["lost"] for r in rs)
        d = boot(rs, "dur"); p = f"{m}.{c}"
        TAB[p] = dict(n=n, imm=imm, dur=sum(r["dur"] for r in rs), strict=sum(r["strict"] for r in rs), lost=lost, latent=sum(r["latent"] for r in rs),
                      heg=sum(r["heg"] for r in rs), tt_all=sum(r["tt"] for r in al), n_all=len(al))
        P[f"{p}.n"] = str(n); P[f"{p}.ISR"] = pn(imm / n); P[f"{p}.DRR"] = pn(d[0]); P[f"{p}.DRR_ci"] = f"[{pn(d[1])}, {pn(d[2])}]"
        P[f"{p}.strict"] = pn(TAB[p]["strict"] / n); P[f"{p}.DFR"] = pn(lost / imm) if imm else "n/a"; P[f"{p}.lost"] = str(lost); P[f"{p}.imm"] = str(imm)
        P[f"{p}.latent"] = str(TAB[p]["latent"]); P[f"{p}.HEG"] = pn(TAB[p]["heg"] / n); P[f"{p}.dur"] = str(TAB[p]["dur"])
        P[f"{p}.tt"] = f"{TAB[p]['tt_all']}/{len(al)}"
        P[f"{p}.steps"] = f"{statistics.mean(r['steps'] for r in al):.1f}"; P[f"{p}.tokens"] = f"{statistics.mean(r['tok'] for r in al) / 1000:.1f}k"
        P[f"{p}.wall"] = f"{statistics.mean(r['wall'] for r in al):.0f}"
# ---------- pooled per condition ----------
MAIN = ["natural", "hint", "headerguard", "gate", "full"]
for c in MAIN:
    rs = sel(c=c); al = sel(c=c, kinds=None); n = len(rs)
    for k in ("imm", "dur", "strict", "lost", "latent", "heg"): P[f"pool.{c}.{k}"] = str(sum(r[k] for r in rs))
    P[f"pool.{c}.n"] = str(n); P[f"pool.{c}.DRR"] = pc(sum(r["dur"] for r in rs) / n); P[f"pool.{c}.strictpct"] = pc(sum(r["strict"] for r in rs) / n)
    imm = sum(r["imm"] for r in rs); P[f"pool.{c}.DFR"] = pc(sum(r["lost"] for r in rs) / imm)
    P[f"pool.{c}.tt"] = str(sum(r["tt"] for r in al)); P[f"pool.{c}.n_all"] = str(len(al)); P[f"pool.{c}.ttpct"] = f"{100 * sum(r['tt'] for r in al) / len(al):.1f}%"
    P[f"pool.{c}.bt"] = str(sum(r["bt"] for r in al))
    P[f"pool.{c}.HEGpct"] = pc(sum(r["heg"] for r in rs) / n)
tt_all = [sum(r["tt"] for r in sel(m, c, kinds=None)) / len(sel(m, c, kinds=None)) for m in MODELS for c in sorted({r["c"] for r in rows if r["m"] == m})]
P["tt.max_cell"] = pc(max(tt_all)); P["tt.min_cell"] = pc(min(tt_all))
P["tt.12b_all"] = str(sum(r["tt"] for r in rows if r["m"] == "k_12b"))
# ---------- pooled contrasts ----------
def put(name, res, holm_p=None):
    RAW[name] = res; P[f"{name}.pairs"] = str(res["pairs"]); P[f"{name}.units"] = str(res["units"])
    P[f"{name}.disc"] = f"{res['treat_only']} vs {res['base_only']}"; P[f"{name}.colon"] = f"{res['treat_only']}:{res['base_only']}"; P[f"{name}.diff"] = f"{100 * res['diff']:+.0f}"
    P[f"{name}.ci"] = f"[{100 * res['ci'][0]:+.0f}, {100 * res['ci'][1]:+.0f}]"; P[f"{name}.p"] = fp(res["p_perm"]); P[f"{name}.mcn"] = fp(res["p_mcnemar"])
    P[f"{name}.treat"] = str(res["treat"]); P[f"{name}.base"] = str(res["base"])
    if holm_p is not None: P[f"{name}.holm"] = fp(holm_p); RAW[name]["holm"] = holm_p
prim = [("natural", "full"), ("hint", "full"), ("headerguard", "full")]
pr = [contrast(a, b) for a, b in prim]; hp = holm([x["p_perm"] for x in pr])
for (a, b), x, h in zip(prim, pr, hp): put(f"pool.{a}_vs_{b}", x, h)
for a, b in [("headerguard", "gate"), ("natural", "gate"), ("hint", "gate"), ("natural", "hint"), ("natural", "headerguard")]:
    put(f"pool.{a}_vs_{b}", contrast(a, b))
for a, b in prim + [("headerguard", "gate"), ("hint", "gate"), ("natural", "gate")]:
    put(f"strict.{a}_vs_{b}", contrast(a, b, key="strict"))
# all 19 tasks, strict (the lab draft's scope), for the disclosure sentence
put("all19strict.hint_vs_full", contrast("hint", "full", kinds=None, key="strict"))
# ---------- per model contrasts (prereg: McNemar on (task, seed), Holm over the three within a model) ----------
for m in MODELS:
    res = [contrast(a, b, models=[m]) for a, b in prim]; hm = holm([x["p_mcnemar"] for x in res])
    for (a, b), x, h in zip(prim, res, hm): put(f"{m}.{a}_vs_{b}", x, h)
    put(f"{m}.headerguard_vs_gate", contrast("headerguard", "gate", models=[m]))
    put(f"{m}.hint_vs_gate", contrast("hint", "gate", models=[m]))
    put(f"{m}.natural_vs_gate", contrast("natural", "gate", models=[m]))
# E4B including seed 3 (robustness)
for a, b in prim + [("headerguard", "gate"), ("natural", "gate")]:
    put(f"e4b123.{a}_vs_{b}", contrast(a, b, models=["k_e4b"], seeds=(1, 2, 3)))
P["e4b123.full.n"] = str(len(sel("k_e4b", "full", seeds=(1, 2, 3))))
# E4B ablations (exploratory)
for a, b in [("staticblock", "gate"), ("verify_tests", "verify"), ("lineage", "gate"), ("verify", "full"), ("gate", "full")]:
    put(f"k_e4b.{a}_vs_{b}", contrast(a, b, models=["k_e4b"]))
# in-region tasks: correct fix lives inside a preserved region of a generated file
for c in ("staticblock", "gate", "full", "natural", "lineage", "verify"):
    rs = sel("k_e4b", c, kinds=("inregion",)); P[f"inreg.k_e4b.{c}"] = frac(sum(r["dur"] for r in rs), len(rs))
    rs = sel("k_e4b", c, kinds=("inregion",), seeds=(1, 2, 3)); P[f"inreg123.k_e4b.{c}"] = frac(sum(r["dur"] for r in rs), len(rs))
for c in MAIN:
    rs = sel(c=c, kinds=("inregion",)); P[f"inreg.pool.{c}"] = frac(sum(r["dur"] for r in rs), len(rs))
# controls (bug in hand-owned code)
for c in MAIN + ["staticblock"]:
    rs = sel(c=c, kinds=("control",)); P[f"ctrl.pool.{c}"] = frac(sum(r["dur"] for r in rs), len(rs))
    rs = sel("k_e4b", c, kinds=("control",)); P[f"ctrl.k_e4b.{c}"] = frac(sum(r["dur"] for r in rs), len(rs))
# headerless regen tasks
HL = sorted(t for t in META if IDX[t]["kind"] == "regen" and not IDX[t]["header"]); P["hl.tasks"] = str(len(HL)); P["hl.names"] = ", ".join(HL)
for c in MAIN:
    rs = sel(c=c, kinds=("regen",), f=lambda r: not r["header"])
    P[f"hl.{c}.dur"] = str(sum(r["dur"] for r in rs)); P[f"hl.{c}.strict"] = str(sum(r["strict"] for r in rs)); P[f"hl.{c}.n"] = str(len(rs))
    P[f"hl.{c}.imm"] = str(sum(r["imm"] for r in rs)); P[f"hl.{c}.lost"] = str(sum(r["lost"] for r in rs)); P[f"hl.{c}.heg"] = str(sum(r["heg"] for r in rs))
    rs4 = sel("k_e4b", c, kinds=("regen",), f=lambda r: not r["header"]); P[f"hl.k_e4b.{c}.heg"] = frac(sum(r["heg"] for r in rs4), len(rs4))
put("hl.headerguard_vs_gate", contrast("headerguard", "gate", kinds=("regen",), f=lambda r: not r["header"]))
# guard blocks of hand-owned (non-generated) files, all seeds
for c in ("headerguard", "gate", "full", "staticblock"):
    rs = [r for r in rows if r["c"] == c]; P[f"blocksrc.{c}"] = str(sum(r["blocked_src"] for r in rs)); P[f"blocksrc.{c}.runs"] = str(sum(1 for r in rs if r["blocked_src"]))
# ---------- signal ladder ----------
cells = {}
for p in glob.glob(os.path.join(ROOT, "results", "runs_ladder", "ladder_e4b", "natural", "seed*", "*", "transcript.json")):
    L = json.load(open(p)); base, lvl = L["task"].rsplit("__L", 1); s = L["score"]
    if str(L["stop"]).startswith("api_error"): continue
    reads = [c_["function"].get("arguments", {}).get("path", "") for t_ in L["turns"] for c_ in (t_.get("tool_calls") or [])
             if c_.get("function", {}).get("name") == "read_file" and isinstance(c_["function"].get("arguments"), dict)]
    cells[(base, int(L["seed"]), int(lvl))] = dict(imm=int(s["immediate_pass"]), dur=int(s["durable_pass"] and not s["tampered_tests"]),
        strict=int(s["immediate_pass"] and s["durable_pass"] and not s["tampered_tests"]),
        read_agents=int(any(os.path.basename(r) == "AGENTS.md" for r in reads) or any("AGENTS.md" in c_ for c_ in L.get("commands", []))))
keys = sorted({(t, s) for t, s, _ in cells if all((t, s, l) in cells for l in (0, 1, 2))})
P["ladder.n"] = str(len(keys)); P["ladder.tasks"] = str(len({t for t, _ in keys}))
for l in (0, 1, 2):
    R = [cells[(t, s, l)] for t, s in keys]
    for k in ("imm", "dur", "strict", "read_agents"): P[f"ladder.L{l}.{k}"] = str(sum(r[k] for r in R))
for a, b in ((0, 1), (1, 2), (0, 2)):
    for key in ("dur", "strict"):
        x = sum(1 for k in keys if cells[(*k, b)][key] and not cells[(*k, a)][key]); y = sum(1 for k in keys if cells[(*k, a)][key] and not cells[(*k, b)][key])
        P[f"ladder.L{a}L{b}.{key}.disc"] = f"{x} vs {y}"; P[f"ladder.L{a}L{b}.{key}.p"] = fp(mcnemar(x, y))
# ---------- static artifacts ----------
S = J("inthewild/out/summary.json")["per_agent"]["ALL"]; H = J("inthewild/out/header_summary.json")
P["aidev.prs"] = f"{S['prs_with_file_data']:,}"; P["aidev.edit_gen"] = f"{S['edit_gen_any']:,}"; P["aidev.edit_gen_pct"] = f"{100 * S['edit_gen_any'] / S['prs_with_file_data']:.1f}%"
P["aidev.nosrc"] = f"{S['edit_gen_nosrc']:,}"
A = list(csv.DictReader(open(os.path.join(ROOT, "inthewild", "sample_audit.csv"))))
P["audit.n"] = str(len(A)); hl_ = sum(1 for a in A if a["judgment"] == "hand_edit_lost"); P["audit.lost"] = str(hl_)
P["audit.truly_gen"] = str(sum(1 for a in A if a["truly_generated"] == "yes")); P["audit.unclear"] = str(sum(1 for a in A if a["judgment"] == "unclear")); P["audit.notgen"] = str(sum(1 for a in A if a["judgment"] == "not_generated"))
P["audit.consistent"] = str(sum(1 for a in A if a["judgment"] == "consistent_regen"))
def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return c - h, c + h
w = wilson(hl_, len(A)); P["audit.lost_pct"] = pc(hl_ / len(A)); P["audit.wilson"] = f"{100 * w[0]:.1f} to {100 * w[1]:.1f}%"
w2 = wilson(hl_ - 1, len(A)); P["audit.lost_net"] = str(hl_ - 1); P["audit.wilson_net"] = f"{100 * w2[0]:.1f} to {100 * w2[1]:.1f}%"
P["hdr.n"] = str(H["fetched"]); P["hdr.nostrong"] = f"{100 * (H['fetched'] - H['strong']) / H['fetched']:.1f}%"; P["hdr.invisible"] = f"{100 * H['headerguard_invisible'] / H['fetched']:.1f}%"
W = J("prevalence/swebench_generated.json"); P["swe.instances_total"] = str(len({r["instance"] for r in W})); P["swe.files"] = f"{len(W):,}"
P["swe.gen_instances"] = str(len({r["instance"] for r in W if r.get("name_hit") or r.get("linguist_generated")}))  # PLY parsetab name hit; marker-only hit in cds.py is the hand-written source (prevalence/RESULTS.md)
V = J("bench/validation.json"); P["bench.validated"] = f"{sum(1 for v in V if v.get('ok'))} of {len(V)}"
P["bench.test"] = str(len(META)); P["bench.dev"] = str(sum(1 for t in IDX if IDX[t]["split"] == "dev"))
for k in ("regen", "inregion", "mixed", "control"): P[f"bench.{k}"] = str(sum(1 for t in META if IDX[t]["kind"] == k))
P["bench.antipatch"] = str(sum(1 for t in META if IDX[t]["kind"] in RM and META[t].get("gen_only_fix")))
G = J("lineage_graph/out/summary.json"); P["graph.runs_min"] = str(min(g["regen_runs"] for g in G)); P["graph.runs_max"] = str(max(g["regen_runs"] for g in G))
P["graph.tasks"] = str(len(G)); P["graph.med_s"] = f"{statistics.median(g['infer_seconds'] for g in G):.1f}"
VR = J("bench/validation_real.json"); P["real.tasks_ok"] = f"{sum(1 for v in (VR.values() if isinstance(VR, dict) else VR) if (v.get('ok') if isinstance(v, dict) else v))}"
RR = []
for p in glob.glob(os.path.join(ROOT, "results", "runs_real", "real_e4b", "*", "seed*", "*", "transcript.json")):
    L = json.load(open(p)); s = L["score"]; RR.append(dict(c=L["cond"], t=L["task"], imm=int(s["immediate_pass"]), post=int(s["durable_pass"]), heg=int(bool(s.get("hand_edited_generated"))), tt=int(bool(s["tampered_tests"]))))
P["real.runs"] = str(len(RR)); P["real.imm"] = str(sum(r["imm"] for r in RR)); P["real.post"] = str(sum(r["post"] for r in RR)); P["real.tt"] = str(sum(r["tt"] for r in RR)); P["real.heg"] = str(sum(r["heg"] for r in RR))
P["real.tasks_run"] = str(len({r["t"] for r in RR}))
os.makedirs(os.path.join(ROOT, "results", "summary"), exist_ok=True)
json.dump(P, open(os.path.join(ROOT, "results", "summary", "paper_stats.json"), "w"), indent=1, sort_keys=True)
json.dump(dict(contrasts=RAW, cells=TAB, infra=infra), open(os.path.join(ROOT, "results", "summary", "paper_stats_raw.json"), "w"), indent=1, default=str)
# ---------- real repositories (lineage, gate spot checks, real-repo tasks) ----------
import sys; sys.path.insert(0, ROOT)
from genlineage.agent import looks_generated
RP = J("realrepo/pycparser_ytdlp/results_run1.json"); RY = J("realrepo/pycparser_ytdlp/results_ytdlp.json")
CA = J("realrepo/res_all.json"); CG = J("realrepo/res_gate.json")
OURS = [RP["pycparser_ast"], RY["ytdlp_supportedsites"], RY["ytdlp_issuetemplates"], RY["ytdlp_readme"]]
P["rr.repos"] = str(len(CA) + len({s["repo"] for s in OURS}))
P["rr.outputs_found"] = f"{sum(len(set(s['written']) & set(s['gt_out'])) for s in OURS)} of {sum(len(s['gt_out']) for s in OURS)}"
P["rr.noise"] = str(sum(sum(s["noise_lines"].values()) for s in OURS))
gate_ok = sum(1 for s in OURS for g in s.get("gate", []) if g["verdict"] == g["expected"]) + sum(1 for g in CG if g["survives"] == g["expected"])
gate_n = sum(len(s.get("gate", [])) for s in OURS) + len(CG); P["rr.gate"] = f"{gate_ok} of {gate_n}"
P["rr.readme"] = "/".join(g["verdict"] for g in RY["ytdlp_readme"]["gate"])
P["rr.discovered"] = f"{sum(1 for s in OURS if s['cmd'] in s['discovered_commands'])} of {len(OURS)}"
KR = J("results/lin_cache_real/check.json"); IR = J("bench/tasks_real/index.json")
P["realtask.outputs_found"] = f"{sum(len(set(r['declared_generated']) & set(r['outputs_found'])) for r in KR)} of {sum(len(r['declared_generated']) for r in KR)}"
hg = [(t, g) for t in sorted(IR) for g in J(f"bench/tasks_real/{t}/task.json")["generated"]]
P["realtask.gen_files"] = str(len(hg)); P["realtask.hg_matches"] = str(sum(1 for t, g in hg if looks_generated(os.path.join(ROOT, "bench", "tasks_real", t, "repo"), g)))
P["realtask.c_ast_lines"] = f"{sum(1 for _ in open(os.path.join(ROOT, 'bench', 'tasks_real', 'rp1_pycparser_if_else', 'repo', 'pycparser', 'c_ast.py'))):,}"
P["realtask.max_prompt"] = f"{max(json.load(open(p))['prompt_tokens'] for p in glob.glob(os.path.join(ROOT, 'results', 'runs_real', 'real_e4b', '*', 'seed*', '*', 'transcript.json'))) // 1000}k"
REQ = open(os.path.join(ROOT, "genlineage", "requirements.txt")).read()
for n in ("grpcio-tools", "datamodel-code-generator", "Jinja2", "lark"): P[f"pin.{n}"] = re.search(r"^" + n + r"==(\S+)$", REQ, re.M).group(1)
CFG = {json.dumps(json.load(open(p))["config"], sort_keys=True) for p in glob.glob(os.path.join(ROOT, "results", "runs", "*", "*", "seed*", "*", "transcript.json"))}
assert len(CFG) == 1, "grid configs differ"; CF = json.loads(CFG.pop())
P["cfg.temp"] = str(CF["temperature"]); P["cfg.ctx"] = f"{CF['num_ctx']:,}"; P["cfg.predict"] = f"{CF['num_predict']:,}"; P["cfg.steps"] = str(CF["max_steps"]); P["cfg.vrounds"] = str(CF["max_verify_rounds"])
json.dump(P, open(os.path.join(ROOT, "results", "summary", "paper_stats.json"), "w"), indent=1, sort_keys=True)

# ---------- derived keys used in prose ----------
import hashlib
P["prereg.sha8"] = hashlib.sha256(open(os.path.join(ROOT, "PREREGISTRATION.md"), "rb").read()).hexdigest()[:8]
P["bench.rm"] = str(sum(1 for t in META if IDX[t]["kind"] in RM))
P["holm.max_e2b_e4b"] = fp(max(RAW[f"{m}.{a}_vs_{b}"]["holm"] for m in ("k_e2b", "k_e4b") for a, b in prim))
P["holm.min_12b"] = fp(min(RAW[f"k_12b.{a}_vs_{b}"]["holm"] for a, b in prim))
x = sum(1 for k in keys if cells[(*k, 1)]["dur"] != cells[(*k, 2)]["dur"]); P["ladder.L1L2.moved"] = str(x)
P["ollama.version"] = re.search(r"client version is (\d+\.\d+\.\d+)", open(os.path.join(ROOT, "results", "kaggle_gl-grid-a.log")).read()).group(1)
P["cell.n"] = str(len(sel("k_e4b", "full")))
mech_sig = [MN[m] for m in MODELS if RAW[f"{m}.headerguard_vs_gate"]["p_perm"] < 0.05]; P["mech.sig_models"] = " and ".join(mech_sig)
json.dump(P, open(os.path.join(ROOT, "results", "summary", "paper_stats.json"), "w"), indent=1, sort_keys=True)

# conservative pooled test: unit = task (13 units), difference averaged over models and seeds
def task_level(base, treat, key="dur", kinds=RM):
    A_ = {(r["m"], r["t"], r["s"]): r[key] for r in sel(c=base, kinds=kinds)}; T_ = {(r["m"], r["t"], r["s"]): r[key] for r in sel(c=treat, kinds=kinds)}
    u = defaultdict(list)
    for k in set(A_) & set(T_): u[k[1]].append(Fraction(T_[k] - A_[k]))
    return exact_signflip([sum(v) / len(v) for v in u.values()]), len(u)
tl = [task_level(a, b)[0] for a, b in prim]; tlh = holm(tl)
P["tl.units"] = str(task_level("natural", "full")[1]); P["tl.max_holm_prim"] = fp(max(tlh))
for (a, b), x, h in zip(prim, tl, tlh): P[f"tl.{a}_vs_{b}.p"] = fp(x); P[f"tl.{a}_vs_{b}.holm"] = fp(h)
P["tl.strict_max_p_prim"] = fp(max(task_level(a, b, key="strict")[0] for a, b in prim))
P["tl.hint_vs_full.strict_p"] = fp(task_level("hint", "full", key="strict")[0])
for a, b in [("headerguard", "gate"), ("hint", "gate"), ("natural", "gate")]: P[f"tl.{a}_vs_{b}.p"] = fp(task_level(a, b)[0])
# ---------- Phase 2 additions (Nov 11) ----------
# root cause of lost natural fixes: file classes the run changed (score.changed_files); "generated only" = every changed file is generated
_lost = [r for r in sel(c="natural") if r["lost"]]
P["pool.natural.lost_genonly"] = str(sum(1 for r in _lost if r["cls"] == ["generated"]))
assert P["pool.natural.lost_genonly"] == str(len(_lost)) == P["pool.natural.lost"], "lost fixes not all generated-only"
# failing runs that changed no file (same rule as analyze.py cat fail_no_edit): no tampering, no pass, no changed file
for c in ("natural", "gate"):
    rs = sel(c=c); P[f"pool.{c}.noedit"] = str(sum(1 for r in rs if not (r["tt"] or r["bt"] or r["dur"] or r["imm"] or r["cls"]))); P[f"pool.{c}.n_rm"] = str(len(rs))
# rich (a competition repository): files its committed generator writes, from realrepo/res_all.json (ground-truth output glob)
_rr = J("realrepo/res_all.json"); _rich = next(x for x in (_rr if isinstance(_rr, list) else _rr.values()) if x["repo"] == "rich")
P["rr.rich_gen_files"] = str(len(_rich["gt_out"]))
s3 = [len({r["t"] for r in rows if r["m"] == "k_e4b" and r["s"] == 3 and r["c"] == c}) for c in {r["c"] for r in rows if r["m"] == "k_e4b"}]
P["runs.e4b_seed3_range"] = f"{min(s3)} or {max(s3)}" if min(s3) != max(s3) else str(min(s3))
json.dump(P, open(os.path.join(ROOT, "results", "summary", "paper_stats.json"), "w"), indent=1, sort_keys=True)
if __name__ == "__main__": print(len(P), "paper claims")
