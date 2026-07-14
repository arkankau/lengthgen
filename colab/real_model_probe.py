"""Does the paper's finding hold in a REAL pretrained LM? (v2 -- redesigned after the v1 probe was
inconclusive: max-over-all-heads saturated, and the raw format gave the model almost no task competence.)

Task: in-context key-value recall in a natural format. Each pair is rendered in token space as
`key : value \n` (the pool tokens carry a leading space, so this decodes to " apple: banana\n"); the query
line is `kq :` and the model should predict the matching value vq. Keys/values are single-token ids, so
accuracy = (argmax next-token == vq). The correct source is the (unique) position of vq.

Two redesigns vs v1:
1. Natural ": \n" format -> a capable base LM actually does short-context recall (real dynamic range).
2. We IDENTIFY the retrieval heads once (top-K by query->source attention at the shortest length, correctness-
   independent), then MEASURE those heads across the length sweep -- instead of max over all 384 head-layers,
   which saturates in a big model. From attention weights alone (no model-specific hooks) we record, at the
   query token: attention-on-source of the retrieval heads, their participation ||a||^2 (= attention-output
   variance up to a constant by Prop 1), and their entropy. (We also keep max-over-all-heads for reference.)

Prediction (results/lengthgen_realmodel_prereg.md): accuracy AND retrieval-head attention-on-source both
fall with length, and within a fixed length attention-on-source predicts correctness better than ||a||^2.

Usage (Colab GPU):
  !python colab/real_model_probe.py --model EleutherAI/pythia-1.4b --lengths 5,10,20,40,80,160 --n 150 \
      --heads 8 --outdir /content/drive/MyDrive/lengthgen_realmodel
  Quick check first:  add  --smoke   (confirm nan_frac=0 AND acc is high at short N)
"""
from __future__ import annotations
import argparse, json, math, os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # Xet CAS backend 401s on unauth Colab; use classic download
import numpy as np
import torch


def single_token_pool(tok, want=1600):
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


def build_example(pool, N, colon, nl, rng):
    picks = rng.choice(len(pool), size=2 * N, replace=False)
    keys = [pool[p] for p in picks[:N]]
    vals = [pool[p] for p in picks[N:2 * N]]
    j = int(rng.integers(0, N))
    ids = []
    for k, v in zip(keys, vals):
        ids += [k] + colon + [v] + nl
    ids += [keys[j]] + colon                              # query line "kq :"
    src = ids.index(vals[j])                              # unique position of the queried value
    return ids, src, vals[j]


@torch.no_grad()
def final_row(model, x):
    """attention FROM the last token to all keys: (L, B, H, S)."""
    out = model(x, output_attentions=True)
    att = torch.stack(out.attentions, 0).float()          # (L, B, H, S, S)
    return att[:, :, :, -1, :], out.logits[:, -1, :]


@torch.no_grad()
def calibrate_heads(model, device, pool, N, colon, nl, K, rng, n_cal=64):
    seqs, srcs = [], []
    for _ in range(n_cal):
        ids, src, _ = build_example(pool, N, colon, nl, rng)
        seqs.append(ids); srcs.append(src)
    x = torch.tensor(seqs, device=device)
    row, _ = final_row(model, x)                          # (L,B,H,S)
    L, B, H, S = row.shape
    score = torch.zeros(L, H)
    for b in range(B):
        score += row[:, b, :, srcs[b]].cpu()              # mean query->source attention per (L,H)
    score /= B
    flat = torch.argsort(score.flatten(), descending=True)[:K]
    heads = [(int(i // H), int(i % H)) for i in flat]
    return heads, score


@torch.no_grad()
def probe_length(model, device, pool, N, n_ex, batch, colon, nl, heads, rng):
    recs = []
    for start in range(0, n_ex, batch):
        B = min(batch, n_ex - start)
        seqs, srcs, vans = [], [], []
        for _ in range(B):
            ids, src, v = build_example(pool, N, colon, nl, rng)
            seqs.append(ids); srcs.append(src); vans.append(v)
        x = torch.tensor(seqs, device=device)
        row, logits = final_row(model, x)                 # (L,B,H,S), (B,V)
        pred = logits.argmax(-1)
        S = row.shape[-1]
        for b in range(B):
            src = srcs[b]
            hv = torch.stack([row[l, b, h, src] for (l, h) in heads])                 # retrieval-head mass on src
            hn = torch.stack([(row[l, b, h, :] ** 2).sum() for (l, h) in heads])      # retrieval-head participation
            he = torch.stack([-(row[l, b, h, :] * (row[l, b, h, :] + 1e-12).log()).sum() / math.log(S)
                              for (l, h) in heads])                                   # retrieval-head entropy
            recs.append({"N": N, "correct": int(pred[b] == vans[b]),
                         "a_js": float(hv.mean()), "normsq": float(hn.mean()), "entropy": float(he.mean()),
                         "a_js_max": float(row[:, b, :, src].max())})
        del row
    return recs


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="EleutherAI/pythia-1.4b")
    ap.add_argument("--lengths", default="5,10,20,40,80,160")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--heads", type=int, default=8, help="number of retrieval heads to identify and measure")
    ap.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"],
                    help="fp16 makes the RETURNED attentions NaN in transformers 5.x; auto uses bf16/fp32.")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    lengths = [int(x) for x in a.lengths.split(",")]
    n_ex = a.n
    if a.smoke:
        lengths = [3, 6, 10]; n_ex = 12
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if a.dtype == "auto":
        dt = torch.bfloat16 if (device == "cuda" and torch.cuda.is_bf16_supported()) else torch.float32
    else:
        dt = {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[a.dtype]
    print(f"device={device} dtype={dt} model={a.model}")
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=dt, attn_implementation="eager").to(device).eval()
    colon = tok.encode(":", add_special_tokens=False)
    nl = tok.encode("\n", add_special_tokens=False)
    pool = single_token_pool(tok, want=max(1600, 3 * max(lengths)))
    print(f"single-token pool: {len(pool)}  colon={colon}  newline={nl}")
    with torch.no_grad():
        r0, _ = final_row(model, torch.tensor([pool[:3]], device=device))
    nanfrac = float(torch.isnan(r0).float().mean())
    print(f"attention diag: layers={r0.shape[0]} heads={r0.shape[2]} nan_frac={nanfrac:.3f}")
    if nanfrac > 0.01:
        raise SystemExit(f"attentions are NaN (frac={nanfrac:.2f}); rerun with --dtype fp32")

    rng = np.random.default_rng(0)
    heads, _ = calibrate_heads(model, device, pool, min(lengths), colon, nl, a.heads, rng)
    print(f"retrieval heads (layer,head) by query->source attention @N={min(lengths)}: {heads}")
    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, "realmodel_results.json")
    recs = []
    for N in lengths:
        if 2 * N > len(pool):
            print(f"[skip N={N}] pool too small"); continue
        r = probe_length(model, device, pool, N, n_ex, a.batch, colon, nl, heads, rng)
        recs += r
        acc = np.mean([x["correct"] for x in r]); aj = np.mean([x["a_js"] for x in r])
        print(f"N={N:4d}  acc={acc:.3f}  retrieval-head a_js={aj:.3f}", flush=True)
        json.dump({"model": a.model, "heads": heads, "records": recs}, open(path, "w"))

    A = np.array([x["a_js"] for x in recs]); C = np.array([x["correct"] for x in recs], float)
    V = np.array([x["normsq"] for x in recs])

    def r(x, y):
        return float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 1e-9 and np.std(y) > 1e-9 else float("nan")
    print(f"\npooled corr(acc, retrieval-head attention-on-source) = {r(A, C):+.3f}")
    print(f"pooled corr(acc, retrieval-head ||a||^2)              = {r(V, C):+.3f}")
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
