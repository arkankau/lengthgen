from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.attention import NullAttractorConfig
from thermosafety.prompts import load_prompt_dir
from thermosafety.runner import evaluate_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep risk threshold R_c.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--output", default="results/threshold_sweep.csv")
    parser.add_argument("--start", type=float, default=0.20)
    parser.add_argument("--stop", type=float, default=0.80)
    parser.add_argument("--steps", type=int, default=25)
    args = parser.parse_args()

    cases = load_prompt_dir(args.prompts)
    thresholds = [
        args.start + i * (args.stop - args.start) / max(1, args.steps - 1)
        for i in range(args.steps)
    ]
    rows = []
    for threshold in thresholds:
        cfg = NullAttractorConfig(risk_threshold=threshold)
        for case in cases:
            rows.append(evaluate_case(case, cfg))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["risk_threshold"]
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
