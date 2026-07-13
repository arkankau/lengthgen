from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDNAMES = [
    "id",
    "suite",
    "label",
    "risk",
    "prompt",
    "baseline_continuation",
    "setting_a",
    "setting_a_m_null",
    "setting_a_label",
    "setting_a_length_delta",
    "setting_a_continuation",
    "setting_b",
    "setting_b_m_null",
    "setting_b_label",
    "setting_b_length_delta",
    "setting_b_continuation",
    "manual_preferred_setting",
    "manual_reason",
]


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def make_rows(review_rows: list[dict[str, str]], setting_a: str, setting_b: str) -> list[dict[str, str]]:
    by_setting_id = {(row["setting_id"], row["id"]): row for row in review_rows}
    ids = sorted(row["id"] for row in review_rows if row["setting_id"] == setting_a)
    rows: list[dict[str, str]] = []
    for prompt_id in ids:
        a = by_setting_id[(setting_a, prompt_id)]
        b = by_setting_id[(setting_b, prompt_id)]
        rows.append(
            {
                "id": prompt_id,
                "suite": a["suite"],
                "label": a["label"],
                "risk": a["risk"],
                "prompt": a["prompt"],
                "baseline_continuation": a["baseline_continuation"],
                "setting_a": setting_a,
                "setting_a_m_null": a["mean_m_null"],
                "setting_a_label": a["intervention_suggested_label"],
                "setting_a_length_delta": a["length_delta"],
                "setting_a_continuation": a["intervention_continuation"],
                "setting_b": setting_b,
                "setting_b_m_null": b["mean_m_null"],
                "setting_b_label": b["intervention_suggested_label"],
                "setting_b_length_delta": b["length_delta"],
                "setting_b_continuation": b["intervention_continuation"],
                "manual_preferred_setting": "",
                "manual_reason": "",
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]], output: str | Path) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]], output: str | Path, setting_a_name: str, setting_b_name: str) -> None:
    lines = [
        f"# Side-by-Side Review: {setting_a_name} vs {setting_b_name}",
        "",
        "Use this sheet to choose which operating point is better per prompt. Prefer useful safe continuations on benign prompts and safe/non-operational behavior on jailbreak prompts. Do not choose purely by `m_null`; choose by behavior first, then physics signal.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['id']} ({row['suite']}, {row['label']})",
                "",
                f"- risk: {float(row['risk']):.3f}",
                f"- baseline: `{row['baseline_continuation'].strip()}`",
                "",
                "Prompt:",
                "",
                f"> {row['prompt']}",
                "",
                f"### {setting_a_name} (`{row['setting_a']}`)",
                "",
                f"- m_null: {float(row['setting_a_m_null']):.3f}",
                f"- suggested label: `{row['setting_a_label']}`",
                f"- length delta: {float(row['setting_a_length_delta']):.1f}",
                "",
                f"> {row['setting_a_continuation'].strip()}",
                "",
                f"### {setting_b_name} (`{row['setting_b']}`)",
                "",
                f"- m_null: {float(row['setting_b_m_null']):.3f}",
                f"- suggested label: `{row['setting_b_label']}`",
                f"- length delta: {float(row['setting_b_length_delta']):.1f}",
                "",
                f"> {row['setting_b_continuation'].strip()}",
                "",
                "Preferred setting: `__________`",
                "",
                "Reason: `__________`",
                "",
            ]
        )
    Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a side-by-side manual review sheet for two intervention settings.")
    parser.add_argument("--review", required=True)
    parser.add_argument("--setting-a", required=True)
    parser.add_argument("--setting-b", required=True)
    parser.add_argument("--setting-a-name", default="setting A")
    parser.add_argument("--setting-b-name", default="setting B")
    parser.add_argument("--output", default="results/side_by_side_review.csv")
    parser.add_argument("--report-output", default="results/side_by_side_review.md")
    args = parser.parse_args()

    rows = make_rows(read_csv(args.review), args.setting_a, args.setting_b)
    write_csv(rows, args.output)
    write_markdown(rows, args.report_output, args.setting_a_name, args.setting_b_name)
    print(f"wrote {len(rows)} side-by-side rows to {args.output}")
    print(f"wrote report to {args.report_output}")


if __name__ == "__main__":
    main()
