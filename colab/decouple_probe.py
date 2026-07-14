"""Decouple attention-failure from readout-failure in a real LM (direction A).

Our real-model probe showed accuracy and attention-on-source co-decline, but attention on the source is
still non-trivial where accuracy is near the floor -- so is length-gen failure on recall *only* attention
dispersion, or is there a second locus (the value is not copied, or is copied then dropped)? We decompose
the failure without any attention surgery, using a logit lens on the residual stream.

For each in-context key-value recall example (same task as real_model_probe.py) we record at the query
token:
  - a_js   : retrieval-head attention on the correct source (did attention reach the source?)
  - vrank  : the BEST (min over layers) logit-lens rank of the correct value vq in the residual
             (was the value ever retrieved INTO the residual stream?)   -- via unembed(final_norm(h_L))
  - correct: was vq actually output?

Then, among the FAILURES at each length, we split them into three loci (thresholds chosen in analysis):
  attention-limited : a_js low                       (never reached the source)
  copy-limited      : a_js high but vrank high       (reached it, but the value was not written to residual)
  readout-limited   : vrank low but still wrong       (value was present, later layers dropped it)

Usage (Colab GPU):
  !python colab/decouple_probe.py --model EleutherAI/pythia-1.4b --lengths 10,20,40,80,160 --n 150 \
      --outdir /content/drive/MyDrive/lengthgen_decouple
"""
from __future__ import annotations
import argparse, json, os
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # Xet CAS backend 401s on unauth Colab; use classic download
import numpy as np
import torch
import real_model_probe as R   # reuse pool / task / head calibration / attention row


def get_norm_and_head(model):
    head = model.get_output_embeddings()
    for path in ("gpt_neox.final_layer_norm", "transformer.ln_f", "model.norm", "model.final_layernorm",
                 "model.transformer.ln_f"):
        m, ok = model, True
        for p in path.split("."):
            if hasattr(m, p):
                m = getattr(m, p)
            else:
                ok = False; break
        if ok:
            return m, head
    return None, head   # fall back to logit lens without the final norm


@torch.no_grad()
def probe_length(model, device, pool, N, n_ex, batch, colon, nl, heads, norm, head, rng):
    recs = []
    for start in range(0, n_ex, batch):
        B = min(batch, n_ex - start)
        seqs, srcs, vans = [], [], []
        for _ in range(B):
            ids, src, v = R.build_example(pool, N, colon, nl, rng)
            seqs.append(ids); srcs.append(src); vans.append(v)
        x = torch.tensor(seqs, device=device)
        out = model(x, output_attentions=True, output_hidden_states=True)
        row = torch.stack(out.attentions, 0).float()[:, :, :, -1, :]     # (L,B,H,S)
        pred = out.logits[:, -1, :].argmax(-1)
        van = torch.tensor(vans, device=device)
        # logit-lens best rank of vq at the query token, min over layers
        hs = out.hidden_states                                           # tuple(L+1) of (B,S,Hd)
        best = torch.full((B,), 10 ** 9, device=device)
        for h in hs:
            q = h[:, -1, :]                                              # (B,Hd)
            q = norm(q) if norm is not None else q
            lg = head(q)                                                 # (B,V)
            vq_lg = lg.gather(1, van.unsqueeze(1))                        # (B,1)
            rank = (lg > vq_lg).sum(1)                                    # (B,) rank of vq (0 = argmax)
            best = torch.minimum(best, rank)
        for b in range(B):
            src = srcs[b]
            a_js = float(torch.stack([row[l, b, hh, src] for (l, hh) in heads]).mean())
            recs.append({"N": N, "correct": int(pred[b] == van[b]),
                         "a_js": a_js, "vrank": int(best[b])})
        del out, row
    return recs


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="EleutherAI/pythia-1.4b")
    ap.add_argument("--lengths", default="10,20,40,80,160")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--heads", type=int, default=8)
    ap.add_argument("--dtype", default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    lengths = [int(x) for x in a.lengths.split(",")]
    n_ex = a.n
    if a.smoke:
        lengths = [6, 12]; n_ex = 12
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if a.dtype == "auto":
        dt = torch.bfloat16 if (device == "cuda" and torch.cuda.is_bf16_supported()) else torch.float32
    else:
        dt = {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[a.dtype]
    print(f"device={device} dtype={dt} model={a.model}")
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=dt, attn_implementation="eager").to(device).eval()
    norm, head = get_norm_and_head(model)
    print(f"logit-lens final-norm found: {norm is not None}")
    colon = tok.encode(":", add_special_tokens=False); nl = tok.encode("\n", add_special_tokens=False)
    pool = R.single_token_pool(tok, want=max(1600, 3 * max(lengths)))
    rng = np.random.default_rng(0)
    heads, _ = R.calibrate_heads(model, device, pool, min(lengths), colon, nl, a.heads, rng)
    print(f"retrieval heads: {heads}")
    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, "decouple_results.json")
    recs = []
    for N in lengths:
        r = probe_length(model, device, pool, N, n_ex, a.batch, colon, nl, heads, norm, head, rng)
        recs += r
        acc = np.mean([x["correct"] for x in r])
        fails = [x for x in r if not x["correct"]]
        vpres = np.mean([x["vrank"] < 10 for x in fails]) if fails else float("nan")
        print(f"N={N:4d}  acc={acc:.3f}  among failures: value-in-residual(top10)={vpres:.2f}", flush=True)
        json.dump({"model": a.model, "heads": heads, "records": recs}, open(path, "w"))
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
