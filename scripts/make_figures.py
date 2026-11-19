#!/usr/bin/env python3
"""Figures for the paper draft, built only from committed result files.

Reads:
  results/omim100/strategies.json
  results/omim100/gaps.direct.json
  results/omim100_secondhand/strategies.json
  results/omim100_secondhand/secondhand_check.json
  results/omim100_reconciled/strategies.json

Writes docs/figures/fig*.png (300 dpi) and fig*.svg, and prints every plotted
value so it can be checked against the paper's tables. Output is deterministic:
fixed SVG hash salt, no timestamps in metadata.

Usage: python scripts/make_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "figures"

SINGLE = 3.5   # inches, one journal column (~89 mm)
FULL = 7.2     # inches, full page width (~183 mm)

# ---- palette (dataviz reference palette, light mode; validated with
# validate_palette.js --pairs all on a white surface) -----------------------
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
WHITE = "#ffffff"

# Colour follows the strategy in every figure.
STRAT_COLOR = {
    "direct": "#2a78d6",      # blue  (slot 1)
    "kg": "#eb6834",          # orange (slot 2)
    "agent": "#1baf7a",       # aqua  (slot 3)
    "cohort": "#6250d6",      # violet (slot 7)
    "closedbook": MUTED,      # control: neutral gray
    "recall": "#e87ba4",      # magenta (slot 5)
}
STRAT_MARKER = {"direct": "o", "kg": "o", "agent": "s", "cohort": "D",
                "closedbook": "o", "recall": "^"}

# Blue ordinal ramp (access levels: more text = darker)
BLUE = {250: "#86b6ef", 450: "#2a78d6", 650: "#104281"}
# Red arm of the blue<->red diverging pair, plus neutral gray
RED_LIGHT = "#f2a6a5"
RED = "#e34948"
RED_DARK = "#a8302f"
NEUTRAL = "#d6d5cf"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 7.5,
    "axes.titlesize": 8,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.6,
    "axes.labelcolor": INK2,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "text.color": INK,
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "savefig.facecolor": WHITE,
    "svg.hashsalt": "aiomim-figures",
    "svg.fonttype": "path",
    "legend.frameon": False,
})


def load(rel: str) -> dict:
    with open(ROOT / rel, encoding="utf-8") as fh:
        return json.load(fh)


def save(fig, name: str) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{name}.png"
    svg = OUT / f"{name}.svg"
    fig.savefig(png, dpi=300, facecolor=WHITE, metadata={"Software": None})
    fig.savefig(svg, facecolor=WHITE, metadata={"Date": None, "Creator": None})
    plt.close(fig)
    return [png, svg]


def header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def clean_axes(ax, grid_axis: str = "x") -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def strat_labels(s: dict) -> dict[str, str]:
    return {x["name"]: x["label"] for x in s["strategies"]}


def short_label(label: str) -> str:
    return label.replace(" (control)", "").replace("Recall, then verify",
                                                   "Recall then verify")


def metric(s: dict, name: str, section: str = "means") -> dict:
    for m in s[section]:
        if m["metric"] == name:
            return m
    raise KeyError(name)


# Strategy order used throughout: baseline, the three close competitors, then
# the two far-off ones (recall, control last).
ORDER = ["direct", "kg", "agent", "cohort", "recall", "closedbook"]


# ---------------------------------------------------------------------------
# Figure 1: study design schematic
# ---------------------------------------------------------------------------
def fig1(s100: dict, s2h: dict, srec: dict) -> list[Path]:
    header("fig1_design: study schematic (labels from strategies.json files)")
    lab = strat_labels(s100)
    lab2 = strat_labels(s2h)
    labr = strat_labels(srec)
    head = [short_label(lab[k]) for k in ORDER]
    built = [
        (lab2["secondhand"], f"on {lab2['direct']}"),
        (labr["reconciled"], f"on {labr['cohort']}"),
        ("Learned curation guide", f"on {lab['direct']}"),
    ]
    print("Compared head to head:", "; ".join(head))
    print("Built on them:", "; ".join(f"{a} ({b})" for a, b in built))
    print(f"Entries: {s100['n_entries']} (head to head), "
          f"{s2h['n_entries']} (second-hand), {srec['n_entries']} (reconciled)")

    fig = plt.figure(figsize=(FULL, 3.15))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 44)
    ax.axis("off")

    def box(x, y, w, h, text, fc=WHITE, ec=AXIS, size=7, weight="normal",
            color=INK, lw=0.8, ha="center"):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8",
                           fc=fc, ec=ec, lw=lw)
        ax.add_patch(p)
        tx = x + w / 2 if ha == "center" else x + 1.2
        ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=size,
                fontweight=weight, color=color, linespacing=1.3)

    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                     mutation_scale=8, lw=0.9, color=INK2,
                                     shrinkA=0, shrinkB=0))

    def group(x, y, w, h, title):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0,rounding_size=1.2",
                                    fc="#f6f6f3", ec="none"))
        ax.text(x + 1.2, y + h - 1.6, title, ha="left", va="center",
                fontsize=7, fontweight="bold", color=INK2)

    # Column 1: inputs
    group(1, 6, 20, 32, "Inputs per entry")
    box(2.5, 27.5, 17, 6.5, "Entry header\n(title, MIM number)")
    box(2.5, 8, 17, 17.5,
        "Papers OMIM cites,\nas readable:\n\n" "full text\n" "or abstract only\n"
        "or title only")

    # Column 2: generation strategies
    group(25, 1, 40.5, 42, "Generation strategies")
    ax.text(26.2, 38.6, "Compared head to head", fontsize=6.8, color=INK2,
            ha="left", va="center")
    bw, bh = 18.3, 4.6
    for i, k in enumerate(ORDER):
        col, row = i % 2, i // 2
        x = 26.2 + col * (bw + 1.4)
        y = 31.3 - row * (bh + 1.2)
        txt = short_label(lab[k]) + ("  (control)" if k == "closedbook" else "")
        box(x, y, bw, bh, txt, ec=STRAT_COLOR[k], lw=1.4, size=6.8)
    ax.text(26.2, 16.6, "Built on them", fontsize=6.8, color=INK2,
            ha="left", va="center")
    for i, (a, b) in enumerate(built):
        y = 11.6 - i * 4.4
        box(26.2, y, 38.0, 3.4, f"{a}  ({b})", size=6.6, ec=AXIS)

    # Column 3: audit + repair
    group(69.5, 13, 13.5, 18, "Same for all")
    box(70.5, 20.5, 11.5, 6.5, "Claim-level\naudit against\ncited paper", size=6.6)
    box(70.5, 14.2, 11.5, 4.6, "One repair\nround", size=6.6)
    arrow(76.25, 20.5, 76.25, 18.8)

    # Column 4: scoring
    group(85, 1, 14, 42, "Scored against\nOMIM gold")
    gold = ["Per-paper\nparagraphs\n(facts)", "Clinical synopsis\nas HPO terms",
            "Allelic\nvariants", "Causal gene", "Inheritance"]
    gy = 34.5
    for g in gold:
        h = 6.0 if g.count("\n") >= 2 else 4.6 if "\n" in g else 3.6
        box(86, gy - h, 12, h, g, size=6.4)
        gy -= h + 1.3

    # arrows between columns
    arrow(21, 22, 25, 22)
    arrow(65.5, 22, 69.5, 22)
    arrow(83, 22, 85, 22)
    return save(fig, "fig1_design")


# ---------------------------------------------------------------------------
# Figure 2: paired differences from direct reading
# ---------------------------------------------------------------------------
FIG2_METRICS = [
    ("claim_supported_rate", "Claims supported"),
    ("gold_fact_coverage", "OMIM facts conveyed"),
    ("hpo_exact_f1", "Clinical synopsis F1, exact"),
    ("hpo_hierarchical_f1", "Clinical synopsis F1, hierarchical"),
    ("variant_recall", "Allelic variants recovered"),
    ("inheritance_match", "Inheritance match"),
]
FIG2_STRATS = ["kg", "agent", "cohort"]


def fig2(s100: dict) -> list[Path]:
    header("fig2_paired_differences: strategy minus Direct reading, "
           "percentage points [95% CI]")
    lab = strat_labels(s100)
    vb = s100["versus_baseline"]
    fig, ax = plt.subplots(figsize=(FULL, 3.4))
    offsets = {"kg": -0.24, "agent": 0.0, "cohort": 0.24}
    yt, yl = [], []
    lo_all, hi_all = 0.0, 0.0
    for i, (mname, mlabel) in enumerate(FIG2_METRICS):
        y0 = i
        yt.append(y0)
        yl.append(mlabel)
        if i % 2 == 0:
            ax.axhspan(y0 - 0.5, y0 + 0.5, color="#f6f6f3", zorder=0, lw=0)
        for k in FIG2_STRATS:
            m = next(r for r in vb[k] if r["metric"] == mname)
            d = 100 * m["difference"]
            lo, hi = (100 * v for v in m["ci95"])
            lo_all, hi_all = min(lo_all, lo), max(hi_all, hi)
            y = y0 + offsets[k]
            ax.plot([lo, hi], [y, y], color=STRAT_COLOR[k], lw=1.6,
                    solid_capstyle="round", zorder=2)
            ax.plot(d, y, marker=STRAT_MARKER[k], ms=5.2, color=STRAT_COLOR[k],
                    mec=WHITE, mew=1.0, zorder=3)
            print(f"  {mlabel:38s} {lab[k]:18s} n={m['n']:3d}  "
                  f"diff {d:+6.2f} pp  [{lo:+6.2f}, {hi:+6.2f}]  "
                  f"(strategy {pct(m['strategy'])}, direct {pct(m['baseline'])})")
    ax.axvline(0, color=INK2, lw=0.9, zorder=1)
    ax.set_yticks(yt, yl)
    ax.set_ylim(len(FIG2_METRICS) - 0.5, -0.5)
    pad = 1.0
    ax.set_xlim(min(-10, lo_all - pad), max(6, hi_all + pad))
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(2))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:+.0f}".replace("-", "\u2212") if v else "0"))
    ax.set_xlabel("Difference from Direct reading (percentage points), "
                  "paired by entry, with 95% interval")
    ax.tick_params(axis="y", length=0)
    clean_axes(ax, "x")
    ax.spines["left"].set_visible(False)
    handles = [Line2D([], [], color=STRAT_COLOR[k], marker=STRAT_MARKER[k],
                      ms=5.2, mec=WHITE, lw=1.6, label=lab[k])
               for k in FIG2_STRATS]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.005, 0.995),
               ncol=3, handlelength=2.2, columnspacing=1.5)
    xform = ax.get_xaxis_transform()
    ax.text(0.3, 1.01, "better →", transform=xform, fontsize=6.5,
            color=INK2, va="bottom", ha="left")
    ax.text(-0.3, 1.01, "← worse", transform=xform, fontsize=6.5,
            color=INK2, va="bottom", ha="right")
    # note on omitted strategies, with their gaps read from the file
    def diff(k, mname):
        return 100 * next(r for r in vb[k] if r["metric"] == mname)["difference"]

    far = ("recall", "closedbook")
    names = " and ".join(short_label(lab[k]) for k in far)
    facts = " and ".join(f"{diff(k, 'gold_fact_coverage'):+.0f}" for k in far)
    variants = " and ".join(f"{diff(k, 'variant_recall'):+.0f}" for k in far)
    note = (f"Not shown: {names}, far below Direct reading "
            f"(OMIM facts conveyed {facts} pp; allelic variants {variants} pp)."
            ).replace("-", "\u2212")
    print("  note:", note)
    fig.text(0.01, 0.015, note, fontsize=6.5, color=INK2, ha="left", va="bottom")
    fig.subplots_adjust(left=0.235, right=0.98, top=0.885, bottom=0.2)
    return save(fig, "fig2_paired_differences")


# ---------------------------------------------------------------------------
# Figure 3: OMIM facts conveyed by content level
# ---------------------------------------------------------------------------
LEVELS = [("fulltext", "Full text", BLUE[650], "o"),
          ("abstract", "Abstract only", BLUE[450], "s"),
          ("title", "Title only", BLUE[250], "D")]


def fig3(s100: dict) -> list[Path]:
    header("fig3_access: OMIM facts conveyed by how the paper was readable "
           "(partial credit; pooled over facts)")
    lab = strat_labels(s100)
    bcl = s100["by_content_level"]
    order = ORDER
    fig, ax = plt.subplots(figsize=(SINGLE, 2.9))
    for i, k in enumerate(order):
        vals = [bcl[lv][k]["coverage"] for lv, *_ in LEVELS]
        ax.plot([100 * min(vals), 100 * max(vals)], [i, i], color=GRID, lw=2.0,
                zorder=1, solid_capstyle="round")
        for (lv, name, col, mk) in LEVELS:
            c = bcl[lv][k]
            ax.plot(100 * c["coverage"], i, marker=mk, ms=6, color=col,
                    mec=WHITE, mew=1.0, zorder=3, ls="none")
            print(f"  {lab[k]:24s} {name:14s} {pct(c['coverage']):>6s}  "
                  f"(facts {c['n_facts']}, present {c['present']}, "
                  f"partial {c['partial']}, contradicted {c['contradicted']})")
    names = [short_label(lab[k]) + ("\n(control)" if k == "closedbook" else "")
             for k in order]
    ax.set_yticks(range(len(order)), names)
    ax.set_ylim(len(order) - 0.5, -0.6)
    ax.set_xlim(0, 85)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("OMIM per-paper facts conveyed")
    ax.tick_params(axis="y", length=0)
    clean_axes(ax, "x")
    ax.spines["left"].set_visible(False)
    nf = {lv: bcl[lv]["direct"]["n_facts"] for lv, *_ in LEVELS}
    handles = [Line2D([], [], marker=mk, color=col, mec=WHITE, ms=6, ls="none",
                      label=f"{name}")
               for lv, name, col, mk in LEVELS]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.02, 1.0),
              ncol=3, handletextpad=0.2, columnspacing=1.0, borderaxespad=0.2)
    print("  OMIM facts per level (Direct reading):", nf)
    fig.subplots_adjust(left=0.30, right=0.97, top=0.89, bottom=0.15)
    return save(fig, "fig3_access")


# ---------------------------------------------------------------------------
# Figure 4: fate of OMIM's facts under direct reading
# ---------------------------------------------------------------------------
FATE = [
    ("present", "Conveyed", BLUE[450], WHITE),
    ("yes", "Not conveyed, though stated in the text", RED, WHITE),
    ("partly", "Not conveyed, partly stated", RED_LIGHT, INK),
    ("no", "Not in the available text", NEUTRAL, INK),
    ("contradicted", "Contradicted", RED_DARK, WHITE),
]


def fig4(gaps: dict) -> list[Path]:
    header("fig4_gap: Direct reading, fate of each OMIM fact "
           "(a fact the draft states only partly counts as not conveyed)")
    rows = [("fulltext", "Full text"), ("abstract", "Abstract only"),
            ("title", "Title only"), ("overall", "All papers")]
    fig, ax = plt.subplots(figsize=(SINGLE, 2.75))
    bar_h = 0.62
    for i, (key, name) in enumerate(rows):
        d = gaps["overall"] if key == "overall" else gaps["by_content_level"][key]
        n = d["n_gold_facts"]
        counts = [d[f] for f, *_ in FATE]
        if sum(counts) != n:
            print(f"  WARNING: {name}: categories sum to {sum(counts)}, not {n}")
        left = 0.0
        parts = []
        for (f, lname, col, tcol), c in zip(FATE, counts):
            w = 100 * c / n
            ax.barh(i, w, left=left, height=bar_h, color=col, edgecolor=WHITE,
                    linewidth=1.0)
            if w >= 7:
                ax.text(left + 1.0, i, f"{w:.0f}%", va="center", ha="left",
                        fontsize=6.3, color=tcol)
            left += w
            parts.append(f"{lname.split(',')[0] if f=='present' else f}={c} ({w:.1f}%)")
        print(f"  {name:13s} n={n:5d}: " + "; ".join(
            f"{lname}: {c} ({100*c/n:.1f}%)" for (f, lname, *_), c in zip(FATE, counts)))
    labels = []
    for key, name in rows:
        d = gaps["overall"] if key == "overall" else gaps["by_content_level"][key]
        labels.append(f"{name}\nn = {d['n_gold_facts']:,}")
    ax.set_yticks(range(len(rows)), labels)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.axhline(2.5, color=AXIS, lw=0.6)
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("Share of OMIM per-paper facts")
    ax.tick_params(axis="y", length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    handles = [Patch(fc=col, ec="none", label=lname) for _, lname, col, _ in FATE]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.01, 0.0),
               ncol=2, handlelength=1.0, handleheight=1.0, columnspacing=1.0,
               fontsize=6.3, labelspacing=0.35)
    fig.subplots_adjust(left=0.25, right=0.97, top=0.98, bottom=0.36)
    return save(fig, "fig4_gap")


# ---------------------------------------------------------------------------
# Figure 5: memory only vs direct reading by creation era
# ---------------------------------------------------------------------------
FIG5_METRICS = [("gold_fact_coverage", "OMIM facts conveyed"),
                ("inheritance_match", "Inheritance match"),
                ("hpo_exact_f1", "Clinical synopsis F1, exact")]


def era_order(keys: list[str]) -> list[str]:
    def k(s: str) -> int:
        if s.startswith("classic"):
            return 0
        return int(s.split("-")[0].split(" ")[0])
    return sorted(keys, key=k)


def era_label(s: str) -> str:
    if s.startswith("classic"):
        return "Classic\n(1xxxxx–5xxxxx)"
    if "onward" in s:
        return s.replace(" onward", "\nonward")
    a, b = s.split("-")
    return f"{a}–\n{b}"


def fig5(s100: dict) -> list[Path]:
    header("fig5_memory_by_era: Memory only vs Direct reading by creation era")
    lab = strat_labels(s100)
    bs = s100["by_stratum"]
    eras = era_order(list(bs))
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 2.65), sharey=True)
    for ax, (mname, mlabel) in zip(axes, FIG5_METRICS):
        print(f"  {mlabel}")
        for k in ("direct", "closedbook"):
            ys, ns = [], []
            for e in eras:
                m = next(r for r in bs[e]["means"] if r["metric"] == mname)
                ys.append(100 * m["values"][k])
                ns.append(m["n"][k])
            x = list(range(len(eras)))
            ax.plot(x, ys, color=STRAT_COLOR[k], lw=2, marker="o", ms=5,
                    mec=WHITE, mew=1.0, solid_capstyle="round", zorder=3)
            print(f"    {lab[k]:22s} " + "  ".join(
                f"{e.split(' ')[0]}: {y:5.1f}% (n={n})"
                for e, y, n in zip(eras, ys, ns)))
        ax.set_title(mlabel, loc="left", fontsize=7.5, color=INK, pad=4)
        ax.set_xticks(range(len(eras)), [era_label(e) for e in eras],
                      fontsize=5.8)
        ax.set_xlim(-0.35, len(eras) - 0.65)
        ax.set_ylim(0, 105)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"{v:.0f}%"))
        clean_axes(ax, "y")
    axes[0].set_ylabel("Mean per entry")
    ns = [bs[e]["n"] for e in eras]
    print("  entries per band:", dict(zip(eras, ns)))
    handles = [Line2D([], [], color=STRAT_COLOR[k], lw=2, marker="o", ms=5,
                      mec=WHITE, label=short_label(lab[k]) +
                      (" (control)" if k == "closedbook" else ""))
               for k in ("direct", "closedbook")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.07, 1.0),
               ncol=2, columnspacing=2.0)
    fig.text(0.99, 0.985, "Creation-era band of the MIM number, oldest left; "
             f"{min(ns)}–{max(ns)} entries per band",
             ha="right", va="top", fontsize=6.3, color=INK2)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.84, bottom=0.2, wspace=0.12)
    return save(fig, "fig5_memory_by_era")


# ---------------------------------------------------------------------------
# Figure 6: hidden-full-text experiment
# ---------------------------------------------------------------------------
VERDICTS = [
    ("supported", "Supported", BLUE[650], WHITE),
    ("partially_supported", "Partly supported", BLUE[250], INK),
    ("unsupported", "Unsupported", RED_LIGHT, INK),
    ("contradicted", "Contradicted", RED_DARK, WHITE),
    ("no_verdict", "No verdict", NEUTRAL, INK),
]


def fig6(chk: dict) -> list[Path]:
    header("fig6_secondhand: hidden-full-text experiment "
           f"({chk['n_entries']} entries, "
           f"{chk['retrieval']['hidden_papers']} hidden papers)")
    fig = plt.figure(figsize=(FULL, 2.7))
    axa = fig.add_axes([0.075, 0.33, 0.27, 0.56])
    axb = fig.add_axes([0.53, 0.33, 0.45, 0.56])

    # (a) coverage
    conds = [("abstract", "Abstract\nonly"),
             ("secondhand", "Abstract +\nsecond-hand"),
             ("fulltext", "Full text")]
    cov = chk["coverage"]
    print("  (a) OMIM facts conveyed for the gold paragraphs about hidden papers "
          f"({cov['abstract']['paragraphs']} paragraphs)")
    for i, (c, name) in enumerate(conds):
        v = 100 * cov[c]["coverage"]
        axa.bar(i, v, width=0.5, color=BLUE[450], edgecolor="none")
        axa.text(i, v + 1.5, f"{v:.1f}%", ha="center", va="bottom",
                 fontsize=6.8, color=INK)
        d = cov[c]
        print(f"    {name.replace(chr(10), ' '):26s} {v:5.1f}%  (facts {d['n_facts']}, "
              f"present {d['present']}, partial {d['partial']}, absent {d['absent']}, "
              f"contradicted {d['contradicted']})")
    axa.set_xticks(range(3), [n for _, n in conds])
    axa.set_ylim(0, 85)
    axa.set_xlim(-0.55, 2.55)
    axa.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:.0f}%"))
    axa.set_ylabel("OMIM facts conveyed")
    axa.tick_params(axis="x", length=0)
    clean_axes(axa, "y")
    axa.set_title("a   Coverage of the hidden papers", loc="left",
                  fontsize=7.5, x=-0.25, pad=8)

    # (b) verdicts against full text
    cl = chk["claims"]
    groups = [
        ("Paper's own abstract", cl["by_evidence_location"]["own"]),
        ("Later paper, running text", cl["secondhand_by_passage_kind"]["paragraph"]),
        ("Later paper, table row", cl["secondhand_by_passage_kind"]["table"]),
    ]
    print("  (b) verdicts against the paper's full text, by evidence the claim "
          "rested on (claims not collapsed)")
    for i, (name, g) in enumerate(groups):
        n = g["n"]
        v = g["against_full_text"]
        tot = sum(v[k] for k, *_ in VERDICTS)
        if tot != n:
            print(f"    WARNING: {name}: verdicts sum to {tot}, not n={n}")
        left = 0.0
        for k, vname, col, tcol in VERDICTS:
            w = 100 * v[k] / n
            axb.barh(i, w, left=left, height=0.6, color=col, edgecolor=WHITE,
                     linewidth=1.0)
            if w >= 7:
                axb.text(left + 1.0, i, f"{w:.0f}%", va="center", ha="left",
                         fontsize=6.3, color=tcol)
            left += w
        print(f"    {name:28s} n={n:5d}: " + "; ".join(
            f"{vname} {v[k]} ({100*v[k]/n:.1f}%)" for k, vname, *_ in VERDICTS))
    axb.set_yticks(range(3), [f"{name}\nn = {g['n']:,}" for name, g in groups])
    axb.set_ylim(2.5, -0.5)
    axb.set_xlim(0, 100)
    axb.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:.0f}%"))
    axb.set_xlabel("Share of claims, judged against the paper's full text")
    axb.tick_params(axis="y", length=0)
    for side in ("top", "right", "left"):
        axb.spines[side].set_visible(False)
    axb.set_title("b   Claims about hidden papers, by the evidence they rested on",
                  loc="left", fontsize=7.5, x=-0.36, pad=8)
    handles = [Patch(fc=col, ec="none", label=vn) for _, vn, col, _ in VERDICTS]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.36, 0.0),
               ncol=5, handlelength=1.0, handleheight=1.0, columnspacing=1.2,
               fontsize=6.5)
    return save(fig, "fig6_secondhand")


# ---------------------------------------------------------------------------
# Figure 7: cost vs coverage
# ---------------------------------------------------------------------------
def fig7(s100: dict) -> list[Path]:
    header("fig7_cost: generation cost per entry (list price, USD) vs "
           "OMIM facts conveyed")
    lab = strat_labels(s100)
    cov = metric(s100, "gold_fact_coverage")["values"]
    cost = s100["cost"]
    fig, ax = plt.subplots(figsize=(SINGLE, 2.7))
    # label offsets in points, chosen to avoid collisions
    off = {"direct": (6, 4), "kg": (6, 4), "agent": (-6, -11),
           "cohort": (6, -10), "recall": (-6, 6), "closedbook": (6, 4)}
    ha = {"agent": "right", "recall": "right"}
    for k in ORDER:
        x = cost[k]["generate"]["per_entry"]["list_price_usd"]
        y = 100 * cov[k]
        ctrl = k == "closedbook"
        ax.plot(x, y, marker="o", ms=6.5, ls="none",
                mfc=WHITE if ctrl else INK2, mec=INK2, mew=1.4, zorder=3)
        name = short_label(lab[k]) + (" (control)" if ctrl else "")
        ax.annotate(name, (x, y), xytext=off[k], textcoords="offset points",
                    fontsize=6.6, color=INK, ha=ha.get(k, "left"), va="center")
        print(f"  {lab[k]:24s} generate ${x:.3f}/entry "
              f"(n={cost[k]['entries']}; total incl. audit+score "
              f"${cost[k]['total']['per_entry']['list_price_usd']:.3f})  "
              f"facts conveyed {y:.1f}%")
    ax.set_xlim(0, 0.8)
    ax.set_ylim(0, 60)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"${v:.2f}"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("Generation cost per entry (list price)")
    ax.set_ylabel("OMIM facts conveyed")
    clean_axes(ax, "both")
    ax.text(0.99, 0.02, "Hollow marker: control (no papers)",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6.3,
            color=INK2)
    fig.subplots_adjust(left=0.15, right=0.97, top=0.97, bottom=0.16)
    return save(fig, "fig7_cost")


def main() -> None:
    s100 = load("results/omim100/strategies.json")
    gaps = load("results/omim100/gaps.direct.json")
    s2h = load("results/omim100_secondhand/strategies.json")
    chk = load("results/omim100_secondhand/secondhand_check.json")
    srec = load("results/omim100_reconciled/strategies.json")

    written: list[Path] = []
    written += fig1(s100, s2h, srec)
    written += fig2(s100)
    written += fig3(s100)
    written += fig4(gaps)
    written += fig5(s100)
    written += fig6(chk)
    written += fig7(s100)
    header("files written")
    for p in written:
        print(" ", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
