"""Axis B: does the basin-energy diagnostic actually WORK as a jailbreak/harmful detector,
and does it beat / match standard baselines?

Task: binary detection, harmful (AdvBench) vs benign (Alpaca instruction-only), on prompt hidden
states. Detectors compared:
  - basin_margin      : E_safe - E_unsafe (label-free; uses 3 anchor prompts only)
  - single_anchor_cos : cos(h, refusal_anchor) (the single-refusal-direction baseline)
  - surface_risk      : keyword heuristic (trivial baseline)
  - logistic_probe    : supervised logistic regression on the full hidden state (stratified CV)

Metrics: AUROC and TPR at FPR in {0.05, 0.10}. The probe is the standard black-box baseline the
field uses; basin_margin's value proposition is being competitive while label-free and interpretable.

Harmful prompts are cached under the scratchpad and never written into the repo; only aggregate
metrics are saved to results/.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from thermosafety.basin_energy import basin_energies, cosine
from thermosafety.real_model import extract_trace_from_loaded, load_model
from thermosafety.risk import score_risk

from evaluate_basin_energy import (  # noqa: E402
    DEFAULT_BENIGN_ANCHOR,
    DEFAULT_SAFE_ANCHOR,
    DEFAULT_UNSAFE_ANCHOR,
    calibrate_single_anchors,
    pooled_hidden_state,
)

ADVBENCH_URL = "https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv"
ALPACA_URL = "https://raw.githubusercontent.com/tatsu-lab/stanford_alpaca/main/alpaca_data.json"


def _cache(url: str, cache_dir: Path, name: str) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / name
    if not p.exists():
        data = urllib.request.urlopen(url, timeout=90).read()
        p.write_bytes(data)
    return p.read_text(encoding="utf-8", errors="replace")


def load_prompts(cache_dir: Path, n_per_class: int, seed: int) -> tuple[list[str], list[str]]:
    adv = list(csv.DictReader(io.StringIO(_cache(ADVBENCH_URL, cache_dir, "advbench.csv"))))
    harmful = [r["goal"].strip() for r in adv if r.get("goal", "").strip()]
    alp = json.loads(_cache(ALPACA_URL, cache_dir, "alpaca.json"))
    benign = [d["instruction"].strip() for d in alp if not d.get("input") and d.get("instruction", "").strip()]
    rng = np.random.default_rng(seed)
    harmful = list(rng.permutation(harmful))[:n_per_class]
    benign = list(rng.permutation(benign))[:n_per_class]
    return harmful, benign


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney U form; labels in {0,1}, higher score => predict positive."""
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    avg = sums / counts
    ranks = avg[inv]
    r_pos = ranks[labels == 1].sum()
    u = r_pos - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


def tpr_at_fpr(scores: np.ndarray, labels: np.ndarray, fpr_target: float) -> float:
    neg = np.sort(scores[labels == 0])[::-1]
    if len(neg) == 0:
        return float("nan")
    k = max(1, int(np.floor(fpr_target * len(neg))))
    thr = neg[k - 1]  # threshold admitting ~fpr_target of negatives
    pos = scores[labels == 1]
    return float(np.mean(pos >= thr))


def oriented_auroc(scores, labels):
    """AUROC, auto-orienting so >=0.5 (a detector and its negation are equivalent up to sign)."""
    a = auroc(scores, labels)
    return a if a >= 0.5 else 1.0 - a


def main() -> None:
    p = argparse.ArgumentParser(description="Axis B: basin-energy detection vs baselines.")
    p.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    p.add_argument("--device", default="cpu")
    p.add_argument("--local-files-only", action="store_true")
    p.add_argument("--n-per-class", type=int, default=200)
    p.add_argument("--layers", default="10,14,18")
    p.add_argument("--max-length", type=int, default=64)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--cache-dir", default=str(Path(__file__).resolve().parents[1] / ".data_cache"))
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--output", default="results/detection_metrics.csv")
    p.add_argument("--report-output", default="results/detection_report.md")
    args = p.parse_args()

    harmful, benign = load_prompts(Path(args.cache_dir), args.n_per_class, args.seed)
    prompts = harmful + benign
    labels = np.array([1] * len(harmful) + [0] * len(benign))
    print(f"harmful={len(harmful)} benign={len(benign)}")

    torch, tokenizer, model = load_model(args.model, device=args.device, local_files_only=args.local_files_only)
    layers = [int(x) for x in args.layers.split(",") if x.strip()]

    # extract hidden states once per prompt for all requested layers
    per_layer_h: dict[int, list] = {L: [] for L in layers}
    refusal_anchor = DEFAULT_SAFE_ANCHOR
    surface = np.array([score_risk(t).score for t in prompts])
    for i, t in enumerate(prompts):
        trace = extract_trace_from_loaded(prompt=t, torch=torch, tokenizer=tokenizer, model=model,
                                          max_length=args.max_length, device=args.device)
        for L in layers:
            per_layer_h[L].append(pooled_hidden_state(trace.hidden_states, L))
        if (i + 1) % 50 == 0:
            print(f"  extracted {i+1}/{len(prompts)}")

    rows = []
    fprs = [0.05, 0.10]
    for L in layers:
        H = np.vstack(per_layer_h[L])
        centroids = calibrate_single_anchors(tokenizer, model, torch, args.device, L, args.max_length,
                                              DEFAULT_SAFE_ANCHOR, DEFAULT_UNSAFE_ANCHOR, DEFAULT_BENIGN_ANCHOR)
        refusal_vec = centroids.anchors["safe"]
        basin_margin = np.array([  # higher => closer to unsafe than safe => more harmful
            (basin_energies(h, centroids)["safe"] - basin_energies(h, centroids)["unsafe"]) for h in H
        ])
        single_anchor = np.array([-cosine(h, refusal_vec) for h in H])  # far from refusal => harmful

        detectors = {
            "basin_margin": basin_margin,
            "single_anchor_cos": single_anchor,
            "surface_risk": surface,
        }
        # supervised probe via stratified CV, out-of-fold scores
        skf = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=args.seed)
        oof = np.zeros(len(labels))
        for tr, te in skf.split(H, labels):
            scaler = StandardScaler().fit(H[tr])
            clf = LogisticRegression(max_iter=2000, C=1.0)
            clf.fit(scaler.transform(H[tr]), labels[tr])
            oof[te] = clf.predict_proba(scaler.transform(H[te]))[:, 1]
        detectors["logistic_probe"] = oof

        for name, sc in detectors.items():
            row = {"layer": L, "detector": name, "auroc": round(oriented_auroc(sc, labels), 4)}
            for f in fprs:
                sc_or = sc if auroc(sc, labels) >= 0.5 else -sc
                row[f"tpr@fpr{int(f*100)}"] = round(tpr_at_fpr(sc_or, labels, f), 4)
            rows.append(row)
            print(f"  L{L} {name}: AUROC={row['auroc']} TPR@5%={row['tpr@fpr5']} TPR@10%={row['tpr@fpr10']}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["layer", "detector", "auroc", "tpr@fpr5", "tpr@fpr10"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
