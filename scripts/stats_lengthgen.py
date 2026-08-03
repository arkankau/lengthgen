"""Corrected-inference statistics for the length-gen paper.

(1) Is attention a better predictor than variance ROBUST to the layer-aggregation choice?
    Recompute pooled corr(acc, attn) and corr(acc, var) under max/mean/last-layer aggregation.
    Kills the "you took max-attn-layer but min-variance-layer to favor your story" objection.
(2) Bootstrap 95% CIs + N for the pooled correlations.
(3) Aggregate significance for the variance-fix null: across all order-invariant (cell,seed) pairs,
    the paired benefit at the break point -- mean, bootstrap CI, count<=0, and a two-sided sign test.

Usage: .venv/Scripts/python.exe scripts/stats_lengthgen.py results/lengthgen/gpu_resultsA.json
"""
from __future__ import annotations
import json, sys, math
from collections import defaultdict
import numpy as np

INV = ("argmax", "flagret"); PES = ("nope", "rope")
rng = np.random.default_rng(0)


def load(path):
    g = defaultdict(dict)  # (task,pe,cond,seed) -> {length: row}
    for r in json.load(open(path)):
        c = r["cfg"]; sc = c.get("attn_scale", "none"); ln = int(c["post_attn_ln"])
        cond = "baseline" if (ln == 0 and sc == "none") else "varfix" if (ln == 1 and sc == "none") else None
        if c["task"] in INV and cond:
            g[(c["task"], c["pe"], cond, c["seed"])] = {row["length"]: row for row in r["ladder"]}
    return g


def collapse_layer(lad):  # layer with the largest train->max collapse
    Ls = sorted(lad); nL = len(lad[Ls[0]]["var"])
    return min(range(nL), key=lambda k: lad[Ls[-1]]["var"][k] / lad[Ls[0]]["var"][k])


def points(g, attn_agg, var_agg):
    """Return arrays (acc, attn, varratio) pooled over baseline runs, lengths."""
    A, T, V = [], [], []
    for (t, pe, cond, sd), lad in g.items():
        if cond != "baseline":
            continue
        Ls = sorted(lad); k = collapse_layer(lad)
        for L in Ls:
            r = lad[L]
            T.append(r["tok"])
            av = r["attn_tgt"]
            A.append(max(av) if attn_agg == "max" else np.mean(av) if attn_agg == "mean" else av[-1])
            vv = r["var"]; v0 = lad[Ls[0]]["var"]
            if var_agg == "collapse":
                V.append(vv[k] / v0[k])
            elif var_agg == "mean":
                V.append(np.mean([vv[i] / v0[i] for i in range(len(vv))]))
            else:
                V.append(vv[-1] / v0[-1])
    return np.array(T), np.array(A), np.array(V)


def boot_r(x, y, n=2000):
    rs = []
    idx = np.arange(len(x))
    for _ in range(n):
        b = rng.choice(idx, len(idx), replace=True)
        rs.append(np.corrcoef(x[b], y[b])[0, 1])
    lo, hi = np.percentile(rs, [2.5, 97.5])
    return float(np.corrcoef(x, y)[0, 1]), float(lo), float(hi)


def break_len(g, t, pe, L0=5):
    seeds = [s for (a, b, c, s) in g if (a, b, c) == (t, pe, "baseline")]
    lad0 = {L: np.mean([g[(t, pe, "baseline", s)][L]["tok"] for s in seeds]) for L in g[(t, pe, "baseline", seeds[0])]}
    broke = [L for L in sorted(lad0) if L > L0 and lad0[L] < 0.9]
    return broke[-1] if broke else max(lad0)


def main(path):
    g = load(path)
    print(f"# {path}\n")
    print("## (1) attention vs variance as predictor -- robustness to layer aggregation")
    print("| attn agg | var agg | corr(acc,attn) [95% CI] | corr(acc,var) [95% CI] | N |")
    print("|---|---|---|---|---|")
    for aa, va in [("max", "collapse"), ("mean", "mean"), ("last", "last")]:
        T, A, V = points(g, aa, va)
        ra = boot_r(A, T); rv = boot_r(V, T)
        print(f"| {aa} | {va} | {ra[0]:+.2f} [{ra[1]:+.2f},{ra[2]:+.2f}] | {rv[0]:+.2f} [{rv[1]:+.2f},{rv[2]:+.2f}] | {len(T)} |")

    print("\n## (2) variance-fix null: paired benefit across order-invariant (cell,seed) pairs")
    benefits = []
    for t in INV:
        for pe in PES:
            L = break_len(g, t, pe)
            common = [s for (a, b, c, s) in g if (a, b, c) == (t, pe, "varfix")]
            for s in common:
                if L in g[(t, pe, "varfix", s)] and L in g[(t, pe, "baseline", s)]:
                    benefits.append(g[(t, pe, "varfix", s)][L]["tok"] - g[(t, pe, "baseline", s)][L]["tok"])
    b = np.array(benefits)
    nn = len(b); neg = int((b <= 0).sum()); pos = int((b > 0).sum())
    # bootstrap CI of the mean
    means = [rng.choice(b, nn, replace=True).mean() for _ in range(5000)]
    lo, hi = np.percentile(means, [2.5, 97.5])
    # two-sided sign test: P(>=neg negatives) under p=0.5
    from math import comb
    k = max(neg, pos)
    p = 2 * sum(comb(nn, i) for i in range(k, nn + 1)) / (2 ** nn)
    p = min(1.0, p)
    print(f"- pairs N={nn}, benefit<=0 in {neg}/{nn}, mean={b.mean():+.3f} [95% CI {lo:+.3f},{hi:+.3f}]")
    print(f"- max benefit = {b.max():+.3f}; two-sided sign test p={p:.4f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/gpu_resultsA.json")
