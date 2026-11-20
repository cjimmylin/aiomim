"""fig_design_vs_reading: differences from direct reading in OMIM facts conveyed (mean over entries, pp),
two separate comparisons drawn as two blocks.
  a: other designs minus direct reading AFTER repair, 93 entries      (experimental_log.md Sec. 2.10a)
  b: ways of reading better minus direct reading BEFORE repair,
     held-out entries with full text, 38 (D1-D3) or 35 (D4) entries    (experimental_log.md Sec. 15)
Print size: 5.5 in wide (ICLR text width, include at width=\\linewidth); all text >= 7 pt."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 2.5, "xtick.major.pad": 1.5,
    "svg.fonttype": "none", "pdf.fonttype": 42,
})

FACETS = ["All facts", "Stated,\nfull-text papers", "Stated,\nabstract-only papers", "Not stated"]

# (row label, colour, [(estimate, lo, hi) per facet]); facets in FACETS order
# Block a: Sec. 2.10a, "Difference from Direct reading" (mean over entries; 95% bootstrap interval)
BLOCK_A = [
    ("Agentic curator",  "#56B4E9", [(-0.6, -1.3, 0.0), (-0.2, -1.8, 1.2), (-0.8, -2.6, 0.5), (-0.5, -1.8, 1.0)]),
    ("Evidence graph",   "#009E73", [(-0.5, -1.5, 0.5), (1.7, -0.7, 4.0), (-0.5, -2.5, 1.2), (-1.4, -3.4, 0.7)]),
    ("Case table first", "#D55E00", [(-1.9, -3.1, -0.7), (-8.4, -14.3, -3.8), (-1.6, -3.6, 0.2), (-1.0, -3.1, 1.2)]),
]
# Block b: Sec. 15, D1-D3 from "Improving on direct reading: evaluation" (38 entries),
# D4 from "Extension: D4", row "D4 - baseline (primary)" (35 entries)
BLOCK_B = [
    ("Checklist (38)",          "#8C8C8C", [(1.6, 0.5, 2.7), (2.0, 0.4, 3.7), (0.2, -1.0, 1.3), (-0.3, -1.9, 1.3)]),
    ("Completeness pass (38)",  "#3D6F98", [(2.6, 1.7, 3.6), (4.5, 2.9, 6.3), (1.0, -0.3, 2.9), (-0.1, -1.3, 0.7)]),
    ("Three-draft merge (38)",  "#555555", [(3.1, 2.1, 4.2), (3.7, 2.1, 5.5), (1.0, 0.1, 2.1), (1.5, 0.4, 2.7)]),
    ("Checklist +\ncompleteness pass (35)", "#003A5E",
     [(3.3, 2.0, 4.7), (6.3, 4.0, 8.7), (1.5, -0.6, 3.9), (0.2, -1.2, 1.8)]),
]
# Not drawn (off scale, Sec. 2.10a): memory only (control) and recall, then verify, -34.0 to -77.6 on these facets.

# One common x SCALE (same inches per percentage point in every panel); each facet spans only the range its
# data need (all intervals lie inside), so short intervals are not squeezed by the one wide interval (-14.3).
XLIMS = [(-5.5, 6.0), (-15.0, 9.5), (-5.5, 5.5), (-5.5, 5.5)]
XTICKS = [[-5, 0, 5], [-10, -5, 0, 5], [-5, 0, 5], [-5, 0, 5]]

# ---- layout in inches (measured from the top of the figure) ----
W = 5.5
LEFT = 1.20            # panels start here (row labels to the left)
RIGHT = 5.44           # keeps the tight-cropped output <= 5.5 in, so 7 pt prints at 7 pt
GAP = 0.18             # between facet panels (room for edge tick labels of neighbouring panels)
PITCH = 0.205          # row pitch
SPAN = [hi - lo for lo, hi in XLIMS]
PPI = (RIGHT - LEFT - 3 * GAP) / sum(SPAN)          # inches per percentage point, all panels
PWS = [sp * PPI for sp in SPAN]                     # panel widths
X0S = [LEFT + sum(PWS[:j]) + j * GAP for j in range(4)]

TOP_COLHEAD = 0.0      # column headers (two lines)
A_HEAD = 0.30          # block a header baseline region
A_TOP = 0.44
A_H = len(BLOCK_A) * PITCH
B_HEAD = A_TOP + A_H + 0.43
B_TOP = B_HEAD + 0.14
B_H = len(BLOCK_B) * PITCH
H = B_TOP + B_H + 0.32

fig = plt.figure(figsize=(W, H))
fig.patch.set_facecolor("white")


def fy(y_from_top):
    return 1 - y_from_top / H


def fx(x):
    return x / W


def block(rows, top, height, marker, ms, xlabel, dotted_before=None):
    axes = []
    n = len(rows)
    for j in range(4):
        ax = fig.add_axes([fx(X0S[j]), fy(top + height), PWS[j] / W, height / H])
        ax.set_xlim(*XLIMS[j])
        ax.set_ylim(n - 0.5, -0.5)  # first row at top
        ax.axvline(0, color="black", lw=0.6, zorder=1)
        for gx in [t for t in XTICKS[j] if t != 0]:
            ax.axvline(gx, color="0.9", lw=0.4, zorder=0)
        if dotted_before is not None:
            ax.axhline(dotted_before - 0.5, color="0.6", lw=0.5, ls=(0, (1, 1.5)), zorder=0)
        for i, (lab, col, vals) in enumerate(rows):
            est, lo, hi = vals[j]
            ax.errorbar(est, i, xerr=[[est - lo], [hi - est]], fmt=marker, color=col, mec=col, mfc=col,
                        ms=ms, elinewidth=1.0, capsize=1.6, capthick=0.8, zorder=3)
        ax.set_xticks(XTICKS[j])
        ax.set_xticklabels([("+" if t > 0 else "") + f"{t}".replace("-", "\u2212") for t in XTICKS[j]])
        ax.set_yticks(range(n))
        if j == 0:
            ax.set_yticklabels([r[0] for r in rows])
        else:
            ax.set_yticklabels([])
        ax.tick_params(axis="y", length=0, pad=3)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        axes.append(ax)
    # x-axis label naming this block's baseline, centred under the four panels
    fig.text(fx((LEFT + RIGHT) / 2), fy(top + height + 0.27), xlabel, ha="center", va="bottom", fontsize=7)
    return axes


# column headers (facets), drawn once above block a
for j, f in enumerate(FACETS):
    xc = X0S[j] + PWS[j] / 2
    fig.text(fx(xc), fy(TOP_COLHEAD + 0.255), f, ha="center", va="bottom", fontsize=7.5, linespacing=1.15)

# block headers
fig.text(fx(0.02), fy(A_HEAD + 0.12), "a", ha="left", va="bottom", fontsize=8, fontweight="bold")
fig.text(fx(0.17), fy(A_HEAD + 0.12), "Other designs (93 entries)", ha="left", va="bottom", fontsize=7.5)
fig.text(fx(0.02), fy(B_HEAD + 0.12), "b", ha="left", va="bottom", fontsize=8, fontweight="bold")
fig.text(fx(0.17), fy(B_HEAD + 0.12), "Ways of reading better (held-out entries with full text)",
         ha="left", va="bottom", fontsize=7.5)
# thin rule separating the two blocks
sep_y = fy(B_HEAD - 0.06)
fig.add_artist(Line2D([fx(0.02), fx(RIGHT)], [sep_y, sep_y], color="0.6", lw=0.5))

block(BLOCK_A, A_TOP, A_H, "o", 2.7, "Difference from direct reading after repair (percentage points)")
block(BLOCK_B, B_TOP, B_H, "D", 2.6, "Difference from direct reading before repair (percentage points)",
      dotted_before=3)

out = os.environ["PO_OUT"]
fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.02)
root, ext = os.path.splitext(out)
if ext.lower() == ".png":
    fig.savefig(root + ".pdf", facecolor="white", bbox_inches="tight", pad_inches=0.02)
