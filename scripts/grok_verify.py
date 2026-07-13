"""E2 verifier: does a thermodynamic observable show a localized change AT the grokking transition,
beyond the memorization-plateau noise, consistently across seeds?

Parses one or more grok training logs (either the CSV written at end, or the per-checkpoint stdout
lines "step .. | train .. val .. | C_attn .. H_attn .. PR .. Sspec ..") so it can run on in-progress
runs too. Verifier discipline (same null-control we used throughout): an observable "passes" for a
seed only if its post-grok value differs from the memorization-plateau value beyond the plateau's
bootstrap 95% CI, AND the steepest change in the observable is localized near the grok step. Reports
per-seed and aggregate; a robust positive requires a consistent-direction pass across seeds.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thermosafety.thermo_observables import bootstrap_ci  # noqa: E402

OBS = ["attn_specific_heat", "attn_entropy", "repr_participation_ratio", "weight_spectral_entropy"]
LINE_RE = re.compile(
    r"step\s+(\d+) \| train ([\d.]+) val ([\d.]+) \| C_attn ([\d.]+) H_attn ([\d.]+) PR ([\d.]+) Sspec ([\d.]+)"
)


def load_log(path: Path) -> dict[str, np.ndarray]:
    text = path.read_text(encoding="utf-8", errors="replace")
    steps, tr, va, c, h, pr, ss = [], [], [], [], [], [], []
    if "step,train_acc,val_acc" in text.splitlines()[0] if text.splitlines() else False:
        import csv
        for r in csv.DictReader(text.splitlines()):
            steps.append(float(r["step"])); tr.append(float(r["train_acc"])); va.append(float(r["val_acc"]))
            c.append(float(r["attn_specific_heat"])); h.append(float(r["attn_entropy"]))
            pr.append(float(r["repr_participation_ratio"])); ss.append(float(r["weight_spectral_entropy"]))
    else:
        for m in LINE_RE.finditer(text):
            g = m.groups()
            steps.append(float(g[0])); tr.append(float(g[1])); va.append(float(g[2]))
            c.append(float(g[3])); h.append(float(g[4])); pr.append(float(g[5])); ss.append(float(g[6]))
    return {
        "step": np.array(steps), "train_acc": np.array(tr), "val_acc": np.array(va),
        "attn_specific_heat": np.array(c), "attn_entropy": np.array(h),
        "repr_participation_ratio": np.array(pr), "weight_spectral_entropy": np.array(ss),
    }


def analyze_seed(log: dict[str, np.ndarray], seed_name: str) -> list[dict]:
    step, val, train = log["step"], log["val_acc"], log["train_acc"]
    memorized = train > 0.95
    grokked = val > 0.9
    if not grokked.any():
        print(f"[{seed_name}] never grokked; skipping")
        return []
    grok_step = float(step[grokked.argmax()])
    # memorization plateau: memorized but not yet grokked, excluding the last 300 steps before grok
    plateau_mask = memorized & (val < 0.55) & (step < grok_step - 300)
    post_mask = val > 0.98
    if plateau_mask.sum() < 5 or post_mask.sum() < 5:
        print(f"[{seed_name}] insufficient plateau/post samples; skipping")
        return []
    rng = np.random.default_rng(0)
    out = []
    for o in OBS:
        vals = log[o]
        p_mean, p_lo, p_hi = bootstrap_ci(vals[plateau_mask], n_boot=2000, rng=rng)
        post_mean = float(vals[post_mask].mean())
        beyond_ci = post_mean > p_hi or post_mean < p_lo
        direction = "up" if post_mean > p_mean else "down"
        fold = post_mean / p_mean if p_mean not in (0.0,) else float("inf")
        # Localization (robust to post-grok noise spikes): the step at which the observable first
        # crosses the midpoint between its plateau and post-grok levels should sit near the grok step.
        midpoint = 0.5 * (p_mean + post_mean)
        after_plateau = step >= (grok_step - 2500)
        if direction == "up":
            crossed = after_plateau & (vals >= midpoint)
        else:
            crossed = after_plateau & (vals <= midpoint)
        cross_step = float(step[crossed.argmax()]) if crossed.any() else float("nan")
        cross_dist = abs(cross_step - grok_step) if cross_step == cross_step else float("inf")
        localized = cross_dist <= 800  # within 800 steps of the val-accuracy transition
        out.append({
            "seed": seed_name, "observable": o, "grok_step": grok_step,
            "plateau_mean": round(p_mean, 5), "plateau_ci": (round(p_lo, 5), round(p_hi, 5)),
            "post_mean": round(post_mean, 5), "direction": direction, "fold_change": round(fold, 2),
            "beyond_ci": beyond_ci, "cross_step": cross_step, "cross_dist": cross_dist,
            "pass": bool(beyond_ci and localized),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Grokking thermodynamic-fingerprint verifier.")
    ap.add_argument("logs", nargs="+", help="grok log files (csv or stdout capture), one per seed")
    args = ap.parse_args()

    all_rows = []
    for p in args.logs:
        rows = analyze_seed(load_log(Path(p)), Path(p).stem)
        all_rows.extend(rows)
        for r in rows:
            flag = "PASS" if r["pass"] else "    "
            cd = r["cross_dist"]
            cd_s = f"{int(cd)}" if cd != float("inf") else "inf"
            print(f"[{flag}] {r['seed']:20s} {r['observable']:26s} grok@{int(r['grok_step']):5d} | "
                  f"plateau {r['plateau_mean']:.4f} {r['plateau_ci']} -> post {r['post_mean']:.4f} "
                  f"({r['direction']}, x{r['fold_change']}) | cross@{int(r['cross_step']) if r['cross_step']==r['cross_step'] else 'NA'} dist {cd_s}")

    print("\n=== aggregate across seeds ===")
    for o in OBS:
        rws = [r for r in all_rows if r["observable"] == o]
        if not rws:
            continue
        passes = [r for r in rws if r["pass"]]
        dirs = {r["direction"] for r in passes}
        consistent = len(dirs) == 1
        print(f"{o:26s}: {len(passes)}/{len(rws)} seeds pass, "
              f"direction {'consistent ' + dirs.pop() if passes and consistent else 'mixed/none'}")


if __name__ == "__main__":
    main()
