"""Figure for the real LLFF next-best-view feasibility comparison."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
d = pd.read_csv(ROOT / "outputs_cv_nbv" / "cv_nbv_results.csv")
eps_order = [0.5, 0.2, 0.05]
blue, red, muted, ink = "#3264a8", "#c44e52", "#6c737d", "#20242a"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": "#aab0b8", "axes.labelcolor": ink})

fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.1))

ax = axes[0]
x = np.arange(3)
grid_rates = [100 * d[d.eps_deg == e].grid_hit.mean() for e in eps_order]
branch_rates = [100 * d[d.eps_deg == e].branch_hit.mean() for e in eps_order]
ax.bar(x - 0.18, grid_rates, 0.36, color=blue, label="grid")
ax.bar(x + 0.18, branch_rates, 0.36, color=red, label="branch")
for xx in x:
    ax.text(xx - 0.18, 100.45, "grid\n100", ha="center", va="bottom", fontsize=6.8, color=blue)
    ax.text(xx + 0.18, 100.45, "branch\n100", ha="center", va="bottom", fontsize=6.8, color=red)
ax.set_xticks(x, [str(e) for e in eps_order])
ax.set_xlabel("resolution (deg)")
ax.set_ylabel("feasible-point success (%)")
ax.set_ylim(94, 104)
ax.set_title("(a) 0 misses in 4,254 queries", loc="left", color=ink)

ax = axes[1]
data, positions, colors = [], [], []
for i, e in enumerate(eps_order):
    g = d[d.eps_deg == e]
    data.extend([1000 * g.grid_s.to_numpy(), 1000 * g.branch_s.to_numpy()])
    positions.extend([i - 0.16, i + 0.16])
    colors.extend([blue, red])
bp = ax.boxplot(data, positions=positions, widths=0.25, patch_artist=True,
                showfliers=False, medianprops={"color": ink, "lw": 1.0},
                whiskerprops={"lw": 0.8}, capprops={"lw": 0.8})
for patch, color in zip(bp["boxes"], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.75)
    patch.set_edgecolor("none")
ax.set_yscale("log")
ax.set_xticks(x, [str(e) for e in eps_order])
ax.set_xlabel("resolution (deg)")
ax.set_ylabel("query time (ms, log)")
ax.set_title("(b) certification is not faster", loc="left", color=ink)
ax.set_xlabel("resolution (deg; grid cached)")

ax = axes[2]
one = d[d.eps_deg == 0.5]
ax.hist(one.branch_point_clearance_deg, bins=22, color=blue, alpha=0.85)
lo = one.branch_point_clearance_deg.min()
ax.axvline(lo, color=red, ls="--", lw=1.1)
ax.text(lo + 0.04, ax.get_ylim()[1] * 0.86, f"min {lo:.3f} deg", color=red, fontsize=7.5)
ax.set_xlabel("clearance of returned point (deg)")
ax.set_ylabel("planning states")
ax.set_title("(c) solutions are not tangencies", loc="left", color=ink)

for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=3)
fig.tight_layout(w_pad=2.0)
out = ROOT / "analysis" / "figures" / "cv_nbv.png"
fig.savefig(out, dpi=220, bbox_inches="tight")
print(out)
