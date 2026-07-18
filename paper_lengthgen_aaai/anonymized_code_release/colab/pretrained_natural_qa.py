"""Context-grounded natural-language QA test for utility-conditioned routing."""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass

import numpy as np
import torch

import pretrained_causal_routing as routing
import pretrained_utility_gap as utility
import pretrained_utility_selection as selection


@dataclass
class NaturalExample:
    example_id: str
    question: str
    answer: str
    target_answer: str
    main: routing.Batch
    gold_only: routing.Batch
    no_context: routing.Batch


def answer_boundary_target(answer):
    """Return the deterministic sentence-initial answer form used for scoring."""
    stripped = answer.strip()
    if stripped and stripped[0].islower():
        return stripped[0].upper() + stripped[1:]
    return stripped


def sentence_containing(context, answer_start, answer_text, max_chars=320):
    """Extract a sentence-like window and preserve the answer's local offset."""
    answer_end = answer_start + len(answer_text)
    left_candidates = [context.rfind(mark, 0, answer_start) for mark in (". ", "? ", "! ", "\n")]
    left = max(left_candidates)
    left = 0 if left < 0 else left + (1 if context[left] == "\n" else 2)
    right_candidates = []
    for mark in (". ", "? ", "! ", "\n"):
        found = context.find(mark, answer_end)
        if found >= 0:
            right_candidates.append(found + (0 if mark == "\n" else 1))
    right = min(right_candidates) if right_candidates else len(context)
    if right - left > max_chars:
        left = max(left, answer_start - max_chars // 2)
        right = min(right, left + max_chars)
        if right < answer_end:
            right = answer_end
            left = max(0, right - max_chars)
    text = context[left:right].strip()
    stripped_left = len(context[left:right]) - len(context[left:right].lstrip())
    local_start = answer_start - left - stripped_left
    if text[local_start:local_start + len(answer_text)] != answer_text:
        raise ValueError("answer offset was not preserved")
    return text, local_start


def first_sentence(context, max_chars=260):
    match = re.search(r"[.!?](?:\s|$)", context)
    end = match.end() if match else min(len(context), max_chars)
    return context[:min(end, max_chars)].strip()


def assemble_prompt(question, passages, gold_passage_index=None, answer_start=None):
    parts = [
        "Use the passages to answer the question. Reply with only the answer.\n\n"
    ]
    answer_global = None
    for index, passage in enumerate(passages):
        prefix = f"Passage {index + 1}: "
        if index == gold_passage_index:
            answer_global = sum(len(part) for part in parts) + len(prefix) + answer_start
        parts.append(prefix + passage + "\n")
    parts.append(f"\nQuestion: {question}\nAnswer:")
    prompt = "".join(parts)
    return prompt, answer_global


def render_user_prompt(tokenizer, prompt, source_char=None):
    """Apply an instruction model's chat template and preserve source offsets."""
    if tokenizer.chat_template:
        rendered = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
        content_start = rendered.find(prompt)
        if content_start < 0:
            raise ValueError("chat template did not preserve the user prompt")
        rendered_source = None if source_char is None else content_start + source_char
        return rendered, rendered_source, "chat_template"
    return prompt, source_char, "plain_text"


def token_batch(tokenizer, prompt, answer_id, device, source=None):
    token_ids = tokenizer.encode(prompt, add_special_tokens=False)
    return routing.Batch(
        tokens=torch.tensor([token_ids], device=device),
        sources=torch.tensor([0 if source is None else source], device=device),
        answers=torch.tensor([answer_id], device=device),
    )


def collate_batches(batches, pad_token_id, batch_size, device):
    """Left-pad variable prompts so the final query remains the last token."""
    result = []
    for start in range(0, len(batches), batch_size):
        chunk = batches[start:start + batch_size]
        max_length = max(batch.tokens.shape[1] for batch in chunk)
        tokens = torch.full(
            (len(chunk), max_length), pad_token_id, dtype=torch.long, device=device
        )
        attention_mask = torch.zeros_like(tokens)
        sources = []
        answers = []
        for index, batch in enumerate(chunk):
            length = batch.tokens.shape[1]
            padding = max_length - length
            tokens[index, padding:] = batch.tokens[0]
            attention_mask[index, padding:] = 1
            sources.append(int(batch.sources[0]) + padding)
            answers.append(int(batch.answers[0]))
        result.append(routing.Batch(
            tokens=tokens,
            sources=torch.tensor(sources, device=device),
            answers=torch.tensor(answers, device=device),
            attention_mask=attention_mask,
        ))
    return result


def build_example(tokenizer, row, distractors, rng, device, max_tokens):
    answer = row["answers"]["text"][0]
    answer_start = int(row["answers"]["answer_start"][0])
    source_encoding = tokenizer.encode(answer, add_special_tokens=False)
    target_answer = answer_boundary_target(answer)
    target = tokenizer.encode(target_answer, add_special_tokens=False)
    if (
        len(source_encoding) != 1
        or len(target) != 1
        or not target_answer
        or "\n" in answer
    ):
        return None
    gold, local_start = sentence_containing(
        row["context"], answer_start, answer
    )
    passages = [(gold, local_start, True)] + [
        (text, None, False) for text in distractors
    ]
    rng.shuffle(passages)
    gold_index = next(index for index, value in enumerate(passages) if value[2])
    prompt, source_char = assemble_prompt(
        row["question"],
        [value[0] for value in passages],
        gold_passage_index=gold_index,
        answer_start=passages[gold_index][1],
    )
    prompt, source_char, _ = render_user_prompt(tokenizer, prompt, source_char)
    encoded = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
    source_tokens = [
        index for index, (start, end) in enumerate(encoded["offset_mapping"])
        if start < source_char + len(answer) and end > source_char
    ]
    if len(source_tokens) != 1:
        return None
    source = source_tokens[0]
    if len(encoded["input_ids"]) > max_tokens:
        return None

    gold_prompt, _ = assemble_prompt(row["question"], [gold])
    gold_prompt, _, _ = render_user_prompt(tokenizer, gold_prompt)
    no_context_prompt = (
        "Answer the question. Reply with only the answer.\n\n"
        f"Question: {row['question']}\nAnswer:"
    )
    no_context_prompt, _, _ = render_user_prompt(tokenizer, no_context_prompt)
    return NaturalExample(
        example_id=str(row["id"]),
        question=row["question"],
        answer=answer,
        target_answer=target_answer,
        main=routing.Batch(
            tokens=torch.tensor([encoded["input_ids"]], device=device),
            sources=torch.tensor([source], device=device),
            answers=torch.tensor([target[0]], device=device),
        ),
        gold_only=token_batch(tokenizer, gold_prompt, target[0], device),
        no_context=token_batch(tokenizer, no_context_prompt, target[0], device),
    )


def collect_examples(tokenizer, dataset, count, distractor_count, seed, device, max_tokens):
    rng = np.random.default_rng(300_000 + seed)
    order = rng.permutation(len(dataset))
    distractor_pool = [first_sentence(row["context"]) for row in dataset]
    examples = []
    for dataset_index in order:
        choices = []
        while len(choices) < distractor_count:
            candidate = int(rng.integers(0, len(dataset)))
            if candidate != dataset_index and candidate not in choices:
                choices.append(candidate)
        try:
            example = build_example(
                tokenizer,
                dataset[int(dataset_index)],
                [distractor_pool[index] for index in choices],
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


@torch.no_grad()
def evaluate_plain(model, batches):
    correct = []
    margins = []
    prediction_ids = []
    target_ids = []
    for batch in batches:
        logits = model(
            batch.tokens, attention_mask=batch.attention_mask, use_cache=False
        ).logits[:, -1].float()
        current_correct, current_margin = routing.point_metrics(logits, batch.answers)
        predictions = logits.argmax(dim=-1)
        correct.extend(current_correct.cpu().tolist())
        margins.extend(current_margin.cpu().tolist())
        prediction_ids.extend(predictions.cpu().tolist())
        target_ids.extend(batch.answers.cpu().tolist())
    return {
        "n_examples": len(correct),
        "accuracy": float(np.mean(correct)),
        "mean_margin": float(np.mean(margins)),
        "records": [
            {
                "correct": float(value),
                "margin": float(margins[index]),
                "prediction_id": int(prediction_ids[index]),
                "target_id": int(target_ids[index]),
            }
            for index, value in enumerate(correct)
        ],
    }


def effect_records(intervention, reference):
    return np.asarray([
        intervention["records"][index]["margin"] - row["margin"]
        for index, row in enumerate(reference["records"])
    ], dtype=np.float64)


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
    parser.add_argument("--distractors", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--outdir", default=".")
    args = parser.parse_args()

    if args.smoke:
        args.pilot = min(args.pilot, 8)
        args.calibration_examples = min(args.calibration_examples, 8)
        args.n = min(args.n, 8)
        args.batch = min(args.batch, 2)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = routing.dtype_for(args.dtype, device)
    routing.register_attention_backend()
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, trust_remote_code=args.trust_remote_code
    )
    model, device = utility.load_model(args, device, dtype)
    dataset = load_dataset(args.dataset, split=args.split)
    total = args.pilot + args.calibration_examples + args.n
    examples = collect_examples(
        tokenizer, dataset, total, args.distractors, args.seed, device, args.max_tokens
    )
    pilot = examples[:args.pilot]
    calibration_examples = examples[
        args.pilot:args.pilot + args.calibration_examples
    ]
    evaluation = examples[args.pilot + args.calibration_examples:]

    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    def packed(rows, attribute):
        return collate_batches(
            [getattr(example, attribute) for example in rows],
            tokenizer.pad_token_id,
            args.batch,
            device,
        )

    pilot_main = evaluate_plain(model, packed(pilot, "main"))
    pilot_gold = evaluate_plain(model, packed(pilot, "gold_only"))
    pilot_no_context = evaluate_plain(model, packed(pilot, "no_context"))
    context_gain = pilot_main["accuracy"] - pilot_no_context["accuracy"]
    gate_pass = (
        pilot_main["accuracy"] >= 0.50
        and context_gain >= 0.10
        and pilot_gold["accuracy"] + 0.05 >= pilot_main["accuracy"]
    )
    result = {
        "model": args.model,
        "dataset": args.dataset,
        "split": args.split,
        "prompt_protocol": (
            "tokenizer_chat_template" if tokenizer.chat_template else "plain_text"
        ),
        "seed": args.seed,
        "structural_seed": 300_000 + args.seed,
        "pilot": {
            "main": pilot_main,
            "gold_only": pilot_gold,
            "no_context": pilot_no_context,
            "context_accuracy_gain": context_gain,
            "gate_pass": gate_pass,
        },
        "example_ids": {
            "pilot": [example.example_id for example in pilot],
            "calibration": [example.example_id for example in calibration_examples],
            "evaluation": [example.example_id for example in evaluation],
        },
    }
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "pretrained_natural_qa_results.json")
    if not gate_pass:
        with open(path, "w") as handle:
            json.dump(result, handle, indent=2)
        print(
            f"GATE FAIL main={pilot_main['accuracy']:.3f} "
            f"no_context={pilot_no_context['accuracy']:.3f} "
            f"gold={pilot_gold['accuracy']:.3f}",
            flush=True,
        )
        print(f"saved: {path}")
        return

    model.enable_input_require_grads()
    calibration = selection.calibrate_selectors(
        model, packed(calibration_examples, "main"), args.heads
    )
    model.disable_input_require_grads()
    evaluation_batches = packed(evaluation, "main")
    result["calibration"] = calibration
    result["evaluation_controls"] = {
        "gold_only": evaluate_plain(model, packed(evaluation, "gold_only")),
        "no_context": evaluate_plain(model, packed(evaluation, "no_context")),
    }
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
        effect = effect_records(
            conditions["source_max"], conditions["matched_distractor_control"]
        )
        result["selectors"][selector_name] = {
            "selected_layer": layer,
            "selected_heads": heads,
            "conditions": conditions,
            "source_max_minus_matched_control": {
                "mean_margin": float(effect.mean()),
                "ci95": routing.paired_interval(effect, 400_000 + args.seed),
                "positive_fraction": float(np.mean(effect > 0)),
            },
        }
        print(
            f"selector={selector_name} baseline={conditions['baseline']['accuracy']:.3f} "
            f"max-control={effect.mean():+.3f}",
            flush=True,
        )

    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
