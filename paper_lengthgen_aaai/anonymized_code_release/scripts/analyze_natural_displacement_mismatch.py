"""Summarize row-level displacement mismatch from the frozen natural-QA audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out")
    args = parser.parse_args()
    path = Path(args.input)
    if path.is_dir():
        legacy_path = path.parent / "natural_displacement_mismatch_rows.json"
        records = (
            json.loads(legacy_path.read_text()).get("records", [])
            if legacy_path.exists() else []
        )
        existing_seeds = {int(row["seed"]) for row in records}
        for result_path in sorted(path.glob("s*/pretrained_natural_mcqa_results.json")):
            result = json.loads(result_path.read_text())
            if int(result["seed"]) in existing_seeds:
                continue
            for selector, cell in result["selectors"].items():
                conditions = cell["conditions"]
                source = conditions["source_max"]["invariant_max_abs_error"].get(
                    "mean_l1_displacement_by_example"
                )
                control = conditions["matched_distractor_control"][
                    "invariant_max_abs_error"
                ].get("mean_l1_displacement_by_example")
                if source is None or control is None:
                    continue
                records.extend({
                    "seed": int(result["seed"]),
                    "selector": selector,
                    "example_index": index,
                    "epsilon": float(source_value - control_value),
                } for index, (source_value, control_value) in enumerate(zip(source, control)))
        data = {
            "definition": (
                "epsilon_i = mean-head source-max L1 displacement minus mean-head "
                "matched-control L1 displacement"
            ),
            "records": records,
        }
    else:
        data = json.loads(path.read_text())
    absolute = np.abs(np.asarray([row["epsilon"] for row in data["records"]], dtype=np.float64))
    summary = {
        "definition": data["definition"],
        "n_rows": int(len(absolute)),
        "median_absolute_epsilon": float(np.median(absolute)),
        "p95_absolute_epsilon": float(np.quantile(absolute, 0.95)),
        "max_absolute_epsilon": float(absolute.max()),
    }
    output = Path(args.out) if args.out else path.with_name(path.stem + "_summary.json")
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
