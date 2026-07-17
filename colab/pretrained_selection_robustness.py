"""Audit calibration split, head-count, layer, and seed robustness in one pretrained LM."""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import torch

import pretrained_causal_routing as routing
from real_model_probe import single_token_pool


def select_layer_heads(score, head_count):
    score = torch.as_tensor(score)
    k = min(head_count, score.shape[1])
    layer_scores = torch.topk(score, k=k, dim=1).values.sum(dim=1)
    layer = int(layer_scores.argmax())
    heads = [int(value) for value in torch.topk(score[layer], k=k).indices]
    return layer, heads


def heads_in_layer(score, layer, head_count):
    score = torch.as_tensor(score)
    k = min(head_count, score.shape[1])
    return [int(value) for value in torch.topk(score[layer], k=k).indices]


def config_grid(score, seed):
    score_tensor = torch.as_tensor(score)
    configs = []
    for head_count in (2, 4, 8):
        layer, heads = select_layer_heads(score_tensor, head_count)
        configs.append({
            "name": f"selected_k{head_count}",
            "kind": "selected",
            "layer": layer,
            "heads": heads,
        })
    selected_layer, _ = select_layer_heads(score_tensor, 4)
    control_layers = []
    if selected_layer > 0:
        control_layers.append(("adjacent_minus", selected_layer - 1))
    if selected_layer + 1 < score_tensor.shape[0]:
        control_layers.append(("adjacent_plus", selected_layer + 1))
    excluded = {selected_layer}
    excluded.update(layer for _, layer in control_layers)
    candidates = [layer for layer in range(score_tensor.shape[0]) if layer not in excluded]
    if candidates:
        random_layer = int(np.random.default_rng(900_000 + seed).choice(candidates))
        control_layers.append(("random_layer", random_layer))
    for name, layer in control_layers:
        configs.append({
            "name": name,
            "kind": "layer_control",
            "layer": layer,
            "heads": heads_in_layer(score_tensor, layer, 4),
        })
    return configs


def max_control_contrast(conditions, seed):
    source_max = conditions["source_max"]
    control = conditions["distractor_control"]
    accuracy = [
        source_max["records"][index]["correct"] - row["correct"]
        for index, row in enumerate(control["records"])
    ]
    margin = [
        source_max["records"][index]["margin"] - row["margin"]
        for index, row in enumerate(control["records"])
    ]
    return {
        "accuracy_delta": float(np.mean(accuracy)),
        "accuracy_delta_ci95": routing.paired_interval(accuracy, seed),
        "margin_delta": float(np.mean(margin)),
        "margin_delta_ci95": routing.paired_interval(margin, seed + 1),
        "positive_margin_fraction": float(np.mean(np.asarray(margin) > 0)),
    }


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--length", type=int, default=20)
    parser.add_argument("--n", type=int, default=64)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument(
        "--modes",
        default="baseline,source_max,source_min,distractor_control",
        help="comma-separated conditions; source_max and distractor_control are required",
    )
    parser.add_argument("--format", default="colon_newline", choices=sorted(routing.FORMATS))
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()

    seeds = [int(value) for value in args.seeds.split(",") if value]
    modes = tuple(value for value in args.modes.split(",") if value)
    if not {"source_max", "distractor_control"}.issubset(modes):
        raise ValueError("selection robustness requires source_max and distractor_control")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=dtype,
        attn_implementation="routing_eager",
    ).to(device).eval()
    separator, terminator = routing.format_tokens(tokenizer, args.format)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * args.length))

    result = {
        "model": args.model,
        "dtype": str(dtype),
        "format": args.format,
        "length": args.length,
        "n_examples_per_cell": args.n,
        "calibration_examples": args.calibration_examples,
        "modes": modes,
        "seeds": {},
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_selection_robustness_results.json")
    for seed in seeds:
        calibration_rng = np.random.default_rng(100_000 + seed)
        evaluation_rng = np.random.default_rng(seed)
        calibration = routing.make_batches(
            pool, args.length, args.calibration_examples, args.batch,
            separator, terminator, calibration_rng, device,
        )
        _, _, score = routing.calibrate_circuit(model, calibration, 8)
        batches = routing.make_batches(
            pool, args.length, args.n, args.batch,
            separator, terminator, evaluation_rng, device,
        )
        cells = []
        for config in config_grid(score, seed):
            conditions = {
                mode: routing.evaluate_condition(
                    model, batches, config["layer"], config["heads"], mode
                )
                for mode in modes
            }
            cell = {
                **config,
                "conditions": conditions,
                "source_max_vs_control": max_control_contrast(
                    conditions,
                    seed=seed * 10_000 + 900 + len(cells),
                ),
            }
            if "baseline" in conditions:
                cell["contrasts_vs_baseline"] = [
                    routing.contrast(
                        conditions["baseline"],
                        conditions[mode],
                        seed=seed * 10_000 + index,
                    )
                    for index, mode in enumerate(modes)
                    if mode != "baseline"
                ]
            cells.append(cell)
            contrast = cell["source_max_vs_control"]
            print(
                f"seed={seed} {config['name']} layer={config['layer']} "
                f"dacc={contrast['accuracy_delta']:+.3f} "
                f"dmargin={contrast['margin_delta']:+.3f}",
                flush=True,
            )
        result["seeds"][str(seed)] = {
            "calibration_seed": 100_000 + seed,
            "evaluation_seed": seed,
            "calibration_source_mass_by_layer_head": score,
            "cells": cells,
        }
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)

    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
