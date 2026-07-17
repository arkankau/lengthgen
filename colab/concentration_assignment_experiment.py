"""Paired concentration-by-assignment factorial on cached retrieval checkpoints.

For each model, select one retrieval layer using only L_train examples and freeze it.
At long lengths, temperature-sharpen the existing attention spectrum with
    a_j(beta) = a_j**beta / sum_k a_k**beta
for beta in {1, 2, 4}. At each beta, either leave token assignment unchanged,
assign each head's maximum to the source, assign its minimum to the source, or
permute distractors only. Correct and wrong assignment conditions therefore use
the exact same sharpened spectrum.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

import length_gen_colab as G
from paired_head_count_experiment import evaluate_heads
from paired_permutation_experiment import (
    load_or_train,
    make_cfg,
    paired_contrast,
    sample_batches,
    select_circuit,
)


MODES = ("identity", "source_max", "source_min", "distractor_control")


def label(condition, beta):
    condition["mode"] = f"{condition['mode']}_beta{beta:g}"
    return condition


def run_model(task, pe, seed, args):
    cfg = make_cfg(task, pe, seed, args)
    model, saved_checkpoint = load_or_train(cfg, args)
    train_row = G.evaluate(
        model, cfg, np.random.default_rng(args.eval_seed), [cfg.l_train], n_eval=args.n_eval
    )[0]
    circuit = select_circuit(model, cfg, args.selection_examples, args.selection_seed)
    layer = circuit["selected_layer"]
    heads = list(range(cfg.n_heads))
    print(
        f"[circuit] task={task} pe={pe} seed={seed} layer={layer} "
        f"selection_mass={circuit['selected_source_mass']:.4f}",
        flush=True,
    )
    result = {
        "cfg": {
            "task": task,
            "pe": pe,
            "seed": seed,
            "steps": args.steps,
            "layers": args.layers,
            "width": args.width,
            "heads": args.heads,
            "batch": args.batch,
        },
        "checkpoint": saved_checkpoint,
        "train_length": {
            "length": cfg.l_train,
            "exact_match": train_row["em"],
            "token_accuracy": train_row["tok"],
        },
        "circuit": circuit,
        "betas": args.betas,
        "lengths": {},
    }
    for length in args.lengths:
        batches = sample_batches(cfg, length, args.n_eval, args.eval_seed)
        baseline = evaluate_heads(model, batches, layer, heads, "baseline")
        baseline["mode"] = "natural_baseline"
        levels = {}
        for beta_index, beta in enumerate(args.betas):
            conditions = {
                mode: label(evaluate_heads(model, batches, layer, heads, mode, beta), beta)
                for mode in MODES
            }
            correct = conditions["source_max"]
            wrong = conditions["source_min"]
            identity = conditions["identity"]
            control = conditions["distractor_control"]
            offset = args.bootstrap_seed + length * 100 + beta_index * 10
            contrasts = {
                "correct_vs_wrong": paired_contrast(
                    wrong, correct, offset + 1, args.bootstrap_draws
                ),
                "correct_vs_identity": paired_contrast(
                    identity, correct, offset + 2, args.bootstrap_draws
                ),
                "identity_vs_baseline": paired_contrast(
                    baseline, identity, offset + 3, args.bootstrap_draws
                ),
                "wrong_vs_identity": paired_contrast(
                    identity, wrong, offset + 4, args.bootstrap_draws
                ),
                "correct_vs_distractor_control": paired_contrast(
                    control, correct, offset + 5, args.bootstrap_draws
                ),
            }
            levels[f"{beta:g}"] = {
                "conditions": conditions,
                "paired_contrasts": contrasts,
            }
        result["lengths"][str(length)] = {"baseline": baseline, "levels": levels}
        compact = []
        for beta in args.betas:
            level = levels[f"{beta:g}"]
            gap = level["paired_contrasts"]["correct_vs_wrong"]["token_accuracy_delta"]
            rescue = level["paired_contrasts"]["correct_vs_identity"]["token_accuracy_delta"]
            maximum = level["conditions"]["source_max"]["mean_head_max_weight"]
            compact.append(f"b{beta:g}:gap={gap:+.3f},rescue={rescue:+.3f},max={maximum:.3f}")
        print(f"  L={length} " + " | ".join(compact), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="argmax,flagret")
    parser.add_argument("--pes", default="nope,rope")
    parser.add_argument("--seeds", default="0,1,2,3")
    parser.add_argument("--lengths", default="100,250")
    parser.add_argument("--betas", default="1,2,4")
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--warmup", type=int, default=400)
    parser.add_argument("--batch", type=int, default=512)
    parser.add_argument("--n-eval", type=int, default=256)
    parser.add_argument("--selection-examples", type=int, default=256)
    parser.add_argument("--selection-seed", type=int, default=4321)
    parser.add_argument("--eval-seed", type=int, default=1234)
    parser.add_argument("--bootstrap-seed", type=int, default=2027)
    parser.add_argument("--bootstrap-draws", type=int, default=10000)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--heads", type=int, default=8)
    parser.add_argument("--mlp", type=int, default=1024)
    parser.add_argument("--outdir", default=".")
    parser.add_argument("--checkpoint-dir", default=None)
    args = parser.parse_args()
    args.tasks = [value for value in args.tasks.split(",") if value]
    args.pes = [value for value in args.pes.split(",") if value]
    args.seeds = [int(value) for value in args.seeds.split(",") if value]
    args.lengths = [int(value) for value in args.lengths.split(",") if value]
    args.betas = [float(value) for value in args.betas.split(",") if value]

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "concentration_assignment_results.json")
    results = json.load(open(path)) if os.path.exists(path) else []
    done = {
        (
            row["cfg"]["task"], row["cfg"]["pe"], row["cfg"]["seed"],
            row["cfg"]["steps"], tuple(row["betas"]),
            tuple(sorted(int(value) for value in row["lengths"])),
        )
        for row in results
    }
    plan = [
        (task, pe, seed)
        for task in args.tasks
        for pe in args.pes
        for seed in args.seeds
    ]
    print(f"device={G.DEVICE}; models={len(plan)}; output={path}")
    for index, (task, pe, seed) in enumerate(plan, 1):
        key = (
            task, pe, seed, args.steps, tuple(args.betas), tuple(sorted(args.lengths))
        )
        if key in done:
            print(f"[skip {index}/{len(plan)}] {key}")
            continue
        result = run_model(task, pe, seed, args)
        results.append(result)
        with open(path, "w") as handle:
            json.dump(results, handle, indent=2)
        print(f"[saved {index}/{len(plan)}] {key}", flush=True)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
