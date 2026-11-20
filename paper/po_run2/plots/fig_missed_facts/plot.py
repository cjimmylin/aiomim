"""fig_missed_facts: where the OMIM facts direct reading did not fully convey went (Appendix D).

Data: experimental_log.md Sec. 3 "Where the missed facts went (direct reading, fixed fact lists)", first table, and
the line "Facts contradicted by the draft (not in the columns above)". 97 entries, 466 OMIM paragraphs; counts are
pooled over facts. Printed at full text width: 5.5 x 3.09 in (16:9), saved at exactly that size; all text >= 7 pt.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.transforms import blended_transform_factory

FS = 8  # every text element; nothing below 7 pt at the printed width
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS, "legend.fontsize": FS,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 3, "xtick.major.pad": 2,
    "hatch.linewidth": 0.6, "pdf.fonttype": 42, "svg.fonttype": "none",
})

# ---- data, copied from the log (Sec. 3, first table; contradicted from the line below the second table) ----
levels = ["Full text", "Abstract only", "Title only"]
facts = [1837, 4282, 379]            # "OMIM facts"
conveyed = [1329, 1420, 38]          # "Conveyed" (in full)
not_fully = [501, 2837, 341]         # "Not fully conveyed" (partly conveyed facts count as missed)
stated = [245, 46, 0]                # "... in text"
partly = [134, 632, 53]              # "... partly in text"
not_stated = [122, 2159, 288]        # "... not in text"
contradicted = [7, 25, 0]            # "Facts contradicted by the draft (not in the columns above)"
share_missed_stated = ["49%", "2%", "0%"]  # "In text, share of missed"
for i in range(3):
    assert stated[i] + partly[i] + not_stated[i] == not_fully[i]
    assert conveyed[i] + not_fully[i] + contradicted[i] == facts[i]

# ---- style: greys from fig_access_bound panel (b) + direct reading's black for its conveyed facts ----
GREY_STATED, GREY_PARTLY, HATCH_GREY = "#3B3B3B", "#9E9E9E", "#9E9E9E"
segments = [  # label, counts, face, hatch, text colour
    ("Conveyed in full", conveyed, "#000000", None, "white"),
    ("Missed, stated", stated, GREY_STATED, None, "white"),
    ("Missed, partly stated", partly, GREY_PARTLY, None, "black"),
    ("Missed, not stated", not_stated, "white", "////", "black"),
]

W, H = 5.5, 5.5 * 9 / 16              # printed size in inches
fig = plt.figure(figsize=(W, H), facecolor="white")
L, R, B, T = 0.95, 1.0, 0.48, 0.42    # margins in inches: tick labels | share column | x axis | legend
ax = fig.add_axes([L / W, B / H, (W - L - R) / W, (H - B - T) / H])
ax_w_in = W - L - R

ypos = [2, 1, 0]
BH = 0.56
left = [0.0, 0.0, 0.0]
handles = []
for label, counts, face, hatch, tcol in segments:
    pct = [100.0 * c / n for c, n in zip(counts, facts)]
    if hatch:
        ax.barh(ypos, pct, left=left, height=BH, color=face, hatch=hatch, hatchcolor=HATCH_GREY,
                edgecolor=HATCH_GREY, linewidth=0.5, zorder=2)
        handles.append(Patch(facecolor=face, hatch=hatch, hatchcolor=HATCH_GREY, edgecolor=HATCH_GREY,
                             linewidth=0.5, label=label))
    else:
        ax.barh(ypos, pct, left=left, height=BH, color=face, edgecolor="white", linewidth=0.8, zorder=3)
        handles.append(Patch(facecolor=face, edgecolor="none", label=label))
    for y, l, p, c in zip(ypos, left, pct, counts):
        # label a segment with its log count only if the number fits inside at print size (~0.2 in for 3 digits)
        if p / 100 * ax_w_in >= 0.07 * len(f"{c:,}") + 0.04:
            box = dict(facecolor="white", edgecolor="none", pad=0.6) if hatch else None
            ax.text(l + p / 2, y, f"{c:,}", ha="center", va="center", color=tcol, fontsize=FS, bbox=box, zorder=4)
    left = [l + p for l, p in zip(left, pct)]

ax.set_xlim(0, 100)
ax.set_ylim(-0.5, 2.5)
ax.set_yticks(ypos)
ax.set_yticklabels([f"{lev}\n{n:,} facts" for lev, n in zip(levels, facts)])
ax.tick_params(axis="y", length=0, pad=4)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("Share of OMIM facts", labelpad=3)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.spines["bottom"].set_bounds(0, 100)

# right-hand column: share of the missed facts that the available text states (log column, copied)
COLX = 1.0 + 0.5 / ax_w_in            # column centre 0.5 in right of the 100% end
tr = blended_transform_factory(ax.transAxes, ax.transData)
ax.text(COLX, 2.5, "Stated, share\nof missed", transform=tr, ha="center", va="bottom", fontsize=FS,
        linespacing=1.1, clip_on=False)
for y, s in zip(ypos, share_missed_stated):
    ax.text(COLX, y, s, transform=tr, ha="center", va="center", fontsize=FS, clip_on=False)

fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(L / W - 0.01, 1.0), ncol=4, frameon=False,
           handlelength=1.1, handleheight=1.1, handletextpad=0.4, columnspacing=1.1, borderaxespad=0.2)

out = os.environ["PO_OUT"]
fig.savefig(out, dpi=300, facecolor="white")
fig.savefig(os.path.splitext(out)[0] + ".pdf", facecolor="white")
