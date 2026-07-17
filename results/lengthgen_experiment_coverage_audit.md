# Length-Gen Experiment Coverage Audit

This is a CPU-only audit generated from existing files.
It identifies what evidence is already present and which experiments are still reviewer-relevant.

## Current Coverage

| evidence block | status | artifact detail | paper role |
| --- | --- | --- | --- |
| Main scratch grid | complete | 48 configs; 4 seeds; tasks=argmax,flagret | Core correlation and variance-fix dissociation. |
| Causal sharpening | complete | 16 configs; 4 seeds; tasks=argmax,flagret | Intervention that raises attention-on-source. |
| Direct patching | complete | present | Sufficiency test for selection. |
| Pretrained Pythia probe | complete | 1 Pythia row; 900 examples | First pretrained-model external-validity result. |
| Model-family robustness | complete | Qwen/Qwen2.5-1.5B (heads 4,8,16), google/gemma-2-2b (heads 8) | Tests the mechanism outside the Pythia family. |
| Real-model head-count robustness | complete | Qwen/Qwen2.5-1.5B | Checks that retrieval-head selection is not tuned to one K. |
| Fixed-spectrum assignment grid | complete | 16 configs; 4 seeds; tasks=argmax,flagret | Core spectrum-preserving source assignment and head-dose test. |
| Capacity-by-assignment factorial | complete | 16 configs; 4 seeds; tasks=argmax,flagret | Direct test of the capacity--assignment interaction. |
| Two-evidence fixed-spectrum routing | complete | 8 models; min train exact=1.000 | Extends the set-valued law to a learned two-input computation. |
| Pretrained causal backend | validated | EleutherAI/pythia-1.4b, EleutherAI/pythia-70m, Qwen/Qwen2.5-1.5B, Qwen/Qwen2.5-7B, google/gemma-2-2b | Fixed-spectrum intervention works inside pretrained attention implementations. |
| Paper-grade pretrained causal grid | complete | competent N>=128 model | Needed before claiming a causal pretrained-model result. |
| Pretrained utility-gap audit | complete | 9 model families; two lengths; 64 examples/cell | Tests the nonlinear theorem's local utility term in pretrained models. |
| Causal selection robustness | complete | 9/9 selected intervals exclude zero | Checks independent splits, three seeds, K=2/4/8, and layer controls. |
| Second prompt format | failed competence | equals-newline at N=5,20; N=80 runtime-limited | External-validity boundary; causal direction is not claimed without competence. |
| 8-layer/512-width replication | complete | 32 configs; 4 seeds; tasks=argmax,flagret | Scale objection reducer; verify completeness before relying on it. |
| Natural context-grounded QA | complete | 3 competent seeds; full-size seeds=[0, 1, 2] | Tests whether source-conditioned routing survives natural language and free answer choice. |
| Natural-QA length ladder | boundary result | Qwen full seeds=[0, 2]; SmolLM full seeds=[0]; preregistered mechanism failed | Tests whether the fixed-context natural-QA effect explains length degradation. |
| Cross-family selector ablation | complete | 3 complete families; claim=heterogeneous_or_incomplete | Separates a general output-conditioned principle from a universal selector formula. |
| Interpolation dose response | complete | 5 seeds; alphas=[0.0, 0.25, 0.5, 0.75, 1.0] | Checks that routing effects vary smoothly rather than appearing only at a maximal rewrite. |
| Three-/four-evidence routing | boundary result | complete grid; largest capacity search reaches exact match 0.748 | Tests whether the set-valued routing account scales beyond two required sources. |

## Real-Model Rows Available Now

| model | heads | examples | acc drop | attn drop | corr attn | corr normsq | corr -entropy | winner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EleutherAI/pythia-1.4b | 8 | 900 | 0.493 | 0.259 | 0.194 | 0.122 | 0.100 | attn |
| Qwen/Qwen2.5-1.5B | 4 | 900 | 0.760 | 0.370 | 0.219 | 0.214 | 0.231 | neg_entropy |
| Qwen/Qwen2.5-1.5B | 8 | 900 | 0.760 | 0.356 | 0.268 | 0.223 | 0.248 | attn |
| Qwen/Qwen2.5-1.5B | 16 | 900 | 0.760 | 0.295 | 0.317 | 0.176 | 0.246 | attn |
| google/gemma-2-2b | 8 | 900 | -0.007 | 0.250 | 0.346 | 0.268 | 0.238 | attn |

## Experiment Queue

| priority | experiment | needs | reason |
| --- | --- | --- | --- |
| done | Two-evidence modular-sum grid | 8 models; 256 paired examples/cell | Closes the single-source copying objection for one learned two-input task. |
| done | Pretrained fixed-spectrum backend validation | Pythia-70M and Qwen2.5-1.5B | Confirms the intervention and invariant checks run on two real architectures. |
| done | Competent pretrained causal family grid | Qwen, Pythia, Gemma | Complete with paired intervals and explicit competence boundaries. |
| done | Qwen2.5-7B fixed-spectrum run | NF4/bfloat16; 96 examples/cell | Adds a within-family scale replication. |
| done | Qwen/Qwen2.5-1.5B real-model run | 900 examples | Replicates the co-decline outside Pythia. |
| done | Gemma-2-2B real-model run | 900 examples | Adds a mixed third-family boundary result. |
| done | Head-count robustness on best non-Pythia model | Qwen K=4,8,16 | Source-attention co-decline holds across all three head counts. |
| done | 8-layer/512-width scratch replication | 32 configs; four seeds | Replicates the controlled result at larger scratch-model scale. |
| done | Natural context-grounded multiple-choice QA | Qwen; three seeds; 64 calibration/128 evaluation | Passes the locked context-necessity and hierarchical-effect rules. |
| done | Cross-family selector ablation | Qwen, Pythia, SmolLM2; three seeds each | Supports output-conditioned selection but rejects a unique universal selector ranking. |
| done | Interpolation dose response | SmolLM2; five seeds; five alpha values | Shows a smooth monotone causal response from no patch to the full patch. |
| done: boundary | Three-/four-evidence routing | NoPE/RoPE; seeds 0,1; pair/triple/quad | Triple effect includes zero and quadruple models fail competence. |
| done | Full-size natural-QA confirmation | 64 calibration/128 evaluation; three seeds | Upgrades the replicated pilot into a positive locked confirmatory result. |
| done: boundary | Natural-QA nested length ladder | Qwen seeds 0,2; SmolLM2 seed 0; 4/8/16/32 passages | Length degrades margin and accuracy, but the preregistered source-mass/rescue mechanism fails. |
| done: boundary | Competence-matched four-evidence search | c1/c2/c3; frozen exact-match threshold 0.8 | No candidate clears competence; c3 reaches 0.748 and no causal contrast is interpreted. |
| can | Additional seeds for loglen sharpening | GPU | Strengthens the intervention estimate. |
| can | Direct patching at multiple long lengths | GPU | Makes the sufficiency result cleaner. |
| now | Claim and artifact audit | CPU | Keeps the paper aligned with completed evidence. |

## Immediate Interpretation

- The central controlled evidence, fixed-spectrum test, and capacity-by-assignment factorial are complete.
- The two-evidence task is complete: all eight models pass the competence gate, and at 5x length evidence-max exceeds the evidence-mass-preserving control by +0.043 with 95% interval [0.017, 0.072].
- The pretrained fixed-spectrum backend is validated on Pythia and Qwen with invariant error below 1e-6.
- The paper-grade pretrained causal grid is complete on Qwen2.5 at two scales, Pythia-1.4B, and Gemma-2-2B.
- The pretrained utility-gap term has positive source-max association in all six model-length cells across three architectures.
- Qwen circuit selection is robust across independent splits, three seeds, and K=2/4/8; all nine selected paired margin intervals exclude zero.
- The preregistered equals-sign format fails the competence gate at the two completed lengths, so second-format generalization remains open.
- The accuracy/source-attention co-decline reproduces on Pythia-1.4B and Qwen2.5-1.5B.
- On Qwen, accuracy and source attention decline at K=4, 8, and 16; attention is the best within-length predictor at K=8 and 16 and narrowly trails negative entropy at K=4.
- Gemma-2-2B is a mixed boundary case: source attention declines with length while accuracy remains near 0.5, but source attention is the strongest within-length correctness predictor at every tested length.
- Natural multiple-choice QA passes the locked 64/128 design on all three seeds: utility-selected source assignment beats the matched control by +0.336 margin, with hierarchical 95% interval [0.176, 0.512], while source-mass selection is -0.112 [-0.188, -0.043].
- The nested natural-QA length ladder is a boundary result: Qwen and SmolLM2 both lose margin and accuracy from 4 to 32 passages, but Qwen source mass rises and rescue weakens while SmolLM2 source mass falls without increasing rescue.
- Equal-budget selector ablations are complete on Qwen, Pythia, and SmolLM2. Utility gain ranks first on two families and ties an equivalent circuit on Qwen, so the evidence supports output-conditioned selection but not a unique universal ranking formula.
- The five-seed interpolation audit passes its preregistered rule: the matched-control margin effect rises monotonically from +0.000 at alpha=0 to +1.417 at alpha=1.
- The pair/triple/quad stage is complete and sets a boundary: pair and triple models are train-competent, but the triple max-control interval includes zero; quadruple evidence fails the competence gate (minimum train exact match 0.090).
- The outcome-blind capacity search does not close the four-evidence competence gap: c3 reaches 0.748 exact match against the frozen 0.8 threshold, so no four-source causal intervention is interpreted.
- The previously critical natural-QA and evidence-arity GPU gaps are now closed; neither requires another sweep for the present claims.
- Closed GPT-style APIs are not substitutes for this experiment because they do not expose attention weights or hidden states.
