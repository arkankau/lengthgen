"""Analyze the pre-registered 2x2 length-generalization experiment.

Reads results/lengthgen/lg_{pe}_ln{0,1}_s{seed}.csv (columns:
pe, post_attn_ln, length, exact_match, attn_var_L0, attn_var_L1) and tests the three
pre-registered hypotheses from results/lengthgen_preregistration.md:

  H1: post_attn_ln improves extrapolation accuracy at 2x/3x vs no-LN, within a PE.
  H2: the improvement is PE-dependent (interaction).
  H3: extrapolation accuracy tracks attention-output variance stability across length.

Aggregates across seeds (mean +/- range). Prints a summary table and a verdict against the
pre-registered interpretation, and writes results/lengthgen_analysis.md.
"""
from __future__ import annotations

import csv
import glob
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LGDIR = ROOT / "results" / "lengthgen"
L_TRAIN = 5  # keep in sync with the runner


def load(task: str) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(str(LGDIR / f"lg_{task}_*_s*.csv"))):
        m = re.search(rf"lg_{task}_(nope|rope|learned)_ln(\d)_s(\d+)\.csv", Path(path).name)
        if not m:
            continue
        pe, ln, seed = m.group(1), int(m.group(2)), int(m.group(3))
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "pe": pe, "ln": ln, "seed": seed,
                    "length": int(r["length"]),
                    "acc": float(r["exact_match"]),
                    "var0": float(r.get("attn_var_L0", "nan")),
                    "var1": float(r.get("attn_var_L1", "nan")),
                })
    return rows


def agg_acc(rows, pe, ln, length):
    vals = [r["acc"] for r in rows if r["pe"] == pe and r["ln"] == ln and r["length"] == length]
    if not vals:
        return None
    return sum(vals) / len(vals), min(vals), max(vals), len(vals)


def var_stability(rows, pe, ln):
    """Ratio of layer-0 attn-out variance at 3x length vs at train length (1.0 = no collapse)."""
    def mean_var(length, layer):
        vals = [r[layer] for r in rows if r["pe"] == pe and r["ln"] == ln and r["length"] == length]
        return sum(vals) / len(vals) if vals else float("nan")
    out = {}
    for layer in ("var0", "var1"):
        v_tr = mean_var(L_TRAIN, layer)
        v_3x = mean_var(3 * L_TRAIN, layer)
        out[layer] = (v_tr, v_3x, (v_3x / v_tr if v_tr and v_tr == v_tr else float("nan")))
    return out


def analyze_task(task: str, out: list) -> dict:
    rows = load(task)
    if not rows:
        out.append(f"# {task}: no result CSVs found")
        return {}
    pes = ["nope", "rope"]
    lns = [0, 1]
    lengths = {"train(1x)": L_TRAIN, "2x": 2 * L_TRAIN, "3x": 3 * L_TRAIN}

    out.append(f"# Task: {task}")
    out.append("")
    out.append("Accuracy = mean exact-match across seeds [min,max]. Extrapolation = 2x/3x length.")
    out.append("")
    out.append("| PE | post_attn_ln | " + " | ".join(lengths) + " |")
    out.append("|---|---|" + "|".join(["---"] * len(lengths)) + "|")
    acc = {}
    for pe in pes:
        for ln in lns:
            cells = []
            for name, L in lengths.items():
                a = agg_acc(rows, pe, ln, L)
                acc[(pe, ln, name)] = a[0] if a else None
                cells.append(f"{a[0]:.2f} [{a[1]:.2f},{a[2]:.2f}]" if a else "-")
            out.append(f"| {pe} | {ln} | " + " | ".join(cells) + " |")
    out.append("")

    # --- H1: within each PE, does post-LN help 2x and 3x? ---
    out.append("## H1: does post-attention LayerNorm improve extrapolation? (within PE)")
    h1 = {}
    for pe in pes:
        for name in ("2x", "3x"):
            a0, a1 = acc.get((pe, 0, name)), acc.get((pe, 1, name))
            if a0 is None or a1 is None:
                continue
            delta = a1 - a0
            h1[(pe, name)] = delta
            out.append(f"- {pe} {name}: no-LN={a0:.2f} -> LN={a1:.2f}  (delta {delta:+.2f})")
    out.append("")

    # --- H2: interaction (is the LN benefit PE-dependent?) ---
    out.append("## H2: is the LayerNorm benefit PE-dependent? (interaction)")
    for name in ("2x", "3x"):
        d_nope = h1.get(("nope", name))
        d_rope = h1.get(("rope", name))
        if d_nope is None or d_rope is None:
            continue
        out.append(f"- {name}: LN-benefit(nope)={d_nope:+.2f} vs LN-benefit(rope)={d_rope:+.2f} "
                   f"-> interaction gap {d_nope - d_rope:+.2f}")
    out.append("")

    # --- H3: does extrapolation track variance stability? ---
    out.append("## H3: does extrapolation accuracy track attention-output variance stability?")
    out.append("(variance-stability = layer-0 attn-out var at 3x / at train length; 1.0 = no collapse)")
    for pe in pes:
        for ln in lns:
            vs = var_stability(rows, pe, ln)
            a3 = acc.get((pe, ln, "3x"))
            v0 = vs["var0"]
            out.append(f"- {pe} ln{ln}: 3x-acc={a3:.2f} | L0 var {v0[0]:.3f}->{v0[1]:.3f} "
                       f"(stability {v0[2]:.2f})")
    out.append("")

    # --- verdict ---
    out.append("## Verdict (pre-registered interpretation)")
    helps = {pe: (h1.get((pe, "2x"), 0) + h1.get((pe, "3x"), 0)) / 2 for pe in pes}
    thr = 0.05  # a cell must gain >5 pts averaged over 2x/3x to count as "helped"
    # only count a PE as informative if its train-length acc (no-LN) is >= 0.8
    train_ok = {pe: (acc.get((pe, 0, "train(1x)")) or 0) >= 0.8 for pe in pes}
    helped = {pe: (helps[pe] > thr and train_ok[pe]) for pe in pes}
    if helped["nope"] and helped["rope"]:
        verdict = "OUTCOME 1: fix helps BOTH PEs."
    elif helped["nope"] != helped["rope"]:
        which = "nope" if helped["nope"] else "rope"
        verdict = f"OUTCOME 2: fix helps ONLY {which} -> PE x variance INTERACTION (cf. 2404.12224)."
    else:
        verdict = "OUTCOME 3: fix helps NEITHER informative PE."
    for pe in pes:
        flag = "" if train_ok[pe] else "  (UNINFORMATIVE: train acc < 0.8)"
        out.append(f"- {pe}: mean LN benefit over {{2x,3x}} = {helps[pe]:+.2f}{flag}")
    out.append(f"- **{verdict}**")
    out.append("")
    return {"task": task, "helps": helps, "train_ok": train_ok, "helped": helped}


def main():
    out = []
    summ = {}
    for task in ("addition", "recall"):
        res = analyze_task(task, out)
        if res:
            summ[task] = res
        out.append("")

    # --- cross-task contrast (the contribution) ---
    out.append("# Cross-task contrast: is the variance fix's benefit task-type-dependent?")
    if "addition" in summ and "recall" in summ:
        def best_help(res):  # largest LN benefit among informative PEs
            vals = [res["helps"][pe] for pe in res["helps"] if res["train_ok"][pe]]
            return max(vals) if vals else float("nan")
        add_h, rec_h = best_help(summ["addition"]), best_help(summ["recall"])
        out.append(f"- addition (order-DEPENDENT): best LN benefit among informative PEs = {add_h:+.2f}")
        out.append(f"- recall  (order-INVARIANT): best LN benefit among informative PEs = {rec_h:+.2f}")
        rec_helps = rec_h == rec_h and rec_h > 0.05
        add_helps = add_h == add_h and add_h > 0.05
        if rec_helps and not add_helps:
            out.append("- **CONTRAST CONFIRMED: post-LN rescues length-gen on the order-INVARIANT task "
                       "(reproducing 2504.02827, positive control valid) but NOT on the order-DEPENDENT "
                       "task -> variance collapse is not the binding constraint when position is load-bearing.**")
        elif rec_helps and add_helps:
            out.append("- Both improve -> the variance fix transfers to order-dependent tasks too (stronger "
                       "positive than the source paper claims).")
        elif not rec_helps:
            out.append("- **POSITIVE CONTROL FAILED: post-LN does not rescue even the order-invariant task in "
                       "this harness -> the harness cannot reproduce 2504.02827; the addition null is about "
                       "the setup, not the science. Do NOT publish the contrast.**")
    else:
        out.append("- (waiting on both tasks' CSVs)")
    out.append("")

    text = "\n".join(out) + "\n"
    (ROOT / "results" / "lengthgen_analysis.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
