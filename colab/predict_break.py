"""Direction B: predict the length-generalization break point from the attention logit gap.

Proposition 2 says attention on the correct source, a_j*, stays concentrated only if the attention logit gap
grows about like log n. We make this predictive. At the answer query the softmax over keys gives

    a_j* = sigmoid( Delta(n) ),   Delta(n) = z_src - logsumexp_{k != src} z_k,

where z are the effective attention logits (post any sharpening) at the retrieval head. Writing the per-key
margin g(n) = z_src - mean_k z_k, and using logsumexp ~ log(n-1) + mean, gives Delta(n) ~ g(n) - log(n-1), so
the break (a_j* -> 0.5, Delta -> 0) is predicted at

    n*  ~  1 + exp(g),      more generally  log n* = a/b  from a linear fit Delta(n) = a - b log n.

We FIT Delta(n) on SHORT lengths only (in and just past the training regime), extrapolate to predict n*, and
compare to the OBSERVED accuracy break (where exact-match crosses 0.5). If the sharpening intervention makes
Delta stop declining, the predicted n* moves far out, matching its better generalization.

For each config we train a small transformer, identify the retrieval head (max a_j* at the shortest length,
correctness-independent), and record Delta(n), g(n), predicted a_j*, and observed accuracy across lengths.

Usage (Colab GPU):
  !python colab/predict_break.py --tasks argmax,flagret --scales none,loglen --seeds 0,1 \
      --steps 12000 --outdir /content/drive/MyDrive/lengthgen_break
  Quick check first:  add  --smoke
"""
from __future__ import annotations
import argparse, json, math, os
import numpy as np
import torch
import length_gen_colab as G


def train(cfg, steps, log=print):
    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)
    model = G.build_model(cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay, betas=(0.9, 0.98))
    lossfn = torch.nn.CrossEntropyLoss(reduction="none")
    for step in range(steps + 1):
        model.train()
        if step < cfg.warmup:
            lr = step / max(1, cfg.warmup)
        else:
            p = (step - cfg.warmup) / max(1, steps - cfg.warmup)
            lr = 0.5 * (1 + math.cos(math.pi * min(1.0, p)))
        for gp in opt.param_groups:
            gp["lr"] = cfg.lr * lr
        x, y, mask, _, _ = G.sample_batch(rng, cfg.batch, 1, cfg.l_train, cfg)
        logits = model(x)
        loss = lossfn(logits.reshape(-1, cfg.vocab), y.reshape(-1)).reshape(y.shape)
        loss = (loss * mask).sum() / mask.sum().clamp_min(1)
        opt.zero_grad(); loss.backward(); opt.step()
        if step % max(1, steps // 5) == 0:
            log(f"  step {step:6d} loss {loss.item():.3f}")
    return model


def _delta_g_for_head(S, aq, tgt, l, h):
    """per-example Delta and margin g at layer l head h, from captured logits S[l] (b,heads,t)."""
    b = S[l].shape[0]
    ds, gs, ok = [], [], []
    for i in range(b):
        si = int(tgt[i]); qi = int(aq[i])
        if si < 0 or qi < 1:
            continue
        row = S[l][i, h, :qi + 1].float()                 # causal keys 0..qi
        z_src = row[si]
        mask = torch.ones_like(row, dtype=torch.bool); mask[si] = False
        others = row[mask]
        if others.numel() == 0:
            continue
        lse = torch.logsumexp(others, 0)
        ds.append(float(z_src - lse))                     # Delta ; a_j* = sigmoid(Delta)
        gs.append(float(z_src - others.mean()))           # per-key margin
        ok.append(i)
    return np.array(ds), np.array(gs), ok


@torch.no_grad()
def measure(model, cfg, lengths, rng, nb=128):
    model.eval()
    # pass 1: pick the retrieval head as argmax mean a_j* at the shortest length
    x, y, mask, aq, tgt = G.sample_batch(rng, nb, lengths[0], lengths[0], cfg)
    model(x, aq, tgt)
    S = [blk.z_aq_scores for blk in model.blocks]          # list of (b,heads,t)
    Ln, H = len(S), S[0].shape[1]
    best, best_a = (0, 0), -1.0
    for l in range(Ln):
        for h in range(H):
            ds, _, _ = _delta_g_for_head(S, aq, tgt, l, h)
            a = float(np.mean(1 / (1 + np.exp(-ds)))) if ds.size else -1
            if a > best_a:
                best_a, best = a, (l, h)
    l_r, h_r = best
    # pass 2: Delta(n), g(n), predicted a, observed accuracy at each length
    out = []
    for L in lengths:
        x, y, mask, aq, tgt = G.sample_batch(rng, nb, L, L, cfg)
        pred = model(x, aq, tgt).argmax(-1)
        S = [blk.z_aq_scores for blk in model.blocks]
        ds, gs, ok = _delta_g_for_head(S, aq, tgt, l_r, h_r)
        m = mask.bool()
        em = []
        for i in range(x.shape[0]):
            mi = m[i]
            if mi.sum() == 0:
                continue
            em.append(float((pred[i][mi] == y[i][mi]).all()))
        nkeys = float(np.mean([int(aq[i]) + 1 for i in range(len(aq)) if int(tgt[i]) >= 0]))
        out.append({"L": L, "nkeys": nkeys,
                    "delta": float(np.mean(ds)) if ds.size else float("nan"),
                    "g": float(np.mean(gs)) if gs.size else float("nan"),
                    "a_pred": float(np.mean(1 / (1 + np.exp(-ds)))) if ds.size else float("nan"),
                    "em": float(np.mean(em)) if em else float("nan")})
    return {"retrieval_layer": l_r, "retrieval_head": h_r}, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="argmax,flagret")
    ap.add_argument("--pes", default="nope,rope")
    ap.add_argument("--scales", default="none,loglen")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--steps", type=int, default=12000)
    ap.add_argument("--l-train", type=int, default=5)
    ap.add_argument("--lengths", default="")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    tasks = a.tasks.split(","); pes = a.pes.split(","); scales = a.scales.split(",")
    seeds = [int(s) for s in a.seeds.split(",")]
    steps = 300 if a.smoke else a.steps
    if a.smoke:
        tasks, pes, scales, seeds = ["argmax"], ["nope"], ["none"], [0]
    L = a.l_train
    if a.lengths:
        lengths = [int(x) for x in a.lengths.split(",")]
    else:
        lengths = sorted(set([L, 2 * L, 3 * L, 4 * L, 6 * L, 10 * L, 15 * L, 25 * L, 35 * L, 50 * L]))
    if a.smoke:
        lengths = [L, 2 * L, 4 * L, 8 * L]
    print(f"device={G.DEVICE} steps={steps} lengths={lengths}")
    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, "break_results.json")
    results = []
    for task in tasks:
        tk = G.TASKS[task]
        for pe in pes:
            for scale in scales:
                for seed in seeds:
                    cfg = G.Cfg(task=task, pe=pe, seed=seed, steps=steps, l_train=L,
                                attn_scale=scale, vocab=tk["vocab"], pad=tk["pad"])
                    if a.smoke:  # tiny model so the plumbing check runs on CPU in seconds
                        cfg.n_layers, cfg.d_model, cfg.n_heads, cfg.d_mlp, cfg.batch = 2, 64, 4, 128, 64
                    tag = f"task={task} pe={pe} scale={scale} seed={seed}"
                    print(f"\n=== {tag} ===", flush=True)
                    model = train(cfg, steps)
                    head, series = measure(model, cfg, lengths, np.random.default_rng(999))
                    results.append({"cfg": {"task": task, "pe": pe, "scale": scale, "seed": seed,
                                    "l_train": L, "steps": steps}, **head, "series": series})
                    br = next((r["L"] for r in series if r["em"] < 0.5), None)
                    print(f"  retrieval=({head['retrieval_layer']},{head['retrieval_head']})  "
                          f"observed break L(em<0.5)={br}", flush=True)
                    for r in series:
                        print(f"    L={r['L']:4d} nkeys={r['nkeys']:6.1f} delta={r['delta']:+.2f} "
                              f"g={r['g']:+.2f} a_pred={r['a_pred']:.2f} em={r['em']:.2f}")
                    json.dump(results, open(path, "w"))
    print(f"\nsaved: {path}")


if __name__ == "__main__":
    main()
