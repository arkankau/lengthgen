# Length Generalization Project Context

This is the current handoff context for the length-generalization work in this repo.

Repo: https://github.com/arkankau/lengthgen

Local root: `thermo-safety/`.

The length-generalization work is the active focus.

Do not invent results or citations.

Everything below is verified.

## Paper

Title: "Selection over Scale in Transformer Length Generalization".

Location: `paper_lengthgen_aaai/main.tex`.

The paper uses AAAI 2027 style files: `aaai2027.sty`, `aaai2027.bst`, and natbib `\citep`.

`references.bib` has 14 entries.

All bibliography entries are verified against arXiv.

All bibliography entries are cited.

The thesis is positive and non-adversarial.

The internal property that supports length generalization on retrieval is attention staying concentrated on the token holding the answer.

This is "attention on the correct source".

Attention-output variance is a co-varying symptom.

Attention-output variance is not the controlling variable.

The paper never argues that another paper is wrong.

The variance account from Li et al., arXiv:2504.02827, is cited neutrally as one candidate account that we measured.

## Evidence

All evidence uses 4-layer decoder transformers with `d_model=256`.

Training length is 1 to 5.

Evaluation goes to 50x length, equal to length 250.

Correlational evidence:

Attention-on-correct-source predicts per-token accuracy with within-cell `r=0.97`.

Attention-on-correct-source predicts per-token accuracy with pooled `r=0.94`.

Attention-output variance predicts per-token accuracy worse, with within-cell `r=0.59`.

Attention-output variance predicts per-token accuracy worse, with pooled `r=0.45`.

Variance intervention evidence:

The variance intervention is post-attention LayerNorm.

It provably holds downstream variance constant.

It does not improve length generalization.

The paired benefit is `<=0` in all cells.

It lowers accuracy under RoPE.

Interventional causal-control evidence:

Length-scaled logit sharpening is SSMax-style.

The setting is `loglen` with `ref=6`.

It raises attention-on-source and accuracy in proportion.

Across the 4 task-by-positional-encoding cells, the accuracy gain tracks the attention gain at `r=+1.0`.

The variance fix raises neither attention-on-source nor accuracy.

The verdict is partial.

Only `argmax/NoPE` clears the pre-registered `+0.05` bar.

`argmax/NoPE` gives `+0.083` across `4/4` seeds.

`argmax/RoPE` is the one cell where attention did not rise and accuracy did not improve.

This is consistent with the account.

Math evidence:

Section 5 contains Proposition 1 and Proposition 2.

Proposition 1 states `Var(z)=sigma^2/n_eff`.

Attention-output variance is inverse participation ratio.

It collapses whenever attention disperses, for right or wrong selection.

Proposition 2 states that softmax weight on the correct source decays with length unless the logit gap grows like `log n`.

This motivates the `loglen` intervention.

Both propositions are framed as elementary or known.

They are not claimed as novel.

## Positioning

This is a workshop or findings-tier paper.

The novelty is the direct ground-truthed measurement, the controlled dissociation, and the matched intervention.

The novelty is not the thesis that attention concentration matters.

The novelty is not the math.

## Key Files

Trainer:

`colab/length_gen_colab.py`

The trainer is self-contained and intended to run on GPU.

Important flags:

`--tasks`

`--seeds`

`--attn-scale {none|loglen|fixedK}`

`--attn-ref`

`--n-layers`

`--d-model`

`--batch`

`--outdir`

Tasks:

`argmax`: argmax retrieval.

`flagret`: flag retrieval.

`addition`: reversed decimal, order-dependent contrast.

`recall`: untrained.

Analysis scripts:

`scripts/analyze_lengthgen_json.py`

`scripts/analyze_causal.py`

`scripts/analyze_causalB.py`

Figures:

`scripts/make_lengthgen_paper_figures.py`

`scripts/make_lengthgen_causalB_figure.py`

Utilities:

`scripts/merge_lengthgen_json.py`

`scripts/recover_from_log.py`

Data:

`results/lengthgen/gpu_resultsA.json`

This contains baseline plus variance-fix results, 32 configs, 4 seeds.

`results/lengthgen/gpu_resultsB.json`

This contains loglen results, 16 configs.

`results/lengthgen/gpu_resultsAB.json`

This contains the merged 48 configs.

`results/lengthgen/gpu_results.json`

This contains 40 configs, including addition.

Pre-registrations:

`results/lengthgen_preregistration.md`

`results/lengthgen_causal_prereg.md`

`results/lengthgen_causalB_prereg.md`

`results/lengthgen_causalB_prereg.md` has the outcome.

## Hard Conventions

Matplotlib lives only in `.venv/Scripts/python.exe`.

Matplotlib does not live in system Python.

Run all plotting scripts with the venv Python.

Writing style is plain declarative sentences.

Use one sentence per source line.

Use concrete numbers.

Use careful hedging.

Do not use em dashes.

Do not use `---`.

Do not use constructions of the form `X, not Y`, `not X but Y`, or `X rather than Y`.

Do not use the openers `Moreover`, `Furthermore`, `Notably`, or `Crucially`.

Use no adversarial framing.

Figures are single-column `\begin{figure}[H]` at `\columnwidth`.

The paper uses the `float` package.

Do not use `figure*`.

`figure*` bunches floats at page ends.

The trainer resume key is `(task, pe, post_attn_ln, seed, attn_scale)`.

The trainer resume key does not include model size.

Any different-size run must use a fresh `--outdir`.

LaTeX cannot be compiled locally.

The paper compiles on Overleaf.

## Next Steps

GPU runs are hand-offs.

The user runs them on Colab.

Codex should prep and analyze.

Highest value next step:

Scale confirmation at 8 layers and `d_model=512`.

Command:

```powershell
python colab/length_gen_colab.py --tasks argmax,flagret --seeds 0,1,2,3 --n-layers 8 --d-model 512 --batch 256 --outdir <fresh_dir>
```

After the run, analyze with:

`scripts/analyze_lengthgen_json.py`

`scripts/analyze_causal.py`

Check that the three claims still hold.

The first claim is that variance collapses.

The second claim is that attention-on-source predicts accuracy.

The third claim is that the variance fix stays `<=0`.

This blunts the "toy model" reviewer critique.

Prep the exact analysis and a figure that overlays 4L versus 8L.

Second next step:

Add statistical rigor.

Add a script that computes a paired sign test and bootstrap confidence intervals for per-seed benefits.

Replace "negative in 4/4 seeds" language with p-values and confidence intervals.

Use data in `results/lengthgen/gpu_resultsAB.json`.

Third next step:

Add a task-schematic figure for the Setup section.

Show token layouts for `argmax`, `flagret`, and `addition`.

Mark the answer-query position.

Mark the correct-source position.

Fourth next step:

Write a top-level `README.md` that leads with this paper.

The current `README.md` is the older thermo-safety one.

The repo front page does not mention the length-generalization work.

Fifth next step:

Fill `paper_lengthgen_aaai/ReproducibilityChecklist.tex`.

Check the page budget for the target venue.

## First Files To Read Before Continuing

Read `paper_lengthgen_aaai/main.tex`.

Read `paper_lengthgen_aaai/README.md`.

Read `results/lengthgen_causalB_prereg.md`.

After reading those files, confirm this brief.

Then propose which next step to take.
