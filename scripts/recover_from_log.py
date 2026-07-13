"""Rebuild lengthgen_results.json from a saved/pasted Colab console log.

The trainer prints each completed run as a single `RESULTJSON {...}` line (see colab/length_gen_colab.py).
If the JSON file is ever lost (unmounted Drive / recycled VM), the console log alone is enough: paste it
into a text file and run this to reconstruct the exact results file.

Usage: python scripts/recover_from_log.py <console_log.txt> [out.json]
"""
import json
import sys

MARK = "RESULTJSON "


def main(log_path, out_path="results/lengthgen/recovered_results.json"):
    recs = {}
    dropped = 0
    for line in open(log_path, encoding="utf-8", errors="replace"):
        s = line.lstrip()
        if not s.startswith(MARK):   # only genuine data lines start with the marker (ignores prose mentions)
            continue
        try:
            rec = json.loads(s[len(MARK):].strip())
            c = rec["cfg"]
            recs[(c["task"], c["pe"], int(c["post_attn_ln"]), c["seed"])] = rec  # last wins
        except Exception:
            dropped += 1  # a genuinely truncated data line; re-paste that cell if a run is missing
    out = list(recs.values())
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    from collections import Counter
    by_task = Counter(k[0] for k in recs)
    print(f"recovered {len(out)} run records -> {out_path}")
    print("by task:", dict(by_task))
    if dropped:
        print(f"(skipped {dropped} malformed/truncated RESULTJSON lines -- re-paste those if a cell is missing)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/recover_from_log.py <console_log.txt> [out.json]"); sys.exit(1)
    main(*sys.argv[1:3])
