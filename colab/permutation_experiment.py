"""Exact attention-permutation test for task-conditioned source selection.

For a trained retrieval model, evaluate the same examples under four conditions at the
model's baseline retrieval layer:

  baseline            unchanged attention
  source_max          swap the source weight with the row maximum in every head
  source_min          swap the source weight with the row minimum in every head
  distractor_control  swap the largest and smallest non-source weights

The three interventions are permutations of the model's own attention weights. They
therefore preserve entropy, all attention norms, the maximum weight, participation
ratio, and the complete sorted distribution. Only source_max/source_min change which
weight is assigned to the task-relevant position.

Usage:
  python permutation_experiment.py --tasks argmax --pes nope --seeds 0 --steps 4000
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import torch

import length_gen_colab as G


MODES = ("source_max", "source_min", "distractor_control")


def train_baseline(cfg):
    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)
    model = G.build_model(cfg)
    opt = torch.optim.AdamW(
        model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay, betas=(0.9, 0.98)
    )
    lossfn = torch.nn.CrossEntropyLoss(reduction="none")

    def lr_at(step):
        if step < cfg.warmup:
            return step / max(1, cfg.warmup)
        progress = (step - cfg.warmup) / max(1, cfg.steps - cfg.warmup)
        return 0.5 * (1 + math.cos(math.pi * min(1.0, progress)))

    for step in range(cfg.steps + 1):
        model.train()
        for group in opt.param_groups:
            group["lr"] = cfg.lr * lr_at(step)
        x, y, mask, _, _ = G.sample_batch(rng, cfg.batch, 1, cfg.l_train, cfg)
        logits = model(x)
        loss = lossfn(logits.reshape(-1, cfg.vocab), y.reshape(-1)).reshape(y.shape)
        loss = (loss * mask).sum() / mask.sum().clamp_min(1)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step and step % max(1, cfg.steps // 4) == 0:
            print(f"    step {step}/{cfg.steps} loss={float(loss.detach()):.4f}", flush=True)
    return model


def evaluate_condition(model, cfg, length, layer, mode, n_eval, eval_seed):
    if mode == "baseline":
        G.PATCH = None
    else:
        G.PATCH = {"layer": layer, "mode": mode, "diagnostics": {}}
    row = G.evaluate(
        model, cfg, np.random.default_rng(eval_seed), [length], n_eval=n_eval
    )[0]
    diagnostics = {} if G.PATCH is None else dict(G.PATCH["diagnostics"])
    zvar = model.blocks[layer].z_aq_var
    G.PATCH = None
    return {
        "mode": mode,
        "em": round(row["em"], 6),
        "tok": round(row["tok"], 6),
        "source_mass": round(row["attn_tgt"][layer], 6),
        "entropy": round(row["attn_ent"][layer], 8),
        "max_weight": round(row["attn_max"][layer], 8),
        "attention_output_var": round(float(zvar), 8),
        "invariant_max_abs_error": {
            key: float(value) for key, value in diagnostics.items()
        },
    }


def run_model(task, pe, seed, args):
    task_cfg = G.TASKS[task]
    cfg = G.Cfg(
        task=task,
        pe=pe,
        post_attn_ln=False,
        seed=seed,
        steps=args.steps,
        attn_scale="none",
        n_layers=args.layers,
        d_model=args.width,
        n_heads=args.heads,
        d_mlp=args.mlp,
        batch=args.batch,
        warmup=min(args.warmup, max(1, args.steps // 4)),
        vocab=task_cfg["vocab"],
        pad=task_cfg["pad"],
    )
    checkpoint_dir = args.checkpoint_dir or os.path.join(args.outdir, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_name = (
        f"{task}_{pe}_s{seed}_{args.layers}L_{args.width}d_{args.heads}h_"
        f"b{args.batch}_steps{args.steps}.pt"
    )
    checkpoint_path = os.path.join(checkpoint_dir, checkpoint_name)
    if os.path.exists(checkpoint_path):
        print(f"[load] {checkpoint_path}", flush=True)
        model = G.build_model(cfg)
        model.load_state_dict(torch.load(checkpoint_path, map_location=G.DEVICE, weights_only=True))
    else:
        print(
            f"[train] task={task} pe={pe} seed={seed} steps={args.steps} "
            f"model={args.layers}L/{args.width}d/{args.heads}h batch={args.batch}",
            flush=True,
        )
        model = train_baseline(cfg)
        torch.save(model.state_dict(), checkpoint_path)
        print(f"[checkpoint] {checkpoint_path}", flush=True)
    train_row = G.evaluate(
        model, cfg, np.random.default_rng(args.eval_seed), [cfg.l_train], n_eval=args.n_eval
    )[0]
    result = {
        "cfg": {
            "task": task,
            "pe": pe,
            "seed": seed,
            "steps": args.steps,
            "layers": args.layers,
            "width": args.width,
            "heads": args.heads,
            "batch": args.batch,
        },
        "train_length": {
            "length": cfg.l_train,
            "em": round(train_row["em"], 6),
            "tok": round(train_row["tok"], 6),
        },
        "lengths": {},
    }
    for length in args.lengths:
        baseline_probe = G.evaluate(
            model, cfg, np.random.default_rng(args.eval_seed), [length], n_eval=args.n_eval
        )[0]
        layer = int(np.argmax(baseline_probe["attn_tgt"]))
        conditions = [
            evaluate_condition(
                model, cfg, length, layer, mode, args.n_eval, args.eval_seed
            )
            for mode in ("baseline",) + MODES
        ]
        result["lengths"][str(length)] = {
            "retrieval_layer": layer,
            "conditions": conditions,
        }
        by_mode = {row["mode"]: row for row in conditions}
        print(
            f"  L={length} layer={layer} "
            f"source[min/base/max]={by_mode['source_min']['source_mass']:.4f}/"
            f"{by_mode['baseline']['source_mass']:.4f}/"
            f"{by_mode['source_max']['source_mass']:.4f} "
            f"tok[min/base/max]={by_mode['source_min']['tok']:.3f}/"
            f"{by_mode['baseline']['tok']:.3f}/"
            f"{by_mode['source_max']['tok']:.3f}",
            flush=True,
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="argmax,flagret")
    parser.add_argument("--pes", default="nope,rope")
    parser.add_argument("--seeds", default="0,1,2,3")
    parser.add_argument("--lengths", default="100,250")
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--warmup", type=int, default=400)
    parser.add_argument("--batch", type=int, default=512)
    parser.add_argument("--n-eval", type=int, default=256)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--heads", type=int, default=8)
    parser.add_argument("--mlp", type=int, default=1024)
    parser.add_argument("--eval-seed", type=int, default=1234)
    parser.add_argument("--outdir", default=".")
    parser.add_argument("--checkpoint-dir", default=None)
    args = parser.parse_args()
    args.tasks = [value for value in args.tasks.split(",") if value]
    args.pes = [value for value in args.pes.split(",") if value]
    args.seeds = [int(value) for value in args.seeds.split(",") if value]
    args.lengths = [int(value) for value in args.lengths.split(",") if value]

    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "permutation_results.json")
    results = json.load(open(path)) if os.path.exists(path) else []
    done = {
        (
            row["cfg"]["task"], row["cfg"]["pe"], row["cfg"]["seed"],
            row["cfg"]["steps"], row["cfg"]["layers"], row["cfg"]["width"],
            row["cfg"]["heads"], row["cfg"]["batch"],
            tuple(sorted(int(length) for length in row["lengths"])),
        )
        for row in results
    }
    plan = [
        (task, pe, seed)
        for task in args.tasks
        for pe in args.pes
        for seed in args.seeds
    ]
    print(f"device={G.DEVICE}; models={len(plan)}; output={path}")
    for index, (task, pe, seed) in enumerate(plan, 1):
        key = (
            task, pe, seed, args.steps, args.layers, args.width, args.heads,
            args.batch, tuple(sorted(args.lengths)),
        )
        if key in done:
            print(f"[skip {index}/{len(plan)}] {key}")
            continue
        result = run_model(task, pe, seed, args)
        results.append(result)
        with open(path, "w") as handle:
            json.dump(results, handle, indent=2)
        print(f"[saved {index}/{len(plan)}] {key}", flush=True)
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
