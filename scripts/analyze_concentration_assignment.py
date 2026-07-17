"""Model-level analysis for the concentration-by-assignment factorial.

The unit of resampling is a trained model. Lengths are averaged within each model
for the headline estimates so examples and repeated lengths are not treated as
independent replications.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def bootstrap_summary(values, rng, draws):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return {"n": 0, "mean": float("nan"), "ci95": [float("nan"), float("nan")]}
    means = np.empty(draws, dtype=np.float64)
    chunk = 1000
    for start in range(0, draws, chunk):
        count = min(chunk, draws - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means[start:start + count] = values[indices].mean(axis=1)
    return {
        "n": int(len(values)),
        "mean": float(values.mean()),
        "ci95": [float(value) for value in np.quantile(means, [0.025, 0.975])],
    }


def average_by_model(rows, field, predicate=lambda row: True):
    grouped = defaultdict(list)
    for row in rows:
        if predicate(row):
            grouped[row["model"]].append(row[field])
    return [float(np.mean(values)) for values in grouped.values()]


def format_estimate(summary):
    low, high = summary["ci95"]
    return f"{summary['mean']:+.4f} [{low:+.4f}, {high:+.4f}]"


def extract_rows(records):
    rows = []
    invariant_sorted = []
    invariant_derived = []
    assignment_observable_error = []
    for record in records:
        cfg = record["cfg"]
        model = (cfg["task"], cfg["pe"], int(cfg["seed"]))
        for length_text, length_result in record["lengths"].items():
            baseline = length_result["baseline"]
            for beta_text, level in length_result["levels"].items():
                beta = float(beta_text)
                conditions = level["conditions"]
                correct = conditions["source_max"]
                wrong = conditions["source_min"]
                identity = conditions["identity"]
                control = conditions["distractor_control"]
                row = {
                    "model": model,
                    "task": cfg["task"],
                    "pe": cfg["pe"],
                    "seed": int(cfg["seed"]),
                    "length": int(length_text),
                    "beta": beta,
                    "capacity": float(correct["mean_head_max_weight"]),
                    "entropy": float(correct["mean_head_entropy"]),
                    "correct_wrong": correct["token_accuracy"] - wrong["token_accuracy"],
                    "correct_identity": correct["token_accuracy"] - identity["token_accuracy"],
                    "identity_baseline": identity["token_accuracy"] - baseline["token_accuracy"],
                    "correct_baseline": correct["token_accuracy"] - baseline["token_accuracy"],
                    "wrong_baseline": wrong["token_accuracy"] - baseline["token_accuracy"],
                    "correct_control": correct["token_accuracy"] - control["token_accuracy"],
                    "correct_source_mass": float(np.mean(correct["source_mass_by_selected_head"])),
                    "wrong_source_mass": float(np.mean(wrong["source_mass_by_selected_head"])),
                    "correct_output_var_ratio": (
                        correct["attention_output_var"] / baseline["attention_output_var"]
                    ),
                }
                rows.append(row)
                for condition in conditions.values():
                    diagnostics = condition["invariant_max_abs_error"]
                    invariant_sorted.append(float(diagnostics.get("sorted", 0.0)))
                    invariant_derived.extend(
                        float(value) for key, value in diagnostics.items() if key != "sorted"
                    )
                assignment_observable_error.extend(
                    [
                        abs(correct["mean_head_entropy"] - wrong["mean_head_entropy"]),
                        abs(correct["mean_head_max_weight"] - wrong["mean_head_max_weight"]),
                    ]
                )
    return rows, {
        "max_sorted_spectrum_error": max(invariant_sorted, default=0.0),
        "max_derived_invariant_error": max(invariant_derived, default=0.0),
        "max_correct_wrong_observable_error": max(assignment_observable_error, default=0.0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="results/lengthgen/factorial_grid/concentration_assignment_results.json",
    )
    parser.add_argument("--bootstrap-draws", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    records = json.loads(Path(args.path).read_text())
    keys = {(r["cfg"]["task"], r["cfg"]["pe"], int(r["cfg"]["seed"])) for r in records}
    if len(keys) != len(records):
        raise SystemExit("duplicate task/PE/seed record")
    if args.require_complete and len(records) != 16:
        raise SystemExit(f"incomplete factorial grid: {len(records)}/16")

    rows, invariant_checks = extract_rows(records)
    rng = np.random.default_rng(args.seed)
    betas = sorted({row["beta"] for row in rows})
    train_min = min(r["train_length"]["token_accuracy"] for r in records)
    summary = {
        "completed_models": len(records),
        "expected_models": 16,
        "train_accuracy_min": float(train_min),
        "invariants": invariant_checks,
        "beta_effects": {},
        "interaction": {},
        "groups": {},
    }

    for beta in betas:
        beta_summary = {}
        for field in (
            "correct_wrong",
            "correct_identity",
            "identity_baseline",
            "correct_baseline",
            "wrong_baseline",
            "correct_control",
        ):
            values = average_by_model(rows, field, lambda row, b=beta: row["beta"] == b)
            beta_summary[field] = bootstrap_summary(values, rng, args.bootstrap_draws)
        beta_rows = [row for row in rows if row["beta"] == beta]
        beta_summary["capacity_mean"] = float(np.mean([row["capacity"] for row in beta_rows]))
        beta_summary["entropy_mean"] = float(np.mean([row["entropy"] for row in beta_rows]))
        beta_summary["positive_correct_wrong_models"] = sum(
            value > 0 for value in average_by_model(rows, "correct_wrong", lambda row, b=beta: row["beta"] == b)
        )
        summary["beta_effects"][f"{beta:g}"] = beta_summary

    if len(betas) >= 2:
        low, high = betas[0], betas[-1]
        by_model_beta = defaultdict(lambda: defaultdict(list))
        for row in rows:
            by_model_beta[row["model"]][row["beta"]].append(row["correct_wrong"])
        interaction = [
            float(np.mean(values[high]) - np.mean(values[low]))
            for values in by_model_beta.values()
            if low in values and high in values
        ]
        summary["interaction"] = {
            "contrast": f"correct-wrong(beta={high:g}) - correct-wrong(beta={low:g})",
            "estimate": bootstrap_summary(interaction, rng, args.bootstrap_draws),
            "positive_models": sum(value > 0 for value in interaction),
        }

    for task in ("argmax", "flagret"):
        for pe in ("nope", "rope"):
            group_key = f"{task}/{pe}"
            group = {}
            for beta in betas:
                predicate = lambda row, t=task, p=pe, b=beta: (
                    row["task"] == t and row["pe"] == p and row["beta"] == b
                )
                group[f"beta{beta:g}_correct_wrong"] = bootstrap_summary(
                    average_by_model(rows, "correct_wrong", predicate), rng, args.bootstrap_draws
                )
                group[f"beta{beta:g}_correct_baseline"] = bootstrap_summary(
                    average_by_model(rows, "correct_baseline", predicate), rng, args.bootstrap_draws
                )
            summary["groups"][group_key] = group

    if rows:
        summary["relationships"] = {
            "corr_capacity_correct_wrong": float(
                np.corrcoef(
                    [row["capacity"] for row in rows],
                    [row["correct_wrong"] for row in rows],
                )[0, 1]
            ),
            "corr_source_mass_correct_baseline": float(
                np.corrcoef(
                    [row["correct_source_mass"] for row in rows],
                    [row["correct_baseline"] for row in rows],
                )[0, 1]
            ),
            "corr_output_var_ratio_correct_baseline": float(
                np.corrcoef(
                    [row["correct_output_var_ratio"] for row in rows],
                    [row["correct_baseline"] for row in rows],
                )[0, 1]
            ),
        }

    print(f"Factorial status: {len(records)}/16 models; train accuracy min={train_min:.4f}")
    print(
        "Invariant checks: sorted={:.3g}, derived={:.3g}, correct/wrong observables={:.3g}".format(
            invariant_checks["max_sorted_spectrum_error"],
            invariant_checks["max_derived_invariant_error"],
            invariant_checks["max_correct_wrong_observable_error"],
        )
    )
    print("\nModel-level effects averaged over lengths")
    print("beta  max-weight  entropy  correct-wrong (95% CI)  correct-natural  sharpen-natural")
    for beta in betas:
        result = summary["beta_effects"][f"{beta:g}"]
        print(
            f"{beta:>4g}  {result['capacity_mean']:.4f}      {result['entropy_mean']:.4f}   "
            f"{format_estimate(result['correct_wrong'])}   "
            f"{format_estimate(result['correct_identity'])}   "
            f"{format_estimate(result['identity_baseline'])}"
        )
    if summary["interaction"]:
        interaction = summary["interaction"]
        print(
            "\nInteraction: {} = {}; positive models={}/{}".format(
                interaction["contrast"],
                format_estimate(interaction["estimate"]),
                interaction["positive_models"],
                interaction["estimate"]["n"],
            )
        )
    print("\nGroup correct-vs-wrong assignment effects")
    for group_key, group in summary["groups"].items():
        values = " | ".join(
            f"beta={beta:g}: {format_estimate(group[f'beta{beta:g}_correct_wrong'])}"
            for beta in betas
        )
        print(f"{group_key}: {values}")
    if "relationships" in summary:
        relationships = summary["relationships"]
        print("\nRelationships across model-length-beta cells")
        for key, value in relationships.items():
            print(f"{key}={value:.4f}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(summary, indent=2))
        print(f"\njson={args.json_out}")


if __name__ == "__main__":
    main()
