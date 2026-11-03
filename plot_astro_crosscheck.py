"""Figure for section 9.12: what the astroplan cross-check found.

(a) how far the shipped ephemeris and coordinate path are from astropy,
(b) does the area bracket contain an independently computed area,
(c) where the boolean disagreements sit relative to the decision boundary.

Usage:  python plot_astro_crosscheck.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("outputs_astro_crosscheck")
FIG = Path("analysis/figures/astro_crosscheck.png")

INK = "#1f2937"
MUTED = "#6b7280"
BLUE = "#1d4ed8"
RED = "#b91c1c"
GREEN = "#047857"
AMBER = "#b45309"


def read(name: str) -> list[dict]:
    with (OUT / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def panel_ephemeris(ax) -> None:
    rows = read("ac_ephemeris.csv")
    series = [
        ("sun direction", "err_sun_arcmin", BLUE),
        ("moon direction", "err_moon_arcmin", RED),
        ("target altitude", "err_alt_arcmin", AMBER),
    ]
    bins = np.logspace(np.log10(0.05), np.log10(400), 48)
    for k, (label, key, colour) in enumerate(series):
        v = np.array([float(r[key]) for r in rows])
        ax.hist(
            np.clip(v, bins[0], bins[-1]),
            bins=bins,
            histtype="step",
            lw=1.4,
            color=colour,
            label=f"{label} (median {np.median(v):.2g}')",
        )
    ax.set_xscale("log")
    ax.set_xlabel("offset from astropy (arcmin, log)", fontsize=8)
    ax.set_ylabel("samples", fontsize=8)
    ax.set_title("(a) where the shipped path differs", fontsize=9, color=INK, loc="left")
    ax.legend(fontsize=6.8, frameon=False, loc="upper right", handlelength=1.5)
    ax.tick_params(labelsize=7.5)
    ax.grid(alpha=0.25, lw=0.6)


def panel_area(ax) -> None:
    rows = read("ac_area.csv")
    labels, y = [], 0
    ticks, ticklabels = [], []
    for i in range(0, len(rows), 2):
        m, a = rows[i], rows[i + 1]
        base = float(m["area_lo_sr"])
        for r, colour, tag in ((m, BLUE, "Meeus"), (a, RED, "astropy")):
            lo = (float(r["area_lo_sr"]) - base) * 1000.0
            hi = (float(r["area_hi_sr"]) - base) * 1000.0
            ax.plot([lo, hi], [y, y], color=colour, lw=5, alpha=0.35, solid_capstyle="butt")
            ax.plot([lo, hi], [y, y], color=colour, lw=0.9)
            ax.plot((lo + hi) / 2, y, "|", color=colour, ms=7)
            y += 1
        ax.plot(
            (float(m["grid_area_sr"]) - base) * 1000.0,
            y - 1.5,
            "o",
            ms=4.5,
            mfc="white",
            mec=GREEN,
            mew=1.3,
            zorder=5,
        )
        ticks.append(y - 1.5)
        ticklabels.append(f"{m['site']}  {float(m['area_lo_sr']):.3f} sr")
        y += 0.6

    ax.axvline(0, color=MUTED, lw=0.7)
    ax.set_yticks(ticks)
    ax.set_yticklabels(ticklabels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("area minus scene lower bound ($10^{-3}$ sr)", fontsize=8)
    ax.set_title("(b) bracket contains an independent grid value", fontsize=9, color=INK, loc="left")
    ax.tick_params(axis="x", labelsize=7.5)
    ax.grid(alpha=0.25, lw=0.6, axis="x")
    from matplotlib.lines import Line2D

    ax.legend(
        handles=[
            Line2D([0], [0], color=BLUE, lw=3, alpha=0.5, label="Meeus"),
            Line2D([0], [0], color=RED, lw=3, alpha=0.5, label="astropy"),
            Line2D([0], [0], color=GREEN, marker="o", ls="none", mfc="white", mew=1.3, label="grid mask"),
        ],
        fontsize=6.8,
        frameon=True,
        framealpha=0.92,
        edgecolor="none",
        loc="upper left",
    )


def panel_verdicts(ax) -> None:
    rows = read("ac_margins_fast.csv")
    margin = np.abs(np.array([float(r["margin_deg"]) for r in rows]))
    dis = np.array([int(r["disagree"]) for r in rows])

    edges = np.array([0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 4.0, 8.0, 30.0])
    frac, mid, n = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (margin >= lo) & (margin < hi)
        n.append(int(sel.sum()))
        frac.append(float(dis[sel].mean()) if sel.any() else np.nan)
        mid.append(np.sqrt(max(lo, 1e-3) * hi))
    frac = np.array(frac)
    mid = np.array(mid)

    ax.step(mid, 100 * frac, where="mid", color=INK, lw=1.4)
    ax.plot(mid, 100 * frac, "o", ms=3.5, color=INK)
    ax.axvline(1.1, color=RED, lw=1.0, ls="--")
    ax.text(0.92, 36, "moon error\nmedian 1.1 deg", fontsize=7, color=RED, va="top", ha="right")
    ax.axvline(2.36, color=RED, lw=1.0, ls=":")
    ax.text(2.7, 16, "p95\n2.4 deg", fontsize=7, color=RED, va="top")
    ax.set_xscale("log")
    ax.set_xlim(0.03, 30)
    ax.set_ylim(-3, 60)
    ax.set_xlabel("|margin| to boundary (deg, log)", fontsize=8.4)
    ax.set_ylabel("disagreement rate (%)", fontsize=8.4)
    ax.set_title("(c) disagreements cluster at the edge", fontsize=8.8, color=INK, loc="left")
    ax.tick_params(labelsize=7.5)
    ax.grid(alpha=0.25, lw=0.6)
    ax.text(
        0.035,
        3.0,
        f"{len(rows)} verdicts\n{int(dis.sum())} disagree ({100 * dis.mean():.2f}%)",
        fontsize=7,
        color=MUTED,
    )


def main() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.35))
    panel_ephemeris(axes[0])
    panel_area(axes[1])
    panel_verdicts(axes[2])
    fig.tight_layout(pad=0.6, w_pad=1.6)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=260)
    print("wrote", FIG, FIG.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
