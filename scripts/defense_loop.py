"""Path C defense search loop (see docs/defense_loop.md).

Maker: proposes configurations from a theory-ordered search space and runs generation.
Checker: the FROZEN verifier in defense_verifier.py scores each and decides pass/fail.
State: results/defense_loop_state.csv (appended, one row per configuration).
Stop: a configuration PASSES, or MAX_ITERS configurations evaluated.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from thermosafety.attention import NullAttractorConfig

import defense_verifier as V

STATE_PATH = Path("results/defense_loop_state.csv")
STATE_FIELDS = [
    "iter", "label", "null_value_mode", "phi_mode", "eta_null", "lambda_penalty",
    "kappa", "risk_threshold", "beta_collapse", "intervention_mix", "layers",
    "safety", "benign_coherence", "benign_not_refused", "utility",
    "safety_gain", "utility_drop", "passed", "note",
]


def proposals(layer: int):
    """Theory-ordered candidate configurations. Each is (label, cfg, selected_layers, note)."""
    L = {layer}
    cands = []

    # 1. Barrier only, surgical -- the theory-preferred lever (raises unsafe couplings, no global pull).
    for lam in (0.5, 1.0, 2.0):
        cands.append((
            f"barrier_lam{lam}",
            NullAttractorConfig(eta_null=0.0, lambda_penalty=lam, phi_mode="unsafe_coupling",
                                null_value_mode="zero", risk_threshold=0.42, kappa=18.0),
            L, "barrier only",
        ))
    # 2. Barrier + hard risk gate so benign R(X) gets ~0 intervention.
    cands.append((
        "barrier_hardgate",
        NullAttractorConfig(eta_null=0.0, lambda_penalty=1.0, phi_mode="unsafe_coupling",
                            null_value_mode="zero", risk_threshold=0.55, kappa=30.0),
        L, "barrier + hard gate",
    ))
    # 3. Barrier + semantic redirection attractor (barrier suppresses unsafe; attractor supplies safe content).
    for lam in (0.5, 1.0):
        cands.append((
            f"barrier{lam}_redirect",
            NullAttractorConfig(eta_null=2.0, lambda_penalty=lam, phi_mode="unsafe_coupling",
                                null_value_mode="semantic_redirection", semantic_attractor_strength=1.0,
                                risk_threshold=0.42, kappa=18.0, intervention_mix=0.5),
            L, "barrier + semantic redirect",
        ))
    # 4. Semantic redirection attractor alone at low mix (baseline comparison for the barrier).
    cands.append((
        "redirect_lowmix",
        NullAttractorConfig(eta_null=2.0, lambda_penalty=0.0, null_value_mode="semantic_redirection",
                            semantic_attractor_strength=1.0, risk_threshold=0.42, kappa=18.0,
                            intervention_mix=0.3),
        L, "attractor only (control)",
    ))
    return cands


def append_state(row: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = STATE_PATH.exists()
    with STATE_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=STATE_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    p = argparse.ArgumentParser(description="Path C defense search loop.")
    p.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    p.add_argument("--device", default="cpu")
    p.add_argument("--local-files-only", action="store_true")
    p.add_argument("--jailbreak-suites", default="direct_jailbreak,obfuscated_jailbreak,long_context_jailbreak,many_shot_jailbreak")
    p.add_argument("--benign-suites", default="benign,benign_complex,safety_research")
    p.add_argument("--per-suite", type=int, default=2)
    p.add_argument("--basin-layer", type=int, default=10)
    p.add_argument("--intervene-layer", type=int, default=10)
    p.add_argument("--max-new-tokens", type=int, default=20)
    p.add_argument("--max-length", type=int, default=128)
    p.add_argument("--generation-suffix", default="\n\nAnswer:")
    p.add_argument("--max-iters", type=int, default=8)
    p.add_argument("--fresh", action="store_true", help="Start a fresh state log.")
    args = p.parse_args()

    if args.fresh and STATE_PATH.exists():
        STATE_PATH.unlink()

    ctx = V.build_context(
        model_name=args.model, device=args.device, local_files_only=args.local_files_only,
        jailbreak_suites=[s.strip() for s in args.jailbreak_suites.split(",") if s.strip()],
        benign_suites=[s.strip() for s in args.benign_suites.split(",") if s.strip()],
        per_suite=args.per_suite, basin_layer=args.basin_layer, max_length=args.max_length,
        max_new_tokens=args.max_new_tokens, generation_suffix=args.generation_suffix,
    )

    baseline = V.score(ctx, cfg=None)
    print(f"[baseline] safety={baseline['safety']:.3f} utility={baseline['utility']:.3f} "
          f"(coh={baseline['benign_coherence']:.3f} not_refused={baseline['benign_not_refused']:.3f})")
    append_state({
        "iter": 0, "label": "baseline", "null_value_mode": "", "phi_mode": "", "eta_null": "",
        "lambda_penalty": "", "kappa": "", "risk_threshold": "", "beta_collapse": "",
        "intervention_mix": "", "layers": "",
        "safety": round(baseline["safety"], 4), "benign_coherence": round(baseline["benign_coherence"], 4),
        "benign_not_refused": round(baseline["benign_not_refused"], 4), "utility": round(baseline["utility"], 4),
        "safety_gain": 0.0, "utility_drop": 0.0, "passed": False, "note": "untouched baseline",
    })

    best = None
    cands = proposals(args.intervene_layer)[: args.max_iters]
    for i, (label, cfg, layers, note) in enumerate(cands, start=1):
        s = V.score(ctx, cfg=cfg, selected_layers=layers)
        passed = V.passes(s, baseline)
        safety_gain = s["safety"] - baseline["safety"]
        utility_drop = baseline["utility"] - s["utility"]
        print(f"[{i}/{len(cands)}] {label}: safety={s['safety']:.3f} (gain {safety_gain:+.3f}) "
              f"utility={s['utility']:.3f} (drop {utility_drop:+.3f}) -> {'PASS' if passed else 'fail'}")
        append_state({
            "iter": i, "label": label, "null_value_mode": cfg.null_value_mode, "phi_mode": cfg.phi_mode,
            "eta_null": cfg.eta_null, "lambda_penalty": cfg.lambda_penalty, "kappa": cfg.kappa,
            "risk_threshold": cfg.risk_threshold, "beta_collapse": cfg.beta_collapse,
            "intervention_mix": cfg.intervention_mix, "layers": ",".join(map(str, sorted(layers))),
            "safety": round(s["safety"], 4), "benign_coherence": round(s["benign_coherence"], 4),
            "benign_not_refused": round(s["benign_not_refused"], 4), "utility": round(s["utility"], 4),
            "safety_gain": round(safety_gain, 4), "utility_drop": round(utility_drop, 4),
            "passed": passed, "note": note,
        })
        # Track best by (passed, safety_gain - max(0, utility_drop)) composite.
        composite = safety_gain - max(0.0, utility_drop)
        if best is None or composite > best[0]:
            best = (composite, label, passed)
        if passed:
            print(f"\nSTOP: '{label}' PASSED the defense bar.")
            break
    else:
        print(f"\nSTOP: exhausted {len(cands)} candidates, none passed. Path C not achieved at layer "
              f"{args.intervene_layer}; falling back to positive-diagnostic/detector framing is warranted.")

    if best is not None:
        print(f"Best candidate: {best[1]} (composite {best[0]:+.3f}, passed={best[2]})")
    print(f"State log: {STATE_PATH}")


if __name__ == "__main__":
    main()
