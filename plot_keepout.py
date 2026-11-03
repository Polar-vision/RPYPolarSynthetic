"""Figures for the keep-out cone section."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs_keepout"
FIGS = ROOT / "analysis" / "figures"

C_EXACT = "#1D9E75"
C_UNDET = "#B4B2A9"
C_FEAS = "#378ADD"
C_BAD = "#A32D2D"


def load(name: str) -> list[dict]:
    with (OUT / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    sweep = load("keepout_sweep.csv")
    inner = load("keepout_interior.csv")
    wit = load("keepout_witness.csv")

    fig = plt.figure(figsize=(9.8, 3.5))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 0.95, 0.9], wspace=0.30)

    # ---- (a) which path decides, as a function of the exclusion half-angle ----
    ax = fig.add_subplot(gs[0, 0])
    styles = {
        "feasible": (C_EXACT, "framework exact: feasible"),
        "infeasible": (C_EXACT, "framework exact: infeasible"),
        "undetermined": (C_UNDET, "framework refuses (non-convex)"),
    }
    for kind, (col, lab) in styles.items():
        pts = [r for r in sweep if r["capform"] == kind]
        if not pts:
            continue
        ax.scatter([float(r["delta_over_beta"]) for r in pts],
                   [float(r["beta_deg"]) for r in pts],
                   s=46, marker="s", facecolor=col, edgecolor="white", linewidth=0.6,
                   label=lab, zorder=3)
    ax.axhline(90.0, color=C_BAD, lw=1.0, ls="--", zorder=2,
               label=r"$\beta=90^\circ$: convexity limit")
    ax.set_xlabel(r"sun offset / cone half-angle  $\delta/\beta$", fontsize=9.5)
    ax.set_ylabel(r"cone half-angle $\beta$ (deg)", fontsize=9.5)
    ax.set_title("(a) framework covers wide cones only", fontsize=10.5, loc="left")
    ax.tick_params(labelsize=9)
    ax.legend(fontsize=7.6, loc="center left", frameon=True, framealpha=0.96,
              edgecolor="none", borderpad=0.5, handletextpad=0.4)
    ax.grid(alpha=0.18, lw=0.5)

    # ---- (b) who gets the decision right, per geometry ----
    ax = fig.add_subplot(gs[0, 1])
    convex = [r for r in sweep if r["convex_regime"] == "True" and r["capform"] != "undetermined"]
    boundary = [r for r in sweep if r["convex_regime"] == "False" and abs(float(r["grid_margin_deg"])) > 0.05]
    inner_h = [r for r in inner if abs(float(r["grid_margin_deg"])) > 0.05]
    groups = [
        (r"$\beta>90^\circ$", "framework", sum(r["capform"] == r["branch"] for r in convex), len(convex), C_EXACT),
        ("sun at edge", "candidates", sum(r["blind"] == ("feasible" if float(r["grid_margin_deg"]) <= 0 else "infeasible") for r in boundary), len(boundary), C_FEAS),
        ("sun inside", "candidates", sum(r["blind"] == r["truth"] for r in inner_h), len(inner_h), C_BAD),
        ("sun inside", "branching", sum(r["branch"] == r["truth"] for r in inner_h), len(inner_h), C_EXACT),
    ]
    ypos = np.arange(len(groups))[::-1]
    for y, (g, meth, ok, n, col) in zip(ypos, groups):
        ax.barh(y, 100.0, color="#EFEEE9", height=0.62, zorder=1)
        ax.barh(y, 100.0 * ok / max(n, 1), color=col, height=0.62, zorder=2)
        frac = ok / max(n, 1)
        ax.text(3.0, y, f"{g} · {meth}", va="center", ha="left", fontsize=8.4,
                color="white" if frac > 0.55 else "#2C2C2A", zorder=4)
        ax.text(104, y, f"{ok}/{n}", va="center", fontsize=9.0, color="#3C3C3A")
    ax.set_yticks([])
    ax.set_ylim(-0.75, len(groups) - 0.25)
    ax.set_xlim(0, 136)
    ax.set_xlabel("correct decisions (%)", fontsize=9.5)
    ax.set_title("(b) failure is geometry-specific", fontsize=10.5, loc="left")
    ax.tick_params(axis="x", labelsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # ---- (c) the certificate stops being minimal ----
    ax = fig.add_subplot(gs[0, 2])
    k = np.array([int(r["n_keepouts"]) for r in wit])
    w = np.array([int(r["witness_size"]) for r in wit])
    ax.plot(k, w, "-o", color=C_BAD, ms=5, lw=1.2, zorder=3, label="irreducible certificate size")
    ax.axhline(4, color="#5F5E5A", lw=1.0, ls="--", zorder=2)
    ax.text(2.05, 4.4, r"Helly bound (4)", fontsize=8.0, color="#5F5E5A")
    ax.fill_between([1.8, 8.4], 4, 10, color=C_BAD, alpha=0.06, zorder=1)
    ax.set_xlim(1.8, 8.4)
    ax.set_ylim(1.5, 10)
    ax.set_xlabel("number of keep-out cones in the ring", fontsize=9.5)
    ax.set_ylabel("witness size (constraints)", fontsize=9.5)
    ax.set_title("(c) witness has no fixed bound", fontsize=10.5, loc="left")
    ax.tick_params(labelsize=9)
    ax.grid(alpha=0.18, lw=0.5) if False else None
    ax.grid(alpha=0.18, lw=0.5)
    ax.legend(fontsize=8.2, loc="upper left", frameon=False)

    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    for dest in (OUT / "keepout_decision.png", FIGS / "keepout_decision.png"):
        fig.savefig(dest, dpi=190, bbox_inches="tight")
    plt.close(fig)
    print("wrote", FIGS / "keepout_decision.png")


if __name__ == "__main__":
    main()
