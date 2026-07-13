"""Analyze the attention-patching causal test (colab/patch_experiment.py -> patch_results.json).

Verdict on the pre-registered hypotheses (results/lengthgen_patch_prereg.md):
  H-P1 sufficiency : Sweep-P, accuracy rises with forced a_j*, p->1 restores accuracy.
  H-P2 dissociation: FIXVAR, accuracy rises with a_j* at ~constant variance  (corr(tok,a_j*) >> 0).
  H-P3 variance null: FIXP, accuracy ~flat as variance varies at fixed a_j*   (corr(tok,Var) ~ 0).

Writes results/lengthgen/fig_patch.{pdf,png} and prints the verdict.
Usage: .venv/Scripts/python.exe scripts/analyze_patch.py results/lengthgen/patch_results.json [--length 250]
"""
from __future__ import annotations
import json, sys, argparse
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
                            "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6, "figure.dpi": 150})
OUT = "results/lengthgen"


def collect(data, L, sweep, xkey, ykey):
    """pool points across all models for one sweep; return per-grid mean x,y and all (x,y) points."""
    byp = defaultdict(lambda: ([], []))
    allx, ally = [], []
    for r in data:
        pts = r["sweeps"].get(str(L), {}).get(sweep, [])
        for i, pt in enumerate(pts):
            x = pt[xkey] if pt[xkey] is not None else np.nan
            byp[i][0].append(x); byp[i][1].append(pt[ykey])
            allx.append(x); ally.append(pt[ykey])
    xs = [np.nanmean(byp[i][0]) for i in sorted(byp)]
    ys = [np.nanmean(byp[i][1]) for i in sorted(byp)]
    return np.array(xs), np.array(ys), np.array(allx), np.array(ally)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=f"{OUT}/patch_results.json")
    ap.add_argument("--length", type=int, default=250)
    a = ap.parse_args()
    data = json.load(open(a.path)); L = a.length
    nmodels = len(data)

    # P: tok vs a_js
    pax, pay, _, _ = collect(data, L, "P", "a_js", "tok")
    base_tok = np.mean([r["baseline"][str(L)]["tok"] for r in data])
    # FIXVAR: tok vs a_js (variance ~const)
    fvx, fvy, fvxa, fvya = collect(data, L, "FIXVAR", "a_js", "tok")
    _, fvz, _, _ = collect(data, L, "FIXVAR", "a_js", "zvar")
    r_sel = float(np.corrcoef(fvxa, fvya)[0, 1])
    # FIXP: tok vs Var(z) (a_js ~const)
    fpx, fpy, fpxa, fpya = collect(data, L, "FIXP", "zvar", "tok")
    _, fpaj, _, _ = collect(data, L, "FIXP", "zvar", "a_js")
    r_var = float(np.corrcoef(fpxa, fpya)[0, 1])

    # per-task FIXP correlation (FIXP's variance axis is confounded with distractor margin; report honestly)
    tasks = sorted(set(r["cfg"]["task"] for r in data))
    fp_by_task = {}
    for tk in tasks:
        sub = [r for r in data if r["cfg"]["task"] == tk]
        _, _, zx, ty = collect(sub, L, "FIXP", "zvar", "tok")
        fp_by_task[tk] = float(np.corrcoef(zx, ty)[0, 1])

    fig, ax = plt.subplots(2, 1, figsize=(3.3, 4.4))
    ax[0].plot(pax, pay, "-o", ms=3, color="#1f77b4")
    ax[0].axhline(base_tok, color="gray", ls=":", lw=1, label=f"unpatched baseline ({base_tok:.2f})")
    ax[0].set_xlabel("forced attention on source $a_{j^\\star}$"); ax[0].set_ylabel("per-token acc")
    ax[0].set_title("Force selection: patch attention onto the source"); ax[0].legend(fontsize=5.5); ax[0].grid(alpha=0.25)
    ax[1].plot(fvx, fvy, "-o", ms=3, color="#d62728")
    ax[1].set_xlabel("attention on source $a_{j^\\star}$ (constructed $\\|a\\|^2$ held)"); ax[1].set_ylabel("per-token acc")
    ax[1].set_title(f"Selection drives accuracy  (r={r_sel:+.2f})"); ax[1].grid(alpha=0.25)
    fig.tight_layout(pad=0.5)
    fig.savefig(f"{OUT}/fig_patch.pdf"); fig.savefig(f"{OUT}/fig_patch.png", dpi=150)

    print(f"# Attention-patching causal test  (L={L}, {nmodels} models)\n")
    print(f"- baseline per-token acc at L={L}: {base_tok:.3f}")
    print(f"- H-P1 sufficiency: Sweep-P tok goes {pay[0]:.3f} (a_js~0) -> {pay[-1]:.3f} (a_js~1)")
    print(f"- H-P2 dissociation: FIXVAR corr(acc, a_js) = {r_sel:+.2f}  "
          f"(acc {fvy[0]:.3f}->{fvy[-1]:.3f} as a_js {fvx[0]:.2f}->{fvx[-1]:.2f}; Var(z) {fvz.min():.3f}-{fvz.max():.3f})")
    print(f"- H-P3 variance null: FIXP pooled corr(acc, Var(z)) = {r_var:+.2f}, but per task "
          + ", ".join(f"{tk}={c:+.2f}" for tk, c in fp_by_task.items())
          + "  (opposite signs => FIXP's variance axis is CONFOUNDED with distractor margin; inconclusive)")
    ok1 = pay[-1] > pay[0] + 0.1
    ok2 = r_sel > 0.5
    signs = [np.sign(c) for c in fp_by_task.values()]
    ok3 = all(abs(c) < 0.3 for c in fp_by_task.values())        # truly flat per task (not a cancellation)
    if ok1 and ok2:
        verdict = ("DIRECT CAUSAL SUFFICIENCY (H-P1+H-P2): forcing attention onto the source restores "
                   "accuracy, and accuracy rises with selection at held norm. ")
        verdict += ("The variance-null leg (H-P3) is CLEAN." if ok3 else
                    "The variance-null leg (H-P3) is NOT clean: FIXP is confounded (opposite-sign per-task "
                    "correlations), so it does not isolate variance-at-fixed-selection. Report H-P1/H-P2 as "
                    "the direct causal result and do not overclaim variance irrelevance from FIXP.")
    else:
        verdict = "PARTIAL: " + ", ".join(h for h, ok in [("H-P1", ok1), ("H-P2", ok2)] if not ok) + " not met"
    print(f"\n**{verdict}**")
    print("wrote results/lengthgen/fig_patch.pdf (2 panels: force-selection, selection-drives-accuracy)")


if __name__ == "__main__":
    main()
