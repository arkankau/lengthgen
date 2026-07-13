from __future__ import annotations

import argparse
import csv
from pathlib import Path

from thermosafety.attention import NullAttractorConfig
from thermosafety.intervention import calibrate_refusal_value_bank, calibrate_semantic_value_bank, patch_gpt2_attention
from thermosafety.prompts import load_prompt_dir
from thermosafety.risk_provider import RISK_SOURCES, risk_scores_for_cases


FIELDNAMES = [
    "id",
    "suite",
    "label",
    "risk",
    "risk_source",
    "mode",
    "selected_layers",
    "mean_m_null",
    "prompt_tokens",
    "new_tokens",
    "generated_text",
]

LOG_FIELDNAMES = [
    "id",
    "suite",
    "label",
    "risk",
    "risk_source",
    "layer",
    "head",
    "null_bias",
    "beta",
    "m_null",
    "entropy",
    "psi",
    "spectral_gap",
    "head_selected",
    "mix_alpha",
    "phi_penalty_mean",
    "null_value_norm",
]


def load_hf(model_name: str, device: str, local_files_only: bool):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModelForCausalLM.from_pretrained(model_name, local_files_only=local_files_only)
    model.to(device)
    model.eval()
    return tokenizer, model


def generate_text(
    tokenizer,
    model,
    prompt: str,
    max_new_tokens: int,
    device: str,
    suppress_eos: bool = False,
    repetition_penalty: float = 1.0,
    no_repeat_ngram_size: int = 0,
    banned_phrases: list[str] | None = None,
) -> tuple[str, str, int, int]:
    import torch

    encoded = tokenizer(prompt, return_tensors="pt").to(device)
    prompt_tokens = int(encoded["input_ids"].shape[-1])
    bad_words_ids = []
    if suppress_eos and tokenizer.eos_token_id is not None:
        bad_words_ids.append([tokenizer.eos_token_id])
    for phrase in banned_phrases or []:
        phrase_ids = tokenizer.encode(phrase, add_special_tokens=False)
        if phrase_ids:
            bad_words_ids.append(phrase_ids)
    with torch.no_grad():
        output = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
            bad_words_ids=bad_words_ids or None,
            repetition_penalty=repetition_penalty,
            no_repeat_ngram_size=no_repeat_ngram_size,
        )
    new_tokens = int(output.shape[-1] - prompt_tokens)
    full_text = tokenizer.decode(output[0], skip_special_tokens=True)
    continuation = tokenizer.decode(output[0, prompt_tokens:], skip_special_tokens=True)
    return full_text, continuation, prompt_tokens, new_tokens


def parse_layers(value: str) -> set[int] | None:
    if value.lower() in {"", "all", "*"}:
        return None
    return {int(part.strip()) for part in value.split(",") if part.strip()}


def parse_heads(value: str) -> set[int] | None:
    return parse_layers(value)


def parse_suites(value: str) -> set[str] | None:
    if value.lower() in {"", "all", "*"}:
        return None
    return {part.strip() for part in value.split(",") if part.strip()}


def parse_banned_phrases(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a first GPT-2 null-attractor intervention generation harness.")
    parser.add_argument("--prompts", default="prompts")
    parser.add_argument("--model", default="distilgpt2")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--suites", default="all")
    parser.add_argument("--max-new-tokens", type=int, default=24)
    parser.add_argument("--generation-suffix", default="")
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--no-repeat-ngram-size", type=int, default=0)
    parser.add_argument("--ban-phrases", default="")
    parser.add_argument("--layers", default="4,5")
    parser.add_argument("--risk-source", choices=RISK_SOURCES, default="surface")
    parser.add_argument("--risk-max-length", type=int, default=128)
    parser.add_argument("--output", default="results/intervention_generation.csv")
    parser.add_argument("--log-output", default="results/intervention_m_null_by_head.csv")
    parser.add_argument("--risk-threshold", type=float, default=0.26)
    parser.add_argument("--eta-null", type=float, default=4.0)
    parser.add_argument("--kappa", type=float, default=18.0)
    parser.add_argument("--lambda-penalty", type=float, default=0.0)
    parser.add_argument("--beta-collapse", type=float, default=2.5)
    parser.add_argument("--null-value-mode", default="zero")
    parser.add_argument("--semantic-attractor-strength", type=float, default=1.0)
    parser.add_argument("--redirect-risk-threshold", type=float, default=0.75)
    parser.add_argument("--intervention-mix", type=float, default=1.0)
    parser.add_argument("--phi-mode", default="uniform")
    parser.add_argument("--heads", default="all")
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
    args = parser.parse_args()

    tokenizer, model = load_hf(args.model, args.device, args.local_files_only)
    selected_layers = parse_layers(args.layers)
    selected_heads = parse_heads(args.heads)
    cfg = NullAttractorConfig(
        risk_threshold=args.risk_threshold,
        eta_null=args.eta_null,
        kappa=args.kappa,
        lambda_penalty=args.lambda_penalty,
        beta_collapse=args.beta_collapse,
        null_value_mode=args.null_value_mode,
        semantic_attractor_strength=args.semantic_attractor_strength,
        redirect_risk_threshold=args.redirect_risk_threshold,
        intervention_mix=args.intervention_mix,
        phi_mode=args.phi_mode,
    )
    null_value_bank = None
    if args.null_value_mode == "calibrated_refusal":
        null_value_bank = calibrate_refusal_value_bank(
            model,
            tokenizer,
            anchor_text=args.refusal_anchor,
            device=args.device,
            selected_layers=selected_layers,
        )
    elif args.null_value_mode in {"semantic_refusal", "semantic_redirection"}:
        null_value_bank = calibrate_semantic_value_bank(
            model,
            tokenizer,
            refusal_anchor=args.refusal_anchor,
            unsafe_anchor=args.unsafe_anchor,
            redirect_anchor=args.redirect_anchor,
            device=args.device,
            selected_layers=selected_layers,
        )

    rows = []
    log_rows = []
    suites = parse_suites(args.suites)
    cases = load_prompt_dir(args.prompts)
    if suites is not None:
        cases = [case for case in cases if case.suite in suites]
    cases = cases[: args.limit]
    banned_phrases = parse_banned_phrases(args.ban_phrases)
    risk_by_id = risk_scores_for_cases(
        cases,
        source=args.risk_source,
        tokenizer=tokenizer,
        model=model,
        device=args.device,
        max_length=args.risk_max_length,
    )
    for case in cases:
        risk = risk_by_id[case.id]
        generation_prompt = case.prompt + args.generation_suffix
        baseline_text, _, prompt_tokens, new_tokens = generate_text(
            tokenizer,
            model,
            generation_prompt,
            args.max_new_tokens,
            args.device,
            repetition_penalty=args.repetition_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
            banned_phrases=banned_phrases,
        )
        rows.append(
            {
                "id": case.id,
                "suite": case.suite,
                "label": case.label,
                "risk": risk,
                "risk_source": args.risk_source,
                "mode": "baseline",
                "selected_layers": "",
                "mean_m_null": 0.0,
                "prompt_tokens": prompt_tokens,
                "new_tokens": new_tokens,
                "generated_text": baseline_text,
            }
        )

        with patch_gpt2_attention(
            model,
            risk=risk,
            config=cfg,
            selected_layers=selected_layers,
            selected_heads=selected_heads,
            null_value_bank=null_value_bank,
        ) as log:
            intervention_text, _, prompt_tokens, new_tokens = generate_text(
                tokenizer,
                model,
                generation_prompt,
                args.max_new_tokens,
                args.device,
                repetition_penalty=args.repetition_penalty,
                no_repeat_ngram_size=args.no_repeat_ngram_size,
                banned_phrases=banned_phrases,
            )
        for record in log.records:
            log_rows.append(
                {
                    "id": case.id,
                    "suite": case.suite,
                    "label": case.label,
                    "risk": risk,
                    "risk_source": args.risk_source,
                    "layer": int(record["layer"]),
                    "head": int(record["head"]),
                    "null_bias": record["null_bias"],
                    "beta": record["beta"],
                    "m_null": record["m_null"],
                    "entropy": record["entropy"],
                    "psi": record["psi"],
                    "spectral_gap": record["spectral_gap"],
                    "head_selected": record["head_selected"],
                    "mix_alpha": record["mix_alpha"],
                    "phi_penalty_mean": record["phi_penalty_mean"],
                    "null_value_norm": record["null_value_norm"],
                }
            )
        rows.append(
            {
                "id": case.id,
                "suite": case.suite,
                "label": case.label,
                "risk": risk,
                "risk_source": args.risk_source,
                "mode": "null_intervention",
                "selected_layers": "all" if selected_layers is None else ",".join(str(v) for v in sorted(selected_layers)),
                "mean_m_null": log.mean_null_mass(),
                "prompt_tokens": prompt_tokens,
                "new_tokens": new_tokens,
                "generated_text": intervention_text,
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    log_output = Path(args.log_output)
    log_output.parent.mkdir(parents=True, exist_ok=True)
    with log_output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES)
        writer.writeheader()
        writer.writerows(log_rows)
    print(f"wrote {len(rows)} rows to {output}")
    print(f"wrote {len(log_rows)} null-mass log rows to {log_output}")


if __name__ == "__main__":
    main()
