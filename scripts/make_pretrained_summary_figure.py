"""Generate the main-paper summary of pretrained routing experiments."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


RESULTS = Path("results/lengthgen")
PAPER = Path("paper_lengthgen_aaai/figures")
PAPER.mkdir(parents=True, exist_ok=True)

ROUTE_BLUE = "#011F5B"
UTILITY_TEAL = "#011F5B"
HARM_ORANGE = "#990000"
BOUNDARY_PURPLE = "#7F7F7F"
CONTROL_GRAY = "#7F7F7F"
CHARCOAL = "#333333"
MIDGRAY = "#7A8388"
LIGHTGRAY = "#D8DDDF"
MATCHED_LENGTHS = (5, 20, 80)
PAIRED_EXAMPLES_PER_CELL = 128

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 10.8,
        "axes.titlesize": 11.0,
        "axes.labelsize": 10.6,
        "xtick.labelsize": 10.6,
        "ytick.labelsize": 10.6,
        "figure.dpi": 180,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def paired_interval(values: np.ndarray, seed: int, draws: int = 5000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(draws, len(values)))
    means = values[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def model_trajectory(path: Path, seed: int) -> list[dict]:
    data = load(path)
    if data.get("seed") != 0:
        raise ValueError(f"expected experiment seed 0 in {path}, found {data.get('seed')}")
    rows = []
    for length_text, sweep in sorted(data["lengths"].items(), key=lambda item: int(item[0])):
        baseline = sweep["conditions"]["baseline"]["records"]
        source_max = sweep["conditions"]["source_max"]["records"]
        source_min = sweep["conditions"]["source_min"]["records"]
        control = sweep["conditions"]["distractor_control"]["records"]
        counts = {len(baseline), len(source_max), len(source_min), len(control)}
        if len(counts) != 1:
            raise ValueError(f"paired sample-count mismatch at length {length_text}")
        contrasts = {}
        for offset, (name, records) in enumerate(
            [
                ("source_max", source_max),
                ("source_min", source_min),
                ("untouched", baseline),
            ]
        ):
            effects = np.asarray(
                [left["margin"] - right["margin"] for left, right in zip(records, control)],
                dtype=np.float64,
            )
            contrasts[name] = {
                "mean": float(effects.mean()),
                "ci95": paired_interval(effects, seed + offset),
            }
        rows.append(
            {
                "length": int(length_text),
                "n": counts.pop(),
                "contrasts": contrasts,
            }
        )
    return rows


def main() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.05, 4.75), sharex=True, sharey=True)
    fig.subplots_adjust(
        left=0.105, right=0.985, bottom=0.115, top=0.87, wspace=0.16, hspace=0.30
    )

    models = [
        ("Qwen2.5-1.5B", "pretrained_causal_qwen1p5b"),
        ("Pythia-1.4B", "pretrained_causal_pythia1p4b"),
        ("Gemma-2-2B", "pretrained_causal_gemma2b"),
        ("SmolLM2-1.7B", "pretrained_causal_smollm2_1p7b"),
    ]
    trajectories = [
        (
            label,
            model_trajectory(
                RESULTS / directory / "pretrained_causal_routing_results.json",
                3100 + index,
            ),
        )
        for index, (label, directory) in enumerate(models)
    ]
    for model_label, trajectory in trajectories:
        rows_by_length = {row["length"]: row for row in trajectory}
        missing = set(MATCHED_LENGTHS) - set(rows_by_length)
        if missing:
            raise ValueError(
                f"{model_label} is missing matched lengths {sorted(missing)}"
            )
        counts = {rows_by_length[length]["n"] for length in MATCHED_LENGTHS}
        if counts != {PAIRED_EXAMPLES_PER_CELL}:
            raise ValueError(
                f"{model_label} expected {PAIRED_EXAMPLES_PER_CELL} paired examples "
                f"at each matched length, found {sorted(counts)}"
            )

    shared_ticks = list(MATCHED_LENGTHS)
    series = [
        ("source-max", "source_max", ROUTE_BLUE, "s", "-"),
        ("source-min", "source_min", HARM_ORANGE, "v", "--"),
        ("untouched", "untouched", CONTROL_GRAY, "o", ":"),
    ]
    panel_letters = ["a", "b", "c", "d"]
    for ax, letter, (model_label, trajectory) in zip(
        axes.flat, panel_letters, trajectories
    ):
        rows_by_length = {row["length"]: row for row in trajectory}
        rows = [rows_by_length[length] for length in MATCHED_LENGTHS]
        x = np.asarray([row["length"] for row in rows])
        for display, key, color, marker, linestyle in series:
            means = np.asarray([row["contrasts"][key]["mean"] for row in rows])
            cis = np.asarray([row["contrasts"][key]["ci95"] for row in rows])
            ax.errorbar(
                x,
                means,
                yerr=np.vstack([means - cis[:, 0], cis[:, 1] - means]),
                color=color,
                marker=marker,
                markersize=3.5,
                linewidth=1.2,
                linestyle=linestyle,
                capsize=2,
                label=display,
            )
        ax.axhline(0, color=MIDGRAY, linewidth=0.8, linestyle=":")
        ax.set_xscale("log", base=2)
        ax.set_xticks(shared_ticks)
        ax.set_xticklabels(shared_ticks)
        ax.set_xlim(4, 105)
        ax.set_title(f"({letter}) {model_label}", pad=5)
        ax.grid(alpha=0.18)

    axes[0, 0].set_ylabel("margin effect vs. control")
    axes[1, 0].set_ylabel("margin effect vs. control")
    axes[1, 0].set_xlabel("key-value pairs")
    axes[1, 1].set_xlabel("key-value pairs")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.55, 0.985),
        frameon=False,
        fontsize=8.5,
        ncol=3,
        handlelength=1.8,
        columnspacing=1.2,
    )

    output_pdf = RESULTS / "fig_pretrained_summary.pdf"
    output_png = RESULTS / "fig_pretrained_summary.png"
    fig.savefig(output_pdf, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(output_png, dpi=600, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    shutil.copy2(output_pdf, PAPER / output_pdf.name)
    shutil.copy2(output_png, PAPER / output_png.name)
    print("wrote", output_pdf, output_png, "and paper copies")


if __name__ == "__main__":
    main()
