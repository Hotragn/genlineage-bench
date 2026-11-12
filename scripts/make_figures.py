"""Figures from results/summary (written by analyze.py). Usage: python scripts/make_figures.py [--sum results/summary] [--out ../figures]"""
import argparse, json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("--sum", default=os.path.join(ROOT, "results", "summary")); ap.add_argument("--out", default=os.path.join(ROOT, "..", "figures")); a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
CONDS = ["natural", "hint", "headerguard", "staticblock", "verify_tests", "verify", "lineage", "gate", "full"]
LAB = {"natural": "natural", "hint": "hint", "headerguard": "HeaderGuard", "staticblock": "StaticBlock", "verify_tests": "VerifyTests", "verify": "V", "lineage": "R", "gate": "R+G", "full": "R+G+V"}
S = json.load(open(os.path.join(a.sum, "summary.json"))); T = json.load(open(os.path.join(a.sum, "taxonomy.json")))
models = sorted({k.split("|")[0] for k in S}, key=lambda m: {"k_e2b": 0, "k_e4b": 1, "k_12b": 2, "k_31b": 3}.get(m, 9))
MN = {"k_e2b": "Gemma 4 E2B", "k_e4b": "Gemma 4 E4B", "k_12b": "Gemma 4 12B", "k_31b": "Gemma 4 31B"}
# Fig 2: immediate vs durable on regeneration tasks
fig, axs = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.6), sharey=True, squeeze=False)
for ax, m in zip(axs[0], models):
    cs = [c for c in CONDS if f"{m}|{c}" in S]; x = range(len(cs))
    for off, key, col, lab in ((-0.2, "ISR_regen", "#bbbbbb", "passes tests now"), (0.2, "DRR_regen", "#1f5fa8", "passes after make gen")):
        v = [S[f"{m}|{c}"][key] for c in cs]
        ax.bar([i + off for i in x], [p[0] for p in v], 0.4, color=col, label=lab,
               yerr=[[p[0] - p[1] for p in v], [p[2] - p[0] for p in v]], capsize=2, error_kw=dict(lw=0.8))
    ax.set_xticks(list(x)); ax.set_xticklabels([LAB[c] for c in cs], rotation=55, ha="right", fontsize=8)
    ax.set_title(f"{MN.get(m, m)} ({T[f'{m}|{cs[0]}']['n']} regeneration-task runs per condition)", fontsize=8); ax.set_ylim(0, 1.05)
axs[0][0].set_ylabel("rate on regeneration tasks"); axs[0][0].legend(fontsize=7, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(a.out, "fig2_immediate_vs_durable.png"), dpi=200); plt.close(fig)
# Fig 3: outcome taxonomy
CATS = [("durable", "#1f5fa8", "durable fix"), ("lost_generated_only", "#d9534f", "edited generated file only, lost"), ("lost_other", "#f0ad4e", "other, lost on regen"),
        ("fail_touched_upstream", "#9fc5e8", "edited source, tests fail"), ("fail_other_edit", "#cccccc", "other edit, tests fail"), ("fail_no_edit", "#eeeeee", "no edit"), ("tamper", "#000000", "tests or build tampered")]
fig, axs = plt.subplots(1, len(models), figsize=(4.2 * len(models), 3.6), sharey=True, squeeze=False)
for ax, m in zip(axs[0], models):
    cs = [c for c in CONDS if f"{m}|{c}" in T]; bottom = [0] * len(cs)
    for cat, col, lab in CATS:
        v = [T[f"{m}|{c}"]["cats"].get(cat, 0) / max(1, T[f"{m}|{c}"]["n"]) for c in cs]
        ax.bar(range(len(cs)), v, 0.7, bottom=bottom, color=col, label=lab, edgecolor="white", lw=0.3); bottom = [b + y for b, y in zip(bottom, v)]
    ax.set_xticks(range(len(cs))); ax.set_xticklabels([LAB[c] for c in cs], rotation=55, ha="right", fontsize=8); ax.set_title(MN.get(m, m), fontsize=9)
axs[0][0].set_ylabel("share of runs (regeneration tasks)"); axs[0][-1].legend(fontsize=6, loc="center left", bbox_to_anchor=(1, 0.5))
fig.tight_layout(); fig.savefig(os.path.join(a.out, "fig3_outcomes.png"), dpi=200); plt.close(fig)
print("wrote", os.listdir(a.out))
# Fig 4: signal-dose ladder on regeneration tasks (first rungs are subsets of the natural runs)
F = json.load(open(os.path.join(a.sum, "factors.json")))
fig, ax = plt.subplots(figsize=(7.5, 3.4))
for m, mk in zip(models, "osD^"):
    rungs = [("no header\n(natural)", F.get(f"{m}|natural|header=False", {}).get("DRR")), ("header\n(natural)", F.get(f"{m}|natural|header=True", {}).get("DRR")),
             ("AGENTS.md\n(natural)", F.get(f"{m}|natural|agents_md=True", {}).get("DRR")), ("prompt hint", S.get(f"{m}|hint", {}).get("DRR_regen", [None])[0]),
             ("HeaderGuard", S.get(f"{m}|headerguard", {}).get("DRR_regen", [None])[0]), ("R banners", S.get(f"{m}|lineage", {}).get("DRR_regen", [None])[0]),
             ("R+G gate", S.get(f"{m}|gate", {}).get("DRR_regen", [None])[0]), ("R+G+V", S.get(f"{m}|full", {}).get("DRR_regen", [None])[0])]
    xs = [i for i, (_, v) in enumerate(rungs) if v is not None]; ys = [v for _, v in rungs if v is not None]
    ax.plot(xs, ys, marker=mk, label=MN.get(m, m)); labels = [r for r, _ in rungs]
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontsize=7); ax.set_ylim(0, 1.05); ax.set_ylabel("durable repair rate"); ax.legend(fontsize=7)
ax.set_title("Signal ladder on regeneration tasks (first three rungs: subsets of natural runs)", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(a.out, "fig4_ladder.png"), dpi=200); plt.close(fig); print("fig4 ok")
