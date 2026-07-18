"""Figures for the length-gen scoping result (colab/length_gen_colab.py JSON output).

Fig 1 (main): per-token accuracy vs length, baseline (no-LN) vs post-attention-LN, for each
              order-invariant task x positional-encoding. Shows the fix never helps and hurts on RoPE.
Fig 2 (mechanism): deep-layer attention-output variance vs length (normalized to train length),
              showing the variance collapse the fix targets IS present.

Usage: python scripts/make_lengthgen_figures.py results/lengthgen/gpu_results.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "results/lengthgen"
L_TRAIN = 5


def load(path):
    data = json.load(open(path))
    g = defaultdict(list)
    for r in data:
        c = r["cfg"]
        g[(c["task"], c["pe"], int(c["post_attn_ln"]))].append({row["length"]: row for row in r["ladder"]})
    return g


def curve(ladders, key, layer=None):
    """Mean and (min,max) across seeds at each length. layer=None -> accuracy; else var[layer]."""
    lengths = sorted({L for lad in ladders for L in lad})
    mean, lo, hi = [], [], []
    for L in lengths:
        vals = []
        for lad in ladders:
            if L in lad:
                vals.append(lad[L]["var"][layer] if layer is not None else lad[L][key])
        vals = np.array(vals)
        mean.append(vals.mean()); lo.append(vals.min()); hi.append(vals.max())
    return np.array(lengths), np.array(mean), np.array(lo), np.array(hi)


def maxcollapse_layer(g, task, pe):
    """Layer with strongest baseline collapse (train->longest)."""
    lads = g[(task, pe, 0)]
    Ls = sorted({L for lad in lads for L in lad})
    nlayer = len(lads[0][Ls[0]]["var"])
    ratios = []
    for l in range(nlayer):
        vt = np.mean([lad[Ls[0]]["var"][l] for lad in lads])
        vl = np.mean([lad[Ls[-1]]["var"][l] for lad in lads])
        ratios.append(vl / vt if vt > 1e-9 else 1.0)
    return int(np.argmin(ratios))


def fig_accuracy(g, tasks, path):
    pes = ["nope", "rope"]
    fig, axes = plt.subplots(len(tasks), 2, figsize=(9, 3.4 * len(tasks)), squeeze=False)
    for i, task in enumerate(tasks):
        for j, pe in enumerate(pes):
            ax = axes[i][j]
            for ln, color, lab, ls in [(0, "#1f77b4", "baseline (no LN)", "-"),
                                       (1, "#d62728", "post-attn LayerNorm", "--")]:
                if (task, pe, ln) not in g:
                    continue
                x, m, lo, hi = curve(g[(task, pe, ln)], "tok")
                ax.plot(x, m, ls, color=color, label=lab, lw=2)
                ax.fill_between(x, lo, hi, color=color, alpha=0.15)
            ax.axvline(L_TRAIN, color="gray", ls=":", lw=1)
            ax.text(L_TRAIN * 1.05, 0.12, "train len", color="gray", fontsize=8, rotation=90, va="bottom")
            ax.set_xscale("log")
            ax.set_ylim(0, 1.03)
            ax.set_title(f"{task}  ·  {pe.upper()}", fontsize=11)
            ax.set_xlabel("sequence length (log)"); ax.set_ylabel("per-token accuracy")
            ax.grid(alpha=0.25)
            if i == 0 and j == 0:
                ax.legend(fontsize=9, loc="lower left")
    fig.suptitle("Post-attention LayerNorm does not rescue length generalization\n"
                 "(order-invariant tasks; the arXiv:2504.02827 fix is neutral under NoPE, harmful under RoPE)",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{path}.png", dpi=150); fig.savefig(f"{path}.pdf")
    print(f"wrote {path}.png / .pdf")


def fig_variance(g, tasks, path):
    pes = ["nope", "rope"]
    fig, axes = plt.subplots(1, len(tasks), figsize=(5 * len(tasks), 4), squeeze=False)
    for i, task in enumerate(tasks):
        ax = axes[0][i]
        for pe in pes:
            layer = maxcollapse_layer(g, task, pe)
            x, m, lo, hi = curve(g[(task, pe, 0)], None, layer=layer)
            ax.plot(x, m / m[0], "-o", ms=3, label=f"{pe.upper()} (layer {layer})")
        ax.axhline(1.0, color="gray", ls=":", lw=1)
        ax.set_xscale("log")
        ax.set_title(f"{task}: baseline attention-output variance", fontsize=11)
        ax.set_xlabel("sequence length (log)")
        ax.set_ylabel("variance (normalized to train length)")
        ax.grid(alpha=0.25); ax.legend(fontsize=9)
    fig.suptitle("The variance collapse the fix targets IS present in the baseline "
                 "(deepest-collapsing layer)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(f"{path}.png", dpi=150); fig.savefig(f"{path}.pdf")
    print(f"wrote {path}.png / .pdf")


def main(path):
    g = load(path)
    tasks = [t for t in ("argmax", "flagret", "addition", "recall") if any(k[0] == t for k in g)]
    fig_accuracy(g, tasks, f"{OUT}/fig_accuracy_vs_length")
    fig_variance(g, tasks, f"{OUT}/fig_variance_collapse")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/gpu_results.json")
