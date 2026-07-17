"""Competence-first natural multiple-choice QA with fixed-spectrum routing.

The model freely emits one option label from its full vocabulary. Each example
retains an exact source-token position in a natural SQuAD evidence sentence, so
the same spectrum-preserving causal intervention used by the synthetic tests
can be applied without teacher-forcing an answer prefix. A frozen competence
filter retains only examples answered correctly with evidence, incorrectly
without context, and correctly with the gold passage alone. This prevents
parametric recall from masquerading as evidence routing.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass

import numpy as np
import torch

import pretrained_causal_routing as routing
import pretrained_natural_qa as natural
import pretrained_utility_gap as utility
import pretrained_utility_selection as selection


LABELS = ("A", "B", "C", "D")


@dataclass
class MCExample:
    example_id: str
    question: str
    answer: str
    target_label: str
    main: routing.Batch
    gold_only: routing.Batch
    no_context: routing.Batch


def assemble_prompt(question, passages, options, gold_passage_index=None, answer_start=None):
    parts = [
        "Answer the multiple-choice question using the passages. "
        "Reply with only the option letter.\n\n"
    ]
    answer_global = None
    for index, passage in enumerate(passages):
        prefix = f"Passage {index + 1}: "
        if index == gold_passage_index:
            answer_global = sum(len(part) for part in parts) + len(prefix) + answer_start
        parts.append(prefix + passage + "\n")
    parts.append(f"\nQuestion: {question}\n")
    for label, option in zip(LABELS, options):
        parts.append(f"{label}. {option}\n")
    parts.append("Answer:")
    return "".join(parts), answer_global


def _target_id(tokenizer, label):
    encoded = tokenizer.encode(label, add_special_tokens=False)
    return encoded[0] if len(encoded) == 1 else None


def build_example(tokenizer, row, distractor_rows, rng, device, max_tokens):
    answer = row["answers"]["text"][0].strip()
    answer_start = int(row["answers"]["answer_start"][0])
    if not answer or "\n" in answer:
        return None
    if len(tokenizer.encode(answer, add_special_tokens=False)) != 1:
        return None

    gold, local_start = natural.sentence_containing(
        row["context"], answer_start, row["answers"]["text"][0]
    )
    distractor_passages = [natural.first_sentence(value["context"]) for value in distractor_rows]
    distractor_answers = [value["answers"]["text"][0].strip() for value in distractor_rows]
    options = [answer] + distractor_answers
    if len(set(value.casefold() for value in options)) != len(options):
        return None
    rng.shuffle(options)
    target_label = LABELS[options.index(answer)]
    target_id = _target_id(tokenizer, target_label)
    if target_id is None:
        return None

    passages = [(gold, local_start, True)] + [
        (text, None, False) for text in distractor_passages
    ]
    rng.shuffle(passages)
    gold_index = next(index for index, value in enumerate(passages) if value[2])
    prompt, source_char = assemble_prompt(
        row["question"],
        [value[0] for value in passages],
        options,
        gold_passage_index=gold_index,
        answer_start=passages[gold_index][1],
    )
    prompt, source_char, _ = natural.render_user_prompt(tokenizer, prompt, source_char)
    encoded = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
    source_tokens = [
        index for index, (start, end) in enumerate(encoded["offset_mapping"])
        if start < source_char + len(answer) and end > source_char
    ]
    if len(source_tokens) != 1 or len(encoded["input_ids"]) > max_tokens:
        return None

    gold_prompt, _ = assemble_prompt(row["question"], [gold], options)
    gold_prompt, _, _ = natural.render_user_prompt(tokenizer, gold_prompt)
    no_context_prompt, _ = assemble_prompt(row["question"], [], options)
    no_context_prompt, _, _ = natural.render_user_prompt(tokenizer, no_context_prompt)
    return MCExample(
        example_id=str(row["id"]),
        question=row["question"],
        answer=answer,
        target_label=target_label,
        main=routing.Batch(
            tokens=torch.tensor([encoded["input_ids"]], device=device),
            sources=torch.tensor([source_tokens[0]], device=device),
            answers=torch.tensor([target_id], device=device),
        ),
        gold_only=natural.token_batch(tokenizer, gold_prompt, target_id, device),
        no_context=natural.token_batch(tokenizer, no_context_prompt, target_id, device),
    )


def collect_examples(tokenizer, dataset, count, seed, device, max_tokens):
    rng = np.random.default_rng(610_000 + seed)
    order = rng.permutation(len(dataset))
    examples = []
    for dataset_index in order:
        distractor_indices = []
        while len(distractor_indices) < len(LABELS) - 1:
            candidate = int(rng.integers(0, len(dataset)))
            if candidate != dataset_index and candidate not in distractor_indices:
                distractor_indices.append(candidate)
        try:
            example = build_example(
                tokenizer,
                dataset[int(dataset_index)],
                [dataset[index] for index in distractor_indices],
                rng,
                device,
                max_tokens,
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


def decoded_predictions(tokenizer, evaluation):
    return [
        tokenizer.decode([row["prediction_id"]], skip_special_tokens=True)
        for row in evaluation["records"]
    ]


def generation_text_metrics(text):
    words = [word.casefold() for word in text.split() if word.strip()]
    return {
        "word_count": len(words),
        "repetition_fraction": 0.0 if not words else 1.0 - len(set(words)) / len(words),
    }


@torch.no_grad()
def generate_condition(
    model, tokenizer, examples, layer, heads, mode, max_new_tokens
):
    """Run unconstrained greedy generation with the routing patch active throughout."""
    records = []
    diagnostics = {}
    try:
        for example in examples:
            batch = example.main
            if mode == "baseline":
                routing.PATCH_STATE = None
            else:
                routing.PATCH_STATE = {
                    "layer": layer,
                    "heads": heads,
                    "mode": mode,
                    "sources": batch.sources,
                    "diagnostics": diagnostics,
                    # Each example is unpadded. Generated keys may become valid donors.
                    "valid_mask": None,
                }
            output = model.generate(
                input_ids=batch.tokens,
                attention_mask=torch.ones_like(batch.tokens),
                do_sample=False,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                use_cache=True,
            )
            generated = output[0, batch.tokens.shape[1]:]
            first_id = int(generated[0]) if len(generated) else -1
            text = tokenizer.decode(generated, skip_special_tokens=True)
            records.append({
                "example_id": example.example_id,
                "target_label": example.target_label,
                "target_id": int(batch.answers[0]),
                "first_token_id": first_id,
                "first_token": "" if first_id < 0 else tokenizer.decode(
                    [first_id], skip_special_tokens=True
                ),
                "first_token_correct": float(first_id == int(batch.answers[0])),
                "text": text,
                **generation_text_metrics(text),
            })
    finally:
        routing.PATCH_STATE = None
    return {
        "mode": mode,
        "n_examples": len(records),
        "first_token_accuracy": float(np.mean([
            row["first_token_correct"] for row in records
        ])),
        "mean_repetition_fraction": float(np.mean([
            row["repetition_fraction"] for row in records
        ])),
        "invariant_max_abs_error": diagnostics,
        "records": records,
    }


def competence_indices(main_eval, gold_eval, no_context_eval):
    """Return examples that are both solvable and demonstrably context-dependent."""
    return [
        index
        for index, (main_row, gold_row, no_context_row) in enumerate(zip(
            main_eval["records"], gold_eval["records"], no_context_eval["records"]
        ))
        if main_row["correct"] and gold_row["correct"] and not no_context_row["correct"]
    ]


def main():
    from datasets import load_dataset
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--dataset", default="rajpurkar/squad")
    parser.add_argument("--split", default="validation")
    parser.add_argument("--pilot", type=int, default=64)
    parser.add_argument("--calibration-examples", type=int, default=64)
    parser.add_argument("--n", type=int, default=128)
    parser.add_argument("--pool-multiplier", type=int, default=8)
    parser.add_argument("--generation-examples", type=int, default=16)
    parser.add_argument("--generation-tokens", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=384)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--eval-batch", type=int, default=16)
    parser.add_argument("--screening-batch", type=int, default=16)
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()
    if args.smoke:
        args.pilot = min(args.pilot, 32)
        args.calibration_examples = min(args.calibration_examples, 8)
        args.n = min(args.n, 8)
        args.generation_examples = min(args.generation_examples, 4)
        args.batch = min(args.batch, 2)
        args.screening_batch = min(args.screening_batch, 8)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    model, device = utility.load_model(args, device, dtype)
    dataset = load_dataset(args.dataset, split=args.split)
    required = args.calibration_examples + args.n
    pool_size = max(args.pilot, required * args.pool_multiplier)
    examples = collect_examples(tokenizer, dataset, pool_size, args.seed, device, args.max_tokens)
    print(f"constructed candidate pool: {len(examples)}", flush=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    def packed(rows, attribute, batch_size=None):
        return natural.collate_batches(
            [getattr(example, attribute) for example in rows],
            tokenizer.pad_token_id,
            args.batch if batch_size is None else batch_size,
            device,
        )

    pilot_no_context = natural.evaluate_plain(
        model, packed(examples, "no_context", args.screening_batch)
    )
    print(f"screened no-context: {pilot_no_context['accuracy']:.3f}", flush=True)
    no_context_failed_indices = [
        index for index, row in enumerate(pilot_no_context["records"])
        if not row["correct"]
    ]
    context_candidates = [examples[index] for index in no_context_failed_indices]
    pilot_main = natural.evaluate_plain(
        model, packed(context_candidates, "main", args.screening_batch)
    )
    print(f"rescued with full context: {pilot_main['accuracy']:.3f}", flush=True)
    pilot_gold = natural.evaluate_plain(
        model, packed(context_candidates, "gold_only", args.screening_batch)
    )
    print(f"rescued with gold-only: {pilot_gold['accuracy']:.3f}", flush=True)
    failed_no_context = {
        "records": [pilot_no_context["records"][index] for index in no_context_failed_indices]
    }
    eligible_indices = competence_indices(pilot_main, pilot_gold, failed_no_context)
    gate_pass = len(eligible_indices) >= required
    selected = [context_candidates[index] for index in eligible_indices[:required]]
    calibration_examples = selected[:args.calibration_examples]
    evaluation = selected[args.calibration_examples:]
    result = {
        "protocol": "natural_mcqa_v2_context_dependent",
        "answer_decision": "unconstrained top-1 next token from the full vocabulary",
        "model": args.model,
        "dataset": args.dataset,
        "split": args.split,
        "seed": args.seed,
        "structural_seed": 610_000 + args.seed,
        "pilot": {
            "main": pilot_main,
            "gold_only": pilot_gold,
            "no_context": pilot_no_context,
            "context_accuracy_gain": pilot_main["accuracy"],
            "context_gain_is_conditional": True,
            "no_context_failed_count": len(no_context_failed_indices),
            "conditional_context_rescue_accuracy": pilot_main["accuracy"],
            "candidate_pool_size": len(examples),
            "eligible_count": len(eligible_indices),
            "eligible_rate": len(eligible_indices) / len(examples),
            "eligibility_rule": "main correct AND gold-only correct AND no-context incorrect",
            "gate_pass": gate_pass,
        },
        "example_ids": {
            "candidate_pool": [row.example_id for row in examples],
            "calibration": [row.example_id for row in calibration_examples],
            "evaluation": [row.example_id for row in evaluation],
        },
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_natural_mcqa_results.json")
    if not gate_pass:
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)
        print(
            f"GATE FAIL main={pilot_main['accuracy']:.3f} "
            f"no_context={pilot_no_context['accuracy']:.3f} gold={pilot_gold['accuracy']:.3f} "
            f"eligible={len(eligible_indices)}/{required}",
            flush=True,
        )
        print(f"saved: {path}")
        return

    model.enable_input_require_grads()
    calibration = selection.calibrate_selectors(
        model, packed(calibration_examples, "main"), args.heads
    )
    model.disable_input_require_grads()
    evaluation_batches = packed(evaluation, "main", args.eval_batch)
    result["calibration"] = calibration
    result["selectors"] = {}
    for selector_name in ("source_mass", "utility_gain"):
        circuit = calibration["selectors"][selector_name]
        layer = circuit["selected_layer"]
        heads = circuit["selected_heads"]
        conditions = {
            mode: routing.evaluate_condition(model, evaluation_batches, layer, heads, mode)
            for mode in (
                "baseline", "source_max", "source_min", "matched_distractor_control"
            )
        }
        for condition in conditions.values():
            condition["generated_tokens"] = decoded_predictions(tokenizer, condition)
        effect = natural.effect_records(
            conditions["source_max"], conditions["matched_distractor_control"]
        )
        accuracy_effect = np.asarray([
            conditions["source_max"]["records"][index]["correct"]
            - conditions["matched_distractor_control"]["records"][index]["correct"]
            for index in range(len(effect))
        ])
        result["selectors"][selector_name] = {
            "selected_layer": layer,
            "selected_heads": heads,
            "conditions": conditions,
            "source_max_minus_matched_control": {
                "mean_margin": float(effect.mean()),
                "margin_ci95": routing.paired_interval(effect, 620_000 + args.seed),
                "accuracy_delta": float(accuracy_effect.mean()),
                "accuracy_ci95": routing.paired_interval(accuracy_effect, 630_000 + args.seed),
            },
        }
        print(
            f"selector={selector_name} baseline={conditions['baseline']['accuracy']:.3f} "
            f"max-control={effect.mean():+.3f}",
            flush=True,
        )
    utility_circuit = calibration["selectors"]["utility_gain"]
    generation_examples = evaluation[:min(args.generation_examples, len(evaluation))]
    generation_conditions = {
        mode: generate_condition(
            model,
            tokenizer,
            generation_examples,
            utility_circuit["selected_layer"],
            utility_circuit["selected_heads"],
            mode,
            args.generation_tokens,
        )
        for mode in ("baseline", "source_max", "matched_distractor_control")
    }
    source_generation = np.asarray([
        row["first_token_correct"]
        for row in generation_conditions["source_max"]["records"]
    ])
    control_generation = np.asarray([
        row["first_token_correct"]
        for row in generation_conditions["matched_distractor_control"]["records"]
    ])
    result["free_generation"] = {
        "protocol": "unconstrained greedy decoding with the patch active at every generated step",
        "max_new_tokens": args.generation_tokens,
        "selector": "utility_gain",
        "conditions": generation_conditions,
        "source_max_minus_matched_control_first_token_accuracy": float(
            (source_generation - control_generation).mean()
        ),
        "paired_accuracy_ci95": routing.paired_interval(
            source_generation - control_generation, 640_000 + args.seed
        ),
    }
    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
