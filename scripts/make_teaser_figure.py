"""Honest FSS teaser: the source-max condition on in-context key-value recall (a condition we run).

Two panels share one attention-weight multiset. Left is the model's original row (its maximum on a distractor
value); right is the spectrum-preserving swap that moves that maximum onto the gold value, with every sorted
weight preserved. This depicts the actual treatment, not the semantic-distractor control.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import numpy as np

PENNBLUE = "#011F5B"
PENNRED = "#990000"
GRAY = "#9AA3AF"
BLUEFILL = "#3B6FB6"

# in-context KV recall: "milk : warm  leaf : green  ...  milk :"  -> gold value is "warm"
tokens = ["milk", ":", "warm", "leaf", ":", "green", "milk", ":"]
gold = 2  # position of the gold value ("warm")
# a fixed weight multiset (sorted heights), assigned two ways
heights = np.array([0.05, 0.03, 0.10, 0.46, 0.04, 0.22, 0.06, 0.04])
orig = heights.copy()               # original: max (0.46) sits on "leaf" (a distractor), pos 3
swapped = heights.copy()            # source-max: swap the max onto the gold value (pos 2)
swapped[gold], swapped[3] = orig[3], orig[gold]

fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.5))


def draw(ax, w, title, hot):
    colors = [GRAY] * len(w)
    colors[gold] = PENNBLUE if hot == gold else PENNBLUE
    bars = ax.bar(range(len(w)), w, color=colors, width=0.62, edgecolor="none")
    bars[hot].set_color(PENNRED)          # the maximum weight
    if hot != gold:
        bars[gold].set_color(BLUEFILL)
    else:
        bars[gold].set_color(PENNRED)
    ax.set_xticks(range(len(w)))
    ax.set_xticklabels(tokens, rotation=35, ha="right", fontsize=8)
    ax.set_ylim(0, 0.55)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title(title, fontsize=10, pad=6)
    # mark the gold value position
    ax.annotate("gold value", (gold, w[gold]), xytext=(gold, 0.52),
                ha="center", fontsize=7.5, color=PENNBLUE,
                arrowprops=dict(arrowstyle="->", color=PENNBLUE, lw=0.8))


draw(axes[0], orig, "Original attention row", hot=3)
draw(axes[1], swapped, "Spectrum-preserving swap (source-max)", hot=gold)

# arrow + label between panels
fig.text(0.5, 0.60, "move the maximum weight\nonto the gold value",
         ha="center", va="center", fontsize=8.5, color="black")
arr = FancyArrowPatch((0.44, 0.5), (0.56, 0.5), transform=fig.transFigure,
                      arrowstyle="-|>", mutation_scale=16, lw=1.4, color="black")
fig.add_artist(arr)
fig.text(0.5, 0.015,
         "The complete sorted weight multiset is identical in both panels; only its assignment to positions "
         "changes.\nThe paired change in the target-answer margin measures the effect.",
         ha="center", va="bottom", fontsize=7.6, color="#333333")

fig.subplots_adjust(left=0.03, right=0.97, top=0.80, bottom=0.28, wspace=0.18)
out = "paper_workshop/figures/fig_teaser_sourcemax"
fig.savefig(out + ".png", dpi=200)
fig.savefig(out + ".pdf")
print("saved", out + ".png")
