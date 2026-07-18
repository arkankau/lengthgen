# Runbook — vanishing-variance × PE length generalization (GPU)

Tests whether the arXiv:2504.02827 post-attention-LayerNorm "vanishing variance" fix restores length
extrapolation on the paper's own order-invariant tasks (argmax retrieval, dictionary lookup) and on an
order-dependent task (addition), across NoPE and RoPE. Self-contained; needs only torch + a GPU.

The script is **resumable**: it reloads `lengthgen_results.json` and skips configs already done, so a
disconnect never loses progress — just run the same command again.

---

## RECOMMENDED: Kaggle (does not disconnect like Colab)

Colab free tier recycles the VM and kills long runs. Kaggle notebooks run up to 12h and can **background-
run** (close the tab, come back later). Use it.

1. kaggle.com → Create → **Notebook**. Settings → Accelerator → **GPU T4 x2** (or P100).
2. Cell 1 — write the script:
   ```python
   %%writefile length_gen_colab.py
   ...paste colab/length_gen_colab.py here...
   ```
3. Cell 2 — smoke (≈2 min), confirms GPU + pipeline:
   ```
   !python length_gen_colab.py --smoke
   ```
4. Cell 3 — the real run (outputs land in /kaggle/working, which persists):
   ```
   !python length_gen_colab.py --tasks addition,flagret,recall,argmax --seeds 0,1
   ```
5. **Save Version → Save & Run All (Commit)** to run it headless in the background. When it finishes,
   open the version and download `lengthgen_results.json` + `lengthgen_ladder.csv` from the Output tab.
   ~30–60 min at the reduced 4000-step setting.

---

## FALLBACK: Colab, made disconnect-proof

Save results to Google Drive so they survive a runtime recycle, and run in small chunks + resume.

1. Runtime → Change runtime type → **GPU**.
2. Mount Drive and write the script:
   ```python
   from google.colab import drive; drive.mount('/content/drive')
   ```
   ```python
   %%writefile length_gen_colab.py
   ...paste colab/length_gen_colab.py here...
   ```
3. Run **one task at a time** (each chunk is short enough to finish before a disconnect), saving to Drive:
   ```
   !python length_gen_colab.py --tasks argmax   --seeds 0,1 --outdir /content/drive/MyDrive/lengthgen
   !python length_gen_colab.py --tasks recall   --seeds 0,1 --outdir /content/drive/MyDrive/lengthgen
   !python length_gen_colab.py --tasks flagret  --seeds 0,1 --outdir /content/drive/MyDrive/lengthgen
   !python length_gen_colab.py --tasks addition --seeds 0,1 --outdir /content/drive/MyDrive/lengthgen
   ```
   All chunks accumulate into the same file. **If any disconnects, just re-run that same line** — it
   prints `[skip …]` for finished configs and continues. The last line prints the full SUMMARY + VERDICT.
4. To get the combined verdict any time: re-run the full command; it resumes and summarizes everything:
   ```
   !python length_gen_colab.py --tasks addition,flagret,recall,argmax --seeds 0,1 --outdir /content/drive/MyDrive/lengthgen
   ```

---

## What to send back

The `SUMMARY` table + `CONTRAST VERDICT` block, or upload `lengthgen_results.json`. The verdict
self-classifies:

- **GENUINE NULL** — post-LN stabilizes variance but doesn't rescue length-gen even on the paper's own
  tasks → reproduction-and-scoping negative (contests 2504.02827).
- **CONTRAST CONFIRMED** — post-LN rescues order-invariant but not addition → the interaction result.
- **BOTH IMPROVE** — the fix transfers to order-dependent tasks too.
- **CONTROL DID NOT BREAK** — even at 20× the baseline generalizes; push the ladder further.

Reads at the longest length where the no-LN baseline actually fails (per-token < 0.9); a control that
never breaks is flagged, not counted as a null. Both PEs reported (NoPE ≈ the paper's PE-removed setup).
