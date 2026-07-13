"""Direct causal test: does attention on the correct source CONTROL length-gen accuracy?

We train baseline models, then at eval overwrite the attention distribution at the answer-query position
(the PATCH hook in length_gen_colab.py) to place a chosen mass p on the correct source, holding the trained
weights fixed. At a long test length we run three sweeps, patching the model's own retrieval layer L*
(the layer with the highest baseline attention on the source):

  P      : spread (1-p) over ALL valid keys; sweep p. Accuracy vs FORCED attention-on-source. Here the
           attention-output variance ||a||^2 co-moves with p, so this is the basic "force selection" curve.
  FIXVAR : hold ||a||^2 (hence Var(z) by Prop 1) at a constant C by choosing the spread k; sweep p.
           Accuracy vs a_j* at CONSTANT variance -> the key dissociation.
  FIXP   : hold p fixed, vary ||a||^2 by varying k. Accuracy vs variance at FIXED attention-on-source.

Prediction (results/lengthgen_patch_prereg.md): accuracy rises with a_j* in P and FIXVAR, and is flat vs
variance in FIXP. That is attention selection causing the behavior, with variance not causing it.

Usage (Colab GPU, put this file next to length_gen_colab.py):
  !python patch_experiment.py --tasks argmax,flagret --seeds 0,1,2,3 --outdir /content/drive/MyDrive/lengthgen_patch
"""
from __future__ import annotations
import argparse, json, math, os
import numpy as np
import torch
import length_gen_colab as G   # validated model / tasks / evaluate / PATCH hook

LENGTHS = [100, 250]                      # long test lengths (20x, 50x of l_train=5)
P_GRID = [0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 1.0]
FIXVAR_C = 0.25                            # target ||a||^2 for the constant-variance sweep
FIXVAR_P = [0.05, 0.1, 0.2, 0.3, 0.4, 0.48]
FIXP_P = 0.3
FIXP_K = [2, 4, 8, 16, 32, 64]


def train_baseline(cfg):
    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)
    model = G.build_model(cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay, betas=(0.9, 0.98))

    def lr_at(step):
        if step < cfg.warmup:
            return step / max(1, cfg.warmup)
        p = (step - cfg.warmup) / max(1, cfg.steps - cfg.warmup)
        return 0.5 * (1 + math.cos(math.pi * min(1.0, p)))

    lossfn = torch.nn.CrossEntropyLoss(reduction="none")
    for step in range(cfg.steps + 1):
        model.train()
        for g in opt.param_groups:
            g["lr"] = cfg.lr * lr_at(step)
        x, y, mask, _, _ = G.sample_batch(rng, cfg.batch, 1, cfg.l_train, cfg)
        logits = model(x)
        loss = lossfn(logits.reshape(-1, cfg.vocab), y.reshape(-1)).reshape(y.shape)
        loss = (loss * mask).sum() / mask.sum().clamp_min(1)
        opt.zero_grad(); loss.backward(); opt.step()
    return model


def patched_point(model, cfg, L, layer, p, k, n_eval=256):
    """Eval at length L with attention at the query patched to (p on source, rest over k valid keys)."""
    G.PATCH = {"layer": layer, "p": p, "k": k}
    row = G.evaluate(model, cfg, np.random.default_rng(1234), [L], n_eval=n_eval)[0]
    G.PATCH = None
    normsq = None if k is None else p * p + (1 - p) ** 2 / max(1, k)
    zv = getattr(model.blocks[layer], "z_aq_var", None)
    return {"p": p, "k": k, "normsq": normsq,
            "a_js": round(row["attn_tgt"][layer], 5),                       # achieved mass on source (~p)
            "zvar": round(zv, 5) if zv is not None else None,              # measured Var(z) at the query
            "em": round(row["em"], 5), "tok": round(row["tok"], 5)}


def run_model(task, pe, seed, steps):
    tk = G.TASKS[task]
    cfg = G.Cfg(task=task, pe=pe, post_attn_ln=False, seed=seed, steps=steps, attn_scale="none",
                n_layers=4, d_model=256, n_heads=8, d_mlp=1024, batch=512, warmup=400,
                vocab=tk["vocab"], pad=tk["pad"])
    print(f"[train] {task} {pe} seed={seed} ({steps} steps)", flush=True)
    model = train_baseline(cfg)
    out = {"cfg": {"task": task, "pe": pe, "seed": seed, "n_layers": 4, "d_model": 256},
           "Lstar": {}, "baseline": {}, "sweeps": {}}
    for L in LENGTHS:
        G.PATCH = None
        base = G.evaluate(model, cfg, np.random.default_rng(1234), [L], n_eval=256)[0]
        Lstar = int(np.argmax(base["attn_tgt"]))                          # the model's retrieval layer
        out["Lstar"][str(L)] = Lstar
        out["baseline"][str(L)] = {"em": round(base["em"], 5), "tok": round(base["tok"], 5),
                                   "attn_tgt": [round(x, 5) for x in base["attn_tgt"]]}
        sw = {"P": [], "FIXVAR": [], "FIXP": []}
        for p in P_GRID:
            sw["P"].append(patched_point(model, cfg, L, Lstar, p, None))
        for p in FIXVAR_P:
            k = max(1, round((1 - p) ** 2 / max(1e-6, FIXVAR_C - p * p)))
            sw["FIXVAR"].append(patched_point(model, cfg, L, Lstar, p, k))
        for k in FIXP_K:
            sw["FIXP"].append(patched_point(model, cfg, L, Lstar, FIXP_P, k))
        out["sweeps"][str(L)] = sw
        print(f"  L={L} Lstar={Lstar} baseline tok={base['tok']:.3f} "
              f"| patch p=1.0 tok={sw['P'][-1]['tok']:.3f} p=0.0 tok={sw['P'][0]['tok']:.3f}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="argmax,flagret")
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()
    if not hasattr(G, "_apply_attn_patch") or not hasattr(G, "PATCH"):
        raise SystemExit("length_gen_colab.py is OUT OF DATE: it lacks the PATCH hook. Re-upload the "
                         "updated length_gen_colab.py (it must contain `_apply_attn_patch` and `PATCH = None`) "
                         "next to this script, then rerun.")
    os.makedirs(args.outdir, exist_ok=True)
    path = os.path.join(args.outdir, "patch_results.json")
    print(f"device = {G.DEVICE}")
    results = json.load(open(path)) if os.path.exists(path) else []
    done = {(r["cfg"]["task"], r["cfg"]["pe"], r["cfg"]["seed"]) for r in results}
    plan = [(t, pe, s) for t in args.tasks.split(",") for pe in ("nope", "rope")
            for s in [int(x) for x in args.seeds.split(",")]]
    for i, (t, pe, s) in enumerate(plan, 1):
        if (t, pe, s) in done:
            print(f"[skip {i}/{len(plan)}] {t} {pe} seed={s} (done)"); continue
        rec = run_model(t, pe, s, args.steps)
        results.append(rec)
        print("RESULTJSON " + json.dumps(rec), flush=True)
        json.dump(results, open(path, "w"), indent=2)
        print(f"[progress {i}/{len(plan)}] saved ({len(results)} models)", flush=True)
    print(f"\nsaved: {path}")


if __name__ == "__main__":
    main()
