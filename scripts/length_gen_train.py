"""Length-generalization trainer for the vanishing-variance x positional-encoding study.

Gap (from the transformer-gap-scan; source paper arXiv:2504.02827 "On Vanishing Variance in
Transformer Length Generalization"): that paper shows attention-output variance collapses as
sequence length grows and that a post-attention normalization fixes it -- but (per our prior-art
check) on order-INVARIANT tasks and without crossing the fix against positional encoding.

Two tasks, same harness, same 2x2 {nope,rope} x {post_attn_ln 0/1}:
  - task=addition : reversed multi-digit addition -> ORDER-DEPENDENT (position is load-bearing).
  - task=recall   : dictionary lookup / associative recall -> ORDER-INVARIANT (the source paper's
                    own task family). Serves as the internal POSITIVE CONTROL: if post-LN rescues
                    length extrapolation here (reproducing 2504.02827) but not on addition, the
                    contrast is the contribution and the harness is shown to have dynamic range.

Logs, per test length: exact-match accuracy (train short, test to 3x) and attention-output variance
per layer (the vanishing-variance observable, captured BEFORE post-LN). Runs on CPU.
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Tasks. Each provides: vocab size, pad id, and make_example(rng, lo, hi) ->
# (tokens, answer_start) where positions >= answer_start (through EOS) are supervised.
# ---------------------------------------------------------------------------

# addition vocab: 0-9 digits, '+', '=', PAD, EOS
ADD_PLUS, ADD_EQ, ADD_PAD, ADD_EOS = 10, 11, 12, 13


def make_addition(rng, lo, hi):
    la = int(rng.integers(lo, hi + 1)); lb = int(rng.integers(lo, hi + 1))
    a = int(rng.integers(10 ** (la - 1) if la > 1 else 0, 10 ** la))
    b = int(rng.integers(10 ** (lb - 1) if lb > 1 else 0, 10 ** lb))
    ar = [int(c) for c in str(a)][::-1]
    br = [int(c) for c in str(b)][::-1]
    cr = [int(c) for c in str(a + b)][::-1]
    toks = ar + [ADD_PLUS] + br + [ADD_EQ] + cr + [ADD_EOS]
    answer_start = len(ar) + 1 + len(br) + 1
    return toks, answer_start


# recall vocab: values 0..9 (tokens 0-9), keys K0..K39 (tokens 10-49), EQ=50, QUERY=51, EOS=52, PAD=53
REC_NKEYS = 40
REC_KEY0 = 10
REC_EQ, REC_QUERY, REC_EOS, REC_PAD = 50, 51, 52, 53


def make_recall(rng, lo, hi):
    n = int(rng.integers(lo, hi + 1))
    keys = rng.choice(REC_NKEYS, size=n, replace=False)          # distinct keys
    vals = rng.integers(0, 10, size=n)                            # values 0-9 (repeats ok)
    qi = int(rng.integers(0, n))                                  # which pair is queried
    toks = []
    for k, v in zip(keys, vals):
        toks += [REC_KEY0 + int(k), int(v)]
    toks += [REC_QUERY, REC_KEY0 + int(keys[qi]), REC_EQ, int(vals[qi]), REC_EOS]
    answer_start = 2 * n + 3                                      # index of the answer value
    return toks, answer_start


TASKS = {
    "addition": {"vocab": 14, "pad": ADD_PAD, "make": make_addition},
    "recall":   {"vocab": 54, "pad": REC_PAD, "make": make_recall},
}


@dataclass
class Cfg:
    task: str = "addition"
    pe: str = "rope"           # nope | rope | learned
    post_attn_ln: bool = False
    n_layers: int = 2
    d_model: int = 128
    n_heads: int = 4
    d_mlp: int = 512
    l_train: int = 5           # operand digits (addition) / #pairs (recall) uniform in 1..l_train
    max_ctx: int = 256
    lr: float = 3e-4
    weight_decay: float = 0.1
    batch: int = 256
    steps: int = 4000
    log_every: int = 1000
    seed: int = 0
    vocab: int = 14
    pad: int = 12


def sample_batch(torch, rng, n, lo, hi, cfg: Cfg):
    """n examples with per-task length uniform in [lo, hi]. Returns padded x, y, loss_mask."""
    make = TASKS[cfg.task]["make"]
    seqs, masks, maxlen = [], [], 0
    while len(seqs) < n:
        toks, ans = make(rng, lo, hi)
        if len(toks) > cfg.max_ctx:
            continue
        m = [0] * len(toks)
        for i in range(ans, len(toks)):
            m[i] = 1
        seqs.append(toks); masks.append(m); maxlen = max(maxlen, len(toks))
    xs, ys, ms = [], [], []
    for toks, m in zip(seqs, masks):
        pad = maxlen - len(toks)
        xs.append(toks + [cfg.pad] * pad)
        ys.append(toks[1:] + [cfg.pad] * (pad + 1))
        ms.append(m[1:] + [0] * (pad + 1))
    x = torch.tensor(xs); y = torch.tensor(ys); mask = torch.tensor(ms, dtype=torch.float32)
    return x, y, mask


def build_model(torch, nn, cfg: Cfg):
    gen = torch.Generator().manual_seed(cfg.seed)
    d_head = cfg.d_model // cfg.n_heads

    def rope_freqs(t, device):
        half = d_head // 2
        inv = 1.0 / (10000 ** (torch.arange(0, half, device=device).float() / half))
        pos = torch.arange(t, device=device).float()
        ang = torch.outer(pos, inv)
        return torch.cos(ang), torch.sin(ang)

    def apply_rope(x, cos, sin):
        x1, x2 = x[..., ::2], x[..., 1::2]
        cos = cos[None, None]; sin = sin[None, None]
        return torch.stack([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1).flatten(-2)

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            self.ln1 = nn.LayerNorm(cfg.d_model); self.ln2 = nn.LayerNorm(cfg.d_model)
            self.W_Q = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
            self.W_K = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
            self.W_V = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
            self.W_O = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
            self.post_ln = nn.LayerNorm(cfg.d_model) if cfg.post_attn_ln else nn.Identity()
            self.W_in = nn.Linear(cfg.d_model, cfg.d_mlp); self.W_out = nn.Linear(cfg.d_mlp, cfg.d_model)
            self.attn_out_var = None

        def forward(self, h, rope):
            b, t, _ = h.shape
            x = self.ln1(h)
            q = self.W_Q(x).view(b, t, cfg.n_heads, d_head).transpose(1, 2)
            k = self.W_K(x).view(b, t, cfg.n_heads, d_head).transpose(1, 2)
            v = self.W_V(x).view(b, t, cfg.n_heads, d_head).transpose(1, 2)
            if rope is not None:
                cos, sin = rope; q = apply_rope(q, cos, sin); k = apply_rope(k, cos, sin)
            scores = (q @ k.transpose(-1, -2)) / (d_head ** 0.5)
            causal = torch.triu(torch.full((t, t), float("-inf"), device=h.device), diagonal=1)
            attn = torch.softmax(scores + causal, dim=-1)
            z = (attn @ v).transpose(1, 2).reshape(b, t, cfg.d_model)
            z = self.W_O(z)
            self.attn_out_var = float(z.detach().float().var(dim=-1).mean().cpu())  # BEFORE post-LN
            z = self.post_ln(z)
            h = h + z
            h = h + self.W_out(torch.relu(self.W_in(self.ln2(h))))
            return h

    class Model(nn.Module):
        def __init__(self):
            super().__init__()
            self.embed = nn.Embedding(cfg.vocab, cfg.d_model)
            self.learned_pos = (nn.Parameter(torch.randn(cfg.max_ctx, cfg.d_model, generator=gen) * 0.02)
                                if cfg.pe == "learned" else None)
            self.blocks = nn.ModuleList([Block() for _ in range(cfg.n_layers)])
            self.ln_f = nn.LayerNorm(cfg.d_model)
            self.unembed = nn.Linear(cfg.d_model, cfg.vocab, bias=False)

        def forward(self, x):
            b, t = x.shape
            h = self.embed(x)
            if self.learned_pos is not None:
                h = h + self.learned_pos[None, :t, :]
            rope = rope_freqs(t, x.device) if cfg.pe == "rope" else None
            for blk in self.blocks:
                h = blk(h, rope)
            return self.unembed(self.ln_f(h))

        def attn_vars(self):
            return [blk.attn_out_var for blk in self.blocks]

    return Model()


@dataclass
class EvalRow:
    length: int
    exact_match: float
    per_token: float          # fraction of individual answer tokens correct (graded, teacher-forced)
    attn_var_by_layer: list


def evaluate(torch, model, cfg: Cfg, rng, lengths, n_eval=100):
    model.eval()
    rows = []
    for L in lengths:
        correct = 0; total = 0; tok_correct = 0; tok_total = 0; var_acc = None
        for _ in range(max(1, n_eval // 32)):
            x, y, mask = sample_batch(torch, rng, 32, L, L, cfg)
            with torch.no_grad():
                logits = model(x)
            pred = logits.argmax(-1)
            m = mask.bool()
            for i in range(x.shape[0]):
                mi = m[i]
                if mi.sum() == 0:
                    continue
                total += 1
                eq = (pred[i][mi] == y[i][mi])
                tok_correct += int(eq.sum()); tok_total += int(mi.sum())
                if bool(eq.all()):
                    correct += 1
            v = model.attn_vars()
            var_acc = v if var_acc is None else [a + b for a, b in zip(var_acc, v)]
        rows.append(EvalRow(L, correct / max(1, total), tok_correct / max(1, tok_total),
                            [round(x / max(1, n_eval // 32), 5) for x in (var_acc or [0] * cfg.n_layers)]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="addition", choices=list(TASKS))
    ap.add_argument("--pe", default="rope", choices=["nope", "rope", "learned"])
    ap.add_argument("--post-attn-ln", type=int, default=0)
    ap.add_argument("--n-layers", type=int, default=2)
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--l-train", type=int, default=5)
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--log-every", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output", default="results/lengthgen_run.csv")
    args = ap.parse_args()
    import torch
    from torch import nn

    tk = TASKS[args.task]
    cfg = Cfg(task=args.task, pe=args.pe, post_attn_ln=bool(args.post_attn_ln), n_layers=args.n_layers,
              d_model=args.d_model, l_train=args.l_train, steps=args.steps,
              log_every=args.log_every, seed=args.seed, vocab=tk["vocab"], pad=tk["pad"])
    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)
    model = build_model(torch, nn, cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay, betas=(0.9, 0.98))
    lossfn = nn.CrossEntropyLoss(reduction="none")
    tag = f"task={cfg.task} pe={cfg.pe} postLN={int(cfg.post_attn_ln)}"

    for step in range(cfg.steps + 1):
        model.train()
        x, y, mask = sample_batch(torch, rng, cfg.batch, 1, cfg.l_train, cfg)
        logits = model(x)
        loss = lossfn(logits.reshape(-1, cfg.vocab), y.reshape(-1)).reshape(y.shape)
        loss = (loss * mask).sum() / mask.sum().clamp_min(1)
        opt.zero_grad(); loss.backward(); opt.step()
        if step % cfg.log_every == 0:
            ev = evaluate(torch, model, cfg, np.random.default_rng(999),
                          lengths=[cfg.l_train, 2 * cfg.l_train, 3 * cfg.l_train])
            msg = " | ".join(f"L{r.length}:em={r.exact_match:.2f},tok={r.per_token:.2f},var={r.attn_var_by_layer}" for r in ev)
            print(f"[{tag}] step {step:6d} loss {loss.item():.3f} | {msg}", flush=True)

    lengths = list(range(1, 3 * cfg.l_train + 1))
    ev = evaluate(torch, model, cfg, np.random.default_rng(999), lengths=lengths, n_eval=128)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task", "pe", "post_attn_ln", "length", "exact_match", "per_token"] +
                   [f"attn_var_L{i}" for i in range(cfg.n_layers)])
        for r in ev:
            w.writerow([cfg.task, cfg.pe, int(cfg.post_attn_ln), r.length,
                        round(r.exact_match, 4), round(r.per_token, 4)] + r.attn_var_by_layer)
    print(f"[{tag}] wrote {args.output}")


if __name__ == "__main__":
    main()
