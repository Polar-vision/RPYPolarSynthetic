"""Figure 3: the regime map and the design-side round trip.

(a) share of the design box on which the table accepts and geometry does not,
    against the allocation measured in standard deviations, for four channel
    counts
(b) the same, against allocation heterogeneity at fixed channel count
(c) the design-side statement: allocation required by geometry against the
    allocation the pairwise rule implies, for a given worst-case spread
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

EXACT = "#1f4e79"
PAIR = "#c0504d"
GREY = "#7f7f7f"
GOLD = "#bf9000"
TEAL = "#2e7d6f"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.6,
    "axes.titlesize": 9.5,
    "axes.labelsize": 8.6,
    "axes.edgecolor": "#444444",
    "axes.linewidth": 0.8,
    "figure.dpi": 200,
})


def load(name):
    with open(ROOT / "outputs_p3" / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


grid = load("regime_grid.csv")
het = load("regime_heterogeneity.csv")
rt = load("regime_round_trip.csv")

fig, axes = plt.subplots(1, 3, figsize=(7.3, 2.7))
fig.subplots_adjust(left=0.077, right=0.982, top=0.885, bottom=0.245, wspace=0.34)

# --- (a) channel count ------------------------------------------------------
ax = axes[0]
colors = {3: "#9dc3e6", 4: TEAL, 5: GOLD, 9: PAIR}
peaks = {}
for n in (3, 4, 5, 9):
    rows = [r for r in grid if int(r["n"]) == n]
    x = [float(r["A_over_sigma"]) for r in rows]
    y = [100 * float(r["missed_by_pairwise"]) for r in rows]
    ax.plot(x, y, "o-", ms=2.8, lw=1.1, color=colors[n], label="$n=%d$" % n,
            markeredgewidth=0)
    k = int(np.argmax(y))
    peaks[n] = (x[k], y[k])
    ax.plot(x[k], y[k], "o", ms=4.0, mfc="white", mew=0.85, mec=colors[n], zorder=5)

ax.set_xlabel(r"tightest allocation $A_{\min}/\sigma$")
ax.set_ylabel("share of design box (%)")
ax.set_xlim(0.65, 3.15)
ax.set_ylim(-0.15, 3.25)
ax.legend(frameon=False, fontsize=7.2, loc="upper right", handlelength=1.4,
          borderpad=0.1, labelspacing=0.25, title="channels", title_fontsize=6.8)
ax.annotate("table accepts,\nno common point", xy=(1.52, 2.10), xytext=(0.86, 2.98),
            fontsize=6.4, color=GREY, ha="left", va="top",
            arrowprops=dict(arrowstyle="-", lw=0.55, color=GREY,
                            connectionstyle="arc3,rad=-0.32"))
ax.set_title("(a)", loc="left", fontsize=9.2, color="#222222")

# --- (b) heterogeneity ------------------------------------------------------
ax = axes[1]
x = [float(r["A_max_over_A_min"]) for r in het]
y = [100 * float(r["missed_by_pairwise"]) for r in het]
ax.plot(x, y, "s-", ms=3.0, lw=1.1, color=EXACT, markeredgewidth=0)
ax.fill_between(x, 0, y, color=EXACT, alpha=0.10, lw=0)
ax.set_xscale("log")
ax.set_xticks([1, 1.5, 2, 3, 5, 10, 20])
ax.set_xticklabels(["1", "1.5", "2", "3", "5", "10", "20"])
ax.set_xlabel(r"allocation ratio $A_{\max}/A_{\min}$")
ax.set_ylabel("share of design box (%)")
ax.set_ylim(0, 3.45)
ax.set_xlim(0.92, 23)
ax.annotate("a slack channel\nabsorbs the spread", xy=(8.0, 0.45),
            xytext=(2.35, 2.30), fontsize=6.4, color=GREY, ha="left", va="center",
            arrowprops=dict(arrowstyle="->", lw=0.5, color=GREY,
                            connectionstyle="arc3,rad=-0.30"))
ax.text(1.02, 3.10, r"$n=9$, $A_{\min}=1.5\sigma$", fontsize=6.6, color="#333333",
        ha="left", va="center")
ax.set_title("(b)", loc="left", fontsize=9.2, color="#222222")

# --- (c) round trip ---------------------------------------------------------
ax = axes[2]
d = np.array([float(r["d_arcsec"]) for r in rt])
a_ex = np.array([float(r["A_required_exact"]) for r in rt])
a_im = np.array([float(r["A_implied_by_pairwise"]) for r in rt])
xs = np.linspace(470, 600, 240)
ax.fill_between(xs, xs / 2, xs / np.sqrt(3), color=PAIR, alpha=0.12, lw=0)
ax.plot(xs, xs / 2, "-", lw=1.2, color=PAIR,
        label=r"table implies $d/2$")
ax.plot(xs, xs / np.sqrt(3), "-", lw=1.2, color=EXACT,
        label=r"geometry requires $d/\sqrt{3}$")
ax.plot(d, a_im, "o", ms=2.8, color=PAIR, mec="white", mew=0.45, zorder=5)
ax.plot(d, a_ex, "o", ms=2.8, color=EXACT, mec="white", mew=0.45, zorder=5)
ax.axvline(519.62, color=GREY, lw=0.6, ls=(0, (4, 2.5)))
ax.annotate("", xy=(574, 574 / 2), xytext=(574, 574 / np.sqrt(3)),
            arrowprops=dict(arrowstyle="<->", lw=0.65, color="#333333"))
ax.text(577.5, 302, "+15.5%", fontsize=6.9, color="#333333", ha="left", va="center")
ax.text(522.5, 226.5, r"band opens at $d=\sqrt{3}A$", fontsize=6.2, color=GREY,
        ha="left", va="bottom")
ax.set_xlabel(r"worst separation $d$  (arcsec)")
ax.set_ylabel("allocation (arcsec)")
ax.set_xlim(470, 600)
ax.set_ylim(222, 358)
ax.legend(frameon=False, fontsize=6.5, loc="upper left", handlelength=1.6,
          borderpad=0.05, labelspacing=0.22,
          bbox_to_anchor=(-0.015, 1.005))
ax.set_title("(c)", loc="left", fontsize=9.2, color="#222222")

for ax in axes:
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

path = OUT / "paper_fig3.png"
fig.savefig(path, dpi=400, facecolor="white")
print("wrote", path, "peaks", {k: (round(v[0], 2), round(v[1], 2)) for k, v in peaks.items()})
