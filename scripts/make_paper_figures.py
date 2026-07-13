from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path("results")
OUT = Path("paper/figures")
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_basin_energy_depth_figure() -> None:
    """Cross-model basin-energy figure.

    The load-bearing cross-model signal is NOT the raw separation magnitude (which is
    comparable across models) but (a) the agreement between two independently-constructed
    refusal-axis margins -- single mean-difference anchor vs. multi-pair subspace primary
    axis -- and (b) the depth structure of that separation on the aligned model. Panel A
    plots the single-vs-subspace correlation against fractional depth for both models
    (aligned: positive/agreeing; unaligned: negative/disagreeing). Panel B plots sep(margin)
    by layer on the aligned model, showing the mid-to-late rise and the layer-22/23 collapse.
    """
    distilgpt2_rows = read_csv(RESULTS / "basin_energy_depth_sweep_distilgpt2.csv")
    qwen_rows = read_csv(RESULTS / "basin_energy_depth_sweep_qwen.csv")
    n_distil, n_qwen = 6, 24

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6))

    ax = axes[0]
    ax.axhline(0.0, color="gray", linewidth=0.6, linestyle=":")
    d_depth = [int(r["layer"]) / n_distil for r in distilgpt2_rows]
    d_corr = [float(r["correlation_single_vs_subspace"]) for r in distilgpt2_rows]
    q_depth = [int(r["layer"]) / n_qwen for r in qwen_rows]
    q_corr = [float(r["correlation_single_vs_subspace"]) for r in qwen_rows]
    ax.plot(d_depth, d_corr, marker="s", markersize=3, linewidth=1.1, linestyle="--",
            color="tab:red", label="distilgpt2 (no RLHF)")
    ax.plot(q_depth, q_corr, marker="^", markersize=3, linewidth=1.2,
            color="tab:blue", label="Qwen2.5-0.5B-Instruct (aligned)")
    ax.set_xlabel("fractional depth (layer / num layers)", fontsize=8)
    ax.set_ylabel("corr(single, subspace)\nmargin agreement", fontsize=8)
    ax.set_title("(a) Refusal-axis agreement", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="lower right")

    ax = axes[1]
    ax.axhline(0.0, color="gray", linewidth=0.6, linestyle=":")
    q_layers = [int(r["layer"]) for r in qwen_rows]
    q_sep = [float(r["sep_margin_single_anchor"]) for r in qwen_rows]
    ax.plot(q_layers, q_sep, marker="^", markersize=3, linewidth=1.2, color="tab:blue")
    ax.set_xlabel("layer (of 24)", fontsize=8)
    ax.set_ylabel("sep(margin)\n(jailbreak - benign)", fontsize=8)
    ax.set_title("(b) Aligned-model depth structure", fontsize=9)
    ax.tick_params(labelsize=7)

    fig.tight_layout()
    fig.savefig(OUT / "basin_energy_depth.pdf")
    plt.close(fig)
    print("wrote", OUT / "basin_energy_depth.pdf")


def make_null_attractor_fix_figure() -> None:
    pre_fix = read_csv(RESULTS / "null_attractor_depth_qwen_summary.csv")
    pre_fix_risk0 = read_csv(RESULTS / "null_attractor_depth_qwen_risk0_summary.csv")
    post_fix = read_csv(RESULTS / "null_attractor_depth_qwen_fixed_summary.csv")

    layers = [int(r["layer"]) for r in pre_fix]
    pre_fix_sep = [float(r["sep_m_null"]) for r in pre_fix]
    pre_fix_risk0_sep = [float(r["sep_m_null"]) for r in pre_fix_risk0]
    post_fix_attributable_sep = [float(r["risk_attributable_sep_m_null"]) for r in post_fix]

    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ax.axhline(0.0, color="gray", linewidth=0.6, linestyle=":")
    ax.plot(layers, pre_fix_sep, marker="o", markersize=3, linewidth=1.2, label="pre-fix, raw sep(m_null)", color="tab:red")
    ax.plot(
        layers, pre_fix_risk0_sep, marker="s", markersize=3, linewidth=1.0, linestyle="--",
        label="pre-fix, risk=0 control", color="tab:orange",
    )
    ax.plot(
        layers, post_fix_attributable_sep, marker="^", markersize=3, linewidth=1.2,
        label="post-fix, risk-attributable sep", color="tab:blue",
    )
    ax.set_xlabel("layer (of 24)", fontsize=8)
    ax.set_ylabel("sep(m_null)\n(jailbreak - benign)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "null_attractor_depth_fix.pdf")
    plt.close(fig)
    print("wrote", OUT / "null_attractor_depth_fix.pdf")


if __name__ == "__main__":
    make_basin_energy_depth_figure()
    make_null_attractor_fix_figure()
