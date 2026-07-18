# Runbook: direct attention-patching causal test

The definitive test of the paper's thesis ("selection over scale"): manipulate attention-on-source
DIRECTLY (not via a logit lever) and read the accuracy response, including at CONSTANT variance.

Pre-registration: `results/lengthgen_patch_prereg.md`. Mechanism validated on a CPU smoke (forcing
attention onto the source restored accuracy 0.56->1.00; at constant variance, accuracy rose 0.59->1.00 as
a_j* went 0.05->0.48).

## What it does
Trains baseline models (argmax+flagret x nope+rope x 4 seeds, 4L/256), then at eval overwrites the
attention row at the answer-query position in the model's retrieval layer L*, and runs three sweeps at
L in {100, 250}:
- **P**: force mass p on the source, spread the rest over all keys; sweep p (variance co-moves).
- **FIXVAR**: hold ||a||^2 (Var(z)) constant; sweep p -> accuracy vs selection at CONSTANT variance.
- **FIXP**: hold p fixed; vary the spread -> accuracy vs variance at FIXED selection.

## Step 1 - GPU run (Colab)
Runtime -> GPU. Mount Drive and VERIFY the mount, then put both files in the working dir:
```python
from google.colab import drive; drive.mount('/content/drive')
import os; assert os.path.isdir('/content/drive/MyDrive')
```
`length_gen_colab.py` must be next to `patch_experiment.py` (the script imports it).
```bash
!python patch_experiment.py --tasks argmax,flagret --seeds 0,1,2,3 \
    --outdir /content/drive/MyDrive/lengthgen_patch
```
- 16 models (train once each, ~4000 steps); patch evals are cheap.
- Saves `patch_results.json` incrementally, prints `RESULTJSON` per model, skips completed (task,pe,seed)
  on re-run after a disconnect.

## Step 2 - analyze (local)
Download to `results/lengthgen/patch_results.json`, then:
```bash
python scripts/analyze_patch.py results/lengthgen/patch_results.json
```
Prints the H-P1/H-P2/H-P3 verdict and writes `results/lengthgen/fig_patch.pdf` (three panels: force-selection,
selection-at-constant-variance, variance-at-fixed-selection).

## Expected outcome (from theory + smoke)
- **H-P1**: forcing a_j*->1 restores accuracy at long length.
- **H-P2 (key)**: accuracy rises with a_j* at constant variance -> corr(acc, a_j*) strongly positive.
- **H-P3**: accuracy flat vs variance at fixed a_j* -> corr(acc, Var(z)) near zero.
All three -> a DIRECT causal dissociation, the strongest form of the paper's claim. It would upgrade §6 from
an indirect (logit-sharpening) intervention to a direct manipulation of the operative variable, and add
`fig_patch` as the causal centerpiece.

## Honest caveats (in the prereg, carry to the paper)
- The patch forces all heads in L* to one distribution (tests sufficiency + dissociation, not the exact
  natural circuit).
- FIXVAR holds variance only approximately (iid-value model, Prop 1); FIXP is the clean complement.
