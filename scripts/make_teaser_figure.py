"""Honest FSS teaser: mechanism (source-max onto gold evidence) + a natural-QA use case.

Left/middle: the mechanism. One attention-weight multiset over the context, assigned two ways; source-max
moves the row maximum onto the gold-evidence token ("Tokyo") while preserving the complete spectrum. Right:
the natural-QA use case we run at fixed context -- when attention is routed to the gold evidence, the model's
answer flips from a competitor ("Paris") to the correct answer, and the target-answer margin becomes positive.
This depicts source-max onto the gold evidence (the treatment), not the semantic-distractor control; the margin
scale is illustrative and FSS is a diagnostic, not an inference-time fix.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.gridspec import GridSpec
import numpy as np

PENNBLUE = "#011F5B"
PENNRED = "#990000"
GRAY = "#9AA3AF"
BLUEFILL = "#3B6FB6"
GREEN = "#2E7D57"

# context tokens the answer query attends over; gold evidence is "Tokyo"
ctx = ["France", ":", "Paris", "Japan", ":", "Tokyo", "…", "Japan?"]
gold = 5
heights = np.array([0.06, 0.03, 0.44, 0.08, 0.04, 0.11, 0.05, 0.03])
orig = heights.copy()                 # model's max lands on the "Paris" distractor (pos 2)
swap = heights.copy()
swap[gold], swap[2] = orig[2], orig[gold]   # source-max: move the max onto the gold evidence "Tokyo"

fig = plt.figure(figsize=(8.4, 2.75))
gs = GridSpec(1, 3, width_ratios=[1.05, 1.05, 1.25], wspace=0.4,
              left=0.015, right=0.985, top=0.82, bottom=0.17)
ax0, ax1, ax2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])


def draw_row(ax, w, title, hot):
    bars = ax.bar(range(len(w)), w, color=[GRAY] * len(w), width=0.64)
    bars[hot].set_color(PENNRED)
    bars[gold].set_color(PENNRED if hot == gold else BLUEFILL)
    ax.set_xticks(range(len(w)))
    ax.set_xticklabels(ctx, rotation=42, ha="right", fontsize=6.7)
    ax.set_ylim(0, 0.52); ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title(title, fontsize=9, pad=4)
    ax.annotate("gold evidence", (gold, w[gold] + 0.01), ha="center", fontsize=6.6, color=PENNBLUE)


draw_row(ax0, orig, "Original attention", hot=2)
draw_row(ax1, swap, "Source-max (onto gold)", hot=gold)

arr = FancyArrowPatch((0.33, 0.52), (0.395, 0.52), transform=fig.transFigure,
                      arrowstyle="-|>", mutation_scale=13, lw=1.3, color="black")
fig.add_artist(arr)
fig.text(0.3625, 0.6, "route to\ngold evidence", ha="center", va="center", fontsize=6.8)

# --- natural-QA use case: answer flips, margin turns positive ---
ax2.set_title("Use case: context-grounded QA", fontsize=9, pad=4)
ax2.set_xlim(0, 1); ax2.set_ylim(0, 1); ax2.axis("off")
ax2.text(0.5, 0.93, "“What is the capital of Japan?”", ha="center", fontsize=7.6, style="italic")
# two mini answer chips
ax2.add_patch(FancyBboxPatch((0.06, 0.42), 0.4, 0.28, boxstyle="round,pad=0.02",
                             fc="#F3F3F3", ec=GRAY, lw=1))
ax2.text(0.26, 0.61, "original", ha="center", fontsize=7.2, color="#555")
ax2.text(0.26, 0.49, "“Paris”  ✗", ha="center", fontsize=8.2, color=PENNRED, weight="bold")
ax2.add_patch(FancyBboxPatch((0.54, 0.42), 0.4, 0.28, boxstyle="round,pad=0.02",
                             fc="#EAF3EE", ec=GREEN, lw=1.2))
ax2.text(0.74, 0.61, "source-max", ha="center", fontsize=7.2, color="#555")
ax2.text(0.74, 0.49, "“Tokyo”  ✓", ha="center", fontsize=8.2, color=GREEN, weight="bold")
ax2.annotate("", (0.54, 0.56), (0.46, 0.56), arrowprops=dict(arrowstyle="-|>", lw=1.3, color="black"))
# margin annotation
ax2.text(0.5, 0.22, "answer margin:  $-\\;\\rightarrow\\;+$",
         ha="center", fontsize=7.6, color="#333")

out = "paper_workshop/figures/fig_teaser_sourcemax"
fig.savefig(out + ".png", dpi=200)
fig.savefig(out + ".pdf")
print("saved", out + ".png")
