"""Compare fixed-spectrum reassignment with standard clean-to-corrupt activation patching.

The selected layer and heads are calibrated once on a disjoint split. On each held-out
row, the fixed-spectrum condition swaps source and maximum attention weights on the
unaltered prompt. The activation-patching condition replaces the source value with a
different value token, then patches the selected per-head attention outputs from the
clean prompt into that corrupted run. These interventions answer different causal
questions: assignment sensitivity versus component-mediated restoration.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import torch

import pretrained_causal_routing as routing
import pretrained_utility_gap as utility
from real_model_probe import single_token_pool


def run_with_state(model, batch, state):
    routing.PATCH_STATE = state
    routing.EAGER_CAPTURE_LAYER = state["layer"]
    try:
        with torch.no_grad():
            return model(
                batch.tokens,
                attention_mask=batch.attention_mask,
                output_attentions=False,
                use_cache=False,
            )
    finally:
        routing.PATCH_STATE = None
        routing.EAGER_CAPTURE_LAYER = None
        routing.LAST_CAPTURED_ATTENTION = None


def capture_outputs(model, batch, layer, heads):
    state = {
        "layer": layer,
        "heads": heads,
        "mode": "activation_capture",
        "sources": batch.sources,
        "diagnostics": {},
        "valid_mask": batch.attention_mask,
        "capture_head_outputs": True,
    }
    result = run_with_state(model, batch, state)
    cached = state.get("captured_head_outputs")
    if cached is None:
        raise RuntimeError("attention backend did not capture per-head outputs")
    return result, cached


def corrupt_source_values(batch):
    """Replace each labeled source value while preserving prompt length and positions."""
    tokens = batch.tokens.clone()
    replacements = batch.answers.roll(1)
    for index in range(tokens.shape[0]):
        answer = int(batch.answers[index])
        replacement = int(replacements[index])
        if replacement == answer:
            candidates = tokens[index][tokens[index] != answer]
            if not len(candidates):
                raise RuntimeError("could not construct a distinct source-value corruption")
            replacement = int(candidates[0])
        tokens[index, int(batch.sources[index])] = replacement
    return routing.Batch(
        tokens=tokens,
        sources=batch.sources,
        answers=batch.answers,
        attention_mask=batch.attention_mask,
    )


def fixed_margin(logits, answers, competitors):
    return utility.fixed_margin(logits, answers, competitors)


def evaluate_batches(model, batches, layer, heads, seed):
    swap_effects = []
    corruption_effects = []
    patch_rescues = []
    recovered_fractions = []
    swap_displacements = []
    activation_displacements = []
    spectrum_errors = []

    for batch in batches:
        clean, clean_heads = capture_outputs(model, batch, layer, heads)
        clean_logits = clean.logits[:, -1].float()
        clean_competitors = utility.fixed_competitor(clean_logits, batch.answers)
        clean_margin = fixed_margin(clean_logits, batch.answers, clean_competitors)

        swap_state = {
            "layer": layer,
            "heads": heads,
            "mode": "source_max",
            "sources": batch.sources,
            "diagnostics": {},
            "valid_mask": batch.attention_mask,
        }
        swapped = run_with_state(model, batch, swap_state)
        swap_margin = fixed_margin(
            swapped.logits[:, -1].float(), batch.answers, clean_competitors
        )

        corrupt_batch = corrupt_source_values(batch)
        corrupt, corrupt_heads = capture_outputs(model, corrupt_batch, layer, heads)
        corrupt_logits = corrupt.logits[:, -1].float()
        corrupt_competitors = utility.fixed_competitor(corrupt_logits, batch.answers)
        corrupt_margin = fixed_margin(corrupt_logits, batch.answers, corrupt_competitors)

        patch_state = {
            "layer": layer,
            "heads": heads,
            "mode": "activation_patch",
            "sources": corrupt_batch.sources,
            "diagnostics": {},
            "valid_mask": corrupt_batch.attention_mask,
            "cached_head_outputs": clean_heads,
        }
        patched = run_with_state(model, corrupt_batch, patch_state)
        patched_margin = fixed_margin(
            patched.logits[:, -1].float(), batch.answers, corrupt_competitors
        )

        swap_delta = swap_margin - clean_margin
        corruption_delta = corrupt_margin - clean_margin
        rescue = patched_margin - corrupt_margin
        damage = clean_margin - corrupt_margin
        recoverable = damage.abs() > 1e-6
        recovery = torch.full_like(rescue, float("nan"))
        recovery[recoverable] = rescue[recoverable] / damage[recoverable]

        swap_effects.extend(swap_delta.cpu().tolist())
        corruption_effects.extend(corruption_delta.cpu().tolist())
        patch_rescues.extend(rescue.cpu().tolist())
        recovered_fractions.extend(recovery[recoverable].cpu().tolist())

        diagnostics = swap_state["diagnostics"]
        spectrum_errors.append(max(
            diagnostics.get(name, 0.0)
            for name in ("sorted", "entropy", "l1", "l2", "linf")
        ))
        if diagnostics.get("displacement_count", 0):
            swap_displacements.append(
                diagnostics["l1_displacement_sum"] / diagnostics["displacement_count"]
            )
        head_delta = clean_heads[:, heads] - corrupt_heads[:, heads]
        activation_displacements.append(float(head_delta.square().mean().sqrt().cpu()))

    swap = np.asarray(swap_effects, dtype=np.float64)
    corruption = np.asarray(corruption_effects, dtype=np.float64)
    rescue = np.asarray(patch_rescues, dtype=np.float64)
    recovery = np.asarray(recovered_fractions, dtype=np.float64)
    return {
        "n_examples": int(len(swap)),
        "fixed_spectrum_swap_margin_delta": float(swap.mean()),
        "fixed_spectrum_swap_margin_delta_ci95": routing.paired_interval(swap, seed),
        "source_value_corruption_margin_delta": float(corruption.mean()),
        "source_value_corruption_margin_delta_ci95": routing.paired_interval(
            corruption, seed + 1
        ),
        "clean_to_corrupt_activation_patch_rescue": float(rescue.mean()),
        "clean_to_corrupt_activation_patch_rescue_ci95": routing.paired_interval(
            rescue, seed + 2
        ),
        "median_fraction_of_corruption_damage_recovered": (
            float(np.median(recovery)) if len(recovery) else float("nan")
        ),
        "fixed_spectrum_mean_l1_displacement": float(np.mean(swap_displacements)),
        "activation_patch_rms_displacement": float(np.mean(activation_displacements)),
        "fixed_spectrum_max_abs_invariant_error": float(np.max(spectrum_errors)),
    }


def main():
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--length", type=int, default=5)
    parser.add_argument("--n", type=int, default=64)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--format", default="colon_newline", choices=sorted(routing.FORMATS))
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, trust_remote_code=args.trust_remote_code
    )
    model, device = utility.load_model(args, device, dtype)
    separator, terminator = routing.format_tokens(tokenizer, args.format)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * args.length))
    calibration = routing.make_batches(
        pool, args.length, args.calibration_examples, args.batch,
        separator, terminator, np.random.default_rng(100_000 + args.seed), device,
    )
    layer, heads, _ = routing.calibrate_circuit(model, calibration, args.heads)
    batches = routing.make_batches(
        pool, args.length, args.n, args.batch,
        separator, terminator, np.random.default_rng(args.seed), device,
    )
    summary = evaluate_batches(model, batches, layer, heads, args.seed)
    result = {
        "model": args.model,
        "seed": args.seed,
        "selected_layer": layer,
        "selected_heads": heads,
        "summary": summary,
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_activation_patching_baseline.json")
    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
