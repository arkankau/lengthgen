"""Figure for Direction A: attention-on-correct-source predicts length-gen accuracy; variance doesn't.

Two panels, pooled over all baseline (fix-off) order-invariant runs and lengths:
  (left)  per-token accuracy vs attention-on-correct-source  -> tight
  (right) per-token accuracy vs variance-collapse ratio      -> diffuse
Point color by task; r shown in each panel.

Usage: python scripts/make_causal_figure.py results/lengthgen/gpu_resultsA.json
"""
from __future__ import annotations
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "results/lengthgen/fig_causal"
COL = {"argmax": "#1f77b4", "flagret": "#d62728"}


def main(path):
    data = json.load(open(path))
    acc, tgt, vr, cols = [], [], [], []
    for r in data:
        c = r["cfg"]
        if c["task"] not in COL or c["post_attn_ln"]:   # baselines only
            continue
        lad = r["ladder"]
        vt = np.array(lad[0]["var"]); good = vt > 1e-9
        for row in lad:
            if "attn_tgt" not in row:
                continue
            acc.append(row["tok"]); tgt.append(max(row["attn_tgt"]))
            rr = np.array(row["var"])
            vr.append(float(np.min(rr[good] / vt[good])) if good.any() else np.nan)
            cols.append(COL[c["task"]])
    acc, tgt, vr = np.array(acc), np.array(tgt), np.array(vr)

    def r_of(x, y):
        ok = np.isfinite(x) & np.isfinite(y)
        return float(np.corrcoef(x[ok], y[ok])[0, 1])

    fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
    ax[0].scatter(tgt, acc, c=cols, s=10, alpha=0.5)
    ax[0].set_xlabel("attention on correct source token"); ax[0].set_ylabel("per-token accuracy")
    ax[0].set_title(f"accuracy vs attention-on-source   (r = {r_of(tgt, acc):.2f})")
    ax[1].scatter(vr, acc, c=cols, s=10, alpha=0.5)
    ax[1].set_xlabel("attention-output variance ratio (long / train)")
    ax[1].set_title(f"accuracy vs variance collapse   (r = {r_of(vr, acc):.2f})")
    for a in ax:
        a.set_ylim(0.45, 1.03); a.grid(alpha=0.25)
    from matplotlib.lines import Line2D
    ax[0].legend(handles=[Line2D([0], [0], marker='o', ls='', color=COL[t], label=t) for t in COL],
                 fontsize=9, loc="lower right")
    fig.suptitle("The driver of length-gen failure is attention dispersion off the correct source, "
                 "not variance collapse\n(baselines, order-invariant tasks, both positional encodings, "
                 "all lengths & seeds)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(f"{OUT}.png", dpi=150); fig.savefig(f"{OUT}.pdf")
    print(f"wrote {OUT}.png / .pdf   (n={len(acc)} points)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/gpu_resultsA.json")
