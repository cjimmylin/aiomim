import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
})

# experimental_log.md Sec. 2.11 (entry means)
bands = ["1xxxxx\n–5xxxxx\nn=18", "600000\n–609999\nn=19",
         "610000\n–615999\nn=20", "616000\n–619999\nn=19",
         "620000\nonward\nn=17"]
facts_mem = [14.5, 24.1, 17.5, 12.6, 5.7]
facts_dir = [34.9, 53.9, 51.2, 51.4, 53.5]
gene_mem = [88.9, 94.7, 100.0, 89.5, 41.2]
gene_dir = [87.0, 100.0, 100.0, 100.0, 100.0]
# experimental_log.md Sec. 10 (separate set: 20 entries created Jun-Nov 2026)
new_label = "Jun–Nov\n2026\nn=20\n(separate set)"
new_facts = (7.0, 52.2)   # memory, direct
new_gene = (30.0, 100.0)  # memory, direct

C_DIR, C_MEM = "#0072B2", "#D55E00"
x = list(range(5))
x_new = 5.9

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.6), sharey=False)
panels = [
    (axes[0], facts_mem, facts_dir, new_facts, "OMIM facts conveyed (%)"),
    (axes[1], gene_mem, gene_dir, new_gene, "Causal gene F1 (%)"),
]
for ax, mem, dr, new, ylab in panels:
    ax.plot(x, dr, "-o", color=C_DIR, lw=1.6, ms=5, label="Direct reading", zorder=3)
    ax.plot(x, mem, "-s", color=C_MEM, lw=1.6, ms=5, label="Memory only (control)", zorder=3)
    ax.plot([x_new], [new[1]], "o", mfc="white", mec=C_DIR, mew=1.6, ms=6, zorder=3)
    ax.plot([x_new], [new[0]], "s", mfc="white", mec=C_MEM, mew=1.6, ms=6, zorder=3)
    ax.axvline(5.0 + (x_new - 5.0) / 2, color="0.5", lw=0.8, ls="--")
    ax.set_xticks(x + [x_new])
    ax.set_xticklabels(bands + [new_label])
    ax.set_xlim(-0.5, x_new + 0.5)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Entry mean (%)")
    ax.set_title(ylab.replace(" (%)", ""))
    ax.grid(axis="y", color="0.9", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

fig.supxlabel("Creation era of the entry (MIM-number range; first band = classic entries)", fontsize=8.5, y=0.02)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.04))
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(os.environ["PO_OUT"], dpi=300, bbox_inches="tight", facecolor="white")
