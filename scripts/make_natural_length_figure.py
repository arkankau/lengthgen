"""Generate the main-paper natural-QA length-generalization figure."""
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
BOUNDARY_PURPLE = "#7F7F7F"
HARM_ORANGE = "#990000"
MIDGRAY = "#7A8388"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 9.6,
        "axes.titlesize": 9.8,
        "axes.labelsize": 9.6,
        "xtick.labelsize": 9.6,
        "ytick.labelsize": 9.6,
        "legend.fontsize": 9.4,
        "figure.dpi": 180,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def trajectory(summary: dict, field: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lengths = np.asarray(summary["passage_counts"], dtype=float)
    rows = [summary["trajectory"][str(int(length))][field] for length in lengths]
    means = np.asarray([row["mean"] for row in rows], dtype=float)
    intervals = np.asarray([row["ci95"] for row in rows], dtype=float)
    return lengths, means, intervals


def plot_series(ax, summary: dict, field: str, label: str, color: str, marker: str) -> None:
    x, mean, interval = trajectory(summary, field)
    ax.plot(x, mean, color=color, marker=marker, markersize=3.5, linewidth=1.35, label=label)
    ax.fill_between(x, interval[:, 0], interval[:, 1], color=color, alpha=0.13, linewidth=0)


def main() -> None:
    qwen = load(RESULTS / "pretrained_natural_mcqa_ladder" / "qwen_two_seed_summary.json")
    smol = load(RESULTS / "pretrained_natural_mcqa_ladder" / "smollm2_seed0_summary.json")
    models = [
        (qwen, "Qwen2.5-1.5B (2 seeds)", ROUTE_BLUE, "o"),
        (smol, "SmolLM2-1.7B (1 seed)", BOUNDARY_PURPLE, "s"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(7.05, 3.10))
    fig.subplots_adjust(left=0.075, right=0.99, bottom=0.30, top=0.88, wspace=0.38)

    for summary, label, color, marker in models:
        plot_series(axes[0], summary, "baseline_accuracy", label, color, marker)
        plot_series(axes[1], summary, "baseline_source_mass", label, color, marker)
        plot_series(axes[2], summary, "rescue_margin", label, color, marker)

    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xticks([4, 8, 16, 32])
        ax.set_xticklabels(["1x", "2x", "4x", "8x"])
        ax.set_xlabel("context multiplier")
        ax.grid(alpha=0.18)

    axes[0].set_ylim(0.82, 1.015)
    axes[0].set_ylabel("baseline accuracy")
    axes[0].set_title("(a) Accuracy declines with length", pad=5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.015),
        frameon=False,
        ncol=2,
        handlelength=1.5,
    )

    axes[1].set_yscale("log")
    axes[1].set_ylabel("baseline source mass")
    axes[1].set_title("(b) Routing trajectories disagree", pad=5)

    axes[2].axhline(0, color=MIDGRAY, linewidth=0.8, linestyle=":")
    axes[2].set_ylabel("max - control margin")
    axes[2].set_title("(c) Frozen-circuit rescue", pad=5)

    output_pdf = RESULTS / "fig_natural_length_ladder.pdf"
    output_png = RESULTS / "fig_natural_length_ladder.png"
    fig.savefig(output_pdf, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(output_png, dpi=600, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    shutil.copy2(output_pdf, PAPER / output_pdf.name)
    shutil.copy2(output_png, PAPER / output_png.name)
    print("wrote", output_pdf, output_png, "and paper copies")


if __name__ == "__main__":
    main()
