"""fig_audit_coverage: what the claim-level audit flags, by class of planted error.

Data: experimental_log.md Sec. 11 ('Planted errors', 'Audit control') and Sec. 14.4 ('Audit on planted
errors', 'C5 by deletion rule', 'Control'). Counts over truth-known items; controls are paragraphs.
Print size: 3.0 in wide (0.55 of a 5.5 in text width), drawn 1:1, so every font size below is final.
Smallest text: 7 pt. Greys only (no strategy colour).
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import blended_transform_factory

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.major.size": 2.5, "xtick.major.pad": 1.5,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})

INK = "0.2"     # markers and text
GUIDE = "0.85"  # row guide lines

# (heading, [(row label, k flagged, n, marker style)])
#   "fill" = should be flagged, "square" = not visible by design, "open" = unaltered control
groups = [
    ("Errors the audit should catch", [
        ("Single value altered", 60, 60, "fill"),            # Sec. 11, flagged all 60
        ("Citation swapped, other entry", 30, 30, "fill"),   # Sec. 14.4 C1, planted claim 30/30
        ("Citation swapped, same entry", 26, 26, "fill"),    # Sec. 14.4 C2, 26/26 truth-known
        ("Sentence moved to other paper", 25, 25, "fill"),   # Sec. 14.4 C3 conflation, 25/25 truth-known
        ("Negation deleted", 8, 8, "fill"),                  # Sec. 14.4 C5 by rule: negation 8/8
        ("Hedge deleted", 2, 8, "fill"),                     # C5 hedge 2/8
        ("Count deleted", 1, 4, "fill"),                     # C5 count 1/4
        ("Zygosity deleted", 0, 8, "fill"),                  # C5 zygosity 0/8
        ("“One family/patient” deleted", 0, 2, "fill"),  # C5 single family or patient 0/2
    ]),
    ("Not visible to the audit by design", [
        ("Irrelevant citation added", 0, 30, "square"),      # Sec. 14.4 C4 over-citation, 0/30
        ("Finding omitted", 0, 30, "square"),                # Sec. 14.4 C6, paragraph flagged 0/30
    ]),
    ("Unaltered control", [
        ("Single-value paragraphs", 0, 60, "open"),          # Sec. 11 audit control, 0 of 60
        ("Paragraphs of other classes", 0, 113, "open"),     # Sec. 14.4 Control, 113 paragraphs, 0 flagged
    ]),
]

# ---- layout (inches) -------------------------------------------------------------------------------
FIG_W = 3.0
PITCH = 0.132          # inches per text line (about 9.5 pt)
GAP = 0.45             # extra space before a heading, in lines
X_HEAD, X_ROW = 0.0, 0.08            # left edges of headings and row labels
AX_L, AX_R = 1.48, 2.52              # data axes, left and right edge
X_SLASH = 2.76                       # k/n column aligned on the slash
BOTTOM = 0.36                        # room for ticks and the x-axis label

# y positions in "lines", top line = 0, increasing downward
items = []  # (y, kind, payload)
y = 0.0
for gi, (head, rows) in enumerate(groups):
    if gi:
        y += GAP
    items.append((y, "head", head))
    y += 1
    for r in rows:
        items.append((y, "row", r))
        y += 1
n_lines = y
plot_h = (n_lines - 0.5 + 0.35) * PITCH
FIG_H = BOTTOM + plot_h + 0.02

fig = plt.figure(figsize=(FIG_W, FIG_H))
ax = fig.add_axes([AX_L / FIG_W, BOTTOM / FIG_H, (AX_R - AX_L) / FIG_W, plot_h / FIG_H])
ax.set_ylim(n_lines - 0.5 + 0.35, -0.5)  # inverted: first line on top
ax.set_xlim(-6, 106)
fx = blended_transform_factory(fig.transFigure, ax.transData)  # x in figure fraction, y in lines

for yy, kind, payload in items:
    if kind == "head":
        ax.text(X_HEAD / FIG_W, yy, payload, transform=fx, ha="left", va="center",
                fontweight="bold", color="black", clip_on=False)
        continue
    label, k, n, style = payload
    pct = 100.0 * k / n
    ax.text(X_ROW / FIG_W, yy, label, transform=fx, ha="left", va="center", color=INK, clip_on=False)
    ax.plot([0, 100], [yy, yy], color=GUIDE, lw=0.5, zorder=1, solid_capstyle="butt")
    if style == "fill":
        ax.plot(pct, yy, "o", ms=4.2, mfc=INK, mec=INK, mew=0.8, zorder=3, clip_on=False)
    elif style == "square":
        ax.plot(pct, yy, "s", ms=4.0, mfc="white", mec=INK, mew=0.9, zorder=3, clip_on=False)
    else:
        ax.plot(pct, yy, "o", ms=4.2, mfc="white", mec=INK, mew=0.9, zorder=3, clip_on=False)
    # k/n, aligned on the slash
    ax.text(X_SLASH / FIG_W, yy, f"{k}", transform=fx, ha="right", va="center", color=INK, clip_on=False)
    ax.text(X_SLASH / FIG_W, yy, f"/{n}", transform=fx, ha="left", va="center", color=INK, clip_on=False)

ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("Flagged by the audit (%)", labelpad=2)
ax.set_yticks([])
for s in ("left", "right", "top"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_bounds(0, 100)
ax.tick_params(axis="x", colors="black")

out = os.environ["PO_OUT"]
fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=0.02, facecolor="white")
fig.savefig(os.path.splitext(out)[0] + ".pdf", bbox_inches="tight", pad_inches=0.02, facecolor="white")
print(f"figsize {FIG_W:.2f} x {FIG_H:.2f} in")
