"""Direction-B (intervention) figure: raising attention on the correct source raises accuracy,
where stabilizing variance does not, and the accuracy gain tracks the attention gain across cells.

Reads results/lengthgen/gpu_resultsAB.json (baseline + varfix + attn(loglen), 4 seeds).
Writes results/lengthgen/fig_intervention.{pdf,png} at single-column size.
"""
from __future__ import annotations
import json
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({
    "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
    "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6, "figure.dpi": 150,
})
OUT = "results/lengthgen"
CELLS = [("argmax", "nope"), ("argmax", "rope"), ("flagret", "nope"), ("flagret", "rope")]
LABELS = ["argmax\nNoPE", "argmax\nRoPE", "flagret\nNoPE", "flagret\nRoPE"]
GRAY, RED = "#7f7f7f", "#d62728"


def cond_of(c):
    ln, sc = int(c["post_attn_ln"]), c.get("attn_scale", "none")
    return "baseline" if (ln == 0 and sc == "none") else "varfix" if (ln == 1 and sc == "none") else "attn" if ln == 0 else None


def main():
    data = json.load(open(f"{OUT}/gpu_resultsAB.json"))
    L0 = data[0]["cfg"]["l_train"]
    idx = {}
    for r in data:
        c = r["cfg"]; cd = cond_of(c)
        if cd:
            idx[(c["task"], c["pe"], cd, c["seed"])] = {row["length"]: row for row in r["ladder"]}
    seeds = defaultdict(set)
    for (t, pe, cd, sd) in idx:
        seeds[(t, pe, cd)].add(sd)

    def mtok(t, pe, cd, L):
        return float(np.mean([idx[(t, pe, cd, s)][L]["tok"] for s in seeds[(t, pe, cd)] if L in idx[(t, pe, cd, s)]]))

    def break_len(t, pe):
        lens = sorted({L for s in seeds[(t, pe, "baseline")] for L in idx[(t, pe, "baseline", s)]})
        broke = [L for L in lens if L > L0 and mtok(t, pe, "baseline", L) < 0.9]
        return broke[-1] if broke else lens[-1]

    def pdelta(t, pe, cd, L):
        common = seeds[(t, pe, cd)] & seeds[(t, pe, "baseline")]
        return float(np.mean([idx[(t, pe, cd, s)][L]["tok"] - idx[(t, pe, "baseline", s)][L]["tok"] for s in common]))

    def attn(t, pe, cd, L):
        return float(np.mean([max(idx[(t, pe, cd, s)][L]["attn_tgt"]) for s in seeds[(t, pe, cd)] if L in idx[(t, pe, cd, s)]]))

    varb, shpb, again = [], [], []
    for (t, pe) in CELLS:
        L = break_len(t, pe)
        varb.append(pdelta(t, pe, "varfix", L))
        shpb.append(pdelta(t, pe, "attn", L))
        again.append(attn(t, pe, "attn", L) - attn(t, pe, "baseline", L))
    varb, shpb, again = np.array(varb), np.array(shpb), np.array(again)
    r = float(np.corrcoef(again, shpb)[0, 1])

    fig, ax = plt.subplots(2, 1, figsize=(3.3, 4.3))
    # Panel A: benefit by cell, varfix vs sharpen
    x = np.arange(len(CELLS)); w = 0.38
    ax[0].bar(x - w / 2, varb, w, color=GRAY, label="stabilize variance")
    ax[0].bar(x + w / 2, shpb, w, color=RED, label="sharpen attention")
    ax[0].axhline(0, color="k", lw=0.7); ax[0].axhline(0.05, color="gray", ls=":", lw=0.8)
    ax[0].set_xticks(x); ax[0].set_xticklabels(LABELS)
    ax[0].set_ylabel("per-token benefit at break"); ax[0].legend(loc="upper right")
    ax[0].set_title("Sharpen attention vs stabilize variance")
    ax[0].grid(axis="y", alpha=0.25)
    # Panel B: accuracy gain vs attention gain, r
    ax[1].axhline(0, color="k", lw=0.5); ax[1].axvline(0, color="k", lw=0.5)
    ax[1].scatter(again, shpb, s=28, c=RED, zorder=3)
    for gx, gy, lab in zip(again, shpb, ["a·N", "a·R", "f·N", "f·R"]):
        ax[1].annotate(lab, (gx, gy), textcoords="offset points", xytext=(4, 3), fontsize=6)
    # fit line
    if np.std(again) > 1e-9:
        b1, b0 = np.polyfit(again, shpb, 1)
        xs = np.linspace(min(again) - 0.02, max(again) + 0.02, 20)
        ax[1].plot(xs, b1 * xs + b0, color="k", lw=0.8, ls="--")
    ax[1].set_xlabel("gain in attention on correct source")
    ax[1].set_ylabel("gain in accuracy")
    ax[1].set_title(f"Accuracy gain tracks attention gain (r={r:+.2f})")
    ax[1].grid(alpha=0.25)
    fig.tight_layout(pad=0.5)
    fig.savefig(f"{OUT}/fig_intervention.pdf"); fig.savefig(f"{OUT}/fig_intervention.png", dpi=150)
    print(f"wrote fig_intervention  r(attn_gain, acc_gain)={r:+.3f}")
    for (t, pe), v, s, a in zip(CELLS, varb, shpb, again):
        print(f"  {t:8s}{pe:5s} varfix {v:+.3f}  sharpen {s:+.3f}  attn_gain {a:+.3f}")


if __name__ == "__main__":
    main()
