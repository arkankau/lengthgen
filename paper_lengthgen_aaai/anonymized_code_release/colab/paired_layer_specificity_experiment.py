"""Layer-specificity control for spectrum-preserving attention permutations."""
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


def run_model(task, pe, seed, args):
    cfg = make_cfg(task, pe, seed, args)
    model, saved_checkpoint = load_or_train(cfg, args)
    train_row = G.evaluate(
        model, cfg, np.random.default_rng(args.eval_seed), [cfg.l_train], n_eval=args.n_eval
    )[0]
    circuit = select_circuit(model, cfg, args.selection_examples, args.selection_seed)
    layer_matrix = np.asarray(circuit["source_mass_by_layer_head"])
    layer_ranking = np.argsort(-layer_matrix.max(axis=1)).tolist()
    circuit["layer_ranking_by_best_head"] = layer_ranking
    print(
        f"[circuit] selected_layer={circuit['selected_layer']} layer_ranking={layer_ranking} "
        f"best_mass={[round(value, 3) for value in layer_matrix.max(axis=1)]}",
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
        "lengths": {},
    }
    all_heads = list(range(cfg.n_heads))
    for length in args.lengths:
        batches = sample_batches(cfg, length, args.n_eval, args.eval_seed)
        baseline = evaluate_heads(model, batches, circuit["selected_layer"], all_heads, "baseline")
        layers = {}
        for layer in range(cfg.n_layers):
            conditions = {
                mode: evaluate_heads(model, batches, layer, all_heads, mode)
                for mode in ("source_max", "source_min", "distractor_control")
            }
            contrasts = {
                mode: paired_contrast(
                    baseline,
                    condition,
                    args.bootstrap_seed + length + layer * 10 + index,
                    args.bootstrap_draws,
                )
                for index, (mode, condition) in enumerate(conditions.items())
            }
            layers[str(layer)] = {
                "conditions": conditions,
                "paired_contrasts_vs_baseline": contrasts,
            }
        result["lengths"][str(length)] = {"baseline": baseline, "layers": layers}
        deltas = [
            layers[str(layer)]["paired_contrasts_vs_baseline"]["source_max"]
            ["token_accuracy_delta"]
            for layer in range(cfg.n_layers)
        ]
        print(
            f"  L={length} source_max token delta by layer="
            + ", ".join(f"{layer}:{delta:+.3f}" for layer, delta in enumerate(deltas)),
            flush=True,
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="argmax,flagret")
    parser.add_argument("--pes", default="nope,rope")
    parser.add_argument("--seeds", default="0,1,2,3")
    parser.add_argument("--lengths", default="100,250")
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

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "paired_layer_specificity_results.json")
    results = json.load(open(path)) if os.path.exists(path) else []
    done = {
        (
            row["cfg"]["task"], row["cfg"]["pe"], row["cfg"]["seed"],
            row["cfg"]["steps"], tuple(sorted(int(value) for value in row["lengths"])),
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
        key = (task, pe, seed, args.steps, tuple(sorted(args.lengths)))
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
