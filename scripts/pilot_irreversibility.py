"""Pilot: is there a depth-wise "arrow of time" in the transformer residual stream, and is it
non-trivial (not flat) and non-redundant (not just representation change)?

Pre-registered kill conditions (decided BEFORE seeing results, see docs/irreversibility_pilot.md):
  K1 (real):        the irreversibility-fraction profile must exceed the depth-shuffle null beyond
                    bootstrap 95% CIs at some depth, and vary across depth (not flat).
  K2 (non-redundant): |corr(irr, repr_change)| < 0.9 AND the irr peak is at a different depth than
                    the repr_change peak (it is not merely tracking how much the representation moves).
If either fails -> report NEGATIVE and stop; do not build a paper on it.

Standardizes hidden dims (z-score) before PCA so the known massive-activation "sink" dimensions do
not dominate the covariance.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.irreversibility import (
    bootstrap_profile,
    common_pca_basis,
    depth_irreversibility_profile,
    shuffle_null_profile,
)
from thermosafety.prompts import load_prompt_dir
from thermosafety.real_model import extract_trace_from_loaded, load_model


def gather_trajectories(model_name, device, local_files_only, prompts, max_len, max_tokens_per_prompt):
    torch, tokenizer, model = load_model(model_name, device=device, local_files_only=local_files_only)
    trajs = []
    for p in prompts:
        tr = extract_trace_from_loaded(prompt=p, torch=torch, tokenizer=tokenizer, model=model,
                                       max_length=max_len, device=device)
        hs = tr.hidden_states  # list of (seq, d), length L+1
        L1 = len(hs)
        seq = hs[0].shape[0]
        take = min(seq, max_tokens_per_prompt)
        # take the last `take` token positions
        for t in range(seq - take, seq):
            trajs.append(np.stack([hs[l][t] for l in range(L1)], axis=0))  # (L+1, d)
    return np.stack(trajs, axis=0)  # (n_tokens, L+1, d)


def standardize(traj: np.ndarray) -> np.ndarray:
    n, L, d = traj.shape
    flat = traj.reshape(n * L, d)
    mu = flat.mean(axis=0, keepdims=True)
    sd = flat.std(axis=0, keepdims=True) + 1e-8
    return ((flat - mu) / sd).reshape(n, L, d)


def main() -> None:
    ap = argparse.ArgumentParser(description="Depth-wise irreversibility pilot.")
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--local-files-only", action="store_true")
    ap.add_argument("--suites", default="benign,benign_complex,direct_jailbreak,safety_research")
    ap.add_argument("--per-suite", type=int, default=8)
    ap.add_argument("--max-length", type=int, default=48)
    ap.add_argument("--max-tokens-per-prompt", type=int, default=40)
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--output", default="results/irreversibility_profile.csv")
    args = ap.parse_args()

    all_cases = load_prompt_dir("prompts")
    prompts = []
    for s in [x.strip() for x in args.suites.split(",") if x.strip()]:
        prompts.extend([c.prompt for c in all_cases if c.suite == s][: args.per_suite])
    print(f"prompts: {len(prompts)}")

    traj = gather_trajectories(args.model, args.device, args.local_files_only, prompts,
                               args.max_length, args.max_tokens_per_prompt)
    print(f"trajectories: {traj.shape[0]} tokens x {traj.shape[1]} layers x {traj.shape[2]} dim")
    traj = standardize(traj)

    # Fit the PCA basis ONCE on all (token, layer) states and reuse it everywhere.
    n, L, d = traj.shape
    basis = common_pca_basis(traj.reshape(n * L, d), args.k)
    prof = depth_irreversibility_profile(traj, k=args.k, basis=basis)
    irr = prof["irr_fraction"]
    dh = prof["repr_change"]
    boot = bootstrap_profile(traj, k=args.k, n_boot=200, basis=basis)
    null = shuffle_null_profile(traj, k=args.k, n_shuffles=30, basis=basis)
    null_hi = np.percentile(null, 97.5, axis=0)
    null_mean = null.mean(axis=0)

    L = len(irr)
    # K1: real exceeds null beyond CI, and non-flat
    exceeds = boot["lo"] > null_hi   # per depth: real lower-CI above null upper band
    n_exceed = int(exceeds.sum())
    flat_ratio = float(irr.max() / (irr.min() + 1e-12))
    non_flat = flat_ratio > 1.5
    k1 = n_exceed > 0 and non_flat

    # K2: not redundant with representation change
    corr = float(np.corrcoef(irr, dh)[0, 1])
    irr_peak = int(np.argmax(irr))
    dh_peak = int(np.argmax(dh))
    k2 = abs(corr) < 0.9 and (irr_peak != dh_peak)

    rows = []
    for l in range(L):
        rows.append({
            "transition": f"{l}->{l+1}", "irr_fraction": round(float(irr[l]), 5),
            "boot_lo": round(float(boot["lo"][l]), 5), "boot_hi": round(float(boot["hi"][l]), 5),
            "null_mean": round(float(null_mean[l]), 5), "null_hi": round(float(null_hi[l]), 5),
            "repr_change": round(float(dh[l]), 4), "exceeds_null": bool(exceeds[l]),
        })
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print("\ntransition | irr [boot CI] | null_hi | repr_change | >null")
    for r in rows:
        print(f"{r['transition']:>7} | {r['irr_fraction']:.4f} [{r['boot_lo']:.4f},{r['boot_hi']:.4f}] | "
              f"{r['null_hi']:.4f} | {r['repr_change']:.3f} | {'YES' if r['exceeds_null'] else '.'}")

    print("\n=== pre-registered kill conditions ===")
    print(f"K1 real & non-flat: {n_exceed}/{L} depths exceed null CI, max/min ratio {flat_ratio:.2f} "
          f"-> {'PASS' if k1 else 'FAIL'}")
    print(f"K2 non-redundant:  corr(irr, repr_change)={corr:.3f}, irr peak @{irr_peak} vs "
          f"repr_change peak @{dh_peak} -> {'PASS' if k2 else 'FAIL'}")
    verdict = "PROMISING (both pass) -- worth developing" if (k1 and k2) else "NEGATIVE -- stop"
    print(f"\nVERDICT: {verdict}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
