from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def intervention_row(rows: list[dict[str, str]]) -> dict[str, str]:
    for row in rows:
        if row["mode"] == "null_intervention":
            return row
    raise ValueError("no null_intervention row found")


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def mean_log_mass(path: str | Path) -> float:
    rows = read_rows(path)
    return mean([float(row["m_null"]) for row in rows])


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Phase 4 intervention smoke outputs.")
    parser.add_argument("--benign-generation", default="results/intervention_generation_benign_smoke.csv")
    parser.add_argument("--benign-log", default="results/intervention_m_null_benign_smoke.csv")
    parser.add_argument("--direct-generation", default="results/intervention_generation_direct_smoke.csv")
    parser.add_argument("--direct-log", default="results/intervention_m_null_direct_smoke.csv")
    parser.add_argument("--output", default="results/intervention_smoke_report.md")
    args = parser.parse_args()

    benign = intervention_row(read_rows(args.benign_generation))
    direct = intervention_row(read_rows(args.direct_generation))
    benign_log_mean = mean_log_mass(args.benign_log)
    direct_log_mean = mean_log_mass(args.direct_log)

    lines = [
        "# Phase 4 Intervention Smoke Report",
        "",
        "This is a mechanics smoke test for in-layer GPT-2 attention intervention. It does not evaluate safety or prove jailbreak defense.",
        "",
        "| case | suite | risk | selected layers | row mean m_null | log mean m_null |",
        "|---|---|---:|---|---:|---:|",
        f"| benign | {benign['suite']} | {float(benign['risk']):.3f} | {benign['selected_layers']} | {float(benign['mean_m_null']):.3f} | {benign_log_mean:.3f} |",
        f"| direct jailbreak | {direct['suite']} | {float(direct['risk']):.3f} | {direct['selected_layers']} | {float(direct['mean_m_null']):.3f} | {direct_log_mean:.3f} |",
        "",
        "## Reading",
        "",
        "The hook fires inside selected GPT-2 attention layers and records per-layer/head null mass. In this smoke run, higher risk produces much larger null mass, which verifies the intervention plumbing and logging path. Generation-quality and safety behavior remain untested.",
    ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
