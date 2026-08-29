"""Causal test in a REAL pretrained LM: does forcing attention onto the source restore retrieval?

The paper's real-model evidence is correlational (attention on the source co-declines with accuracy, and
predicts correctness within a length). The toy result is causal (patching attention onto the source restores
accuracy). This probe closes the gap: it MANIPULATES attention on the source in a real LM and reads accuracy.

Mechanism (no monkey-patching, architecture-agnostic): transformers adds the 4D attention mask to the
attention logits, so we pass a causal mask with a positive bias b added at (query row -> source key). The
bias is applied ONLY at the final query position, so the rest of the forward pass is untouched.

Conditions, run on the SAME examples (paired):
  base        : b = 0
  source@b    : +b at the correct source token
  random@b    : +b at a random OTHER (non-source, non-query) position -- THE CONTROL. If accuracy rose simply
                because attention got sharper anywhere, the control would rise too. It should not.

H-C1 (sufficiency): accuracy increases monotonically with b in the source condition.
H-C2 (specificity): accuracy does NOT increase in the random condition at the same b.
Together these say attention on the correct source is causally sufficient to drive retrieval in a real LM.

Usage:
  python colab/real_patch_probe.py --model gpt2-medium --lengths 20,40,80 --n 96 --biases 0,2,4,8
"""
from __future__ import annotations
import argparse, json, os
import numpy as np
import torch
import real_model_probe as R


def causal_mask(B, S, device, dtype):
    m = torch.zeros(B, 1, S, S, device=device, dtype=dtype)
    m.masked_fill_(torch.triu(torch.ones(S, S, dtype=torch.bool, device=device), 1), float("-inf"))
    return m


@torch.no_grad()
def run_condition(model, x, srcs, heads, bias, mode, rng, device, dtype):
    """mode: 'base' | 'source' | 'random'. Returns (preds, mean a_js on retrieval heads)."""
    B, S = x.shape
    mask = causal_mask(B, S, device, dtype)
    tgt_pos = []
    for b in range(B):
        if mode == "source":
            p = srcs[b]
        elif mode == "random":
            p = int(rng.integers(0, S - 1))            # any earlier position that is not the source
            while p == srcs[b]:
                p = int(rng.integers(0, S - 1))
        else:
            p = -1
        tgt_pos.append(p)
        if p >= 0:
            mask[b, :, -1, p] += bias
    out = model(x, attention_mask=mask, output_attentions=True)
    row = torch.stack([a[:, :, -1, :] for a in out.attentions], 0).float()   # (L,B,H,S)
    pred = out.logits[:, -1, :].argmax(-1)
    ajs = [float(torch.stack([row[l, b, h, srcs[b]] for (l, h) in heads]).mean()) for b in range(B)]
    del out, row
    return pred, ajs


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt2-medium")
    ap.add_argument("--lengths", default="20,40,80")
    ap.add_argument("--n", type=int, default=96)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--heads", type=int, default=8)
    ap.add_argument("--biases", default="0,2,4,8")
    ap.add_argument("--dtype", default="auto", choices=["auto", "fp32", "bf16"])
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    lengths = [int(x) for x in a.lengths.split(",")]
    biases = [float(x) for x in a.biases.split(",")]
    n_ex = a.n
    if a.smoke:
        lengths, n_ex, biases = [10, 20], 16, [0, 4]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dt = (torch.bfloat16 if (device == "cuda" and torch.cuda.is_bf16_supported()) else torch.float32) \
        if a.dtype == "auto" else {"fp32": torch.float32, "bf16": torch.bfloat16}[a.dtype]
    print(f"device={device} dtype={dt} model={a.model}", flush=True)
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=dt, attn_implementation="eager").to(device).eval()
    colon = tok.encode(":", add_special_tokens=False); nl = tok.encode("\n", add_special_tokens=False)
    pool = R.single_token_pool(tok, want=2000)
    rng = np.random.default_rng(0)

    # verify the 4D mask actually biases attention in THIS architecture before trusting any result
    ids, src, _ = R.build_example(pool, lengths[0], colon, nl, rng)
    xv = torch.tensor([ids], device=device)
    with torch.no_grad():
        r0, _ = R.final_row(model, xv)
        mk = causal_mask(1, xv.shape[1], device, dt); mk[0, :, -1, src] += 12.0
        o1 = model(xv, attention_mask=mk, output_attentions=True)
        r1 = torch.stack([q[:, :, -1, :] for q in o1.attentions], 0).float()
    before, after = float(r0[:, 0, :, src].mean()), float(r1[:, 0, :, src].mean())
    print(f"mask check: mean attention on source {before:.4f} -> {after:.4f}", flush=True)
    if after <= before * 1.5:
        raise SystemExit("the 4D attention mask does not bias attention in this model; aborting")

    heads, _ = R.calibrate_heads(model, device, pool, lengths[0], colon, nl, a.heads, rng)
    print(f"retrieval heads: {heads}", flush=True)
    os.makedirs(a.outdir, exist_ok=True)
    path = os.path.join(a.outdir, "realpatch_results.json")
    recs = []
    for L in lengths:
        for start in range(0, n_ex, a.batch):
            B = min(a.batch, n_ex - start)
            ex = [R.build_example(pool, L, colon, nl, rng) for _ in range(B)]
            x = torch.tensor([e[0] for e in ex], device=device)
            srcs = [e[1] for e in ex]
            van = torch.tensor([e[2] for e in ex], device=device)
            for bias in biases:
                modes = ["base"] if bias == 0 else ["source", "random"]
                for mode in modes:
                    pred, ajs = run_condition(model, x, srcs, heads, bias, mode, rng, device, dt)
                    for b in range(B):
                        recs.append({"L": L, "bias": bias, "mode": mode,
                                     "correct": int(pred[b] == van[b]), "a_js": ajs[b]})
        # progress
        for bias in biases:
            for mode in (["base"] if bias == 0 else ["source", "random"]):
                sel = [r for r in recs if r["L"] == L and r["bias"] == bias and r["mode"] == mode]
                if sel:
                    print(f"  L={L:4d} bias={bias:>4} {mode:>6}: acc={np.mean([r['correct'] for r in sel]):.3f} "
                          f"a_js={np.mean([r['a_js'] for r in sel]):.3f}", flush=True)
        json.dump({"model": a.model, "heads": heads, "records": recs}, open(path, "w"))
    print(f"saved: {path}")


if __name__ == "__main__":
    main()
