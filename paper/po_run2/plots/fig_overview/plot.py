"""fig_overview: benchmark overview schematic (diagram).
Content from raw_materials: idea.md (Core idea, Formal setup), experimental_log.md Sec. 1.1, 1.3, 1.4 and Sec. 15
(reading-better arms); wording from notes.md. Adapted from po_run1 fig_benchmark_overview.
Print size: full text width 5.5 in; every text element >= 7 pt; no subscripts or fractions (they would print < 7 pt).
Layout is built top-down in inches (y = 0 at the top, negative downwards); the figure height is set at the end
from the content, so 1 data unit = 1 inch in both directions."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch, Arc, Polygon

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic",
    "mathtext.bf": "Liberation Sans:bold", "mathtext.cal": "Liberation Sans", "mathtext.sf": "Liberation Sans",
    "pdf.fonttype": 42, "svg.fonttype": "none",
})
FS = 7.0      # body text (pt)
FH = 7.5      # column headers (pt)
LH = 0.118    # body line pitch (in)

W = 5.5
fig = plt.figure(figsize=(W, 3.3), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.axis("off")

INK = "#222222"
GREY = "#777777"
SOFT = "#5A5A5A"
GROUP_EC, GROUP_FC = "#B5B5B5", "#F1F1F1"
REF_FC = "#F4F4F4"
# one colour per strategy, identical in every figure (orchestrator's palette)
STRAT = {
    "Direct reading (baseline)": "#0072B2",
    "Agentic curator": "#56B4E9",
    "Evidence graph": "#009E73",
    "Case table first": "#D55E00",
    "Recall, then verify": "#E69F00",
    "Memory only (no papers)": "#000000",
}
# reading-better arms (variants of direct reading): same colours as fig_design_vs_reading
BETTER = {
    "checklist": "#8C8C8C",
    "completeness pass": "#3D6F98",
    "three-draft merge": "#555555",
    "checklist + completeness pass": "#003A5E",
}


def box(x0, y0, x1, y1, ec=GREY, fc="white", lw=0.6, ls="-", r=0.035, z=1):
    """Rounded box between bottom y0 and top y1."""
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle=f"round,pad=0,rounding_size={r}",
                                ec=ec, fc=fc, lw=lw, ls=ls, zorder=z))


def txt(x, y, s, size=FS, weight="normal", color=INK, ha="left", va="center", **kw):
    ax.text(x, y, s, fontsize=size, fontweight=weight, color=color, ha=ha, va=va, zorder=5, **kw)


def arrow(x0, y0, x1, y1, col=INK, lw=0.7):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=6,
                                 lw=lw, color=col, shrinkA=0, shrinkB=0, zorder=4))


def line(xs, ys, col=GREY, lw=0.6, **kw):
    ax.plot(xs, ys, color=col, lw=lw, solid_capstyle="butt", zorder=2, **kw)


def dot(x, y, col):
    ax.plot([x], [y], "o", ms=3.4, color=col, mec=col, zorder=6)


HEAD = -0.075     # header row (centre)
BT = -0.165       # top of the content

# column extents (in)
AX0, AX1 = 0.02, 1.02
BX0, BX1 = 1.16, 3.04
CX0, CX1 = 3.18, 5.48

# ====================================================================== Column C: audit and scoring
TX = CX0 + 0.07   # text left
IND = 0.12        # continuation indent
txt(CX0, HEAD, "One audit, every draft", size=FH, weight="bold")
audit = [("paragraph → atomic claims $c$, cited papers $R(c)$", 0),
         ("→ verdict per cited paper + verbatim quote", 0),
         ("supported / partly / unsupported / contradicted", IND),
         ("→ best verdict over $R(c)$", 0),
         ("→ one repair round for flagged claims", 0)]
a_top = BT
for k, (s, ind) in enumerate(audit):
    txt(TX + ind, a_top - 0.075 - k * LH, s)
a_bot = a_top - (0.075 + (len(audit) - 1) * LH + 0.07)
box(CX0, a_bot, CX1, a_top, ec=INK)

y_sh = a_bot - 0.105
txt(CX0, y_sh, "One scoring, every draft", size=FH, weight="bold")
s_top = a_bot - 0.20
x_down = CX1 - 0.32
arrow(x_down, a_bot, x_down, s_top)                       # audited draft -> scoring

# reference paragraph g
RX0, RX1 = CX0 + 0.06, CX1 - 0.06
r_top = s_top - 0.06
ref = [("Curator paragraph $g$", "bold"),
       ("curator-written per-paper text: OMIM", "normal"),
       ("allelic-variant descriptions in ClinVar", "normal")]
for k, (s, w) in enumerate(ref):
    txt(RX0 + 0.06, r_top - 0.075 - k * LH, s, weight=w)
r_bot = r_top - (0.075 + (len(ref) - 1) * LH + 0.07)
box(RX0, r_bot, RX1, r_top, ec=GREY, fc=REF_FC)

# split once -> fixed fact list, with the availability tag
f_top = r_bot - 0.17
xa = RX0 + 0.20
arrow(xa, r_bot, xa, f_top)
txt(xa + 0.07, (r_bot + f_top) / 2, "split once, without sight of any draft")
f_bot = f_top - (0.075 + LH + 0.07)
FX1 = RX0 + 0.58
box(RX0, f_bot, FX1, f_top, ec=INK)
txt(RX0 + 0.06, f_top - 0.075, "fixed fact", weight="bold")
txt(RX0 + 0.06, f_top - 0.075 - LH, r"list $\Phi(g)$", weight="bold")
# tag (pentagon pointing at the fact list)
tx0, tx1 = FX1 + 0.10, FX1 + 0.10 + 1.30
tmid = (f_top + f_bot) / 2
ax.add_patch(Polygon([(tx0, tmid), (tx0 + 0.07, f_top), (tx1, f_top), (tx1, f_bot), (tx0 + 0.07, f_bot)],
                     closed=True, ec=GREY, fc="white", lw=0.6, zorder=1))
ax.plot([tx0 + 0.035], [tmid], "o", ms=1.6, mfc="white", mec=GREY, mew=0.5, zorder=3)
line([FX1, tx0], [tmid, tmid])
txt(tx0 + 0.11, f_top - 0.075, "stated / partly / not stated")
txt(tx0 + 0.11, f_top - 0.075 - LH, "in the supplied text")

# judging against the draft, primary measure, secondary fields
y = f_bot - 0.105
txt(TX, y, "→ each fact in the draft text citing the paper:")
txt(TX + IND, y - LH, "present / partly / absent / contradicted")
y2 = y - 2 * LH - 0.03
txt(TX, y2, "→ OMIM facts conveyed (primary)", weight="bold")
txt(TX + IND, y2 - LH, "(present + 0.5 × partly) / facts judged")
y_rule = y2 - LH - 0.085
line([RX0, RX1], [y_rule, y_rule], col=GROUP_EC, lw=0.5)
y3 = y_rule - 0.085
txt(TX, y3, "secondary: HPO disease annotations,")
txt(TX + IND, y3 - LH, "allelic variants, causal gene, inheritance")
s_bot = y3 - LH - 0.075
C_BOTTOM = s_bot

# ====================================================================== Column B: strategies
txt(BX0, HEAD, "Strategy (the only variable)", size=FH, weight="bold")
P0, P1 = BX0 + 0.06, BX1 - 0.06       # pill extent
ADD = 0.15                            # add-on indent
PH, ROW = 0.13, 0.16                  # pill height, row pitch
GAP = 0.06                            # between groups
TITLE = 0.135                         # group title row


def pill(x0, x1, yc, s, col=None):
    """Strategy pill (edge and dot in the strategy colour) or add-on pill (col None: dashed grey, '+')."""
    if col is None:
        box(x0, yc - PH / 2, x1, yc + PH / 2, ec=GREY, fc="white", lw=0.6, ls=(0, (2.2, 1.3)), r=0.04, z=3)
        txt(x0 + 0.05, yc, "+ " + s)
    else:
        box(x0, yc - PH / 2, x1, yc + PH / 2, ec=col, fc="white", lw=0.9, r=0.04, z=3)
        dot(x0 + 0.065, yc, col)
        txt(x0 + 0.115, yc, s)


def group_box(y_top, y_bot, title):
    box(BX0, y_bot, BX1, y_top, ec=GROUP_EC, fc=GROUP_FC, lw=0.6)
    txt(BX0 + 0.06, y_top - 0.07, title, weight="bold")


groups = []                            # (top, bottom) of each paradigm box

# --- Read and write
g_top = BT
y = g_top - TITLE - ROW / 2
pill(P0, P1, y, "Direct reading (baseline)", STRAT["Direct reading (baseline)"])
dr_y = y
tree_x = P0 + ADD / 2
ticks = []
for s in ["Second-hand evidence", "Learned curation guide"]:
    y -= ROW
    pill(P0 + ADD, P1, y, s)
    ticks.append(y)
# reading-better sub-box
SB_ROW = 0.122
sb_top = y - PH / 2 - 0.035
sb_rows = [[("checklist", 0.0), ("completeness pass", 0.56)],
           [("three-draft merge", 0.0)],
           [("checklist + completeness pass", 0.0)]]
sb_title_y = sb_top - 0.075
txt(P0 + ADD + 0.05, sb_title_y, "reading better", weight="bold")
for i, row in enumerate(sb_rows):
    yy = sb_title_y - 0.125 - i * SB_ROW
    for s, dx in row:
        dot(P0 + ADD + 0.10 + dx, yy, BETTER[s])
        txt(P0 + ADD + 0.15 + dx, yy, s)
sb_bot = sb_title_y - 0.125 - (len(sb_rows) - 1) * SB_ROW - 0.075
box(P0 + ADD, sb_bot, P1, sb_top, ec=GREY, fc="white", lw=0.6, r=0.04, z=3)
ticks.append(sb_title_y)
line([tree_x, tree_x], [dr_y - PH / 2, ticks[-1]])
for t in ticks:
    line([tree_x, P0 + ADD], [t, t])
y = sb_bot - 0.035 - PH / 2
pill(P0, P1, y, "Agentic curator", STRAT["Agentic curator"])
g_bot = y - PH / 2 - 0.035
group_box(g_top, g_bot, "Read and write")
groups.append((g_top, g_bot))

# --- Extract, then write
g_top = g_bot - GAP
y = g_top - TITLE - ROW / 2
pill(P0, P1, y, "Evidence graph", STRAT["Evidence graph"])
y -= ROW
pill(P0, P1, y, "Case table first", STRAT["Case table first"])
ct_y = y
y -= ROW
pill(P0 + ADD, P1, y, "Reconciled case database")
line([tree_x, tree_x, P0 + ADD], [ct_y - PH / 2, y, y])
g_bot = y - PH / 2 - 0.035
group_box(g_top, g_bot, "Extract, then write")
groups.append((g_top, g_bot))

# --- Memory first, Control (title and pill on one row)
for title, s, pill_w in [("Memory first", "Recall, then verify", 0.98), ("Control", "Memory only (no papers)", 1.30)]:
    g_top = g_bot - GAP
    g_bot = g_top - 0.20
    box(BX0, g_bot, BX1, g_top, ec=GROUP_EC, fc=GROUP_FC, lw=0.6)
    txt(BX0 + 0.06, (g_top + g_bot) / 2, title, weight="bold")
    pill(P1 - pill_w, P1, (g_top + g_bot) / 2, s, STRAT[s])
    groups.append((g_top, g_bot))
B_BOTTOM = g_bot

# ====================================================================== content bottom, column A
CB = min(B_BOTTOM, C_BOTTOM)
box(CX0, s_bot, CX1, s_top, ec=INK, z=0)    # scoring frame (drawn after the layout is known)

txt(AX0, HEAD, "Input (same for all)", size=FH, weight="bold")
box(AX0, CB, AX1, BT, ec=GREY, fc="none", lw=0.6)
txt(AX0 + 0.06, BT - 0.085, r"Entry $e=(h,R)$", weight="bold")
IX0, IX1 = AX0 + 0.05, AX1 - 0.05
# header h
h_top = BT - 0.18
hdr = [(r"Header $h$", "bold"), ("number, title,", "normal"), ("alternative titles", "normal")]
for k, (s, w) in enumerate(hdr):
    txt(IX0 + 0.05, h_top - 0.075 - k * LH, s, weight=w)
h_bot = h_top - (0.075 + 2 * LH + 0.07)
box(IX0, h_bot, IX1, h_top, ec=GREY, fc=REF_FC, lw=0.5)
# cited papers with access-level icons
p_top = h_bot - 0.10
txt(IX0 + 0.05, p_top - 0.075, r"Cited papers $R$", weight="bold")
IW, IHt = 0.12, 0.155
icon_x = IX0 + 0.08
rows = [("full text", 4), ("abstract", 2), (None, 0), ("title", 0)]
yc = p_top - 0.075 - 0.20
for lab, nbody in rows:
    if lab is None:                    # vertical ellipsis: more papers
        for dy in (-0.035, 0.0, 0.035):
            ax.plot([icon_x + IW / 2], [yc + dy], "o", ms=1.3, color=INK, zorder=5)
        yc -= 0.16
        continue
    y0 = yc - IHt / 2
    ax.add_patch(Rectangle((icon_x, y0), IW, IHt, ec=INK, fc="white", lw=0.6, zorder=3))
    line([icon_x + 0.022, icon_x + IW - 0.022], [y0 + IHt - 0.032] * 2, col=INK, lw=1.2)
    for k in range(nbody):
        yy = y0 + IHt - 0.062 - k * 0.022
        line([icon_x + 0.022, icon_x + IW - 0.022], [yy, yy], col=GREY, lw=0.5)
    txt(icon_x + IW + 0.07, yc, lab)
    yc -= 0.215
acc_y = yc + 0.215 - IHt / 2 - 0.13
txt(IX0 + 0.05, acc_y, r"access level $a(d)$,")
txt(IX0 + 0.05, acc_y - LH, "set by open access")
p_bot = acc_y - LH - 0.075
box(IX0, p_bot, IX1, p_top, ec=GREY, fc=REF_FC, lw=0.5)
# padlock: causal gene withheld
lk_x, lk_y = IX0 + 0.08, p_bot - 0.20
ax.add_patch(Rectangle((lk_x, lk_y - 0.045), 0.09, 0.07, ec=SOFT, fc=SOFT, lw=0.6, zorder=3))
ax.add_patch(Arc((lk_x + 0.045, lk_y + 0.025), 0.058, 0.085, theta1=0, theta2=180, ec=SOFT, lw=1.1, zorder=3))
line([lk_x + 0.016, lk_x + 0.016], [lk_y + 0.025, lk_y + 0.02], col=SOFT, lw=1.1)
line([lk_x + 0.074, lk_x + 0.074], [lk_y + 0.025, lk_y + 0.02], col=SOFT, lw=1.1)
txt(lk_x + 0.15, lk_y + LH / 2 - 0.005, "causal gene", color=SOFT)
txt(lk_x + 0.15, lk_y - LH / 2 - 0.005, "withheld", color=SOFT)
A_CONTENT_BOTTOM = lk_y - LH / 2 - 0.06

# ====================================================================== brackets and arrows
g_first_top, g_last_bot = groups[0][0], groups[-1][1]
# fan-out: input -> every strategy group
bx = BX0 - 0.045
line([bx, bx], [groups[0][0] - 0.10, groups[-1][1] + 0.10], col=INK, lw=0.7)
for gt, gb in groups:
    ym = min(gt - 0.10, (gt + gb) / 2) if gt - gb > 0.5 else (gt + gb) / 2
    line([bx, BX0], [ym, ym], col=INK, lw=0.7)
y_in = (BT + CB) / 2
arrow(AX1, y_in, bx, y_in)
# fan-in: every strategy group -> one draft D -> audit
bx2 = BX1 + 0.045
for gt, gb in groups:
    ym = min(gt - 0.10, (gt + gb) / 2) if gt - gb > 0.5 else (gt + gb) / 2
    line([BX1, bx2], [ym, ym], col=INK, lw=0.7)
y_d = (a_top + a_bot) / 2
line([bx2, bx2], [groups[-1][1] + 0.10, groups[0][0] - 0.10], col=INK, lw=0.7)
arrow(bx2, y_d, CX0, y_d)
txt((bx2 + CX0) / 2, y_d + 0.08, r"$D$", ha="center")

# ====================================================================== bottom band: guards
band_top = CB - 0.08
band_bot = band_top - (0.075 + LH + 0.075)
box(AX0, band_bot, CX1, band_top, ec=GROUP_EC, fc=GROUP_FC, lw=0.6)
cells = [("Guards for", "every strategy"),
         ("ontology IDs only from", "ontology-search candidates"),
         ("gene symbols", "normalised (HGNC)"),
         ("recalled cross-reference", "numbers removed"),
         ("every paragraph cites", "a supplied paper")]
widths = [0.71, 1.19, 0.85, 1.04, 0.93]          # widest line of each cell (in, measured at 7 pt)
free = (CX1 - AX0) - 0.12 - sum(widths)
sep = free / (len(cells) - 1)
x = AX0 + 0.06
for i, ((l1, l2), w) in enumerate(zip(cells, widths)):
    wt = "bold" if i == 0 else "normal"
    txt(x, band_top - 0.075, l1, weight=wt)
    txt(x, band_top - 0.075 - LH, l2, weight=wt)
    if i < len(cells) - 1:
        xs = x + w + sep / 2
        line([xs, xs], [band_bot + 0.04, band_top - 0.04], col=GROUP_EC, lw=0.6)
    x += w + sep

# ====================================================================== frame the drawing at 1 in per unit
y_min = band_bot - 0.02
H = -y_min
fig.set_size_inches(W, H)
ax.set_xlim(0, W)
ax.set_ylim(y_min, 0)
print(f"figsize {W} x {H:.3f} in; bottoms: A {A_CONTENT_BOTTOM:.3f} B {B_BOTTOM:.3f} C {C_BOTTOM:.3f}")

out = os.environ["PO_OUT"]
fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.02)
root, ext = os.path.splitext(out)
if ext.lower() != ".pdf":
    fig.savefig(root + ".pdf", facecolor="white", bbox_inches="tight", pad_inches=0.02)
