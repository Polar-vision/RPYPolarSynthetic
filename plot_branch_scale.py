"""Figure for the real-scale branch experiment (section 9.11)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs_branch_scale"
FIGS = ROOT / "analysis" / "figures"

C_RED = "#A32D2D"
C_GREEN = "#1D9E75"
C_GOLD = "#C08A2E"
C_BLUE = "#4A5A8C"
C_GREY = "#8C8A82"


def load(name: str) -> list[dict]:
    with (OUT / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fnum(rows: list[dict], key: str) -> np.ndarray:
    return np.array([float(r[key]) for r in rows])


def style(ax) -> None:
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(labelsize=8.4)
    ax.grid(alpha=0.22, lw=0.6)


def _kfmt(v, _p) -> str:
    return f"{v / 1000:g}k" if v < 1e6 else f"{v / 1e6:g}M"


def main() -> None:
    fig = plt.figure(figsize=(9.4, 5.6))
    gs = fig.add_gridspec(2, 3, left=0.065, right=0.985, bottom=0.095, top=0.915,
                          hspace=0.46, wspace=0.36)

    r0 = load("bs_resolution_0stars.csv")
    r2 = load("bs_resolution_200stars.csv")

    # ---- (a) the cost law is 1/eps, not 1/eps^2 ---------------------------
    ax = fig.add_subplot(gs[0, 0])
    e0, n0 = fnum(r0, "eps_deg"), fnum(r0, "nodes")
    e2, n2 = fnum(r2, "eps_deg"), fnum(r2, "nodes")
    ax.plot(1 / e0, n0, "o-", ms=3.4, lw=1.3, color=C_BLUE, label="m = 8")
    ax.plot(1 / e2, n2, "s-", ms=3.4, lw=1.3, color=C_RED, label="m = 208")
    ref_x = np.array([1.0, 50.0])
    ax.plot(ref_x, n0[0] * ref_x, ls=":", lw=1.0, color=C_GREY)
    ax.text(2.2, n0[0] * 2.2 * 3.0, r"slope $-1$", fontsize=7.2, color=C_GREY, rotation=34)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$1/\varepsilon$ (deg$^{-1}$)", fontsize=8.8)
    ax.set_ylabel("boxes", fontsize=8.8)
    ax.set_title(r"(a) cost is $O(1/\varepsilon)$", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.4, frameon=False, loc="upper left")
    style(ax)

    # ---- (b) point answer vs existence answer -----------------------------
    ax = fig.add_subplot(gs[0, 1])
    ax.plot(e2, n2, "s-", ms=3.4, lw=1.4, color=C_RED, label="existence (full partition)")
    ax.plot(e2, fnum(r2, "nodes_to_first_feasible"), "o-", ms=3.4, lw=1.4, color=C_GREEN,
            label="point answer (first cell)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$\varepsilon$ (deg)", fontsize=8.8)
    ax.set_ylabel("boxes", fontsize=8.8)
    ax.set_title("(b) two questions, two prices", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.0, frameon=False, loc="center left")
    style(ax)

    # ---- (c) count flat in m, time linear in m ----------------------------
    ax = fig.add_subplot(gs[0, 2])
    rc = load("bs_constraints.csv")
    m = fnum(rc, "m_total")
    ax.plot(m, fnum(rc, "nodes"), "o-", ms=3.4, lw=1.4, color=C_BLUE, label="boxes")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("constraints in the suite", fontsize=8.8)
    ax.set_ylabel("boxes", fontsize=8.8, color=C_BLUE)
    ax.tick_params(axis="y", labelcolor=C_BLUE, labelsize=8.4)
    ax2 = ax.twinx()
    ax2.plot(m, fnum(rc, "seconds"), "^-", ms=3.4, lw=1.3, color=C_GOLD)
    ax2.set_ylabel("wall time (s)", fontsize=8.8, color=C_GOLD)
    ax2.tick_params(axis="y", labelcolor=C_GOLD, labelsize=8.4)
    for sp in ("top",):
        ax2.spines[sp].set_visible(False)
    ax.set_title("(c) boxes flat, time linear", fontsize=9.6, loc="left")
    ax.text(8.5, 2.6e5, "51× more constraints\n→ 2.7× more boxes", fontsize=7.0,
            color=C_GREY)
    ax.set_ylim(3.6e4, 6e5)
    ax.yaxis.set_major_formatter(FuncFormatter(_kfmt))
    style(ax)

    # ---- (d) the enclosure decides the constant ---------------------------
    ax = fig.add_subplot(gs[1, 0])
    rb = load("bs_bounds.csv")
    names = [r["bound"] for r in rb]
    nodes = fnum(rb, "nodes")
    cert = 100 * fnum(rb, "certified_frac")
    res = 100 * fnum(rb, "resolution_frac")
    cols = {"lip": C_GREY, "ia": C_GOLD, "tri": C_GREEN}
    ypos = np.arange(len(names))[::-1]
    ax.barh(ypos, nodes, color=[cols[n] for n in names], height=0.56)
    for y, n_, c, r_, nm in zip(ypos, nodes, cert, res, names):
        ax.text(n_ * 1.22, y, f"{int(n_):,}", va="center", fontsize=7.2, color="#333")
        if nm == "tri":
            ax.text(n_ * 7.5, y, f"{c:.0f}% excl.\n{r_:.1f}% point", va="center",
                    ha="left", fontsize=6.4, color="#666")
        else:
            ax.text(2.4e4, y, f"{c:.0f}% excl.\n{r_:.1f}% point", va="center", ha="left",
                    fontsize=6.4, color="white")
    ax.set_xscale("log")
    ax.set_xlim(2e4, 8e6)
    ax.set_yticks(ypos)
    ax.set_yticklabels(["Lipschitz\n(9.6 as built)", "interval\narithmetic",
                        "triangle\ninequality"], fontsize=7.4)
    ax.set_xlabel("boxes  (m = 208, $\\varepsilon$ = 0.1°)", fontsize=8.4)
    ax.set_title("(d) the enclosure sets the constant", fontsize=9.6, loc="left")
    style(ax)

    # ---- (e) interface length, not constraint count ----------------------
    ax = fig.add_subplot(gs[1, 1])
    rs = load("bs_separated.csv")
    rm = load("bs_merged.csv")
    ax.plot(fnum(rs, "k"), fnum(rs, "nodes"), "o-", ms=3.4, lw=1.4, color=C_RED,
            label="separated (interface grows)")
    ax.plot(fnum(rm, "k"), fnum(rm, "nodes"), "s--", ms=3.4, lw=1.3, color=C_GREEN,
            label="merged (interface fixed)")
    ax.set_xscale("log")
    ax.set_xlabel("cones in the cap", fontsize=8.8)
    ax.set_ylabel("boxes", fontsize=8.8)
    ax.set_ylim(3.2e4, 9e4)
    ax.yaxis.set_major_formatter(FuncFormatter(_kfmt))
    ax.set_title("(e) boxes track the interface", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.0, frameon=False, loc="upper left")
    style(ax)

    # ---- (f) how much of the answer rests on a point check ---------------
    ax = fig.add_subplot(gs[1, 2])
    labels = ["feasible\n(certified)", "excluded\n(certified)", "resolved by\npoint check"]
    ypos = np.arange(3)[::-1]
    for j, (bd, col) in enumerate((("lip", C_GREY), ("tri", C_GREEN))):
        row = [r for r in rb if r["bound"] == bd][0]
        vals = [100 * float(row["feasible_frac"]), 100 * float(row["certified_frac"]),
                100 * float(row["resolution_frac"])]
        off = 0.18 if j else -0.18
        ax.barh(ypos + off, vals, height=0.32, color=col, alpha=0.92,
                label="Lipschitz (9.6)" if bd == "lip" else "triangle")
    for j, bd in enumerate(("lip", "tri")):
        row = [r for r in rb if r["bound"] == bd][0]
        vals = [100 * float(row["feasible_frac"]), 100 * float(row["certified_frac"]),
                100 * float(row["resolution_frac"])]
        off = 0.18 if j else -0.18
        for y, v in zip(ypos, vals):
            ax.text(v + 1.5, y + off, f"{v:.1f}", va="center", fontsize=6.8, color="#333")
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=7.4)
    ax.set_xlabel("% of the pointing cap", fontsize=8.8)
    ax.set_xlim(0, 96)
    ax.set_title("(f) what the certificate covers", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.0, frameon=False, loc="lower right", bbox_to_anchor=(1.0, -0.02))
    style(ax)

    FIGS.mkdir(parents=True, exist_ok=True)
    out = FIGS / "branch_scale.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
