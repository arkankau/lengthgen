# Runbook: Direction-B causal control (attention sharpening)

Goal: complete the adjudication. Direction A showed attention-on-source predicts accuracy (r=0.94) far
better than variance (r=0.47), and that the variance fix leaves attention unrestored. This run intervenes
on attention directly (log-length logit sharpening, `--attn-scale loglen`, the SSMax operator) and reads
whether length generalization recovers WHERE THE VARIANCE FIX DID NOT.

Pre-registration: `results/lengthgen_causalB_prereg.md` (+ Amendment 1, which locks `attn_ref=6`).
The operator is prior art (SSMax, arXiv:2501.19399); it is used here as the causal probe, not claimed as new.

## What already exists (do not re-run)
`results/lengthgen/gpu_resultsA.json` holds the two comparison arms at 4 seeds:
baseline (LN off, no scaling) and varfix (LN on). This run adds only the third arm.

## Step 1 — GPU run on Colab (~16 configs, LN-off attention-sharpen arm)

Runtime -> Change runtime type -> GPU. Mount Drive and VERIFY the mount before running
(the `/content` prefix matters; a bare `/drive/...` silently writes to a VM-local folder that is lost on
recycle):

```python
from google.colab import drive; drive.mount('/content/drive')
import os; assert os.path.isdir('/content/drive/MyDrive'), 'Drive not mounted'
```

```bash
!python colab/length_gen_colab.py \
    --tasks argmax,flagret --seeds 0,1,2,3 \
    --attn-scale loglen --attn-ref 6 \
    --outdir /content/drive/MyDrive/lengthgenB
```

- 16 configs = argmax+flagret x nope+rope x 4 seeds (LN-off only, because `--attn-scale != none` forces
  `ln_opts=(0,)`).
- Saves incrementally to `/content/drive/MyDrive/lengthgenB/lengthgen_results.json` after every config, and
  prints a `RESULTJSON ...` line per config so the console log alone can rebuild the file if Drive drops.
- Safe to re-run after a disconnect: completed configs are skipped by `(task,pe,ln,seed,attn_scale)` key.

If the file is ever lost but you have the console log, recover with:
`python scripts/recover_from_log.py <log.txt> -o results/lengthgen/gpu_resultsB.json`

## Step 2 — merge + analyze (local)

Download `lengthgenB/lengthgen_results.json` to `results/lengthgen/gpu_resultsB.json`, then:

```bash
python scripts/merge_lengthgen_json.py \
    results/lengthgen/gpu_resultsA.json \
    results/lengthgen/gpu_resultsB.json \
    -o results/lengthgen/gpu_resultsAB.json

python scripts/analyze_causalB.py results/lengthgen/gpu_resultsAB.json
```

`analyze_causalB.py` prints the three-condition table and self-classifies against the pre-registered
hypotheses:

| outcome | meaning |
|---|---|
| CLINCHER | sharpening gives >+0.05 benefit in ~all cells where the variance fix gave <=0 -> causal dissociation, the strongest version of the paper |
| PARTIAL | sharpening lifts attn_tgt and helps some cells (likely NoPE) but does not fully rescue -> attention is necessary; report honestly |
| NEGATIVE | sharpening does not help accuracy -> the correlational A-result stands, the cause is more than attention; report honestly |

## Honest expectation
The CPU smoke (2L/128) gave only a modest long-length lift, and the dispersion literature reports
sharpening helps NoPE more than RoPE. PARTIAL is a realistic outcome. Whatever the verdict, it is reportable:
CLINCHER strengthens the paper toward beyond-workshop; PARTIAL/NEGATIVE still completes the adjudication and
keeps the honest-broker framing. No result here weakens the existing negative + localization.

## After the run
Hand the `analyze_causalB.py` output back. Then the paper's Section "Relation to attention-sharpening
interventions" upgrades from "we leave the causal test to future work" to a reported result, and (on
CLINCHER/PARTIAL) a new figure: benefit and attn_tgt for baseline vs varfix vs sharpen, side by side.
