"""Summarize the two-evidence fixed-spectrum routing experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


MODES = ("baseline", "source_max", "source_min", "distractor_control")


def bootstrap(values, seed=2027, draws=20000):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(draws, len(values)))
    means = values[indices].mean(axis=1)
    return [float(value) for value in np.quantile(means, [0.025, 0.975])]


def summarize(results, competence=0.8):
    if not results:
        raise ValueError("no multi-evidence results")
    train_exact = [float(row["train_length"]["exact_match"]) for row in results]
    lengths = sorted({int(length) for row in results for length in row["lengths"]})
    rows = []
    for result in results:
        cfg = result["cfg"]
        for length_text, payload in result["lengths"].items():
            conditions = payload["conditions"]
            base = conditions["baseline"]
            row = {
                "task": cfg["task"],
                "pe": cfg["pe"],
                "seed": int(cfg["seed"]),
                "length": int(length_text),
                "train_exact": float(result["train_length"]["exact_match"]),
            }
            for mode in MODES:
                condition = conditions[mode]
                row[f"{mode}_exact"] = float(condition["exact_match"])
                row[f"{mode}_token"] = float(condition["token_accuracy"])
                row[f"{mode}_mass"] = float(condition["selected_head_source_mass"])
            for mode in MODES[1:]:
                row[f"{mode}_exact_delta"] = row[f"{mode}_exact"] - row["baseline_exact"]
                row[f"{mode}_token_delta"] = row[f"{mode}_token"] - row["baseline_token"]
            row["max_minus_min_exact"] = row["source_max_exact"] - row["source_min_exact"]
            row["max_minus_control_exact"] = (
                row["source_max_exact"] - row["distractor_control_exact"]
            )
            rows.append(row)

    by_length = {}
    for length in lengths:
        group = [row for row in rows if row["length"] == length]
        summary = {"models": len(group)}
        for mode in MODES:
            summary[f"mean_{mode}_exact"] = float(np.mean([row[f"{mode}_exact"] for row in group]))
            summary[f"mean_{mode}_token"] = float(np.mean([row[f"{mode}_token"] for row in group]))
            summary[f"mean_{mode}_mass"] = float(np.mean([row[f"{mode}_mass"] for row in group]))
        for key in ("source_max_exact_delta", "source_min_exact_delta", "distractor_control_exact_delta",
                    "max_minus_min_exact", "max_minus_control_exact"):
            values = [row[key] for row in group]
            summary[f"mean_{key}"] = float(np.mean(values))
            summary[f"{key}_ci95"] = bootstrap(values, seed=2027 + length)
            summary[f"{key}_positive_models"] = int(np.sum(np.asarray(values) > 0))
        by_length[str(length)] = summary

    invariant_errors = []
    for result in results:
        for payload in result["lengths"].values():
            for mode in MODES[1:]:
                invariant_errors.extend(payload["conditions"][mode]["invariant_max_abs_error"].values())
    return {
        "models": len(results),
        "competence_threshold": competence,
        "min_train_exact": min(train_exact),
        "all_models_competent": min(train_exact) >= competence,
        "max_invariant_error": max(invariant_errors, default=0.0),
        "by_length": by_length,
        "rows": rows,
    }


def report(summary):
    lines = [
        "# Multi-Evidence Routing Summary",
        "",
        f"- Models: {summary['models']}",
        f"- Minimum train-length exact match: {summary['min_train_exact']:.3f}",
        f"- Competence gate passed: {summary['all_models_competent']}",
        f"- Maximum spectrum-invariant error: {summary['max_invariant_error']:.3g}",
        "",
        "| length | baseline exact | source-max | source-min | control | max delta | min delta | control delta | max-minus-min | max-minus-control |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for length, row in summary["by_length"].items():
        lines.append(
            f"| {length} | {row['mean_baseline_exact']:.3f} | {row['mean_source_max_exact']:.3f} | "
            f"{row['mean_source_min_exact']:.3f} | {row['mean_distractor_control_exact']:.3f} | "
            f"{row['mean_source_max_exact_delta']:+.3f} | {row['mean_source_min_exact_delta']:+.3f} | "
            f"{row['mean_distractor_control_exact_delta']:+.3f} | {row['mean_max_minus_min_exact']:+.3f} | "
            f"{row['mean_max_minus_control_exact']:+.3f} |"
        )
    lines += [
        "",
        "Interpretation is conditional on the competence gate. Source-max and source-min assign the same",
        "complete attention spectrum to opposite ends of the two-token evidence-mass range. The distractor",
        "control preserves both the spectrum and evidence mass.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--json-out", default="results/lengthgen/multievidence_summary.json")
    parser.add_argument("--report-out", default="results/lengthgen/multievidence_summary.md")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    results = json.loads(Path(args.input).read_text())
    summary = summarize(results)
    if args.require_complete and (summary["models"] != 8 or not summary["all_models_competent"]):
        raise SystemExit(
            f"incomplete/undertrained grid: models={summary['models']} "
            f"competent={summary['all_models_competent']}"
        )
    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.report_out).write_text(report(summary))
    print(Path(args.report_out).as_posix())


if __name__ == "__main__":
    main()
