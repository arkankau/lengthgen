"""Merge length-gen result files into one, deduping by config key.

Used to combine the existing baseline+varfix runs (gpu_resultsA.json) with a new
attention-sharpening arm (the Direction-B loglen run) so analyze_causalB.py sees all
three conditions in a single file.

Later files win on a key collision (so a re-run overrides a stale record).

Usage:
  python scripts/merge_lengthgen_json.py A.json B.json [C.json ...] -o out.json
"""
from __future__ import annotations
import json, sys, argparse


def key(c):
    return (c["task"], c["pe"], int(c["post_attn_ln"]), int(c["seed"]), c.get("attn_scale", "none"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    merged = {}
    for path in a.inputs:
        recs = json.load(open(path))
        for r in recs:
            merged[key(r["cfg"])] = r
        print(f"  {path}: {len(recs)} records")
    out = list(merged.values())
    json.dump(out, open(a.out, "w"), indent=2)
    # report condition coverage
    from collections import Counter
    conds = Counter((r["cfg"]["task"], r["cfg"]["pe"], int(r["cfg"]["post_attn_ln"]),
                     r["cfg"].get("attn_scale", "none")) for r in out)
    print(f"merged -> {a.out}: {len(out)} unique records")
    for (t, pe, ln, sc), n in sorted(conds.items()):
        cond = "baseline" if (ln == 0 and sc == "none") else "varfix" if (ln == 1 and sc == "none") else f"attn({sc})"
        print(f"  {t:8s} {pe:4s} {cond:14s} x{n} seeds")


if __name__ == "__main__":
    main()
