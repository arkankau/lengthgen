"""Train-length-locked, selected-head attention permutation experiment.

The retrieval circuit is selected once using source attention at the training length.
At every test length, the same layer and head are evaluated under spectrum-preserving
source-max, source-min, and distractor-only permutations. All conditions reuse the
same examples, enabling paired bootstrap intervals and exact McNemar tests.
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import torch

import length_gen_colab as G
from permutation_experiment import train_baseline


CONDITIONS = ("baseline", "source_max", "source_min", "distractor_control")


def make_cfg(task, pe, seed, args):
    task_cfg = G.TASKS[task]
    return G.Cfg(
        task=task,
        pe=pe,
        post_attn_ln=False,
        seed=seed,
        steps=args.steps,
        attn_scale="none",
        n_layers=args.layers,
        d_model=args.width,
        n_heads=args.heads,
        d_mlp=args.mlp,
        batch=args.batch,
        warmup=min(args.warmup, max(1, args.steps // 4)),
        vocab=task_cfg["vocab"],
        pad=task_cfg["pad"],
    )


def checkpoint_path(cfg, args):
    directory = args.checkpoint_dir or os.path.join(args.outdir, "checkpoints")
    os.makedirs(directory, exist_ok=True)
    name = (
        f"{cfg.task}_{cfg.pe}_s{cfg.seed}_{cfg.n_layers}L_{cfg.d_model}d_"
        f"{cfg.n_heads}h_b{cfg.batch}_steps{cfg.steps}.pt"
    )
    return os.path.join(directory, name)


def load_or_train(cfg, args):
    path = checkpoint_path(cfg, args)
    if os.path.exists(path):
        print(f"[load] {path}", flush=True)
        model = G.build_model(cfg)
        model.load_state_dict(torch.load(path, map_location=G.DEVICE, weights_only=True))
        return model, path
    print(f"[train] {cfg.task} {cfg.pe} seed={cfg.seed} steps={cfg.steps}", flush=True)
    model = train_baseline(cfg)
    torch.save(model.state_dict(), path)
    print(f"[checkpoint] {path}", flush=True)
    return model, path


def sample_batches(cfg, length, n_examples, seed, batch_size=64):
    rng = np.random.default_rng(seed)
    batches = []
    remaining = n_examples
    while remaining:
        size = min(batch_size, remaining)
        batches.append(G.sample_batch(rng, size, length, length, cfg))
        remaining -= size
    return batches


def select_circuit(model, cfg, n_examples, seed):
    G.PATCH = None
    total = np.zeros((cfg.n_layers, cfg.n_heads), dtype=np.float64)
    seen = 0
    for x, _, _, aq, tgt in sample_batches(cfg, cfg.l_train, n_examples, seed):
        with torch.no_grad():
            model(x, aq, tgt)
        batch_size = x.shape[0]
        total += np.asarray(model.attn_source_by_head(), dtype=np.float64) * batch_size
        seen += batch_size
    means = total / max(1, seen)
    layer, head = np.unravel_index(np.argmax(means), means.shape)
    return {
        "selection_length": cfg.l_train,
        "selection_seed": seed,
        "selection_examples": seen,
        "selected_layer": int(layer),
        "selected_head": int(head),
        "selected_source_mass": float(means[layer, head]),
        "source_mass_by_layer_head": means.tolist(),
    }


def evaluate_condition(model, batches, layer, head, mode):
    if mode == "baseline":
        G.PATCH = None
    else:
        G.PATCH = {
            "layer": layer,
            "head": head,
            "mode": mode,
            "diagnostics": {},
        }

    exact = []
    token_accuracy = []
    source_mass_sum = entropy_sum = max_weight_sum = output_var_sum = 0.0
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
        block = model.blocks[layer]
        source_mass_sum += block.attn_tgt_heads[head] * batch_size
        entropy_sum += block.attn_ent * batch_size
        max_weight_sum += block.attn_max * batch_size
        output_var_sum += block.z_aq_var * batch_size
        seen += batch_size

    diagnostics = {} if G.PATCH is None else dict(G.PATCH["diagnostics"])
    G.PATCH = None
    return {
        "mode": mode,
        "n_examples": seen,
        "exact_match": float(np.mean(exact)),
        "token_accuracy": float(np.mean(token_accuracy)),
        "selected_head_source_mass": source_mass_sum / max(1, seen),
        "mean_head_entropy": entropy_sum / max(1, seen),
        "mean_head_max_weight": max_weight_sum / max(1, seen),
        "attention_output_var": output_var_sum / max(1, seen),
        "invariant_max_abs_error": diagnostics,
        "per_example_exact": exact,
        "per_example_token_accuracy": token_accuracy,
    }


def bootstrap_interval(delta, rng, draws):
    values = np.asarray(delta, dtype=np.float64)
    if not len(values):
        return [float("nan"), float("nan")]
    means = np.empty(draws, dtype=np.float64)
    chunk = 1000
    for start in range(0, draws, chunk):
        count = min(chunk, draws - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means[start:start + count] = values[indices].mean(axis=1)
    return [float(value) for value in np.quantile(means, [0.025, 0.975])]


def exact_mcnemar(base, intervention):
    base = np.asarray(base, dtype=np.int8)
    intervention = np.asarray(intervention, dtype=np.int8)
    base_only = int(np.sum((base == 1) & (intervention == 0)))
    intervention_only = int(np.sum((base == 0) & (intervention == 1)))
    discordant = base_only + intervention_only
    if discordant == 0:
        p_value = 1.0
    else:
        lower = min(base_only, intervention_only)
        tail = sum(math.comb(discordant, value) for value in range(lower + 1)) / (2 ** discordant)
        p_value = min(1.0, 2.0 * tail)
    return {
        "baseline_only_correct": base_only,
        "intervention_only_correct": intervention_only,
        "discordant_pairs": discordant,
        "two_sided_exact_p": p_value,
    }


def paired_contrast(baseline, intervention, seed, draws):
    base_token = np.asarray(baseline["per_example_token_accuracy"])
    int_token = np.asarray(intervention["per_example_token_accuracy"])
    base_exact = np.asarray(baseline["per_example_exact"])
    int_exact = np.asarray(intervention["per_example_exact"])
    rng = np.random.default_rng(seed)
    return {
        "condition": intervention["mode"],
        "token_accuracy_delta": float(np.mean(int_token - base_token)),
        "token_accuracy_delta_ci95": bootstrap_interval(int_token - base_token, rng, draws),
        "exact_match_delta": float(np.mean(int_exact - base_exact)),
        "exact_match_delta_ci95": bootstrap_interval(int_exact - base_exact, rng, draws),
        "mcnemar_exact_match": exact_mcnemar(base_exact, int_exact),
    }


def run_model(task, pe, seed, args):
    cfg = make_cfg(task, pe, seed, args)
    model, saved_checkpoint = load_or_train(cfg, args)
    train_row = G.evaluate(
        model, cfg, np.random.default_rng(args.eval_seed), [cfg.l_train], n_eval=args.n_eval
    )[0]
    circuit = select_circuit(model, cfg, args.selection_examples, args.selection_seed)
    layer = circuit["selected_layer"]
    head = circuit["selected_head"]
    print(
        f"[circuit] L={cfg.l_train} layer={layer} head={head} "
        f"source_mass={circuit['selected_source_mass']:.4f}",
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
    for length in args.lengths:
        batches = sample_batches(cfg, length, args.n_eval, args.eval_seed)
        conditions = {
            mode: evaluate_condition(model, batches, layer, head, mode)
            for mode in CONDITIONS
        }
        baseline = conditions["baseline"]
        contrasts = [
            paired_contrast(
                baseline,
                conditions[mode],
                args.bootstrap_seed + length + index,
                args.bootstrap_draws,
            )
            for index, mode in enumerate(CONDITIONS[1:])
        ]
        result["lengths"][str(length)] = {
            "conditions": conditions,
            "paired_contrasts_vs_baseline": contrasts,
        }
        compact = {row["condition"]: row for row in contrasts}
        print(
            f"  L={length} tok_delta max/min/control="
            f"{compact['source_max']['token_accuracy_delta']:+.3f}/"
            f"{compact['source_min']['token_accuracy_delta']:+.3f}/"
            f"{compact['distractor_control']['token_accuracy_delta']:+.3f}",
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
    path = os.path.join(args.outdir, "paired_permutation_results.json")
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
