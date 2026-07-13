#!/usr/bin/env bash
# Pre-registered 2x2 x 2 seeds for vanishing-variance x PE length generalization.
# Usage: run_lengthgen_2x2.sh <task> <steps>   (defaults: addition 4000)
set -u
cd "$(dirname "$0")/.."
source .venv/Scripts/activate 2>/dev/null
mkdir -p results/lengthgen
TASK="${1:-addition}"
STEPS="${2:-4000}"
LTRAIN=5
for pe in nope rope; do
  for ln in 0 1; do
    for seed in 0 1; do
      out="results/lengthgen/lg_${TASK}_${pe}_ln${ln}_s${seed}.csv"
      echo "=== RUN task=$TASK pe=$pe post_attn_ln=$ln seed=$seed -> $out ==="
      python scripts/length_gen_train.py --task "$TASK" --pe "$pe" --post-attn-ln "$ln" \
        --l-train "$LTRAIN" --steps "$STEPS" --log-every 2000 --seed "$seed" \
        --output "$out" 2>&1 | grep -v -i warning
    done
  done
done
echo "=== ALL 8 RUNS DONE (task=$TASK) ==="
