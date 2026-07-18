"""Select a second prompt format using baseline competence on a held-out pilot split."""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import torch

import pretrained_causal_routing as routing
from real_model_probe import single_token_pool


@torch.no_grad()
def evaluate_baseline(model, batches):
    records = []
    for batch in batches:
        logits = model(batch.tokens, use_cache=False).logits[:, -1].float()
        correct, margin = routing.point_metrics(logits, batch.answers)
        records.extend(
            {
                "correct": float(correct[index].cpu()),
                "margin": float(margin[index].cpu()),
            }
            for index in range(batch.tokens.shape[0])
        )
    return {
        "n_examples": len(records),
        "accuracy": float(np.mean([row["correct"] for row in records])),
        "mean_margin": float(np.mean([row["margin"] for row in records])),
        "records": records,
    }


def select_format(results, candidates, lengths, min_short, min_intermediate):
    short, intermediate = str(lengths[0]), str(lengths[1])
    eligible = [
        name for name in candidates
        if results[name][short]["accuracy"] >= min_short
        and results[name][intermediate]["accuracy"] >= min_intermediate
    ]
    if not eligible:
        return None, []
    winner = max(
        eligible,
        key=lambda name: (
            np.mean([results[name][str(length)]["accuracy"] for length in lengths]),
            min(results[name][str(length)]["accuracy"] for length in lengths),
            -candidates.index(name),
        ),
    )
    return winner, eligible


def load_model(args, device, dtype):
    from transformers import AutoModelForCausalLM

    kwargs = {
        "dtype": dtype,
        "attn_implementation": "eager",
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
    return model, device


def main():
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B")
    parser.add_argument("--formats", default="colon_newline,colon_semicolon,arrow_newline,is_newline")
    parser.add_argument("--reference-format", default="colon_newline")
    parser.add_argument("--lengths", default="5,20")
    parser.add_argument("--n", type=int, default=64)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--min-short-accuracy", type=float, default=0.40)
    parser.add_argument("--min-intermediate-accuracy", type=float, default=0.25)
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=31415)
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()

    formats = [value for value in args.formats.split(",") if value]
    unknown = set(formats) - set(routing.FORMATS)
    if unknown:
        raise ValueError(f"unknown formats: {sorted(unknown)}")
    if args.reference_format not in formats:
        raise ValueError("reference format must be included in --formats")
    lengths = [int(value) for value in args.lengths.split(",") if value]
    if len(lengths) != 2:
        raise ValueError("pilot requires exactly two ordered lengths")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    model, device = load_model(args, device, dtype)
    pool = single_token_pool(tokenizer, want=max(1600, 3 * max(lengths)))
    candidates = [name for name in formats if name != args.reference_format]
    result = {
        "model": args.model,
        "dtype": str(dtype),
        "seed": args.seed,
        "reference_format": args.reference_format,
        "candidate_formats": candidates,
        "lengths": lengths,
        "n_examples_per_cell": args.n,
        "competence_gate": {
            "min_short_accuracy": args.min_short_accuracy,
            "min_intermediate_accuracy": args.min_intermediate_accuracy,
        },
        "formats": {},
        "eligible_formats": [],
        "selected_format": None,
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_format_pilot_results.json")
    for format_index, name in enumerate(formats):
        separator, terminator = routing.format_tokens(tokenizer, name)
        cells = {}
        for length in lengths:
            rng = np.random.default_rng(args.seed + 1000 * format_index + length)
            batches = routing.make_batches(
                pool, length, args.n, args.batch,
                separator, terminator, rng, device,
            )
            cells[str(length)] = evaluate_baseline(model, batches)
            print(
                f"format={name} N={length} acc={cells[str(length)]['accuracy']:.3f} "
                f"margin={cells[str(length)]['mean_margin']:+.3f}",
                flush=True,
            )
        result["formats"][name] = cells
        winner, eligible = select_format(
            result["formats"],
            [candidate for candidate in candidates if candidate in result["formats"]],
            lengths,
            args.min_short_accuracy,
            args.min_intermediate_accuracy,
        )
        result["eligible_formats"] = eligible
        result["selected_format"] = winner
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)
    print(f"selected_format={result['selected_format']} eligible={result['eligible_formats']}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
