"""Flatten every reportable number into named claims (results/summary/claims.json).
Used by render_writeup.py ({{c:key}} placeholders) and check_claims.py."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p, d=None):
    p = os.path.join(ROOT, p)
    return json.load(open(p)) if os.path.exists(p) else d
def pct(x): return f"{100 * x:.0f}%"
def ci(t): return f"{100 * t[0]:.0f}% [{100 * t[1]:.0f}, {100 * t[2]:.0f}]"
def build():
    S = load("results/summary/summary.json", {}); T = load("results/summary/tests.json", {}); X = load("results/summary/taxonomy.json", {})
    F = load("results/summary/factors.json", {}); rows = load("results/summary/rows.json", [])
    C = {}
    for k, v in S.items():
        m, c = k.split("|"); p = f"{m}.{c}"
        C[f"{p}.n"] = str(v["n"]); C[f"{p}.seeds"] = ",".join(map(str, v["seeds"]))
        for key in ("ISR_regen", "DRR_regen", "DRR_control", "DRR_inregion", "ISR_all", "DRR_all", "hgen_regen", "root_regen", "lost_regen", "strict_regen"):
            C[f"{p}.{key}"] = pct(v[key][0]); C[f"{p}.{key}_ci"] = ci(v[key])
        regen = [r for r in rows if r["model"] == m and r["cond"] == c and r["kind"] in ("regen", "mixed")]
        imm = sum(r["imm"] for r in regen); lost = sum(r["lost"] for r in regen)
        C[f"{p}.imm_count"] = str(imm); C[f"{p}.lost_count"] = str(lost); C[f"{p}.regen_runs"] = str(len(regen))
        C[f"{p}.DFR"] = pct(lost / imm) if imm else "n/a"
        C[f"{p}.latent"] = str(v["latent_regen"]); C[f"{p}.tamper"] = str(v["tamper"]); C[f"{p}.build_tamper"] = str(v["build_tamper"])
        C[f"{p}.steps"] = f"{v['mean_steps']:.1f}"; C[f"{p}.wall"] = f"{v['mean_wall']:.0f}"; C[f"{p}.tokens"] = f"{v['mean_tokens']:,}"
    for k, v in T.items():
        if not v.get("n"): continue
        m, contrast, _ = k.split("|"); p = f"{m}.{contrast}"
        C[f"{p}.diff"] = f"{100 * v['diff']:+.0f} points"; C[f"{p}.ci"] = f"[{100 * v['ci'][0]:+.0f}, {100 * v['ci'][1]:+.0f}]"
        C[f"{p}.p"] = f"{v['mcnemar_p']:.3g}" if v["mcnemar_p"] >= 0.001 else "<0.001"
        C[f"{p}.perm_p"] = f"{v['perm_p']:.3g}" if v["perm_p"] >= 0.001 else "<0.001"
        if "holm_p" in v: C[f"{p}.holm_p"] = f"{v['holm_p']:.3g}" if v["holm_p"] >= 0.001 else "<0.001"
        C[f"{p}.discordant"] = f"{v['a_only']}/{v['b_only']}"; C[f"{p}.pairs"] = str(v["n"]); C[f"{p}.tasks_up"] = str(v["tasks_up"]); C[f"{p}.tasks_down"] = str(v["tasks_down"])
    for k, v in X.items():
        m, c = k.split("|"); C[f"{m}.{c}.paid"] = str(v["tree_reward_paid"]); C[f"{m}.{c}.paid_lost"] = str(v["paid_but_lost"])
        C[f"{m}.{c}.paid_lost_pct"] = pct(v["paid_but_lost"] / v["tree_reward_paid"]) if v["tree_reward_paid"] else "n/a"
        for cat, n in v["cats"].items(): C[f"{m}.{c}.cat.{cat}"] = str(n)
    for k, v in F.items():
        m, c, f = k.split("|"); C[f"{m}.{c}.{f}.DRR"] = pct(v["DRR"]); C[f"{m}.{c}.{f}.ISR"] = pct(v["ISR"]); C[f"{m}.{c}.{f}.n"] = str(v["n"])
    LD = load("results/summary/ladder.json", None)
    if LD:
        C["ladder.pairs"] = str(LD["complete_pairs"]); C["ladder.tasks"] = str(LD["tasks"]); C["ladder.seeds"] = ",".join(map(str, LD["seeds"]))
        for l, v in LD["level"].items():
            for k, x in v.items(): C[f"ladder.{l}.{k}"] = str(x)
        for k, v in LD["tests"].items(): C[f"ladder.{k}.p"] = f"{v['p']:.3g}"; C[f"ladder.{k}.discordant"] = f"{v['a_only']}/{v['b_only']}"
    infra = load("results/summary/infra_errors.json", [])
    for m in sorted({r["model"] for r in rows}):
        rm = [r for r in rows if r["model"] == m]; C[f"{m}.runs"] = str(len(rm)); C[f"{m}.seeds"] = ",".join(map(str, sorted({r["seed"] for r in rm})))
        C[f"{m}.infra"] = str(sum(1 for x in infra if x["model"] == m))
    C["infra.total"] = str(len(infra))
    MN = {"k_e2b": "E2B", "k_e4b": "E4B", "k_12b": "12B"}; LB = {"natural": "natural", "hint": "hint", "headerguard": "HeaderGuard", "staticblock": "StaticBlock", "verify_tests": "VerifyTests", "verify": "V", "lineage": "R", "gate": "R+G", "full": "R+G+V"}
    def ptab(specs):
        out = ["| Model | Contrast (A vs B) | DRR change, B minus A, points [95% CI] | pairs (A only / B only) | McNemar p (Holm) | task perm. p |", "|---|---|---|---|---|---|"]
        for m in ("k_e2b", "k_e4b", "k_12b"):
            for a_, b_ in specs:
                v = T.get(f"{m}|{a_}_vs_{b_}|dur")
                if not v or not v.get("n"): continue
                fp = lambda x: f"{x:.3g}" if x >= 0.001 else "<0.001"
                pp = fp(v["mcnemar_p"]) + (f" ({fp(v['holm_p'])})" if "holm_p" in v else "")
                out.append(f"| {MN[m]} | {LB[a_]} vs {LB[b_]} | {100 * v['diff']:+.0f} [{100 * v['ci'][0]:+.0f}, {100 * v['ci'][1]:+.0f}] | {v['n']} ({v['a_only']} / {v['b_only']}) | {pp} | {fp(v['perm_p'])} |")
        return "\n".join(out)
    def stab(specs):
        out = ["| Model | A vs B | DRR change [95% CI] | perm. p | McNemar p (Holm) |", "|---|---|---|---|---|"]
        for m in ("k_e2b", "k_e4b", "k_12b"):
            for a_, b_ in specs:
                v = T.get(f"{m}|{a_}_vs_{b_}|dur")
                if not v or not v.get("n"): continue
                fp = lambda x: f"{x:.3g}" if x >= 0.001 else "<0.001"
                out.append(f"| {MN[m]} | {LB[a_]} vs {LB[b_]} | {100 * v['diff']:+.0f} [{100 * v['ci'][0]:+.0f}, {100 * v['ci'][1]:+.0f}] | {fp(v['perm_p'])} | {fp(v['mcnemar_p'])}" + (f" ({fp(v['holm_p'])})" if "holm_p" in v else "") + " |")
        return "\n".join(out)
    C["table.primary_short"] = stab([("natural", "full"), ("headerguard", "full"), ("hint", "full"), ("headerguard", "gate")])
    C["table.primary"] = ptab([("natural", "full"), ("headerguard", "full"), ("hint", "full"), ("headerguard", "gate")])
    C["table.ablation"] = ptab([("staticblock", "gate"), ("lineage", "gate"), ("verify_tests", "verify"), ("verify", "full"), ("natural", "headerguard"), ("natural", "hint")])
    C["runs.total"] = str(len(rows))
    return C
if __name__ == "__main__":
    C = build(); os.makedirs(os.path.join(ROOT, "results", "summary"), exist_ok=True)
    json.dump(C, open(os.path.join(ROOT, "results", "summary", "claims.json"), "w"), indent=1, sort_keys=True); print(len(C), "claims")
