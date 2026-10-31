"""Four panels for the replication study (section 9.16).

(a) the pairwise window against tolerance imbalance -- where the defect lives
(b) how optimistic the table is, by channel count
(c) setups promised by single linkage vs setups actually needed
(d) the three-sensor bracket, drawn to scale in the tangent plane
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis" / "figures"
S = json.loads((ROOT / "outputs_replication" / "summary.json").read_text(encoding="utf-8"))

EXACT = "#1f4e79"
PAIR = "#c0504d"
PHANTOM = "#7030a0"
GREY = "#7f7f7f"

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
    rows = S["R1"]["rows"]
    k = np.array([r["kappa"] for r in rows])
    w = np.array([r["window_frac"] for r in rows]) * 100
    ax.semilogx(k, w, "-o", ms=3.5, lw=1.4, color=PAIR,
                markerfacecolor="white", markeredgewidth=1.0)
    ax.axhline(0, color=GREY, lw=0.7)
    ax.axvline(1.0, color=GREY, lw=0.7, ls=":")
    peak = S["R1"]["peak_window_frac"] * 100
    ax.annotate(f"balanced design\n{peak:.1f}% optimistic",
                xy=(1.0, peak), xytext=(0.16, peak * 0.72),
                fontsize=8, color="#333333",
                arrowprops=dict(arrowstyle="->", lw=0.8, color="#333333"))
    ax.text(2.2, 2.0, "one channel given\n2x the tolerance:\nwindow closes",
            fontsize=7.5, color="#333333", ha="left", va="bottom")
    ax.set_xlabel(r"tolerance ratio $\kappa$ of the third channel")
    ax.set_ylabel("pairwise window (% of required tolerance)")
    ax.set_title("(a) the defect peaks when the design is balanced", loc="left")
    ax.set_ylim(-2, 16.5)
    ax.grid(alpha=0.25)


def panel_b(ax):
    rows = S["R2"]["by_n"]
    n = [r["n"] for r in rows]
    med = [r["rho_median"] for r in rows]
    p90 = [r["rho_p90"] for r in rows]
    mx = [r["rho_max"] for r in rows]
    ax.fill_between(n, med, p90, color=PAIR, alpha=0.18, lw=0,
                    label="median to 90th pct")
    ax.plot(n, med, "-o", ms=3.5, lw=1.3, color=EXACT, label="median")
    ax.plot(n, p90, "--", lw=1.0, color=PAIR, label="90th pct")
    ax.scatter(n, mx, s=14, color=PHANTOM, zorder=3, label="worst in sample")
    ax.axhline(1.0, color=GREY, lw=0.8)
    ax.set_xlabel("channels in the suite")
    ax.set_ylabel(r"optimism factor $\rho$")
    ax.set_title("(b) optimism is common but usually small", loc="left")
    ax.legend(fontsize=7, loc="upper right", frameon=False)
    ax.grid(alpha=0.25)
    ax.set_ylim(0.994, 1.14)


def panel_c(ax):
    rows = S["R3"]["sweep"]
    r = np.array([x["ratio"] for x in rows])
    plan = np.array([x["plan_setups"] for x in rows])
    true = np.array([x["true_setups"] for x in rows])
    ax.step(r, plan, where="mid", lw=1.8, color=PAIR, label="setups the plan promises")
    ax.step(r, true, where="mid", lw=1.8, color=EXACT, label="setups the machine needs")
    ax.fill_between(r, plan, true, step="mid", color=PHANTOM, alpha=0.18, lw=0)
    band = S["R3"]["phantom_window_ratio"]
    ax.axvspan(band[0], band[1], color=PHANTOM, alpha=0.07, lw=0)
    ax.text((band[0] + band[1]) / 2, 1.42, "phantom\nwindow",
            ha="center", fontsize=7.5, color=PHANTOM, linespacing=1.3)
    ax.set_xlabel("pocket radius / reach angle")
    ax.set_ylabel("setups")
    ax.set_title("(c) single linkage under-counts setups", loc="left")
    ax.set_yticks([1, 2, 3])
    ax.set_ylim(0.7, 3.5)
    ax.legend(fontsize=7, loc="upper left", frameon=False)
    ax.grid(alpha=0.25)


def panel_d(ax):
    tol = 0.45
    centre = np.array([[0.0, 0.5], [0.433, -0.25], [-0.433, -0.25]])
    names = ["camera", "lidar", "radar"]
    for (x, y), nm in zip(centre, names):
        ax.add_patch(Circle((x, y), tol, fill=True, facecolor=EXACT,
                            alpha=0.10, edgecolor=EXACT, lw=1.2))
        ax.plot([0, x * 1.55], [0, y * 1.55], color=GREY, lw=0.6, ls=":")
        ax.text(x * 1.75, y * 1.75, nm, fontsize=7.5, ha="center",
                color="#333333")
    ax.plot(0, 0, "o", ms=4, color=PHANTOM, zorder=5)
    ax.annotate("circumcentre: 0.500$^\\circ$\nfrom each nominal,\n0.45$^\\circ$ allowed",
                xy=(0, 0), xytext=(-0.34, -0.95), fontsize=7.2,
                color=PHANTOM, ha="left",
                arrowprops=dict(arrowstyle="->", lw=0.8, color=PHANTOM))
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.25, 1.2)
    ax.set_xlabel("tangent-plane offset (deg)")
    ax.set_ylabel("tangent-plane offset (deg)")
    ax.set_title("(d) three-sensor bracket, drawn to scale", loc="left")
    ax.grid(alpha=0.2)


def main():
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 7.0))
    panel_a(axes[0, 0])
    panel_b(axes[0, 1])
    panel_c(axes[1, 0])
    panel_d(axes[1, 1])
    fig.tight_layout(pad=1.4)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "replication.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    print("saved", path)


if __name__ == "__main__":
    main()
