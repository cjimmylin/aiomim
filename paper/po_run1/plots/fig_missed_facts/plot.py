"""fig_missed_facts: where the OMIM facts direct reading did not fully convey went.
Data: experimental_log.md Section 3, first table (97 entries, 466 OMIM paragraphs).
Print size: 2.4 in wide (beside fig_hidden_fulltext, same height); all text >= 7 pt."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 2.5, "xtick.major.pad": 1.5,
})

levels = ["Full text", "Abstract only", "Title only"]
facts = [1837, 4282, 379]
conveyed = [1329, 1420, 38]
not_fully = [501, 2837, 341]
in_text = [245, 46, 0]
partly = [134, 632, 53]
not_in_text = [122, 2159, 288]
share_missed_in_text = ["49%", "2%", "0%"]  # log column "In text, share of missed"
contradicted = [f - c - m for f, c, m in zip(facts, conveyed, not_fully)]  # log: remainder contradicted
for i in range(3):
    assert in_text[i] + partly[i] + not_in_text[i] == not_fully[i]

# outcome colours shared with fig_hidden_fulltext; the key category (missed although stated) is highlighted
HIGHLIGHT = "#F0E442"
segments = [
    ("Conveyed", conveyed, "#555555", "white"),
    ("Missed, in text", in_text, HIGHLIGHT, "black"),
    ("Missed, partly in text", partly, "#A8A8A8", "black"),
    ("Missed, not in text", not_in_text, "#DEDEDE", "black"),
    ("Contradicted", contradicted, "#CC79A7", "white"),
]

fig, ax = plt.subplots(figsize=(2.4, 2.3), layout="constrained")
fig.get_layout_engine().set(w_pad=0.02, h_pad=0.02)
ypos = [2, 1, 0]
BH = 0.42
left = [0.0, 0.0, 0.0]
for label, vals, color, tcol in segments:
    pct = [100.0 * v / f for v, f in zip(vals, facts)]
    ax.barh(ypos, pct, left=left, color=color, height=BH, label=label, edgecolor="white", linewidth=0.4)
    for y, l, p in zip(ypos, left, pct):
        if p >= 9.5:  # smaller segments are left unlabelled (too narrow at print size)
            ax.text(l + p / 2, y, f"{p:.0f}%", ha="center", va="center", color=tcol, fontsize=7)
    left = [l + p for l, p in zip(left, pct)]

# one line above each bar: access level and n (left), share of missed facts stated in the text (right)
for y, lev, n, s in zip(ypos, levels, facts, share_missed_in_text):
    top = y + BH / 2
    ax.annotate(f"{lev}, n = {n:,}", (0, top), xytext=(0, 1.5), textcoords="offset points",
                ha="left", va="bottom", fontweight="bold")
    ax.annotate(f"in text: {s} of missed", (100, top), xytext=(0, 1.5), textcoords="offset points",
                ha="right", va="bottom")

ax.set_yticks([])
ax.set_xlim(0, 100)
ax.set_ylim(-0.3, 2.5)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("Share of OMIM facts")
ax.spines[["top", "right", "left"]].set_visible(False)
handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc="outside upper left", ncol=2, frameon=False, handlelength=0.9,
           handleheight=0.9, handletextpad=0.35, columnspacing=0.6, labelspacing=0.25, borderaxespad=0.1)

fig.savefig(os.environ["PO_OUT"], dpi=300, facecolor="white")
