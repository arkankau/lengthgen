"""Train-length-locked top-k head dose response for attention permutation.

Heads in the selected retrieval layer are ranked once by source mass at L_train.
The top k heads are then permuted at long lengths for k in {1,2,4,8}, with paired
source-max, source-min, and distractor-only controls on identical examples.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import torch

import length_gen_colab as G
from paired_permutation_experiment import (
    load_or_train,
    make_cfg,
    paired_contrast,
    sample_batches,
    select_circuit,
)


def evaluate_heads(model, batches, layer, heads, mode, beta=1.0):
    if mode == "baseline":
        G.PATCH = None
    else:
        G.PATCH = {
            "layer": layer,
            "heads": heads,
            "mode": mode,
            "beta": beta,
            "diagnostics": {},
        }
    exact = []
    token_accuracy = []
    source_mass = np.zeros(len(heads), dtype=np.float64)
    output_var_sum = entropy_sum = max_weight_sum = 0.0
    seen = 0
    for x, y, mask, aq, tgt in batches:
        with torch.no_grad():
            prediction = model(x, aq, tgt).argmax(dim=-1)
        valid = mask.bool()
        for index in range(x.shape[0]):
            selected = valid[index]
            correct = prediction[index][selected] == y[index][selected]
            exact.append(float(bool(correct.all())))
            token_accuracy.append(float(correct.float().mean().cpu()))
        batch_size = x.shape[0]
        masses = np.asarray(model.attn_source_by_head()[layer], dtype=np.float64)
        source_mass += masses[heads] * batch_size
        block = model.blocks[layer]
        output_var_sum += block.z_aq_var * batch_size
        entropy_sum += block.attn_ent * batch_size
        max_weight_sum += block.attn_max * batch_size
        seen += batch_size
    diagnostics = {} if G.PATCH is None else dict(G.PATCH["diagnostics"])
    G.PATCH = None
    return {
        "mode": mode,
        "beta": beta,
        "heads": heads,
        "n_examples": seen,
        "exact_match": float(np.mean(exact)),
        "token_accuracy": float(np.mean(token_accuracy)),
        "source_mass_by_selected_head": (source_mass / max(1, seen)).tolist(),
        "mean_head_entropy": entropy_sum / max(1, seen),
        "mean_head_max_weight": max_weight_sum / max(1, seen),
        "attention_output_var": output_var_sum / max(1, seen),
        "invariant_max_abs_error": diagnostics,
        "per_example_exact": exact,
        "per_example_token_accuracy": token_accuracy,
    }


def run_model(task, pe, seed, args):
    cfg = make_cfg(task, pe, seed, args)
    model, saved_checkpoint = load_or_train(cfg, args)
    train_row = G.evaluate(
        model, cfg, np.random.default_rng(args.eval_seed), [cfg.l_train], n_eval=args.n_eval
    )[0]
    circuit = select_circuit(model, cfg, args.selection_examples, args.selection_seed)
    layer = circuit["selected_layer"]
    layer_masses = np.asarray(circuit["source_mass_by_layer_head"][layer])
    ranking = np.argsort(-layer_masses).tolist()
    counts = sorted(set(min(value, cfg.n_heads) for value in args.head_counts))
    circuit["selected_layer_head_ranking"] = ranking
    circuit["selected_layer_ranked_source_mass"] = layer_masses[ranking].tolist()
    print(
        f"[circuit] L={cfg.l_train} layer={layer} ranking={ranking} "
        f"mass={[round(value, 3) for value in layer_masses[ranking]]}",
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
        "head_counts": counts,
        "lengths": {},
    }
    for length in args.lengths:
        batches = sample_batches(cfg, length, args.n_eval, args.eval_seed)
        baseline = evaluate_heads(model, batches, layer, ranking, "baseline")
        sweeps = {}
        for count in counts:
            heads = ranking[:count]
            conditions = {
                mode: evaluate_heads(model, batches, layer, heads, mode)
                for mode in ("source_max", "source_min", "distractor_control")
            }
            contrasts = {
                mode: paired_contrast(
                    baseline,
                    condition,
                    args.bootstrap_seed + length + count * 10 + index,
                    args.bootstrap_draws,
                )
                for index, (mode, condition) in enumerate(conditions.items())
            }
            sweeps[str(count)] = {
                "heads": heads,
                "conditions": conditions,
                "paired_contrasts_vs_baseline": contrasts,
            }
        result["lengths"][str(length)] = {"baseline": baseline, "sweeps": sweeps}
        deltas = [
            sweeps[str(count)]["paired_contrasts_vs_baseline"]["source_max"]
            ["token_accuracy_delta"]
            for count in counts
        ]
        print(
            f"  L={length} source_max token delta by k="
            + ", ".join(f"{count}:{delta:+.3f}" for count, delta in zip(counts, deltas)),
            flush=True,
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="argmax,flagret")
    parser.add_argument("--pes", default="nope,rope")
    parser.add_argument("--seeds", default="0,1,2,3")
    parser.add_argument("--lengths", default="100,250")
    parser.add_argument("--head-counts", default="1,2,4,8")
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
    args.head_counts = [int(value) for value in args.head_counts.split(",") if value]

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "paired_head_count_results.json")
    results = json.load(open(path)) if os.path.exists(path) else []
    done = {
        (
            row["cfg"]["task"], row["cfg"]["pe"], row["cfg"]["seed"],
            row["cfg"]["steps"], tuple(row["head_counts"]),
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
            task, pe, seed, args.steps, tuple(sorted(set(args.head_counts))),
            tuple(sorted(args.lengths)),
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
