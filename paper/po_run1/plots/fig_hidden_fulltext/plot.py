"""fig_hidden_fulltext: within-paper effect of access (hidden-full-text experiment).
Data: experimental_log.md Sec. 6.2, table 'OMIM-fact coverage on the frozen fact lists (main measure)'
and the paired-differences table under it. 46 entries, 136 paragraphs, 2,120 facts per condition."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "sans-serif", "font.size": 8,
                     "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"]})

conditions = ["Abstract only", "Abstract +\nsecond-hand passages", "Full text"]
present = [495, 629, 1513]
partial = [331, 297, 254]
absent = [1290, 1184, 343]
contradicted = [4, 10, 10]
facts = [2120, 2120, 2120]
coverage = ["31.2%", "36.7%", "77.4%"]  # log values
diff = [None, "+4.9 (+2.8 to +7.1)", "+43.9 (+38.5 to +49.3)"]  # pp, paired over 46 entries
bwt = [None, "33 better, 9 worse, 4 tied", "45 better, 0 worse, 1 tied"]  # entries, log

for i in range(3):
    assert present[i] + partial[i] + absent[i] + contradicted[i] == facts[i]
    assert f"{100 * (present[i] + partial[i] / 2) / facts[i]:.1f}%" == coverage[i]

# colours matched to fig_missed_facts (conveyed / partly stated / not in text / contradicted)
segments = [
    ("Present", present, "#009E73", "white"),
    ("Partly present", partial, "#E69F00", "black"),
    ("Absent", absent, "#BBBBBB", "black"),
    ("Contradicted", contradicted, "#000000", "white"),
]

N = 2120
fig, ax = plt.subplots(figsize=(5.5, 3.1), layout="constrained")
ypos = [2, 1, 0]
left = [0, 0, 0]
for label, vals, color, tcol in segments:
    ax.barh(ypos, vals, left=left, color=color, height=0.6, label=label,
            edgecolor="white", linewidth=0.5)
    for y, l, v in zip(ypos, left, vals):
        if v >= 200:
            ax.text(l + v / 2, y, f"{v:,}", ha="center", va="center", color=tcol,
                    fontsize=8 if v >= 300 else 7)
    left = [l + v for l, v in zip(left, vals)]

# coverage at bar end
x_cov = N + 40
for y, c in zip(ypos, coverage):
    ax.text(x_cov, y, c, ha="left", va="center", fontsize=9, fontweight="bold", clip_on=False)
ax.text(x_cov, 2.42, "Coverage", ha="left", va="bottom", fontsize=7.5, color="0.3", clip_on=False)

# paired difference from abstract only
x_d = N + 640
ax.text(x_d, 2.42, "Paired difference from\nabstract only, pp (95% CI)", ha="left", va="bottom",
        fontsize=7.5, color="0.3", linespacing=1.0, clip_on=False)
for y, d, b in zip(ypos, diff, bwt):
    if d is None:
        ax.text(x_d, y, "reference", ha="left", va="center", fontsize=8, color="0.3", clip_on=False)
    else:
        ax.text(x_d, y + 0.11, d, ha="left", va="center", fontsize=8, clip_on=False)
        ax.text(x_d, y - 0.17, f"entries: {b}", ha="left", va="center",
                fontsize=7, color="0.3", clip_on=False)

ax.set_yticks(ypos)
ax.set_yticklabels(conditions)
ax.set_xlim(0, N + 1950)
ax.set_ylim(-0.45, 2.45)
ax.spines["bottom"].set_bounds(0, N)
ax.set_xticks([0, 500, 1000, 1500, 2000, N])
ax.set_xticklabels(["0", "500", "1,000", "1,500", "", "2,120"])
ax.set_xlabel("OMIM facts (the same 2,120 facts judged in each condition)", loc="left")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="y", length=0)
handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc="outside upper left", ncol=4, frameon=False, fontsize=8,
           handlelength=1.0, handletextpad=0.4, columnspacing=1.2)

fig.savefig(os.environ["PO_OUT"], dpi=300, bbox_inches="tight", facecolor="white")
