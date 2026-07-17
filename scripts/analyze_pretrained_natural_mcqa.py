"""Aggregate the competence-first natural multiple-choice QA runs."""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

from analyze_pretrained_utility_selection import hierarchical_interval


def _effect(result, selector, field):
    row = result["selectors"][selector]["conditions"]
    source = row["source_max"]["records"]
    control = row["matched_distractor_control"]["records"]
    return np.asarray([
        source[index][field] - value[field]
        for index, value in enumerate(control)
    ], dtype=np.float64)


def _generation_effect(result, field):
    conditions = result["free_generation"]["conditions"]
    source = conditions["source_max"]["records"]
    control = conditions["matched_distractor_control"]["records"]
    return np.asarray([
        source[index][field] - value[field]
        for index, value in enumerate(control)
    ], dtype=np.float64)


def _summary(groups, seed):
    values = np.concatenate(groups)
    return {
        "n_seeds": len(groups),
        "n_examples": int(len(values)),
        "mean": float(values.mean()),
        "ci95": hierarchical_interval(groups, seed),
        "seed_means": [float(group.mean()) for group in groups],
    }


def _pilot_metrics(result):
    pilot = result["pilot"]
    if pilot.get("context_gain_is_conditional"):
        main_accuracy = pilot["main"]["accuracy"]
        gold_accuracy = pilot["gold_only"]["accuracy"]
    else:
        failed = [
            index for index, row in enumerate(pilot["no_context"]["records"])
            if not row["correct"]
        ]
        main_accuracy = float(np.mean([
            pilot["main"]["records"][index]["correct"] for index in failed
        ]))
        gold_accuracy = float(np.mean([
            pilot["gold_only"]["records"][index]["correct"] for index in failed
        ]))
    return {
        "main_accuracy": main_accuracy,
        "gold_only_accuracy": gold_accuracy,
        "no_context_accuracy": pilot["no_context"]["accuracy"],
        "context_gain": main_accuracy,
        "eligible_count": pilot.get("eligible_count"),
        "eligible_rate": pilot.get("eligible_rate"),
    }


def aggregate(results, expected_seeds=(0, 1, 2)):
    ordered = sorted(results, key=lambda row: int(row["seed"]))
    gates = {int(row["seed"]): bool(row["pilot"]["gate_pass"]) for row in ordered}
    passing = [row for row in ordered if row["pilot"]["gate_pass"]]
    effects = {}
    for index, selector in enumerate(("source_mass", "utility_gain")):
        eligible = [row for row in passing if selector in row.get("selectors", {})]
        if not eligible:
            continue
        effects[selector] = {
            "margin": _summary(
                [_effect(row, selector, "margin") for row in eligible], 700_000 + index
            ),
            "next_token_accuracy": _summary(
                [_effect(row, selector, "correct") for row in eligible], 710_000 + index
            ),
        }
    generated = [row for row in passing if "free_generation" in row]
    free_generation = {}
    if generated:
        free_generation = {
            "first_token_accuracy": _summary(
                [_generation_effect(row, "first_token_correct") for row in generated],
                720_000,
            ),
            "repetition_fraction": _summary(
                [_generation_effect(row, "repetition_fraction") for row in generated],
                730_000,
            ),
        }
    enough_competent = len(passing) >= 2
    utility = effects.get("utility_gain")
    stage1_success = bool(
        enough_competent
        and utility
        and utility["margin"]["ci95"][0] > 0
        and free_generation
        and len(generated) >= 2
        and free_generation["first_token_accuracy"]["ci95"][0] >= 0
    )
    full_size_seeds = [
        int(row["seed"]) for row in passing
        if len(row.get("example_ids", {}).get("calibration", [])) >= 64
        and len(row.get("example_ids", {}).get("evaluation", [])) >= 128
        and row.get("free_generation", {}).get("conditions", {})
        .get("baseline", {}).get("n_examples", 0) >= 16
    ]
    success = bool(stage1_success and len(full_size_seeds) >= 2)
    return {
        "expected_seeds": list(expected_seeds),
        "available_seeds": [int(row["seed"]) for row in ordered],
        "missing_seeds": sorted(set(expected_seeds) - set(gates)),
        "competence_gates": gates,
        "passing_seeds": [int(row["seed"]) for row in passing],
        "pilot_metrics": {str(row["seed"]): _pilot_metrics(row) for row in ordered},
        "effects": effects,
        "free_generation": free_generation,
        "stage1_replicated_success": stage1_success,
        "full_size_seeds": full_size_seeds,
        "preregistered_success": success,
        "variable_evidence_triggered": stage1_success,
    }


def markdown(summary):
    lines = [
        "# Natural Multiple-Choice QA Summary",
        "",
        f"Stage-1 replicated success: **{'pass' if summary['stage1_replicated_success'] else 'fail'}**.",
        f"Full-size preregistered result: **{'pass' if summary['preregistered_success'] else 'pending'}**.",
        f"Full-size seeds: `{summary['full_size_seeds']}`.",
        f"Competent seeds: `{summary['passing_seeds']}`.",
        "",
        "| Seed | Full context on no-context failures | Gold only | No context (pool) | Rescue rate | Gate |",
        "|---:|---:|---:|---:|---:|:---:|",
    ]
    for seed, row in summary["pilot_metrics"].items():
        lines.append(
            f"| {seed} | {row['main_accuracy']:.3f} | {row['gold_only_accuracy']:.3f} | "
            f"{row['no_context_accuracy']:.3f} | {row['context_gain']:+.3f} | "
            f"{'pass' if summary['competence_gates'][int(seed)] else 'fail'} |"
        )
    if summary["effects"]:
        lines += [
            "",
            "| Selector | Margin max-control | 95% CI | Free-choice accuracy delta | 95% CI |",
            "|---|---:|---:|---:|---:|",
        ]
        for selector, row in summary["effects"].items():
            margin = row["margin"]
            accuracy = row["next_token_accuracy"]
            lines.append(
                f"| {selector} | {margin['mean']:+.3f} | "
                f"[{margin['ci95'][0]:+.3f}, {margin['ci95'][1]:+.3f}] | "
                f"{accuracy['mean']:+.3f} | "
                f"[{accuracy['ci95'][0]:+.3f}, {accuracy['ci95'][1]:+.3f}] |"
            )
    if summary["free_generation"]:
        accuracy = summary["free_generation"]["first_token_accuracy"]
        repetition = summary["free_generation"]["repetition_fraction"]
        lines += [
            "",
            "| Greedy-generation contrast | Mean | 95% CI |",
            "|---|---:|---:|",
            f"| First-token accuracy | {accuracy['mean']:+.3f} | "
            f"[{accuracy['ci95'][0]:+.3f}, {accuracy['ci95'][1]:+.3f}] |",
            f"| Repetition fraction | {repetition['mean']:+.3f} | "
            f"[{repetition['ci95'][0]:+.3f}, {repetition['ci95'][1]:+.3f}] |",
        ]
    lines += [
        "",
        "The answer decision is the model's unconstrained top-1 next token; no gold answer token is fed to the model.",
        "A separate greedy-decoding audit keeps the intervention active across multiple generated tokens and reports repetition collapse.",
        "Hierarchical intervals resample competent seeds and paired evaluation examples.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputs", nargs="*",
        default=[
            "results/lengthgen/pretrained_natural_mcqa_qwen_s*/"
            "pretrained_natural_mcqa_results.json"
        ],
    )
    parser.add_argument(
        "--json-output", default="results/lengthgen/pretrained_natural_mcqa_summary.json"
    )
    parser.add_argument(
        "--md-output", default="results/lengthgen/pretrained_natural_mcqa_summary.md"
    )
    args = parser.parse_args()
    paths = []
    for pattern in args.inputs:
        paths.extend(glob.glob(pattern) or [pattern])
    results = [json.loads(Path(path).read_text()) for path in sorted(set(paths))]
    summary = aggregate(results)
    Path(args.json_output).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.md_output).write_text(markdown(summary))
    print(f"wrote {args.json_output}")
    print(f"wrote {args.md_output}")


if __name__ == "__main__":
    main()
