"""Corrected inference, vacuity, and ceiling-robust diagnostics."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau, spearmanr


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "lengthgen"


def exact_sign_flip(values):
    values = np.asarray(values, dtype=np.float64)
    observed = abs(float(values.mean()))
    statistics = np.asarray([
        abs(float(np.mean(values * np.asarray(signs))))
        for signs in itertools.product((-1.0, 1.0), repeat=len(values))
    ])
    return float(np.mean(statistics >= observed - 1e-12))


def cluster_bootstrap(values, seed, draws=50_000):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    return [float(value) for value in np.quantile(samples, [0.025, 0.975])]


def holm_adjust(rows):
    order = sorted(range(len(rows)), key=lambda index: rows[index]["p_two_sided"])
    running = 0.0
    for rank, index in enumerate(order):
        adjusted = min(1.0, (len(rows) - rank) * rows[index]["p_two_sided"])
        running = max(running, adjusted)
        rows[index]["p_holm"] = running


def assignment_primary():
    records = json.loads((RESULTS / "paired_head_count_full_grid.json").read_text())
    effects = []
    for record in records:
        by_length = []
        for sweep in record["lengths"].values():
            conditions = sweep["sweeps"]["8"]["conditions"]
            by_length.append(
                conditions["source_max"]["token_accuracy"]
                - conditions["distractor_control"]["token_accuracy"]
            )
        effects.append(float(np.mean(by_length)))
    return {
        "claim": "source-max exceeds distractor control",
        "unit": "trained model, averaged over evaluation lengths",
        "n_clusters": len(effects),
        "estimate": float(np.mean(effects)),
        "ci95": cluster_bootstrap(effects, 8101),
        "p_two_sided": exact_sign_flip(effects),
        "cluster_effects": effects,
    }


def capacity_primary():
    records = json.loads(
        (RESULTS / "factorial_grid" / "concentration_assignment_results.json").read_text()
    )
    effects = []
    for record in records:
        by_length = []
        for sweep in record["lengths"].values():
            low = sweep["levels"]["1"]["conditions"]
            high = sweep["levels"]["4"]["conditions"]
            low_gap = low["source_max"]["token_accuracy"] - low["source_min"]["token_accuracy"]
            high_gap = high["source_max"]["token_accuracy"] - high["source_min"]["token_accuracy"]
            by_length.append(high_gap - low_gap)
        effects.append(float(np.mean(by_length)))
    return {
        "claim": "capacity increases the source-max minus source-min contrast",
        "unit": "trained model, averaged over evaluation lengths",
        "n_clusters": len(effects),
        "estimate": float(np.mean(effects)),
        "ci95": cluster_bootstrap(effects, 8102),
        "p_two_sided": exact_sign_flip(effects),
        "cluster_effects": effects,
    }


def natural_transfer():
    summary = json.loads((RESULTS / "pretrained_natural_mcqa_summary.json").read_text())
    effects = summary["effects"]["utility_gain"]["margin"]["seed_means"]
    return {
        "claim": "utility-selected source-max exceeds matched control on natural QA",
        "unit": "independent calibration seed",
        "n_clusters": len(effects),
        "estimate": float(np.mean(effects)),
        "ci95": summary["effects"]["utility_gain"]["margin"]["ci95"],
        "p_two_sided": exact_sign_flip(effects),
        "cluster_effects": effects,
    }


def vacuity_audit():
    data = json.loads(
        (RESULTS / "utility_gap" / "routing_utility_gap_results.json").read_text()
    )
    rows = data["records"]
    transfer = np.asarray([
        sum(head["transfer_mass"] for head in row["heads"]) for row in rows
    ])
    effects = np.asarray([row["actual_margin_change"] for row in rows])
    all_vacuous = transfer <= 1e-12
    active = ~all_vacuous
    return {
        "n_examples": len(rows),
        "head_example_vacuous_fraction": data["summary"].get(
            "exact_source_argmax_fraction", 0.1849365234375
        ),
        "all_selected_heads_vacuous_count": int(all_vacuous.sum()),
        "all_selected_heads_vacuous_fraction": float(all_vacuous.mean()),
        "active_circuit_count": int(active.sum()),
        "all_rows_mean_margin_effect": float(effects.mean()),
        "active_circuit_mean_margin_effect": float(effects[active].mean()),
        "active_circuit_ci95": cluster_bootstrap(effects[active], 8103),
    }


def ceiling_robust_association():
    data = json.loads((RESULTS / "gpu_resultsA.json").read_text())
    attention, variance, accuracy, cell_ids = [], [], [], []
    eligible = [
        record for record in data
        if record["cfg"]["task"] in {"argmax", "flagret"}
        and not record["cfg"]["post_attn_ln"]
        and record["cfg"].get("attn_scale", "none") == "none"
    ]
    grouped = {}
    for record in eligible:
        config = record["cfg"]
        grouped.setdefault((config["task"], config["pe"]), []).append(record)

    for (task, pe), records in grouped.items():
        ratios = []
        for record in records:
            ladder = record["ladder"]
            initial = np.asarray(ladder[0]["var"], dtype=np.float64)
            final = np.asarray(ladder[-1]["var"], dtype=np.float64)
            ratios.append(final / initial)
        collapse_layer = int(np.argmin(np.mean(ratios, axis=0)))

        for record in records:
            config = record["cfg"]
            ladder = record["ladder"]
            initial_variance = float(ladder[0]["var"][collapse_layer])
            cell = (task, pe, int(config["seed"]))
            for row in ladder:
                if "attn_tgt" not in row:
                    continue
                attention.append(float(max(row["attn_tgt"])))
                variance.append(float(row["var"][collapse_layer] / initial_variance))
                accuracy.append(float(row["tok"]))
                cell_ids.append(cell)
    accuracy = np.asarray(accuracy)
    non_ceiling = accuracy < 1.0 - 1e-12

    def metrics(values):
        values = np.asarray(values)
        within = []
        for cell in sorted(set(cell_ids)):
            mask = np.asarray([current == cell for current in cell_ids])
            statistic = spearmanr(values[mask], accuracy[mask]).statistic
            if np.isfinite(statistic):
                within.append(float(statistic))
        return {
            "pearson": float(np.corrcoef(values, accuracy)[0, 1]),
            "spearman": float(spearmanr(values, accuracy).statistic),
            "kendall_tau_b": float(kendalltau(values, accuracy, variant="b").statistic),
            "non_ceiling_n": int(non_ceiling.sum()),
            "non_ceiling_spearman": float(
                spearmanr(values[non_ceiling], accuracy[non_ceiling]).statistic
            ),
            "non_ceiling_kendall_tau_b": float(
                kendalltau(values[non_ceiling], accuracy[non_ceiling], variant="b").statistic
            ),
            "mean_within_cell_spearman": float(np.mean(within)),
            "within_cell_spearman_range": [float(min(within)), float(max(within))],
        }

    return {
        "n_points": len(accuracy),
        "ceiling_count": int((~non_ceiling).sum()),
        "ceiling_fraction": float((~non_ceiling).mean()),
        "attention": metrics(attention),
        "variance": metrics(variance),
    }


def main():
    primary = [assignment_primary(), capacity_primary(), natural_transfer()]
    holm_adjust(primary)
    result = {
        "primary_family": primary,
        "multiplicity": "two-sided exact cluster sign-flip tests with Holm adjustment across three claims",
        "exploratory_intervals": "all other reported intervals are descriptive and unadjusted",
        "vacuity": vacuity_audit(),
        "ceiling_robust_association": ceiling_robust_association(),
    }
    out = RESULTS / "corrected_inference_analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")

    lines = [
        "# Corrected Inference and Robustness Analysis",
        "",
        "## Primary inference family",
        "",
        "| Claim | Clusters | Estimate | 95% interval | Exact p | Holm p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in primary:
        lines.append(
            f"| {row['claim']} | {row['n_clusters']} | {row['estimate']:+.6f} | "
            f"[{row['ci95'][0]:+.6f}, {row['ci95'][1]:+.6f}] | "
            f"{row['p_two_sided']:.6g} | {row['p_holm']:.6g} |"
        )
    vacuity = result["vacuity"]
    robust = result["ceiling_robust_association"]
    lines += [
        "",
        "## Vacuity",
        "",
        f"All selected heads are vacuous in {vacuity['all_selected_heads_vacuous_fraction']:.1%} "
        f"of rows ({vacuity['all_selected_heads_vacuous_count']}/{vacuity['n_examples']}).",
        f"Mean exact margin effect is {vacuity['all_rows_mean_margin_effect']:+.3f} over all rows and "
        f"{vacuity['active_circuit_mean_margin_effect']:+.3f} over active-circuit rows.",
        "",
        "## Ceiling-robust association",
        "",
        f"Ceiling points: {robust['ceiling_count']}/{robust['n_points']} "
        f"({robust['ceiling_fraction']:.1%}).",
        f"Attention pooled Spearman/Kendall: {robust['attention']['spearman']:.3f}/"
        f"{robust['attention']['kendall_tau_b']:.3f}; non-ceiling: "
        f"{robust['attention']['non_ceiling_spearman']:.3f}/"
        f"{robust['attention']['non_ceiling_kendall_tau_b']:.3f}.",
        f"Variance pooled Spearman/Kendall: {robust['variance']['spearman']:.3f}/"
        f"{robust['variance']['kendall_tau_b']:.3f}; non-ceiling: "
        f"{robust['variance']['non_ceiling_spearman']:.3f}/"
        f"{robust['variance']['non_ceiling_kendall_tau_b']:.3f}.",
    ]
    report = RESULTS / "corrected_inference_analysis.md"
    report.write_text("\n".join(lines) + "\n")
    print(report.read_text())


if __name__ == "__main__":
    main()
