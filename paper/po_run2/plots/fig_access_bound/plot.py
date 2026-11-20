"""fig_access_bound: access to the source bounds what a reading strategy can convey.

Printed at full ICLR text width (5.5 in), so the figure is drawn at 5.5 in and every text element is >= 7 pt in print.
All values copied from RUN/raw_materials/experimental_log.md:
  (a) Sec. 6.2, sentence 'OMIM facts conveyed on the fixed fact lists' and the 'Repair parity' paragraph: direct
      reading, same 46 entries / 136 paragraphs / 2,120 fixed facts in every bar, MEAN OVER ENTRIES; the full-text bar
      is the draft BEFORE the repair round, so no bar is repaired (like for like).
  (b) Sec. 2.10a, table 'The facts, by availability': the 6,239 fixed facts of the 93 compared entries, POOLED OVER
      FACTS, by how the paper was readable and whether the supplied text states the fact.
  (c) Sec. 2.10a, table 'Summary: mean over entries', columns 'Stated' (89 entries) and 'Not stated' (90 entries).
Strategy colours: binding shared palette (one colour per strategy in every figure). Greys = availability only.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

FS = 7  # every text element; panel letters 8 pt bold
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS, "legend.fontsize": FS,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
    "axes.labelpad": 2.0, "hatch.linewidth": 0.6, "pdf.fonttype": 42, "svg.fonttype": "none",
})

# shared strategy palette (binding)
COL = {
    "Direct reading": "#0072B2",
    "Agentic curator": "#56B4E9",
    "Evidence graph": "#009E73",
    "Case table first": "#D55E00",
    "Recall, then verify": "#E69F00",
    "Memory only (control)": "#000000",
}
DIRECT = COL["Direct reading"]
# availability greys (never a strategy colour)
G_STATED, G_PARTLY, G_HATCH = "#3B3B3B", "#9E9E9E", "#8C8C8C"
GRID = "#E6E6E6"

# ---------------------------------------------------------------- data (copied from the log)
# (a) log Sec. 6.2, mean over 46 entries; full text = before the repair round (79.8%, 'Repair parity')
A_LABELS = ["Abstract\nonly", "Abstract +\nsecond-\nhand", "Full text"]
A_VALUES = [36.1, 40.9, 79.8]

# (b) log Sec. 2.10a 'The facts, by availability' (pooled over facts)
B_LEVELS = ["Full text", "Abstract only", "Title only"]
B_FACTS = [1639, 4221, 379]
B_STATED = [1246, 1099, 27]
B_PARTLY = [253, 883, 62]
B_NOT = [140, 2239, 290]
for f, s, p, n in zip(B_FACTS, B_STATED, B_PARTLY, B_NOT):
    assert s + p + n == f  # unjudged = 0 in every row
assert sum(B_FACTS) == 6239 and sum(B_STATED) == 2372 and sum(B_PARTLY) == 1198 and sum(B_NOT) == 2669

# (c) log Sec. 2.10a 'Summary: mean over entries' (Stated n = 89 entries, Not stated n = 90 entries)
C_ROWS = ["Direct reading", "Agentic curator", "Evidence graph", "Case table first", "Recall, then verify",
          "Memory only (control)"]
C_TICKS = [r.replace(" (control)", "\n(control)") for r in C_ROWS]  # two lines: keeps the label column narrow
C_STATED = [94.4, 93.6, 94.2, 91.0, 28.8, 23.3]
C_NOT = [6.9, 6.3, 5.5, 5.9, 2.1, 8.2]

# ---------------------------------------------------------------- figure
fig = plt.figure(figsize=(5.5, 2.36), layout="constrained")
fig.get_layout_engine().set(w_pad=0.03, h_pad=0.02, wspace=0.06)
gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.0, 1.16])
axa, axb, axc = (fig.add_subplot(gs[0, i]) for i in range(3))

# ---- (a) vertical bars, direct reading in its strategy colour; fill encodes what was readable
xa = [0, 1, 2]
styles = [dict(facecolor="white", edgecolor=DIRECT, hatch=None),
          dict(facecolor="white", edgecolor=DIRECT, hatch="////"),
          dict(facecolor=DIRECT, edgecolor=DIRECT, hatch=None)]
for x, v, st in zip(xa, A_VALUES, styles):
    axa.bar(x, v, width=0.62, linewidth=0.9, zorder=2, **st)
    axa.text(x, v + 2.0, f"{v:.1f}%", ha="center", va="bottom", fontsize=FS)
axa.set_xticks(xa, A_LABELS)
axa.tick_params(axis="x", length=0)
axa.set_xlim(-0.41, 2.41)
axa.set_ylim(0, 100)
axa.set_yticks([0, 25, 50, 75, 100])
axa.set_ylabel("% of fixed facts conveyed")
axa.yaxis.grid(True, color=GRID, linewidth=0.4, zorder=0)
axa.set_axisbelow(True)
axa.spines[["top", "right"]].set_visible(False)

# ---- (b) horizontal 100%-stacked bars (pooled over facts)
yb = [2, 1, 0]  # top to bottom: full text, abstract only, title only
BH = 0.58
left = [0.0, 0.0, 0.0]
segs = [
    ("Stated", B_STATED, dict(facecolor=G_STATED, edgecolor="white", hatch=None), "white"),
    ("Partly stated", B_PARTLY, dict(facecolor=G_PARTLY, edgecolor="white", hatch=None), "black"),
    ("Not stated", B_NOT, dict(facecolor="white", edgecolor=G_HATCH, hatch="\\\\\\\\"), "black"),
]
seg_labels = []  # (text artist, segment left, segment width) -> fitted after layout
for name, vals, st, tcol in segs:
    pct = [100.0 * v / f for v, f in zip(vals, B_FACTS)]
    axb.barh(yb, pct, left=left, height=BH, linewidth=0.5, label=name, **st)
    for y, l, p in zip(yb, left, pct):
        bbox = dict(boxstyle="square,pad=0.08", facecolor="white", edgecolor="none") if st["hatch"] else None
        t = axb.text(l + p / 2, y, f"{p:.0f}", ha="center", va="center", color=tcol, fontsize=FS, bbox=bbox)
        seg_labels.append((t, l, p))
    left = [l + p for l, p in zip(left, pct)]
assert all(abs(l - 100.0) < 1e-9 for l in left)
axb.set_yticks(yb, [f"{lev}\n{n:,} facts" for lev, n in zip(B_LEVELS, B_FACTS)])
axb.tick_params(axis="y", length=0)
axb.set_xlim(0, 100)
axb.set_ylim(-0.45, 3.0)
axb.set_xticks([0, 25, 50, 75, 100])
axb.set_xlabel("% of fixed facts")
axb.spines[["top", "right", "left"]].set_visible(False)
# anchored right during layout so it stays inside the row-label margin; left-aligned with the labels after layout
hb, lb = axb.get_legend_handles_labels()
order = [0, 2, 1]  # matplotlib fills legend columns first: row 1 = Stated | Partly stated, row 2 = Not stated
leg_b = axb.legend([hb[i] for i in order], [lb[i] for i in order], loc="upper right", bbox_to_anchor=(1.0, 1.0),
                   ncol=2, frameon=False, handlelength=1.0,
                   handleheight=0.9, handletextpad=0.3, columnspacing=0.8, labelspacing=0.3, borderaxespad=0.0,
                   borderpad=0.0)

# ---- (c) dumbbell, one row per strategy (means over entries)
yc = list(range(len(C_ROWS)))[::-1]  # direct reading on top
for y, name, s, n in zip(yc, C_ROWS, C_STATED, C_NOT):
    c = COL[name]
    axc.plot([n, s], [y, y], color=c, linewidth=0.9, zorder=2, solid_capstyle="butt")
    axc.plot([s], [y], marker="o", markersize=5, color=c, markeredgecolor=c, linestyle="none", zorder=3,
             clip_on=False)
    axc.plot([n], [y], marker="o", markersize=5, markerfacecolor="white", markeredgecolor=c,
             markeredgewidth=1.0, linestyle="none", zorder=3, clip_on=False)
axc.set_yticks(yc, C_TICKS)
axc.tick_params(axis="y", length=0, pad=6)  # clear of hollow markers drawn left of x = 0
axc.set_ylim(-0.6, len(C_ROWS) - 0.4)
axc.set_xlim(0, 100)
axc.set_xticks([0, 25, 50, 75, 100])
axc.set_xlabel("% of fixed facts conveyed")
axc.xaxis.grid(True, color=GRID, linewidth=0.4, zorder=0)
axc.set_axisbelow(True)
axc.spines[["top", "right", "left"]].set_visible(False)
handles = [Line2D([], [], marker="o", markersize=5, color=G_STATED, linestyle="none", label="Stated"),
           Line2D([], [], marker="o", markersize=5, markerfacecolor="white", markeredgecolor=G_STATED,
                  markeredgewidth=1.0, linestyle="none", label="Not stated")]
axc.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 0.02), frameon=False, handlelength=0.8,
           handletextpad=0.4, borderaxespad=0.0, borderpad=0.0, labelspacing=0.35)

# ---- panel letters: reserve space with left titles, then align them to the left edge of each panel's labels
letters = {}
for ax, letter in zip((axa, axb, axc), "abc"):
    letters[ax] = ax.set_title(f"({letter})", loc="left", fontsize=8, fontweight="bold", pad=6)

fig.canvas.draw()
fig.set_layout_engine("none")  # freeze the constrained layout before the fine adjustments below
renderer = fig.canvas.get_renderer()

# keep a percentage label only where it fits inside its segment (with a small margin)
for t, l, p in seg_labels:
    x0 = axb.transData.transform((l, 0))[0]
    x1 = axb.transData.transform((l + p, 0))[0]
    w = t.get_window_extent(renderer).width
    if w + 2 * 0.015 * fig.dpi > (x1 - x0):  # at least 0.015 in clear on each side
        t.set_visible(False)

for ax, title in letters.items():
    x_disp = ax.yaxis.get_tightbbox(renderer).x0
    x_axes = ax.transAxes.inverted().transform((x_disp, 0))[0]
    title.set_x(x_axes)
    if ax is axb:  # legend of (b) starts at the left edge of the row labels, under the panel letter
        leg_b.set_loc("upper left")
        leg_b.set_bbox_to_anchor((x_axes, 1.0), transform=axb.transAxes)

out = os.environ["PO_OUT"]
fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.02, facecolor="white")
fig.savefig(os.path.splitext(out)[0] + ".pdf", bbox_inches="tight", pad_inches=0.02, facecolor="white")
