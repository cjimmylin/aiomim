"""Benchmark overview schematic (diagram). Content from raw_materials: idea.md (Core idea, Formal setup),
experimental_log.md Sec. 1.1, 1.3, 1.4; wording from notes.md.
Print size: full text width, 5.5 in; all text >= 7 pt. Strategy pills use the same per-strategy colours as the
data figures; paradigm groups are neutral grey so no strategy colour means anything else."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic",
    "mathtext.bf": "Liberation Sans:bold",
})
FS = 7.0      # body font size (pt)
FH = 7.5      # panel header font size (pt)
LH = 0.118    # body line pitch (in)

W, H = 5.5, 2.32
fig = plt.figure(figsize=(W, H), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

INK = "#222222"
GREY = "#777777"
GROUP_EC, GROUP_FC = "#B5B5B5", "#F1F1F1"
# one colour per strategy, shared by all figures
STRAT = {
    "Direct reading": "#0072B2",
    "Agentic curator": "#56B4E9",
    "Evidence graph": "#009E73",
    "Case table first": "#D55E00",
    "Recall, then verify": "#E69F00",
    "Memory only": "#000000",
}


def box(x0, y0, x1, y1, ec=GREY, fc="white", lw=0.6, ls="-", r=0.035):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                ec=ec, fc=fc, lw=lw, ls=ls))


def txt(x, y, s, size=FS, weight="normal", color=INK, ha="left", va="center", **kw):
    ax.text(x, y, s, fontsize=size, fontweight=weight, color=color, ha=ha, va=va, **kw)


PH = 0.128  # pill height


def pill(x0, x1, y, s, col=None):
    """Strategy pill (solid edge in the strategy colour, colour dot) or add-on pill (col None: dashed grey, '+')."""
    if col is None:
        box(x0, y - PH / 2, x1, y + PH / 2, ec=GREY, fc="white", lw=0.6, ls=(0, (2.2, 1.3)), r=0.04)
        txt(x0 + 0.05, y, "+ " + s)
    else:
        box(x0, y - PH / 2, x1, y + PH / 2, ec=col, fc="white", lw=0.9, r=0.04)
        ax.plot([x0 + 0.065], [y], "o", ms=3.2, color=col)
        txt(x0 + 0.115, y, s)


def arrow(x0, y0, x1, y1, col=INK, lw=0.7):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=6,
                                 lw=lw, color=col, shrinkA=0, shrinkB=0))


TOP = H - 0.075   # panel header row
BT = H - 0.17     # top of panel content

# ------------------------------------------------------------------ Panel A: input
AX0, AX1 = 0.02, 1.40
txt(AX0, TOP, "Input (same for all)", size=FH, weight="bold")
txt(AX0 + 0.07, BT - 0.09, r"Entry $e=(h,R)$", weight="bold")
# header
hy1 = BT - 0.17
box(AX0 + 0.07, hy1 - 0.37, AX1 - 0.07, hy1, ec=GREY, fc="#F4F4F4", lw=0.5)
txt(AX0 + 0.12, hy1 - 0.075, r"Header $h$", weight="bold")
txt(AX0 + 0.12, hy1 - 0.075 - LH, "number, title,")
txt(AX0 + 0.12, hy1 - 0.075 - 2 * LH, "alternative titles")
# papers
py1 = hy1 - 0.45
pb = py1 - 0.68
box(AX0 + 0.07, pb, AX1 - 0.07, py1, ec=GREY, fc="#F4F4F4", lw=0.5)
txt(AX0 + 0.12, py1 - 0.075, r"Cited papers $R=\{d_i\}$", weight="bold")
txt(AX0 + 0.12, py1 - 0.075 - LH, r"access level $a(d)$ of each:")
levels = [("full text", 3), ("abstract", 1.4), ("title", 0)]
for i, (lab, nlines) in enumerate(levels):
    cx = AX0 + 0.31 + i * 0.39
    x0, y0 = cx - 0.11, pb + 0.18
    ax.add_patch(Rectangle((x0, y0), 0.22, 0.24, ec=INK, fc="white", lw=0.6))
    ax.plot([x0 + 0.035, x0 + 0.185], [y0 + 0.195, y0 + 0.195], color=INK, lw=1.2, solid_capstyle="butt")
    n = int(nlines * 2)
    for k in range(min(n, 6)):
        yy = y0 + 0.145 - k * 0.022
        ax.plot([x0 + 0.035, x0 + 0.185], [yy, yy], color=GREY, lw=0.5)
    txt(cx, pb + 0.09, lab, ha="center")
txt(AX0 + 0.07, pb - 0.11, "causal gene withheld", weight="bold")
cy = pb - 0.11 - 0.17
txt(AX0 + 0.07, cy, "100 entries; 515 papers:")
txt(AX0 + 0.07, cy - LH, "96 full text, 345 abstract,")
txt(AX0 + 0.07, cy - 2 * LH, "74 title only")
A_BOTTOM = cy - 2 * LH - 0.08

# ------------------------------------------------------------------ Panel B: strategies
BX0, BX1 = 1.56, 3.30
txt(BX0, TOP, "Strategy (the only variable)", size=FH, weight="bold")
P0 = BX0 + 0.06              # pill left edge
P1 = BX1 - 0.06              # pill right edge
IND = 0.15                   # add-on indent
ROW = 0.168                  # pill pitch


def group(y_top, title, rows):
    """Neutral group box with a bold title line and one pill per row; returns the box bottom."""
    n = len(rows)
    y_bot = y_top - 0.13 - n * ROW - 0.02
    box(BX0, y_bot, BX1, y_top, ec=GROUP_EC, fc=GROUP_FC, lw=0.6)
    txt(BX0 + 0.06, y_top - 0.07, title, weight="bold")
    parent_y = None
    for k, (s, is_addon) in enumerate(rows):
        y = y_top - 0.13 - ROW / 2 - k * ROW
        if is_addon:
            pill(P0 + IND, P1, y, s)
            ax.plot([P0 + IND / 2, P0 + IND / 2, P0 + IND], [parent_y - PH / 2, y, y], color=GREY, lw=0.6)
        else:
            pill(P0, P1, y, s, STRAT[s])
            parent_y = y
    return y_bot


def group_inline(y_top, title, s):
    """One-pill group: title left, pill right, on one row."""
    y_bot = y_top - 0.20
    box(BX0, y_bot, BX1, y_top, ec=GROUP_EC, fc=GROUP_FC, lw=0.6)
    txt(BX0 + 0.06, y_top - 0.10, title, weight="bold")
    return y_bot


gap = 0.07
y = group(BT, "Read and write", [("Direct reading", False), ("Second-hand evidence", True),
                                 ("Learned curation guide", True), ("Agentic curator", False)])
y = group(y - gap, "Extract, then write", [("Evidence graph", False), ("Case table first", False),
                                          ("Reconciled case database", True)])
y_mf = y - gap
y = group_inline(y_mf, "Memory first", "Recall, then verify")
pill(P1 - 0.93, P1, y_mf - 0.10, "Recall, then verify", STRAT["Recall, then verify"])
y_ct = y - gap
y = group_inline(y_ct, "Control", "Memory only")
pill(P1 - 0.93, P1, y_ct - 0.10, "Memory only", STRAT["Memory only"])
B_BOTTOM = y

# ------------------------------------------------------------------ Panel C: audit, scoring, reference
CX0, CX1 = 3.46, 5.48
txt(CX0, TOP, "Shared audit and scoring", size=FH, weight="bold")
TX = CX0 + 0.07


def lines(y_top, items):
    """items: (text, weight); first baseline-centre 0.075 below y_top; returns y after the last line."""
    for k, (s, w) in enumerate(items):
        txt(TX, y_top - 0.075 - k * LH, s, weight=w)
    return y_top - 0.075 - (len(items) - 1) * LH - 0.07


audit = [("Claim-level audit of every draft", "bold"),
         ("atomic claims → verdict per cited paper", "normal"),
         ("+ verbatim quote → one repair round", "normal")]
a_top = BT
a_bot = a_top - (0.075 + (len(audit) - 1) * LH + 0.07)
box(CX0, a_bot, CX1, a_top, ec=INK)
lines(a_top, audit)

score = [("Scoring against the reference", "bold"),
         ("primary: OMIM facts conveyed", "bold"),
         ("(fixed fact lists)", "normal"),
         ("secondary: HPO terms, allelic variants,", "normal"),
         ("causal gene, inheritance", "normal")]
s_top = a_bot - 0.12
s_bot = s_top - (0.075 + (len(score) - 1) * LH + 0.07)
box(CX0, s_bot, CX1, s_top, ec=INK)
lines(s_top, score)

ref = [("Reference (public sources)", "bold"),
       ("curator-written per-paper text (OMIM", "normal"),
       ("allelic-variant descriptions in ClinVar):", "normal"),
       ("476 paragraphs, 6,652 fixed facts", "normal"),
       ("HPO disease annotations: 2,311", "normal"),
       ("OMIM allelic variants in ClinVar: 427", "normal"),
       ("causal gene; inheritance modes", "normal")]
r_top = s_bot - 0.12
r_bot = r_top - (0.075 + (len(ref) - 1) * LH + 0.07)
box(CX0, r_bot, CX1, r_top, ec=GREY, fc="#F4F4F4")
lines(r_top, ref)

# ------------------------------------------------------------------ arrows
mid_a = (r_bot + BT) / 2
arrow(AX1, mid_a, BX0, mid_a)                          # input -> strategies
ya = (a_top + a_bot) / 2
arrow(BX1, ya, CX0, ya)                                # draft -> audit
txt((BX1 + CX0) / 2, ya + 0.075, r"$D$", ha="center")
xm = (CX0 + CX1) / 2
arrow(xm, a_bot, xm, s_top)                            # audit -> scoring
arrow(xm, r_top, xm, s_bot)                            # reference -> scoring
box(AX0, r_bot, AX1, BT, ec=GREY, fc="none")   # input panel frame, aligned with panel C
print("bottoms: A", A_BOTTOM, "B", B_BOTTOM, "C", r_bot)

fig.savefig(os.environ["PO_OUT"], dpi=300, facecolor="white")
