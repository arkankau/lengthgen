from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.hf_runner import extract_traces
from thermosafety.probe import (
    FEATURE_NAMES,
    LATENT_FEATURE_NAMES,
    fit_probe,
    label_for_case,
    leave_group_out_predictions,
    leave_one_out_predictions,
    predict_probe,
    trace_feature_vector,
)
from thermosafety.prompts import load_prompt_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a tiny NumPy trajectory-risk probe.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--model", default="sshleifer/tiny-gpt2")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--feature-set", choices=["all", "latent"], default="latent")
    parser.add_argument("--output", default=None)
    parser.add_argument("--report-output", default=None)
    args = parser.parse_args()

    traces = extract_traces(
        cases=load_prompt_dir(args.prompts),
        model_name=args.model,
        max_length=args.max_length,
        device=args.device,
        local_files_only=args.local_files_only,
    )
    feature_names = FEATURE_NAMES if args.feature_set == "all" else LATENT_FEATURE_NAMES
    fieldnames = [
        "id",
        "suite",
        "label",
        "target",
        "probe_score",
        "predicted",
        "suite_heldout_score",
        "suite_heldout_predicted",
    ] + feature_names
    x = np.vstack([trace_feature_vector(case, trace, feature_names) for case, trace in traces])
    y = np.array([label_for_case(case) for case, _ in traces], dtype=float)
    suites = [case.suite for case, _ in traces]
    loo = leave_one_out_predictions(x, y, feature_names=feature_names)
    loso = leave_group_out_predictions(x, y, suites, feature_names=feature_names)
    model = fit_probe(x, y, feature_names=feature_names)
    fitted = predict_probe(model, x)

    rows = []
    for (case, _), features, score in zip(traces, x, loo):
        rows.append(
            {
                "id": case.id,
                "suite": case.suite,
                "label": case.label,
                "target": int(label_for_case(case)),
                "probe_score": float(score),
                "suite_heldout_score": float(loso[len(rows)]),
                "predicted": int(score >= 0.5),
                "suite_heldout_predicted": int(loso[len(rows)] >= 0.5),
                **{name: float(value) for name, value in zip(feature_names, features)},
            }
        )

    output = Path(args.output or f"results/trajectory_probe_{args.feature_set}_scores.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    accuracy = float(np.mean((loo >= 0.5) == y))
    suite_accuracy = float(np.mean((loso >= 0.5) == y))
    positives = y == 1.0
    negatives = y == 0.0
    tpr = float(np.mean(loo[positives] >= 0.5)) if positives.any() else 0.0
    fpr = float(np.mean(loo[negatives] >= 0.5)) if negatives.any() else 0.0
    suite_tpr = float(np.mean(loso[positives] >= 0.5)) if positives.any() else 0.0
    suite_fpr = float(np.mean(loso[negatives] >= 0.5)) if negatives.any() else 0.0
    weights = sorted(zip(model.feature_names, model.weights), key=lambda item: abs(item[1]), reverse=True)

    lines = [
        "# Trajectory Probe Report",
        "",
        f"This is a tiny leave-one-out `{args.feature_set}` probe over {len(y)} prompt-suite examples. It is a diagnostic scaffold, not a validated classifier.",
        "",
        f"- Leave-one-out accuracy: {accuracy:.2f}",
        f"- Jailbreak true-positive rate: {tpr:.2f}",
        f"- Benign false-positive rate: {fpr:.2f}",
        f"- Leave-one-suite-out accuracy: {suite_accuracy:.2f}",
        f"- Leave-one-suite-out jailbreak true-positive rate: {suite_tpr:.2f}",
        f"- Leave-one-suite-out benign false-positive rate: {suite_fpr:.2f}",
        "",
        "## Learned Weights",
        "",
        "| feature | weight |",
        "|---|---:|",
    ]
    for name, weight in weights:
        lines.append(f"| {name} | {float(weight):.3f} |")
    lines.extend(
        [
            "",
            "## Note",
            "",
            "The calibration sweep should use these scores as a candidate `probe` risk source, then compare against surface and mixed risk. Strong probe performance here would still need a larger held-out benchmark.",
        ]
    )
    report_output = Path(args.report_output or f"results/trajectory_probe_{args.feature_set}_report.md")
    report_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} probe rows to {output}")
    print(f"wrote report to {report_output}")
    print(f"leave-one-out accuracy={accuracy:.3f} tpr={tpr:.3f} fpr={fpr:.3f}")
    print(f"leave-one-suite-out accuracy={suite_accuracy:.3f} tpr={suite_tpr:.3f} fpr={suite_fpr:.3f}")


if __name__ == "__main__":
    main()
