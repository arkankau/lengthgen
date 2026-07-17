"""Aggregate fixed-spectrum routing effects over evidence-set arity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_pretrained_utility_selection import hierarchical_interval


ARITY = {"pairadd": 2, "tripleadd": 3, "quadadd": 4}


def _paired(sweep, field):
    source = sweep["conditions"]["source_max"][field]
    control = sweep["conditions"]["distractor_control"][field]
    return np.asarray(source, dtype=np.float64) - np.asarray(control, dtype=np.float64)


def summarize(results, head_count=8):
    grouped = {arity: [] for arity in ARITY.values()}
    competence = {arity: [] for arity in ARITY.values()}
    for result in results:
        task = result["cfg"]["task"]
        if task not in ARITY:
            continue
        arity = ARITY[task]
        competence[arity].append(result["train_length"]["exact_match"])
        longest = result["lengths"][max(result["lengths"], key=int)]
        sweep = longest["sweeps"][str(head_count)]
        grouped[arity].append(_paired(sweep, "per_example_exact"))
    rows = {}
    for arity, groups in grouped.items():
        if not groups:
            continue
        values = np.concatenate(groups)
        rows[str(arity)] = {
            "n_models": len(groups),
            "train_competence_min": float(min(competence[arity])),
            "source_max_minus_control_exact": float(values.mean()),
            "ci95": hierarchical_interval(groups, 800_000 + arity),
            "model_means": [float(group.mean()) for group in groups],
        }
    complete = all(str(arity) in rows for arity in (2, 3, 4))
    competent = complete and all(rows[str(arity)]["train_competence_min"] >= 0.8 for arity in (2, 3, 4))
    positive = competent and all(rows[str(arity)]["ci95"][0] > 0 for arity in (2, 3, 4))
    return {
        "head_count": head_count,
        "arity_results": rows,
        "complete": complete,
        "all_train_competent": competent,
        "set_routing_generalizes_through_arity_four": positive,
    }


def markdown(summary):
    lines = [
        "# Variable-Evidence Routing Summary",
        "",
        f"Generalizes through arity four: **{summary['set_routing_generalizes_through_arity_four']}**.",
        "",
        "| Evidence count | Models | Min train EM | Max-control exact | Hierarchical 95% CI |",
        "|---:|---:|---:|---:|---:|",
    ]
    for arity, row in sorted(summary["arity_results"].items(), key=lambda item: int(item[0])):
        lines.append(
            f"| {arity} | {row['n_models']} | {row['train_competence_min']:.3f} | "
            f"{row['source_max_minus_control_exact']:+.3f} | "
            f"[{row['ci95'][0]:+.3f}, {row['ci95'][1]:+.3f}] |"
        )
    lines += [
        "",
        "This tests the set-valued routing corollary for two, three, and four simultaneously required evidence tokens.",
        "It does not claim coverage of unrestricted reasoning or hidden intermediate computations.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--head-count", type=int, default=8)
    parser.add_argument(
        "--json-output", default="results/lengthgen/variable_evidence_summary.json"
    )
    parser.add_argument(
        "--md-output", default="results/lengthgen/variable_evidence_summary.md"
    )
    args = parser.parse_args()
    results = json.loads(Path(args.input).read_text())
    summary = summarize(results, args.head_count)
    Path(args.json_output).write_text(json.dumps(summary, indent=2) + "\n")
    Path(args.md_output).write_text(markdown(summary))
    print(f"wrote {args.json_output}")
    print(f"wrote {args.md_output}")


if __name__ == "__main__":
    main()
