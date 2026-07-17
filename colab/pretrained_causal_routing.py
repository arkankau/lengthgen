"""Fixed-spectrum causal routing interventions in pretrained causal LMs.

The task and head calibration match ``real_model_probe.py``, but this runner intervenes inside one
train-length-selected attention layer. It swaps the source weight with the selected head maximum or
minimum, or permutes two distractor weights while preserving the source weight. Every condition reuses
the same examples and preserves the complete attention spectrum of each patched row.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass

import numpy as np
import torch

from real_model_probe import single_token_pool


PATCH_STATE = None
# None keeps every layer eager (needed for calibration). An integer keeps only
# that layer eager; -1 uses fused attention in every layer for plain screening.
EAGER_CAPTURE_LAYER = None
LAST_CAPTURED_ATTENTION = None


def matched_distractor_pair(row, source, target_delta):
    """Choose the distractor swap whose weight gap best matches target_delta."""
    distractors = torch.arange(row.shape[0], device=row.device)
    distractors = distractors[distractors != source]
    if distractors.numel() < 2:
        return None
    indices = distractors.detach().cpu().numpy()
    values = row[distractors].float().detach().cpu().numpy()
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    target = float(target_delta.float().detach().cpu())
    left, right = 0, 1
    best_error = float("inf")
    best_pair = None
    while right < len(order):
        gap = float(sorted_values[right] - sorted_values[left])
        pair = tuple(sorted((int(indices[order[left]]), int(indices[order[right]]))))
        error = abs(gap - target)
        if error < best_error or (error == best_error and (best_pair is None or pair < best_pair)):
            best_error = error
            best_pair = pair
        if gap < target:
            right += 1
        else:
            left += 1
            if left == right:
                right += 1
    return best_pair


def repeat_kv(states, groups):
    if groups == 1:
        return states
    batch, heads, length, dim = states.shape
    states = states[:, :, None, :, :].expand(batch, heads, groups, length, dim)
    return states.reshape(batch, heads * groups, length, dim)


def patch_attention_weights(
    weights, sources, heads, mode, diagnostics, alpha=None, valid_mask=None
):
    """Patch the final query row and return an exact permutation of every selected row."""
    patched = weights.clone()
    before_rows = []
    after_rows = []
    query = weights.shape[-2] - 1
    key_count = weights.shape[-1]
    for batch in range(weights.shape[0]):
        source = int(sources[batch])
        if not 0 <= source < key_count:
            raise ValueError(f"source index {source} outside attention row of length {key_count}")
        if valid_mask is None:
            valid = list(range(key_count))
        else:
            valid = [
                index for index in range(key_count)
                if bool(valid_mask[batch, index].detach().cpu())
            ]
        if source not in valid:
            raise ValueError(f"source index {source} is masked")
        for head_index, head in enumerate(heads):
            row = patched[batch, head, query]
            before_rows.append(row.clone())
            if mode in {"source_max", "source_min", "source_max_interp", "source_min_interp"}:
                choose_max = mode.startswith("source_max")
                valid_index = torch.tensor(valid, device=row.device)
                valid_values = row[valid_index]
                chosen = int(valid_index[
                    valid_values.argmax() if choose_max else valid_values.argmin()
                ])
                target = row.clone()
                if chosen != source:
                    source_weight = target[source].clone()
                    target[source] = target[chosen]
                    target[chosen] = source_weight
                if mode.endswith("_interp"):
                    if alpha is None:
                        raise ValueError("interpolated routing mode requires alpha")
                    patched[batch, head, query] = row + alpha[batch, head_index] * (target - row)
                    row = patched[batch, head, query]
                else:
                    patched[batch, head, query] = target
                    row = patched[batch, head, query]
            elif mode in {
                "distractor_control",
                "distractor_control_interp",
                "matched_distractor_control",
                "matched_distractor_control_interp",
            }:
                distractors = [index for index in valid if index != source]
                if len(distractors) >= 2:
                    target = row.clone()
                    if mode.startswith("matched_"):
                        target_delta = row.max() - row[source]
                        pair = matched_distractor_pair(row, source, target_delta)
                        high, low = pair
                    else:
                        index = torch.tensor(distractors, device=row.device)
                        values = row[index]
                        high = int(index[values.argmax()])
                        low = int(index[values.argmin()])
                    high_weight = target[high].clone()
                    target[high] = target[low]
                    target[low] = high_weight
                    if mode.endswith("_interp"):
                        if alpha is None:
                            raise ValueError("interpolated routing mode requires alpha")
                        patched[batch, head, query] = (
                            row + alpha[batch, head_index] * (target - row)
                        )
                        row = patched[batch, head, query]
                    else:
                        patched[batch, head, query] = target
                        row = patched[batch, head, query]
            else:
                raise ValueError(f"unknown routing mode: {mode}")
            after_rows.append(row.clone())

    if before_rows:
        before = torch.stack(before_rows).float()
        after = torch.stack(after_rows).float()
        displacement = (after - before).abs().sum(dim=-1)
        diagnostics["l1_displacement_sum"] = (
            diagnostics.get("l1_displacement_sum", 0.0)
            + float(displacement.sum().detach().cpu())
        )
        diagnostics["displacement_count"] = (
            diagnostics.get("displacement_count", 0) + int(displacement.numel())
        )
    if before_rows and not mode.endswith("_interp"):
        eps = 1e-12
        errors = {
            "sorted": (before.sort(dim=-1).values - after.sort(dim=-1).values).abs().max(),
            "entropy": (-(before * (before + eps).log()).sum(-1)
                        + (after * (after + eps).log()).sum(-1)).abs().max(),
            "l1": (before.abs().sum(-1) - after.abs().sum(-1)).abs().max(),
            "l2": (before.square().sum(-1) - after.square().sum(-1)).abs().max(),
            "linf": (before.abs().max(-1).values - after.abs().max(-1).values).abs().max(),
        }
        for name, error in errors.items():
            diagnostics[name] = max(diagnostics.get(name, 0.0), float(error.detach().cpu()))
    return patched


def routing_attention_forward(
    module,
    query,
    key,
    value,
    attention_mask,
    scaling=None,
    dropout=0.0,
    softcap=None,
    **kwargs,
):
    """Model-family-neutral eager attention with an optional fixed-spectrum row patch."""
    global LAST_CAPTURED_ATTENTION
    del kwargs
    if scaling is None:
        scaling = module.head_dim ** -0.5
    groups = int(getattr(module, "num_key_value_groups", query.shape[1] // key.shape[1]))
    key_states = repeat_kv(key, groups)
    value_states = repeat_kv(value, groups)
    layer = int(getattr(module, "layer_idx", -1))
    if EAGER_CAPTURE_LAYER is not None and layer != EAGER_CAPTURE_LAYER:
        output = torch.nn.functional.scaled_dot_product_attention(
            query,
            key_states,
            value_states,
            attn_mask=attention_mask,
            dropout_p=dropout if module.training else 0.0,
            scale=scaling,
        )
        return output.transpose(1, 2).contiguous(), None
    weights = torch.matmul(query, key_states.transpose(2, 3)) * scaling
    if softcap is not None:
        weights = torch.tanh(weights / softcap) * softcap
    if attention_mask is not None:
        weights = weights + attention_mask
    weights = torch.softmax(weights, dim=-1, dtype=torch.float32).to(query.dtype)

    state = PATCH_STATE
    if state is not None and layer == state["layer"]:
        weights = patch_attention_weights(
            weights,
            state["sources"],
            state["heads"],
            state["mode"],
            state["diagnostics"],
            state.get("alpha"),
            state.get("valid_mask"),
        )

    weights = torch.nn.functional.dropout(weights, p=dropout, training=module.training)
    if EAGER_CAPTURE_LAYER == layer:
        LAST_CAPTURED_ATTENTION = weights
    output = torch.matmul(weights, value_states)
    return output.transpose(1, 2).contiguous(), weights


def register_attention_backend():
    from transformers import AttentionInterface
    from transformers.masking_utils import ALL_MASK_ATTENTION_FUNCTIONS, eager_mask

    AttentionInterface.register("routing_eager", routing_attention_forward)
    # A custom attention name is otherwise treated as maskless by Transformers.
    ALL_MASK_ATTENTION_FUNCTIONS.register("routing_eager", eager_mask)


@dataclass
class Batch:
    tokens: torch.Tensor
    sources: torch.Tensor
    answers: torch.Tensor
    attention_mask: torch.Tensor | None = None


FORMATS = {
    "colon_newline": (":", "\n"),
    "equals_newline": (" =", "\n"),
    "colon_semicolon": (":", ";\n"),
    "arrow_newline": (" ->", "\n"),
    "is_newline": (" is", "\n"),
}


def format_tokens(tokenizer, name):
    separator_text, terminator_text = FORMATS[name]
    separator = tokenizer.encode(separator_text, add_special_tokens=False)
    terminator = tokenizer.encode(terminator_text, add_special_tokens=False)
    if not separator or not terminator:
        raise ValueError(f"format {name} produced an empty token sequence")
    return separator, terminator


def build_formatted_example(pool, length, separator, terminator, rng):
    picks = rng.choice(len(pool), size=2 * length, replace=False)
    keys = [pool[index] for index in picks[:length]]
    values = [pool[index] for index in picks[length:2 * length]]
    query_pair = int(rng.integers(0, length))
    tokens = []
    for key, value in zip(keys, values):
        tokens += [key] + separator + [value] + terminator
    tokens += [keys[query_pair]] + separator
    source = tokens.index(values[query_pair])
    return tokens, source, values[query_pair]


def make_batches(pool, length, count, batch_size, separator, terminator, rng, device):
    examples = [
        build_formatted_example(pool, length, separator, terminator, rng)
        for _ in range(count)
    ]
    batches = []
    for start in range(0, count, batch_size):
        chunk = examples[start:start + batch_size]
        batches.append(Batch(
            tokens=torch.tensor([row[0] for row in chunk], device=device),
            sources=torch.tensor([row[1] for row in chunk], device=device),
            answers=torch.tensor([row[2] for row in chunk], device=device),
        ))
    return batches


@torch.no_grad()
def calibrate_circuit(model, batches, head_count):
    score = None
    seen = 0
    for batch in batches:
        output = model(
            batch.tokens,
            attention_mask=batch.attention_mask,
            output_attentions=True,
            use_cache=False,
        )
        rows = torch.stack([attention[:, :, -1, :] for attention in output.attentions])
        layers, size, heads, _ = rows.shape
        current = torch.zeros(layers, heads, device=rows.device)
        for index in range(size):
            current += rows[:, index, :, batch.sources[index]]
        score = current if score is None else score + current
        seen += size
    score = score / max(1, seen)
    k = min(head_count, score.shape[1])
    layer_scores = torch.topk(score, k=k, dim=1).values.sum(dim=1)
    layer = int(layer_scores.argmax())
    heads = [int(value) for value in torch.topk(score[layer], k=k).indices]
    return layer, heads, score.detach().float().cpu().tolist()


def point_metrics(logits, answers):
    prediction = logits.argmax(dim=-1)
    target = logits.gather(1, answers[:, None]).squeeze(1)
    competitors = logits.clone()
    competitors.scatter_(1, answers[:, None], float("-inf"))
    margin = target - competitors.max(dim=-1).values
    return prediction.eq(answers).float(), margin.float()


@torch.no_grad()
def evaluate_condition(model, batches, layer, heads, mode, alpha=None):
    global PATCH_STATE, EAGER_CAPTURE_LAYER, LAST_CAPTURED_ATTENTION
    records = []
    diagnostics = {}
    EAGER_CAPTURE_LAYER = layer
    try:
        for batch in batches:
            LAST_CAPTURED_ATTENTION = None
            if mode == "baseline":
                PATCH_STATE = None
            else:
                PATCH_STATE = {
                    "layer": layer,
                    "heads": heads,
                    "mode": mode,
                    "sources": batch.sources,
                    "diagnostics": diagnostics,
                    "valid_mask": batch.attention_mask,
                }
                if mode.endswith("_interp"):
                    if alpha is None or not 0.0 <= alpha <= 1.0:
                        raise ValueError("interpolated condition requires alpha in [0, 1]")
                    PATCH_STATE["alpha"] = torch.full(
                        (batch.tokens.shape[0], len(heads)),
                        float(alpha),
                        device=batch.tokens.device,
                    )
            output = model(
                batch.tokens,
                attention_mask=batch.attention_mask,
                output_attentions=False,
                use_cache=False,
            )
            logits = output.logits[:, -1].float()
            correct, margin = point_metrics(logits, batch.answers)
            predictions = logits.argmax(dim=-1)
            if LAST_CAPTURED_ATTENTION is None:
                raise RuntimeError("selected attention layer was not captured")
            row = LAST_CAPTURED_ATTENTION[:, heads, -1, :].float()
            source_index = batch.sources[:, None, None].expand(-1, len(heads), 1)
            source_mass = row.gather(2, source_index).squeeze(-1).mean(dim=1)
            entropy = -(row * (row + 1e-12).log()).sum(dim=-1).mean(dim=1)
            maximum = row.max(dim=-1).values.mean(dim=1)
            for index in range(batch.tokens.shape[0]):
                records.append({
                    "correct": float(correct[index].cpu()),
                    "margin": float(margin[index].cpu()),
                    "prediction_id": int(predictions[index].cpu()),
                    "target_id": int(batch.answers[index].cpu()),
                    "source_mass": float(source_mass[index].cpu()),
                    "entropy": float(entropy[index].cpu()),
                    "max_weight": float(maximum[index].cpu()),
                })
    finally:
        PATCH_STATE = None
        EAGER_CAPTURE_LAYER = None
        LAST_CAPTURED_ATTENTION = None
    return {
        "mode": mode,
        "alpha": alpha,
        "n_examples": len(records),
        "accuracy": float(np.mean([row["correct"] for row in records])),
        "mean_margin": float(np.mean([row["margin"] for row in records])),
        "mean_source_mass": float(np.mean([row["source_mass"] for row in records])),
        "mean_entropy": float(np.mean([row["entropy"] for row in records])),
        "mean_max_weight": float(np.mean([row["max_weight"] for row in records])),
        "invariant_max_abs_error": diagnostics,
        "records": records,
    }


def paired_interval(values, seed, draws=10000):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    means = []
    for start in range(0, draws, 1000):
        count = min(1000, draws - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means.append(values[indices].mean(axis=1))
    return [float(value) for value in np.quantile(np.concatenate(means), [0.025, 0.975])]


def contrast(baseline, intervention, seed):
    accuracy_delta = [
        intervention["records"][index]["correct"] - row["correct"]
        for index, row in enumerate(baseline["records"])
    ]
    margin_delta = [
        intervention["records"][index]["margin"] - row["margin"]
        for index, row in enumerate(baseline["records"])
    ]
    return {
        "mode": intervention["mode"],
        "accuracy_delta": intervention["accuracy"] - baseline["accuracy"],
        "accuracy_delta_ci95": paired_interval(accuracy_delta, seed),
        "margin_delta": intervention["mean_margin"] - baseline["mean_margin"],
        "margin_delta_ci95": paired_interval(margin_delta, seed + 1),
        "positive_margin_fraction": float(np.mean(np.asarray(margin_delta) > 0)),
        "source_mass_delta": intervention["mean_source_mass"] - baseline["mean_source_mass"],
    }


def dtype_for(name, device):
    if name == "auto":
        return torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    return {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[name]


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--lengths", default="5,20,80,160")
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument(
        "--selection-length",
        type=int,
        help="calibration length; defaults to the shortest evaluation length",
    )
    parser.add_argument("--format", default="colon_newline", choices=sorted(FORMATS))
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true",
                        help="use bitsandbytes NF4 loading for larger open-weight models")
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
    dtype = dtype_for(args.dtype, device)
    register_attention_backend()
    print(f"device={device} dtype={dtype} model={args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    load_kwargs = {
        "dtype": dtype,
        "attn_implementation": "routing_eager",
        "trust_remote_code": args.trust_remote_code,
    }
    if args.load_in_4bit:
        from transformers import BitsAndBytesConfig

        load_kwargs.update(
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
            ),
            device_map="auto",
        )
        model = AutoModelForCausalLM.from_pretrained(args.model, **load_kwargs).eval()
        device = str(model.get_input_embeddings().weight.device)
    else:
        model = AutoModelForCausalLM.from_pretrained(args.model, **load_kwargs).to(device).eval()
    separator, terminator = format_tokens(tokenizer, args.format)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * max(lengths)))
    rng = np.random.default_rng(args.seed)

    selection_length = args.selection_length or min(lengths)
    calibration = make_batches(
        pool,
        selection_length,
        args.calibration_examples,
        args.batch,
        separator,
        terminator,
        rng,
        device,
    )
    layer, heads, score = calibrate_circuit(model, calibration, args.heads)
    print(f"selected layer={layer} heads={heads}")

    result = {
        "model": args.model,
        "dtype": str(dtype),
        "seed": args.seed,
        "format": args.format,
        "selection_length": selection_length,
        "selected_layer": layer,
        "selected_heads": heads,
        "calibration_source_mass_by_layer_head": score,
        "lengths": {},
    }
    modes = ("baseline", "source_max", "source_min", "distractor_control")
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_causal_routing_results.json")
    for length in lengths:
        batches = make_batches(
            pool, length, args.n, args.batch, separator, terminator, rng, device
        )
        conditions = {
            mode: evaluate_condition(model, batches, layer, heads, mode)
            for mode in modes
        }
        baseline = conditions["baseline"]
        result["lengths"][str(length)] = {
            "conditions": conditions,
            "contrasts_vs_baseline": [
                contrast(baseline, conditions[mode], args.seed + 1000 * length + index)
                for index, mode in enumerate(modes[1:])
            ],
        }
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)
        print(
            f"N={length} baseline_acc={baseline['accuracy']:.3f} "
            + " ".join(
                f"{mode} dacc={conditions[mode]['accuracy'] - baseline['accuracy']:+.3f} "
                f"dmargin={conditions[mode]['mean_margin'] - baseline['mean_margin']:+.3f}"
                for mode in modes[1:]
            ),
            flush=True,
        )
    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
