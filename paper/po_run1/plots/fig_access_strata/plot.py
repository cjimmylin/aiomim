"""fig_access_strata: paired difference from direct reading in OMIM facts conveyed, by access group.
Data: experimental_log.md Sec. 2.9 (OMIM facts conveyed) and Sec. 4.2 (replicate-noise half-widths)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

groups = [  # (label, entries)
    ("No full text\n(abstracts only)", 46),
    ("Under half\nfull text", 25),
    ("Half or more\nfull text", 21),
]
# strategy -> list of (estimate, lo, hi) per group, Sec. 2.9
data = {
    "Evidence graph":   [(-0.2, -1.1, 0.8), (-0.7, -2.6, 1.3), (-1.8, -4.4, 0.7)],
    "Agentic curator":  [(-0.1, -1.1, 0.7), (-0.4, -1.6, 0.8), (-2.0, -3.4, -0.7)],
    "Case table first": [(0.6, -0.3, 1.6), (-4.0, -6.3, -2.0), (-6.1, -8.3, -3.6)],
}
colors = {"Evidence graph": "#0072B2", "Agentic curator": "#009E73", "Case table first": "#D55E00"}
offsets = {"Evidence graph": 0.25, "Agentic curator": 0.0, "Case table first": -0.25}

fig, ax = plt.subplots(figsize=(7.0, 3.94))

# replicate-noise bands (Sec. 4.2)
ax.axvspan(-1.8, 1.8, color="0.5", alpha=0.08, lw=0, zorder=0)
ax.axvspan(-1.0, 1.0, color="0.5", alpha=0.20, lw=0, zorder=0)
ax.axvline(0, color="black", lw=0.8, zorder=1)

ys = [2, 1, 0]
for s, vals in data.items():
    for y, (est, lo, hi) in zip(ys, vals):
        yy = y + offsets[s]
        ax.errorbar(est, yy, xerr=[[est - lo], [hi - est]], fmt="o", color=colors[s],
                    ms=5, elinewidth=1.6, capsize=2.5, capthick=1.2, zorder=3)
        ax.text(hi + 0.15, yy, f"{est:+.1f}".replace("-", "\u2212"), va="center", ha="left", fontsize=8, color=colors[s])

for y in (0.5, 1.5):
    ax.axhline(y, color="0.7", lw=0.6, ls=":")

ax.set_yticks(ys)
ax.set_yticklabels([f"{g}\nn = {n} entries" for g, n in groups])
ax.set_ylim(-0.55, 2.75)
ax.set_xlim(-9.0, 3.0)
ax.set_xlabel("Difference from direct reading in OMIM facts conveyed (percentage points)")
ax.grid(axis="x", color="0.9", lw=0.5, zorder=0)
ax.set_axisbelow(True)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.tick_params(axis="y", length=0)

handles = [Line2D([], [], marker="o", color=colors[s], ls="-", lw=1.6, ms=5, label=s) for s in data]
handles += [Patch(color="0.5", alpha=0.20, lw=0, label="Replicate noise, ±1.0 (93 entries)"),
            Patch(color="0.5", alpha=0.08, lw=0, label="Replicate noise, ±1.8 (30 entries)")]
handles = [handles[0], handles[3], handles[1], handles[4], handles[2]]  # rows: strategies / noise bands
ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.01), fontsize=8, frameon=False, ncol=3,
          columnspacing=1.2, handlelength=1.8)

note = ("Off scale (same groups, top to bottom):\n"
        "memory only (control): −18.1, −41.7, −59.6\n"
        "recall, then verify: −19.1, −42.5, −58.7")
ax.text(0.01, 0.99, note, transform=ax.transAxes, ha="left", va="top", fontsize=8, color="0.3")

fig.savefig(os.environ["PO_OUT"], dpi=300, bbox_inches="tight", facecolor="white")
