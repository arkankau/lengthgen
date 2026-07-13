# Pilot: Arrow of Time Across Transformer Depth -- NEGATIVE (pre-registered)

Source: `thermosafety/irreversibility.py` (validated on synthetic reversible/irreversible processes,
6 unit tests), `scripts/pilot_irreversibility.py`, `results/irreversibility_profile.csv`.
Qwen2.5-0.5B-Instruct, 247 token-trajectories x 25 layers, standardized, k=20 PCA, fixed basis.

Pre-registered kill conditions (coded before the run): K1 real & non-flat above a null; K2 not
redundant with representation change. Verdict computed automatically.

## Result

- **K1 FAILED** (0/24 depths exceed the null CI). Caveat: the depth-shuffle null was mis-designed --
  permuting depth pairs far-apart layers, whose cross-covariance is almost entirely antisymmetric
  (null fraction ~1.97 at every depth), so the test could not fire. This is an error in the null, not
  a positive result hidden by it.
- **K2 PASSED** (corr(irr, repr_change) = 0.028; irr peak at layer 2 vs repr_change peak at layer 23).
  Irreversibility is genuinely not a restatement of representation-change magnitude -- but this cannot
  rescue an absent signal.

## What the raw profile actually shows (honest reading, independent of the broken null)

The antisymmetric fraction of consecutive-layer cross-covariance is **near zero through the entire
bulk** of the network (~0.0003, i.e. ~0.03%), meaning **the residual stream evolves almost perfectly
reversibly from layer to layer in the middle of the model.** Irreversibility spikes only at:

- the first few layers (0->1 ~1.4, 2->3 ~1.6, 3->4 ~1.0): input encoding;
- the 21->22 transition (~1.4): the *already-known* compression-valley / attention-sink region we
  found in earlier diagnostics.

So even correcting the null, there is no rich, novel "arrow of time across depth". There is a
near-reversible bulk (arguably implied by residual-stream contractivity) plus boundary spikes that
coincide with structure we had already characterized. Not a novel, developable finding.

## Decision

Per pre-registration, this is NEGATIVE and we stop developing it. The candidate survived literature
vetting (nine searches, two deep reads) but failed the empirical pilot -- which is exactly what the
pilot-with-kill-condition was for. This is the discipline working as intended: it stopped us before a
paper was built on a non-signal.
