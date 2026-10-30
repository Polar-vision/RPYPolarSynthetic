"""Figure for the five further candidate scenarios (S1-S5).

Every panel is fed from ``outputs_next/*.csv``; nothing is hard-coded, so the
figure cannot drift away from the tables after a rerun.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("outputs_next")
FIG = Path("analysis/figures/next_scenarios.png")

GRID = {"0.5": "#d62728", "0.25": "#ff7f0e", "0.1": "#1f77b4", "0.2": "#8c564b",
        "1.0": "#9467bd", "2.0": "#7f7f7f"}
BRANCH = "#2ca02c"
UNDEC = "#6baed6"


def load(name):
    with open(OUT / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    s1 = load("next_s1_spacecraft.csv")
    s1c = load("next_s1c_spacecraft_infeasible.csv")
    s1b = load("next_s1b_spacecraft_grazing.csv")
    s2 = load("next_s2_radiotherapy.csv")
    s3 = load("next_s3_tolerance.csv")
    s4 = load("next_s4_window_sample.csv")
    s5 = load("next_s5_arm.csv")

    fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.4))

    # ---- (a) what a proof costs as constraints pile up ---------------------
    ax = axes[0, 0]
    for rows, colour, label in ((s1, BRANCH, "feasible (YES)"),
                                (s1c, "#9467bd", "infeasible, proved (NO)")):
        ax.scatter([int(r["m_constraints"]) for r in rows],
                   [float(r["branch_s"]) * 1e3 for r in rows],
                   s=26, color=colour, label=label, zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("live constraints in the suite")
    ax.set_ylabel("branch time (ms)")
    heavy = max(s1, key=lambda r: int(r["m_constraints"]))
    ax.set_ylim(0.35, 60)
    ax.set_title(f"(a) spacecraft suite: 8-{heavy['m_constraints']} constraints, "
                 f"{float(heavy['branch_s'])*1e3:.0f} ms", fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3, which="both")

    # ---- (b) grazing sun: grid misses the thin crescent -------------------
    ax = axes[0, 1]
    w = [float(r["w_deg"]) for r in s1b]
    for step in ("0.5", "0.25", "0.1"):
        ax.plot(w, [int(r[f"grid{step}_fn"]) for r in s1b], "o-",
                color=GRID[step], label=f"grid {step} deg: wrong NO")
    ax.plot(w, [int(r["branch_undecided"]) for r in s1b], "s--",
            color=UNDEC, label="branch: undecided (residue given)")
    ax.plot(w, [int(r["branch_wrong"]) for r in s1b], "^-",
            color=BRANCH, label="branch: wrong claim")
    ax.axvline(2.0, color="k", lw=0.8, ls=":")
    ax.text(1.80, 2.25, "box swallowed", fontsize=8, ha="right", va="top")
    ax.set_xlabel("surviving crescent width w (deg), pointing box 1 deg")
    ax.set_ylabel("instances answered incorrectly")
    ax.set_ylim(-0.15, 2.4)
    ax.set_title("(b) grazing sun: the last 0.05 deg of crescent", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper left")
    ax.grid(alpha=0.3)

    # ---- (c) radiotherapy: verdict map over the crescent family -----------
    ax = axes[0, 2]
    gaps = [float(r["gap_deg"]) for r in s2]
    ax.step(gaps, [1 if r["truth"] == "NO" else 0 for r in s2], where="mid",
            color="k", lw=1.8, label="truth (closed form)")
    for step in ("1.0", "0.5"):
        ax.step(gaps, [1 - int(r[f"grid{step}_yes"]) for r in s2], where="mid",
                color=GRID[step], lw=1.2, label=f"grid {step} deg: infeasible")
    ax.step(gaps, [1 if r["branch_claim"] == "NO" else 0 for r in s2],
            where="mid", color=BRANCH, lw=1.4, ls="--",
            label="branch: proved infeasible")
    und = [g for g, r in zip(gaps, s2) if r["branch_claim"] == "UNDECIDED"]
    ax.plot(und, [0.5] * len(und), "o", ms=7, mfc="none", mec=UNDEC,
            label="branch: undecided")
    ax.axvline(16.0, color="k", lw=0.8, ls=":")
    ax.set_xlabel("organ-at-risk gap (deg); truth flips at 2*tol = 16")
    ax.set_ylabel("verdict = infeasible")
    ax.set_title("(c) radiotherapy: both flip late, only one proves", fontsize=10)
    ax.legend(fontsize=7.5, loc="center left")
    ax.grid(alpha=0.3)

    # ---- (d) alignment tolerance: the 13.4% window ------------------------
    ax = axes[1, 0]
    tau = [float(r["tau"]) for r in s3]
    ax.plot(tau, [int(r["pairwise_ok"]) for r in s3], "o-", color="#9467bd",
            label="pairwise check (industry)")
    ax.plot(tau, [1 - int(r["grid0.5_yes"]) for r in s3], "s-", color=GRID["0.5"],
            label="grid 0.5 deg: says infeasible")
    ax.plot(tau, [1 if r["branch_claim"] == "NO" else 0 for r in s3], "^--",
            color=BRANCH, label="branch: proves infeasible")
    ax.axvspan(np.sqrt(3) / 2, 1.0, color="#9467bd", alpha=0.10)
    ax.axvline(np.sqrt(3) / 2, color="#9467bd", lw=0.8, ls=":")
    ax.axvline(1.0, color="k", lw=0.8, ls=":")
    ax.text(np.sqrt(3) / 2 - 0.004, 0.06, "0.866", rotation=90, fontsize=8,
            ha="right", color="#9467bd")
    ax.text(1.004, 0.06, "1.000", rotation=90, fontsize=8, color="k")
    ax.set_xlabel("normalised tolerance tau = theta / r")
    ax.set_ylabel("says feasible / says infeasible")
    ax.set_title("(d) alignment tolerance: the 13.4% window", fontsize=10)
    ax.legend(fontsize=7.5, loc="center left")
    ax.grid(alpha=0.3)

    # ---- (e) pass window: sampling misses near-tangent violations ---------
    ax = axes[1, 1]
    steps = ["5.0", "2.0", "1.0", "0.5"]
    miss = [sum(int(r["wrong"]) for r in s4 if r["step_deg"] == s) for s in steps]
    tot = [sum(1 for r in s4 if r["step_deg"] == s) for s in steps]
    bars = ax.bar(steps, miss, color="#d62728", width=0.55)
    for b, m, t in zip(bars, miss, tot):
        ax.text(b.get_x() + b.get_width() / 2, m + 0.06, f"{m}/{t}",
                ha="center", fontsize=9)
    ax.set_ylim(0, max(miss) * 1.6 + 0.5)
    ax.set_xlabel("time step (deg of solar arc)")
    ax.set_ylabel("near-tangent passes called clean")
    ax.set_title("(e) pass window: 5 deg misses what 2 deg sees", fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    # ---- (f) arm: cost of proving a patch empty --------------------------
    ax = axes[1, 2]
    for x, kind, colour in ((0, "normal", BRANCH), (1, "blocked", "#9467bd")):
        nodes = [int(r["branch_nodes"]) for r in s5 if r["kind"] == kind]
        ax.scatter([x] * len(nodes), nodes, s=24, color=colour, alpha=0.85,
                   zorder=3)
        ax.text(x, 1.55e5, f"n={len(nodes)}", ha="center", fontsize=8)
        ax.text(x + 0.14, float(np.median(nodes)),
                f"median {int(np.median(nodes))}", ha="left", va="center",
                fontsize=8, color=colour)
    ax.set_yscale("log")
    ax.set_ylim(60, 3.2e5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["random joint holes\n(feasible)", "covered patch\n(proved empty)"])
    ax.set_xlim(-0.55, 1.75)
    ax.set_ylabel("branch nodes to finish")
    ax.set_title("(f) arm: the empty patch is the cheap case", fontsize=10)
    ax.grid(axis="y", alpha=0.3, which="both")

    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=170)
    print("wrote", FIG)


if __name__ == "__main__":
    main()
