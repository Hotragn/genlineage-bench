"""Figure 4: exposure in AIDev agent PRs and the hand audit (from inthewild/out/summary.json and inthewild/sample_audit.csv)."""
import csv, json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fig_style as F
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "paper", "figures")
A = json.load(open(os.path.join(ROOT, "inthewild", "out", "summary.json")))["per_agent"]["ALL"]
jud = Counter(r["judgment"] for r in csv.DictReader(open(os.path.join(ROOT, "inthewild", "sample_audit.csv")))); n = sum(jud.values())
steps = [("agent PRs with file data\n(AIDev-pop, v5)", A["prs_with_file_data"]), ("touch a generated file", A["touch_gen_any"]),
         ("edit a generated file", A["edit_gen_any"]), ("edit one with no plausible\nsource change in the PR", A["edit_gen_nosrc"])]
F.setup(8)
fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.6, 2.2), gridspec_kw={"width_ratios": [2.3, 1]})
for i, (lbl, v) in enumerate(steps):
    y = len(steps) - 1 - i; ax.barh(y, v, height=0.62, color=F.BLUE)
    ax.text(v * 1.15, y, f"{v:,}" + ("" if i == 0 else f" ({100 * v / steps[i - 1][1]:.1f}% of previous)"), va="center", fontsize=7)
ax.set_xscale("log"); ax.set_xlim(500, steps[0][1] * 12); ax.set_yticks(range(len(steps))); ax.set_yticklabels([s for s, _ in reversed(steps)])
ax.set_xlabel("PRs (log scale)"); ax.set_title("Exposure in agent pull requests", loc="left")
order = [("hand_edit_lost", "hand edit lost on regeneration", F.RED), ("consistent_regen", "consistent with regeneration", F.BLUE),
         ("unclear", "unclear", F.GREY), ("not_generated", "not generated", "#E2E2DE")]
left = 0
for k, l, c in order:
    v = jud.get(k, 0)
    if v: bx.barh(0, v, left=left, height=0.5, color=c, edgecolor="white", hatch=""); bx.text(left + v / 2, -0.42, str(v), ha="center", va="top", fontsize=7); left += v
bx.set_xlim(0, n); bx.set_ylim(-1.1, 0.6); bx.axis("off")
bx.set_title(f"Hand audit, {n} sampled PR-file pairs:\n{jud.get('hand_edit_lost', 0)} judged lost on regeneration\n(2 confirmed in the net PR diff)", loc="left", fontsize=7.5)
bx.legend(handles=[Patch(facecolor=c, hatch="", edgecolor="white", label=l) for k, l, c in order if jud.get(k)],
          frameon=False, loc="upper left", bbox_to_anchor=(0, 0.12), fontsize=6.5, ncol=1)
fig.tight_layout(); os.makedirs(OUT, exist_ok=True); fig.savefig(os.path.join(OUT, "fig4_aidev.png")); print("wrote fig4_aidev.png", dict(jud))
