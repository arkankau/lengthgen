"""Analyze the GPU length-gen results (colab/length_gen_colab.py output: lengthgen_results.json).

Per (task, pe, fix), averaged over seeds: per-token accuracy across the length ladder, and the
attention-output variance collapse in the most-collapsing layer -- reported both BEFORE the fix (var,
the raw collapse) and AFTER the fix (var_post; should be ~1.0 if the fix stabilizes variance as
intended). The fix's benefit is a PAIRED per-seed difference at the length where the no-fix baseline
breaks, reported as mean [min,max] with the sign-consistency across seeds.

Usage: python scripts/analyze_lengthgen_json.py <path-to-lengthgen_results.json>
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np

ORDER = {"addition": "dependent", "flagret": "invariant", "recall": "invariant", "argmax": "invariant"}


def main(path):
    data = json.load(open(path))
    L = data[0]["cfg"]["l_train"]
    mults = [1, 2, 3, 10, 20, 50]
    names = [(f"{m}x", m * L) for m in mults]

    # index by (task, pe, fix, seed) -> {length: row}
    idx = {}
    for r in data:
        c = r["cfg"]
        idx[(c["task"], c["pe"], int(c["post_attn_ln"]), c["seed"])] = {row["length"]: row for row in r["ladder"]}
    seeds_of = defaultdict(set)
    for (t, pe, fx, sd) in idx:
        seeds_of[(t, pe, fx)].add(sd)

    def mean_over_seeds(task, pe, fx, Lv, key):
        vals = [idx[(task, pe, fx, sd)][Lv][key] for sd in seeds_of[(task, pe, fx)]
                if Lv in idx[(task, pe, fx, sd)]]
        return float(np.mean(vals)) if vals else float("nan")

    def collapse(task, pe, fx, key):
        """min-over-layers ratio var@longest / var@train, averaged over seeds.
        Falls back to 'var' if the requested key (e.g. var_post) is absent (older records)."""
        longest = max(v for _, v in names)
        rs = []
        for sd in seeds_of[(task, pe, fx)]:
            lad = idx[(task, pe, fx, sd)]
            if L in lad and longest in lad:
                k = key if key in lad[L] else "var"
                vt, vl = np.array(lad[L][k]), np.array(lad[longest][k])
                good = vt > 1e-9
                if good.any():
                    rs.append(float(np.min(vl[good] / vt[good])))
        return float(np.mean(rs)) if rs else float("nan")

    def paired_benefit(task, pe, at_len):
        """per-seed tok(fix on) - tok(fix off) at at_len; returns (mean, lo, hi, n_neg, n)."""
        diffs = []
        common = seeds_of[(task, pe, 0)] & seeds_of[(task, pe, 1)]
        for sd in common:
            l0, l1 = idx[(task, pe, 0, sd)], idx[(task, pe, 1, sd)]
            if at_len in l0 and at_len in l1:
                diffs.append(l1[at_len]["tok"] - l0[at_len]["tok"])
        if not diffs:
            return None
        d = np.array(diffs)
        return float(d.mean()), float(d.min()), float(d.max()), int((d < 0).sum()), len(d)

    tasks = sorted({t for (t, _, _, _) in idx}, key=lambda t: ORDER.get(t, "z"))
    out = ["# Length-Gen GPU Analysis", "",
           "Per-token accuracy (mean over seeds). var-collapse = min-layer ratio var@longest/var@train:",
           "`pre` = before the fix (raw collapse); `post` = after the fix (want ~1.0 => fix stabilizes it).",
           "Benefit = PAIRED per-seed tok(fix)-tok(no-fix) at the length where the no-fix baseline breaks.", ""]
    longest = max(v for _, v in names)
    task_benefit = {}
    for task in tasks:
        out.append(f"## {task} ({ORDER.get(task,'?')}-order)")
        out.append("| PE | fix | " + " | ".join(nm for nm, _ in names) + " | em@1x | var-collapse(pre/post) |")
        out.append("|---|---|" + "|".join("---" for _ in names) + "|---|---|")
        best = None
        for pe in ("nope", "rope"):
            if (task, pe, 0) not in {(t, p, f) for (t, p, f) in seeds_of}:
                continue
            for fx in (0, 1):
                toks = [mean_over_seeds(task, pe, fx, Lv, "tok") for _, Lv in names]
                pre = collapse(task, pe, fx, "var")
                post = collapse(task, pe, fx, "var_post")
                em1 = mean_over_seeds(task, pe, fx, L, "em")
                out.append(f"| {pe} | {'on' if fx else 'off'} | "
                           + " | ".join(f"{t:.2f}" for t in toks)
                           + f" | {em1:.2f} | {pre:.2f} / {post:.2f} |")
            mastered = mean_over_seeds(task, pe, 0, L, "em") >= 0.8
            # length where the no-fix baseline breaks (tok<0.9), farthest
            broke = [Lv for nm, Lv in names if nm != "1x" and mean_over_seeds(task, pe, 0, Lv, "tok") < 0.9]
            if not mastered:
                out.append(f"- {pe}: UNINFORMATIVE (train-len em < 0.8)")
            elif not broke:
                out.append(f"- {pe}: baseline never breaks to {longest}x -> can't test the fix")
            else:
                pb = paired_benefit(task, pe, broke[-1])
                if pb:
                    mean, lo, hi, nneg, n = pb
                    best = mean if best is None else max(best, mean)
                    out.append(f"- {pe}: post-LN benefit at {broke[-1]//L}x = **{mean:+.3f}** "
                               f"[{lo:+.3f}, {hi:+.3f}], {nneg}/{n} seeds negative")
        task_benefit[task] = best
        out.append("")

    out.append("## Verdict")
    inv = [t for t in tasks if ORDER.get(t) == "invariant" and task_benefit.get(t) is not None]
    inv_best = max((task_benefit[t] for t in inv), default=None)
    for t in tasks:
        b = task_benefit.get(t)
        out.append(f"- {t} ({ORDER.get(t)}): best post-LN benefit where baseline breaks = "
                   f"{'n/a' if b is None else round(b,3)}")
    if inv_best is not None and inv_best <= 0.05:
        out.append("\n**GENUINE NULL: across order-invariant tasks the fix stabilizes downstream variance "
                   "(post-collapse ~1.0) yet yields no length-gen benefit (best "
                   f"{inv_best:+.3f}); harmful under RoPE. Variance stabilization is decoupled from length "
                   "generalization -> scopes/contests 2504.02827.**")
    elif inv_best is not None:
        out.append(f"\n**post-LN HELPS order-invariant (best {inv_best:+.3f}) -> reproduces 2504.02827; "
                   "check addition for the contrast.**")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/gpu_results.json")
