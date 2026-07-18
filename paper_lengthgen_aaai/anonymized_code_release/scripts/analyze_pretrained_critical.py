"""Combine the preregistered pretrained critical experiments without rerunning models."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def interval(values, seed=0, draws=10000):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(draws, len(values)))
    return [float(value) for value in np.quantile(values[indices].mean(axis=1), [0.025, 0.975])]


def contrast_records(left, right, field):
    return np.asarray([
        left["records"][index][field] - row[field]
        for index, row in enumerate(right["records"])
    ], dtype=np.float64)


def summarize_format(data):
    rows = []
    invariant_errors = []
    for length, cell in sorted(data["lengths"].items(), key=lambda item: int(item[0])):
        conditions = cell["conditions"]
        max_control_margin = contrast_records(
            conditions["source_max"], conditions["distractor_control"], "margin"
        )
        max_control_accuracy = contrast_records(
            conditions["source_max"], conditions["distractor_control"], "correct"
        )
        contrasts = {row["mode"]: row for row in cell["contrasts_vs_baseline"]}
        for condition in conditions.values():
            invariant_errors.extend(condition.get("invariant_max_abs_error", {}).values())
        rows.append({
            "length": int(length),
            "baseline_accuracy": conditions["baseline"]["accuracy"],
            "max_control_accuracy_delta": float(max_control_accuracy.mean()),
            "max_control_accuracy_delta_ci95": interval(max_control_accuracy, 100 + int(length)),
            "max_control_margin_delta": float(max_control_margin.mean()),
            "max_control_margin_delta_ci95": interval(max_control_margin, 200 + int(length)),
            "source_min_margin_delta": contrasts["source_min"]["margin_delta"],
            "source_min_margin_delta_ci95": contrasts["source_min"]["margin_delta_ci95"],
        })
    max_error = max(invariant_errors, default=0.0)
    gate = (
        any(row["baseline_accuracy"] >= 0.5 for row in rows)
        and sum(row["max_control_margin_delta"] > 0 for row in rows) >= 2
        and sum(row["source_min_margin_delta"] < 0 for row in rows) >= 2
        and max_error < 1e-6
    )
    return {
        "model": data["model"],
        "format": data.get("format", "colon_newline"),
        "rows": rows,
        "invariant_max_error": max_error,
        "gate_pass": gate,
    }


def summarize_utility(data):
    rows = []
    for length, modes in sorted(data["lengths"].items(), key=lambda item: int(item[0])):
        for mode, payload in modes.items():
            summary = payload["summary"]
            rows.append({"length": int(length), "mode": mode, **summary})
    competent = [row for row in rows if row["mode"] == "source_max"]
    associations = [
        row["spearman_first_order_exact"]
        for row in competent
        if math.isfinite(row["spearman_first_order_exact"])
    ]
    return {
        "model": data["model"],
        "seed": data.get("seed", 0),
        "format": data.get("format", "colon_newline"),
        "rows": rows,
        "mean_source_max_spearman": float(np.mean(associations)) if associations else None,
        "directional_gate_pass": bool(associations and np.mean(associations) > 0),
    }


def aggregate_utility(items, expected_seeds=(0, 1, 2)):
    grouped = {}
    for item in items:
        grouped.setdefault(item["model"], []).append(item)
    aggregates = []
    for model, model_items in sorted(grouped.items()):
        model_items = sorted(model_items, key=lambda item: item["seed"])
        observed_seeds = [item["seed"] for item in model_items]
        missing_seeds = sorted(set(expected_seeds) - set(observed_seeds))
        seed_spearman = []
        seed_sign = []
        seed_exact = []
        positive_cells = 0
        total_cells = 0
        for item in model_items:
            source_max = [row for row in item["rows"] if row["mode"] == "source_max"]
            correlations = [
                row["spearman_first_order_exact"] for row in source_max
                if math.isfinite(row["spearman_first_order_exact"])
            ]
            seed_spearman.append(float(np.mean(correlations)))
            seed_sign.append(float(np.mean([row["sign_agreement"] for row in source_max])))
            seed_exact.append(float(np.mean([row["mean_exact_margin_delta"] for row in source_max])))
            positive_cells += sum(row["spearman_first_order_exact"] > 0 for row in source_max)
            total_cells += len(source_max)
        aggregates.append({
            "model": model,
            "seeds": observed_seeds,
            "expected_seeds": list(expected_seeds),
            "missing_seeds": missing_seeds,
            "n_seeds": len(model_items),
            "positive_source_max_cells": positive_cells,
            "source_max_cells": total_cells,
            "mean_seed_spearman": float(np.mean(seed_spearman)),
            "mean_seed_spearman_ci95": interval(seed_spearman, seed=71),
            "mean_seed_sign_agreement": float(np.mean(seed_sign)),
            "mean_seed_sign_agreement_ci95": interval(seed_sign, seed=72),
            "mean_seed_exact_margin_delta": float(np.mean(seed_exact)),
            "mean_seed_exact_margin_delta_ci95": interval(seed_exact, seed=73),
            "gate_pass": bool(
                not missing_seeds
                and len(observed_seeds) == len(set(expected_seeds))
                and
                positive_cells == total_cells
                and all(value > 0 for value in seed_exact)
            ),
        })
    return aggregates


def summarize_priority2_format(pilot, data):
    result = summarize_format(data)
    selected = pilot.get("selected_format")
    rows_by_length = {row["length"]: row for row in result["rows"]}
    full_competence = (
        rows_by_length.get(5, {}).get("baseline_accuracy", 0.0) >= 0.40
        or rows_by_length.get(20, {}).get("baseline_accuracy", 0.0) >= 0.25
    )
    positive_max_control = sum(row["max_control_margin_delta"] > 0 for row in result["rows"])
    negative_source_min = sum(row["source_min_margin_delta"] < 0 for row in result["rows"])
    result.update({
        "pilot_seed": pilot.get("seed"),
        "pilot_selected_format": selected,
        "pilot_eligible_formats": pilot.get("eligible_formats", []),
        "pilot_pass": bool(selected and selected == data.get("format")),
        "full_competence_pass": full_competence,
        "positive_max_control_cells": positive_max_control,
        "negative_source_min_cells": negative_source_min,
    })
    result["gate_pass"] = bool(
        result["pilot_pass"]
        and full_competence
        and positive_max_control >= 2
        and negative_source_min >= 2
        and result["invariant_max_error"] < 1e-6
    )
    return result


def summarize_llama_replication(pilot, data):
    result = summarize_format(data)
    format_name = data.get("format", "colon_newline")
    pilot_cell = pilot.get("formats", {}).get(format_name, {}).get("5", {})
    pilot_competence = pilot_cell.get("accuracy", 0.0) >= 0.25
    competent_rows = [row for row in result["rows"] if row["baseline_accuracy"] >= 0.25]
    positive_max_control = sum(row["max_control_margin_delta"] > 0 for row in result["rows"])
    negative_source_min = sum(row["source_min_margin_delta"] < 0 for row in competent_rows)
    result.update({
        "pilot_accuracy_n5": pilot_cell.get("accuracy"),
        "pilot_competence_pass": pilot_competence,
        "positive_max_control_cells": positive_max_control,
        "competent_cells": len(competent_rows),
        "negative_source_min_competent_cells": negative_source_min,
    })
    result["gate_pass"] = bool(
        pilot_competence
        and positive_max_control >= 2
        and competent_rows
        and negative_source_min == len(competent_rows)
        and result["invariant_max_error"] < 1e-6
    )
    return result


def summarize_selection(data):
    rows = []
    for seed, payload in sorted(data["seeds"].items(), key=lambda item: int(item[0])):
        for cell in payload["cells"]:
            rows.append({
                "seed": int(seed),
                "name": cell["name"],
                "kind": cell["kind"],
                "layer": cell["layer"],
                "head_count": len(cell["heads"]),
                **cell["source_max_vs_control"],
            })
    selected = [row for row in rows if row["kind"] == "selected"]
    random_rows = [row for row in rows if row["name"] == "random_layer"]
    selected_mean = float(np.mean([row["margin_delta"] for row in selected]))
    random_mean = float(np.mean([row["margin_delta"] for row in random_rows])) if random_rows else None
    gate = (
        sum(row["margin_delta"] > 0 for row in selected) > len(selected) / 2
        and random_mean is not None
        and selected_mean > random_mean
    )
    return {
        "model": data["model"],
        "length": data["length"],
        "rows": rows,
        "selected_positive_cells": sum(row["margin_delta"] > 0 for row in selected),
        "selected_significant_cells": sum(
            row["margin_delta_ci95"][0] > 0 for row in selected
        ),
        "selected_cells": len(selected),
        "selected_mean_margin_delta": selected_mean,
        "random_mean_margin_delta": random_mean,
        "gate_pass": gate,
    }


def fmt(value):
    if value is None or not math.isfinite(float(value)):
        return "NA"
    return f"{float(value):+.3f}"


def write_report(path, result):
    lines = [
        "# Pretrained Critical Experiment Summary",
        "",
        "The gates below were fixed in `pretrained_critical_preregistration.json` before these GPU runs.",
        "",
    ]
    format_result = result.get("format_replication")
    if format_result:
        lines.extend([
            "## Format Replication",
            "",
            f"Gate: **{'pass' if format_result['gate_pass'] else 'fail'}**; model={format_result['model']}; format={format_result['format']}; invariant error={format_result['invariant_max_error']:.2e}.",
            "",
            "| N | baseline acc | max-control dacc | max-control dmargin | source-min dmargin |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ])
        for row in format_result["rows"]:
            lines.append(
                f"| {row['length']} | {row['baseline_accuracy']:.3f} | "
                f"{fmt(row['max_control_accuracy_delta'])} | {fmt(row['max_control_margin_delta'])} | "
                f"{fmt(row['source_min_margin_delta'])} |"
            )
        lines.append("")
    priority2 = result.get("priority2_format_replication")
    if priority2:
        lines.extend([
            "## Held-out Format Replication",
            "",
            f"Gate: **{'pass' if priority2['gate_pass'] else 'fail'}**; pilot selected="
            f"{priority2['pilot_selected_format']} from {priority2['pilot_eligible_formats']}; "
            f"full-run competence={'pass' if priority2['full_competence_pass'] else 'fail'}; "
            f"positive max-control cells={priority2['positive_max_control_cells']}/"
            f"{len(priority2['rows'])}; negative source-min cells="
            f"{priority2['negative_source_min_cells']}/{len(priority2['rows'])}.",
            "",
        ])
        for row in priority2["rows"]:
            lines.append(
                f"- N={row['length']}: baseline={row['baseline_accuracy']:.3f}, "
                f"max-control dmargin={fmt(row['max_control_margin_delta'])}, "
                f"source-min dmargin={fmt(row['source_min_margin_delta'])}."
            )
        lines.append("")
    llama = result.get("llama_family_replication")
    if llama:
        lines.extend([
            "## Llama-family Replication",
            "",
            f"Gate: **{'pass' if llama['gate_pass'] else 'fail'}**; model={llama['model']}; "
            f"N=5 pilot accuracy={llama['pilot_accuracy_n5']:.3f}; positive max-control cells="
            f"{llama['positive_max_control_cells']}/{len(llama['rows'])}; negative source-min "
            f"competent cells={llama['negative_source_min_competent_cells']}/"
            f"{llama['competent_cells']}.",
            "",
        ])
        for row in llama["rows"]:
            lines.append(
                f"- N={row['length']}: baseline={row['baseline_accuracy']:.3f}, "
                f"max-control dmargin={fmt(row['max_control_margin_delta'])}, "
                f"source-min dmargin={fmt(row['source_min_margin_delta'])}."
            )
        lines.append("")
    if result.get("utility_gap"):
        lines.extend(["## Pretrained Utility Gap", ""])
        for item in result["utility_gap"]:
            lines.append(
                f"- **{item['model']}**: mean source-max Spearman={fmt(item['mean_source_max_spearman'])}; "
                f"directional gate={'pass' if item['directional_gate_pass'] else 'fail'}."
            )
            for row in item["rows"]:
                lines.append(
                    f"  - N={row['length']} {row['mode']}: exact={fmt(row['mean_exact_margin_delta'])}, "
                    f"first-order={fmt(row['mean_first_order_margin_delta'])}, "
                    f"Spearman={fmt(row['spearman_first_order_exact'])}, sign={row['sign_agreement']:.3f}, "
                    f"MAE residual={row['mean_absolute_residual']:.3f}."
                )
        lines.append("")
    if result.get("utility_gap_aggregate"):
        lines.extend(["## Utility Seed Replication", ""])
        for item in result["utility_gap_aggregate"]:
            lines.append(
                f"- **{item['model']}**, seeds={item['seeds']}: "
                f"gate={'pass' if item['gate_pass'] else 'fail'}; positive source-max cells="
                f"{item['positive_source_max_cells']}/{item['source_max_cells']}; mean seed Spearman="
                f"{fmt(item['mean_seed_spearman'])} [{fmt(item['mean_seed_spearman_ci95'][0])},"
                f"{fmt(item['mean_seed_spearman_ci95'][1])}]; missing seeds={item['missing_seeds']}; sign agreement="
                f"{item['mean_seed_sign_agreement']:.3f}."
            )
        lines.append("")
    selection = result.get("selection_robustness")
    if selection:
        lines.extend([
            "## Selection Robustness",
            "",
            f"Gate: **{'pass' if selection['gate_pass'] else 'fail'}**; positive selected cells={selection['selected_positive_cells']}/{selection['selected_cells']}; paired intervals exclude zero in {selection['selected_significant_cells']}/{selection['selected_cells']}; selected/random mean dmargin={fmt(selection['selected_mean_margin_delta'])}/{fmt(selection['random_mean_margin_delta'])}.",
            "",
            "| seed | configuration | layer | K | max-control dmargin [95% CI] |",
            "| ---: | --- | ---: | ---: | ---: |",
        ])
        for row in selection["rows"]:
            lines.append(
                f"| {row['seed']} | {row['name']} | {row['layer']} | {row['head_count']} | "
                f"{fmt(row['margin_delta'])} [{fmt(row['margin_delta_ci95'][0])},{fmt(row['margin_delta_ci95'][1])}] |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format-run")
    parser.add_argument("--format-pilot")
    parser.add_argument("--priority2-format-run")
    parser.add_argument("--llama-pilot")
    parser.add_argument("--llama-run")
    parser.add_argument("--utility", nargs="*", default=[])
    parser.add_argument("--expected-utility-seeds", default="0,1,2")
    parser.add_argument("--selection")
    parser.add_argument("--outdir", default="results/lengthgen")
    args = parser.parse_args()
    result = {}
    if args.format_run:
        result["format_replication"] = summarize_format(load(args.format_run))
    if args.format_pilot and args.priority2_format_run:
        result["priority2_format_replication"] = summarize_priority2_format(
            load(args.format_pilot), load(args.priority2_format_run)
        )
    if args.llama_pilot and args.llama_run:
        result["llama_family_replication"] = summarize_llama_replication(
            load(args.llama_pilot), load(args.llama_run)
        )
    if args.utility:
        result["utility_gap"] = [summarize_utility(load(path)) for path in args.utility]
        expected_seeds = tuple(int(value) for value in args.expected_utility_seeds.split(",") if value)
        result["utility_gap_aggregate"] = aggregate_utility(
            result["utility_gap"], expected_seeds=expected_seeds
        )
    if args.selection:
        result["selection_robustness"] = summarize_selection(load(args.selection))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / "pretrained_critical_summary.json"
    report_path = outdir / "pretrained_critical_summary.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_report(report_path, result)
    print(report_path)


if __name__ == "__main__":
    main()
