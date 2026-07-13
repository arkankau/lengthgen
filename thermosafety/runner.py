from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path

from thermosafety.attention import NullAttractorConfig, null_attractor_attention
from thermosafety.embeddings import embed_prompt
from thermosafety.metrics import attention_entropy, null_mass, null_selective_psi, spectral_gap
from thermosafety.prompts import PromptCase, load_prompt_dir
from thermosafety.risk import score_risk


FIELDNAMES = [
    "id",
    "suite",
    "label",
    "risk",
    "m_null",
    "collapsed",
    "entropy",
    "psi",
    "spectral_gap",
    "risk_threshold",
    "eta_null",
    "kappa",
    "lambda_penalty",
    "beta_base",
    "beta_collapse",
    "null_key_scale",
    "null_value_scale",
]


def evaluate_case(case: PromptCase, config: NullAttractorConfig) -> dict[str, object]:
    hidden = embed_prompt(case.prompt)
    risk = score_risk(case.prompt).score
    result = null_attractor_attention(hidden, hidden, hidden, risk=risk, config=config)
    m_null = null_mass(result.attention)
    return {
        "id": case.id,
        "suite": case.suite,
        "label": case.label,
        "risk": risk,
        "m_null": m_null,
        "collapsed": int(m_null >= 0.5),
        "entropy": attention_entropy(result.attention),
        "psi": null_selective_psi(result.attention),
        "spectral_gap": spectral_gap(result.attention),
        **asdict(config),
    }


def run_suite(cases: list[PromptCase], config: NullAttractorConfig) -> list[dict[str, object]]:
    return [evaluate_case(case, config) for case in cases]


def write_csv(rows: list[dict[str, object]], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run toy null-attractor diagnostics.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--output", default="results/toy_diagnostics.csv")
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
    rows = run_suite(load_prompt_dir(args.prompts), cfg)
    write_csv(rows, args.output)
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
