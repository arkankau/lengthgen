# Pre-Registration: decoupling attention-failure from readout-failure (direction A)

Locked 2026-07-13, BEFORE the GPU run. Plumbing validated on a CPU smoke (pythia-70m): logit-lens final-norm
found, retrieval heads calibrated, decomposition + instrument-sanity + threshold-robustness all run and the
figure writes. (70m is too weak to be a result; the smoke is a plumbing check.)

## Premise / the puzzle this closes
Our real-model probe (results/lengthgen_realmodel_prereg.md) showed accuracy and retrieval-head
attention-on-source co-decline, but attention on the source is still non-trivial (a_js ~= 0.22) where accuracy
is near the floor (0.19). So a question is open: is length-gen failure on recall ONLY attention dispersing off
the source, or is there a SECOND locus -- the value is not copied into the residual, or is copied then dropped
by later layers? The paper currently claims attention-on-source is THE operative variable; an honest
decomposition either confirms that (attention/copy dominate the failures) or refines it (a readout locus is
also present). Both outcomes are reportable.

## Instrument (no attention surgery; robust)
Same in-context key-value recall task as the real-model probe (Pythia-1.4B, eager attentions). At the query
token we record, per example:
- **a_js**: retrieval-head attention on the correct source (did attention REACH the source?).
- **vrank**: the BEST (min over layers) logit-lens rank of the correct value vq in the residual stream,
  logits_L = unembed(final_norm(hidden_L)) at the query position (was the value RETRIEVED into the residual?).
- **correct**: was vq actually OUTPUT?

## Decomposition (mutually exclusive, priority order)
Among the FAILURES (correct=0) at each length:
- **readout-limited**: vrank < V_THR (value was in the residual top-k) yet not output -> a second locus.
- **attention-limited**: value absent AND a_js < A_THR -> attention never reached the source (paper mechanism).
- **copy-limited**: value absent BUT a_js >= A_THR -> reached the source, OV did not write the value.

A_THR = median a_js among CORRECT examples at the shortest length ("healthy attention" reference).
V_THR = 10. Robustness reported over V_THR in {5,10,20} and A_THR in {0.5x, 1x}.

## Pre-registered hypotheses
- **H-D1 (instrument valid):** among CORRECT examples, a_js is high AND value-present (vrank<V_THR) is common
  (>~0.6). If the logit lens does not show the value on the cases the model gets right, the instrument is
  invalid and we stop.
- **H-D2 (decomposition shifts with length):** as N grows and accuracy falls, the failure mix moves. We
  pre-commit to reporting the mix at every N; the primary readout is the fraction of each locus at the LONGEST
  length.
- **H-D3 (which locus dominates):** we do NOT pre-commit to an outcome. Two honest readings:
  (a) attention-limited + copy-limited dominate (>~0.6 of long-N failures never wrote the value) -> the paper's
      attention-on-source mechanism carries the failure; the account is confirmed at finer grain.
  (b) readout-limited is substantial (>=0.25 of long-N failures) -> length-gen failure on recall has a SECOND
      locus (retrieved-then-dropped); the paper's claim is refined to "attention is necessary but not the whole
      story in a large model," which is a stronger, more novel decomposition than the current single-variable
      claim.

## Decision / how it enters the paper
- Outcome (a): add a short "Decomposing the failure" paragraph + fig_decouple to the real-model section,
  strengthening the mechanism claim with a finer-grained confirmation.
- Outcome (b): add the decomposition as a distinct finding -- length-gen recall failure splits into an
  attention locus and a readout locus, quantified -- and soften the single-variable framing accordingly. This
  is the higher-novelty result and we report it plainly, not buried.
- Either way: honest, pre-registered, and the instrument-validity gate (H-D1) must pass first.

## Honest caveats (pre-committed)
- The logit lens with the final norm is a standard but imperfect readout of intermediate residuals; a value
  "absent" from the lens may still be present in a form the lens does not surface. We therefore treat
  readout-limited as a LOWER bound on the second locus and copy/attention as possibly over-counted, and we say
  so.
- One model (Pythia-1.4B), one task. The decomposition characterizes THIS setting, not all models.
- A_THR is set from correct short-N examples; we report threshold robustness so the split is not an artifact of
  one cutoff.

## Run
`python colab/decouple_probe.py --model EleutherAI/pythia-1.4b --lengths 10,20,40,80,160 --n 150
--outdir /content/drive/MyDrive/lengthgen_decouple` -> decouple_results.json.
Analyze: `python scripts/analyze_decouple.py results/lengthgen/decouple_results.json`.
