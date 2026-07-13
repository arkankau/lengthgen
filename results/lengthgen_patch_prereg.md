# Pre-Registration: direct attention-patching causal test

Locked 2026-07-13, before running on GPU. Mechanism validated on a CPU smoke (2L/64) that reproduced the
predicted signatures; the GPU run is the pre-registered test at the paper's scale.

## Premise
Directions A (correlation, r=0.97) and the sharpening intervention (r=1.0 tracking) show attention on the
correct source predicts and moves with accuracy, but sharpening is an INDIRECT lever (it changes logits).
This test manipulates the operative variable DIRECTLY: at eval, overwrite the attention distribution at the
answer-query position (length_gen_colab.py PATCH hook) to place mass p on the correct source, holding the
trained weights fixed. We patch the model's own retrieval layer L* (argmax baseline attention-on-source).

## Sweeps (at long test length L in {100, 250}; 4L/256; argmax+flagret x nope+rope x 4 seeds)
- **P** (k = all valid keys): sweep p. Accuracy vs FORCED a_j*. Here ||a||^2 (hence Var(z), Prop 1) co-moves.
- **FIXVAR** (target ||a||^2 = C = 0.25; k = round((1-p)^2/(C-p^2))): sweep p. Accuracy vs a_j* at CONSTANT
  variance. THE KEY DISSOCIATION.
- **FIXP** (p = 0.3 fixed; vary k in {2,4,8,16,32,64}): accuracy vs variance at FIXED a_j*.

We report, per patch point, the CONSTRUCTED ||a||^2 (controlled exactly) AND the MEASURED Var(z) at the
query (z_aq_var), plus the achieved a_j* (= mass on source, ~p).

## Pre-registered hypotheses
- **H-P1 (sufficiency):** in P, accuracy rises monotonically with a_j* and forcing a_j*->1 restores accuracy
  at a length where the baseline has dropped well below mastery.
- **H-P2 (dissociation, KEY):** in FIXVAR, accuracy still rises with a_j* while the variance is held ~constant
  -> selection controls accuracy even when variance is fixed.
- **H-P3 (variance null):** in FIXP, accuracy is ~flat as variance varies at fixed a_j* -> variance does not
  control accuracy when selection is fixed.

## Decision / interpretation
- H-P1 + H-P2 + H-P3 all hold -> DIRECT causal dissociation: attention selection is the operative variable and
  attention-output variance is not. This is the strongest form of the paper's claim and upgrades §6 from an
  indirect intervention to a direct manipulation. quantify: corr(accuracy, a_j*) in FIXVAR should be strongly
  positive; corr(accuracy, Var(z)) in FIXP should be near zero.
- H-P2 holds but H-P3 fails (accuracy also moves with variance at fixed a_j*) -> both matter; report honestly.
- H-P1 fails (forcing attention does not restore accuracy) -> the readout needs more than source attention at
  L*; report honestly, the correlational result stands but sufficiency does not.

## Honest caveats (pre-committed)
- The patch forces every head in L* to one distribution, an intervention that does not occur naturally; it
  tests SUFFICIENCY of source-attention and the variance-vs-selection dissociation, not the exact natural
  circuit.
- Under the iid-value model Var(z)=sigma^2 ||a||^2 (Prop 1); with real (correlated) values the measured
  Var(z) tracks ||a||^2 approximately, so FIXVAR holds variance APPROXIMATELY. The FIXP sweep is the clean
  complement (fix selection, vary variance directly).
- Single retrieval layer patched (L*); patching more layers is a robustness extension, not the primary test.

## Run
`python colab/patch_experiment.py --tasks argmax,flagret --seeds 0,1,2,3 --outdir /content/drive/MyDrive/lengthgen_patch`
-> patch_results.json. Analyze: scripts/analyze_patch.py. Runbook: colab/README_patch.md.

---

## OUTCOME (2026-07-13, run complete; 16 models 4L/256, analyzed at L=250)
Data: results/lengthgen/patch_results.json. Figure: results/lengthgen/fig_patch.pdf (2 clean panels).

- **H-P1 (sufficiency): SUPPORTED, strong.** Forcing attention onto the source restores per-token accuracy
  from baseline ~0.59 to ~0.99 (Sweep-P pooled 0.569 at a_j*~0 -> 0.986 at a_j*~1); 15/16 cells reach ~1.0,
  the lone exception argmax/rope/seed2 -> 0.83 (the same RoPE-argmax cell that resisted sharpening; it
  patched a worse layer L*=3). Direct causal SUFFICIENCY of attention-on-source.
- **H-P2 (accuracy tracks selection): SUPPORTED.** FIXVAR corr(acc, a_j*) = +0.89 pooled (flagret +0.95,
  argmax +0.83); accuracy 0.585 -> 0.935 as a_j* 0.05 -> 0.48. CAVEAT: the "constant variance" framing is
  APPROXIMATE -- the constructed ||a||^2 is pinned but MEASURED Var(z) still drifts 3x (flagret) to 6x
  (argmax), because the source value vector is not exchangeable with distractors. So this shows selection
  drives accuracy, not cleanly "at fixed measured variance".
- **H-P3 (variance null): NOT clean.** FIXP pooled corr(acc, Var(z)) = -0.02 but this is a CANCELLATION:
  per-task argmax=+0.64, flagret=-0.73 (opposite signs). FIXP's variance axis is confounded with the
  source-vs-distractor margin (varying k changes whether the source dominates), so it does NOT isolate
  variance-at-fixed-selection. Do not claim variance irrelevance from FIXP.

VERDICT: DIRECT CAUSAL SUFFICIENCY (H-P1 + H-P2). This upgrades the paper's causal leg from the INDIRECT
sharpening lever to a DIRECT manipulation: patching the attention distribution onto the source restores
accuracy, and accuracy rises with the patched selection. Honest limits carried to the paper: variance is
held only approximately (H-P2) and FIXP does not cleanly isolate it (H-P3), so we report sufficiency of
selection, not a clean "variance is causally inert" claim.
