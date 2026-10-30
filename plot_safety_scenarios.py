"""Figure for section 9.14: three-scenario validation summary."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("outputs_safety")
FIG = Path("analysis/figures/safety_scenarios.png")


def load(name):
    with open(OUT / name) as f:
        return list(csv.DictReader(f))


def main():
    lens = load("safety_a_lens.csv")
    plans = load("safety_b_plans.csv")
    shell = load("safety_c_shell.csv")

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0))

    # ---- (a) blob miss rate vs width -------------------------------------
    ax = axes[0, 0]
    widths = [0.5, 0.2, 0.1, 0.05, 0.02]
    for step, color in (("0.5", "#d62728"), ("0.25", "#ff7f0e"), ("0.1", "#1f77b4")):
        rate = []
        for w in widths:
            sel = [r for r in lens if r["shape"] == "blob"
                   and r["width_deg"] == str(w) and r["truth"] == "YES"]
            rate.append(sum(1 for r in sel if int(r[f"grid{step}_yes"]) == 0)
                        / max(len(sel), 1))
        ax.plot(widths, rate, "o-", color=color, label=f"grid {step} deg")
    br = [0.0] * len(widths)
    ax.plot(widths, br, "s--", color="#2ca02c", label="branch (eps 0.01)")
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("feasible-pocket width (deg)")
    ax.set_ylabel("fraction wrongly judged infeasible")
    ax.set_title("(a) small feasible pockets: grids fail by area, branch does not")
    ax.set_ylim(-0.08, 1.12)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="center right")
    ax.annotate("thin lenses 0.02-0.5 deg:\n0 misses for every method\n(area, not width, decides)",
                xy=(0.04, 0.42), xycoords="axes fraction", fontsize=8, ha="left",
                color="#555555")

    # ---- (b) inspection-plan pruning --------------------------------------
    ax = axes[0, 1]
    tp = [p for p in plans if p["truth_feasible"] == "1"]
    g_lost = sum(1 for p in tp if p["grid_feasible"] == "0")
    b_lost = sum(1 for p in tp if p["branch_feasible"] == "0")
    tg = 1e3 * np.array([float(p["grid_seconds"]) for p in plans])
    tb = 1e3 * np.array([float(p["branch_seconds"]) for p in plans])
    x = np.arange(2)
    w = 0.35
    ax.bar(x - w / 2, [g_lost, np.median(tg)], w, color="#d62728",
           label="grid 0.5 deg")
    ax.bar(x + w / 2, [b_lost, np.median(tb)], w, color="#2ca02c",
           label="branch eps 0.05")
    ax.set_xticks(x)
    ax.set_xticklabels(["valid plans wrongly pruned\n(of 30)",
                        "median seconds per plan"])
    ax.set_yscale("symlog", linthresh=1)
    ax.set_title("(b) plan pruning: grid lost 1/30, branch 0/30")
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=8)
    for xi, v in zip(x - w / 2, [g_lost, np.median(tg)]):
        ax.annotate(f"{v:.3g}", (xi, v), ha="center", va="bottom", fontsize=9)
    for xi, v in zip(x + w / 2, [b_lost, np.median(tb)]):
        ax.annotate(f"{v:.3g}", (xi, v), ha="center", va="bottom", fontsize=9)

    # ---- (c) safety shell funnel ------------------------------------------
    ax = axes[1, 0]
    n = len(shell)
    acc = sum(1 for r in shell if r["accepted"] == "1")
    rej = [r for r in shell if r["accepted"] == "0"]
    rep = [r for r in rej if r.get("repair_truth") == "YES"]
    irr = [r for r in rej if r.get("repair_truth") == "NO"]
    g5_miss = sum(1 for r in rep if r["repair_grid0.5_yes"] == "0")
    labels = ["proposals\n300", "accepted by exact\npoint check",
              "rejected", "repair exists\n(truth)", "no repair\n(truth)"]
    vals = [n, acc, len(rej), len(rep), len(irr)]
    y = np.arange(len(labels))[::-1]
    ax.barh(y, vals, color=["#7f7f7f", "#2ca02c", "#d62728", "#1f77b4", "#9467bd"])
    for yi, v in zip(y, vals):
        ax.annotate(str(v), (v, yi), va="center", xytext=(4, 0),
                    textcoords="offset points", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title("(c) safety shell: where the geometric layer adds something")
    ax.set_xlim(0, 330)
    ax.grid(alpha=0.3, axis="x")
    ax.annotate("exact point check is identical for\ngrid and branch (24 us) -> no edge",
                xy=(0.98, 0.80), xycoords="axes fraction", fontsize=7.5,
                ha="right", va="top", color="#2ca02c")
    ax.annotate(f"grid 0.5 deg missed {g5_miss}/{len(rep)} repairs;\nbranch missed 0/{len(rep)}",
                xy=(0.98, 0.24), xycoords="axes fraction", fontsize=7.5,
                ha="right", color="#1f77b4")
    ax.annotate(f"branch proved all {len(irr)}\n(median 1 node)",
                xy=(0.98, 0.08), xycoords="axes fraction", fontsize=7.5,
                ha="right", color="#9467bd")

    # ---- (d) latency ladder ------------------------------------------------
    ax = axes[1, 1]
    pt = np.array([float(r["point_check_us"]) for r in shell])  # already us
    rep_us = np.array([float(r["repair_branch_us"]) for r in rej])
    proofs = [r for r in lens if r["truth"] == "NO"
              and r["branch_verdict"] == "NO_PROVEN"]
    pf_ms = 1e3 * np.array([float(r["branch_s"]) for r in proofs])
    items = [
        ("point check\n(any method)", np.median(pt), np.percentile(pt, 95), "us"),
        ("repair verdict\n(branch)", np.median(rep_us), np.percentile(rep_us, 95), "us"),
        ("infeasibility proof\n(branch, A scenes)", np.median(pf_ms * 1e3), np.percentile(pf_ms * 1e3, 95), "us"),
        ("plan prune\n(branch, 6 waypoints)", np.median(tb) * 1e3, tb.max() * 1e3, "us"),
    ]
    y = np.arange(len(items))[::-1]
    med = np.array([i[1] for i in items])
    hi = np.array([i[2] for i in items])
    ax.barh(y, med, color="#1f77b4")
    ax.errorbar(med, y, xerr=[np.zeros_like(med), hi - med], fmt="none",
                ecolor="#d62728", capsize=4)
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels([i[0] for i in items], fontsize=8)
    ax.set_xlabel("microseconds (log scale; whisker = p95 or max)")
    ax.set_title("(d) latency: planning loops OK, kHz control no")
    ax.grid(alpha=0.3, axis="x")
    ax.axvline(1e4, color="#555555", ls=":", lw=1)
    ax.annotate("10 ms", (1e4, 3.42), fontsize=7.5, ha="center", color="#555555")

    fig.tight_layout()
    FIG.parent.mkdir(exist_ok=True)
    fig.savefig(FIG, dpi=160)
    print(f"wrote {FIG}")


if __name__ == "__main__":
    main()
