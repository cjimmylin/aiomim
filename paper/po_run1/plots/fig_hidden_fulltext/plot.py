"""fig_hidden_fulltext: within-paper effect of access (hidden-full-text experiment).
Data: experimental_log.md Sec. 6.2: the abstract-only and second-hand rows of 'OMIM-fact coverage on the frozen
fact lists (main measure)', the full text before the repair round ('Repair parity'), the means over entries in the
sentence 'OMIM facts conveyed on the fixed fact lists', and the paired differences (second-hand from the main table,
full text before repair from the repair-parity table). No arm went through the repair round. Bars: fact counts pooled
over 46 entries, 136 paragraphs, 2,120 facts per condition; printed percentages: means over the 46 entries.
Print size: 3.0 in wide (beside fig_missed_facts, same height); all text >= 7 pt."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 2.5, "xtick.major.pad": 1.5,
})

conditions = ["Abstract only", "Abstract + second-hand passages", "Full text, before repair"]
present = [495, 629, 1511]
partial = [331, 297, 255]
absent = [1290, 1184, 344]
contradicted = [4, 10, 10]
facts = [2120, 2120, 2120]
pooled = ["31.2%", "36.7%", "77.3%"]  # log, pooled over facts: checks the counts, not printed
mean_over_entries = ["36.1%", "40.9%", "79.8%"]  # log, mean of per-entry coverage over 46 entries: printed
diff = [None, "+4.9 (+2.8 to +7.1)", "+43.7 (+38.3 to +49.1)"]  # pp, paired over 46 entries
bwt = [None, "33 better, 9 worse, 4 tied", "45 better, 0 worse, 1 tied"]  # entries, log

for i in range(3):
    assert present[i] + partial[i] + absent[i] + contradicted[i] == facts[i]
    assert f"{100 * (present[i] + partial[i] / 2) / facts[i]:.1f}%" == pooled[i]

# outcome colours shared with fig_missed_facts; neutral greys so no strategy colour is reused
segments = [
    ("Present", present, "#555555", "white"),
    ("Partly present", partial, "#A8A8A8", "black"),
    ("Absent", absent, "#DEDEDE", "black"),
    ("Contradicted", contradicted, "#CC79A7", "white"),
]

N = 2120
fig, ax = plt.subplots(figsize=(3.0, 2.3), layout="constrained")
fig.get_layout_engine().set(w_pad=0.02, h_pad=0.02)
ypos = [2, 1, 0]
BH = 0.34
left = [0, 0, 0]
for label, vals, color, tcol in segments:
    ax.barh(ypos, vals, left=left, color=color, height=BH, label=label, edgecolor="white", linewidth=0.4)
    for y, l, v in zip(ypos, left, vals):
        if v >= 200:
            ax.text(l + v / 2, y, f"{v:,}", ha="center", va="center", color=tcol, fontsize=7)
    left = [l + v for l, v in zip(left, vals)]

# two text lines above each bar: condition + mean over entries, then paired difference from abstract only
for y, name, c, d in zip(ypos, conditions, mean_over_entries, diff):
    top = y + BH / 2
    ax.annotate(name, (0, top), xytext=(0, 10.5), textcoords="offset points", ha="left", va="bottom",
                fontweight="bold")
    ax.annotate(f"mean over entries {c}", (N, top), xytext=(0, 10.5), textcoords="offset points", ha="right",
                va="bottom", fontweight="bold")
    sub = "reference for the paired differences" if d is None else f"{d.split(' ')[0]} pp vs abstract only (95% CI {d.split('(')[1]}"
    ax.annotate(sub, (0, top), xytext=(0, 1.5), textcoords="offset points", ha="left", va="bottom",
                color="0.25")

ax.set_yticks([])
ax.set_xlim(0, N)
ax.set_ylim(-0.22, 2.74)
ax.set_xticks([0, 500, 1000, 1500, N])
ax.set_xticklabels(["0", "500", "1,000", "1,500", "2,120"])
ax.set_xlabel("OMIM facts (the same 2,120 in each condition)")
ax.spines[["top", "right", "left"]].set_visible(False)
handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc="outside upper left", ncol=4, frameon=False,
           handlelength=0.9, handleheight=0.9, handletextpad=0.35, columnspacing=0.8, borderaxespad=0.1)

fig.savefig(os.environ["PO_OUT"], dpi=300, facecolor="white")
