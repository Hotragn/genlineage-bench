"""Figures 1 and 2 of the paper: the disappearing-fix flow (task oa1_property_typo) and the LineageGuard overview.
Static diagrams, drawn with plain boxes and right-angle arrows. Usage: python scripts/fig_diagrams.py [OUT_DIR]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fig_style as S
from fig_style import box, arrow, canvas, INK, BLUE, BLUE_L, RED, RED_L, GREY_L
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "paper", "figures")
os.makedirs(OUT, exist_ok=True)
S.setup()

def fig1():
    W, H = 9.3, 3.3
    fig, ax = canvas(W, H)
    bw, bh, gap = 1.62, 0.78, 0.26
    # start: the issue
    box(ax, 0.05, 1.18, 1.25, 0.9, "Issue: a test\nfails on the\nfield emial", fc=GREY_L)
    ya, yb = 2.15, 0.3                      # lower edge of the two lanes
    x0 = 1.62
    xs = [x0 + i * (bw + gap) for i in range(4)]
    # lane labels
    ax.text(x0, ya + bh + 0.14, "Natural agent", fontsize=8.5, color=RED, ha="left")
    ax.text(x0, yb + bh + 0.14, "With the write gate (G)", fontsize=8.5, color=BLUE, ha="left")
    top = ["Edits the generated\nclient/models.py", "Tests pass\n(scored as solved)", "make gen rebuilds it\nfrom api/openapi.yaml", "Tests fail again:\nthe fix is lost"]
    bot = ["Tries the same edit\nto client/models.py", "Gate reruns make gen\nin a shadow copy", "Edit is reverted, so\nthe write is rejected\nwith a source pointer", "Fixes the source;\nafter make gen the\ntests pass: durable"]
    for i, (x, t, b) in enumerate(zip(xs, top, bot)):
        box(ax, x, ya, bw, bh, t, fc=RED_L if i == 3 else "white", ec=RED if i == 3 else INK)
        box(ax, x, yb, bw, bh + (0.16 if i >= 2 else 0), b, fc=BLUE_L if i == 3 else "white", ec=BLUE if i == 3 else INK)
        if i:
            arrow(ax, [(x - gap, ya + bh / 2), (x, ya + bh / 2)])
            arrow(ax, [(x - gap, yb + bh / 2 + (0.08 if i >= 3 else 0)), (x, yb + bh / 2 + (0.08 if i >= 3 else 0))], color=BLUE if i >= 2 else INK)
    xm = 1.30 + (x0 - 1.30) / 2
    ax.plot([1.30, xm], [1.63, 1.63], color=INK, lw=0.9)
    arrow(ax, [(xm, 1.63), (xm, ya + bh / 2), (x0, ya + bh / 2)])
    arrow(ax, [(xm, 1.63), (xm, yb + bh / 2), (x0, yb + bh / 2)])
    # the misleading score
    ax.text(xs[1] + bw / 2, ya - 0.1, "a score taken on the agent's tree stops here", fontsize=7.5, color=INK, ha="center", va="top", style="italic")
    fig.savefig(os.path.join(OUT, "fig1_disappearing_fix.png")); fig.savefig(os.path.join(OUT, "fig1_disappearing_fix.svg")); plt.close(fig)

def fig2():
    W, H = 9.3, 4.55
    fig, ax = canvas(W, H)
    # top row: task, agent, guard, lineage inference
    box(ax, 0.05, 2.55, 1.6, 1.9, "", fc=GREY_L)
    ax.text(0.85, 4.22, "Benchmark task", ha="center", fontsize=8.5, weight="bold")
    ax.text(0.17, 3.35, "issue text\nhand-owned code\ngenerator inputs\ngenerated files\ntests\nmake gen", ha="left", va="center", fontsize=8, linespacing=1.45)
    box(ax, 2.05, 2.95, 1.55, 1.1, "Gemma 4 agent\n(ollama, QAT)\nfile and shell tools", fc="white")
    # LineageGuard container
    box(ax, 4.25, 2.35, 2.6, 2.13, "", fc="white", ec=BLUE, dashed=True)
    ax.text(4.37, 4.3, "LineageGuard", fontsize=8.5, color=BLUE, weight="bold", ha="left", va="center")
    box(ax, 4.4, 3.58, 2.3, 0.58, "R  read: banner names the\ncommand and its inputs", fc=BLUE_L, ec=BLUE, size=7.8)
    box(ax, 4.4, 2.5, 2.3, 0.98, "G  write: apply in a shadow\ncopy, rerun the generator;\nreject only if reverted,\npoint to source lines", fc=BLUE_L, ec=BLUE, size=7.8)
    box(ax, 7.45, 2.8, 1.8, 1.4, "A  lineage inference\n(once per repository)\nwrite detection,\ndelete-one inputs,\nline map, noise mask", fc="white", ec=BLUE, size=7.8)
    # arrows on the top row
    arrow(ax, [(1.65, 3.5), (2.05, 3.5)])
    arrow(ax, [(3.6, 3.72), (4.25, 3.72)], label="tool calls", size=7)
    arrow(ax, [(4.25, 3.28), (3.6, 3.28)], label="results", dy=-0.24, size=7)
    arrow(ax, [(7.45, 3.5), (6.85, 3.5)], color=BLUE)
    ax.text(7.15, 3.58, "lineage", fontsize=7, color=BLUE, ha="center", va="bottom")
    # bottom row: durable scorer
    ax.text(1.0, 1.42, "Durable scorer (after the agent stops)", fontsize=8.5, weight="bold", ha="left")
    steps = ["restore tests and\nbuild files\n(SHA-256 checked)", "run tests\n(ISR)", "make gen\nin place", "run tests\nagain (DRR)"]
    sx, sw, sg, sy, sh = 0.05, 1.55, 0.32, 0.3, 0.85
    for i, t in enumerate(steps):
        x = sx + i * (sw + sg); box(ax, x, sy, sw, sh, t)
        if i: arrow(ax, [(x - sg, sy + sh / 2), (x, sy + sh / 2)])
    xe = sx + 4 * (sw + sg)
    arrow(ax, [(xe - sg, sy + sh / 2), (xe, sy + sh / 2)])
    box(ax, xe, sy + 0.47, 1.7, 0.38, "durable", fc=BLUE_L, ec=BLUE, size=8)
    box(ax, xe, sy, 1.7, 0.38, "lost or failed", fc=RED_L, ec=RED, size=8)
    # agent's final tree goes to the scorer
    arrow(ax, [(2.82, 2.95), (2.82, 2.2), (0.83, 2.2), (0.83, sy + sh)], label="final tree", label_at=1, dy=0.05, size=7)
    # V reuses the scorer's procedure
    box(ax, 4.4, 1.6, 2.3, 0.55, "V  on stop: regenerate, run tests,\nreturn failures (up to 2 rounds)", fc="white", ec=BLUE, size=7.4, dashed=True)
    arrow(ax, [(5.55, 2.35), (5.55, 2.15)], color=BLUE)
    vx = sx + 2 * (sw + sg) + sw / 2
    ax.plot([6.7, 7.2, 7.2], [1.875, 1.875, 1.32], color=BLUE, lw=0.9, ls=(0, (4, 3)))
    ax.plot([7.2, vx, vx], [1.32, 1.32, 1.22], color=BLUE, lw=0.9, ls=(0, (4, 3)))
    arrow(ax, [(vx, 1.22), (vx, sy + sh)], color=BLUE, dashed=True)
    ax.text(7.28, 1.6, "uses the scorer's steps:\noracle-in-the-loop", fontsize=7, color=BLUE, ha="left", va="center")
    fig.savefig(os.path.join(OUT, "fig2_overview.png")); fig.savefig(os.path.join(OUT, "fig2_overview.svg")); plt.close(fig)

fig1(); fig2(); print("wrote fig1_disappearing_fix and fig2_overview to", OUT)
