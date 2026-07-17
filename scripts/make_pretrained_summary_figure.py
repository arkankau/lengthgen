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

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 9.6,
        "axes.titlesize": 9.8,
        "axes.labelsize": 9.6,
        "xtick.labelsize": 9.6,
        "ytick.labelsize": 9.6,
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


def causal_trajectory(path: Path, seed: int) -> list[tuple[int, float, tuple[float, float]]]:
    data = load(path)
    rows = []
    for length_text, sweep in sorted(data["lengths"].items(), key=lambda item: int(item[0])):
        source = sweep["conditions"]["source_max"]["records"]
        control = sweep["conditions"]["distractor_control"]["records"]
        effects = np.asarray(
            [left["margin"] - right["margin"] for left, right in zip(source, control)],
            dtype=np.float64,
        )
        rows.append((int(length_text), float(effects.mean()), paired_interval(effects, seed)))
    return rows


def main() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.05, 5.35))
    fig.subplots_adjust(left=0.075, right=0.98, bottom=0.10, top=0.88, wspace=0.48, hspace=0.46)

    # The same source-max operation has different effects across pretrained circuits.
    models = [
        ("Qwen", "pretrained_causal_qwen1p5b", ROUTE_BLUE, "s", "-"),
        ("Pythia", "pretrained_causal_pythia1p4b", ROUTE_BLUE, "o", "--"),
        ("Gemma", "pretrained_causal_gemma2b", BOUNDARY_PURPLE, "^", "-."),
        ("SmolLM2", "pretrained_causal_smollm2_1p7b", HARM_ORANGE, "D", ":"),
    ]
    ax = axes[0, 0]
    for index, (label, directory, color, marker, linestyle) in enumerate(models):
        rows = causal_trajectory(
            RESULTS / directory / "pretrained_causal_routing_results.json", 3100 + index
        )
        x = np.asarray([row[0] for row in rows])
        y = np.asarray([row[1] for row in rows])
        ci = np.asarray([row[2] for row in rows])
        ax.errorbar(
            x,
            y,
            yerr=np.vstack([y - ci[:, 0], ci[:, 1] - y]),
            color=color,
            marker=marker,
            markersize=3.5,
            linewidth=1.2,
            linestyle=linestyle,
            capsize=2,
            label=label,
        )
    ax.axhline(0, color=MIDGRAY, linewidth=0.8, linestyle=":")
    ax.set_xscale("log", base=2)
    ax.set_xticks([5, 20, 80, 160])
    ax.set_xticklabels([5, 20, 80, 160])
    ax.set_xlim(4, 235)
    ax.set_xlabel("key-value pairs")
    ax.set_ylabel("margin effect (max - control)")
    ax.set_title("(a) Routing varies by model regime", pad=5)
    ax.grid(alpha=0.18)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.30, 0.995),
        frameon=False,
        fontsize=8.0,
        ncol=2,
        handlelength=1.4,
        columnspacing=0.8,
    )

    # A broad selector ablation tests whether output-conditioned scoring matters.
    selector = load(RESULTS / "pretrained_selector_ablation_summary.json")["selectors"]
    selector_order = [
        ("source grad.", "source_gradient", ROUTE_BLUE),
        ("utility gain", "utility_gain", UTILITY_TEAL),
        ("utility gap", "utility_gap", UTILITY_TEAL),
        ("random", "random", MIDGRAY),
        ("grad. magnitude", "gradient_magnitude", MIDGRAY),
        ("source mass", "source_mass", HARM_ORANGE),
        ("transfer mass", "transfer_mass", CONTROL_GRAY),
    ]
    ax = axes[0, 1]
    labels = [row[0] for row in selector_order][::-1]
    means = np.asarray([selector[row[1]]["mean"] for row in selector_order][::-1])
    cis = np.asarray([selector[row[1]]["ci95"] for row in selector_order][::-1])
    colors = [row[2] for row in selector_order][::-1]
    positions = np.arange(len(labels))
    ax.barh(positions, means, color=colors, alpha=0.88, height=0.68)
    ax.errorbar(
        means,
        positions,
        xerr=np.vstack([means - cis[:, 0], cis[:, 1] - means]),
        fmt="none",
        ecolor=CHARCOAL,
        elinewidth=0.8,
        capsize=2,
    )
    ax.axvline(0, color=MIDGRAY, linewidth=0.8, linestyle=":")
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.set_xlabel("margin effect (max - control)")
    ax.set_title("(b) Output-aware selection", pad=5)
    ax.grid(axis="x", alpha=0.18)

    # Interpolation tests whether the effect changes smoothly with intervention strength.
    dose = load(RESULTS / "pretrained_dose_response_summary.json")
    alphas = np.asarray(dose["alphas"], dtype=np.float64)
    dose_rows = [dose["dose_response"][str(float(alpha))] for alpha in alphas]
    means = np.asarray([row["mean"] for row in dose_rows])
    cis = np.asarray([row["ci95"] for row in dose_rows])
    ax = axes[1, 0]
    for seed_values in zip(*[row["seed_means"] for row in dose_rows]):
        ax.plot(alphas, seed_values, color=LIGHTGRAY, linewidth=0.9, zorder=1)
    ax.errorbar(
        alphas,
        means,
        yerr=np.vstack([means - cis[:, 0], cis[:, 1] - means]),
        color=UTILITY_TEAL,
        marker="o",
        markersize=4,
        linewidth=1.5,
        capsize=2.5,
        zorder=2,
    )
    ax.axhline(0, color=MIDGRAY, linewidth=0.8, linestyle=":")
    ax.set_xticks(alphas)
    ax.set_xlabel(r"intervention strength $\alpha$")
    ax.set_ylabel("margin effect (max - control)")
    ax.set_title("(c) Response is graded", pad=5)
    ax.grid(alpha=0.18)

    # The natural QA experiment keeps the task grounded in ordinary text.
    natural = load(RESULTS / "pretrained_natural_mcqa_summary.json")["effects"]
    natural_order = [
        ("source mass", natural["source_mass"]["margin"], HARM_ORANGE),
        ("utility gain", natural["utility_gain"]["margin"], UTILITY_TEAL),
    ]
    ax = axes[1, 1]
    labels = [row[0] for row in natural_order]
    means = np.asarray([row[1]["mean"] for row in natural_order])
    cis = np.asarray([row[1]["ci95"] for row in natural_order])
    ax.bar(labels, means, color=[row[2] for row in natural_order], width=0.58, alpha=0.88)
    ax.errorbar(
        np.arange(len(labels)),
        means,
        yerr=np.vstack([means - cis[:, 0], cis[:, 1] - means]),
        fmt="none",
        ecolor=CHARCOAL,
        elinewidth=0.9,
        capsize=3,
    )
    ax.axhline(0, color=MIDGRAY, linewidth=0.8, linestyle=":")
    ax.set_ylabel("margin effect (max - control)")
    ax.set_title("(d) Natural-QA transfer", pad=5)
    ax.grid(axis="y", alpha=0.18)

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
