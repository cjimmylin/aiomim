"""fig_missed_facts: where the OMIM facts direct reading did not fully convey went.
Data: experimental_log.md Section 3, first table (97 entries, 466 OMIM paragraphs)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "sans-serif", "font.size": 8,
                     "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"]})

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

segments = [
    ("Conveyed", conveyed, "#009E73", "white"),
    ("Missed, stated in available text", in_text, "#D55E00", "white"),
    ("Missed, partly stated", partly, "#E69F00", "black"),
    ("Missed, not in available text", not_in_text, "#BBBBBB", "black"),
    ("Contradicted", contradicted, "#000000", "white"),
]

fig, ax = plt.subplots(figsize=(3.4, 2.55), layout="constrained")
ypos = [2, 1, 0]
left = [0.0, 0.0, 0.0]
for label, vals, color, tcol in segments:
    pct = [100.0 * v / f for v, f in zip(vals, facts)]
    ax.barh(ypos, pct, left=left, color=color, height=0.62, label=label,
            edgecolor="white", linewidth=0.5)
    for y, l, p in zip(ypos, left, pct):
        if p >= 9.5:  # smaller segments are left unlabelled (too narrow at column width)
            ax.text(l + p / 2, y, f"{p:.0f}%", ha="center", va="center", color=tcol,
                    fontsize=8 if p >= 12 else 7)
    left = [l + p for l, p in zip(left, pct)]

for y, s in zip(ypos, share_missed_in_text):
    ax.text(108, y, s, ha="center", va="center", fontsize=8, color="#D55E00", clip_on=False)
ax.text(108, 2.34, "In text,\nshare of\nmissed", ha="center", va="bottom", fontsize=7,
        color="#D55E00", linespacing=0.95, clip_on=False)

ax.set_yticks(ypos)
ax.set_yticklabels([f"{l}\nn = {n:,}" for l, n in zip(levels, facts)])
ax.set_xlim(0, 115)
ax.spines["bottom"].set_bounds(0, 100)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("Share of OMIM facts")
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(axis="y", length=0)
handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc="outside upper center", ncol=2, frameon=False, fontsize=7,
           handlelength=1.0, handletextpad=0.4, columnspacing=0.8, labelspacing=0.3)

fig.savefig(os.environ["PO_OUT"], dpi=300, bbox_inches="tight", facecolor="white")
