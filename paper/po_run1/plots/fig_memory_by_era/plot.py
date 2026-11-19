import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
})

# experimental_log.md Sec. 2.11 (entry means)
bands = ["classic\n(1xxxxx–5xxxxx)\nn=18", "600000–609999\n\nn=19",
         "610000–615999\n\nn=20", "616000–619999\n\nn=19",
         "620000 onward\n\nn=17"]
facts_mem = [14.5, 24.1, 17.5, 12.6, 5.7]
facts_dir = [34.9, 53.9, 51.2, 51.4, 53.5]
gene_mem = [88.9, 94.7, 100.0, 89.5, 41.2]
gene_dir = [87.0, 100.0, 100.0, 100.0, 100.0]
# experimental_log.md Sec. 10 (separate set: 20 compared entries created Jun-Nov 2026)
new_label = "created Jun–Nov 2026\n(separate set)\nn=20"
new_facts = (7.0, 52.2)   # memory, direct
new_gene = (30.0, 100.0)  # memory, direct

C_DIR, C_MEM = "#0072B2", "#D55E00"
x = list(range(5))
x_new = 5.4

fig, axes = plt.subplots(2, 1, figsize=(7.0, 4.4), sharex=True)
panels = [
    (axes[0], facts_mem, facts_dir, new_facts, "OMIM facts conveyed"),
    (axes[1], gene_mem, gene_dir, new_gene, "Causal gene F1"),
]
for ax, mem, dr, new, title in panels:
    ax.plot(x, dr, "-o", color=C_DIR, lw=1.6, ms=5, label="Direct reading", zorder=3)
    ax.plot(x, mem, "-s", color=C_MEM, lw=1.6, ms=5, label="Memory only (control)", zorder=3)
    ax.plot([x_new], [new[1]], "o", mfc="white", mec=C_DIR, mew=1.6, ms=6, zorder=3)
    ax.plot([x_new], [new[0]], "s", mfc="white", mec=C_MEM, mew=1.6, ms=6, zorder=3)
    ax.axvline(4.7, color="0.5", lw=0.8, ls="--")
    ax.set_xlim(-0.45, x_new + 0.55)
    ax.set_ylim(0, 108)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel(title + " (%)")
    ax.grid(axis="y", color="0.9", lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

axes[1].set_xticks(x + [x_new])
axes[1].set_xticklabels(bands + [new_label])
axes[1].set_xlabel("Creation era of the entry (MIM-number range)")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.03))
fig.tight_layout(rect=(0, 0, 1, 0.96), h_pad=0.6)
fig.align_ylabels(axes)
fig.savefig(os.environ["PO_OUT"], dpi=300, bbox_inches="tight", facecolor="white")
