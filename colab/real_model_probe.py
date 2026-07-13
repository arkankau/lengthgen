"""Does the paper's finding hold in a REAL pretrained LM? (generalization beyond the toy transformers)

Task: in-context key-value recall. Sequence  [k1 v1 k2 v2 ... kN vN  kq]  (kq repeats one ki); the model
should predict the matching value vq. Keys/values are single-token ids, so accuracy = (argmax next-token
== vq). The correct source is the known position of vq. We vary the number of pairs N (the context length)
and, at the query token, measure from the attention weights alone (attn_implementation='eager'):
  - attention on the correct source  a_j* = max over layers,heads of attn(query -> vq position)
  - the variance candidate = attention participation  ||a||^2 = mean over layers,heads of sum_s a_s^2,
    which equals the attention-output variance up to a constant by Proposition 1 (no model-specific hooks).
  - attention entropy (a second dispersion summary).

Prediction (results/lengthgen_realmodel_prereg.md): across lengths and examples, accuracy is predicted by
attention-on-source, and both fall as N grows; attention-on-source predicts accuracy better than the
||a||^2 variance candidate. That generalizes "selection over scale" from the toy models to a real LM.

Usage (Colab GPU):
  !python colab/real_model_probe.py --model EleutherAI/pythia-1.4b --lengths 5,10,20,40,80,160 --n 150 \
      --outdir /content/drive/MyDrive/lengthgen_realmodel
  Quick check first:  add  --smoke
"""
from __future__ import annotations
import argparse, json, math, os
import numpy as np
import torch


def single_token_pool(tok, want=1200):
    """ids whose text is ' word' (leading space, alphabetic) and round-trips to a single token."""
    pool = []
    for i in range(tok.vocab_size):
        s = tok.decode([i])
        if len(s) >= 4 and s[0] == " " and s[1:].isalpha() and s.islower():
            if tok.encode(s, add_special_tokens=False) == [i]:
                pool.append(i)
        if len(pool) >= want:
            break
    if len(pool) < 40:
        raise RuntimeError("could not build a single-token pool for this tokenizer")
    return pool


@torch.no_grad()
def probe_length(model, device, pool, N, n_ex, batch, rng):
    recs = []
    S = 2 * N + 1
    for start in range(0, n_ex, batch):
        B = min(batch, n_ex - start)
        seqs, srcs, vans = [], [], []
        for _ in range(B):
            picks = rng.choice(len(pool), size=2 * N, replace=False)
            keys = [pool[p] for p in picks[:N]]
            vals = [pool[p] for p in picks[N:2 * N]]
            j = int(rng.integers(0, N))                    # which pair is queried
            ids = []
            for kk, vv in zip(keys, vals):
                ids += [kk, vv]
            ids.append(keys[j])                            # query key at position 2N
            seqs.append(ids); srcs.append(2 * j + 1); vans.append(vals[j])
        x = torch.tensor(seqs, device=device)
        out = model(x, output_attentions=True)
        logits = out.logits[:, -1, :]                       # next-token dist at the query position
        pred = logits.argmax(-1)
        att = torch.stack(out.attentions, 0).float()        # (L, B, H, S, S)
        row = att[:, :, :, -1, :]                           # (L, B, H, S): attention FROM the query token
        # mass on the correct source: per example, max over layers,heads (small B -> explicit, no index ambiguity)
        a_js = torch.stack([row[:, b, :, srcs[b]].max() for b in range(B)])           # (B,)
        normsq = (row ** 2).sum(-1).mean(dim=(0, 2))        # (B,) mean participation = variance proxy
        ent = (-(row * (row + 1e-12).log()).sum(-1) / math.log(S)).mean(dim=(0, 2))  # (B,) mean norm. entropy
        van = torch.tensor(vans, device=device)
        correct = (pred == van)
        for b in range(B):
            recs.append({"N": N, "correct": int(correct[b]), "a_js": float(a_js[b]),
                         "normsq": float(normsq[b]), "entropy": float(ent[b])})
        del out, att, row
    return recs


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="EleutherAI/pythia-1.4b")
    ap.add_argument("--lengths", default="5,10,20,40,80,160")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"],
                    help="fp16 makes the RETURNED attentions overflow to NaN in transformers 5.x; "
                         "default 'auto' uses bf16 if supported else fp32 (never fp16).")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    lengths = [int(x) for x in a.lengths.split(",")]
    n_ex = a.n
    if a.smoke:
        lengths = [3, 6, 10]; n_ex = 8
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if a.dtype == "auto":
        dt = torch.bfloat16 if (device == "cuda" and torch.cuda.is_bf16_supported()) else torch.float32
    else:
        dt = {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[a.dtype]
    print(f"device={device} dtype={dt} model={a.model}")
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=dt, attn_implementation="eager").to(device).eval()
    pool = single_token_pool(tok, want=max(1200, 3 * max(lengths)))
    print(f"single-token pool: {len(pool)}")
    # diagnostic: confirm attentions are returned and not NaN (fp16 overflows them in transformers 5.x)
    with torch.no_grad():
        t = model(torch.tensor([[pool[0], pool[1], pool[0]]], device=device), output_attentions=True)
    if t.attentions is None:
        raise SystemExit("model returned no attentions; update transformers or set attn_implementation=eager")
    diag = torch.stack(t.attentions, 0).float()
    nanfrac = float(torch.isnan(diag).float().mean())
    print(f"attention diag: layers={len(t.attentions)} shape={tuple(t.attentions[0].shape)} nan_frac={nanfrac:.3f}")
    if nanfrac > 0.01:
        raise SystemExit(f"attentions are NaN (frac={nanfrac:.2f}); rerun with --dtype fp32")
    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, "realmodel_results.json")
    rng = np.random.default_rng(0)
    recs = []
    for N in lengths:
        if 2 * N > len(pool):
            print(f"[skip N={N}] pool too small"); continue
        r = probe_length(model, device, pool, N, n_ex, a.batch, rng)
        recs += r
        acc = np.mean([x["correct"] for x in r]); aj = np.mean([x["a_js"] for x in r])
        print(f"N={N:4d}  acc={acc:.3f}  mean a_js={aj:.3f}", flush=True)
        json.dump({"model": a.model, "records": recs}, open(path, "w"))
    # quick pooled correlations
    A = np.array([x["a_js"] for x in recs]); C = np.array([x["correct"] for x in recs], float)
    V = np.array([x["normsq"] for x in recs]); E = np.array([x["entropy"] for x in recs])
    def r(x, y):
        return float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 1e-9 and np.std(y) > 1e-9 else float("nan")
    print(f"\npooled corr(acc, attention-on-source) = {r(A, C):+.3f}")
    print(f"pooled corr(acc, ||a||^2 variance proxy) = {r(V, C):+.3f}")
    print(f"pooled corr(acc, -entropy)               = {r(-E, C):+.3f}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
