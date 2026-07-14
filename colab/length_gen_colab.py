"""Vanishing-variance x positional-encoding on length generalization -- COLAB GPU driver.

WHY THIS EXISTS
  Gap (novelty 0.78, prior-art verified): arXiv:2504.02827 "On Vanishing Variance in Transformer
  Length Generalization" shows attention-output variance collapses with length and a post-attention
  normalization fixes it -- but ONLY on order-INVARIANT tasks, with positional encoding deliberately
  REMOVED, never crossed against {NoPE, RoPE}. Open question: does the fix restore length extrapolation
  on an ORDER-DEPENDENT task, and is the effect PE-dependent?

  The CPU pilot could not reach a clean test regime: arithmetic fails at CHANCE past train length (no
  dynamic range) and a tiny model never MASTERS associative recall (the order-invariant positive
  control). This GPU driver uses a big-enough model + LR warmup/cosine + enough steps to (a) master the
  recall positive control at train length, then (b) run the identical pre-registered 2x2 on both tasks.

HOW TO RUN (Colab)
  1. Runtime -> Change runtime type -> GPU (T4 is fine).
  2. Upload this file (or %%writefile it), then:  !python length_gen_colab.py
     Quick smoke first (recommended):            !python length_gen_colab.py --smoke
  3. Read the "CONTRAST VERDICT" block at the end. Results also saved to lengthgen_results.json / .csv.

PRE-REGISTERED CONTRAST (locked; every outcome reportable)
  - post-LN rescues recall (order-invariant) but NOT addition (order-dependent) -> CONTRAST CONFIRMED:
    variance collapse governs order-invariant length-gen, not when position is load-bearing. (the paper)
  - post-LN rescues both -> the fix transfers to order-dependent tasks too (stronger positive).
  - post-LN rescues NEITHER (incl. recall) -> POSITIVE CONTROL FAILED: harness cannot reproduce the
    source effect; any addition null is about the setup, not the science. Do NOT publish the contrast.
  Validity gate: a cell with train-length exact-match < 0.8 is UNINFORMATIVE for extrapolation.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# --------------------------------------------------------------------------- tasks
# addition vocab: 0-9 digits, '+', '=', PAD, EOS   (ORDER-DEPENDENT: position load-bearing)
ADD_PLUS, ADD_EQ, ADD_PAD, ADD_EOS = 10, 11, 12, 13

def _rand_number(rng, ndigits):
    """Exactly ndigits digits (no leading zero for ndigits>1), built digit-by-digit so ndigits can be
    arbitrarily large -- Python int is arbitrary-precision; avoids numpy int64 overflow at 10**ndigits."""
    if ndigits <= 1:
        return int(rng.integers(0, 10))
    digits = [int(rng.integers(1, 10))] + [int(rng.integers(0, 10)) for _ in range(ndigits - 1)]
    return int("".join(map(str, digits)))

# All make_* return (tokens, answer_start, target_idx). target_idx = input position holding the answer
# value for single-source retrieval tasks (ground truth for the attention observable); -1 if n/a.
def make_addition(rng, lo, hi):
    la = int(rng.integers(lo, hi + 1)); lb = int(rng.integers(lo, hi + 1))
    a = _rand_number(rng, la); b = _rand_number(rng, lb)
    ar = [int(c) for c in str(a)][::-1]; br = [int(c) for c in str(b)][::-1]
    cr = [int(c) for c in str(a + b)][::-1]
    toks = ar + [ADD_PLUS] + br + [ADD_EQ] + cr + [ADD_EOS]
    return toks, len(ar) + 1 + len(br) + 1, -1   # addition: no single source token

# recall = the paper's DICTIONARY LOOKUP. values 0-9, keys K0..K255 (10-265), EQ QUERY EOS PAD.
# 256 distinct keys so long lengths can still draw distinct keys.  (ORDER-INVARIANT)
REC_NKEYS = 256
REC_KEY0 = 10
REC_EQ, REC_QUERY, REC_EOS, REC_PAD = 266, 267, 268, 269

def make_recall(rng, lo, hi):
    n = int(rng.integers(lo, hi + 1))
    keys = rng.choice(REC_NKEYS, size=n, replace=False)
    vals = rng.integers(0, 10, size=n)
    qi = int(rng.integers(0, n))
    toks = []
    for k, v in zip(keys, vals):
        toks += [REC_KEY0 + int(k), int(v)]
    toks += [REC_QUERY, REC_KEY0 + int(keys[qi]), REC_EQ, int(vals[qi]), REC_EOS]
    return toks, 2 * n + 3, 2 * qi + 1   # queried value sits at index 2*qi+1

# flag-retrieval vocab: values 0-9, MARK=10, EQ=11, EOS=12, PAD=13  (ORDER-INVARIANT, 1-hop, not guessable)
FLAG_MARK, FLAG_EQ, FLAG_EOS, FLAG_PAD = 10, 11, 12, 13

def make_flagret(rng, lo, hi):
    n = int(rng.integers(lo, hi + 1))
    vals = rng.integers(0, 10, size=n)
    ki = int(rng.integers(0, n))            # exactly one value is MARKed
    toks = []; tgt = -1
    for i, v in enumerate(vals):
        if i == ki:
            toks.append(FLAG_MARK)
        toks.append(int(v))
        if i == ki:
            tgt = len(toks) - 1          # position of the marked value
    toks.append(FLAG_EQ)
    answer_start = len(toks)
    toks.append(int(vals[ki])); toks.append(FLAG_EOS)
    return toks, answer_start, tgt

# argmax = the paper's ARGMAX RETRIEVAL: output the value paired with the maximum score.
# values 0-9, scores S0..S255 (10-265), EQ EOS PAD.  (ORDER-INVARIANT; value uniform => not guessable)
ARG_NSCORES = 256
ARG_S0 = 10
ARG_EQ, ARG_EOS, ARG_PAD = 266, 267, 268

def make_argmax(rng, lo, hi):
    n = int(rng.integers(lo, hi + 1))
    scores = rng.choice(ARG_NSCORES, size=n, replace=False)
    vals = rng.integers(0, 10, size=n)
    amax = int(np.argmax(scores))
    toks = []
    for s, v in zip(scores, vals):
        toks += [ARG_S0 + int(s), int(v)]
    toks.append(ARG_EQ)
    answer_start = len(toks)
    toks.append(int(vals[amax])); toks.append(ARG_EOS)
    return toks, answer_start, 2 * amax + 1   # value of the max-score item

TASKS = {
    "addition": {"vocab": 14, "pad": ADD_PAD, "make": make_addition, "order": "dependent"},
    "flagret":  {"vocab": 14, "pad": FLAG_PAD, "make": make_flagret, "order": "invariant"},
    "recall":   {"vocab": 270, "pad": REC_PAD, "make": make_recall, "order": "invariant"},
    "argmax":   {"vocab": 269, "pad": ARG_PAD, "make": make_argmax, "order": "invariant"},
}


@dataclass
class Cfg:
    task: str = "recall"
    pe: str = "rope"
    post_attn_ln: bool = False
    n_layers: int = 4
    d_model: int = 256
    n_heads: int = 8
    d_mlp: int = 1024
    l_train: int = 5
    attn_scale: str = "none"   # Direction B: "none" | "loglen" (length-scaled logit sharpening) | "fixedK"
    attn_ref: float = 16.0     # reference #keys where loglen scaling == 1 (~ training sequence length)
    max_ctx: int = 1024
    lr: float = 5e-4
    warmup: int = 500
    weight_decay: float = 0.1
    batch: int = 512
    steps: int = 20000
    seed: int = 0
    vocab: int = 54
    pad: int = 53


# -------- eval-time attention patching (default OFF; used by colab/patch_experiment.py) -----------------
# Set PATCH = {"layer": int, "p": float, "k": int|None} to overwrite the answer-query attention row with a
# target distribution: mass p on the correct source token, the rest spread uniformly over k nearest valid
# keys (k=None spreads over all valid keys). Lets us MOVE attention-on-source causally, holding the model
# fixed. With PATCH=None this code never runs, so all other experiments are unaffected.
PATCH = None


def _apply_attn_patch(attn, aq, tgt):
    b, _, t, _ = attn.shape
    p = float(PATCH["p"]); k = PATCH.get("k", None)
    attn = attn.clone()
    for i in range(b):
        q = int(aq[i]); j = int(tgt[i])
        if q < 0 or j < 0 or j > q:
            continue
        valid = [x for x in range(q + 1) if x != j]   # causal keys 0..q excluding the source j
        if k is not None and 0 < k < len(valid):
            valid = valid[-k:]                         # the k keys nearest the query
        row = torch.zeros(t, device=attn.device, dtype=attn.dtype)
        if valid:
            row[j] = p; row[valid] = (1.0 - p) / len(valid)
        else:
            row[j] = 1.0
        attn[i, :, q, :] = row
    return attn


def sample_batch(rng, n, lo, hi, cfg):
    make = TASKS[cfg.task]["make"]
    seqs, masks, aqs, tgts, maxlen = [], [], [], [], 0
    tries = 0
    while len(seqs) < n:
        tries += 1
        if tries > 200 * n:  # guard: length infeasible for max_ctx -> fail loudly, don't hang
            raise ValueError(f"{cfg.task} length [{lo},{hi}] exceeds max_ctx={cfg.max_ctx}; raise max_ctx")
        toks, ans, tgt = make(rng, lo, hi)
        if len(toks) > cfg.max_ctx:
            continue
        m = [0] * len(toks)
        for i in range(ans, len(toks)):
            m[i] = 1
        seqs.append(toks); masks.append(m); maxlen = max(maxlen, len(toks))
        aqs.append(ans - 1); tgts.append(tgt)   # answer-query position; ground-truth source position
    xs, ys, ms = [], [], []
    for toks, m in zip(seqs, masks):
        pad = maxlen - len(toks)
        xs.append(toks + [cfg.pad] * pad)
        ys.append(toks[1:] + [cfg.pad] * (pad + 1))
        ms.append(m[1:] + [0] * (pad + 1))
    x = torch.tensor(xs, device=DEVICE)
    y = torch.tensor(ys, device=DEVICE)
    mask = torch.tensor(ms, dtype=torch.float32, device=DEVICE)
    aq = torch.tensor(aqs, dtype=torch.long, device=DEVICE)
    tgt = torch.tensor(tgts, dtype=torch.long, device=DEVICE)
    return x, y, mask, aq, tgt


def build_model(cfg):
    gen = torch.Generator().manual_seed(cfg.seed)
    d_head = cfg.d_model // cfg.n_heads

    def rope_freqs(t, device):
        half = d_head // 2
        inv = 1.0 / (10000 ** (torch.arange(0, half, device=device).float() / half))
        ang = torch.outer(torch.arange(t, device=device).float(), inv)
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
            self.attn_out_var = None       # variance of the attention output BEFORE the fix
            self.attn_out_var_post = None  # variance AFTER the fix (== pre when fix is off / Identity)
            self.attn_tgt = None           # attention mass on the ground-truth source token (max over heads)
            self.attn_ent = None           # normalized attention entropy at the answer-query position
            self.attn_max = None           # max attention weight (sharpness) at the answer-query position
            self.z_aq_var = None           # variance of z at the answer-query position (for the patch experiment)
            self.z_aq_scores = None        # (b,heads,t) effective attention logits at the answer query (break-length law)

        def forward(self, h, rope, aq=None, tgt=None):
            b, t, _ = h.shape
            x = self.ln1(h)
            q = self.W_Q(x).view(b, t, cfg.n_heads, d_head).transpose(1, 2)
            k = self.W_K(x).view(b, t, cfg.n_heads, d_head).transpose(1, 2)
            v = self.W_V(x).view(b, t, cfg.n_heads, d_head).transpose(1, 2)
            if rope is not None:
                cos, sin = rope; q = apply_rope(q, cos, sin); k = apply_rope(k, cos, sin)
            scores = (q @ k.transpose(-1, -2)) / (d_head ** 0.5)
            if cfg.attn_scale != "none":  # Direction B: sharpen attention logits to counteract dispersion
                if cfg.attn_scale == "loglen":
                    pos = torch.arange(1, t + 1, device=h.device).float()  # query q attends to q+1 keys
                    s = (torch.log(pos.clamp(min=2.0)) / math.log(cfg.attn_ref)).clamp(min=1.0)
                    scores = scores * s[None, None, :, None]  # per-query logit scaling
                elif cfg.attn_scale.startswith("fixed"):
                    scores = scores * float(cfg.attn_scale[5:])
            causal = torch.triu(torch.full((t, t), float("-inf"), device=h.device), diagonal=1)
            attn = torch.softmax(scores + causal, dim=-1)
            if PATCH is not None and getattr(self, "layer_idx", -1) == PATCH.get("layer") and aq is not None:
                attn = _apply_attn_patch(attn, aq, tgt)   # force attention-on-source at the query (eval only)
            if aq is not None:  # capture attention observables at the answer-query position (eval only)
                idx = torch.arange(b, device=h.device)
                rows = attn[idx, :, aq, :]                         # (b, heads, t): attn FROM aq to all keys
                self.z_aq_scores = scores[idx, :, aq, :].detach()  # (b, heads, t): effective logits at the query
                valid = tgt >= 0
                if valid.any():
                    tmass = rows[idx, :, tgt.clamp(min=0)].max(dim=1).values  # (b,) mass on target, best head
                    ent = -(rows * (rows + 1e-12).log()).sum(-1).mean(1) / math.log(max(t, 2))  # (b,)
                    sharp = rows.max(-1).values.mean(1)              # (b,) mean over heads of max weight
                    self.attn_tgt = float(tmass[valid].mean().cpu())
                    self.attn_ent = float(ent[valid].mean().cpu())
                    self.attn_max = float(sharp[valid].mean().cpu())
                else:
                    self.attn_tgt = self.attn_ent = self.attn_max = float("nan")
            z = (attn @ v).transpose(1, 2).reshape(b, t, cfg.d_model)
            z = self.W_O(z)
            if aq is not None:  # variance of the attention output AT the answer-query position (patch experiment)
                self.z_aq_var = float(z[torch.arange(b, device=z.device), aq, :].detach().float().var(dim=-1).mean().cpu())
            self.attn_out_var = float(z.detach().float().var(dim=-1).mean().cpu())  # BEFORE the fix
            z = self.post_ln(z)
            self.attn_out_var_post = float(z.detach().float().var(dim=-1).mean().cpu())  # AFTER the fix
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
            for i, blk in enumerate(self.blocks):
                blk.layer_idx = i   # so the patch hook can target a specific layer
            self.ln_f = nn.LayerNorm(cfg.d_model)
            self.unembed = nn.Linear(cfg.d_model, cfg.vocab, bias=False)

        def forward(self, x, aq=None, tgt=None):
            b, t = x.shape
            h = self.embed(x)
            if self.learned_pos is not None:
                h = h + self.learned_pos[None, :t, :]
            rope = rope_freqs(t, x.device) if cfg.pe == "rope" else None
            for blk in self.blocks:
                h = blk(h, rope, aq, tgt)
            return self.unembed(self.ln_f(h))

        def attn_vars(self):
            return [blk.attn_out_var for blk in self.blocks]

        def attn_vars_post(self):
            return [blk.attn_out_var_post for blk in self.blocks]

        def attn_stats(self):  # per-layer (tgt-mass, entropy, sharpness) at the answer-query position
            return ([blk.attn_tgt for blk in self.blocks],
                    [blk.attn_ent for blk in self.blocks],
                    [blk.attn_max for blk in self.blocks])

    return Model().to(DEVICE)


def evaluate(model, cfg, rng, lengths, n_eval=256):
    model.eval()
    rows = []
    for L in lengths:
        correct = total = tok_c = tok_t = 0
        var_acc = varp_acc = tgt_acc = ent_acc = mx_acc = None; nb = max(1, n_eval // 64)
        for _ in range(nb):
            x, y, mask, aq, tgt = sample_batch(rng, 64, L, L, cfg)
            with torch.no_grad():
                pred = model(x, aq, tgt).argmax(-1)
            m = mask.bool()
            for i in range(x.shape[0]):
                mi = m[i]
                if mi.sum() == 0:
                    continue
                total += 1
                eq = (pred[i][mi] == y[i][mi])
                tok_c += int(eq.sum()); tok_t += int(mi.sum())
                if bool(eq.all()):
                    correct += 1
            v = model.attn_vars(); vp = model.attn_vars_post()
            at, ae, am = model.attn_stats()
            var_acc = v if var_acc is None else [a + b for a, b in zip(var_acc, v)]
            varp_acc = vp if varp_acc is None else [a + b for a, b in zip(varp_acc, vp)]
            tgt_acc = at if tgt_acc is None else [a + b for a, b in zip(tgt_acc, at)]
            ent_acc = ae if ent_acc is None else [a + b for a, b in zip(ent_acc, ae)]
            mx_acc = am if mx_acc is None else [a + b for a, b in zip(mx_acc, am)]
        rows.append({"length": L, "em": correct / max(1, total), "tok": tok_c / max(1, tok_t),
                     "var": [round(x / nb, 5) for x in var_acc],
                     "var_post": [round(x / nb, 5) for x in varp_acc],
                     "attn_tgt": [round(x / nb, 5) for x in tgt_acc],
                     "attn_ent": [round(x / nb, 5) for x in ent_acc],
                     "attn_max": [round(x / nb, 5) for x in mx_acc]})
    return rows


def train_one(cfg, log=print):
    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)
    model = build_model(cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay, betas=(0.9, 0.98))

    def lr_at(step):
        if step < cfg.warmup:
            return step / max(1, cfg.warmup)
        p = (step - cfg.warmup) / max(1, cfg.steps - cfg.warmup)
        return 0.5 * (1 + math.cos(math.pi * min(1.0, p)))

    lossfn = nn.CrossEntropyLoss(reduction="none")
    tag = f"task={cfg.task} pe={cfg.pe} postLN={int(cfg.post_attn_ln)} seed={cfg.seed}"
    L = cfg.l_train
    # eval out to LONG length ratios -- the source paper's variance-collapse regime shows up far past 3x.
    # cap each length so even addition's ~3-token-per-digit sequence fits max_ctx.
    key_mults = [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 30, 50]
    cap = cfg.max_ctx // 3
    lengths = sorted(set([m * L for m in key_mults] + list(range(1, 3 * L + 1))))
    lengths = [x for x in lengths if 1 <= x <= cap]
    Ls_log = [L, 3 * L, min(10 * L, cap)]
    for step in range(cfg.steps + 1):
        model.train()
        for g in opt.param_groups:
            g["lr"] = cfg.lr * lr_at(step)
        x, y, mask, _, _ = sample_batch(rng, cfg.batch, 1, cfg.l_train, cfg)
        logits = model(x)   # training doesn't need the attention observables
        loss = lossfn(logits.reshape(-1, cfg.vocab), y.reshape(-1)).reshape(y.shape)
        loss = (loss * mask).sum() / mask.sum().clamp_min(1)
        opt.zero_grad(); loss.backward(); opt.step()
        if step % max(1, cfg.steps // 10) == 0:
            ev = evaluate(model, cfg, np.random.default_rng(999), Ls_log, n_eval=128)
            msg = " | ".join(f"L{r['length']}:em={r['em']:.2f},tok={r['tok']:.2f}" for r in ev)
            log(f"[{tag}] step {step:6d} loss {loss.item():.3f} | {msg}")
    ladder = evaluate(model, cfg, np.random.default_rng(999), lengths, n_eval=128)
    return {"cfg": {k: getattr(cfg, k) for k in ("task", "pe", "post_attn_ln", "seed",
                    "n_layers", "d_model", "steps", "l_train", "attn_scale")}, "ladder": ladder}


def summarize(results, log=print):
    """Aggregate across seeds and print the pre-registered contrast verdict.

    Key upgrade: the benefit is measured at the LONGEST length where the no-LN baseline actually FAILS
    (per-token < 0.9). A control that never breaks cannot test the fix -> reported as 'never broke',
    NOT as a null. This separates a genuine negative (baseline fails, fix doesn't rescue) from an
    uninformative one (baseline never fails, nothing to rescue)."""
    L = results[0]["cfg"]["l_train"]
    mults = [1, 2, 3, 6, 10]
    names = {f"{m}x": m * L for m in mults}

    def cells(task, pe, ln, metric):
        vals = {nm: [] for nm in names}
        for r in results:
            c = r["cfg"]
            if c["task"] != task or c["pe"] != pe or c["post_attn_ln"] != ln:
                continue
            for row in r["ladder"]:
                for nm, Lv in names.items():
                    if row["length"] == Lv:
                        vals[nm].append(row[metric])
        return {nm: (sum(v) / len(v) if v else float("nan")) for nm, v in vals.items()}

    def var_stab(task, pe, ln):
        # collapse ratio (var@longest / var@train) for the MOST-collapsing layer -- layer 0 barely
        # moves; the collapse the source paper describes lives in deeper layers, so report min ratio.
        longest = max(v for v in names.values())
        vt, vl = [], []
        for r in results:
            c = r["cfg"]
            if c["task"] != task or c["pe"] != pe or c["post_attn_ln"] != ln:
                continue
            for row in r["ladder"]:
                if row["length"] == L:
                    vt.append(row["var"])
                if row["length"] == longest:
                    vl.append(row["var"])
        if not vt or not vl:
            return float("nan")
        vt = np.array(vt).mean(0); vl = np.array(vl).mean(0)  # per-layer means
        ratios = [vl[i] / vt[i] for i in range(len(vt)) if vt[i] > 1e-9]
        return min(ratios) if ratios else float("nan")

    log("\n" + "=" * 90 + "\nSUMMARY (mean over seeds); benefit measured where baseline BREAKS\n" + "=" * 90)
    task_help = {}
    present = [t for t in TASKS if any(r["cfg"]["task"] == t for r in results)]
    hdr = f"{'PE':<6}{'LN':<4}" + "".join(f"{nm+'-tok':<9}" for nm in names) + f"{'varStab':<8}"
    for task in present:
        log(f"\n### {task} ({TASKS[task]['order']}-order)   [tok = per-token acc; em shown for 1x only]")
        log(hdr)
        best_help = float("-inf")
        for pe in ("nope", "rope"):
            em = {ln: cells(task, pe, ln, "em") for ln in (0, 1)}
            tok = {ln: cells(task, pe, ln, "tok") for ln in (0, 1)}
            for ln in (0, 1):
                vs = var_stab(task, pe, ln)
                row = f"{pe:<6}{ln:<4}" + "".join(f"{tok[ln][nm]:<9.2f}" for nm in names) + f"{vs:<8.2f}"
                log(row)
            mastered = em[0]["1x"] >= 0.8
            # longest length where the no-LN baseline BREAKS (tok < 0.9); benefit = post-LN gain there
            broke = [nm for nm in names if nm != "1x" and tok[0][nm] < 0.9]
            if not mastered:
                log(f"       -> {pe}: UNINFORMATIVE (no-LN 1x em={em[0]['1x']:.2f} < 0.8)")
            elif not broke:
                log(f"       -> {pe}: baseline NEVER BREAKS out to {max(names.values())} "
                    f"(min tok={min(tok[0][nm] for nm in names):.2f}) -> cannot test the fix here")
            else:
                at = broke[-1]
                benefit = tok[1][at] - tok[0][at]
                best_help = max(best_help, benefit)
                log(f"       -> {pe}: baseline breaks by {at} (tok {tok[0][at]:.2f}); "
                    f"post-LN benefit there = {benefit:+.3f}")
        task_help[task] = best_help if best_help > float("-inf") else None

    log("\n" + "=" * 90 + "\nCONTRAST VERDICT (pre-registered)\n" + "=" * 90)
    dep = [t for t in present if TASKS[t]["order"] == "dependent"]
    inv = [t for t in present if TASKS[t]["order"] == "invariant"]
    add_h = max([task_help.get(t) for t in dep if task_help.get(t) is not None], default=None)
    inv_scores = {t: task_help.get(t) for t in inv if task_help.get(t) is not None}
    inv_h = max(inv_scores.values(), default=None)
    inv_best = max(inv_scores, key=inv_scores.get) if inv_scores else None
    log(f"order-DEPENDENT ({','.join(dep)}) post-LN benefit where baseline breaks: "
        f"{add_h if add_h is None else round(add_h, 3)}")
    log(f"order-INVARIANT ({','.join(inv)}) post-LN benefit where baseline breaks: "
        f"{inv_h if inv_h is None else round(inv_h, 3)}"
        + (f"  [best control: {inv_best}]" if inv_best else ""))
    thr = 0.05
    inv_ok = inv_h is not None and inv_h > thr
    add_ok = add_h is not None and add_h > thr
    if inv_h is None:
        log("CONTROL DID NOT BREAK (or never mastered): no order-invariant control both mastered train "
            "length AND failed at long length, so the variance-collapse regime was not reached. The fix "
            "cannot be tested -> push to longer lengths / a harder retrieval variant. NOT a result yet.")
    elif inv_ok and not add_ok:
        log("CONTRAST CONFIRMED: post-LN rescues length-gen on the ORDER-INVARIANT control where its "
            "baseline breaks (reproduces 2504.02827) but NOT on the ORDER-DEPENDENT task -> variance "
            "collapse is not the binding constraint when position is load-bearing. (publishable)")
    elif inv_ok and add_ok:
        log("BOTH IMPROVE: the variance fix transfers to order-dependent tasks too -> stronger positive "
            "than the source paper claims. (publishable, different framing)")
    else:
        log("GENUINE NULL: the order-invariant control DID break with length (variance-collapse regime "
            "reached) yet post-LN did not rescue it -> in this harness stabilizing attention-output "
            "variance does not drive length generalization. This directly scopes/contests 2504.02827; "
            "check whether the control actually exhibits variance collapse + length-gen failure.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="tiny fast run to validate the pipeline on GPU")
    ap.add_argument("--tasks", default="addition,flagret,recall,argmax",
                    help="addition=order-dependent; flagret/recall/argmax=order-invariant "
                         "(recall=dict-lookup, argmax=argmax-retrieval: the paper's own tasks)")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--outdir", default=".",
                    help="where to save/resume results; use a Google Drive path on Colab so results "
                         "survive runtime recycling, e.g. /content/drive/MyDrive/lengthgen")
    ap.add_argument("--attn-scale", default="none",
                    help="Direction B intervention: none | loglen | fixedK (e.g. fixed2.0). "
                         "When != none, runs the attention-sharpening condition (LN off).")
    ap.add_argument("--attn-ref", type=float, default=16.0,
                    help="reference #keys where loglen scaling == 1 (~ training sequence length)")
    ap.add_argument("--n-layers", type=int, default=None, help="override model depth (scale experiment)")
    ap.add_argument("--d-model", type=int, default=None,
                    help="override model width (scale experiment); heads=d_model//32, d_mlp=4*d_model")
    ap.add_argument("--batch", type=int, default=None, help="override training batch size (lower if OOM)")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    res_path = os.path.join(args.outdir, "lengthgen_results.json")
    csv_path = os.path.join(args.outdir, "lengthgen_ladder.csv")
    print(f"device = {DEVICE}")
    if DEVICE == "cpu":
        print("WARNING: no GPU detected. Runtime -> Change runtime type -> GPU, then rerun.")

    tasks = args.tasks.split(",")
    seeds = [int(s) for s in args.seeds.split(",")]
    if args.smoke:
        steps = 800; seeds = [0]
        base = dict(n_layers=2, d_model=128, n_heads=4, d_mlp=512, batch=256, warmup=100)
    else:
        steps = args.steps or 4000   # flagret/argmax converge ~2k, addition ~2.4k -> 4k is plenty & fast
        base = dict(n_layers=4, d_model=256, n_heads=8, d_mlp=1024, batch=512, warmup=400)
    # scale experiment: override size from CLI (heads and mlp derived to keep the same proportions).
    # NOTE: the resume key does NOT include model size, so a scale run MUST use a fresh --outdir.
    if args.d_model:
        base.update(d_model=args.d_model, n_heads=max(1, args.d_model // 32), d_mlp=4 * args.d_model)
    if args.n_layers:
        base["n_layers"] = args.n_layers
    if args.batch:
        base["batch"] = args.batch

    def save(results):
        with open(res_path, "w") as f:
            json.dump(results, f, indent=2)
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["task", "pe", "post_attn_ln", "seed", "length", "em", "tok", "var_L0"])
            for r in results:
                c = r["cfg"]
                for row in r["ladder"]:
                    w.writerow([c["task"], c["pe"], c["post_attn_ln"], c["seed"], row["length"],
                                round(row["em"], 4), round(row["tok"], 4), row["var"][0]])

    def key(task, pe, ln, seed, ascale):
        return (task, pe, int(ln), int(seed), ascale)

    # RESUME: reload any completed runs so re-running after a Colab disconnect continues, not restarts.
    results = []
    if os.path.exists(res_path):
        try:
            results = json.load(open(res_path))
            print(f"[resume] loaded {len(results)} completed runs from {res_path}")
        except Exception as e:
            print(f"[resume] could not read existing results ({e}); starting fresh")
            results = []
    done = {key(r["cfg"]["task"], r["cfg"]["pe"], r["cfg"]["post_attn_ln"], r["cfg"]["seed"],
                r["cfg"].get("attn_scale", "none")) for r in results}

    # Direction B: when an attention intervention is set, run LN-off only (we test the attention fix, not LN)
    ln_opts = (0,) if args.attn_scale != "none" else (0, 1)
    plan = [(task, pe, ln, seed) for task in tasks for pe in ("nope", "rope")
            for ln in ln_opts for seed in seeds]
    ncfg = len(plan)
    for i, (task, pe, ln, seed) in enumerate(plan, 1):
        if key(task, pe, ln, seed, args.attn_scale) in done:
            print(f"[skip {i}/{ncfg}] {task} pe={pe} ln={ln} seed={seed} scale={args.attn_scale} (done)")
            continue
        tk = TASKS[task]
        cfg = Cfg(task=task, pe=pe, post_attn_ln=bool(ln), seed=seed, steps=steps,
                  attn_scale=args.attn_scale, attn_ref=args.attn_ref,
                  vocab=tk["vocab"], pad=tk["pad"], **base)
        results.append(train_one(cfg))
        # LOG-RECOVERY: dump the full record (cfg + ladder + pre/post variance) as ONE json line to
        # stdout, so if the file save is ever lost (unmounted Drive, recycled VM) the console log alone
        # is enough to reconstruct everything. Grep 'RESULTJSON ' from the console to recover.
        print("RESULTJSON " + json.dumps(results[-1]), flush=True)
        save(results)  # incremental: a disconnect keeps every completed run
        print(f"[progress {i}/{ncfg}] done + saved ({len(results)} total). "
              f"(full record dumped above for log-recovery)", flush=True)
    summarize(results)
    print(f"\nsaved: {res_path}, {csv_path}")


if __name__ == "__main__":
    main()
