# Pre-Registration: real-model generalization probe

Locked 2026-07-13, before the GPU run. Pipeline validated on a CPU smoke (pythia-70m): pool, task, eager
attentions, source extraction, accuracy, and correlations all run (the 70m model is too weak for recall, so
the smoke was a plumbing check, not a result).

## Premise
The paper's finding is on toy transformers trained from scratch. This probe asks whether the operative
variable generalizes to a REAL pretrained LM: in an in-context retrieval task, does attention on the correct
source predict retrieval accuracy, and does it fall with context length as accuracy fails?

## Task and measurements
In-context key-value recall: sequence `[k1 v1 k2 v2 ... kN vN kq]` with kq a repeat of one ki; the model
should predict the matching vq. Keys/values are single-token ids, so accuracy = (argmax next-token == vq).
The correct source is the known position of vq. We vary N (number of pairs = context length). At the query
token, from the attention weights alone (attn_implementation='eager'):
- **attention on source** a_j* = max over layers,heads of attn(query -> vq position).
- **variance candidate** ||a||^2 = mean over layers,heads of sum_s a_s^2. By Proposition 1 this equals the
  attention-output variance up to a constant, so it is the model-agnostic analog of the paper's variance
  candidate (no per-architecture hooks). Higher ||a||^2 = higher attention-output variance.
- **attention entropy** (a second dispersion summary).

## Pre-registered hypotheses
- **H-R1 (co-decline):** as N grows, accuracy falls AND attention-on-source falls, i.e. the real model's
  length-gen failure localizes to attention dispersing off the correct source.
- **H-R2 (predictor, WITHIN length):** at a fixed N, attention-on-source predicts which examples are correct
  (positive point-biserial correlation), and predicts better than ||a||^2 and than -entropy. Within-length
  is the honest test: a pooled correlation across N is inflated because accuracy and attention both fall
  with N.

## Decision / interpretation
- H-R1 + H-R2 hold -> the account GENERALIZES from toy transformers to a real pretrained LM: attention on the
  correct source is the operative variable there too, and the variance/dispersion summaries predict less.
  Strongest external-validity evidence; add fig_realmodel and a paragraph.
- H-R1 holds, H-R2 mixed -> the length-gen failure still localizes to attention dispersion, but the
  within-example discrimination is weaker; report honestly.
- Neither -> the toy result may not transfer; report honestly, do not bury.

## Honest caveats (pre-committed)
- The base model must have DYNAMIC RANGE (accuracy spanning high at short N to low at long N). A model too
  weak (accuracy ~0 everywhere) or too strong (perfect everywhere) is uninformative. Use pythia-1.4b or
  larger; if accuracy has no range, escalate the model or the length ladder before interpreting.
- Raw induction-format task (no natural-language framing); tests the retrieval mechanism, not task phrasing.
- The variance candidate is ||a||^2 (participation), justified as the attention-output variance by Prop 1,
  not the raw hidden-state variance; stated as such.
- Within-length correlation is the primary H-R2 statistic; the pooled correlation is reported only for
  reference and is expected to be inflated.

## Run
`python colab/real_model_probe.py --model EleutherAI/pythia-1.4b --lengths 5,10,20,40,80,160 --n 150
--outdir /content/drive/MyDrive/lengthgen_realmodel` -> realmodel_results.json.
Analyze: scripts/analyze_real_model.py. Runbook: colab/README_realmodel.md.

---

## AMENDMENT 1 -- v2 redesign (2026-07-13, after the v1 run was inconclusive)

The v1 run on pythia-1.4b was INCONCLUSIVE for two reasons, both anticipated by the caveats above:
(a) the raw interleaved format gave the model almost no task competence (acc 0.25 at N=5), and (b) the
attention-on-source measurement (max over 384 head-layers) SATURATED at ~0.9 at every length, so it had no
variance to correlate with (restricted range). So v1 neither supported nor cleanly refuted the account.

v2 fixes both, and is re-pre-registered here BEFORE the v2 GPU run:
1. **Natural format.** Each pair is rendered in token space as `key : value \n` (pool tokens carry a leading
   space, decoding to " apple: banana\n"); the query line is `kq :`. On a CPU smoke this took pythia-70m from
   acc 0.00 (v1 raw format) to acc 0.75 at short N -- real task competence and dynamic range.
2. **Retrieval-head measurement.** We identify the retrieval heads ONCE, correctness-independently, as the
   top-K (default 8) layer-head pairs by mean query->source attention at the SHORTEST length, then measure
   THOSE heads across the sweep (mean attention-on-source, mean ||a||^2, mean entropy). This replaces the
   saturating max-over-all-heads. We also keep max-over-all-heads (a_js_max) for reference.

Re-pre-registered hypotheses (unchanged in spirit):
- **H-R1:** accuracy AND retrieval-head attention-on-source both fall with N.
- **H-R2 (WITHIN length):** retrieval-head attention-on-source predicts correctness, better than the
  retrieval-head ||a||^2 variance proxy and than -entropy.

Honest notes: identifying heads at the shortest length then testing at longer lengths limits circularity
(selection is correctness-independent and out-of-distribution from the tested lengths); we report a_js_max
alongside so readers see the saturation. If pythia-1.4b's accuracy ceiling is still low, escalate the model
(pythia-2.8b/6.9b) before interpreting. CPU smoke (pythia-70m): pooled corr(acc, retrieval-head a_j*)=+0.66
vs ||a||^2 +0.47 -- promising, but the real verdict is the 1.4b run analyzed WITHIN length.
