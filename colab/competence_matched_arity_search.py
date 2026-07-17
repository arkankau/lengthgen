"""Outcome-blind capacity search for the variable-evidence experiment.

Only unmodified train-length exact match is evaluated. The search starts with
the hardest four-evidence task and freezes the first preregistered architecture
whose NoPE/RoPE cells all clear competence. No routing intervention is run here.
"""
from __future__ import annotations

import argparse
import json
import os
from types import SimpleNamespace

import numpy as np

import length_gen_colab as G
from paired_permutation_experiment import load_or_train, make_cfg


CANDIDATES = (
    {"name": "c1", "layers": 4, "width": 256, "heads": 8, "mlp": 1024, "steps": 8000, "batch": 512},
    {"name": "c2", "layers": 6, "width": 384, "heads": 8, "mlp": 1536, "steps": 8000, "batch": 256},
    {"name": "c3", "layers": 8, "width": 512, "heads": 8, "mlp": 2048, "steps": 12000, "batch": 128},
)


def candidate_args(base, candidate):
    values = vars(base).copy()
    values.update(candidate)
    values["warmup"] = min(base.warmup, candidate["steps"] // 10)
    return SimpleNamespace(**values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pes", default="nope,rope")
    parser.add_argument("--seeds", default="0,1")
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--n-eval", type=int, default=512)
    parser.add_argument("--eval-seed", type=int, default=1234)
    parser.add_argument("--warmup", type=int, default=800)
    parser.add_argument("--outdir", default=".")
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--start-at", choices=[row["name"] for row in CANDIDATES], default=None)
    args = parser.parse_args()
    pes = [value for value in args.pes.split(",") if value]
    seeds = [int(value) for value in args.seeds.split(",") if value]
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "competence_matched_arity_search.json")
    result = {
        "protocol": "competence_matched_arity_search_v1",
        "outcome_blinding": "baseline train-length exact match only; no attention intervention",
        "search_task": "quadadd",
        "positional_encodings": pes,
        "seeds": seeds,
        "threshold": args.threshold,
        "candidates": [],
        "frozen_config": None,
        "start_at": args.start_at,
    }
    start_index = 0 if args.start_at is None else next(
        index for index, row in enumerate(CANDIDATES) if row["name"] == args.start_at
    )
    for candidate in CANDIDATES[start_index:]:
        run_args = candidate_args(args, candidate)
        cells = []
        rejected_early = False
        for pe in pes:
            for seed in seeds:
                cfg = make_cfg("quadadd", pe, seed, run_args)
                model, checkpoint = load_or_train(cfg, run_args)
                row = G.evaluate(
                    model,
                    cfg,
                    np.random.default_rng(args.eval_seed),
                    [cfg.l_train],
                    n_eval=args.n_eval,
                )[0]
                cells.append({
                    "pe": pe,
                    "seed": seed,
                    "exact_match": row["em"],
                    "token_accuracy": row["tok"],
                    "checkpoint": checkpoint,
                })
                print(
                    f"candidate={candidate['name']} pe={pe} seed={seed} "
                    f"train_em={row['em']:.3f}",
                    flush=True,
                )
                if row["em"] < args.threshold:
                    rejected_early = True
                    print(
                        f"EARLY REJECT {candidate['name']}: one required cell is below "
                        f"{args.threshold:.3f}; the all-cell competence rule is now impossible",
                        flush=True,
                    )
                    break
            if rejected_early:
                break
        passed = len(cells) == len(pes) * len(seeds) and all(
            row["exact_match"] >= args.threshold for row in cells
        )
        result["candidates"].append({
            **candidate,
            "cells": cells,
            "passed": passed,
            "rejected_early": rejected_early,
        })
        if passed:
            result["frozen_config"] = candidate
            print(f"FROZEN CONFIG: {candidate}", flush=True)
            break
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)
    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    if result["frozen_config"] is None:
        print("NO PREREGISTERED CANDIDATE CLEARED COMPETENCE", flush=True)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
