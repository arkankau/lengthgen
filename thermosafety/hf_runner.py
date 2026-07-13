from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path

import numpy as np

from thermosafety.attention import NullAttractorConfig, null_attractor_attention
from thermosafety.metrics import attention_entropy, null_mass, null_selective_psi, spectral_gap
from thermosafety.prompts import PromptCase, load_prompt_dir
from thermosafety.real_model import (
    OptionalDependencyError,
    RealModelTrace,
    extract_trace,
    extract_trace_from_loaded,
    hidden_state_features,
    load_model,
)
from thermosafety.trajectory_risk import score_trajectory_risk


FIELDNAMES = [
    "id",
    "suite",
    "label",
    "model",
    "layer",
    "tokens",
    "risk",
    "surface_risk",
    "hidden_drift_risk",
    "layer_path_risk",
    "attention_concentration_risk",
    "probe_risk",
    "m_null",
    "collapsed",
    "entropy",
    "psi",
    "spectral_gap",
    "hidden_token_drift",
    "hidden_norm",
    "layer_path_length",
    "native_attention_entropy",
    "native_attention_peak",
    "risk_threshold",
    "eta_null",
    "kappa",
    "lambda_penalty",
    "beta_base",
    "beta_collapse",
    "null_key_scale",
    "null_value_scale",
    "normalize_hidden",
]


def evaluate_case_real(
    case: PromptCase,
    model_name: str,
    config: NullAttractorConfig,
    max_length: int,
    device: str,
    layer: int = -1,
    risk_source: str = "mixed",
    probe_score: float | None = None,
    normalize_hidden: bool = False,
) -> dict[str, object]:
    trace = extract_trace(
        case.prompt,
        model_name=model_name,
        max_length=max_length,
        device=device,
    )
    return evaluate_trace_real(case, trace, model_name, config, layer, risk_source, probe_score, normalize_hidden)


def maybe_normalize_hidden(hidden: np.ndarray, normalize: bool) -> np.ndarray:
    if not normalize:
        return hidden
    norms = np.linalg.norm(hidden, axis=-1, keepdims=True)
    return np.divide(hidden, norms, out=np.zeros_like(hidden), where=norms > 0)


def evaluate_trace_real(
    case: PromptCase,
    trace: RealModelTrace,
    model_name: str,
    config: NullAttractorConfig,
    layer: int = -1,
    risk_source: str = "mixed",
    probe_score: float | None = None,
    normalize_hidden: bool = False,
) -> dict[str, object]:
    features = hidden_state_features(trace)
    hidden = maybe_normalize_hidden(trace.hidden_states[layer], normalize_hidden)
    risk_breakdown = score_trajectory_risk(trace, mode=risk_source, probe_score=probe_score)
    risk = risk_breakdown.score
    result = null_attractor_attention(hidden, hidden, hidden, risk=risk, config=config)
    m_null = null_mass(result.attention)
    return {
        "id": case.id,
        "suite": case.suite,
        "label": case.label,
        "model": model_name,
        "layer": layer,
        "tokens": len(trace.tokens),
        "risk": risk,
        "surface_risk": risk_breakdown.surface_score,
        "hidden_drift_risk": risk_breakdown.hidden_drift_score,
        "layer_path_risk": risk_breakdown.layer_path_score,
        "attention_concentration_risk": risk_breakdown.attention_concentration_score,
        "probe_risk": risk_breakdown.probe_score,
        "m_null": m_null,
        "collapsed": int(m_null >= 0.5),
        "entropy": attention_entropy(result.attention),
        "psi": null_selective_psi(result.attention),
        "spectral_gap": spectral_gap(result.attention),
        **features,
        **asdict(config),
        "normalize_hidden": int(normalize_hidden),
    }


def extract_traces(
    cases: list[PromptCase],
    model_name: str,
    max_length: int,
    device: str,
    local_files_only: bool = False,
) -> list[tuple[PromptCase, RealModelTrace]]:
    torch, tokenizer, model = load_model(
        model_name=model_name,
        device=device,
        local_files_only=local_files_only,
    )
    return [
        (
            case,
            extract_trace_from_loaded(
                prompt=case.prompt,
                torch=torch,
                tokenizer=tokenizer,
                model=model,
                max_length=max_length,
                device=device,
            ),
        )
        for case in cases
    ]


def write_csv(rows: list[dict[str, object]], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run post-hoc null-attractor diagnostics on HF hidden states.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--output", default="results/hf_diagnostics.csv")
    parser.add_argument("--model", default="sshleifer/tiny-gpt2")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--layer", type=int, default=-1)
    parser.add_argument("--risk-source", choices=["surface", "trajectory", "mixed"], default="mixed")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--normalize-hidden", action="store_true")
    parser.add_argument("--risk-threshold", type=float, default=NullAttractorConfig.risk_threshold)
    parser.add_argument("--eta-null", type=float, default=NullAttractorConfig.eta_null)
    parser.add_argument("--kappa", type=float, default=NullAttractorConfig.kappa)
    parser.add_argument("--lambda-penalty", type=float, default=NullAttractorConfig.lambda_penalty)
    args = parser.parse_args()

    cfg = NullAttractorConfig(
        risk_threshold=args.risk_threshold,
        eta_null=args.eta_null,
        kappa=args.kappa,
        lambda_penalty=args.lambda_penalty,
    )
    try:
        rows = [
            evaluate_trace_real(
                case,
                trace,
                args.model,
                cfg,
                args.layer,
                args.risk_source,
                normalize_hidden=args.normalize_hidden,
            )
            for case, trace in extract_traces(
                load_prompt_dir(args.prompts),
                args.model,
                args.max_length,
                args.device,
                args.local_files_only,
            )
        ]
    except OptionalDependencyError as exc:
        raise SystemExit(str(exc)) from exc

    write_csv(rows, args.output)
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
