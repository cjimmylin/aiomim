"""Benchmark overview schematic (diagram). Content from raw_materials: idea.md (Core idea, Formal setup),
experimental_log.md Sec. 1.1, 1.3, 1.4; wording from notes.md."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Liberation Sans", "Arial", "DejaVu Sans"]
FS = 8.0      # body font size (pt)
FH = 8.5      # header font size (pt)

W, H = 7.2, 3.1
fig = plt.figure(figsize=(W, H), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

INK = "#222222"
GREY = "#777777"
C_RW, C_EW, C_MF, C_CT = "#0072B2", "#009E73", "#E69F00", "#999999"


def light(hex_, a=0.13):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return (1 - a + a * r, 1 - a + a * g, 1 - a + a * b)


def box(x0, y0, x1, y1, ec=GREY, fc="white", lw=0.8, ls="-", r=0.04):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                boxstyle=f"round,pad=0,rounding_size={r}",
                                ec=ec, fc=fc, lw=lw, ls=ls))


def txt(x, y, s, size=FS, weight="normal", color=INK, ha="left", va="center", **kw):
    ax.text(x, y, s, fontsize=size, fontweight=weight, color=color, ha=ha, va=va, **kw)


def pill(x0, xc_or_x1, y, s, col, dashed=False, plus=False):
    """Strategy (solid) or add-on (dashed, prefixed '+') pill, height 0.19 in, centred at y."""
    x1 = xc_or_x1
    box(x0, y - 0.095, x1, y + 0.095, ec=col, fc="white", lw=0.9 if not dashed else 0.8,
        ls=(0, (2.5, 1.5)) if dashed else "-", r=0.05)
    txt(x0 + 0.06, y, ("+ " if plus else "") + s, color=INK)


def arrow(x0, y0, x1, y1, col=INK, lw=0.9):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=7,
                                 lw=lw, color=col, shrinkA=0, shrinkB=0))


TOP = 3.02  # panel title baseline row

# ------------------------------------------------------------------ Panel A: input
AX0, AX1 = 0.05, 1.70
txt(AX0, TOP, "Input (same for every strategy)", size=FH, weight="bold")
box(AX0, 0.62, AX1, 2.88, ec=GREY)
txt(AX0 + 0.08, 2.76, r"Entry $e=(h,R)$", weight="bold")
# header
box(AX0 + 0.08, 2.20, AX1 - 0.08, 2.62, ec=GREY, fc="#F4F4F4", lw=0.6)
txt(AX0 + 0.14, 2.51, r"Header $h$", weight="bold")
txt(AX0 + 0.14, 2.32, "number, title, alt. titles")
# papers
box(AX0 + 0.08, 1.06, AX1 - 0.08, 2.10, ec=GREY, fc="#F4F4F4", lw=0.6)
txt(AX0 + 0.14, 1.98, r"Cited papers $R=\{d_1,\ldots,d_n\}$", weight="bold")
txt(AX0 + 0.14, 1.83, r"access level $a(d)$ of each:", color=INK)
levels = [("full text", 3), ("abstract", 1.4), ("title", 0)]
for i, (lab, nlines) in enumerate(levels):
    cx = AX0 + 0.36 + i * 0.50
    x0, y0 = cx - 0.14, 1.36
    ax.add_patch(Rectangle((x0, y0), 0.28, 0.34, ec=INK, fc="white", lw=0.7))
    # title line (always present)
    ax.plot([x0 + 0.04, x0 + 0.24], [y0 + 0.28, y0 + 0.28], color=INK, lw=1.4, solid_capstyle="butt")
    n = int(nlines * 2)
    for k in range(min(n, 6)):
        yy = y0 + 0.21 - k * 0.032
        ax.plot([x0 + 0.04, x0 + 0.24], [yy, yy], color=GREY, lw=0.6)
    txt(cx, 1.20, lab, ha="center")
txt(AX0 + 0.14, 0.86, "causal gene: withheld", weight="bold", color="#B23A00")
ax.plot([AX0 + 0.14, AX0 + 0.14 + 0.66], [0.86, 0.86], color="#B23A00", lw=0.8)  # strike through "causal gene"
txt(AX0, 0.44, "100 entries; 515 papers:", color=INK)
txt(AX0, 0.29, "96 full text, 345 abstract,", color=INK)
txt(AX0, 0.14, "74 title only", color=INK)

# ------------------------------------------------------------------ Panel B: strategies
BX0, BX1 = 1.90, 4.70
txt(BX0, TOP, "Generation strategy (the only variable)", size=FH, weight="bold")
LX = BX0 + 0.08           # left column of strategy pills
LW = 0.95                 # strategy pill width
RX = LX + LW + 0.20       # add-on column

# Read and write
box(BX0, 1.98, BX1, 2.88, ec=C_RW, fc=light(C_RW))
txt(BX0 + 0.08, 2.77, "Read and write", weight="bold", color=C_RW)
pill(LX, LX + LW, 2.55, "Direct reading", C_RW)
pill(RX, BX1 - 0.08, 2.55, "Second-hand evidence", C_RW, dashed=True, plus=True)
pill(RX, BX1 - 0.08, 2.32, "Learned curation guide", C_RW, dashed=True, plus=True)
ax.plot([LX + LW, RX], [2.55, 2.55], color=C_RW, lw=0.8)
ax.plot([LX + LW + 0.10, LX + LW + 0.10, RX], [2.55, 2.32, 2.32], color=C_RW, lw=0.8)
pill(LX, LX + LW, 2.09, "Agentic curator", C_RW)

# Extract, then write
box(BX0, 1.24, BX1, 1.92, ec=C_EW, fc=light(C_EW))
txt(BX0 + 0.08, 1.81, "Extract, then write", weight="bold", color=C_EW)
pill(LX, LX + LW, 1.59, "Evidence graph", C_EW)
pill(LX, LX + LW, 1.36, "Case table first", C_EW)
pill(RX, BX1 - 0.08, 1.36, "Reconciled case database", C_EW, dashed=True, plus=True)
ax.plot([LX + LW, RX], [1.36, 1.36], color=C_EW, lw=0.8)

# Memory first and control
MID = (BX0 + BX1) / 2
box(BX0, 0.76, MID - 0.04, 1.18, ec=C_MF, fc=light(C_MF, 0.18))
txt(BX0 + 0.08, 1.07, "Memory first", weight="bold", color="#A86E00")
pill(LX, MID - 0.12, 0.87, "Recall, then verify", C_MF)
box(MID + 0.04, 0.76, BX1, 1.18, ec=C_CT, fc=light(C_CT, 0.18))
txt(MID + 0.12, 1.07, "Control", weight="bold", color="#555555")
pill(MID + 0.12, BX1 - 0.08, 0.87, "Memory only (no papers)", C_CT)

# guards band
box(BX0, 0.02, BX1, 0.68, ec=INK, fc="#EFEFEF", lw=0.7)
txt(BX0 + 0.08, 0.58, "Guards applied to every strategy", weight="bold")
txt(BX0 + 0.08, 0.43, "ontology IDs chosen only from ontology-search candidates;")
txt(BX0 + 0.08, 0.28, "gene symbols normalised against HGNC; recalled")
txt(BX0 + 0.08, 0.13, "cross-reference numbers removed; every paragraph cites a supplied paper")

# ------------------------------------------------------------------ Panel C: audit, scoring, reference
CX0, CX1 = 4.88, 7.15
txt(CX0, TOP, "Shared audit and scoring", size=FH, weight="bold")
box(CX0, 2.24, CX1, 2.88, ec=INK, fc="white")
txt(CX0 + 0.08, 2.77, "Claim-level audit of every draft", weight="bold")
txt(CX0 + 0.08, 2.61, "1  split into atomic claims")
txt(CX0 + 0.08, 2.46, "2  verdict per cited paper + verbatim quote")
txt(CX0 + 0.08, 2.31, "3  one repair round for flagged claims")

box(CX0, 1.28, CX1, 2.10, ec=INK, fc="white")
txt(CX0 + 0.08, 1.99, "Scoring against the reference", weight="bold")
txt(CX0 + 0.08, 1.83, "OMIM facts conveyed (primary endpoint;", weight="bold", color=C_RW)
txt(CX0 + 0.08, 1.68, "fixed fact lists)", weight="bold", color=C_RW)
txt(CX0 + 0.08, 1.53, "secondary: HPO terms, allelic variants,")
txt(CX0 + 0.08, 1.38, "causal gene, inheritance")

box(CX0, 0.02, CX1, 1.20, ec=GREY, fc="#F4F4F4")
txt(CX0 + 0.08, 1.09, "Reference (public sources)", weight="bold")
txt(CX0 + 0.08, 0.93, "curator-written per-paper text (OMIM")
txt(CX0 + 0.08, 0.78, "allelic-variant descriptions in ClinVar):")
txt(CX0 + 0.08, 0.63, "476 paragraphs, 6,652 fixed facts")
txt(CX0 + 0.08, 0.46, "HPO disease annotations: 2,311")
txt(CX0 + 0.08, 0.31, "OMIM allelic variants in ClinVar: 427")
txt(CX0 + 0.08, 0.16, "causal gene (gene map); inheritance modes")

# ------------------------------------------------------------------ arrows
arrow(AX1, 1.75, BX0, 1.75)                       # input -> strategies
arrow(BX1, 2.56, CX0, 2.56)                       # draft -> audit
txt((BX1 + CX0) / 2, 2.67, "D", ha="center", style="italic")
arrow((CX0 + CX1) / 2, 2.24, (CX0 + CX1) / 2, 2.10)  # audit -> scoring
arrow((CX0 + CX1) / 2, 1.20, (CX0 + CX1) / 2, 1.28)  # reference -> scoring

fig.savefig(os.environ["PO_OUT"], dpi=300, bbox_inches="tight", facecolor="white")
