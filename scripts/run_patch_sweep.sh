#!/usr/bin/env bash
# Causal attention patching in REAL pretrained LMs (the strong hook), queued behind the NIAH sweep.
set -u
cd "$(dirname "$0")/../colab" || exit 1
PY="../.venv/Scripts/python.exe"
[ -f "$PY" ] || PY=python
OUT="../results/lengthgen/realpatch"
mkdir -p "$OUT"

echo "waiting for the NIAH sweep to finish ($(date +%H:%M:%S))..."
for _ in $(seq 1 900); do
  grep -q "NIAH ALL DONE" ../results/lengthgen/niah_sweep.log 2>/dev/null && break
  sleep 30
done
echo "starting causal patch ($(date +%H:%M:%S))"

run_patch () {
  name="$1"; slug="$2"; lens="$3"; n="$4"; b="$5"
  d="$OUT/$slug"; mkdir -p "$d"
  if [ -f "$d/realpatch_results.json" ]; then echo "[skip] $slug done"; return; fi
  echo "=============== PATCH $name ($(date +%H:%M:%S)) ==============="
  "$PY" real_patch_probe.py --model "$name" --lengths "$lens" --n "$n" --batch "$b" \
      --biases 0,2,4,8 --outdir "$d" 2>&1 \
    | grep -viE 'FutureWarning|warnings.warn|weights_only|Some weights|You should probably|Loading weights'
  echo "=============== done $slug ($(date +%H:%M:%S)) ==============="
}

# The paper's own model first -- makes the existing correlational result causal.
run_patch "EleutherAI/pythia-1.4b" "pythia14b"  "20,40,80"  64 4
run_patch "gpt2-medium"            "gpt2medium" "20,40,80" 96 8
run_patch "Qwen/Qwen2.5-0.5B"      "qwen05"     "20,40,80" 96 6
echo "PATCH ALL DONE $(date +%H:%M:%S)"
