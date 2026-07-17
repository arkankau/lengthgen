"""Audit the routing utility-gap condition inside pretrained causal LMs."""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import torch

import pretrained_causal_routing as routing
from real_model_probe import single_token_pool


def pearson(left, right):
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    if len(left) < 2 or np.std(left) < 1e-12 or np.std(right) < 1e-12:
        return float("nan")
    return float(np.corrcoef(left, right)[0, 1])


def rankdata(values):
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1)
        start = end
    return ranks


def spearman(left, right):
    return pearson(rankdata(left), rankdata(right))


def fixed_competitor(logits, answers):
    alternatives = logits.detach().clone()
    alternatives.scatter_(1, answers[:, None], float("-inf"))
    return alternatives.argmax(dim=-1)


def fixed_margin(logits, answers, competitors):
    target = logits.gather(1, answers[:, None]).squeeze(1)
    rival = logits.gather(1, competitors[:, None]).squeeze(1)
    return target - rival


def transfer_mass(rows, sources, mode):
    source = rows.gather(2, sources[:, None, None].expand(-1, rows.shape[1], 1)).squeeze(-1)
    chosen = rows.max(dim=-1).values if mode == "source_max" else rows.min(dim=-1).values
    return chosen - source


def evaluate_mode(model, batch, layer, heads, mode):
    batch_size = batch.tokens.shape[0]
    alpha = torch.zeros(batch_size, len(heads), device=batch.tokens.device, requires_grad=True)
    routing.PATCH_STATE = {
        "layer": layer,
        "heads": heads,
        "mode": f"{mode}_interp",
        "sources": batch.sources,
        "diagnostics": {},
        "alpha": alpha,
    }
    natural = model(
        batch.tokens,
        attention_mask=batch.attention_mask,
        output_attentions=True,
        use_cache=False,
    )
    logits0 = natural.logits[:, -1].float()
    competitors = fixed_competitor(logits0, batch.answers)
    margin0 = fixed_margin(logits0, batch.answers, competitors)
    gradient = torch.autograd.grad(margin0.sum(), alpha)[0].detach().float()
    rows = natural.attentions[layer][:, heads, -1, :].detach().float()
    transfers = transfer_mass(rows, batch.sources, mode)

    routing.PATCH_STATE = {
        "layer": layer,
        "heads": heads,
        "mode": mode,
        "sources": batch.sources,
        "diagnostics": {},
    }
    with torch.no_grad():
        swapped = model(
            batch.tokens,
            attention_mask=batch.attention_mask,
            output_attentions=True,
            use_cache=False,
        )
        logits1 = swapped.logits[:, -1].float()
        margin1 = fixed_margin(logits1, batch.answers, competitors)
        correct0 = logits0.argmax(dim=-1).eq(batch.answers)
        correct1 = logits1.argmax(dim=-1).eq(batch.answers)
    routing.PATCH_STATE = None

    records = []
    for index in range(batch_size):
        transfer = transfers[index]
        contribution = gradient[index]
        active = transfer.abs() > 1e-8
        utility = torch.full_like(transfer, float("nan"))
        utility[active] = contribution[active] / transfer[active]
        exact = margin1[index] - margin0[index].detach()
        first_order = contribution.sum()
        records.append({
            "mode": mode,
            "correct_natural": float(correct0[index].cpu()),
            "correct_swapped": float(correct1[index].cpu()),
            "margin_natural": float(margin0[index].detach().cpu()),
            "margin_swapped": float(margin1[index].cpu()),
            "exact_margin_delta": float(exact.cpu()),
            "first_order_margin_delta": float(first_order.cpu()),
            "residual": float((exact - first_order).cpu()),
            "transfer_by_head": transfer.cpu().tolist(),
            "contribution_by_head": contribution.cpu().tolist(),
            "utility_gap_by_head": utility.cpu().tolist(),
        })
    return records


def summarize(records, seed):
    exact = np.asarray([row["exact_margin_delta"] for row in records], dtype=np.float64)
    first = np.asarray([row["first_order_margin_delta"] for row in records], dtype=np.float64)
    utility = []
    for row in records:
        utility.extend(value for value in row["utility_gap_by_head"] if math.isfinite(value))
    utility = np.asarray(utility, dtype=np.float64)
    return {
        "n_examples": len(records),
        "mean_exact_margin_delta": float(exact.mean()),
        "mean_exact_margin_delta_ci95": routing.paired_interval(exact, seed),
        "mean_first_order_margin_delta": float(first.mean()),
        "mean_absolute_residual": float(np.abs(exact - first).mean()),
        "pearson_first_order_exact": pearson(first, exact),
        "spearman_first_order_exact": spearman(first, exact),
        "sign_agreement": float(np.mean(np.sign(first) == np.sign(exact))),
        "active_head_count": int(len(utility)),
        "mean_utility_gap": float(utility.mean()) if len(utility) else float("nan"),
        "positive_utility_fraction": float(np.mean(utility > 0)) if len(utility) else float("nan"),
    }


def load_model(args, device, dtype):
    from transformers import AutoModelForCausalLM

    kwargs = {
        "dtype": dtype,
        "attn_implementation": "routing_eager",
        "trust_remote_code": args.trust_remote_code,
    }
    if args.load_in_4bit:
        from transformers import BitsAndBytesConfig

        kwargs.update(
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype,
            ),
            device_map="auto",
        )
        model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs).eval()
        device = str(model.get_input_embeddings().weight.device)
    else:
        model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs).to(device).eval()
    model.requires_grad_(False)
    return model, device


def main():
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--lengths", default="5,20")
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

    lengths = [int(value) for value in args.lengths.split(",") if value]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    model, device = load_model(args, device, dtype)
    separator, terminator = routing.format_tokens(tokenizer, args.format)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * max(lengths)))

    calibration_rng = np.random.default_rng(100_000 + args.seed)
    calibration = routing.make_batches(
        pool, min(lengths), args.calibration_examples, args.batch,
        separator, terminator, calibration_rng, device,
    )
    layer, heads, score = routing.calibrate_circuit(model, calibration, args.heads)
    print(f"model={args.model} layer={layer} heads={heads}", flush=True)

    result = {
        "model": args.model,
        "dtype": str(dtype),
        "seed": args.seed,
        "format": args.format,
        "selected_layer": layer,
        "selected_heads": heads,
        "calibration_source_mass_by_layer_head": score,
        "lengths": {},
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_utility_gap_results.json")
    evaluation_rng = np.random.default_rng(args.seed)
    for length in lengths:
        batches = routing.make_batches(
            pool, length, args.n, args.batch,
            separator, terminator, evaluation_rng, device,
        )
        mode_results = {}
        for mode_index, mode in enumerate(("source_max", "source_min")):
            records = []
            for batch in batches:
                records.extend(evaluate_mode(model, batch, layer, heads, mode))
            mode_results[mode] = {
                "summary": summarize(records, args.seed + 1000 * length + mode_index),
                "records": records,
            }
            summary = mode_results[mode]["summary"]
            print(
                f"N={length} {mode} exact={summary['mean_exact_margin_delta']:+.3f} "
                f"first={summary['mean_first_order_margin_delta']:+.3f} "
                f"utility+={summary['positive_utility_fraction']:.3f}",
                flush=True,
            )
        result["lengths"][str(length)] = mode_results
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)

    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
