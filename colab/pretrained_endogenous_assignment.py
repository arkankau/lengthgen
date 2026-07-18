"""Endogenous assignment bridge using untouched attention rows.

For each key-value instance, the source pair remains in the same slot while only
distractor-pair order changes. Every prompt variant runs through the model without
an internal intervention. Within each base instance, the analysis finds the
smallest sorted-spectrum-distance pair whose source-mass gap exceeds a frozen
threshold, then compares the naturally higher-assignment row with the lower one.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass

import numpy as np
import torch

import pretrained_causal_routing as routing
from real_model_probe import single_token_pool


@dataclass
class Variant:
    base_id: int
    variant_id: int
    tokens: list[int]
    source: int
    answer: int


def build_base(pool, length, rng):
    picks = rng.choice(len(pool), size=2 * length, replace=False)
    keys = [pool[index] for index in picks[:length]]
    values = [pool[index] for index in picks[length:]]
    target = int(rng.integers(0, length))
    source_slot = int(rng.integers(0, length))
    return keys, values, target, source_slot


def render_variant(keys, values, target, source_slot, separator, terminator, order):
    slots = list(order)
    slots.insert(source_slot, target)
    tokens = []
    source = None
    for pair_index in slots:
        tokens.extend([keys[pair_index]] + separator)
        if pair_index == target:
            source = len(tokens)
        tokens.extend([values[pair_index]] + terminator)
    tokens.extend([keys[target]] + separator)
    if source is None:
        raise RuntimeError("source pair was not rendered")
    return tokens, source, values[target]


def make_variants(pool, length, bases, variants, separator, terminator, rng):
    rows = []
    for base_id in range(bases):
        keys, values, target, source_slot = build_base(pool, length, rng)
        distractors = [index for index in range(length) if index != target]
        seen = set()
        attempts = 0
        while len(seen) < variants and attempts < variants * 100:
            attempts += 1
            order = tuple(rng.permutation(distractors).tolist())
            if order in seen:
                continue
            seen.add(order)
            tokens, source, answer = render_variant(
                keys, values, target, source_slot, separator, terminator, order
            )
            rows.append(Variant(base_id, len(seen) - 1, tokens, source, answer))
        if len(seen) != variants:
            raise RuntimeError(f"could only form {len(seen)} variants at length {length}")
    return rows


@torch.no_grad()
def evaluate_variants(model, rows, layer, heads, batch_size, device):
    routing.PATCH_STATE = None
    routing.EAGER_CAPTURE_LAYER = layer
    records = []
    sorted_rows = []
    try:
        for start in range(0, len(rows), batch_size):
            chunk = rows[start:start + batch_size]
            tokens = torch.tensor([row.tokens for row in chunk], device=device)
            sources = torch.tensor([row.source for row in chunk], device=device)
            answers = torch.tensor([row.answer for row in chunk], device=device)
            routing.LAST_CAPTURED_ATTENTION = None
            output = model(tokens, output_attentions=False, use_cache=False)
            if routing.LAST_CAPTURED_ATTENTION is None:
                raise RuntimeError("selected attention layer was not captured")
            attention = routing.LAST_CAPTURED_ATTENTION[:, heads, -1, :].float()
            spectrum = attention.sort(dim=-1, descending=True).values
            source_index = sources[:, None, None].expand(-1, len(heads), 1)
            source_mass = attention.gather(2, source_index).squeeze(-1).mean(dim=1)
            maximum = attention.max(dim=-1).values.mean(dim=1)
            entropy = -(attention * (attention + 1e-12).log()).sum(dim=-1).mean(dim=1)
            logits = output.logits[:, -1].float()
            correct, margin = routing.point_metrics(logits, answers)
            prediction = logits.argmax(dim=-1)
            sorted_rows.append(spectrum.cpu().numpy().astype(np.float32))
            for index, row in enumerate(chunk):
                records.append({
                    "base_id": row.base_id,
                    "variant_id": row.variant_id,
                    "source_position": row.source,
                    "source_mass": float(source_mass[index].cpu()),
                    "max_weight": float(maximum[index].cpu()),
                    "entropy": float(entropy[index].cpu()),
                    "margin": float(margin[index].cpu()),
                    "correct": float(correct[index].cpu()),
                    "prediction_id": int(prediction[index].cpu()),
                    "target_id": row.answer,
                })
    finally:
        routing.PATCH_STATE = None
        routing.EAGER_CAPTURE_LAYER = None
        routing.LAST_CAPTURED_ATTENTION = None
    return records, np.concatenate(sorted_rows, axis=0)


def matched_pairs(records, spectra, minimum_source_gap):
    groups = {}
    for index, row in enumerate(records):
        groups.setdefault(row["base_id"], []).append(index)
    matched = []
    for base_id, indices in sorted(groups.items()):
        candidates = []
        for left_position, left in enumerate(indices):
            for right in indices[left_position + 1:]:
                gap = abs(records[left]["source_mass"] - records[right]["source_mass"])
                if gap < minimum_source_gap:
                    continue
                distance = float(np.abs(spectra[left] - spectra[right]).sum(axis=1).mean())
                candidates.append((distance, -gap, left, right))
        if not candidates:
            continue
        distance, _, left, right = min(candidates)
        if records[left]["source_mass"] < records[right]["source_mass"]:
            left, right = right, left
        high, low = records[left], records[right]
        matched.append({
            "base_id": base_id,
            "high_variant": high["variant_id"],
            "low_variant": low["variant_id"],
            "source_mass_delta": high["source_mass"] - low["source_mass"],
            "margin_delta": high["margin"] - low["margin"],
            "accuracy_delta": high["correct"] - low["correct"],
            "max_weight_delta": high["max_weight"] - low["max_weight"],
            "entropy_delta": high["entropy"] - low["entropy"],
            "sorted_spectrum_l1": distance,
        })
    return matched


def fixed_effects_coefficients(records):
    columns = ("source_mass", "max_weight", "entropy")
    centered_x, centered_y = [], []
    groups = {}
    for row in records:
        groups.setdefault(row["base_id"], []).append(row)
    for rows in groups.values():
        y = np.asarray([row["margin"] for row in rows], dtype=np.float64)
        x = np.asarray([[row[column] for column in columns] for row in rows], dtype=np.float64)
        centered_y.extend((y - y.mean()).tolist())
        centered_x.extend((x - x.mean(axis=0)).tolist())
    coefficient, _, _, _ = np.linalg.lstsq(
        np.asarray(centered_x), np.asarray(centered_y), rcond=None
    )
    return {column: float(value) for column, value in zip(columns, coefficient)}


def paired_interval(values, seed, draws=20_000):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(draws, len(values)))
    return [float(value) for value in np.quantile(values[indices].mean(axis=1), [0.025, 0.975])]


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--lengths", default="20,80")
    parser.add_argument("--bases", type=int, default=128)
    parser.add_argument("--variants", type=int, default=8)
    parser.add_argument("--minimum-source-gap", type=float, default=0.01)
    parser.add_argument("--calibration-length", type=int, default=5)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--format", default="colon_newline", choices=sorted(routing.FORMATS))
    parser.add_argument("--dtype", default="bf16", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()
    lengths = [int(value) for value in args.lengths.split(",") if value]
    if args.smoke:
        lengths = [5]
        args.bases = min(args.bases, 4)
        args.variants = min(args.variants, 3)
        args.calibration_examples = min(args.calibration_examples, 8)
        args.batch = min(args.batch, 2)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=dtype, attn_implementation="routing_eager"
    ).to(device).eval()
    separator, terminator = routing.format_tokens(tokenizer, args.format)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * max(lengths)))

    calibration = routing.make_batches(
        pool, args.calibration_length, args.calibration_examples, args.batch,
        separator, terminator, np.random.default_rng(100_000 + args.seed), device,
    )
    layer, heads, score = routing.calibrate_circuit(model, calibration, args.heads)
    print(f"selected layer={layer} heads={heads}", flush=True)
    os.makedirs(args.outdir, exist_ok=True)
    result = {
        "protocol": "endogenous_distractor_order_assignment",
        "model": args.model,
        "dtype": str(dtype),
        "seed": args.seed,
        "selected_layer": layer,
        "selected_heads": heads,
        "calibration_source_mass_by_layer_head": score,
        "minimum_source_gap": args.minimum_source_gap,
        "lengths": {},
    }
    for length in lengths:
        rows = make_variants(
            pool, length, args.bases, args.variants, separator, terminator,
            np.random.default_rng(700_000 + args.seed * 1_000 + length),
        )
        records, spectra = evaluate_variants(model, rows, layer, heads, args.batch, device)
        pairs = matched_pairs(records, spectra, args.minimum_source_gap)
        margin = [row["margin_delta"] for row in pairs]
        coefficients = fixed_effects_coefficients(records)
        result["lengths"][str(length)] = {
            "n_bases": args.bases,
            "variants_per_base": args.variants,
            "eligible_matched_bases": len(pairs),
            "eligibility_rate": len(pairs) / args.bases,
            "matched_pairs": pairs,
            "mean_matched_margin_delta": float(np.mean(margin)) if margin else float("nan"),
            "matched_margin_ci95": paired_interval(
                margin, 800_000 + args.seed * 100 + length
            ) if margin else [float("nan"), float("nan")],
            "positive_margin_fraction": float(np.mean(np.asarray(margin) > 0)) if margin else float("nan"),
            "fixed_effects_coefficients": coefficients,
            "records": records,
        }
        np.savez_compressed(
            os.path.join(args.outdir, f"endogenous_length{length}_spectra.npz"),
            sorted_attention_rows=spectra,
            tokens=np.asarray([row.tokens for row in rows], dtype=np.int64),
            sources=np.asarray([row.source for row in rows], dtype=np.int64),
            base_ids=np.asarray([row.base_id for row in rows], dtype=np.int64),
            variant_ids=np.asarray([row.variant_id for row in rows], dtype=np.int64),
        )
        print(
            f"length={length} eligible={len(pairs)}/{args.bases} "
            f"dmargin={result['lengths'][str(length)]['mean_matched_margin_delta']:+.3f} "
            f"beta_source={coefficients['source_mass']:+.3f}", flush=True,
        )
        with open(os.path.join(args.outdir, "pretrained_endogenous_assignment_results.json"), "w") as handle:
            json.dump(result, handle, indent=2)


if __name__ == "__main__":
    main()
