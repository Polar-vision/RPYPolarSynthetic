"""Four panels for the P3 replay (section 9.17).

(a) the ten allocations the document actually specifies
(b) one shim: worst-case rescue rate against as-built spread, pairwise vs exact
(c) the knife edge, drawn to scale -- why a 13.41% band is hard to land in
(d) the one clause whose convention is unstated, and what it costs
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis" / "figures"
S = json.loads((ROOT / "outputs_p3" / "summary.json").read_text(encoding="utf-8"))

EXACT = "#1f4e79"
PAIR = "#c0504d"
GREY = "#7f7f7f"
GOLD = "#bf9000"
TEAL = "#2e7d6f"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.edgecolor": "#444444",
    "axes.linewidth": 0.8,
    "figure.dpi": 200,
})


def panel_a(ax):
    rows = list(csv.DictReader(open(ROOT / "outputs_p3" / "lro_channels.csv",
                                    encoding="utf-8-sig")))
    rows.sort(key=lambda r: float(r["allocation_arcsec"]))
    y = np.arange(len(rows))
    vals = [float(r["allocation_arcsec"]) for r in rows]
    cols = [TEAL if r["on_deck"] == "yes" else GOLD for r in rows]
    ax.axvspan(300, 346, color=PAIR, alpha=0.13, lw=0)
    ax.barh(y, vals, color=cols, height=0.62, edgecolor="white", linewidth=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([r["channel"] for r in rows], fontsize=7.4)
    for yi, v in zip(y, vals):
        ax.text(v + 14, yi, f"{v:.0f}", va="center", fontsize=7.2, color="#333333")
    ax.set_xlim(0, 860)
    ax.set_xlabel("allocation to the spacecraft reference (arc-seconds, per axis)")
    ax.set_title("(a) the ten channels LRO actually specifies", loc="left")
    ax.grid(axis="x", color="#dddddd", lw=0.6)
    ax.set_axisbelow(True)
    ax.annotate("blind band\n300–346\"", xy=(323, 8.55), xytext=(395, 9.62),
                fontsize=7.0, color=PAIR, va="center",
                arrowprops=dict(arrowstyle="->", lw=0.8, color=PAIR))
    ax.text(770, 0.0, "on the HGA bracket,\nnot the instrument deck",
            fontsize=6.4, color=GOLD, ha="right", va="center")
    ax.set_ylim(-0.7, 10.6)


def panel_b(ax):
    rows = S["C2_rescue"]
    t = np.array([r["T_over_Amin"] for r in rows])
    p = np.array([r["rate_pairwise"] for r in rows]) * 100
    e = np.array([r["rate_exact"] for r in rows]) * 100
    m = np.array([r["rate_missed_by_pairwise"] for r in rows]) * 100
    ax.fill_between(t, e, p, color=PAIR, alpha=0.25, lw=0,
                    label="believed feasible, actually not")
    ax.plot(t, p, "-o", color=PAIR, lw=1.4, ms=3.2, markerfacecolor="white",
            label="pairwise: every pair within the sum")
    ax.plot(t, e, "-s", color=EXACT, lw=1.4, ms=3.0, markerfacecolor="white",
            label="exact: one shim serves every channel")
    k = int(np.argmax(m))
    ax.annotate(f"widest disagreement\n{m[k]:.1f}% of the box at $T/A={t[k]:.2f}$",
                xy=(t[k], 0.5 * (p[k] + e[k])), xytext=(1.62, 34),
                fontsize=7.0, color=PAIR,
                arrowprops=dict(arrowstyle="->", lw=0.8, color=PAIR))
    ax.axvline(1.0, color=GREY, lw=0.7, ls="--")
    ax.text(1.02, 88, "spread = allocation", fontsize=6.8, color=GREY,
            rotation=90, va="top")
    ax.set_xlabel("as-built spread $T$ / tightest allocation $A$")
    ax.set_ylabel("share of the design box a shim can serve (%)")
    ax.set_title("(b) one shim, nine channels, worst case", loc="left")
    ax.set_ylim(0, 104)
    ax.set_xlim(0.55, 2.55)
    ax.grid(color="#e8e8e8", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="lower left", fontsize=6.8, frameon=False)


def panel_c(ax):
    A, T = 1.0, 1.05
    centres = [np.array([T * np.cos(np.radians(90 + 120 * k)),
                         T * np.sin(np.radians(90 + 120 * k))]) for k in range(3)]
    for c in centres:
        ax.add_patch(Circle(c, A, fill=False, lw=1.1, color=EXACT))
        ax.plot(*c, "o", ms=2.6, color=EXACT)
    # the uncovered spot: the small curved triangle around the origin
    pts = []
    for k in range(3):
        c1, c2 = centres[k], centres[(k + 1) % 3]
        d = c2 - c1
        r = np.linalg.norm(d)
        a = (A * A - A * A + r * r) / (2 * r)
        h = np.sqrt(A * A - a * a)
        u = d / r
        p = c1 + a * u
        perp = np.array([-u[1], u[0]])
        cand = [p + h * perp, p - h * perp]
        pts.append(min(cand, key=lambda q: float(np.linalg.norm(q))))
    ax.add_patch(Polygon(pts, closed=True, color=PAIR, alpha=0.55, lw=0.8,
                         edgecolor=PAIR))
    ax.plot(0, 0, "+", ms=6, color="white", mew=1.2)
    ax.set_xlim(-0.82, 0.82)
    ax.set_ylim(-0.95, 0.82)
    ax.set_aspect("equal")
    ax.spines[["left", "bottom", "right", "top"]].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("(c) the knife edge, to scale", loc="left")
    ax.annotate("the hole: no single\norientation serves all three",
                xy=(0.0, 0.30), xytext=(0.30, 0.60), fontsize=6.8, color=PAIR,
                arrowprops=dict(arrowstyle="->", lw=0.7, color=PAIR))
    ax.text(0, -0.93, "each arc is one channel's boundary of radius $A$;\n"
                      "its centre sits $1.05A$ away, outside the frame",
            ha="center", fontsize=6.8, color="#333333")


def panel_d(ax):
    c = S["C1_containment"]
    req = c["requirement_arcsec"]
    alloc = c["allocation_arcsec"]
    half = c["half_fov_arcsec"]
    ax.barh([1], [req], color=EXACT, height=0.40, label="requirement 1.4$^\\circ$")
    ax.barh([1], [alloc], left=[req], color=PAIR, height=0.40,
            label="co-alignment allocation, Table 8-3")
    ax.barh([0], [half], color=GREY, height=0.40, label="NAC half field of view")
    ax.plot([half, half], [-0.45, 1.55], color="#333333", lw=0.9, ls="--")
    ax.annotate("", xy=(half, 1.30), xytext=(req + alloc, 1.30),
                arrowprops=dict(arrowstyle="<->", lw=0.9, color=PAIR))
    ax.text((req + alloc + half) / 2, 1.36,
            f"overrun {c['overrun_if_built_arcsec']:.0f}\"", ha="center",
            fontsize=7.2, color=PAIR)
    ax.text(req / 2, 1, "5040\"", ha="center", va="center", fontsize=7.0, color="white")
    ax.text(half / 2, 0, f"{half:.0f}\"", ha="center", va="center", fontsize=7.0,
            color="white")
    ax.set_yticks([1, 0])
    ax.set_yticklabels(["as-built\nreading", "geometry"], fontsize=7.4)
    ax.set_xlim(0, 7200)
    ax.set_ylim(-0.55, 1.62)
    ax.set_xlabel("arc-seconds from the NAC boresight")
    ax.set_title("(d) one clause, two readings", loc="left")
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              bbox_to_anchor=(1.02, -0.02))
    ax.grid(axis="x", color="#e8e8e8", lw=0.6)
    ax.set_axisbelow(True)


def main():
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 6.9))
    panel_a(axes[0][0])
    panel_b(axes[0][1])
    panel_c(axes[1][0])
    panel_d(axes[1][1])
    fig.tight_layout(pad=1.5)
    path = OUT / "p3_replay.png"
    fig.savefig(path, dpi=400, bbox_inches="tight")
    print("wrote", path)


if __name__ == "__main__":
    main()
