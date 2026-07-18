"""Generate paper figures for the capacity-assignment and model-family results."""
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

plt.rcParams.update({
    "font.size": 10.2,
    "axes.titlesize": 10.5,
    "axes.labelsize": 10.2,
    "xtick.labelsize": 10.2,
    "ytick.labelsize": 10.2,
    "legend.fontsize": 10.0,
    "lines.linewidth": 1.4,
    "figure.dpi": 160,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

ROUTE_BLUE = "#011F5B"
UTILITY_TEAL = "#011F5B"
HARM_ORANGE = "#990000"
CONTROL_GRAY = "#7F7F7F"
BOUNDARY_PURPLE = "#7F7F7F"
CHARCOAL = "#333333"


def save(fig, name, *, rect=None):
    fig.tight_layout(pad=0.6, rect=rect)
    pdf = RESULTS / f"{name}.pdf"
    png = RESULTS / f"{name}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=600, bbox_inches="tight")
    plt.close(fig)
    shutil.copy2(pdf, PAPER / pdf.name)
    shutil.copy2(png, PAPER / png.name)
    print("wrote", pdf, png, "and paper copies")


def mechanism_figure():
    factorial = json.loads(
        (RESULTS / "factorial_grid/concentration_assignment_summary.json").read_text()
    )
    utility = json.loads(
        (RESULTS / "utility_gap/routing_utility_gap_results.json").read_text()
    )["summary"]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.10))

    ax = axes[0]
    betas = [1, 2, 4]
    rows = [factorial["beta_effects"][str(beta)] for beta in betas]
    capacity = np.array([row["capacity_mean"] for row in rows])
    assignment = np.array([row["correct_wrong"]["mean"] for row in rows])
    assignment_ci = np.array([row["correct_wrong"]["ci95"] for row in rows])
    sharpening = np.array([row["identity_baseline"]["mean"] for row in rows])
    sharpening_ci = np.array([row["identity_baseline"]["ci95"] for row in rows])
    ax.errorbar(
        capacity,
        assignment,
        yerr=np.vstack([assignment - assignment_ci[:, 0], assignment_ci[:, 1] - assignment]),
        marker="o",
        color=ROUTE_BLUE,
        capsize=3,
        label="correct vs. wrong assignment",
    )
    ax.errorbar(
        capacity,
        sharpening,
        yerr=np.vstack([sharpening - sharpening_ci[:, 0], sharpening_ci[:, 1] - sharpening]),
        marker="s",
        linestyle="--",
        color=CONTROL_GRAY,
        capsize=3,
        label="sharpening only",
    )
    ax.axhline(0, color="0.55", linewidth=0.7, linestyle=":")
    ax.set_xlabel("mean maximum attention weight")
    ax.set_ylabel("assignment accuracy contrast")
    ax.set_title("(a) Capacity amplifies assignment")
    ax.grid(alpha=0.2)

    ax = axes[1]
    groups = utility["groups"]
    markers = {("argmax", "nope"): "o", ("argmax", "rope"): "s", ("flagret", "nope"): "^", ("flagret", "rope"): "D"}
    for task in ("argmax", "flagret"):
        for pe in ("nope", "rope"):
            marker = markers[(task, pe)]
            selected = [row for row in groups if row["task"] == task and row["pe"] == pe]
            ax.scatter(
                [row["mean_first_order_change"] for row in selected],
                [row["mean_actual_change"] for row in selected],
                facecolor=UTILITY_TEAL if pe == "nope" else "white",
                edgecolor=UTILITY_TEAL,
                marker=marker,
                s=25,
                alpha=0.85,
                label=f"{task}, {pe.upper()}",
            )
    values = [
        value
        for row in groups
        for value in (row["mean_first_order_change"], row["mean_actual_change"])
    ]
    low, high = min(values), max(values)
    pad = 0.05 * (high - low)
    ax.plot([low - pad, high + pad], [low - pad, high + pad], color=CHARCOAL, linestyle=":", linewidth=1)
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    ax.set_xlabel("first-order predicted margin change")
    ax.set_ylabel("exact margin change")
    ax.set_title("(b) Utility predicts the finite swap effect")
    ax.grid(alpha=0.2)
    handles_left, labels_left = axes[0].get_legend_handles_labels()
    handles_right, labels_right = axes[1].get_legend_handles_labels()
    fig.legend(
        handles_left + handles_right,
        labels_left + labels_right,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.015),
        ncol=3,
        frameon=False,
        fontsize=8.4,
        handlelength=1.6,
        columnspacing=1.15,
    )
    save(fig, "fig_capacity_assignment", rect=(0, 0.16, 1, 1))


def aggregate_real_model(path):
    data = json.loads(path.read_text())
    rows = []
    for length in sorted({int(row["N"]) for row in data["records"]}):
        selected = [row for row in data["records"] if int(row["N"]) == length]
        rows.append((
            length,
            float(np.mean([row["correct"] for row in selected])),
            float(np.mean([row["a_js"] for row in selected])),
        ))
    return rows


def real_model_figure():
    models = [
        ("Pythia-1.4B", RESULTS / "realmodel_results.json", CHARCOAL, "o"),
        ("Qwen2.5-1.5B", RESULTS / "realmodel_qwen1p5b_h8.json", ROUTE_BLUE, "s"),
        ("Gemma-2-2B", RESULTS / "realmodel_gemma2b_h8.json", BOUNDARY_PURPLE, "^"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.45), sharex=True)
    for label, path, color, marker in models:
        rows = aggregate_real_model(path)
        lengths = [row[0] for row in rows]
        axes[0].plot(lengths, [row[1] for row in rows], marker=marker, color=color, label=label)
        axes[1].plot(lengths, [row[2] for row in rows], marker=marker, color=color, label=label)
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xticks([5, 10, 20, 40, 80, 160])
        ax.set_xticklabels([5, 10, 20, 40, 80, 160])
        ax.set_xlabel("number of key-value pairs")
        ax.grid(alpha=0.2)
    axes[0].set_ylim(-0.02, 0.82)
    axes[0].set_ylabel("exact next-token accuracy")
    axes[0].set_title("(a) Retrieval accuracy")
    axes[1].set_ylim(0, 0.75)
    axes[1].set_ylabel("selected-head source attention")
    axes[1].set_title("(b) Task-conditioned routing")
    axes[1].legend(loc="upper right")
    save(fig, "fig_realmodel_family")


if __name__ == "__main__":
    mechanism_figure()
    real_model_figure()
