"""Figures for the reliability-facing measurements.

Figure R1  two criteria, two error directions
  (a) false alarm and miss against margin, for both criteria in use
  (b) coverage against the depth of the shortfall, with Jung's bound on that depth
  (c) the three verdicts swept through the boundary: the record's support ends
      where the criterion's blind spot begins

Figure R2  why the criterion survives
  (a) the share of the design box a build record can occupy
  (b) how much of the hardware clearing the table cannot be aligned at all
  (c) how many units must fly before a miss could be seen
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "analysis" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "outputs_ress"

EXACT = "#1f4e79"
PAIR = "#c0504d"
GOLD = "#bf9000"
GREY = "#7f7f7f"
TEAL = "#2e7d6f"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.4,
    "axes.titlesize": 9.0,
    "axes.labelsize": 8.2,
    "axes.edgecolor": "#444444",
    "axes.linewidth": 0.8,
    "figure.dpi": 200,
})


def load(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        d = {}
        for k, v in r.items():
            if v == "True":
                d[k] = True
            elif v == "False":
                d[k] = False
            else:
                try:
                    d[k] = float(v)
                except ValueError:
                    d[k] = v
        out.append(d)
    return out


def tag(ax, text):
    ax.set_title(text, loc="left", fontsize=8.9, pad=4)


def fig_r1() -> None:
    gp = load("gate_profile.csv")
    sh = load("shortfall.csv")
    rb = load("record.csv")

    fig, axs = plt.subplots(1, 3, figsize=(7.3, 2.45),
                            gridspec_kw={"width_ratios": [1.0, 1.0, 1.12]})

    # (a) two error directions ------------------------------------------------
    ax = axs[0]
    for n, ls, lw, alpha, lab in ((9, "-", 1.35, 1.0, "n=9"),
                                  (3, "--", 0.9, 0.7, None)):
        rows = sorted([r for r in gp if r["n"] == n], key=lambda r: r["A_over_sigma"])
        x = [r["A_over_sigma"] for r in rows]
        ax.plot(x, [max(r["fr_P"], 1e-5) for r in rows], ls, color=GOLD, lw=lw,
                alpha=alpha, marker="o", ms=2.4,
                label="per-channel gate://nrejects good hardware" if lab else None)
        ax.plot(x, [max(r["fa_W"], 1e-5) for r in rows], ls, color=PAIR, lw=lw,
                alpha=alpha, marker="s", ms=2.4,
                label="pairwise gate://naccepts bad hardware" if lab else None)
    ax.set_yscale("log")
    ax.set_ylim(4e-6, 12.0)
    ax.set_xlim(0.9, 3.15)
    ax.set_xlabel("tightest allocation / $\\sigma$")
    ax.set_ylabel("share of as-built draws")
    ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1e0])
    ax.text(0.97, 6.2, "per-channel", fontsize=6.2, color=GOLD, va="center")
    ax.text(0.97, 2.1, "pairwise", fontsize=6.2, color=PAIR, va="center")
    ax.set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1e0])
    ax.text(0.97, 6.2, "per-channel", fontsize=6.2, color=GOLD, va="center")
    ax.text(0.97, 2.1, "pairwise", fontsize=6.2, color=PAIR, va="center")
    tag(ax, "(a) two error directions")

    # (b) what stays visible --------------------------------------------------
    ax = axs[1]
    for n, col, mk in ((3, TEAL, "o"), (5, EXACT, "s"), (9, PAIR, "^")):
        rows = [r for r in sh if r["n"] == n and abs(r["A_over_sigma"] - 1.5) < 1e-6
                and not math.isnan(r["shortfall_lo"])]
        rows.sort(key=lambda r: r["shortfall_lo"])
        xs = [0.0] + [r["shortfall_hi"] * 100 for r in rows]
        ys = [1.0] + [r["coverage"] for r in rows]
        ax.step(xs, ys, where="post", color=col, lw=1.15, marker=mk, ms=2.3,
                label=f"n={n}")
    bound = 100 * (2.0 / math.sqrt(3.0) - 1.0)
    ax.axvspan(bound, 34, color="#f7e3e2", zorder=0)
    ax.axvline(bound, color=PAIR, lw=0.85, ls="--")
    ax.text(bound + 1.0, 1.185, "Jung bound\n15.47%", fontsize=6.1, color=PAIR,
            va="top", linespacing=1.2)
    ax.text(bound + 4.2, 0.68, "nothing can be\nmissed here", fontsize=6.1,
            color="#8b3a36", va="center", linespacing=1.25)
    ax.set_xlim(0, 34)
    ax.set_ylim(0.42, 1.22)
    ax.set_xlabel("shortfall, % of the allocation")
    ax.set_ylabel("P(reject | no common point)", fontsize=7.9)
    ax.legend(fontsize=6.0, loc="lower right", frameon=False, handlelength=1.4,
              borderaxespad=0.25, labelspacing=0.22)
    tag(ax, "(b) what stays visible")

    # (c) where they meet -----------------------------------------------------
    ax = axs[2]
    rows = sorted(rb, key=lambda r: r["r_over_A"])
    bands = (("common point\nexists", "exact_ok", EXACT, 2),
             ("table\naccepts", "pairwise_ok", PAIR, 1),
             ("every channel\nin allocation", "per_channel_ok", GOLD, 0))
    x0 = 0.52
    for label, key, col, y in bands:
        bad = [r["r_over_A"] for r in rows if r[key] is False]
        stop = min(bad) if bad else 1.55
        ax.add_patch(Rectangle((x0, y - 0.26), stop - x0, 0.52,
                               facecolor=col, alpha=0.20, edgecolor=col, lw=0.7))
        ax.plot([stop], [y], marker="|", ms=7.5, color=col, mew=1.3)
        ax.text(1.20, y, label, fontsize=6.0, color=col, va="center",
                linespacing=1.2)
    ax.axvspan(1.0, 2.0 / math.sqrt(3.0), ymin=0.08, ymax=0.98,
               color="#f2cfcd", zorder=0, alpha=0.55)
    ax.annotate("", xy=(1.0, 2.46), xytext=(2.0 / math.sqrt(3.0), 2.46),
                arrowprops=dict(arrowstyle="<->", lw=0.7, color="#8b3a36"))
    ax.text(1.077, 2.56, "blind spot", fontsize=6.1, color="#8b3a36", ha="center")
    ax.axvline(1.0, color="#5a5a5a", lw=0.7, ls=":")
    ax.text(0.80, -0.60, "a record stops here", fontsize=5.9, color="#5a5a5a",
            ha="center", va="center")
    ax.set_xlim(x0, 1.62)
    ax.set_ylim(-0.80, 2.78)
    ax.set_yticks([])
    ax.set_xlabel("minimum enclosing radius / allocation")
    ax.spines[["left", "right", "top"]].set_visible(False)
    tag(ax, "(c) where they meet")

    fig.tight_layout(pad=0.35, w_pad=0.8)
    fig.savefig(FIG / "ress_fig1.png", dpi=400, bbox_inches="tight")
    plt.close(fig)


def fig_r2() -> None:
    cf = load("conforming.csv")
    gp = load("gate_profile.csv")
    ec = load("economics.csv")

    fig, axs = plt.subplots(1, 3, figsize=(7.3, 2.4),
                            gridspec_kw={"width_ratios": [1.08, 1.0, 1.0]})

    # (a) what the record can occupy -----------------------------------------
    ax = axs[0]
    for n, col, mk in ((3, TEAL, "o"), (5, EXACT, "s"), (10, PAIR, "^")):
        rows = sorted([r for r in cf if r["n"] == n], key=lambda r: r["A_over_sigma"])
        ax.plot([r["A_over_sigma"] for r in rows],
                [max(r["analytic_share"], 1e-11) for r in rows],
                "-", color=col, lw=1.15, marker=mk, ms=2.4, label=f"n={n}")
    ax.set_yscale("log")
    ax.set_ylim(1e-11, 3.0)
    ax.set_xlim(1.14, 3.1)
    ax.set_xlabel("tightest allocation / $\\sigma$")
    ax.set_ylabel("share of the 3$\\sigma$ box")
    ax.legend(fontsize=6.0, loc="upper left", frameon=True, facecolor="white",
              edgecolor="none", framealpha=0.9, handlelength=1.4,
              borderaxespad=0.25, labelspacing=0.22)
    ax.text(2.06, 1.5e-11, "the only population a\nbuild record can hold",
            fontsize=5.9, color=GREY, va="bottom", ha="right", linespacing=1.2)
    tag(ax, "(a) the record's territory")

    # (b) unjustified waivers -------------------------------------------------
    ax = axs[1]
    for n, col, mk in ((3, TEAL, "o"), (5, EXACT, "s"), (9, PAIR, "^")):
        rows = sorted([r for r in gp if r["n"] == n], key=lambda r: r["A_over_sigma"])
        ax.plot([r["A_over_sigma"] for r in rows],
                [100 * r["waiver_unalignable"] for r in rows],
                "-", color=col, lw=1.15, marker=mk, ms=2.4, label=f"n={n}")
    ax.set_xlim(0.92, 3.1)
    ax.set_ylim(-0.9, 17.5)
    ax.set_xlabel("tightest allocation / $\\sigma$")
    ax.set_ylabel("% of cleared waivers\nthat cannot be aligned", fontsize=7.9)
    ax.legend(fontsize=6.0, loc="upper right", frameon=False, handlelength=1.4,
              borderaxespad=0.25, labelspacing=0.22)
    tag(ax, "(b) cleared by the table")

    # (c) units needed to learn ----------------------------------------------
    ax = axs[2]
    rows = [r for r in ec if "units" in r]
    p = np.array([r["miss_rate"] for r in rows])
    N = np.array([r["units"] for r in rows])
    grid = np.logspace(-3.2, -1.25, 120)
    ax.plot(grid * 100, np.log(0.2) / np.log(1 - grid), "-", color=EXACT, lw=1.1)
    ax.plot(p * 100, N, "o", color=EXACT, ms=2.8)
    for pv, nv in zip(p, N):
        ax.annotate(f"{nv:.0f}", (pv * 100, nv), textcoords="offset points",
                    xytext=(3.2, 2.4), fontsize=5.9, color=EXACT)
    ax.axhspan(0.75, 3.0, color="#f7e3e2", zorder=0)
    ax.text(1.05, 1.42, "a programme flies\none to three units", fontsize=6.0,
            color="#8b3a36", va="center", ha="center", linespacing=1.2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.055, 5.5)
    ax.set_ylim(0.7, 4000)
    ax.set_xlabel("miss rate of the table, %")
    ax.set_ylabel("units to see one miss (80%)")
    tag(ax, "(c) units before it shows")

    fig.tight_layout(pad=0.35, w_pad=0.85)
    fig.savefig(FIG / "ress_fig2.png", dpi=400, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_r1()
    fig_r2()
    print("wrote", FIG / "ress_fig1.png", FIG / "ress_fig2.png")
