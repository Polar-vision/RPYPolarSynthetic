"""Figures for the observability section."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import rpy_polar_synth.observability as ob  # noqa: E402

OUT = ROOT / "outputs_observability"
FIGS = ROOT / "analysis" / "figures"

C_GRID = "#A32D2D"
C_BRANCH = "#1D9E75"
C_SUN = "#C08A2E"
C_MOON = "#4A5A8C"
C_GREY = "#8C8A82"
DEG = np.pi / 180.0


def load(name: str) -> list[dict]:
    with (OUT / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    fig = plt.figure(figsize=(9.0, 3.3))
    gs = fig.add_gridspec(1, 2, left=0.075, right=0.985, bottom=0.175, top=0.885,
                          wspace=0.30)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])

    # ---- (a) accuracy against cost -------------------------------------
    rows = load("accuracy_vs_cost.csv")
    for method, col, lab, mk in (
        ("grid", C_GRID, "grid sampling", "s"),
        ("branch", C_BRANCH, "branching", "o"),
    ):
        pts = [r for r in rows if r["method"] == method]
        x = [float(r["seconds"]) for r in pts]
        y = [abs(float(r["rel_err_area"])) * 100.0 for r in pts]
        ax0.plot(x, y, marker=mk, ms=4.2, lw=1.4, color=col, label=lab, clip_on=False)
    ax0.set_xscale("log")
    ax0.set_yscale("log")
    ax0.set_xlabel("wall clock (s)", fontsize=9.5)
    ax0.set_ylabel("area error (%)", fontsize=9.5)
    ax0.set_title("(a) same accuracy, less time", fontsize=10.5, loc="left")
    ax0.grid(alpha=0.22, lw=0.6, which="both")
    ax0.legend(fontsize=8.4, frameon=False, loc="lower left")
    ax0.tick_params(labelsize=8.8)
    ax0.axhline(0.1, color=C_GREY, lw=0.8, ls=":", zorder=1)
    ax0.text(0.0021, 0.113, "0.1%", fontsize=7.2, color=C_GREY)

    # ---- (b) diurnal sweep ---------------------------------------------
    day = load("diurnal_sweep.csv")
    t = [float(r["utc_hour"]) for r in day]
    srem = [float(r["sun_removes_sr"]) for r in day]
    mrem = [float(r["moon_removes_sr"]) for r in day]
    alt = [float(r["sun_alt_deg"]) for r in day]
    night_idx = [i for i, a in enumerate(alt) if a < -18.0]
    if night_idx:
        ax1.axvspan(t[night_idx[0]], t[night_idx[-1]], color="#E3EBF5",
                    alpha=0.9, lw=0, zorder=0)
    ax1.plot(t, srem, lw=1.7, color=C_SUN, zorder=3)
    ax1.plot(t, mrem, lw=1.7, color=C_MOON, zorder=3)
    ax1.text(6.2, 0.905, "sun cone", fontsize=8.8, color=C_SUN)
    ax1.text(19.2, 0.905, "moon cone", fontsize=8.8, color=C_MOON)
    ax1.text(18.4, 0.20, "astronomical night", fontsize=8.2, color="#4A6A8C",
             ha="center", va="bottom")
    ax1.set_xlim(0, 24)
    ax1.set_ylim(0, 1.12)
    ax1.set_xlabel("UTC hour, 30 Oct 2026", fontsize=9.5)
    ax1.set_ylabel("sky area removed (sr)", fontsize=9.5)
    ax1.set_title("(b) the sun constraint dies at night", fontsize=10.5, loc="left")
    ax1.grid(alpha=0.22, lw=0.6)
    ax1.tick_params(labelsize=8.8)

    for ax in (ax0, ax1):
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    FIGS.mkdir(parents=True, exist_ok=True)
    for dest in (OUT / "observability_cost.png", FIGS / "observability_cost.png"):
        fig.savefig(dest, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote observability_cost.png")

    # ---- (c) sky map ----------------------------------------------------
    fig = plt.figure(figsize=(4.1, 4.1))
    ax2 = fig.add_axes([0.03, 0.03, 0.94, 0.86], projection="polar")
    site = ob.Site("FAST", 25.653, 106.856, 1100.0)
    jd = ob._julian_day(2026, 10, 30, 2.0)
    scene = ob.build_scene(site, jd, h_min_deg=5.0, sun_beta_deg=30.0, moon_beta_deg=30.0)
    res = ob.enumerate_region(scene, eps_deg=0.05)
    step = 0.5
    rs = np.arange(0.0, 90.0 + 1e-9, step) * DEG
    als = np.arange(0.0, 360.0 + 1e-9, step) * DEG
    R, A = np.meshgrid(rs, als, indexing="ij")
    mask = ob.boxes_to_mask(res, step)
    # close the azimuth seam so contourf does not leave a wedge
    mask = np.hstack([mask, mask[:, :1]])
    mask = np.vstack([mask, mask[-1:, :]])
    if R.shape != mask.shape:
        R, A = np.meshgrid(rs[: mask.shape[0]], als[: mask.shape[1]], indexing="ij")
    # polar sky map: zenith at centre, azimuth around
    ax2.set_theta_zero_location("N")
    ax2.set_theta_direction(-1)
    ax2.contourf(A, R, mask.astype(float), levels=[0.5, 1.5],
                 colors=["#7FB89A"], alpha=0.88, zorder=1, antialiased=True)
    ax2.set_ylim(0, 90 * DEG)
    ax2.set_yticks([30 * DEG, 60 * DEG])
    ax2.set_yticklabels(["30°", "60°"], fontsize=7, color=C_GREY)
    ax2.set_xticks(np.arange(0, 360, 45) * DEG)
    ax2.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"], fontsize=7)
    ax2.grid(alpha=0.25, lw=0.6)
    fig.text(0.03, 0.972, "(c) FAST 10:00 CST, 68.9% of sky",
             fontsize=9.5, ha="left")
    for con, col, lab, dth, dr in (
        (scene.constraints[1], C_SUN, "sun 30°", -0.30, 0.12),
        (scene.constraints[2], C_MOON, "moon 30°", 0.24, -0.16),
    ):
        alt = np.arcsin(con.axis[2])
        az = np.arctan2(con.axis[0], con.axis[1]) % (2 * np.pi)
        rho = 90 * DEG - alt
        ax2.plot([az], [rho], marker="x", ms=6, mew=1.6, color=col)
        ax2.plot([az], [rho], marker="o", ms=11, mfc="none", mec=col, mew=1.3)
        ax2.text(az + dth, rho + dr, lab, fontsize=6.6, color=col, ha="center",
                 va="center")

    for dest in (OUT / "observability_sky.png", FIGS / "observability_sky.png"):
        fig.savefig(dest, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote observability_sky.png")


if __name__ == "__main__":
    main()
