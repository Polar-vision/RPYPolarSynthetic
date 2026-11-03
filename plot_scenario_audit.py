"""Figure for the five-scenario audit (section 9.10)."""

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

OUT = ROOT / "outputs_scenario_audit"
FIGS = ROOT / "analysis" / "figures"

C_RED = "#A32D2D"
C_GREEN = "#1D9E75"
C_GOLD = "#C08A2E"
C_BLUE = "#4A5A8C"
C_GREY = "#8C8A82"
DEG = np.pi / 180.0


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


def main() -> None:
    fig = plt.figure(figsize=(9.4, 5.6))
    gs = fig.add_gridspec(2, 3, left=0.062, right=0.988, bottom=0.085, top=0.925,
                          hspace=0.42, wspace=0.34)

    # ---- (a) interlock: when a keep-out reverses the verdict ---------------
    ax = fig.add_subplot(gs[0, 0])
    rows = load("audit1_interlock.csv")
    b = fnum(rows, "beta_deg")
    ax.plot(b, 100 * fnum(rows, "flip_fraction_closed"), lw=1.6, color=C_RED,
            label="closed form")
    ax.plot(b, 100 * fnum(rows, "flip_fraction_mc"), "o", ms=3.8, color=C_GOLD,
            label="Monte Carlo", clip_on=False)
    ax.axvline(30.0, color=C_GREY, lw=0.8, ls=":")
    ax.annotate("30° cone:\n6.4%", xy=(30.0, 6.4), xytext=(38.0, 13.0), fontsize=7.4,
                color=C_GREY,
                arrowprops=dict(arrowstyle="-", lw=0.7, color=C_GREY))
    ax.set_xlabel(r"keep-out half-angle $\beta$ (deg)", fontsize=8.8)
    ax.set_ylabel("verdict reverses (%)", fontsize=8.8)
    ax.set_title("(a) ① one cone, one formula", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.4, frameon=False, loc="upper left")
    style(ax)

    # ---- (b) star counts --------------------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    rows = load("audit2_stars.csv")
    for fov, col, mk in ((5.0, C_BLUE, "o"), (10.0, C_GREEN, "s"), (15.0, C_GOLD, "^")):
        sub = [r for r in rows if float(r["fov_half_deg"]) == fov]
        ax.plot(fnum(sub, "m_lim"), fnum(sub, "p_fewer_than_3"), marker=mk, ms=3.6,
                lw=1.4, color=col, label=f"FOV ±{fov:.0f}°")
    ax.set_yscale("log")
    ax.set_ylim(1e-12, 3.0)
    ax.set_xlabel("limiting magnitude", fontsize=8.8)
    ax.set_ylabel("P(fewer than 3 stars)", fontsize=8.8)
    ax.set_title("(b) ② the field is never that empty", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.4, frameon=False, loc="lower left")
    style(ax)

    # ---- (c) roll information --------------------------------------------
    ax = fig.add_subplot(gs[0, 2])
    rows = load("audit2_roll.csv")
    single = [r for r in rows if int(r["n_stars"]) == 1]
    many = [r for r in rows if int(r["n_stars"]) > 1]
    for r in single:
        ax.plot([1], [float(r["sigma_psi_over_sigma"])], "o", ms=3.8, color=C_RED,
                clip_on=False)
    ax.annotate("N = 1\noff-axis 5–30°", xy=(1.0, 5.0), xytext=(1.35, 2.4),
                fontsize=7.2, color=C_RED,
                arrowprops=dict(arrowstyle="-", lw=0.7, color=C_RED))
    ax.plot(fnum(many, "n_stars"), fnum(many, "sigma_psi_over_sigma"), "s-", ms=3.4,
            lw=1.4, color=C_GREEN, label=r"$\sigma_\psi/\sigma$")
    ax.plot(fnum(many, "n_stars"), fnum(many, "sigma_theta_over_sigma"), "^-", ms=3.4,
            lw=1.4, color=C_BLUE, label=r"$\sigma_\theta/\sigma$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("stars in the field", fontsize=8.8)
    ax.set_ylabel(r"error / per-star noise", fontsize=8.8)
    ax.set_title("(c) ② roll is the better channel", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.4, frameon=False, loc="lower left")
    style(ax)

    # ---- (d) Helly window is scale free ----------------------------------
    ax = fig.add_subplot(gs[1, 0])
    rows = load("audit3_scale.csv")
    sub = [r for r in rows if float(r["tol_deg"]) == 30.0]
    eps = fnum(sub, "eps")
    gap = np.array([1.0 if r["gap"] == "True" else 0.0 for r in sub])
    ax.plot(eps, gap, lw=2.2, color=C_BLUE,
            label=r"$\Theta$ = 0.5°, 1°, 5°, 30°")
    for tol, col in ((0.5, C_RED), (1.0, C_GOLD), (5.0, C_GREEN)):
        sub = [r for r in rows if float(r["tol_deg"]) == tol]
        g2 = np.array([1.0 if r["gap"] == "True" else 0.0 for r in sub])
        ax.plot(fnum(sub, "eps"), g2, ls="--", lw=0.9, color=col, alpha=0.85)
    ax.axvspan(0.0, 1 - np.sqrt(3) / 2, color="#E8DCC8", alpha=0.55, lw=0, zorder=0)
    ax.text(0.006, 0.42, "pairwise passes,\nno common pointing",
            fontsize=7.4, color=C_GREY)
    ax.set_xlim(0, 0.25)
    ax.set_ylim(-0.08, 1.18)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["passes", "gap"], fontsize=8.2)
    ax.set_xlabel(r"geometry slack $\varepsilon$", fontsize=8.8)
    ax.set_title("(d) ③ the gap does not scale away", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.0, frameon=False, loc="upper right", ncol=2,
              handlelength=1.2, columnspacing=0.8)
    style(ax)

    # ---- (e) baffle design boundary --------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    rows = load("audit4_design.csv")
    ax.axhspan(20.0, 45.0, color="#DCE8E2", alpha=0.8, lw=0, zorder=0)
    ax.text(3.0, 31.0, "typical baffles", fontsize=7.2, color="#4A6A5C")
    for k, col, mk in ((2, C_BLUE, "o"), (3, C_RED, "s")):
        sub = [r for r in rows if int(r["k"]) == k]
        ax.plot(fnum(sub, "gamma_deg"), fnum(sub, "beta_max_deg"), marker=mk, ms=3.6,
                lw=1.5, color=col, label=f"{k} of 4 clear", clip_on=False)
    ax.set_xlim(0, 90)
    ax.set_ylim(15, 95)
    ax.set_xlabel(r"sun–orbit-normal angle $\gamma$ (deg)", fontsize=8.8)
    ax.set_ylabel(r"affordable baffle $\beta_{\max}$ (deg)", fontsize=8.8)
    ax.set_title("(e) ④ the design boundary is one curve", fontsize=9.6, loc="left")
    ax.legend(fontsize=7.2, frameon=False, loc="lower center")
    style(ax)

    # ---- (f) thermal regime map ------------------------------------------
    ax = fig.add_subplot(gs[1, 2])
    rows = load("audit5_thermal.csv")
    qs = sorted({float(r["q_int"]) for r in rows})
    ts = sorted({float(r["t_op"]) for r in rows})
    code = {"none": 0, "cap": 1, "keepout": 2, "annulus": 3, "always_cold": 4,
            "always_hot": 5}
    grid = np.full((len(qs), len(ts)), np.nan)
    for r in rows:
        i = qs.index(float(r["q_int"]))
        j = ts.index(float(r["t_op"]))
        grid[i, j] = code[r["kind"]]
    cmap = matplotlib.colors.ListedColormap(
        ["#F2F0EA", "#CFE0D6", "#E8D8B4", "#B9D2C4", "#9FB6CE", "#DDB2A8"])
    ax.imshow(grid, origin="lower", cmap=cmap, aspect="auto",
              extent=[ts[0] - 10, ts[-1] + 10, qs[0] - 12.5, qs[-1] + 12.5],
              vmin=-0.5, vmax=5.5, interpolation="nearest")
    ann = [(float(r["t_op"]), float(r["q_int"])) for r in rows if r["kind"] == "annulus"]
    ax.plot([a for a, _ in ann], [b for _, b in ann], "o", ms=2.6, color="#255C46")
    ax.set_xlim(234, 376)
    ax.set_xlabel("face set-point $T_{op}$ (K)", fontsize=8.8)
    ax.set_ylabel(r"internal flux $q_{int}$ (W/m$^2$)", fontsize=8.8)
    ax.set_title("(f) ⑥ the band is common, not rare", fontsize=9.6, loc="left")
    handles = [matplotlib.patches.Patch(facecolor=cmap(i), edgecolor="none",
                                        label=lab)
               for i, lab in ((3, "band"), (2, "keep-out only"), (1, "cap only"),
                              (4, "always cold"), (5, "always hot"))]
    ax.legend(handles=handles, fontsize=6.8, frameon=False, loc="center right",
              handlelength=1.0, borderaxespad=0.3)
    style(ax)
    ax.grid(False)

    fig.text(0.062, 0.975, "Five scenarios, five load-bearing assumptions, and what broke them",
             fontsize=10.6, ha="left")
    FIGS.mkdir(parents=True, exist_ok=True)
    for dest in (OUT / "scenario_audit.png", FIGS / "scenario_audit.png"):
        fig.savefig(dest, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote scenario_audit.png")


if __name__ == "__main__":
    main()
