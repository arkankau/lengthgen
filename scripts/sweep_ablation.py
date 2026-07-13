from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.attention import NullAttractorConfig
from thermosafety.prompts import load_prompt_dir
from thermosafety.runner import evaluate_case


GRID = {
    "eta_null": [1.0, 2.0, 4.0, 6.0],
    "kappa": [4.0, 10.0, 18.0, 30.0],
    "lambda_penalty": [0.0, 0.1, 0.2, 0.4],
    "beta_collapse": [1.0, 2.0, 3.0, 4.0],
}


def config_with(name: str, value: float) -> NullAttractorConfig:
    kwargs = {name: value}
    return NullAttractorConfig(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="One-factor ablations for toy null-attractor parameters.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--output", default="results/ablation_sweep.csv")
    args = parser.parse_args()

    cases = load_prompt_dir(args.prompts)
    rows = []
    for param, values in GRID.items():
        for value in values:
            cfg = config_with(param, value)
            for case in cases:
                row = evaluate_case(case, cfg)
                row["ablation_param"] = param
                row["ablation_value"] = value
                rows.append(row)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["ablation_param", "ablation_value"]
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
