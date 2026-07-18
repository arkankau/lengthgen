"""Compare source-mass and utility-gain head selection in a pretrained LM.

The utility selector uses an independent calibration split.  For every layer and
head it estimates the theorem's local source-max term,

    (attention mass transferred to the source)
    * (source-versus-donor downstream utility gap).

Evaluation then freezes the selected circuit and reuses the fixed-spectrum
interventions from ``pretrained_causal_routing.py`` on disjoint examples.
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


def source_max_terms(rows, gradients, sources):
    """Return transfer, utility gap, and predicted gain for final-query rows."""
    if rows.ndim != 3 or gradients.shape != rows.shape:
        raise ValueError("rows and gradients must have shape [batch, heads, keys]")
    if sources.ndim != 1 or sources.shape[0] != rows.shape[0]:
        raise ValueError("sources must have shape [batch]")

    source_index = sources[:, None, None].expand(-1, rows.shape[1], 1)
    donor_index = rows.argmax(dim=-1, keepdim=True)
    source_weight = rows.gather(2, source_index).squeeze(-1)
    donor_weight = rows.gather(2, donor_index).squeeze(-1)
    source_gradient = gradients.gather(2, source_index).squeeze(-1)
    donor_gradient = gradients.gather(2, donor_index).squeeze(-1)
    transfer = donor_weight - source_weight
    utility_gap = source_gradient - donor_gradient
    predicted_gain = transfer * utility_gap
    return transfer, utility_gap, predicted_gain


def select_circuit(scores, head_count):
    """Select one layer and its top-K heads by a precomputed score matrix."""
    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 2 or not scores.size:
        raise ValueError("scores must be a non-empty [layers, heads] matrix")
    if head_count < 1:
        raise ValueError("head_count must be positive")
    if not np.isfinite(scores).any():
        raise ValueError("scores contain no finite values")

    safe = np.where(np.isfinite(scores), scores, -np.inf)
    k = min(head_count, safe.shape[1])
    ranked = np.argsort(-safe, axis=1, kind="stable")[:, :k]
    layer_totals = np.take_along_axis(safe, ranked, axis=1).sum(axis=1)
    layer = int(np.argmax(layer_totals))
    heads = [int(value) for value in ranked[layer]]
    return layer, heads


def calibrate_selectors(model, batches, head_count):
    """Measure source mass and local source-max gain on calibration examples."""
    source_mass_sum = None
    transfer_sum = None
    utility_sum = None
    predicted_gain_sum = None
    source_gradient_sum = None
    gradient_magnitude_sum = None
    positive_utility_count = None
    active_count = None
    seen = 0

    for batch in batches:
        routing.PATCH_STATE = None
        output = model(
            batch.tokens,
            attention_mask=batch.attention_mask,
            output_attentions=True,
            use_cache=False,
        )
        logits = output.logits[:, -1].float()
        competitors = utility.fixed_competitor(logits, batch.answers)
        margins = utility.fixed_margin(logits, batch.answers, competitors)
        attentions = tuple(output.attentions)
        if not all(attention.requires_grad for attention in attentions):
            raise RuntimeError(
                "attention tensors do not carry gradients; enable input gradients before calibration"
            )
        gradients = torch.autograd.grad(margins.sum(), attentions)

        shape = (len(attentions), attentions[0].shape[1])
        if source_mass_sum is None:
            source_mass_sum = np.zeros(shape, dtype=np.float64)
            transfer_sum = np.zeros(shape, dtype=np.float64)
            utility_sum = np.zeros(shape, dtype=np.float64)
            predicted_gain_sum = np.zeros(shape, dtype=np.float64)
            source_gradient_sum = np.zeros(shape, dtype=np.float64)
            gradient_magnitude_sum = np.zeros(shape, dtype=np.float64)
            positive_utility_count = np.zeros(shape, dtype=np.int64)
            active_count = np.zeros(shape, dtype=np.int64)

        for layer, (attention, gradient) in enumerate(zip(attentions, gradients)):
            rows = attention[:, :, -1, :].detach().float()
            grad_rows = gradient[:, :, -1, :].detach().float()
            transfer, utility_gap, predicted_gain = source_max_terms(
                rows, grad_rows, batch.sources
            )
            source_index = batch.sources[:, None, None].expand(-1, rows.shape[1], 1)
            source_mass = rows.gather(2, source_index).squeeze(-1)
            source_gradient = grad_rows.gather(2, source_index).squeeze(-1)
            gradient_magnitude = grad_rows.abs().mean(dim=-1)
            active = transfer.abs() > 1e-8

            source_mass_sum[layer] += source_mass.sum(dim=0).cpu().numpy()
            transfer_sum[layer] += transfer.sum(dim=0).cpu().numpy()
            predicted_gain_sum[layer] += predicted_gain.sum(dim=0).cpu().numpy()
            source_gradient_sum[layer] += source_gradient.sum(dim=0).cpu().numpy()
            gradient_magnitude_sum[layer] += gradient_magnitude.sum(dim=0).cpu().numpy()
            utility_sum[layer] += torch.where(
                active, utility_gap, torch.zeros_like(utility_gap)
            ).sum(dim=0).cpu().numpy()
            positive_utility_count[layer] += (
                active & (utility_gap > 0)
            ).sum(dim=0).cpu().numpy()
            active_count[layer] += active.sum(dim=0).cpu().numpy()
        seen += batch.tokens.shape[0]
        del output, logits, margins, attentions, gradients

    routing.PATCH_STATE = None
    if not seen:
        raise ValueError("calibration requires at least one example")

    mean_source_mass = source_mass_sum / seen
    mean_transfer = transfer_sum / seen
    mean_predicted_gain = predicted_gain_sum / seen
    mean_source_gradient = source_gradient_sum / seen
    mean_gradient_magnitude = gradient_magnitude_sum / seen
    mean_utility_gap = np.divide(
        utility_sum,
        active_count,
        out=np.full_like(utility_sum, np.nan),
        where=active_count > 0,
    )
    positive_utility_fraction = np.divide(
        positive_utility_count,
        active_count,
        out=np.full_like(utility_sum, np.nan),
        where=active_count > 0,
    )

    mass_layer, mass_heads = select_circuit(mean_source_mass, head_count)
    gain_layer, gain_heads = select_circuit(mean_predicted_gain, head_count)
    return {
        "n_examples": seen,
        "mean_source_mass_by_layer_head": mean_source_mass.tolist(),
        "mean_source_max_transfer_by_layer_head": mean_transfer.tolist(),
        "mean_utility_gap_by_layer_head": mean_utility_gap.tolist(),
        "positive_utility_fraction_by_layer_head": positive_utility_fraction.tolist(),
        "mean_predicted_gain_by_layer_head": mean_predicted_gain.tolist(),
        "mean_source_gradient_by_layer_head": mean_source_gradient.tolist(),
        "mean_gradient_magnitude_by_layer_head": mean_gradient_magnitude.tolist(),
        "selectors": {
            "source_mass": {
                "selected_layer": mass_layer,
                "selected_heads": mass_heads,
                "selected_scores": [
                    float(mean_source_mass[mass_layer, head]) for head in mass_heads
                ],
            },
            "utility_gain": {
                "selected_layer": gain_layer,
                "selected_heads": gain_heads,
                "selected_scores": [
                    float(mean_predicted_gain[gain_layer, head]) for head in gain_heads
                ],
                "selected_mean_utility_gaps": [
                    float(mean_utility_gap[gain_layer, head]) for head in gain_heads
                ],
                "selected_positive_utility_fractions": [
                    float(positive_utility_fraction[gain_layer, head])
                    for head in gain_heads
                ],
            },
        },
    }


def effect_records(conditions):
    source_max = conditions["source_max"]["records"]
    control = conditions["distractor_control"]["records"]
    return np.asarray([
        source_max[index]["margin"] - row["margin"]
        for index, row in enumerate(control)
    ], dtype=np.float64)


def selector_difference(source_mass_conditions, utility_conditions, seed):
    """Compare source-max-minus-control effects on the same examples."""
    mass_effect = effect_records(source_mass_conditions)
    utility_effect = effect_records(utility_conditions)
    difference = utility_effect - mass_effect
    return {
        "estimand": "utility_gain_effect_minus_source_mass_effect",
        "mean_margin_difference": float(difference.mean()),
        "mean_margin_difference_ci95": routing.paired_interval(difference, seed),
        "positive_fraction": float(np.mean(difference > 0)),
    }


def main():
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="HuggingFaceTB/SmolLM2-1.7B")
    parser.add_argument("--lengths", default="5,20,80")
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--selection-length", type=int)
    parser.add_argument("--format", default="colon_newline", choices=sorted(routing.FORMATS))
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()

    lengths = [int(value) for value in args.lengths.split(",") if value]
    if args.smoke:
        lengths = [3, 6]
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
    if not hasattr(model, "enable_input_require_grads"):
        raise RuntimeError("model does not support input-gradient calibration")
    model.enable_input_require_grads()

    separator, terminator = routing.format_tokens(tokenizer, args.format)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * max(lengths)))
    selection_length = args.selection_length or min(lengths)
    calibration_rng = np.random.default_rng(100_000 + args.seed)
    calibration_batches = routing.make_batches(
        pool, selection_length, args.calibration_examples, args.batch,
        separator, terminator, calibration_rng, device,
    )
    calibration = calibrate_selectors(model, calibration_batches, args.heads)
    if hasattr(model, "disable_input_require_grads"):
        model.disable_input_require_grads()

    for name, selector in calibration["selectors"].items():
        print(
            f"selector={name} layer={selector['selected_layer']} "
            f"heads={selector['selected_heads']}",
            flush=True,
        )

    result = {
        "model": args.model,
        "dtype": str(dtype),
        "seed": args.seed,
        "format": args.format,
        "selection_length": selection_length,
        "calibration_seed": 100_000 + args.seed,
        "evaluation_seed": args.seed,
        "calibration": calibration,
        "selectors": {
            name: {
                "selected_layer": selector["selected_layer"],
                "selected_heads": selector["selected_heads"],
                "lengths": {},
            }
            for name, selector in calibration["selectors"].items()
        },
        "selector_comparisons": {},
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_utility_selection_results.json")
    evaluation_rng = np.random.default_rng(args.seed)
    modes = ("baseline", "source_max", "source_min", "distractor_control")

    for length in lengths:
        batches = routing.make_batches(
            pool, length, args.n, args.batch,
            separator, terminator, evaluation_rng, device,
        )
        selector_conditions = {}
        for selector_index, (name, selector) in enumerate(
            calibration["selectors"].items()
        ):
            layer = selector["selected_layer"]
            heads = selector["selected_heads"]
            conditions = {
                mode: routing.evaluate_condition(model, batches, layer, heads, mode)
                for mode in modes
            }
            baseline = conditions["baseline"]
            source_control = routing.contrast(
                conditions["distractor_control"],
                conditions["source_max"],
                args.seed + 10_000 * length + selector_index,
            )
            source_control["estimand"] = "source_max_minus_distractor_control"
            result["selectors"][name]["lengths"][str(length)] = {
                "conditions": conditions,
                "contrasts_vs_baseline": [
                    routing.contrast(
                        baseline,
                        conditions[mode],
                        args.seed + 1000 * length + 10 * selector_index + index,
                    )
                    for index, mode in enumerate(modes[1:])
                ],
                "source_max_vs_control": source_control,
            }
            selector_conditions[name] = conditions
            print(
                f"N={length} selector={name} baseline={baseline['accuracy']:.3f} "
                f"max-control dmargin={source_control['margin_delta']:+.3f} "
                f"ci={source_control['margin_delta_ci95']}",
                flush=True,
            )

        result["selector_comparisons"][str(length)] = selector_difference(
            selector_conditions["source_mass"],
            selector_conditions["utility_gain"],
            args.seed + 50_000 + length,
        )
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)

    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
