"""Needle-in-a-haystack retrieval in REAL text: the account on a non-synthetic, benchmark-format task.

The paper's real-model evidence so far uses a synthetic key-value list. This probe keeps the SAME measurements
but replaces the context with genuine natural language: the haystack is real Wikipedia prose (wikitext-2-raw)
and the needle is a natural sentence inserted at a random depth. This is the standard long-context retrieval
benchmark format (needle-in-a-haystack), so it addresses both "synthetic task" and "no recognized benchmark".

Per example, at the query token, we record everything both analyses need:
  a_js    : retrieval-head attention on the correct source (the needle's answer token)
  normsq  : retrieval-head ||a||^2 (attention-output variance proxy, Prop 1)
  entropy : retrieval-head attention entropy
  vrank   : best logit-lens rank of the answer in the residual (the readout locus, as in decouple_probe)
  correct : did the model output the answer
  depth   : needle position as a fraction of context (standard NIAH axis)
The output JSON is field-compatible with BOTH scripts/analyze_real_model.py and scripts/analyze_decouple.py.

The needle is built in token space so the answer is exactly one token at a known position:
  "\\nThe special passcode for <key> is <value>.\\n"   query: "\\nThe special passcode for <key> is"
Key and value are single-token words that do NOT occur anywhere in that example's haystack, so the source
position is unambiguous.

Usage:
  python colab/niah_probe.py --model gpt2-medium --lengths 128,256,512,900 --n 120 --outdir ../results/.../niah
"""
from __future__ import annotations
import argparse, json, math, os
import numpy as np
import torch
import real_model_probe as R
from decouple_probe import get_norm_and_head

NEEDLE_PRE = "\nThe special passcode for"
NEEDLE_MID = " is"
NEEDLE_END = ".\n"


def load_wikitext_tokens(tok, want_tokens=400000):
    """A long stream of REAL Wikipedia text, tokenized once."""
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    p = hf_hub_download("Salesforce/wikitext",
                        filename="wikitext-2-raw-v1/train-00000-of-00001.parquet", repo_type="dataset")
    paras = [x for x in pq.read_table(p).column("text").to_pylist() if len(x.strip()) > 300]
    ids = []
    for para in paras:
        ids.extend(tok.encode(para, add_special_tokens=False))
        if len(ids) >= want_tokens:
            break
    return ids


def build_niah(stream, pool, T, pre, mid, end, rng, tries=20):
    """haystack of exactly T real-text tokens + needle at a random depth + query. Returns (ids, src, val)."""
    start = int(rng.integers(0, max(1, len(stream) - T - 1)))
    hay = stream[start:start + T]
    hayset = set(hay)
    for _ in range(tries):                      # key/value must not occur in the haystack
        k, v = (pool[int(i)] for i in rng.choice(len(pool), size=2, replace=False))
        if k not in hayset and v not in hayset and k != v:
            break
    else:
        return None
    needle = pre + [k] + mid + [v] + end
    cut = int(rng.integers(0, T + 1))           # random depth
    ids = hay[:cut] + needle + hay[cut:] + pre + [k] + mid
    src = cut + len(pre) + 1 + len(mid)         # position of the answer token v
    assert ids[src] == v
    return ids, src, v


@torch.no_grad()
def calibrate(model, device, stream, pool, T, pre, mid, end, K, rng, n_cal=48, batch=8):
    """retrieval heads = top-K by mean query->source attention at the SHORTEST length (correctness-blind)."""
    score = None
    seen = 0
    for s in range(0, n_cal, batch):
        ex = [build_niah(stream, pool, T, pre, mid, end, rng) for _ in range(min(batch, n_cal - s))]
        ex = [e for e in ex if e]
        if not ex:
            continue
        x = torch.tensor([e[0] for e in ex], device=device)
        row, _ = R.final_row(model, x)                      # (L,B,H,S)
        acc = torch.stack([row[:, b, :, ex[b][1]] for b in range(len(ex))]).sum(0).cpu()   # (L,H)
        score = acc if score is None else score + acc
        seen += len(ex)
        del row
    score /= max(1, seen)
    H = score.shape[1]
    flat = torch.argsort(score.flatten(), descending=True)[:K]
    return [(int(i // H), int(i % H)) for i in flat]


@torch.no_grad()
def probe(model, device, stream, pool, T, n_ex, batch, pre, mid, end, heads, norm, head, rng):
    recs = []
    for s in range(0, n_ex, batch):
        ex = [build_niah(stream, pool, T, pre, mid, end, rng) for _ in range(min(batch, n_ex - s))]
        ex = [e for e in ex if e]
        if not ex:
            continue
        x = torch.tensor([e[0] for e in ex], device=device)
        out = model(x, output_attentions=True, output_hidden_states=True)
        row = torch.stack([a[:, :, -1, :] for a in out.attentions], 0).float()   # (L,B,H,S)
        pred = out.logits[:, -1, :].argmax(-1)
        van = torch.tensor([e[2] for e in ex], device=device)
        B, S = len(ex), row.shape[-1]
        best = torch.full((B,), 10 ** 9, device=device)
        for h in out.hidden_states:
            q = h[:, -1, :]
            q = norm(q) if norm is not None else q
            lg = head(q)
            best = torch.minimum(best, (lg > lg.gather(1, van.unsqueeze(1))).sum(1))
        for b in range(B):
            src = ex[b][1]
            hv = torch.stack([row[l, b, hh, src] for (l, hh) in heads])
            hn = torch.stack([(row[l, b, hh, :] ** 2).sum() for (l, hh) in heads])
            he = torch.stack([-(row[l, b, hh, :] * (row[l, b, hh, :] + 1e-12).log()).sum() / math.log(S)
                              for (l, hh) in heads])
            recs.append({"N": T, "correct": int(pred[b] == van[b]),
                         "a_js": float(hv.mean()), "normsq": float(hn.mean()), "entropy": float(he.mean()),
                         "a_js_max": float(row[:, b, :, src].max()),
                         "vrank": int(best[b]), "depth": round(src / len(ex[b][0]), 3)})
        del out, row
    return recs


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt2-medium")
    ap.add_argument("--lengths", default="128,256,512,900", help="haystack size in REAL-TEXT tokens")
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--heads", type=int, default=8)
    ap.add_argument("--dtype", default="auto", choices=["auto", "fp32", "bf16"])
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    lengths = [int(x) for x in a.lengths.split(",")]
    n_ex = a.n
    if a.smoke:
        lengths, n_ex = [64, 128], 12
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dt = (torch.bfloat16 if (device == "cuda" and torch.cuda.is_bf16_supported()) else torch.float32) \
        if a.dtype == "auto" else {"fp32": torch.float32, "bf16": torch.bfloat16}[a.dtype]
    print(f"device={device} dtype={dt} model={a.model}", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=dt, attn_implementation="eager").to(device).eval()
    norm, head = get_norm_and_head(model)
    maxpos = getattr(model.config, "max_position_embeddings", None) or 10 ** 6
    pre = tok.encode(NEEDLE_PRE, add_special_tokens=False)
    mid = tok.encode(NEEDLE_MID, add_special_tokens=False)
    end = tok.encode(NEEDLE_END, add_special_tokens=False)
    overhead = 2 * len(pre) + len(mid) * 2 + len(end) + 4
    lengths = [T for T in lengths if T + overhead < maxpos]
    print(f"max_positions={maxpos} lengths={lengths} norm_found={norm is not None}", flush=True)
    pool = R.single_token_pool(tok, want=2000)
    stream = load_wikitext_tokens(tok)
    print(f"real-text stream: {len(stream)} tokens; pool {len(pool)}", flush=True)
    rng = np.random.default_rng(0)
    heads = calibrate(model, device, stream, pool, lengths[0], pre, mid, end, a.heads, rng, batch=a.batch)
    print(f"retrieval heads: {heads}", flush=True)
    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, "niah_results.json")
    recs = []
    for T in lengths:
        b = a.batch if T <= 512 else max(2, a.batch // 2)
        r = probe(model, device, stream, pool, T, n_ex, b, pre, mid, end, heads, norm, head, rng)
        recs += r
        acc = float(np.mean([x["correct"] for x in r]))
        aj = float(np.mean([x["a_js"] for x in r]))
        fails = [x for x in r if not x["correct"]]
        vp = float(np.mean([x["vrank"] < 10 for x in fails])) if fails else float("nan")
        print(f"T={T:5d}  acc={acc:.3f}  a_js={aj:.3f}  value-in-residual|fail={vp:.2f}", flush=True)
        json.dump({"model": a.model, "heads": heads, "task": "niah-wikitext", "records": recs},
                  open(path, "w"))
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
