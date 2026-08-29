#!/usr/bin/env bash
# NIAH (needle-in-a-haystack) in REAL Wikipedia text -- the non-synthetic / benchmark-format evidence.
# Queued: waits for the multi-model sweep to finish so the two jobs do not contend for CPU.
set -u
cd "$(dirname "$0")/../colab" || exit 1
PY="../.venv/Scripts/python.exe"
[ -f "$PY" ] || PY=python
OUT="../results/lengthgen/niah"
mkdir -p "$OUT"

echo "waiting for the model sweep to finish ($(date +%H:%M:%S))..."
for _ in $(seq 1 600); do
  grep -q "ALL DONE" ../results/lengthgen/ext/sweep.log 2>/dev/null && break
  sleep 30
done
echo "starting NIAH ($(date +%H:%M:%S))"

run_niah () {
  name="$1"; slug="$2"; lens="$3"; n="$4"; b="$5"
  d="$OUT/$slug"; mkdir -p "$d"
  if [ -f "$d/niah_results.json" ]; then echo "[skip] $slug done"; return; fi
  echo "=============== NIAH $name ($(date +%H:%M:%S)) ==============="
  "$PY" niah_probe.py --model "$name" --lengths "$lens" --n "$n" --batch "$b" --outdir "$d" 2>&1 \
    | grep -viE 'FutureWarning|warnings.warn|weights_only|Some weights|You should probably|Loading weights'
  echo "=============== done $slug ($(date +%H:%M:%S)) ==============="
}

# GPT-2 family first (fast, and a different family from the paper's Pythia).
run_niah "gpt2-medium"        "gpt2medium" "128,256,512,900" 120 8
# The paper's own model, now on REAL text -- most directly extends the existing result.
run_niah "EleutherAI/pythia-1.4b" "pythia14b" "128,256,512,1024" 80 4
# Third family.
run_niah "Qwen/Qwen2.5-0.5B"  "qwen05"     "128,256,512,1024" 100 6
echo "NIAH ALL DONE $(date +%H:%M:%S)"
