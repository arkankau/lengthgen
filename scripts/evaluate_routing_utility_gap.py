"""Test the nonlinear routing theorem on cached length-generalization models.

For each example, interpolate from the natural attention row (alpha=0) to the
exact source-max permutation (alpha=1) in a train-length-selected retrieval
layer. Differentiate the target-vs-baseline-competitor logit margin at alpha=0,
then compare the first-order prediction with the actual full-swap margin change.

The per-head derivative is delta_h * (u_source - u_distractor). Dividing by the
transferred attention mass delta_h therefore estimates the theorem's local
value-utility gap for active swaps.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "colab"))
import length_gen_colab as G  # noqa: E402
from paired_permutation_experiment import (  # noqa: E402
    checkpoint_path,
    make_cfg,
    sample_batches,
    select_circuit,
)


def pearson(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if len(x) < 2 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def rankdata(values):
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1)
        start = end
    return ranks


def spearman(x, y):
    return pearson(rankdata(x), rankdata(y))


def finite(value):
    return float(value) if math.isfinite(float(value)) else None


def load_model(cfg, args):
    path = checkpoint_path(cfg, args)
    if not Path(path).exists():
        raise FileNotFoundError(f"cached checkpoint required: {path}")
    model = G.build_model(cfg)
    model.load_state_dict(torch.load(path, map_location=G.DEVICE, weights_only=True))
    model.eval()
    model.requires_grad_(False)
    return model, path


def answer_margin(logits, y, aq):
    batch = torch.arange(logits.shape[0], device=logits.device)
    answer_logits = logits[batch, aq]
    targets = y[batch, aq]
    alternatives = answer_logits.detach().clone()
    alternatives[batch, targets] = -torch.inf
    competitors = alternatives.argmax(dim=-1)
    margin = answer_logits[batch, targets] - answer_logits[batch, competitors]
    return margin, targets, competitors


def fixed_competitor_margin(logits, targets, competitors, aq):
    batch = torch.arange(logits.shape[0], device=logits.device)
    answer_logits = logits[batch, aq]
    return answer_logits[batch, targets] - answer_logits[batch, competitors]


def top1_margin(logits, targets, aq):
    batch = torch.arange(logits.shape[0], device=logits.device)
    answer_logits = logits[batch, aq]
    alternatives = answer_logits.clone()
    alternatives[batch, targets] = -torch.inf
    return answer_logits[batch, targets] - alternatives.max(dim=-1).values


def transfer_mass(rows, aq, tgt, heads):
    values = torch.zeros(rows.shape[0], rows.shape[1], device=rows.device)
    for index in range(rows.shape[0]):
        query = int(aq[index])
        source = int(tgt[index])
        valid = rows[index, :, : query + 1]
        values[index] = valid.max(dim=-1).values - rows[index, :, source]
    return values[:, heads]


def evaluate_batch(model, x, y, aq, tgt, layer, heads):
    batch_size = x.shape[0]
    n_heads = len(model.blocks[layer].attn_tgt_heads)
    alpha = torch.zeros(batch_size, n_heads, device=x.device, requires_grad=True)
    G.PATCH = {
        "layer": layer,
        "heads": heads,
        "mode": "source_max",
        "alpha": alpha,
        "diagnostics": {},
    }
    logits0 = model(x, aq, tgt)
    rows0 = model.blocks[layer].aq_attn_rows.detach()
    margin0, targets, competitors = answer_margin(logits0, y, aq)
    gradient = torch.autograd.grad(margin0.sum(), alpha)[0]
    contributions = gradient[:, heads]
    transfers = transfer_mass(rows0, aq, tgt, heads)
    first_order = contributions.sum(dim=-1)

    G.PATCH = {"layer": layer, "heads": heads, "mode": "source_max", "diagnostics": {}}
    with torch.no_grad():
        logits1 = model(x, aq, tgt)
        margin1 = fixed_competitor_margin(logits1, targets, competitors, aq)
        multiclass0 = top1_margin(logits0.detach(), targets, aq)
        multiclass1 = top1_margin(logits1, targets, aq)
    G.PATCH = None

    actual = margin1 - margin0.detach()
    records = []
    for index in range(batch_size):
        per_head = []
        for local, head in enumerate(heads):
            delta = float(transfers[index, local].cpu())
            weighted = float(contributions[index, local].detach().cpu())
            per_head.append({
                "head": int(head),
                "transfer_mass": delta,
                "weighted_utility": weighted,
                "utility_gap": weighted / delta if delta > 1e-8 else None,
            })
        records.append({
            "baseline_pairwise_margin": float(margin0[index].detach().cpu()),
            "baseline_multiclass_margin": float(multiclass0[index].cpu()),
            "source_max_multiclass_margin": float(multiclass1[index].cpu()),
            "first_order_margin_change": float(first_order[index].detach().cpu()),
            "actual_margin_change": float(actual[index].cpu()),
            "curvature_residual": float((actual[index] - first_order[index].detach()).cpu()),
            "baseline_correct": int(multiclass0[index] > 0),
            "source_max_correct": int(multiclass1[index] > 0),
            "heads": per_head,
        })
    return records


def summarize(records):
    groups = defaultdict(list)
    for row in records:
        groups[(row["task"], row["pe"], row["seed"], row["length"])].append(row)

    group_rows = []
    centered_pred = []
    centered_actual = []
    for key, rows in groups.items():
        predicted = np.array([row["first_order_margin_change"] for row in rows])
        actual = np.array([row["actual_margin_change"] for row in rows])
        active_utilities = [
            head["utility_gap"]
            for row in rows for head in row["heads"]
            if head["utility_gap"] is not None
        ]
        nonzero = np.abs(actual) > 1e-8
        sign_agreement = float(np.mean(np.sign(predicted[nonzero]) == np.sign(actual[nonzero]))) if nonzero.any() else float("nan")
        group_rows.append({
            "task": key[0], "pe": key[1], "seed": key[2], "length": key[3],
            "n_examples": len(rows),
            "mean_first_order_change": float(predicted.mean()),
            "mean_actual_change": float(actual.mean()),
            "pearson": finite(pearson(predicted, actual)),
            "spearman": finite(spearman(predicted, actual)),
            "sign_agreement": finite(sign_agreement),
            "mean_abs_residual": float(np.mean(np.abs(actual - predicted))),
            "positive_active_utility_fraction": float(np.mean(np.asarray(active_utilities) > 0)) if active_utilities else None,
        })
        centered_pred.extend(predicted - predicted.mean())
        centered_actual.extend(actual - actual.mean())

    predicted = np.array([row["first_order_margin_change"] for row in records])
    actual = np.array([row["actual_margin_change"] for row in records])
    residual = actual - predicted
    utilities = [
        head["utility_gap"]
        for row in records for head in row["heads"]
        if head["utility_gap"] is not None
    ]
    nonzero = np.abs(actual) > 1e-8
    group_predicted = [row["mean_first_order_change"] for row in group_rows]
    group_actual = [row["mean_actual_change"] for row in group_rows]
    return {
        "n_examples": len(records),
        "n_model_length_cells": len(group_rows),
        "pooled_pearson": finite(pearson(predicted, actual)),
        "pooled_spearman": finite(spearman(predicted, actual)),
        "within_cell_pearson": finite(pearson(centered_pred, centered_actual)),
        "model_length_mean_pearson": finite(pearson(group_predicted, group_actual)),
        "sign_agreement": float(np.mean(np.sign(predicted[nonzero]) == np.sign(actual[nonzero]))) if nonzero.any() else None,
        "mean_first_order_change": float(predicted.mean()),
        "mean_actual_change": float(actual.mean()),
        "mean_abs_curvature_residual": float(np.mean(np.abs(residual))),
        "median_abs_curvature_residual": float(np.median(np.abs(residual))),
        "positive_active_utility_fraction": float(np.mean(np.asarray(utilities) > 0)) if utilities else None,
        "baseline_accuracy": float(np.mean([row["baseline_correct"] for row in records])),
        "source_max_accuracy": float(np.mean([row["source_max_correct"] for row in records])),
        "groups": group_rows,
    }


def write_report(path, summary):
    def fmt(value):
        return "NA" if value is None else f"{value:.3f}"

    lines = [
        "# Routing Utility-Gap Audit",
        "",
        "The first-order term is the gradient of the target-vs-baseline-competitor logit margin along the exact source-max permutation path at the natural attention row.",
        "",
        f"- Examples: {summary['n_examples']} across {summary['n_model_length_cells']} model-length cells.",
        f"- Pooled Pearson / Spearman: {fmt(summary['pooled_pearson'])} / {fmt(summary['pooled_spearman'])}.",
        f"- Within-cell Pearson: {fmt(summary['within_cell_pearson'])}.",
        f"- Correlation of model-length mean predicted vs. actual changes: {fmt(summary['model_length_mean_pearson'])}.",
        f"- Sign agreement: {fmt(summary['sign_agreement'])}.",
        f"- Positive active source-minus-distractor utility gaps: {fmt(summary['positive_active_utility_fraction'])}.",
        f"- Mean predicted / actual margin change: {summary['mean_first_order_change']:+.3f} / {summary['mean_actual_change']:+.3f}.",
        f"- Mean absolute curvature residual: {summary['mean_abs_curvature_residual']:.3f}.",
        f"- Answer accuracy, natural / source-max: {summary['baseline_accuracy']:.3f} / {summary['source_max_accuracy']:.3f}.",
        "",
        "The audit tests a local sufficient-condition term, not a global linearity assumption; large residuals diagnose downstream curvature along the full swap.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="argmax,flagret")
    parser.add_argument("--pes", default="nope,rope")
    parser.add_argument("--seeds", default="0,1,2,3")
    parser.add_argument("--lengths", default="100,250")
    parser.add_argument("--head-count", type=int, default=8)
    parser.add_argument("--n-eval", type=int, default=32)
    parser.add_argument("--eval-batch", type=int, default=8)
    parser.add_argument("--selection-examples", type=int, default=256)
    parser.add_argument("--selection-seed", type=int, default=4321)
    parser.add_argument("--eval-seed", type=int, default=1234)
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--warmup", type=int, default=400)
    parser.add_argument("--batch", type=int, default=512)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--heads", type=int, default=8)
    parser.add_argument("--mlp", type=int, default=1024)
    parser.add_argument("--checkpoint-dir", default="results/lengthgen/checkpoints")
    parser.add_argument("--outdir", default="results/lengthgen/utility_gap")
    args = parser.parse_args()
    args.tasks = [value for value in args.tasks.split(",") if value]
    args.pes = [value for value in args.pes.split(",") if value]
    args.seeds = [int(value) for value in args.seeds.split(",") if value]
    args.lengths = [int(value) for value in args.lengths.split(",") if value]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    records = []
    models = [(task, pe, seed) for task in args.tasks for pe in args.pes for seed in args.seeds]
    print(f"device={G.DEVICE}; models={len(models)}; lengths={args.lengths}")
    for model_index, (task, pe, seed) in enumerate(models, 1):
        cfg = make_cfg(task, pe, seed, args)
        model, checkpoint = load_model(cfg, args)
        circuit = select_circuit(model, cfg, args.selection_examples, args.selection_seed)
        layer = circuit["selected_layer"]
        masses = np.asarray(circuit["source_mass_by_layer_head"][layer])
        heads = np.argsort(-masses)[: min(args.head_count, cfg.n_heads)].tolist()
        print(f"[{model_index}/{len(models)}] {task}/{pe}/s{seed} layer={layer} heads={heads}", flush=True)
        for length in args.lengths:
            rows = []
            batches = sample_batches(cfg, length, args.n_eval, args.eval_seed, args.eval_batch)
            for x, y, _, aq, tgt in batches:
                rows.extend(evaluate_batch(model, x, y, aq, tgt, layer, heads))
            for example, row in enumerate(rows):
                row.update({
                    "task": task, "pe": pe, "seed": seed, "length": length,
                    "example": example, "layer": layer, "selected_heads": heads,
                    "checkpoint": checkpoint,
                })
            records.extend(rows)
            print(
                f"  L={length} n={len(rows)} pred={np.mean([r['first_order_margin_change'] for r in rows]):+.3f} "
                f"actual={np.mean([r['actual_margin_change'] for r in rows]):+.3f}",
                flush=True,
            )

    summary = summarize(records)
    payload = {"config": vars(args), "summary": summary, "records": records}
    json_path = outdir / "routing_utility_gap_results.json"
    report_path = outdir / "routing_utility_gap_report.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(report_path, summary)
    print(report_path.read_text(encoding="utf-8"))
    print(f"json={json_path}")


if __name__ == "__main__":
    main()
