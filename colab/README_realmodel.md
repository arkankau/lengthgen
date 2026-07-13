# Runbook: real-model generalization probe

Does "selection over scale" hold in a REAL pretrained LM, not just the toy transformers? This probes
in-context key-value recall across context lengths and measures, from attention weights alone, whether
attention on the correct source predicts retrieval accuracy and falls with length.

Pre-registration: `results/lengthgen_realmodel_prereg.md`. Pipeline validated on a CPU smoke.

## Step 0 - smoke (30 s, do this first)
Put `real_model_probe.py` in the working dir. Verify the pipeline and that the model has dynamic range:
```bash
!python real_model_probe.py --model EleutherAI/pythia-1.4b --smoke
```
Look at the printed `acc` per N: it should be high at short N and drop at longer N. If accuracy is ~0 at
every N, the model is too weak -> escalate (`pythia-2.8b`, `pythia-6.9b`, or a stronger instruct model). If
perfect everywhere, add longer lengths.

## Step 1 - full run (Colab GPU)
Mount Drive and VERIFY the mount (note the `/content` prefix -- a bare `/drive/...` saves to the throwaway
VM disk, not Drive):
```python
from google.colab import drive; drive.mount('/content/drive')
import os; assert os.path.isdir('/content/drive/MyDrive')
```
```bash
!python real_model_probe.py --model EleutherAI/pythia-1.4b \
    --lengths 5,10,20,40,80,160 --n 150 \
    --outdir /content/drive/MyDrive/lengthgen_realmodel
```
- Needs `attn_implementation='eager'` (set automatically) so attentions are returned.
- Memory: output_attentions materializes full attention matrices; keep `--batch 8` (lower to 4 if a long-N
  batch OOMs). pythia-1.4b fits a T4 easily; 2.8b fits; 6.9b is tight.
- Saves `realmodel_results.json` incrementally after each length.

## Step 2 - analyze (local)
Download to `results/lengthgen/realmodel_results.json`, then:
```bash
python scripts/analyze_real_model.py results/lengthgen/realmodel_results.json
```
Prints the H-R1/H-R2 verdict and writes `results/lengthgen/fig_realmodel.pdf` (top: accuracy and
attention-on-source both fall with N; bottom: P(correct) rises with attention on the correct source).

## What would make the paper
- **H-R1**: in a real LM, accuracy and attention-on-source both fall with context -> the length-gen failure
  localizes to attention dispersing off the source, as in the toy models.
- **H-R2**: within a fixed length, attention-on-source predicts which examples are correct, better than the
  ||a||^2 variance proxy and than entropy.
Together: the operative-variable account generalizes beyond the toy transformers. This is the paper's
external-validity result -- the single biggest answer to "does any of this hold in a real model?"

## Honest notes (carry to the paper)
- Report the WITHIN-length correlation as primary (pooled is inflated by the shared decline with N).
- The variance candidate is the attention participation ||a||^2 (= attention-output variance up to a
  constant by Prop 1), computed from attention weights to stay model-agnostic.
- Needs a model with dynamic range; state the model and that accuracy spans a range.
