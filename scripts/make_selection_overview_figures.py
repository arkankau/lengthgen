"""Generate conceptual figures for the selection-over-scale paper.

The diagrams are explanatory companions to the empirical plots. They contain no
new measurements; every numeric callout is reported in the paper.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


RESULTS = Path("results/lengthgen")
PAPER = Path("paper_lengthgen_aaai/figures")
PAPER.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 10.5,
        "axes.titlesize": 11,
        "figure.dpi": 180,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

TEAL = "#011F5B"
VERMILION = "#990000"
GOLD = "#7F7F7F"
BLUE = "#011F5B"
CHARCOAL = "#2D3436"
MIDGRAY = "#7F7F7F"
LIGHTGRAY = "#EEF1F2"
PALE_TEAL = "#E8EEF5"
PALE_BLUE = "#E8EEF5"
PALE_RED = "#F7EAEA"
PALE_GOLD = "#F3F3F3"
WHITE = "#FFFFFF"


def save(fig: plt.Figure, name: str) -> None:
    pdf = RESULTS / f"{name}.pdf"
    png = RESULTS / f"{name}.png"
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(png, dpi=600, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    shutil.copy2(pdf, PAPER / pdf.name)
    shutil.copy2(png, PAPER / png.name)
    print("wrote", pdf, png, "and paper copies")


def box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    face: str = WHITE,
    edge: str = MIDGRAY,
    lw: float = 1.0,
) -> Rectangle:
    patch = Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw)
    ax.add_patch(patch)
    return patch


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = CHARCOAL,
    lw: float = 1.2,
    style: str = "-|>",
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=10,
            linewidth=lw,
            color=color,
            shrinkA=0,
            shrinkB=0,
        )
    )


def token_row(
    ax: plt.Axes,
    x: float,
    y: float,
    weights: list[float],
    *,
    label: str,
    label_color: str,
    evidence_index: int = 1,
) -> None:
    cell_w = 0.43
    cell_h = 0.30
    gap = 0.05
    ax.text(x - 0.08, y + cell_h / 2, label, ha="right", va="center", color=label_color, weight="bold")
    for i, value in enumerate(weights):
        left = x + i * (cell_w + gap)
        is_evidence = i == evidence_index
        face = PALE_TEAL if is_evidence else LIGHTGRAY
        edge = TEAL if is_evidence else "#A7B0B5"
        box(ax, left, y, cell_w, cell_h, face=face, edge=edge, lw=1.2 if is_evidence else 0.8)
        ax.text(left + cell_w / 2, y + 0.18, f"{value:.2f}", ha="center", va="center", fontsize=9.6)
        ax.text(
            left + cell_w / 2,
            y + 0.06,
            "evidence" if is_evidence else "D",
            ha="center",
            va="center",
            fontsize=9.6,
            color=TEAL if is_evidence else MIDGRAY,
        )


def routing_overview() -> None:
    fig, ax = plt.subplots(figsize=(7.15, 2.52))
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.05, top=0.88)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 3.0)
    ax.axis("off")
    ax.set_title("One attention spectrum, two token assignments", pad=5, weight="bold", fontsize=11)

    ax.text(7.0, 2.62, "Query: Japan -> ?     Required evidence: Tokyo", ha="center", va="center", fontsize=9.2, color=CHARCOAL)

    def assignment_panel(
        x: float,
        *,
        title: str,
        title_color: str,
        face: str,
        weights: list[float],
        result: str,
        result_color: str,
    ) -> None:
        panel_w = 6.15
        box(ax, x, 0.76, panel_w, 1.52, face=WHITE, edge=title_color, lw=1.15)
        ax.text(x + panel_w / 2, 2.08, title, ha="center", va="center", fontsize=9.1, color=title_color, weight="bold")
        labels = ["Paris", "Tokyo", "Brasilia", "other"]
        for i, (label, value) in enumerate(zip(labels, weights)):
            left = x + 0.22 + i * 1.47
            evidence = label == "Tokyo"
            chip_face = PALE_BLUE if evidence else WHITE
            chip_edge = BLUE if evidence else "#A7B0B5"
            box(ax, left, 1.13, 1.18, 0.62, face=chip_face, edge=chip_edge, lw=1.2 if evidence else 0.8)
            ax.text(left + 0.59, 1.53, label, ha="center", va="center", fontsize=8.2, color=BLUE if evidence else CHARCOAL, weight="bold" if evidence else "normal")
            ax.text(
                left + 0.59,
                1.28,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=9.4,
                color=CHARCOAL,
            )
        ax.text(x + panel_w / 2, 0.94, result, ha="center", va="center", fontsize=8.8, color=result_color, weight="bold")

    assignment_panel(
        0.25,
        title="Maximum assigned to a distractor",
        title_color=VERMILION,
        face=PALE_RED,
        weights=[0.55, 0.07, 0.25, 0.13],
        result="Source mass: 0.07",
        result_color=VERMILION,
    )
    assignment_panel(
        7.60,
        title="Maximum assigned to required evidence",
        title_color=BLUE,
        face=PALE_TEAL,
        weights=[0.07, 0.55, 0.25, 0.13],
        result="Source mass: 0.55",
        result_color=BLUE,
    )

    box(ax, 0.25, 0.14, 13.50, 0.40, face=LIGHTGRAY, edge=MIDGRAY)
    ax.text(
        7.0,
        0.34,
        "Preserved: complete weight spectrum  |  entropy  |  norms  |  maximum weight",
        ha="center",
        va="center",
        fontsize=8.9,
        color=CHARCOAL,
        weight="bold",
    )

    save(fig, "fig_routing_overview")


def paired_causal_protocol() -> None:
    fig, ax = plt.subplots(figsize=(3.35, 3.15))
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)
    ax.set_xlim(0, 6.0)
    ax.set_ylim(0, 7.0)
    ax.axis("off")

    box(ax, 0.15, 5.60, 5.70, 1.16, face=PALE_BLUE, edge="#8CA6C7", lw=1.0)
    ax.text(0.43, 6.18, "CALIBRATE", rotation=90, ha="center", va="center", fontsize=5.6, weight="bold", color=CHARCOAL)

    def node(x: float, y: float, w: float, text: str, *, face: str = WHITE, edge: str = MIDGRAY, h: float = 0.66, size: float = 8.2) -> None:
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.035,rounding_size=0.08",
            facecolor=face,
            edgecolor=edge,
            linewidth=0.9,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=CHARCOAL, weight="bold" if face != WHITE else "normal")

    node(0.75, 5.82, 1.55, "Disjoint\nexamples", h=0.70, size=5.4)
    arrow(ax, (2.35, 6.17), (2.69, 6.17), color=CHARCOAL, lw=0.9)
    node(2.75, 5.82, 1.25, "Select\ncircuit", face="#DDE8F5", edge=BLUE, h=0.70, size=5.2)
    arrow(ax, (4.05, 6.17), (4.38, 6.17), color=CHARCOAL, lw=0.9)
    node(4.45, 5.82, 1.15, "Freeze", face="#DDE8F5", edge=BLUE, h=0.70, size=5.4)

    box(ax, 0.15, 0.22, 5.70, 5.12, face="#F1F4F7", edge="#8CA6C7", lw=1.0)
    ax.text(0.43, 2.78, "PAIRED TEST", rotation=90, ha="center", va="center", fontsize=5.6, weight="bold", color=CHARCOAL)
    node(1.05, 4.47, 3.90, "Same evaluation row", h=0.60, size=6.0)

    arrow(ax, (3.0, 4.43), (1.83, 3.92), color=BLUE, lw=1.0)
    arrow(ax, (3.0, 4.43), (4.17, 3.92), color=VERMILION, lw=1.0)

    node(0.78, 2.67, 2.18, "TREATMENT\nsource <->\nrow maximum", face=PALE_TEAL, edge=BLUE, h=1.25, size=5.2)
    node(3.04, 2.67, 2.18, "CONTROL\nmatched\ndistractor swap", face=PALE_RED, edge=VERMILION, h=1.25, size=5.2)
    ax.text(1.87, 2.48, r"$\delta=a_d-a_s$", ha="center", va="center", fontsize=6.4, color=BLUE)
    ax.text(4.13, 2.48, r"$\epsilon=\left|\,|a_p-a_q|-\delta\,\right|$", ha="center", va="center", fontsize=6.2, color=VERMILION)

    arrow(ax, (1.87, 2.22), (1.87, 1.78), color=CHARCOAL, lw=0.9)
    arrow(ax, (4.13, 2.22), (4.13, 1.78), color=CHARCOAL, lw=0.9)
    node(0.78, 1.10, 4.44, "Compare paired\noutput margins", face="#DDE8F5", edge=BLUE, h=0.58, size=5.6)
    node(0.78, 0.30, 4.44, "Exact: spectrum, entropy, norms\nMatched: displacement", h=0.62, size=4.6)

    save(fig, "fig_paired_causal_protocol")


def pipeline_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: list[str],
    *,
    face: str,
    edge: str,
) -> None:
    box(ax, x, y, w, h, face=face, edge=edge, lw=1.1)
    ax.text(x + w / 2, y + h - 0.16, title, ha="center", va="center", fontsize=7.6, weight="bold", color=edge)
    ax.text(x + w / 2, y + h - 0.39, "\n".join(lines), ha="center", va="top", fontsize=6.4, color=CHARCOAL, linespacing=1.18)


def experiment_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(7.15, 2.05))
    fig.subplots_adjust(left=0.01, right=0.995, bottom=0.08, top=0.84)
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 2.25)
    ax.axis("off")
    ax.set_title("The experiment in practice: a paired causal test", pad=8, weight="bold", fontsize=9.5)

    w, h, y = 1.75, 1.08, 0.76
    xs = [0.05, 2.08, 4.11, 6.14, 8.17, 10.20]
    pipeline_box(
        ax,
        xs[0],
        y,
        w,
        h,
        "1. Calibrate",
        ["Disjoint short-context", "examples rank layers", "and heads"],
        face=PALE_GOLD,
        edge=GOLD,
    )
    pipeline_box(
        ax,
        xs[1],
        y,
        w,
        h,
        "2. Freeze",
        ["Fix circuit, model,", "prompts, values, and", "decoding settings"],
        face=LIGHTGRAY,
        edge=MIDGRAY,
    )
    pipeline_box(
        ax,
        xs[2],
        y,
        w,
        h,
        "3. Reassign",
        ["Same attention row:", "source-max / min /", "distractor control"],
        face=PALE_TEAL,
        edge=TEAL,
    )
    pipeline_box(
        ax,
        xs[3],
        y,
        w,
        h,
        "4. Audit",
        ["Sorted spectrum,", "entropy, norms, and", "maximum unchanged"],
        face=LIGHTGRAY,
        edge=MIDGRAY,
    )
    pipeline_box(
        ax,
        xs[4],
        y,
        w,
        h,
        "5. Measure",
        ["Paired change in", "answer margin and", "accuracy"],
        face=PALE_TEAL,
        edge=TEAL,
    )
    pipeline_box(
        ax,
        xs[5],
        y,
        w,
        h,
        "6. Test theory",
        ["Compare exact effect", "with transferred mass", r"$\times$ utility gap"],
        face=PALE_RED,
        edge=VERMILION,
    )

    for left, right in zip(xs[:-1], xs[1:]):
        arrow(ax, (left + w + 0.05, y + h / 2), (right - 0.05, y + h / 2), color=CHARCOAL)

    ax.text(
        6.1,
        0.43,
        "Identification: every condition uses the same examples and the same attention-weight multiset; "
        "only assignment differs.",
        ha="center",
        va="center",
        fontsize=7,
        color=CHARCOAL,
        weight="bold",
    )
    ax.text(
        6.1,
        0.13,
        "Boundary checks: competence gate, saturation, random/adjacent-layer controls, head dose, interpolation, "
        "multiple evidence tokens, and natural QA.",
        ha="center",
        va="center",
        fontsize=6.6,
        color=MIDGRAY,
    )

    save(fig, "fig_experiment_pipeline")


if __name__ == "__main__":
    routing_overview()
    paired_causal_protocol()
    experiment_pipeline()
