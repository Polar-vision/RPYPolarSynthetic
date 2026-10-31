"""Figure 1 for the pairwise-sufficiency paper.

(a) three channels with equal allocation A whose as-built deviations sit at the
    vertices of an equilateral triangle of side 1.95 A: every pair overlaps, no
    point serves all three.
(b) the three thresholds on one axis: per-channel check, exact condition,
    pairwise rule, with the blind band shaded.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon

TEAL = "#2F6F6A"
GOLD = "#B8860B"
RED = "#B4453C"
GREY = "#7A7A7A"
BAND = "#E8C9C4"

plt.rcParams.update({
    "font.size": 8.4,
    "axes.linewidth": 0.7,
    "axes.edgecolor": "#444444",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "figure.dpi": 220,
    "mathtext.fontset": "dejavusans",
})

S = 1.95
R = 1.0
V = np.array([[0.0, 0.0], [S, 0.0], [S / 2, -S * np.sqrt(3) / 2]])
CENTROID = V.mean(axis=0)
RSTAR = S / np.sqrt(3)

fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.0, 3.15),
                             gridspec_kw={"width_ratios": [1.0, 1.4]})


# ---------------------------------------------------------------- panel (a)
for i, c in enumerate(V):
    ax.add_patch(Circle(c, R, fill=False, lw=1.0, ec=TEAL, zorder=3))
    ax.plot(*c, "o", ms=2.8, color=TEAL, zorder=4)
    away = c + 0.14 * (c - CENTROID) / np.linalg.norm(c - CENTROID)
    ax.text(away[0], away[1], "$d_%d$" % (i + 1), ha="center", va="center",
            fontsize=7.6, color=TEAL)

# the hole: on each circle, keep the arc that faces the centroid and lies
# outside both other circles
segs = []
for i in range(3):
    t = np.linspace(0, 2 * np.pi, 8000)
    pts = np.stack([V[i, 0] + R * np.cos(t), V[i, 1] + R * np.sin(t)], 1)
    outside = np.array([all(np.linalg.norm(p - V[j]) > R for j in range(3) if j != i)
                        for p in pts])
    near = V[i] + R * (CENTROID - V[i]) / np.linalg.norm(CENTROID - V[i])
    k = int(np.argmin(np.linalg.norm(pts - near, axis=1)))
    if not outside[k]:
        continue
    lo = k
    while outside[(lo - 1) % len(pts)]:
        lo = (lo - 1) % len(pts)
    hi = k
    while outside[(hi + 1) % len(pts)]:
        hi = (hi + 1) % len(pts)
    idx = np.arange(lo, lo + (hi - lo) % len(pts)) % len(pts)
    segs.append(pts[idx])
hole = np.vstack(segs)
hole = hole[np.argsort(np.arctan2(hole[:, 1] - CENTROID[1], hole[:, 0] - CENTROID[0]))]
ax.add_patch(Polygon(hole, closed=True, fc=BAND, ec=RED, lw=0.8, alpha=0.95, zorder=2))

ax.plot([V[0, 0], V[1, 0]], [0.03, 0.03], ls=(0, (3, 2)), lw=0.6, color=GREY, zorder=1)
ax.text(S / 2, 0.07, "$1.95A$", ha="center", va="bottom", fontsize=7.0, color=GREY)

ax.annotate("no point serves all three\n$r^{\\star}=%.2fA>A$" % RSTAR,
            xy=(float(CENTROID[0]), float(CENTROID[1])), xytext=(1.42, -2.78),
            fontsize=7.0, color=RED, ha="left", va="center",
            bbox=dict(fc="white", ec="none", pad=1.2), zorder=6,
            arrowprops=dict(arrowstyle="->", lw=0.6, color=RED,
                            connectionstyle="arc3,rad=-0.12"))
ax.text(-1.18, 1.08, "every pair overlaps\n$1.95A<2A$", fontsize=7.0, color=TEAL,
        ha="left", va="center", zorder=6,
        bbox=dict(fc="white", ec="none", pad=1.2))

ax.set_xlim(-1.22, 3.10)
ax.set_ylim(-3.05, 1.30)
ax.set_aspect("equal")
ax.set_xticks([])
ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("(a) pairs pass, the triple fails", loc="left", fontsize=8.8, pad=6)

# ---------------------------------------------------------------- panel (b)
bx.axvspan(np.sqrt(3), 2.0, color=BAND, alpha=0.55, lw=0, zorder=0)

rows = [
    (2.00, "per-channel check  $d\\leq A$", 1.00, TEAL, "sufficient"),
    (1.00, "exact condition  $d\\leq\\sqrt{3}\\,A$", np.sqrt(3), GOLD, "necessary and sufficient"),
    (0.00, "pairwise rule  $d\\leq 2A$", 2.00, RED, "necessary only"),
]
for y, label, x, col, note in rows:
    bx.plot([0, x], [y, y], lw=2.6, color=col, solid_capstyle="butt", zorder=3)
    bx.plot([x], [y], "|", ms=12, mew=1.5, color=col, zorder=4)
    bx.text(x + 0.05, y, "%.3f$A$" % x, va="center", fontsize=7.2, color=col)
    bx.text(-0.05, y + 0.24, label, ha="left", va="bottom", fontsize=7.4, color="#222222")
    bx.text(-0.05, y - 0.26, note, ha="left", va="top", fontsize=6.6, color=GREY)

bx.annotate("", xy=(np.sqrt(3), 2.60), xytext=(2.0, 2.60),
            arrowprops=dict(arrowstyle="<->", lw=0.7, color=RED))
bx.text((np.sqrt(3) + 2.0) / 2, 2.66,
        "blind band\n$(2-\\sqrt{3})A=0.268A$", ha="center", va="bottom",
        fontsize=6.9, color=RED, linespacing=1.3)
bx.text((np.sqrt(3) + 2.0) / 2, -0.62,
        "$13.4\\%$ of the span the table permits", ha="center", va="top",
        fontsize=6.9, color=RED)

bx.set_xlim(-0.06, 2.42)
bx.set_ylim(-0.95, 3.55)
bx.set_yticks([])
bx.set_xlabel("worst pairwise separation $d$  (units of the allocation $A$)",
              fontsize=7.6, labelpad=4)
for s in ("left", "right", "top"):
    bx.spines[s].set_visible(False)
bx.set_title("(b) where the three criteria stop agreeing", loc="left", fontsize=8.8, pad=6)

fig.tight_layout(pad=0.35, w_pad=1.2)
fig.savefig("analysis/figures/paper_fig1.png", dpi=400, bbox_inches="tight", facecolor="white")
print("wrote analysis/figures/paper_fig1.png")
