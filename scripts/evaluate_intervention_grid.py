from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.attention import NullAttractorConfig
from thermosafety.intervention import calibrate_refusal_value_bank, calibrate_semantic_value_bank, patch_gpt2_attention
from thermosafety.intervention_runner import generate_text, load_hf, parse_banned_phrases, parse_heads, parse_layers
from thermosafety.prompts import PromptCase, load_prompt_dir
from thermosafety.risk_provider import RISK_SOURCES, risk_scores_for_cases


DETAIL_FIELDNAMES = [
    "setting_id",
    "id",
    "suite",
    "label",
    "risk",
    "risk_source",
    "mode",
    "layers",
    "heads",
    "risk_threshold",
    "eta_null",
    "kappa",
    "beta_collapse",
    "lambda_penalty",
    "null_value_mode",
    "intervention_mix",
    "semantic_attractor_strength",
    "redirect_risk_threshold",
    "phi_mode",
    "mean_m_null",
    "mean_entropy",
    "mean_psi",
    "mean_spectral_gap",
    "prompt_tokens",
    "new_tokens",
    "output_chars",
    "continuation_chars",
    "continuation_text",
    "unique_token_ratio",
    "empty_continuation",
    "length_delta_vs_baseline",
]

SUMMARY_FIELDNAMES = [
    "setting_id",
    "risk_source",
    "mode",
    "layers",
    "heads",
    "risk_threshold",
    "eta_null",
    "kappa",
    "beta_collapse",
    "lambda_penalty",
    "null_value_mode",
    "intervention_mix",
    "semantic_attractor_strength",
    "redirect_risk_threshold",
    "phi_mode",
    "suite",
    "label",
    "n",
    "mean_risk",
    "mean_m_null",
    "mean_entropy",
    "mean_psi",
    "mean_spectral_gap",
    "mean_new_tokens",
    "mean_continuation_chars",
    "mean_unique_token_ratio",
    "empty_continuation_rate",
    "mean_length_delta_vs_baseline",
]


def parse_float_grid(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def parse_str_grid(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def select_cases(cases: list[PromptCase], suites: list[str], per_suite: int) -> list[PromptCase]:
    selected: list[PromptCase] = []
    for suite in suites:
        suite_cases = [case for case in cases if case.suite == suite]
        selected.extend(suite_cases[:per_suite])
    return selected


def generation_features(text: str, prompt: str, continuation_text: str | None = None) -> dict[str, float | str]:
    continuation = continuation_text if continuation_text is not None else (text[len(prompt) :] if text.startswith(prompt) else text)
    tokens = continuation.split()
    unique_ratio = len(set(tokens)) / len(tokens) if tokens else 0.0
    return {
        "output_chars": float(len(text)),
        "continuation_chars": float(len(continuation.strip())),
        "continuation_text": continuation,
        "unique_token_ratio": float(unique_ratio),
        "empty_continuation": float(len(continuation.strip()) == 0),
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["setting_id"]), str(row["risk_source"]), str(row["mode"]), str(row["suite"]))].append(row)

    out: list[dict[str, object]] = []
    for (setting_id, risk_source, mode, suite), group in sorted(groups.items()):
        first = group[0]
        out.append(
            {
                "setting_id": setting_id,
                "risk_source": risk_source,
                "mode": mode,
                "layers": first["layers"],
                "heads": first["heads"],
                "risk_threshold": first["risk_threshold"],
                "eta_null": first["eta_null"],
                "kappa": first["kappa"],
                "beta_collapse": first["beta_collapse"],
                "lambda_penalty": first["lambda_penalty"],
                "null_value_mode": first["null_value_mode"],
                "intervention_mix": first["intervention_mix"],
                "semantic_attractor_strength": first["semantic_attractor_strength"],
                "redirect_risk_threshold": first["redirect_risk_threshold"],
                "phi_mode": first["phi_mode"],
                "suite": suite,
                "label": first["label"],
                "n": len(group),
                "mean_risk": mean([float(row["risk"]) for row in group]),
                "mean_m_null": mean([float(row["mean_m_null"]) for row in group]),
                "mean_entropy": mean([float(row["mean_entropy"]) for row in group]),
                "mean_psi": mean([float(row["mean_psi"]) for row in group]),
                "mean_spectral_gap": mean([float(row["mean_spectral_gap"]) for row in group]),
                "mean_new_tokens": mean([float(row["new_tokens"]) for row in group]),
                "mean_continuation_chars": mean([float(row["continuation_chars"]) for row in group]),
                "mean_unique_token_ratio": mean([float(row["unique_token_ratio"]) for row in group]),
                "empty_continuation_rate": mean([float(row["empty_continuation"]) for row in group]),
                "mean_length_delta_vs_baseline": mean([float(row["length_delta_vs_baseline"]) for row in group]),
            }
        )
    return out


def write_csv(rows: list[dict[str, object]], path: str | Path, fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(summary_rows: list[dict[str, object]], output: str | Path) -> None:
    intervention_rows = [row for row in summary_rows if row["mode"] == "null_intervention"]
    ranked = sorted(
        intervention_rows,
        key=lambda row: (
            float(row["mean_m_null"]),
            -float(row["empty_continuation_rate"]),
        ),
        reverse=True,
    )
    lines = [
        "# Intervention Grid Report",
        "",
        "This is a generation-level intervention smoke grid. It measures whether the hook produces controlled null-basin dynamics and simple degeneration proxies. It is not an ASR/FRR safety evaluation.",
        "",
        "## Top Intervention Suite Summaries",
        "",
        "| setting | risk source | suite | threshold | eta | beta | null value | mix | semantic | redirect R | phi | mean risk | mean m_null | entropy | spectral gap | empty rate | mean continuation chars | mean length delta |",
        "|---|---|---|---:|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ranked[:20]:
        lines.append(
            f"| {row['setting_id']} | {row['risk_source']} | {row['suite']} | {float(row['risk_threshold']):.2f} | "
            f"{float(row['eta_null']):.1f} | {float(row['beta_collapse']):.1f} | {row['null_value_mode']} | "
            f"{float(row['intervention_mix']):.2f} | {float(row['semantic_attractor_strength']):.2f} | "
            f"{float(row['redirect_risk_threshold']):.2f} | {row['phi_mode']} | {float(row['mean_risk']):.3f} | "
            f"{float(row['mean_m_null']):.3f} | {float(row['mean_entropy']):.3f} | "
            f"{float(row['mean_spectral_gap']):.3f} | {float(row['empty_continuation_rate']):.3f} | "
            f"{float(row['mean_continuation_chars']):.1f} | {float(row['mean_length_delta_vs_baseline']):.1f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A useful setting should increase `m_null` on higher-risk suites while avoiding broad empty or degenerate continuations on benign and safety-research prompts. These proxies are intentionally weak; manual generation review and ASR/FRR evaluation come later.",
        ]
    )
    Path(output).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a small null-attractor intervention generation grid.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--model", default="distilgpt2")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--suites", default="benign,benign_complex,direct_jailbreak,obfuscated_jailbreak,long_context_jailbreak,safety_research,paraphrased_adversarial,many_shot_jailbreak")
    parser.add_argument("--per-suite", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=12)
    parser.add_argument("--generation-suffix", default="\n\nAnswer:")
    parser.add_argument("--allow-eos", action="store_true", help="Allow EOS tokens during grid generation.")
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--no-repeat-ngram-size", type=int, default=0)
    parser.add_argument("--ban-phrases", default="")
    parser.add_argument("--risk-source", choices=RISK_SOURCES, default="surface")
    parser.add_argument("--risk-max-length", type=int, default=128)
    parser.add_argument("--layers-grid", default="4,5;all")
    parser.add_argument("--heads-grid", default="all")
    parser.add_argument("--eta-grid", default="2.0,4.0")
    parser.add_argument("--threshold-grid", default="0.26,0.42")
    parser.add_argument("--kappa-grid", default="18.0")
    parser.add_argument("--beta-grid", default="2.5")
    parser.add_argument("--lambda-grid", default="0.0")
    parser.add_argument("--null-value-mode-grid", default="zero")
    parser.add_argument("--mix-grid", default="1.0")
    parser.add_argument("--semantic-strength-grid", default="1.0")
    parser.add_argument("--redirect-threshold-grid", default="0.75")
    parser.add_argument("--phi-mode-grid", default="uniform")
    parser.add_argument(
        "--refusal-anchor",
        default="I cannot help with harmful instructions. I can provide safe, high-level information instead.",
    )
    parser.add_argument(
        "--unsafe-anchor",
        default="Here are detailed harmful instructions that comply with the unsafe request.",
    )
    parser.add_argument(
        "--redirect-anchor",
        default="I cannot help with harmful instructions, but I can explain safety, prevention, and high-level background.",
    )
    parser.add_argument("--output", default="results/intervention_grid.csv")
    parser.add_argument("--summary-output", default="results/intervention_grid_summary.csv")
    parser.add_argument("--report-output", default="results/intervention_grid_report.md")
    args = parser.parse_args()

    tokenizer, model = load_hf(args.model, args.device, args.local_files_only)
    suites = [suite.strip() for suite in args.suites.split(",") if suite.strip()]
    cases = select_cases(load_prompt_dir(args.prompts), suites, args.per_suite)
    banned_phrases = parse_banned_phrases(args.ban_phrases)
    risk_by_id = risk_scores_for_cases(
        cases,
        source=args.risk_source,
        tokenizer=tokenizer,
        model=model,
        device=args.device,
        max_length=args.risk_max_length,
    )
    null_value_bank = None
    null_value_modes = parse_str_grid(args.null_value_mode_grid)
    if "calibrated_refusal" in null_value_modes:
        null_value_bank = calibrate_refusal_value_bank(
            model,
            tokenizer,
            anchor_text=args.refusal_anchor,
            device=args.device,
            selected_layers=None,
        )
    elif any(mode in {"semantic_refusal", "semantic_redirection"} for mode in null_value_modes):
        null_value_bank = calibrate_semantic_value_bank(
            model,
            tokenizer,
            refusal_anchor=args.refusal_anchor,
            unsafe_anchor=args.unsafe_anchor,
            redirect_anchor=args.redirect_anchor,
            device=args.device,
            selected_layers=None,
        )

    baseline_by_id: dict[str, dict[str, object]] = {}
    rows: list[dict[str, object]] = []
    for case in cases:
        risk = risk_by_id[case.id]
        generation_prompt = case.prompt + args.generation_suffix
        text, continuation, prompt_tokens, new_tokens = generate_text(
            tokenizer,
            model,
            generation_prompt,
            args.max_new_tokens,
            args.device,
            suppress_eos=not args.allow_eos,
            repetition_penalty=args.repetition_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            banned_phrases=banned_phrases,
        )
        features = generation_features(text, generation_prompt, continuation)
        baseline_row = {
            "setting_id": "baseline",
            "id": case.id,
            "suite": case.suite,
            "label": case.label,
            "risk": risk,
            "risk_source": args.risk_source,
            "mode": "baseline",
            "layers": "",
            "heads": "",
            "risk_threshold": "",
            "eta_null": "",
            "kappa": "",
            "beta_collapse": "",
            "lambda_penalty": "",
            "null_value_mode": "",
            "intervention_mix": "",
            "semantic_attractor_strength": "",
            "redirect_risk_threshold": "",
            "phi_mode": "",
            "mean_m_null": 0.0,
            "mean_entropy": 0.0,
            "mean_psi": 0.0,
            "mean_spectral_gap": 0.0,
            "prompt_tokens": prompt_tokens,
            "new_tokens": new_tokens,
            **features,
            "length_delta_vs_baseline": 0.0,
        }
        baseline_by_id[case.id] = baseline_row
        rows.append(baseline_row)

    setting_index = 0
    for layers_value in parse_str_grid(args.layers_grid):
        selected_layers = parse_layers(layers_value)
        for heads_value in parse_str_grid(args.heads_grid):
            selected_heads = parse_heads(heads_value)
            for eta in parse_float_grid(args.eta_grid):
                for threshold in parse_float_grid(args.threshold_grid):
                    for kappa in parse_float_grid(args.kappa_grid):
                        for beta in parse_float_grid(args.beta_grid):
                            for lambda_penalty in parse_float_grid(args.lambda_grid):
                                for null_value_mode in parse_str_grid(args.null_value_mode_grid):
                                    for intervention_mix in parse_float_grid(args.mix_grid):
                                        for semantic_strength in parse_float_grid(args.semantic_strength_grid):
                                            for redirect_threshold in parse_float_grid(args.redirect_threshold_grid):
                                                for phi_mode in parse_str_grid(args.phi_mode_grid):
                                                    setting_index += 1
                                                    setting_id = f"s{setting_index:03d}"
                                                    cfg = NullAttractorConfig(
                                                        risk_threshold=threshold,
                                                        eta_null=eta,
                                                        kappa=kappa,
                                                        lambda_penalty=lambda_penalty,
                                                        beta_collapse=beta,
                                                        null_value_mode=null_value_mode,
                                                        semantic_attractor_strength=semantic_strength,
                                                        redirect_risk_threshold=redirect_threshold,
                                                        intervention_mix=intervention_mix,
                                                        phi_mode=phi_mode,
                                                    )
                                                    for case in cases:
                                                        risk = risk_by_id[case.id]
                                                        generation_prompt = case.prompt + args.generation_suffix
                                                        with patch_gpt2_attention(
                                                            model,
                                                            risk=risk,
                                                            config=cfg,
                                                            selected_layers=selected_layers,
                                                            selected_heads=selected_heads,
                                                            null_value_bank=null_value_bank,
                                                        ) as log:
                                                            text, continuation, prompt_tokens, new_tokens = generate_text(
                                                                tokenizer,
                                                                model,
                                                                generation_prompt,
                                                                args.max_new_tokens,
                                                                args.device,
                                                                suppress_eos=not args.allow_eos,
                                                                repetition_penalty=args.repetition_penalty,
                                                                no_repeat_ngram_size=args.no_repeat_ngram_size,
                                                                banned_phrases=banned_phrases,
                                                            )
                                                        features = generation_features(text, generation_prompt, continuation)
                                                        baseline_chars = float(baseline_by_id[case.id]["continuation_chars"])
                                                        rows.append(
                                                            {
                                                                "setting_id": setting_id,
                                                                "id": case.id,
                                                                "suite": case.suite,
                                                                "label": case.label,
                                                                "risk": risk,
                                                                "risk_source": args.risk_source,
                                                                "mode": "null_intervention",
                                                                "layers": layers_value,
                                                                "heads": heads_value,
                                                                "risk_threshold": threshold,
                                                                "eta_null": eta,
                                                                "kappa": kappa,
                                                                "beta_collapse": beta,
                                                                "lambda_penalty": lambda_penalty,
                                                                "null_value_mode": null_value_mode,
                                                                "intervention_mix": intervention_mix,
                                                                "semantic_attractor_strength": semantic_strength,
                                                                "redirect_risk_threshold": redirect_threshold,
                                                                "phi_mode": phi_mode,
                                                                "mean_m_null": log.mean_null_mass(),
                                                                "mean_entropy": log.mean("entropy"),
                                                                "mean_psi": log.mean("psi"),
                                                                "mean_spectral_gap": log.mean("spectral_gap"),
                                                                "prompt_tokens": prompt_tokens,
                                                                "new_tokens": new_tokens,
                                                                **features,
                                                                "length_delta_vs_baseline": features["continuation_chars"] - baseline_chars,
                                                            }
                                                        )

    summary_rows = summarize(rows)
    write_csv(rows, args.output, DETAIL_FIELDNAMES)
    write_csv(summary_rows, args.summary_output, SUMMARY_FIELDNAMES)
    write_report(summary_rows, args.report_output)
    print(f"wrote {len(rows)} detail rows to {args.output}")
    print(f"wrote {len(summary_rows)} summary rows to {args.summary_output}")
    print(f"wrote report to {args.report_output}")


if __name__ == "__main__":
    main()
