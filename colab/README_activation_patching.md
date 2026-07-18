# GPU run: fixed-spectrum swap versus activation patching

Run this in a fresh T4 Colab after cloning or uploading the repository. The model is Qwen2.5-1.5B, matching
the existing pretrained routing audit. Each seed independently calibrates the circuit, then evaluates the
source-max swap on the clean prompt and clean-to-corrupt per-head activation patching on the same held-out rows.

```bash
pip install -q torch transformers matplotlib
```

```bash
for seed in 0 1 2; do
  python colab/pretrained_activation_patching_baseline.py \
    --model Qwen/Qwen2.5-1.5B \
    --length 5 --n 128 --batch 4 --heads 4 --calibration-examples 64 \
    --dtype fp32 --seed "$seed" \
    --outdir "results/lengthgen/activation_patching_qwen1p5b_s${seed}"
done
```

Each output is `pretrained_activation_patching_baseline.json`. Preserve all three files. The fixed-spectrum
effect and activation-patch rescue have different estimands and must not be subtracted as matched treatments.
Use fp32: the custom eager backend is numerically invalid in fp16 on the tested T4 setup.
