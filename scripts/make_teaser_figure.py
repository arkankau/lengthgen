"""Honest FSS teaser: mechanism (source-max row swap) + a use-case on in-context key-value recall.

Left two panels are the mechanism: one attention-weight multiset, assigned two ways; source-max moves the row
maximum onto the gold value while preserving the complete spectrum. Right panel is the use case: the paired
change in the target-answer margin on the same run condition (source-max onto the gold value), illustrative in
scale. Neither panel depicts the semantic-distractor control we do not run.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.gridspec import GridSpec
import numpy as np

PENNBLUE = "#011F5B"
PENNRED = "#990000"
GRAY = "#9AA3AF"
BLUEFILL = "#3B6FB6"
GREENFILL = "#2E7D57"

tokens = ["milk", ":", "warm", "leaf", ":", "green", "milk", ":"]
gold = 2  # gold value "warm"
heights = np.array([0.05, 0.03, 0.10, 0.46, 0.04, 0.22, 0.06, 0.04])
orig = heights.copy()
swapped = heights.copy()
swapped[gold], swapped[3] = orig[3], orig[gold]

fig = plt.figure(figsize=(8.2, 2.7))
gs = GridSpec(1, 3, width_ratios=[1.05, 1.05, 1.15], wspace=0.42,
              left=0.02, right=0.985, top=0.82, bottom=0.16)
ax0, ax1, ax2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1]), fig.add_subplot(gs[2])


def draw_row(ax, w, title, hot):
    colors = [GRAY] * len(w)
    bars = ax.bar(range(len(w)), w, color=colors, width=0.62)
    bars[hot].set_color(PENNRED)
    bars[gold].set_color(PENNRED if hot == gold else BLUEFILL)
    ax.set_xticks(range(len(w)))
    ax.set_xticklabels(tokens, rotation=40, ha="right", fontsize=7)
    ax.set_ylim(0, 0.55); ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title(title, fontsize=9, pad=4)
    ax.annotate("gold", (gold, w[gold] + 0.01), ha="center", fontsize=7, color=PENNBLUE)


draw_row(ax0, orig, "Original row", hot=3)
draw_row(ax1, swapped, "Source-max swap", hot=gold)

# arrow between the two mechanism panels
arr = FancyArrowPatch((0.335, 0.52), (0.40, 0.52), transform=fig.transFigure,
                      arrowstyle="-|>", mutation_scale=13, lw=1.3, color="black")
fig.add_artist(arr)

# --- use case: paired target-answer margin (illustrative scale) ---
labels = ["original", "source-max"]
margins = [-0.4, 1.1]
answers = ["green (wrong)", "warm  ✓"]
cols = [GRAY, GREENFILL]
b = ax2.bar([0, 1], margins, color=cols, width=0.55)
ax2.axhline(0, color="#555555", lw=0.8)
ax2.set_xticks([0, 1]); ax2.set_xticklabels(labels, fontsize=8)
ax2.set_ylim(-0.9, 1.5); ax2.set_yticks([])
for s in ("top", "right", "left"):
    ax2.spines[s].set_visible(False)
ax2.set_title("Use case: recall answer margin", fontsize=9, pad=4)
for x, m, a in zip([0, 1], margins, answers):
    va = "bottom" if m > 0 else "top"
    ax2.annotate(a, (x, m + (0.06 if m > 0 else -0.06)), ha="center", va=va, fontsize=7.5,
                 color=(GREENFILL if m > 0 else PENNRED))
ax2.set_ylabel("target $-$ competitor\nmargin", fontsize=7.5)

fig.text(0.345, 0.60, "move max\n$\\rightarrow$ gold", ha="center", va="center", fontsize=7.5)

out = "paper_workshop/figures/fig_teaser_sourcemax"
fig.savefig(out + ".png", dpi=200)
fig.savefig(out + ".pdf")
print("saved", out + ".png")
