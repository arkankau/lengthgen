"""Equal-budget selector ablations for fixed-spectrum pretrained interventions."""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import torch

import pretrained_causal_routing as routing
import pretrained_utility_gap as utility
import pretrained_utility_selection as selection
from real_model_probe import single_token_pool


SCORE_KEYS = {
    "source_mass": "mean_source_mass_by_layer_head",
    "transfer_mass": "mean_source_max_transfer_by_layer_head",
    "utility_gap": "mean_utility_gap_by_layer_head",
    "utility_gain": "mean_predicted_gain_by_layer_head",
    "source_gradient": "mean_source_gradient_by_layer_head",
    "gradient_magnitude": "mean_gradient_magnitude_by_layer_head",
}


def build_selectors(calibration, head_count, seed):
    selectors = {}
    for name, key in SCORE_KEYS.items():
        scores = np.asarray(calibration[key], dtype=np.float64)
        layer, heads = selection.select_circuit(scores, head_count)
        selectors[name] = {
            "selected_layer": layer,
            "selected_heads": heads,
            "selected_scores": [float(scores[layer, head]) for head in heads],
        }

    shape = np.asarray(calibration["mean_source_mass_by_layer_head"]).shape
    rng = np.random.default_rng(200_000 + seed)
    random_layer = int(rng.integers(0, shape[0]))
    random_heads = [
        int(value) for value in rng.choice(
            shape[1], size=min(head_count, shape[1]), replace=False
        )
    ]
    selectors["random"] = {
        "selected_layer": random_layer,
        "selected_heads": random_heads,
        "selection_seed": 200_000 + seed,
    }
    return selectors


def effect_records(source_max, control):
    return np.asarray([
        source_max["records"][index]["margin"] - row["margin"]
        for index, row in enumerate(control["records"])
    ], dtype=np.float64)


def main():
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-1.7B")
    parser.add_argument("--length", type=int, default=5)
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--format", default="colon_newline", choices=sorted(routing.FORMATS))
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()

    if args.smoke:
        args.length = 3
        args.n = min(args.n, 8)
        args.calibration_examples = min(args.calibration_examples, 8)
        args.batch = min(args.batch, 2)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, trust_remote_code=args.trust_remote_code
    )
    model, device = utility.load_model(args, device, dtype)
    model.enable_input_require_grads()
    separator, terminator = routing.format_tokens(tokenizer, args.format)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * args.length))

    calibration_rng = np.random.default_rng(100_000 + args.seed)
    calibration_batches = routing.make_batches(
        pool, args.length, args.calibration_examples, args.batch,
        separator, terminator, calibration_rng, device,
    )
    calibration = selection.calibrate_selectors(
        model, calibration_batches, args.heads
    )
    model.disable_input_require_grads()
    selectors = build_selectors(calibration, args.heads, args.seed)

    evaluation_rng = np.random.default_rng(args.seed)
    batches = routing.make_batches(
        pool, args.length, args.n, args.batch,
        separator, terminator, evaluation_rng, device,
    )
    utility_circuit = selectors["utility_gain"]
    baseline = routing.evaluate_condition(
        model, batches,
        utility_circuit["selected_layer"], utility_circuit["selected_heads"],
        "baseline",
    )

    result = {
        "model": args.model,
        "dtype": str(dtype),
        "seed": args.seed,
        "length": args.length,
        "n_examples": args.n,
        "calibration_seed": 100_000 + args.seed,
        "evaluation_seed": args.seed,
        "calibration": calibration,
        "baseline": baseline,
        "selectors": {},
    }
    for index, (name, circuit) in enumerate(selectors.items()):
        layer = circuit["selected_layer"]
        heads = circuit["selected_heads"]
        source_max = routing.evaluate_condition(
            model, batches, layer, heads, "source_max"
        )
        control = routing.evaluate_condition(
            model, batches, layer, heads, "distractor_control"
        )
        effect = effect_records(source_max, control)
        result["selectors"][name] = {
            **circuit,
            "source_max": source_max,
            "distractor_control": control,
            "source_max_minus_control_margin": {
                "mean": float(effect.mean()),
                "ci95": routing.paired_interval(
                    effect, args.seed + 10_000 + index
                ),
                "positive_fraction": float(np.mean(effect > 0)),
            },
        }
        print(
            f"selector={name} layer={layer} heads={heads} "
            f"dmargin={effect.mean():+.3f}",
            flush=True,
        )

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_selector_ablation_results.json")
    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
