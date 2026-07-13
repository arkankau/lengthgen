"""Extra figures so the story is supported by data throughout (not three figures piled at the end).

From results/lengthgen/gpu_resultsA.json (argmax+flagret, 4 seeds, with var / var_post / attn_tgt):
  fig_prepost_var        the remedy holds downstream variance constant (pre collapses, post flat)
  fig_attn_vs_length     attention on the correct source collapses with length (baseline)
  fig_benefit_vs_length  the remedy's per-token benefit vs length (<= 0, worsens under RoPE)
  fig_attn_base_vs_fix   the remedy lowers attention on the correct source, especially under RoPE

Usage: python scripts/make_lengthgen_extra_figures.py results/lengthgen/gpu_resultsA.json
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "results/lengthgen"
TASKS = ["argmax", "flagret"]
PES = ["nope", "rope"]
BLUE, RED = "#1f77b4", "#d62728"


def load(path):
    g = defaultdict(list)  # (task, pe, fix) -> list over seeds of {length: row}
    for r in json.load(open(path)):
        c = r["cfg"]
        if c["task"] in TASKS and c.get("attn_scale", "none") == "none":
            g[(c["task"], c["pe"], int(c["post_attn_ln"]))].append({row["length"]: row for row in r["ladder"]})
    return g


def curve(lads, fn):
    lengths = sorted({L for lad in lads for L in lad})
    m, lo, hi = [], [], []
    for L in lengths:
        v = np.array([fn(lad[L]) for lad in lads if L in lad], float)
        v = v[np.isfinite(v)]
        m.append(v.mean() if len(v) else np.nan); lo.append(v.min() if len(v) else np.nan); hi.append(v.max() if len(v) else np.nan)
    return np.array(lengths), np.array(m), np.array(lo), np.array(hi)


def grid(nrows=2, ncols=2, h=6.4):
    fig, ax = plt.subplots(nrows, ncols, figsize=(9, h), squeeze=False)
    return fig, ax


def panel_title(ax, t, pe):
    ax.set_title(f"{t} · {pe.upper()}", fontsize=11)


def fig_prepost(g):
    fig, ax = grid()
    for i, t in enumerate(TASKS):
        for j, pe in enumerate(PES):
            a = ax[i][j]; lads = g.get((t, pe, 1))
            if not lads:
                continue
            # pick the layer whose raw variance collapses most (matches Table 1's "most-collapsing layer")
            Lmax = max(max(lad) for lad in lads)
            nL = len(lads[0][Lmax]["var"])
            def ratio(layer):
                _, m, *_ = curve(lads, lambda r: r["var"][layer])
                return m[-1] / m[0]
            layer = min(range(nL), key=ratio)
            x, pre, *_ = curve(lads, lambda r: r["var"][layer])
            _, post, *_ = curve(lads, lambda r: r["var_post"][layer])
            a.plot(x, pre / pre[0], "-", color=BLUE, lw=2, label="before the remedy")
            a.plot(x, post / post[0], "--", color=RED, lw=2, label="after the remedy")
            a.axhline(1.0, color="gray", ls=":", lw=1); a.set_xscale("log"); a.grid(alpha=0.25)
            panel_title(a, t, pe); a.set_xlabel("sequence length (log)"); a.set_ylabel("variance (norm. to train)")
            if i == 0 and j == 0:
                a.legend(fontsize=9, loc="upper right")
    fig.suptitle("The remedy holds the downstream attention-output variance constant across length", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(f"{OUT}/fig_prepost_var.pdf"); fig.savefig(f"{OUT}/fig_prepost_var.png", dpi=150)
    print("wrote fig_prepost_var")


def fig_attn_len(g):
    fig, ax = grid()
    for i, t in enumerate(TASKS):
        for j, pe in enumerate(PES):
            a = ax[i][j]; lads = g.get((t, pe, 0))
            if not lads:
                continue
            x, m, lo, hi = curve(lads, lambda r: max(r["attn_tgt"]))
            _, acc, *_ = curve(lads, lambda r: r["tok"])
            a.plot(x, m, "-o", ms=3, color=BLUE, label="attention on correct source")
            a.fill_between(x, lo, hi, color=BLUE, alpha=0.15)
            a.plot(x, acc, "--", color="gray", lw=1.5, label="per-token accuracy")
            a.set_xscale("log"); a.set_ylim(0, 1.03); a.grid(alpha=0.25)
            panel_title(a, t, pe); a.set_xlabel("sequence length (log)")
            if i == 0 and j == 0:
                a.legend(fontsize=8, loc="lower left")
    fig.suptitle("Attention on the correct source collapses with length, and accuracy follows it (baseline)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(f"{OUT}/fig_attn_vs_length.pdf"); fig.savefig(f"{OUT}/fig_attn_vs_length.png", dpi=150)
    print("wrote fig_attn_vs_length")


def fig_benefit(g):
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for k, t in enumerate(TASKS):
        a = ax[k]
        for pe, col in zip(PES, (BLUE, RED)):
            b, f = g.get((t, pe, 0)), g.get((t, pe, 1))
            if not b or not f:
                continue
            xb, mb, *_ = curve(b, lambda r: r["tok"]); xf, mf, *_ = curve(f, lambda r: r["tok"])
            a.plot(xb, mf - mb, "-o", ms=3, color=col, label=pe.upper())
        a.axhline(0.0, color="gray", ls=":", lw=1); a.set_xscale("log"); a.grid(alpha=0.25)
        a.set_title(t, fontsize=11); a.set_xlabel("sequence length (log)"); a.set_ylabel("remedy benefit (per-token)")
        a.legend(fontsize=9)
    fig.suptitle("The remedy's benefit is at most zero and worsens with length, most under RoPE", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(f"{OUT}/fig_benefit_vs_length.pdf"); fig.savefig(f"{OUT}/fig_benefit_vs_length.png", dpi=150)
    print("wrote fig_benefit_vs_length")


def fig_attn_base_vs_fix(g):
    fig, ax = grid()
    for i, t in enumerate(TASKS):
        for j, pe in enumerate(PES):
            a = ax[i][j]; b, f = g.get((t, pe, 0)), g.get((t, pe, 1))
            if not b or not f:
                continue
            xb, mb, *_ = curve(b, lambda r: max(r["attn_tgt"])); xf, mf, *_ = curve(f, lambda r: max(r["attn_tgt"]))
            a.plot(xb, mb, "-", color=BLUE, lw=2, label="baseline")
            a.plot(xf, mf, "--", color=RED, lw=2, label="with remedy")
            a.set_xscale("log"); a.set_ylim(0, 1.03); a.grid(alpha=0.25)
            panel_title(a, t, pe); a.set_xlabel("sequence length (log)"); a.set_ylabel("attention on correct source")
            if i == 0 and j == 0:
                a.legend(fontsize=9, loc="upper right")
    fig.suptitle("The remedy lowers attention on the correct source, most under RoPE", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(f"{OUT}/fig_attn_base_vs_fix.pdf"); fig.savefig(f"{OUT}/fig_attn_base_vs_fix.png", dpi=150)
    print("wrote fig_attn_base_vs_fix")


def main(path):
    g = load(path)
    fig_prepost(g); fig_attn_len(g); fig_benefit(g); fig_attn_base_vs_fix(g)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/gpu_resultsA.json")
