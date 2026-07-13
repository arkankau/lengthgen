"""Direction A: does attention-on-correct-source (not variance) drive length-gen failure?

For the order-invariant tasks (argmax, flagret) we know the source token holding the answer, so we
measured, per layer at the answer-query position: attn_tgt (mass on the correct source, best head),
attn_ent (normalized entropy), attn_max (sharpness). This tests the pre-registered hypotheses
(results/lengthgen_causal_prereg.md):
  H-A1  attn_tgt tracks per-token accuracy across length (high |corr|).
  H-A2  attn_tgt predicts accuracy BETTER than the variance-collapse ratio does.
  H-A3  the fix does NOT restore attn_tgt at long length (consistent with not restoring accuracy).

Usage: python scripts/analyze_causal.py <lengthgen_results.json>
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np

INV = {"argmax", "flagret", "recall"}


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3 or np.std(a[ok]) < 1e-9 or np.std(b[ok]) < 1e-9:
        return float("nan")
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def main(path):
    data = json.load(open(path))
    L = data[0]["cfg"]["l_train"]
    rows_by = {}
    for r in data:
        c = r["cfg"]
        rows_by[(c["task"], c["pe"], int(c["post_attn_ln"]), c["seed"])] = r["ladder"]

    out = ["# Direction A: attention-on-target vs variance as the driver of length-gen failure", ""]
    tgt_corrs, var_corrs = [], []
    a3 = []  # (attn_tgt off vs on) at longest, to test whether the fix restores attention
    per_cell = []
    for (task, pe, fx, sd), lad in sorted(rows_by.items()):
        if task not in INV or "attn_tgt" not in lad[0]:
            continue
        # informative window: lengths where this cell's tok is meaningful (baseline mastered near train)
        lens = [row["length"] for row in lad]
        tok = [row["tok"] for row in lad]
        # best-layer attention on target; variance-collapse ratio vs train length (min-collapse layer)
        best_tgt = [max(row["attn_tgt"]) for row in lad]
        vt = np.array(lad[0]["var"])  # length-1 row is first
        vr = []
        for row in lad:
            r_ = np.array(row["var"]); good = vt > 1e-9
            vr.append(float(np.min(r_[good] / vt[good])) if good.any() else float("nan"))
        ct, cv = corr(tok, best_tgt), corr(tok, vr)
        if fx == 0:  # correlations reported on baselines (the failure we want to explain)
            tgt_corrs.append(ct); var_corrs.append(cv)
            per_cell.append(f"- {task}/{pe}: corr(acc, attn_tgt)={ct:+.2f}  vs  corr(acc, var-ratio)={cv:+.2f}")
    out.append("## H-A1 / H-A2  (baselines; correlation of accuracy with each candidate across length)")
    out += per_cell
    if tgt_corrs:
        out.append("")
        out.append(f"- pooled mean corr(acc, **attn_tgt**) = {np.nanmean(tgt_corrs):+.2f}")
        out.append(f"- pooled mean corr(acc, variance-ratio) = {np.nanmean(var_corrs):+.2f}")
        better = np.nanmean(tgt_corrs) > np.nanmean(var_corrs)
        out.append(f"- **attn_tgt is the {'better' if better else 'NOT the better'} predictor** "
                   f"(H-A2 {'supported' if better else 'not supported'})")

    # H-A3: does the fix restore attention-on-target at the longest length?
    out.append("\n## H-A3  (does the fix restore attention on the correct source at long length?)")
    for task in ("argmax", "flagret"):
        for pe in ("nope", "rope"):
            seeds = [sd for (t, p, f, sd) in rows_by if t == task and p == pe and f == 0]
            if not seeds:
                continue
            def tgt_at_longest(fx):
                vals = []
                for sd in seeds:
                    lad = rows_by.get((task, pe, fx, sd))
                    if lad and "attn_tgt" in lad[0]:
                        vals.append(max(lad[-1]["attn_tgt"]))
                return float(np.mean(vals)) if vals else float("nan")
            off, on = tgt_at_longest(0), tgt_at_longest(1)
            out.append(f"- {task}/{pe}: attn_tgt@longest  off={off:.3f}  on={on:.3f}  "
                       f"(fix {'restores' if on - off > 0.05 else 'does NOT restore'} attention)")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/gpu_results.json")
