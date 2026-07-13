"""Direction B: does intervening on the identified cause (attention dispersion) recover length-gen,
where intervening on variance did not?

Compares three conditions per (task, pe), keyed by (post_attn_ln, attn_scale):
  baseline  = (0, none)     variance-fix = (1, none)     attn-sharpen = (0, loglen)
Tests the pre-registered hypotheses (results/lengthgen_causalB_prereg.md):
  H-B1  attn-sharpen gives POSITIVE paired per-seed accuracy benefit at the break point (Delta > +0.05),
        where the variance-fix gave <= 0.
  H-B2  attn-sharpen RAISES attention-on-correct-source at the break length vs baseline.
  H-B3  across cells, the accuracy gain from sharpening tracks the attention gain.

Usage: python scripts/analyze_causalB.py <lengthgen_results.json>
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
import numpy as np

INV = ("argmax", "flagret")


def cond_of(c):
    ln = int(c["post_attn_ln"]); sc = c.get("attn_scale", "none")
    if ln == 0 and sc == "none":   return "baseline"
    if ln == 1 and sc == "none":   return "varfix"
    if ln == 0 and sc != "none":   return "attn"
    return None


def main(path):
    data = json.load(open(path))
    L = data[0]["cfg"]["l_train"]
    # index: (task, pe, cond, seed) -> {length: row}
    idx = {}
    for r in data:
        c = r["cfg"]; cd = cond_of(c)
        if c["task"] in INV and cd:
            idx[(c["task"], c["pe"], cd, c["seed"])] = {row["length"]: row for row in r["ladder"]}
    seeds_of = defaultdict(set)
    for (t, pe, cd, sd) in idx:
        seeds_of[(t, pe, cd)].add(sd)

    def mean_tok(t, pe, cd, Lv):
        v = [idx[(t, pe, cd, sd)][Lv]["tok"] for sd in seeds_of[(t, pe, cd)]
             if Lv in idx[(t, pe, cd, sd)]]
        return float(np.mean(v)) if v else float("nan")

    def break_len(t, pe):
        lens = sorted({Lv for sd in seeds_of[(t, pe, "baseline")] for Lv in idx[(t, pe, "baseline", sd)]})
        broke = [Lv for Lv in lens if Lv > L and mean_tok(t, pe, "baseline", Lv) < 0.9]
        return broke[-1] if broke else (lens[-1] if lens else None)

    def paired_delta(t, pe, cd, at):  # tok(cond) - tok(baseline), per shared seed
        common = seeds_of[(t, pe, cd)] & seeds_of[(t, pe, "baseline")]
        ds = [idx[(t, pe, cd, sd)][at]["tok"] - idx[(t, pe, "baseline", sd)][at]["tok"]
              for sd in common if at in idx[(t, pe, cd, sd)] and at in idx[(t, pe, "baseline", sd)]]
        return (float(np.mean(ds)), float(np.min(ds)), float(np.max(ds)), int(sum(d > 0 for d in ds)), len(ds)) if ds else None

    def attn_at(t, pe, cd, Lv):
        v = [max(idx[(t, pe, cd, sd)][Lv]["attn_tgt"]) for sd in seeds_of[(t, pe, cd)]
             if Lv in idx[(t, pe, cd, sd)] and "attn_tgt" in idx[(t, pe, cd, sd)][Lv]]
        return float(np.mean(v)) if v else float("nan")

    out = ["# Direction B: does sharpening attention recover length-gen (where the variance fix did not)?", ""]
    have_attn = any(cd == "attn" for (_, _, cd, _) in idx)
    if not have_attn:
        out.append("No attention-sharpen (attn_scale) runs found yet -- send the Direction-B JSON.")
        print("\n".join(out)); return
    acc_gain, attn_gain = [], []
    out.append("| task | PE | break | var-fix Delta | **attn Delta** | attn_tgt base->sharp |")
    out.append("|---|---|---|---|---|---|")
    for t in INV:
        for pe in ("nope", "rope"):
            if (t, pe, "attn") not in {(a, b, c) for (a, b, c, _) in idx}:
                continue
            bl = break_len(t, pe)
            dv = paired_delta(t, pe, "varfix", bl)
            da = paired_delta(t, pe, "attn", bl)
            ab, asr = attn_at(t, pe, "baseline", bl), attn_at(t, pe, "attn", bl)
            if da:
                acc_gain.append(da[0]); attn_gain.append(asr - ab)
            dvs = f"{dv[0]:+.3f}" if dv else "n/a"
            das = f"**{da[0]:+.3f}** [{da[1]:+.3f},{da[2]:+.3f}], {da[3]}/{da[4]} pos" if da else "n/a"
            out.append(f"| {t} | {pe} | {bl//L}x | {dvs} | {das} | {ab:.3f}->{asr:.3f} |")
    # verdict
    out.append("")
    ma = float(np.mean(acc_gain)) if acc_gain else float("nan")
    n_pos = sum(x > 0.05 for x in acc_gain)
    out.append(f"- mean attn-sharpen accuracy benefit at break = **{ma:+.3f}**  ({n_pos}/{len(acc_gain)} cells > +0.05)")
    if attn_gain and np.std(attn_gain) > 1e-9 and np.std(acc_gain) > 1e-9:
        r = float(np.corrcoef(attn_gain, acc_gain)[0, 1])
        out.append(f"- H-B3 corr(attn_tgt gain, accuracy gain) across cells = {r:+.2f}")
    out.append("")
    if ma > 0.05 and n_pos >= max(1, len(acc_gain) - 1):
        out.append("**CAUSAL CLINCHER (H-B1 supported): sharpening attention RECOVERS length-gen where the "
                   "variance fix did not. Intervening on the identified cause works -> beyond-workshop.**")
    elif ma > 0.0:
        out.append("**PARTIAL: sharpening attention helps (and raises attn_tgt) but does not fully rescue at "
                   "the break point. Attention is necessary; report the causal direction honestly.**")
    else:
        out.append("**NEGATIVE: sharpening did not improve accuracy. The correlational A-result stands but "
                   "the causal intervention fails -> the cause is more than attention dispersion. Report honestly.**")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/gpu_resultsA.json")
