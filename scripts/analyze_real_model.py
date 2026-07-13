"""Analyze the real-model probe (colab/real_model_probe.py -> realmodel_results.json).

Two questions (results/lengthgen_realmodel_prereg.md):
  H-R1: do accuracy AND attention-on-source both fall as the context length N grows?
  H-R2: does attention-on-source predict which examples are correct WITHIN a fixed length, and better than
        the ||a||^2 variance proxy / attention entropy? (within-length controls for the shared decline with N)

Writes results/lengthgen/fig_realmodel.{pdf,png} and prints the verdict.
Usage: .venv/Scripts/python.exe scripts/analyze_real_model.py results/lengthgen/realmodel_results.json
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
                            "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6, "figure.dpi": 150})
OUT = "results/lengthgen"


def pb(x, y):  # point-biserial / pearson, guarding zero variance
    return float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 1e-9 and np.std(y) > 1e-9 else float("nan")


def within_length_mean(recs, key):
    byN = defaultdict(list)
    for r in recs:
        byN[r["N"]].append(r)
    rs = []
    for N, rr in byN.items():
        c = np.array([x["correct"] for x in rr], float)
        v = np.array([x[key] for x in rr], float)
        r = pb(v, c)
        if not np.isnan(r):
            rs.append(r)
    return float(np.mean(rs)) if rs else float("nan"), len(rs)


def main(path):
    d = json.load(open(path)); recs = d["records"]; model = d.get("model", "?")
    Ns = sorted(set(r["N"] for r in recs))
    acc = [np.mean([x["correct"] for x in recs if x["N"] == N]) for N in Ns]
    ajs = [np.mean([x["a_js"] for x in recs if x["N"] == N]) for N in Ns]

    # within-length predictive correlations (controls for the shared decline with N)
    r_attn, k = within_length_mean(recs, "a_js")
    r_var, _ = within_length_mean(recs, "normsq")
    r_ent, _ = within_length_mean(recs, "entropy")
    # pooled, for reference
    A = np.array([x["a_js"] for x in recs]); C = np.array([x["correct"] for x in recs], float)

    # accuracy vs attention-on-source, binned (all examples)
    bins = np.linspace(0, 1, 9)
    idx = np.digitize(A, bins) - 1
    bx, by = [], []
    for b in range(len(bins) - 1):
        m = idx == b
        if m.sum() >= 10:
            bx.append((bins[b] + bins[b + 1]) / 2); by.append(C[m].mean())

    fig, ax = plt.subplots(2, 1, figsize=(3.3, 4.4))
    ax[0].plot(Ns, acc, "-o", ms=3, color="#1f77b4", label="accuracy")
    ax[0].plot(Ns, ajs, "--s", ms=3, color="#d62728", label="attention on source")
    ax[0].set_xscale("log"); ax[0].set_ylim(0, 1.03); ax[0].grid(alpha=0.25)
    ax[0].set_xlabel("context length $N$ (pairs, log)"); ax[0].set_ylabel("value")
    ax[0].set_title("Both fall with context length"); ax[0].legend()
    ax[1].plot(bx, by, "-o", ms=3, color="#1f77b4")
    ax[1].set_xlabel("attention on correct source"); ax[1].set_ylabel("P(correct)")
    ax[1].set_title(f"Accuracy rises with attention on source"); ax[1].grid(alpha=0.25)
    fig.tight_layout(pad=0.5)
    fig.savefig(f"{OUT}/fig_realmodel.pdf"); fig.savefig(f"{OUT}/fig_realmodel.png", dpi=150)

    print(f"# Real-model probe: {model}  ({len(recs)} examples, N in {Ns})\n")
    print("- accuracy by N: " + ", ".join(f"{N}:{a:.2f}" for N, a in zip(Ns, acc)))
    print("- attention-on-source by N: " + ", ".join(f"{N}:{a:.2f}" for N, a in zip(Ns, ajs)))
    print(f"- H-R1 (co-decline): accuracy {acc[0]:.2f}->{acc[-1]:.2f}, attention-on-source {ajs[0]:.2f}->{ajs[-1]:.2f}")
    print(f"- H-R2 WITHIN-length corr(correct, .) averaged over {k} lengths:")
    print(f"    attention-on-source = {r_attn:+.3f}   ||a||^2 variance proxy = {r_var:+.3f}   -entropy = {-r_ent:+.3f}")
    print(f"  (pooled corr(acc, attn-on-source) = {pb(A, C):+.3f}, inflated by the shared decline with N)")
    ok1 = acc[0] - acc[-1] > 0.1 and ajs[0] - ajs[-1] > 0.05
    ok2 = (r_attn > 0.1) and (r_attn > abs(r_var)) and (r_attn > abs(r_ent))
    print("\n**" + ("GENERALIZES: in a real LM, retrieval accuracy and attention-on-source co-decline with "
                    "context, and attention-on-source is the best within-length predictor of correctness."
                    if (ok1 and ok2) else
                    "PARTIAL / see numbers -- report honestly (need a model with dynamic range; check acc spans a range).") + "**")
    print("wrote results/lengthgen/fig_realmodel.pdf")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else f"{OUT}/realmodel_results.json")
