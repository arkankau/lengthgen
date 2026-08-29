#!/usr/bin/env bash
# Multi-model / multi-family external-validity sweep, run LOCALLY on CPU (Colab's Xet backend hangs).
# Each model: real_model_probe (co-decline + within-length predictor) then decouple_probe (two-locus split).
# Ordered by value: a different FAMILY first (GPT-2 = learned absolute PE, vs Pythia/Qwen = RoPE).
set -u
cd "$(dirname "$0")/../colab" || exit 1
PY="../.venv/Scripts/python.exe"
[ -f "$PY" ] || PY=python
OUT="../results/lengthgen/ext"
mkdir -p "$OUT"

run_model () {
  name="$1"; slug="$2"
  d="$OUT/$slug"; mkdir -p "$d"
  echo "=============== $name -> $slug ($(date +%H:%M:%S)) ==============="
  if [ -f "$d/realmodel_results.json" ]; then
    echo "[skip] realmodel already done"
  else
    "$PY" real_model_probe.py --model "$name" --lengths 5,10,20,40,80,160 --n 150 --batch 8 --outdir "$d" 2>&1 \
      | grep -viE 'FutureWarning|warnings.warn|weights_only|Some weights|You should probably|progress'
  fi
  if [ -f "$d/decouple_results.json" ]; then
    echo "[skip] decouple already done"
  else
    "$PY" decouple_probe.py --model "$name" --lengths 10,20,40,80,160 --n 150 --batch 8 --outdir "$d" 2>&1 \
      | grep -viE 'FutureWarning|warnings.warn|weights_only|Some weights|You should probably|progress'
  fi
  echo "=============== done $slug ($(date +%H:%M:%S)) ==============="
}

# GPT-2 family (learned absolute position embeddings) -- the cross-FAMILY point that matters most.
run_model "gpt2-medium"        "gpt2medium"
# Qwen2.5 (modern RoPE family, different tokenizer/training) -- third family.
run_model "Qwen/Qwen2.5-0.5B"  "qwen05"
# Scale within the GPT-2 family.
run_model "gpt2-large"         "gpt2large"
echo "ALL DONE $(date +%H:%M:%S)"
