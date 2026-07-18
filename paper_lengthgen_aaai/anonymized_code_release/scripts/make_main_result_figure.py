"""Generate the central fixed-spectrum intervention figure for the main paper."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


RESULTS = Path("results/lengthgen")
PAPER = Path("paper_lengthgen_aaai/figures")
PAPER.mkdir(parents=True, exist_ok=True)

ROUTE_BLUE = "#011F5B"
UTILITY_TEAL = "#011F5B"
HARM_ORANGE = "#990000"
CONTROL_GRAY = "#7F7F7F"
LIGHT_GRAY = "#D9D9D9"
CHARCOAL = "#303030"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 9.6,
        "axes.titlesize": 10.0,
        "axes.labelsize": 9.6,
        "xtick.labelsize": 9.6,
        "ytick.labelsize": 9.6,
        "legend.fontsize": 9.6,
        "figure.dpi": 180,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load(name: str) -> list[dict]:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def bootstrap(values: np.ndarray, seed: int, draws: int = 20000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = []
    for start in range(0, draws, 1000):
        count = min(1000, draws - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        means.append(values[indices].mean(axis=1))
    return tuple(float(value) for value in np.quantile(np.concatenate(means), [0.025, 0.975]))


def fixed_spectrum_effects() -> tuple[list[dict], dict[str, np.ndarray]]:
    records = load("paired_head_count_full_grid.json")
    modes = ("source_max", "distractor_control", "source_min")
    values = {mode: [] for mode in modes}
    metadata = []
    for record in records:
        cfg = record["cfg"]
        metadata.append(cfg)
        for mode in modes:
            effects = []
            for sweep in record["lengths"].values():
                baseline = sweep["baseline"]["token_accuracy"]
                condition = sweep["sweeps"]["8"]["conditions"][mode]
                effects.append(condition["token_accuracy"] - baseline)
            values[mode].append(float(np.mean(effects)))
    return metadata, {key: np.asarray(value, dtype=np.float64) for key, value in values.items()}


def head_dose_effects() -> tuple[list[dict], dict[int, np.ndarray]]:
    records = load("paired_head_count_full_grid.json")
    counts = (1, 2, 4, 8)
    values = {count: [] for count in counts}
    metadata = []
    for record in records:
        metadata.append(record["cfg"])
        for count in counts:
            effects = []
            for sweep in record["lengths"].values():
                baseline = sweep["baseline"]["token_accuracy"]
                source_max = sweep["sweeps"][str(count)]["conditions"]["source_max"]
                effects.append(source_max["token_accuracy"] - baseline)
            values[count].append(float(np.mean(effects)))
    return metadata, {key: np.asarray(value, dtype=np.float64) for key, value in values.items()}


def draw_assignment(ax, title: str) -> None:
    metadata, effects = fixed_spectrum_effects()
    conditions = [
        ("source-max", "source_max", ROUTE_BLUE),
        ("distractor control", "distractor_control", CONTROL_GRAY),
        ("source-min", "source_min", HARM_ORANGE),
    ]
    jitter = np.linspace(-0.13, 0.13, len(metadata))
    for position, (label, key, color) in enumerate(conditions):
        for index, (cfg, value) in enumerate(zip(metadata, effects[key])):
            marker = "o" if cfg["task"] == "argmax" else "s"
            face = color if cfg["pe"] == "nope" else "white"
            ax.scatter(
                position + jitter[index],
                value,
                s=19,
                marker=marker,
                facecolor=face,
                edgecolor=color,
                linewidth=0.8,
                alpha=0.72,
                zorder=2,
            )
        mean = float(effects[key].mean())
        low, high = bootstrap(effects[key], 7100 + position)
        ax.errorbar(
            position,
            mean,
            yerr=[[mean - low], [high - mean]],
            color=CHARCOAL,
            marker="D",
            markerfacecolor=color,
            markeredgecolor=CHARCOAL,
            markersize=6,
            linewidth=1.1,
            capsize=3,
            zorder=4,
        )
    ax.axhline(0, color=CONTROL_GRAY, linestyle=":", linewidth=0.9)
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([row[0] for row in conditions])
    ax.set_ylabel("change in per-token accuracy")
    ax.set_title(title)
    ax.grid(axis="y", color=LIGHT_GRAY, linewidth=0.6, alpha=0.65)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markeredgecolor=CHARCOAL, markerfacecolor="white", label="argmax"),
            Line2D([0], [0], marker="s", color="none", markeredgecolor=CHARCOAL, markerfacecolor="white", label="marked retrieval"),
        ],
        loc="upper center",
        frameon=False,
        ncol=2,
        handletextpad=0.4,
        columnspacing=0.8,
    )


def draw_coverage(ax, title: str) -> None:
    metadata, dose = head_dose_effects()
    counts = np.asarray(sorted(dose), dtype=np.int64)
    positions = np.arange(len(counts))
    for index in range(len(metadata)):
        line = np.asarray([dose[int(count)][index] for count in counts])
        ax.plot(
            positions,
            line,
            color=ROUTE_BLUE,
            alpha=0.18,
            linewidth=0.8,
            marker="o",
            markersize=2,
            zorder=1,
        )
    means = np.asarray([dose[int(count)].mean() for count in counts])
    cis = np.asarray([bootstrap(dose[int(count)], 7200 + int(count)) for count in counts])
    ax.errorbar(
        positions,
        means,
        yerr=np.vstack([means - cis[:, 0], cis[:, 1] - means]),
        color=ROUTE_BLUE,
        marker="D",
        markeredgecolor=CHARCOAL,
        markersize=5.5,
        linewidth=1.6,
        capsize=3,
        zorder=3,
    )
    ax.axhline(0, color=CONTROL_GRAY, linestyle=":", linewidth=0.9)
    ax.set_xticks(positions)
    ax.set_xticklabels(["12.5%", "25%", "50%", "100%"])
    ax.set_xlabel("selected-circuit coverage")
    ax.set_ylabel("source-max accuracy change")
    ax.set_title(title)
    ax.grid(axis="y", color=LIGHT_GRAY, linewidth=0.6, alpha=0.65)


def save_figure(fig, stem: str) -> None:
    output_pdf = RESULTS / f"{stem}.pdf"
    output_png = RESULTS / f"{stem}.png"
    fig.savefig(output_pdf, bbox_inches="tight", pad_inches=0.03)
    fig.savefig(output_png, dpi=600, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    shutil.copy2(output_pdf, PAPER / output_pdf.name)
    shutil.copy2(output_png, PAPER / output_png.name)
    print("wrote", output_pdf, output_png, "and paper copies")


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.05, 3.15))
    fig.subplots_adjust(left=0.075, right=0.99, bottom=0.19, top=0.90, wspace=0.28)
    draw_assignment(axes[0], "(a) Assignment changes accuracy at fixed spectrum")
    draw_coverage(axes[1], "(b) The effect grows with circuit coverage")
    save_figure(fig, "fig_fixed_spectrum_result")

    fig, ax = plt.subplots(figsize=(3.35, 2.45))
    fig.subplots_adjust(left=0.17, right=0.99, bottom=0.20, top=0.89)
    draw_assignment(ax, "Assignment changes accuracy")
    save_figure(fig, "fig_assignment_effect")

    fig, ax = plt.subplots(figsize=(3.35, 2.45))
    fig.subplots_adjust(left=0.17, right=0.99, bottom=0.20, top=0.89)
    draw_coverage(ax, "Effect grows with circuit coverage")
    save_figure(fig, "fig_circuit_coverage")


if __name__ == "__main__":
    main()
