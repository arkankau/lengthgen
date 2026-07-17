"""All paper figures at SINGLE-COLUMN size so they flow inline with the two-column text
(no wide figure* floats that bunch at page tops).

Target width ~3.3in = \\columnwidth; fonts tuned so a 1:1 include stays legible.

Reads:
  results/lengthgen/gpu_results.json   (40 cfgs incl addition; length/em/tok/var) -> variance_collapse, accuracy
  results/lengthgen/gpu_resultsA.json  (argmax/flagret, 4 seeds; + var_post/attn_tgt) -> prepost, attn, benefit, causal, attn_fix

Usage: .venv/Scripts/python.exe scripts/make_lengthgen_paper_figures.py
"""
from __future__ import annotations
import json
import shutil
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({
    "font.size": 11.2, "axes.titlesize": 11.5, "axes.labelsize": 11.2,
    "xtick.labelsize": 10.8, "ytick.labelsize": 10.8, "legend.fontsize": 10.8,
    "lines.linewidth": 1.3, "figure.dpi": 150,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})

OUT = "results/lengthgen"
PAPER = Path("paper_lengthgen_aaai/figures")
PAPER.mkdir(parents=True, exist_ok=True)
MAIN = f"{OUT}/gpu_results.json"
A = f"{OUT}/gpu_resultsA.json"
TASKS = ["argmax", "flagret"]
PES = ["nope", "rope"]
TCOL = {"argmax": "#1f77b4", "flagret": "#d62728", "addition": "#2ca02c"}
BLUE, RED = "#1f77b4", "#d62728"
CW = 7.0


def load(path, tasks):
    g = defaultdict(list)  # (task, pe, fix) -> list over seeds of {length: row}
    for r in json.load(open(path)):
        c = r["cfg"]
        if c["task"] in tasks and c.get("attn_scale", "none") == "none":
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


def collapse_layer(lads):
    """index of the raw-variance layer that collapses most from train to max length."""
    Lmax = max(max(lad) for lad in lads); nL = len(lads[0][Lmax]["var"])
    def ratio(k):
        _, m, *_ = curve(lads, lambda r: r["var"][k]); return m[-1] / m[0]
    return min(range(nL), key=ratio)


def finish(fig, name):
    fig.tight_layout(pad=0.4)
    pdf = Path(OUT) / f"{name}.pdf"
    png = Path(OUT) / f"{name}.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=600)
    shutil.copy2(pdf, PAPER / pdf.name)
    shutil.copy2(png, PAPER / png.name)
    plt.close(fig); print("wrote", name)


# ---- 1. variance collapse (baseline), one panel, 4 retrieval lines ----------
def fig_variance_collapse(gm):
    fig, a = plt.subplots(figsize=(CW, 3.2))
    for t in TASKS:
        for pe in PES:
            lads = gm.get((t, pe, 0))
            if not lads:
                continue
            k = collapse_layer(lads); x, m, *_ = curve(lads, lambda r: r["var"][k])
            a.plot(x, m / m[0], "-" if pe == "nope" else "--", color=TCOL[t], label=f"{t}·{pe.upper()}")
    a.axhline(1.0, color="gray", ls=":", lw=0.8); a.set_xscale("log"); a.grid(alpha=0.25)
    a.set_ylim(0, 1.05); a.set_xlabel("sequence length (log)"); a.set_ylabel("variance (norm. to train)")
    a.legend(ncol=2, loc="lower left")
    finish(fig, "fig_variance_collapse")


# ---- 2. pre/post variance (remedy on), 2x2 -------------------------------------
def fig_prepost(ga):
    fig, ax = plt.subplots(2, 2, figsize=(CW, 5.2), sharex=True)
    for i, t in enumerate(TASKS):
        for j, pe in enumerate(PES):
            a = ax[i][j]; lads = ga.get((t, pe, 1))
            if not lads:
                continue
            k = collapse_layer(lads)
            x, pre, *_ = curve(lads, lambda r: r["var"][k]); _, post, *_ = curve(lads, lambda r: r["var_post"][k])
            a.plot(x, pre / pre[0], "-", color=BLUE, label="before")
            a.plot(x, post / post[0], "--", color=RED, label="after")
            a.axhline(1.0, color="gray", ls=":", lw=0.8); a.set_xscale("log"); a.grid(alpha=0.25)
            a.set_title(f"{t}·{pe.upper()}")
            if i == 1:
                a.set_xlabel("length")
            if j == 0:
                a.set_ylabel("var/train")
            if i == 0 and j == 0:
                a.legend(loc="lower left")
    finish(fig, "fig_prepost_var")


# ---- 3. accuracy vs length, baseline vs fix, 3x2 (tasks x pe) ------------------
def fig_accuracy(gm):
    tasks = ["argmax", "flagret", "addition"]
    fig, ax = plt.subplots(3, 2, figsize=(CW, 7.0), sharex=True)
    for i, t in enumerate(tasks):
        for j, pe in enumerate(PES):
            a = ax[i][j]; b, f = gm.get((t, pe, 0)), gm.get((t, pe, 1))
            if b:
                x, m, lo, hi = curve(b, lambda r: r["tok"]); a.plot(x, m, "-", color=BLUE, label="baseline"); a.fill_between(x, lo, hi, color=BLUE, alpha=0.15)
            if f:
                x, m, lo, hi = curve(f, lambda r: r["tok"]); a.plot(x, m, "--", color=RED, label="remedy"); a.fill_between(x, lo, hi, color=RED, alpha=0.12)
            a.set_xscale("log"); a.set_ylim(0, 1.05); a.grid(alpha=0.25); a.set_title(f"{t}·{pe.upper()}")
            if i == 2:
                a.set_xlabel("length")
            if j == 0:
                a.set_ylabel("per-token acc")
            if i == 0 and j == 0:
                a.legend(loc="lower left")
    finish(fig, "fig_accuracy_vs_length")


# ---- 4. remedy benefit vs length, one panel, 4 lines --------------------------
def fig_benefit(ga):
    fig, a = plt.subplots(figsize=(CW, 2.4))
    for t in TASKS:
        for pe in PES:
            b, f = ga.get((t, pe, 0)), ga.get((t, pe, 1))
            if not b or not f:
                continue
            xb, mb, *_ = curve(b, lambda r: r["tok"]); _, mf, *_ = curve(f, lambda r: r["tok"])
            a.plot(xb, mf - mb, "-" if pe == "nope" else "--", color=TCOL[t], label=f"{t}·{pe.upper()}")
    a.axhline(0.0, color="gray", ls=":", lw=0.8); a.set_xscale("log"); a.grid(alpha=0.25)
    a.set_xlabel("sequence length (log)"); a.set_ylabel("remedy benefit (per-token)")
    a.legend(ncol=2, loc="lower left")
    finish(fig, "fig_benefit_vs_length")


# ---- 5. attention on source vs length (baseline), 2x2 -------------------------
def fig_attn_len(ga):
    fig, ax = plt.subplots(2, 2, figsize=(CW, 5.2), sharex=True)
    for i, t in enumerate(TASKS):
        for j, pe in enumerate(PES):
            a = ax[i][j]; lads = ga.get((t, pe, 0))
            if not lads:
                continue
            x, m, lo, hi = curve(lads, lambda r: max(r["attn_tgt"])); _, acc, *_ = curve(lads, lambda r: r["tok"])
            a.plot(x, m, "-", color=BLUE, label="attn on source"); a.fill_between(x, lo, hi, color=BLUE, alpha=0.15)
            a.plot(x, acc, "--", color="gray", label="accuracy")
            a.set_xscale("log"); a.set_ylim(0, 1.05); a.grid(alpha=0.25); a.set_title(f"{t}·{pe.upper()}")
            if i == 1:
                a.set_xlabel("length")
            if j == 0:
                a.set_ylabel("fraction")
            if i == 0 and j == 0:
                a.legend(loc="lower left")
    finish(fig, "fig_attn_vs_length")


# ---- 6. causal scatter, 2x1 stacked -------------------------------------------
def fig_causal(ga):
    xs_a, xs_v, ys, cs = [], [], [], []
    for (t, pe, fix), lads in ga.items():
        if fix != 0:
            continue
        k = collapse_layer(lads)
        for lad in lads:
            v0 = lad[min(lad)]["var"][k]
            for L, r in lad.items():
                xs_a.append(max(r["attn_tgt"])); xs_v.append(r["var"][k] / v0); ys.append(r["tok"]); cs.append(TCOL[t])
    xs_a, xs_v, ys = np.array(xs_a), np.array(xs_v), np.array(ys)
    ra = np.corrcoef(xs_a, ys)[0, 1]; rv = np.corrcoef(xs_v, ys)[0, 1]
    fig, ax = plt.subplots(2, 1, figsize=(3.3, 5.0))
    ax[0].scatter(xs_a, ys, s=5, c=cs, alpha=0.5, edgecolors="none")
    ax[0].set_xlabel("attention on correct source"); ax[0].set_ylabel("per-token acc"); ax[0].grid(alpha=0.25)
    ax[0].set_title(f"accuracy vs attention  (r={ra:.2f})")
    ax[1].scatter(xs_v, ys, s=5, c=cs, alpha=0.5, edgecolors="none")
    ax[1].set_xlabel("attention-output variance ratio"); ax[1].set_ylabel("per-token acc"); ax[1].grid(alpha=0.25)
    ax[1].set_title(f"accuracy vs variance  (r={rv:.2f})")
    finish(fig, "fig_causal")
    print(f"  causal r(attn)={ra:.3f} r(var)={rv:.3f}")


# ---- 7. attention on source, baseline vs fix, 2x2 -----------------------------
def fig_attn_fix(ga):
    fig, ax = plt.subplots(2, 2, figsize=(CW, 5.2), sharex=True)
    for i, t in enumerate(TASKS):
        for j, pe in enumerate(PES):
            a = ax[i][j]; b, f = ga.get((t, pe, 0)), ga.get((t, pe, 1))
            if not b or not f:
                continue
            xb, mb, *_ = curve(b, lambda r: max(r["attn_tgt"])); xf, mf, *_ = curve(f, lambda r: max(r["attn_tgt"]))
            a.plot(xb, mb, "-", color=BLUE, label="baseline"); a.plot(xf, mf, "--", color=RED, label="remedy")
            a.set_xscale("log"); a.set_ylim(0, 1.05); a.grid(alpha=0.25); a.set_title(f"{t}·{pe.upper()}")
            if i == 1:
                a.set_xlabel("length")
            if j == 0:
                a.set_ylabel("attn on source")
            if i == 0 and j == 0:
                a.legend(loc="upper right")
    finish(fig, "fig_attn_base_vs_fix")


def main():
    gm = load(MAIN, ["argmax", "flagret", "addition"])
    ga = load(A, TASKS)
    fig_variance_collapse(gm); fig_prepost(ga); fig_accuracy(gm); fig_benefit(ga)
    fig_attn_len(ga); fig_causal(ga); fig_attn_fix(ga)


if __name__ == "__main__":
    main()
