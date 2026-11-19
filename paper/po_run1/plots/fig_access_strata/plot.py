"""fig_access_strata: paired difference from direct reading in OMIM facts conveyed, by access group.
Data: experimental_log.md Sec. 2.9 (OMIM facts conveyed) and Sec. 4.2 (replicate-noise half-widths).
Print size: 2.75 in wide (beside fig_memory_by_era, same height); all text >= 7 pt."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 2.5, "xtick.major.pad": 1.5,
})

groups = [  # (label, entries)
    ("No full text", 46),
    ("Under half\nfull text", 25),
    ("Half or more\nfull text", 21),
]
# strategy -> list of (estimate, lo, hi) per group, Sec. 2.9
data = {
    "Evidence graph":   [(-0.2, -1.1, 0.8), (-0.7, -2.6, 1.3), (-1.8, -4.4, 0.7)],
    "Agentic curator":  [(-0.1, -1.1, 0.7), (-0.4, -1.6, 0.8), (-2.0, -3.4, -0.7)],
    "Case table first": [(0.6, -0.3, 1.6), (-4.0, -6.3, -2.0), (-6.1, -8.3, -3.6)],
}
# Off scale (Sec. 2.9), not drawn: memory only (control) -18.1, -41.7, -59.6; recall, then verify -19.1, -42.5, -58.7
# one colour per strategy, shared by all figures
colors = {"Evidence graph": "#009E73", "Agentic curator": "#56B4E9", "Case table first": "#D55E00"}
offsets = {"Evidence graph": 0.26, "Agentic curator": 0.0, "Case table first": -0.26}

fig, ax = plt.subplots(figsize=(2.75, 2.4), layout="constrained")
fig.get_layout_engine().set(w_pad=0.02, h_pad=0.02)

# replicate-noise bands (Sec. 4.2)
ax.axvspan(-1.8, 1.8, color="0.5", alpha=0.10, lw=0, zorder=0)
ax.axvspan(-1.0, 1.0, color="0.5", alpha=0.22, lw=0, zorder=0)
ax.axvline(0, color="black", lw=0.6, zorder=1)
ax.text(1.05, 2.62, "±1.0", ha="left", va="bottom", color="0.3")
ax.text(-1.85, 2.62, "±1.8", ha="right", va="bottom", color="0.3")

ys = [2, 1, 0]
for s, vals in data.items():
    for y, (est, lo, hi) in zip(ys, vals):
        yy = y + offsets[s]
        ax.errorbar(est, yy, xerr=[[est - lo], [hi - est]], fmt="o", color=colors[s],
                    ms=3.2, elinewidth=1.1, capsize=1.6, capthick=0.8, zorder=3)
        lab = f"{est:+.1f}".replace("-", "−")
        if -1.2 < hi < 0:  # label would sit on the zero line: put it left of the interval instead
            ax.text(lo - 0.2, yy, lab, va="center", ha="right", fontsize=7, color="0.15")
        else:
            ax.text(hi + 0.2, yy, lab, va="center", ha="left", fontsize=7, color="0.15")

for y in (0.5, 1.5):
    ax.axhline(y, color="0.7", lw=0.5, ls=":")

ax.set_yticks(ys)
ax.set_yticklabels([f"{g}\nn = {n}" for g, n in groups])
ax.set_ylim(-0.48, 2.8)
ax.set_xlim(-9.0, 3.2)
ax.set_xticks([-8, -6, -4, -2, 0, 2])
ax.set_xticklabels([f"{t}".replace("-", "−") for t in [-8, -6, -4, -2, 0, 2]])
ax.set_xlabel("Difference from direct reading (pp)")
ax.grid(axis="x", color="0.9", lw=0.4, zorder=0)
ax.set_axisbelow(True)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.tick_params(axis="y", length=0)

handles = [Line2D([], [], marker="o", color=colors[s], ls="-", lw=1.1, ms=3.2, label=s) for s in data]
ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 0.97), frameon=False, handlelength=1.2,
          handletextpad=0.4, labelspacing=0.25, borderaxespad=0.1)

fig.savefig(os.environ["PO_OUT"], dpi=300, facecolor="white")
