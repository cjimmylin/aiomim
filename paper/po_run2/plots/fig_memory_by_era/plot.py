"""fig_memory_by_era: memory-only control vs direct reading by creation era of the entry (Appendix D).
Data: experimental_log.md Sec. 2.11 (entry means by era band) and Sec. 10 (separate set created in 2026).
Print size: full text width, 5.5 x 3.67 in (3:2); include with width=\\textwidth. All text 8 pt."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FS = 8  # every text element, at print size
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS, "xtick.labelsize": FS, "ytick.labelsize": FS,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.major.pad": 2.0, "ytick.major.pad": 1.5,
    "pdf.fonttype": 42,
})

# experimental_log.md Sec. 2.11 (entry means); n = compared entries per band ("Entries" column)
band_ticks = ["1xxxxx–\n5xxxxx\nclassic, n = 18", "600000–\n609999\nn = 19", "610000–\n615999\nn = 20",
              "616000–\n619999\nn = 19", "620000\nonward\nn = 17"]
facts_mem = [14.5, 24.1, 17.5, 12.6, 5.7]
facts_dir = [34.9, 53.9, 51.2, 51.4, 53.5]
gene_mem = [88.9, 94.7, 100.0, 89.5, 41.2]
gene_dir = [87.0, 100.0, 100.0, 100.0, 100.0]
# experimental_log.md Sec. 10 (separate set: 20 of 30 entries created in 2026 compared)
new_tick = "created\n2026\nn = 20"
new_facts = (7.0, 52.2)   # memory, direct
new_gene = (30.0, 100.0)  # memory, direct

# one colour per strategy, shared by all figures (orchestrator brief)
C_DIR, C_MEM = "#0072B2", "#000000"
x = list(range(5))
x_new = 5.7
DODGE = 0.07  # keeps coinciding points (e.g. both 100.0) visible; not a data value
xd = [v - DODGE for v in x]
xm = [v + DODGE for v in x]

fig, axes = plt.subplots(2, 1, figsize=(5.5, 3.67), sharex=True, layout="constrained")
fig.get_layout_engine().set(w_pad=0.02, h_pad=0.04, hspace=0.04)
panels = [
    (axes[0], facts_mem, facts_dir, new_facts, "OMIM facts conveyed (%)"),
    (axes[1], gene_mem, gene_dir, new_gene, "Causal gene F1 (%)"),
]
for ax, mem, dr, new, header in panels:
    ax.plot(xd, dr, "-o", color=C_DIR, lw=1.2, ms=4.2, zorder=3, clip_on=False)
    ax.plot(xm, mem, "-s", color=C_MEM, lw=1.2, ms=3.8, zorder=4, clip_on=False)
    ax.plot([x_new - DODGE], [new[1]], "o", mfc="white", mec=C_DIR, mew=1.1, ms=4.6, zorder=3, clip_on=False)
    ax.plot([x_new + DODGE], [new[0]], "s", mfc="white", mec=C_MEM, mew=1.1, ms=4.2, zorder=4, clip_on=False)
    ax.axvline((4 + x_new) / 2, color="0.55", lw=0.6, ls="--", zorder=1)
    ax.set_xlim(-0.45, x_new + 0.45)
    ax.set_ylim(0, 105)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title(header, loc="left", pad=3)
    ax.grid(axis="y", color="0.9", lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

# direct labels instead of a legend
axes[0].text(1.55, 60, "Direct reading", color=C_DIR, ha="center", va="bottom")
axes[0].text(2.55, 22, "Memory only", color=C_MEM, ha="center", va="bottom")

axes[1].set_xticks(x + [x_new])
axes[1].set_xticklabels(band_ticks + [new_tick])
axes[1].set_xlabel("Creation era of the entry (MIM-number range)")
fig.align_ylabels(axes)

out = os.environ["PO_OUT"]
fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.02)
root, ext = os.path.splitext(out)
if ext.lower() != ".pdf":
    fig.savefig(root + ".pdf", facecolor="white", bbox_inches="tight", pad_inches=0.02)
