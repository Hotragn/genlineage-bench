"""Figure 3 of the paper: per model and condition, immediate pass rate vs preregistered DRR (bars, 95% task-clustered CI)
and strict DRR (tick), on the 13 regen+mixed tasks, seeds 1 and 2. Reads raw transcripts via paper_stats helpers.
Usage: python scripts/paper_figures.py [OUT_DIR]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fig_style as F
import matplotlib.pyplot as plt
import paper_stats as S
F.setup(9)
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(S.ROOT, "paper", "figures"); os.makedirs(out, exist_ok=True)
LAB = {"natural": "natural", "hint": "hint", "headerguard": "HeaderGuard", "staticblock": "StaticBlock", "verify_tests": "VerifyTests", "verify": "V", "lineage": "R", "gate": "R+G", "full": "R+G+V"}
ORDER = ["natural", "hint", "headerguard", "staticblock", "verify_tests", "verify", "lineage", "gate", "full"]
fig, axs = plt.subplots(1, 3, figsize=(9.3, 3.3), sharey=True, gridspec_kw=dict(width_ratios=[5, 9, 5], wspace=0.08))
for ax, m in zip(axs, S.MODELS):
    cs = [c for c in ORDER if S.sel(m, c)]
    ax.grid(axis="y"); ax.set_axisbelow(True)
    for i, c in enumerate(cs):
        rs = S.sel(m, c); n = len(rs); imm = sum(r["imm"] for r in rs) / n; d = S.boot(rs, "dur"); st = sum(r["strict"] for r in rs) / n
        ax.bar(i - 0.2, imm, 0.38, color=F.GREY, label="passes tests now (ISR)" if i == 0 else None)
        ax.bar(i + 0.2, d[0], 0.38, color=F.BLUE, yerr=[[d[0] - d[1]], [d[2] - d[0]]], capsize=2,
               error_kw=dict(lw=0.7, ecolor=F.INK), label="passes after make gen (DRR)" if i == 0 else None)
        ax.plot([i + 0.03, i + 0.37], [st, st], color=F.RED, lw=1.8, solid_capstyle="butt", label="strict DRR (before and after)" if i == 0 else None)
    ax.set_xticks(range(len(cs))); ax.set_xticklabels([LAB[c] for c in cs], rotation=40, ha="right")
    ax.set_title(f"Gemma 4 {S.MN[m]}"); ax.set_ylim(0, 1.05); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0]); ax.set_yticklabels(["0", "25", "50", "75", "100"])
    ax.tick_params(axis="x", length=0)
    if m != S.MODELS[0]: ax.tick_params(axis="y", length=0)
axs[0].set_ylabel("share of runs (%)")
h, l = axs[0].get_legend_handles_labels(); o = [l.index(x) for x in ("passes tests now (ISR)", "passes after make gen (DRR)", "strict DRR (before and after)")]
fig.legend([h[i] for i in o], [l[i] for i in o], loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.06))
p = os.path.join(out, "fig3_immediate_vs_durable.png"); fig.savefig(p); print("wrote", p)
