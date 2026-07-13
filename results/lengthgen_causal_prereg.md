# Pre-Registration: What actually drives length-gen failure? (Direction A)

Locked 2026-07-11, before running the causal-observable experiment.

## Motivation
We showed attention-output variance is a symptom: stabilizing it (post-attn LN, downstream var ~1.0)
does not improve length generalization. Direction A asks what the operative cause IS, for the
order-invariant retrieval tasks (argmax, flagret) where we can ground-truth the mechanism.

## Candidate cause (pre-specified)
**Attention dispersion off the correct source.** For flagret/argmax we know the input position holding
the answer value (target_idx). We measure, per layer, at the answer-query position (the position whose
prediction is the answer):
  - `attn_tgt`   = attention mass on target_idx (max over heads, mean over examples)
  - `attn_ent`   = normalized attention entropy (entropy / log(seq_len)) at that position
  - `attn_max`   = max attention weight (sharpness) at that position
across the length ladder, baseline (fix off) and with the fix.

## Pre-registered hypotheses
- **H-A1 (cause):** in the baseline, `attn_tgt` FALLS with length and its fall TRACKS the per-token
  accuracy fall (high within-cell correlation across lengths, |r| >= 0.8 pooled), i.e. losing attention
  on the correct source explains the failure.
- **H-A2 (variance is not it):** the variance-collapse ratio does NOT track accuracy as well as
  `attn_tgt` does (attn_tgt is the better predictor; report both correlations).
- **H-A3 (fix doesn't fix the cause):** post-attn LN does not restore `attn_tgt` at long length
  (consistent with it not restoring accuracy), even though it stabilizes variance.

## Decision / interpretation
- If H-A1 + H-A2 hold: we have a positive mechanism claim -- attention dispersion (not variance) is the
  driver. This becomes the sequel's core, and motivates Direction B (intervene on attention sharpness).
- If attn_tgt also fails to track accuracy: the cause is elsewhere (e.g. positional extrapolation / MLP
  readout); report honestly and widen the observable set.
- Metric window: correlations computed over the length ladder where the baseline is informative
  (train-len em >= 0.8), pooled across the order-invariant cells.

## Compute
Adds a cheap per-layer attention observable to eval; requires re-running argmax+flagret on GPU
(same ~16-32 run cost). recall/addition report attn_tgt=n/a (recall untrained; addition not a copy task).
