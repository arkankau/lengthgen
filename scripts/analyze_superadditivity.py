"""Direction C: is the fixed-spectrum swap effect superadditive in circuit coverage?

Greedy circuit-discovery methods (ACDC, attribution patching) build circuits from component-wise effects,
which presumes roughly additive or diminishing returns. If the effect is SUPERADDITIVE -- each head worth
more inside a larger circuit than alone -- then a circuit cannot be found by testing its parts, and greedy
selection has no approximation guarantee.

We test this on results/lengthgen/paired_head_count_full_grid.json (16 trained models x lengths x
K in {1,2,4,8} heads patched, paired against the same baseline).

Reported per model-length cell:
  eff(K)      : source-max effect at coverage K
  eff(K)/K    : per-head effect (rising => superadditive)
  eff(2K)/(2 eff(K)) : doubling ratio (>1 => superadditive)
Also checks whether the head sets are NESTED, which matters for interpretation: heads are ranked by source
mass, so heads added later are individually weaker, making any superadditivity conservative.

Usage: python scripts/analyze_superadditivity.py
"""
from __future__ import annotations
import json
import numpy as np

PATH = "results/lengthgen/paired_head_count_full_grid.json"
KS = [1, 2, 4, 8]


def effect_at(sweep, key="source_max"):
    """mean paired source-max effect vs baseline for one coverage level."""
    pc = sweep.get("paired_contrasts_vs_baseline") or {}
    v = pc.get(key)
    if isinstance(v, dict):
        for f in ("token_accuracy_delta", "exact_match_delta"):
            if isinstance(v.get(f), (int, float)):
                return float(v[f])
    return None


def main():
    data = json.load(open(PATH))
    print(f"models: {len(data)}")
    e0 = data[0]
    sw = e0["lengths"]["250"]["sweeps"]
    print("available contrast keys:", list((sw["1"].get("paired_contrasts_vs_baseline") or {}).keys()))
    print("condition keys:", list((sw["1"].get("conditions") or {}).keys()))

    # nesting check
    sets = {k: set(sw[str(k)]["heads"]) for k in KS if str(k) in sw}
    nested = all(sets[KS[i]] <= sets[KS[i + 1]] for i in range(len(KS) - 1) if KS[i] in sets and KS[i + 1] in sets)
    print("head sets nested (K=1 subset of 2 subset of 4 subset of 8):", nested)

    rows = []
    for e in data:
        cfg = e["cfg"]
        for Lname, L in e["lengths"].items():
            sweeps = L.get("sweeps", {})
            eff = {}
            for k in KS:
                if str(k) in sweeps:
                    v = effect_at(sweeps[str(k)])
                    if v is not None:
                        eff[k] = v
            if len(eff) == len(KS):
                rows.append({"task": cfg["task"], "pe": cfg["pe"], "seed": cfg["seed"],
                             "length": Lname, **{f"e{k}": eff[k] for k in KS}})

    if not rows:
        print("\nCould not extract effects with the expected keys; inspect the JSON structure above.")
        return

    print(f"\ncells with all four coverage levels: {len(rows)}")
    print(f"\n{'task':>8} {'pe':>5} {'sd':>3} {'len':>4} | " + " ".join(f"e{k}:>8" for k in KS) +
          " | " + " ".join(f"e{k}/{k}" for k in KS))
    perhead = {k: [] for k in KS}
    for r in rows:
        ph = [r[f"e{k}"] / k for k in KS]
        for k, v in zip(KS, ph):
            perhead[k].append(v)
        print(f"{r['task']:>8} {r['pe']:>5} {r['seed']:>3} {r['length']:>4} | " +
              " ".join(f"{r[f'e{k}']:+8.4f}" for k in KS) + " | " +
              " ".join(f"{v:+7.4f}" for v in ph))

    print("\nmean per-head effect by coverage (rising => superadditive):")
    for k in KS:
        print(f"  K={k}: {np.mean(perhead[k]):+.4f}  (n={len(perhead[k])})")

    print("\ndoubling ratios eff(2K) / (2*eff(K))  (>1 => superadditive):")
    for a, b in ((1, 2), (2, 4), (4, 8)):
        ratios = [r[f"e{b}"] / (2 * r[f"e{a}"]) for r in rows if abs(r[f"e{a}"]) > 1e-9]
        if ratios:
            arr = np.asarray(ratios)
            frac = float(np.mean(arr > 1))
            print(f"  {a}->{b}: median {np.median(arr):.2f}   fraction of cells >1: {frac:.2f}  (n={len(arr)})")

    # sign test on superadditivity of the last doubling
    last = [r for r in rows if abs(r["e4"]) > 1e-9]
    pos = sum(1 for r in last if r["e8"] > 2 * r["e4"])
    print(f"\nsuperadditive at 4->8 in {pos}/{len(last)} cells")
    print("\nInterpretation: heads are ranked by source mass, so heads added at larger K are individually")
    print("weaker. Rising per-head effect is therefore a conservative estimate of superadditivity.")
    print("Confound to rule out next: re-run with SHUFFLED head ordering at each K.")


if __name__ == "__main__":
    main()
