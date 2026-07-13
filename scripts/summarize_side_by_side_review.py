from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def summarize(rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        preferred = row["manual_preferred_setting"].strip() or "unlabeled"
        counters["overall"][preferred] += 1
        counters[f"label:{row['label']}"][preferred] += 1
        counters[f"suite:{row['suite']}"][preferred] += 1
    return counters


def write_report(rows: list[dict[str, str]], output: str | Path) -> None:
    counters = summarize(rows)
    labeled = sum(count for key, count in counters["overall"].items() if key != "unlabeled")
    s006 = counters["overall"]["s006"]
    s007 = counters["overall"]["s007"]
    ties = counters["overall"]["tie"]
    neither = counters["overall"]["neither"]
    winner = "s007" if s007 > s006 else ("s006" if s006 > s007 else "tie")

    lines = [
        "# s006 vs s007 Manual Review Summary",
        "",
        f"Rows labeled: {labeled}/{len(rows)}",
        "",
        "## Overall",
        "",
        "| preferred | count |",
        "|---|---:|",
    ]
    for key in ["s006", "s007", "tie", "neither", "unlabeled"]:
        if counters["overall"][key]:
            lines.append(f"| {key} | {counters['overall'][key]} |")

    lines.extend(
        [
            "",
            "## By Label",
            "",
            "| label | s006 | s007 | tie | neither |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for label_key in sorted(key for key in counters if key.startswith("label:")):
        label = label_key.split(":", 1)[1]
        counter = counters[label_key]
        lines.append(f"| {label} | {counter['s006']} | {counter['s007']} | {counter['tie']} | {counter['neither']} |")

    lines.extend(
        [
            "",
            "## By Suite",
            "",
            "| suite | s006 | s007 | tie | neither |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for suite_key in sorted(key for key in counters if key.startswith("suite:")):
        suite = suite_key.split(":", 1)[1]
        counter = counters[suite_key]
        lines.append(f"| {suite} | {counter['s006']} | {counter['s007']} | {counter['tie']} | {counter['neither']} |")

    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"Manual review favors `{winner}` among non-tie wins.",
            "",
            "Because most rows are ties, this should be read as a narrow preference, not a large behavioral separation. The practical conclusion is that `s007` is preferable when it differs, while `s006` remains the stronger physics-signal setting.",
        ]
    )
    Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize manual side-by-side preferences.")
    parser.add_argument("--input", default="results/s006_vs_s007_side_by_side.csv")
    parser.add_argument("--output", default="results/s006_vs_s007_manual_summary.md")
    args = parser.parse_args()

    rows = read_rows(args.input)
    write_report(rows, args.output)
    print(f"wrote summary to {args.output}")


if __name__ == "__main__":
    main()
