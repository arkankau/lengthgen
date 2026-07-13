"""Grokking trainer with per-checkpoint thermodynamic observables (Direction E, see .claude/loop.md).

A tiny 1-layer transformer learns modular addition (a + b) mod p. With high weight decay it "groks":
train accuracy saturates early, validation accuracy jumps much later -- a known, sharp phase
transition. At each checkpoint we log train/val accuracy AND thermodynamic observables of the model,
so a downstream verifier can ask whether the transition leaves a thermodynamic fingerprint.

Observables logged:
  - attn_specific_heat, attn_entropy : energy-fluctuation / entropy of attention (our tools)
  - repr_participation_ratio         : effective dimensionality of the '=' representation over a batch
  - weight_spectral_entropy          : spectral (effective-rank) entropy of the unembedding matrix

This is a self-contained PyTorch training run; nothing else in the repo trains models.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def build_model(torch, nn, vocab: int, d_model: int, n_heads: int, d_mlp: int, n_ctx: int, seed: int):
    gen = torch.Generator().manual_seed(seed)

    class TinyTransformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.d_model, self.n_heads = d_model, n_heads
            self.d_head = d_model // n_heads
            self.embed = nn.Embedding(vocab, d_model)
            self.pos = nn.Parameter(torch.randn(n_ctx, d_model, generator=gen) * 0.02)
            self.W_Q = nn.Linear(d_model, d_model, bias=False)
            self.W_K = nn.Linear(d_model, d_model, bias=False)
            self.W_V = nn.Linear(d_model, d_model, bias=False)
            self.W_O = nn.Linear(d_model, d_model, bias=False)
            self.W_in = nn.Linear(d_model, d_mlp)
            self.W_out = nn.Linear(d_mlp, d_model)
            self.unembed = nn.Linear(d_model, vocab, bias=False)

        def forward(self, x):
            b, t = x.shape
            h = self.embed(x) + self.pos[None, :t, :]
            q = self.W_Q(h).view(b, t, self.n_heads, self.d_head).transpose(1, 2)
            k = self.W_K(h).view(b, t, self.n_heads, self.d_head).transpose(1, 2)
            v = self.W_V(h).view(b, t, self.n_heads, self.d_head).transpose(1, 2)
            scores = (q @ k.transpose(-1, -2)) / (self.d_head ** 0.5)
            attn = torch.softmax(scores, dim=-1)  # (b, heads, t, t)
            z = (attn @ v).transpose(1, 2).reshape(b, t, self.d_model)
            h = h + self.W_O(z)
            mlp_hidden = torch.relu(self.W_in(h))
            h = h + self.W_out(mlp_hidden)
            logits = self.unembed(h)
            return logits, attn, h

    return TinyTransformer()


def make_data(torch, p: int, train_frac: float, seed: int):
    a = torch.arange(p).repeat_interleave(p)
    b = torch.arange(p).repeat(p)
    eq = torch.full_like(a, p)  # '=' token id = p
    x = torch.stack([a, b, eq], dim=1)
    y = (a + b) % p
    n = x.shape[0]
    g = torch.Generator().manual_seed(seed)
    perm = torch.randperm(n, generator=g)
    n_tr = int(train_frac * n)
    tr, te = perm[:n_tr], perm[n_tr:]
    return x[tr], y[tr], x[te], y[te]


def participation_ratio(H: np.ndarray) -> float:
    """Effective dimensionality of a representation matrix (n, d): (sum lam)^2 / sum lam^2."""
    H = H - H.mean(axis=0, keepdims=True)
    cov = H.T @ H / max(1, H.shape[0])
    lam = np.linalg.eigvalsh(cov)
    lam = np.clip(lam, 0, None)
    s1 = lam.sum()
    s2 = (lam * lam).sum()
    return float(s1 * s1 / s2) if s2 > 0 else 0.0


def spectral_entropy(W: np.ndarray) -> float:
    """Shannon entropy of the normalized singular-value spectrum (effective rank, in nats)."""
    s = np.linalg.svd(W, compute_uv=False)
    s = s / s.sum() if s.sum() > 0 else s
    s = np.clip(s, 1e-12, 1.0)
    return float(-(s * np.log(s)).sum())


def main() -> None:
    ap = argparse.ArgumentParser(description="Grokking trainer with thermodynamic observables.")
    ap.add_argument("--p", type=int, default=97)
    ap.add_argument("--train-frac", type=float, default=0.4)
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--n-heads", type=int, default=4)
    ap.add_argument("--d-mlp", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1.0)
    ap.add_argument("--steps", type=int, default=30000)
    ap.add_argument("--log-every", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output", default="results/grok_log.csv")
    args = ap.parse_args()

    import torch
    from torch import nn

    torch.manual_seed(args.seed)
    vocab = args.p + 1
    model = build_model(torch, nn, vocab, args.d_model, args.n_heads, args.d_mlp, 3, args.seed)
    x_tr, y_tr, x_te, y_te = make_data(torch, args.p, args.train_frac, args.seed)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay, betas=(0.9, 0.98))
    loss_fn = nn.CrossEntropyLoss()
    probe = x_te[: min(512, x_te.shape[0])]

    from thermosafety.thermo_observables import layer_observables

    rows = []
    for step in range(args.steps + 1):
        model.train()
        logits, _, _ = model(x_tr)
        loss = loss_fn(logits[:, -1, :], y_tr)
        opt.zero_grad(); loss.backward(); opt.step()

        if step % args.log_every == 0:
            model.eval()
            with torch.no_grad():
                tr_logits, _, _ = model(x_tr)
                te_logits, attn, h = model(probe)
                tr_acc = (tr_logits[:, -1, :].argmax(-1) == y_tr).float().mean().item()
                te_acc = (te_logits[:, -1, :].argmax(-1) == y_te[: probe.shape[0]]).float().mean().item()
                # attention observables at the '=' (last) query position, averaged over batch
                # layer_observables expects (heads, q, k); build (heads, 1, keys) at the '=' query
                a3 = attn[:, :, -1, :].mean(dim=0).unsqueeze(1).cpu().numpy()  # (heads, 1, keys)
                oo = layer_observables(a3)
                pr = participation_ratio(h[:, -1, :].cpu().numpy())
                se = spectral_entropy(model.unembed.weight.detach().cpu().numpy())
            rows.append({
                "step": step, "train_acc": round(tr_acc, 4), "val_acc": round(te_acc, 4),
                "attn_specific_heat": round(oo["specific_heat"], 6), "attn_entropy": round(oo["entropy"], 6),
                "repr_participation_ratio": round(pr, 4), "weight_spectral_entropy": round(se, 6),
            })
            print(f"step {step:6d} | train {tr_acc:.3f} val {te_acc:.3f} | "
                  f"C_attn {oo['specific_heat']:.4f} H_attn {oo['entropy']:.4f} PR {pr:.2f} Sspec {se:.4f}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} checkpoints to {args.output}")


if __name__ == "__main__":
    main()
