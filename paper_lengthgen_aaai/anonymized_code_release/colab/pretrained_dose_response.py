"""Dose-response test for utility-selected pretrained routing interventions."""
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


def paired_effect(intervention, reference):
    return np.asarray([
        intervention["records"][index]["margin"] - row["margin"]
        for index, row in enumerate(reference["records"])
    ], dtype=np.float64)


def summarize(values, seed):
    values = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(values.mean()),
        "ci95": routing.paired_interval(values, seed),
        "positive_fraction": float(np.mean(values > 0)),
    }


def main():
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-1.7B")
    parser.add_argument("--length", type=int, default=5)
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--alphas", default="0,0.25,0.5,0.75,1")
    parser.add_argument("--format", default="colon_newline", choices=sorted(routing.FORMATS))
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()

    alphas = [float(value) for value in args.alphas.split(",") if value]
    if sorted(alphas) != alphas or alphas[0] != 0.0 or alphas[-1] != 1.0:
        raise ValueError("alphas must be ordered and include endpoints 0 and 1")
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
    calibration = selection.calibrate_selectors(model, calibration_batches, args.heads)
    model.disable_input_require_grads()
    circuit = calibration["selectors"]["utility_gain"]
    layer = circuit["selected_layer"]
    heads = circuit["selected_heads"]

    evaluation_rng = np.random.default_rng(args.seed)
    batches = routing.make_batches(
        pool, args.length, args.n, args.batch,
        separator, terminator, evaluation_rng, device,
    )
    baseline = routing.evaluate_condition(model, batches, layer, heads, "baseline")
    result = {
        "model": args.model,
        "dtype": str(dtype),
        "seed": args.seed,
        "length": args.length,
        "alphas": alphas,
        "selected_layer": layer,
        "selected_heads": heads,
        "calibration": calibration,
        "baseline": baseline,
        "dose_response": {},
    }
    for alpha_index, alpha in enumerate(alphas):
        source = routing.evaluate_condition(
            model, batches, layer, heads, "source_max_interp", alpha=alpha
        )
        control = routing.evaluate_condition(
            model, batches, layer, heads,
            "matched_distractor_control_interp", alpha=alpha,
        )
        source_effect = paired_effect(source, baseline)
        control_effect = paired_effect(control, baseline)
        contrast = source_effect - control_effect
        result["dose_response"][str(alpha)] = {
            "source_max": source,
            "matched_control": control,
            "source_vs_baseline": summarize(
                source_effect, args.seed + 10_000 + alpha_index
            ),
            "control_vs_baseline": summarize(
                control_effect, args.seed + 20_000 + alpha_index
            ),
            "source_minus_control": summarize(
                contrast, args.seed + 30_000 + alpha_index
            ),
        }
        print(
            f"alpha={alpha:.2f} source={source_effect.mean():+.3f} "
            f"control={control_effect.mean():+.3f} "
            f"contrast={contrast.mean():+.3f}",
            flush=True,
        )

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_dose_response_results.json")
    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
