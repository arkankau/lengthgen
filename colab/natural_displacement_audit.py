"""Re-evaluate frozen natural-QA circuits and record row-level control mismatch."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

import pretrained_causal_routing as routing
import pretrained_natural_mcqa as mcqa
import pretrained_natural_qa as natural
import pretrained_utility_gap as utility


def condition_displacement(condition):
    values = condition["invariant_max_abs_error"].get(
        "mean_l1_displacement_by_example"
    )
    if values is None:
        raise RuntimeError("backend did not record per-example displacement")
    return np.asarray(values, dtype=np.float64)


def main():
    from datasets import load_dataset
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--references", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--dataset", default="rajpurkar/squad")
    parser.add_argument("--split", default="train")
    parser.add_argument("--pool-size", type=int, default=3072)
    parser.add_argument("--max-tokens", type=int, default=384)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--dtype", default="bf16", choices=["fp32", "fp16", "bf16"])
    args = parser.parse_args()

    reference_paths = sorted(Path(args.references).glob("s*/pretrained_natural_mcqa_results.json"))
    if not reference_paths:
        raise FileNotFoundError(f"no reference runs under {args.references}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model_args = argparse.Namespace(
        model=args.model,
        trust_remote_code=False,
        load_in_4bit=False,
    )
    model, device = utility.load_model(model_args, device, dtype)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dataset = load_dataset(args.dataset, split=args.split)

    rows = []
    for path in reference_paths:
        reference = json.loads(path.read_text())
        seed = int(reference["seed"])
        candidates = mcqa.collect_examples(
            tokenizer, dataset, args.pool_size, seed, device, args.max_tokens
        )
        by_id = {example.example_id: example for example in candidates}
        evaluation = [by_id[example_id] for example_id in reference["example_ids"]["evaluation"]]
        batches = natural.collate_batches(
            [example.main for example in evaluation], tokenizer.pad_token_id, args.batch, device
        )
        for selector, circuit in reference["selectors"].items():
            layer = int(circuit["selected_layer"])
            heads = [int(head) for head in circuit["selected_heads"]]
            source = routing.evaluate_condition(
                model, batches, layer, heads, "source_max"
            )
            control = routing.evaluate_condition(
                model, batches, layer, heads, "matched_distractor_control"
            )
            source_l1 = condition_displacement(source)
            control_l1 = condition_displacement(control)
            epsilon = source_l1 - control_l1
            rows.extend({
                "seed": seed,
                "selector": selector,
                "example_id": example_id,
                "source_mean_l1": float(source_value),
                "control_mean_l1": float(control_value),
                "epsilon": float(error),
            } for example_id, source_value, control_value, error in zip(
                reference["example_ids"]["evaluation"], source_l1, control_l1, epsilon
            ))
            print(
                f"seed={seed} selector={selector} median_abs={np.median(np.abs(epsilon)):.6g}",
                flush=True,
            )

    absolute = np.abs(np.asarray([row["epsilon"] for row in rows], dtype=np.float64))
    result = {
        "definition": "epsilon_i = mean-head source-max L1 displacement minus mean-head matched-control L1 displacement",
        "n_rows": len(rows),
        "median_absolute_epsilon": float(np.median(absolute)),
        "p95_absolute_epsilon": float(np.quantile(absolute, 0.95)),
        "max_absolute_epsilon": float(absolute.max()),
        "records": rows,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"saved: {output}", flush=True)


if __name__ == "__main__":
    main()
