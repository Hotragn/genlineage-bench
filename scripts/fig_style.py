"""Shared look for every paper figure: one sans-serif font, three muted colors, thin lines, light grid.
Diagrams use plain boxes and straight or right-angle arrows, drawn the way one would in draw.io."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle

INK = "#2E3440"      # text and lines
BLUE = "#3B6EA5"     # durable / LineageGuard
BLUE_L = "#E4ECF5"
RED = "#B5523B"      # lost on regeneration
RED_L = "#F5E4DF"
GREY = "#BFC3C9"
GREY_L = "#F2F2F0"

_FONT = "DejaVu Sans"
for name in ("Liberation Sans", "Arial", "Helvetica"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        _FONT = name; break

def setup(size=9):
    plt.rcParams.update({
        "font.family": _FONT, "font.size": size, "axes.titlesize": size + 0.5, "axes.labelsize": size,
        "xtick.labelsize": size - 0.5, "ytick.labelsize": size - 0.5, "legend.fontsize": size - 1,
        "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
        "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "grid.color": "#DADDE1", "grid.linewidth": 0.5,
        "legend.frameon": False, "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
        "axes.titleweight": "normal", "axes.titlelocation": "left"})

def box(ax, x, y, w, h, text, fc="white", ec=INK, lw=0.9, size=8.5, weight="normal", dashed=False, align="center", r=0.04):
    """Plain box with a small corner radius, like a draw.io rounded rectangle. (x, y) is the lower-left corner."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw,
                                ls=(0, (4, 3)) if dashed else "-"))
    if text:
        tx = x + w / 2 if align == "center" else x + 0.08
        ax.text(tx, y + h / 2, text, ha=align, va="center", fontsize=size, weight=weight, linespacing=1.35)
    return (x, y, w, h)

def arrow(ax, pts, color=INK, lw=0.9, label=None, label_at=0, dx=0.0, dy=0.07, size=7.5, dashed=False, ha="center"):
    """Polyline through pts with an arrowhead at the end; use only horizontal and vertical segments."""
    ls = (0, (4, 3)) if dashed else "-"
    for (x1, y1), (x2, y2) in zip(pts[:-2], pts[1:-1]):
        ax.plot([x1, x2], [y1, y2], color=color, lw=lw, ls=ls, solid_capstyle="butt")
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0))
    if label:
        (x1, y1), (x2, y2) = pts[label_at], pts[label_at + 1]
        ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, label, ha=ha, va="bottom", fontsize=size, color=color)

def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off"); ax.set_aspect("equal")
    return fig, ax
