"""Frozen-circuit natural-QA length ladder.

Each SQuAD question is rendered at nested passage counts. The gold passage,
answer options, and answer target are identical across lengths; longer prompts
only append unrelated passages. Competence filtering and circuit calibration
use the shortest context, after which the circuit is frozen for every length.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass

import numpy as np
import torch

import pretrained_causal_routing as routing
import pretrained_natural_mcqa as mcqa
import pretrained_natural_qa as natural
import pretrained_utility_gap as utility
import pretrained_utility_selection as selection


@dataclass
class LadderExample:
    example_id: str
    question: str
    answer: str
    target_label: str
    variants: dict[int, routing.Batch]
    gold_only: routing.Batch
    no_context: routing.Batch


def write_json_atomic(path, payload):
    """Checkpoint a result without exposing a partially written JSON file."""
    temporary = f"{path}.tmp"
    with open(temporary, "w") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(temporary, path)


def nested_passages(gold, distractors, gold_slot, lengths):
    """Return nested passage lists with a fixed gold slot."""
    maximum = max(lengths)
    values = list(distractors[: maximum - 1])
    values.insert(gold_slot, gold)
    return {length: values[:length] for length in lengths}


def passage_snippet(text, max_words=16):
    """Keep distractors natural while bounding quadratic attention cost."""
    return " ".join(natural.first_sentence(text).split()[:max_words])


def build_example(tokenizer, row, distractor_rows, rng, device, max_tokens, lengths):
    raw_answer = row["answers"]["text"][0]
    answer = raw_answer.strip()
    answer_start = int(row["answers"]["answer_start"][0])
    if not answer or "\n" in answer:
        return None
    if len(tokenizer.encode(answer, add_special_tokens=False)) != 1:
        return None

    gold, local_start = natural.sentence_containing(row["context"], answer_start, raw_answer)
    option_answers = [value["answers"]["text"][0].strip() for value in distractor_rows[:3]]
    options = [answer] + option_answers
    if any(not value for value in options):
        return None
    if len(set(value.casefold() for value in options)) != len(options):
        return None
    rng.shuffle(options)
    target_label = mcqa.LABELS[options.index(answer)]
    target_id = mcqa._target_id(tokenizer, target_label)
    if target_id is None:
        return None

    distractors = [
        (passage_snippet(value["context"]), None, False)
        for value in distractor_rows
    ]
    gold_value = (gold, local_start, True)
    gold_slot = int(rng.integers(0, min(lengths)))
    variants = {}
    for length, passages in nested_passages(gold_value, distractors, gold_slot, lengths).items():
        prompt, source_char = mcqa.assemble_prompt(
            row["question"],
            [value[0] for value in passages],
            options,
            gold_passage_index=gold_slot,
            answer_start=local_start,
        )
        prompt, source_char, _ = natural.render_user_prompt(tokenizer, prompt, source_char)
        encoded = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
        source_tokens = [
            index for index, (start, end) in enumerate(encoded["offset_mapping"])
            if start < source_char + len(answer) and end > source_char
        ]
        if len(source_tokens) != 1 or len(encoded["input_ids"]) > max_tokens:
            return None
        variants[length] = routing.Batch(
            tokens=torch.tensor([encoded["input_ids"]], device=device),
            sources=torch.tensor([source_tokens[0]], device=device),
            answers=torch.tensor([target_id], device=device),
        )

    gold_prompt, _ = mcqa.assemble_prompt(row["question"], [gold], options)
    gold_prompt, _, _ = natural.render_user_prompt(tokenizer, gold_prompt)
    no_context_prompt, _ = mcqa.assemble_prompt(row["question"], [], options)
    no_context_prompt, _, _ = natural.render_user_prompt(tokenizer, no_context_prompt)
    return LadderExample(
        example_id=str(row["id"]),
        question=row["question"],
        answer=answer,
        target_label=target_label,
        variants=variants,
        gold_only=natural.token_batch(tokenizer, gold_prompt, target_id, device),
        no_context=natural.token_batch(tokenizer, no_context_prompt, target_id, device),
    )


def collect_examples(tokenizer, dataset, count, seed, device, max_tokens, lengths):
    rng = np.random.default_rng(680_000 + seed)
    order = rng.permutation(len(dataset))
    examples = []
    needed_distractors = max(lengths) - 1
    for dataset_index in order:
        candidates = []
        while len(candidates) < needed_distractors:
            candidate = int(rng.integers(0, len(dataset)))
            if candidate != dataset_index and candidate not in candidates:
                candidates.append(candidate)
        try:
            example = build_example(
                tokenizer,
                dataset[int(dataset_index)],
                [dataset[index] for index in candidates],
                rng,
                device,
                max_tokens,
                lengths,
            )
        except (ValueError, IndexError):
            continue
        if example is not None:
            examples.append(example)
        if len(examples) >= count:
            break
    if len(examples) < count:
        raise RuntimeError(f"only constructed {len(examples)} of {count} required examples")
    return examples


def main():
    from datasets import load_dataset
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--dataset", default="rajpurkar/squad")
    parser.add_argument("--split", default="validation")
    parser.add_argument("--lengths", nargs="+", type=int, default=[4, 8, 16, 32])
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--pool-multiplier", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--eval-batch", type=int, default=8)
    parser.add_argument("--screening-batch", type=int, default=16)
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()
    args.lengths = sorted(set(args.lengths))
    if min(args.lengths) < 4:
        raise ValueError("the shortest ladder context must contain at least four passages")
    if args.smoke:
        args.calibration_examples = min(args.calibration_examples, 8)
        args.n = min(args.n, 8)
        # Preserve enough candidates to exercise calibration/intervention code.
        args.pool_multiplier = min(args.pool_multiplier, 8)
        args.batch = min(args.batch, 2)
        args.eval_batch = min(args.eval_batch, 4)
        args.screening_batch = min(args.screening_batch, 8)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    model, device = utility.load_model(args, device, dtype)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dataset = load_dataset(args.dataset, split=args.split)
    required = args.calibration_examples + args.n
    pool_size = required * args.pool_multiplier
    examples = collect_examples(
        tokenizer, dataset, pool_size, args.seed, device, args.max_tokens, args.lengths
    )
    shortest = min(args.lengths)
    print(f"constructed nested candidate pool: {len(examples)}", flush=True)

    def packed(rows, attribute=None, length=None, batch_size=None):
        batches = [
            row.variants[length] if length is not None else getattr(row, attribute)
            for row in rows
        ]
        return natural.collate_batches(
            batches,
            tokenizer.pad_token_id,
            args.batch if batch_size is None else batch_size,
            device,
        )

    routing.EAGER_CAPTURE_LAYER = -1
    no_context = natural.evaluate_plain(
        model, packed(examples, attribute="no_context", batch_size=args.screening_batch)
    )
    failed_indices = [
        index for index, row in enumerate(no_context["records"]) if not row["correct"]
    ]
    candidates = [examples[index] for index in failed_indices]
    shortest_eval = natural.evaluate_plain(
        model, packed(candidates, length=shortest, batch_size=args.screening_batch)
    )
    gold_eval = natural.evaluate_plain(
        model, packed(candidates, attribute="gold_only", batch_size=args.screening_batch)
    )
    routing.EAGER_CAPTURE_LAYER = None
    failed_no_context = {"records": [no_context["records"][index] for index in failed_indices]}
    eligible_indices = mcqa.competence_indices(shortest_eval, gold_eval, failed_no_context)
    gate_pass = len(eligible_indices) >= required
    selected = [candidates[index] for index in eligible_indices[:required]]
    calibration_examples = selected[:args.calibration_examples]
    evaluation_examples = selected[args.calibration_examples:]
    result = {
        "protocol": "natural_mcqa_nested_length_ladder_v1",
        "model": args.model,
        "dataset": args.dataset,
        "seed": args.seed,
        "structural_seed": 680_000 + args.seed,
        "passage_counts": args.lengths,
        "frozen_at_passage_count": shortest,
        "nesting_rule": "gold slot, answer options, and existing passages fixed; unrelated passages appended",
        "distractor_passage_rule": "first 16 whitespace-delimited words of the first natural sentence",
        "pilot": {
            "gate_pass": gate_pass,
            "candidate_pool_size": len(examples),
            "no_context_accuracy": no_context["accuracy"],
            "shortest_context_accuracy_on_no_context_failures": shortest_eval["accuracy"],
            "gold_only_accuracy_on_no_context_failures": gold_eval["accuracy"],
            "eligible_count": len(eligible_indices),
            "eligibility_rule": "shortest context correct AND gold-only correct AND no-context incorrect",
        },
        "example_ids": {
            "calibration": [row.example_id for row in calibration_examples],
            "evaluation": [row.example_id for row in evaluation_examples],
        },
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_natural_mcqa_ladder_results.json")
    prior_lengths = {}
    prior_circuit = None
    if os.path.exists(path):
        with open(path) as handle:
            prior = json.load(handle)
        same_run = (
            prior.get("protocol") == result["protocol"]
            and prior.get("model") == result["model"]
            and int(prior.get("seed", -1)) == result["seed"]
            and prior.get("passage_counts") == result["passage_counts"]
            and prior.get("example_ids") == result["example_ids"]
        )
        if same_run:
            prior_lengths = prior.get("lengths", {})
            prior_circuit = prior.get("frozen_circuit")
            print(f"resume checkpoint found with lengths={sorted(prior_lengths)}", flush=True)
    result["lengths"] = prior_lengths
    if not gate_pass:
        write_json_atomic(path, result)
        print(f"GATE FAIL eligible={len(eligible_indices)}/{required}", flush=True)
        print(f"saved: {path}")
        return

    write_json_atomic(path, result)

    model.enable_input_require_grads()
    calibration = selection.calibrate_selectors(
        model, packed(calibration_examples, length=shortest), args.heads
    )
    model.disable_input_require_grads()
    circuit = calibration["selectors"]["utility_gain"]
    result["calibration"] = calibration
    result["frozen_circuit"] = {
        "selector": "utility_gain",
        "selected_layer": circuit["selected_layer"],
        "selected_heads": circuit["selected_heads"],
    }
    if prior_circuit is not None and prior_circuit != result["frozen_circuit"]:
        raise RuntimeError("resume checkpoint selected a different frozen circuit")
    write_json_atomic(path, result)
    for length in args.lengths:
        if str(length) in result["lengths"]:
            print(f"passages={length} resume checkpoint already complete", flush=True)
            continue
        token_lengths = [row.variants[length].tokens.shape[1] for row in evaluation_examples]
        batches = packed(evaluation_examples, length=length, batch_size=args.eval_batch)
        conditions = {
            mode: routing.evaluate_condition(
                model,
                batches,
                circuit["selected_layer"],
                circuit["selected_heads"],
                mode,
            )
            for mode in ("baseline", "source_max", "matched_distractor_control")
        }
        for condition in conditions.values():
            condition["generated_tokens"] = mcqa.decoded_predictions(tokenizer, condition)
        effect = natural.effect_records(
            conditions["source_max"], conditions["matched_distractor_control"]
        )
        result["lengths"][str(length)] = {
            "prompt_token_lengths": {
                "minimum": int(min(token_lengths)),
                "mean": float(np.mean(token_lengths)),
                "maximum": int(max(token_lengths)),
            },
            "conditions": conditions,
            "source_max_minus_control_mean_margin": float(effect.mean()),
            "source_max_minus_control_margin_ci95": routing.paired_interval(
                effect, 690_000 + 100 * args.seed + length
            ),
        }
        write_json_atomic(path, result)
        print(
            f"passages={length} baseline_acc={conditions['baseline']['accuracy']:.3f} "
            f"baseline_margin={conditions['baseline']['mean_margin']:+.3f} "
            f"max-control={effect.mean():+.3f}",
            flush=True,
        )
    write_json_atomic(path, result)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
