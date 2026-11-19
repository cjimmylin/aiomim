"""fig_memory_by_era: memory-only control vs direct reading by creation era of the entry.
Data: experimental_log.md Sec. 2.11 (entry means) and Sec. 10 (separate 2026 set).
Print size: 2.75 in wide (beside fig_access_strata, same height); all text >= 7 pt."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
})

# experimental_log.md Sec. 2.11 (entry means); n = 18, 19, 20, 19, 17 compared entries per band (in caption)
bands = ["classic", "600\u2013\n609", "610\u2013\n615", "616\u2013\n619", "620+"]  # MIM number, thousands
facts_mem = [14.5, 24.1, 17.5, 12.6, 5.7]
facts_dir = [34.9, 53.9, 51.2, 51.4, 53.5]
gene_mem = [88.9, 94.7, 100.0, 89.5, 41.2]
gene_dir = [87.0, 100.0, 100.0, 100.0, 100.0]
# experimental_log.md Sec. 10 (separate set: 20 compared entries created Jun-Nov 2026)
new_label = "2026\nset"
new_facts = (7.0, 52.2)   # memory, direct
new_gene = (30.0, 100.0)  # memory, direct

# one colour per strategy, shared by all figures
C_DIR, C_MEM = "#0072B2", "#000000"
x = list(range(5))
x_new = 5.5

fig, axes = plt.subplots(2, 1, figsize=(2.75, 2.4), sharex=True, layout="constrained")
fig.get_layout_engine().set(w_pad=0.02, h_pad=0.03, hspace=0.0)
panels = [
    (axes[0], facts_mem, facts_dir, new_facts, "OMIM facts conveyed (%)"),
    (axes[1], gene_mem, gene_dir, new_gene, "Causal gene F1 (%)"),
]
for ax, mem, dr, new, title in panels:
    ax.plot(x, dr, "-o", color=C_DIR, lw=1.1, ms=3.2, zorder=3)
    ax.plot(x, mem, "-s", color=C_MEM, lw=1.1, ms=3.0, zorder=3)
    ax.plot([x_new], [new[1]], "o", mfc="white", mec=C_DIR, mew=1.0, ms=3.6, zorder=3)
    ax.plot([x_new], [new[0]], "s", mfc="white", mec=C_MEM, mew=1.0, ms=3.4, zorder=3)
    ax.axvline(4.75, color="0.5", lw=0.6, ls="--")
    ax.set_xlim(-0.4, x_new + 0.4)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 50, 100])
    ax.set_title(title, loc="left", pad=2)
    ax.grid(axis="y", color="0.9", lw=0.4)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

# direct labels instead of a legend
axes[0].text(1.0, 61, "Direct reading", color=C_DIR, ha="left", va="bottom")
axes[0].text(1.0, 28, "Memory only", color=C_MEM, ha="left", va="bottom")

axes[1].set_xticks(x + [x_new])
axes[1].set_xticklabels(bands + [new_label])
axes[1].set_xlabel("Creation era (MIM number, thousands)")
fig.align_ylabels(axes)
fig.savefig(os.environ["PO_OUT"], dpi=300, facecolor="white")
