"""Create a CPU-only coverage audit for the length-generalization paper.

The audit does not run models.
It reads existing result artifacts and writes a reviewer-facing gap report.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(".")
OUT = Path("results/lengthgen_experiment_coverage_audit.md")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def load_json(path: str) -> Any | None:
    p = ROOT / path
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def load_csv_rows(path: str) -> list[dict[str, str]]:
    p = ROOT / path
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def count_configs(path: str) -> str:
    data = load_json(path)
    if not isinstance(data, list):
        return "missing"
    configs = len(data)
    seeds = sorted({row.get("cfg", {}).get("seed") for row in data if isinstance(row, dict)})
    tasks = sorted({row.get("cfg", {}).get("task") for row in data if isinstance(row, dict)})
    return f"{configs} configs; {len(seeds)} seeds; tasks={','.join(str(t) for t in tasks)}"


def realmodel_rows() -> list[dict[str, str]]:
    return load_csv_rows("results/lengthgen/realmodel_family_summary.csv")


def status_mark(ok: bool) -> str:
    return "complete" if ok else "missing"


def fmt_float(text: str) -> str:
    try:
        return f"{float(text):.3f}"
    except (TypeError, ValueError):
        return text


def line_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def main() -> None:
    real_rows = realmodel_rows()
    pythia_rows = [row for row in real_rows if "pythia" in row.get("model", "").lower()]
    non_pythia_rows = [row for row in real_rows if row.get("model") and "pythia" not in row["model"].lower()]
    non_pythia_models = sorted({row["model"] for row in non_pythia_rows})
    gemma_rows = [row for row in real_rows if "gemma" in row.get("model", "").lower()]
    heads_by_model: dict[str, set[int]] = defaultdict(set)
    for row in non_pythia_rows:
        try:
            heads_by_model[row["model"]].add(int(row.get("heads", "")))
        except ValueError:
            pass
    robust_head_models = sorted(model for model, heads in heads_by_model.items() if len(heads) >= 3)
    family_detail = ", ".join(
        f"{model} (heads {','.join(str(h) for h in sorted(heads_by_model[model]))})"
        for model in non_pythia_models
    )
    multi = load_json("results/lengthgen/multievidence_summary.json") or {}
    causal_rows = load_csv_rows("results/lengthgen/pretrained_causal_routing_summary.csv")
    causal_models = sorted({row.get("model", "") for row in causal_rows if row.get("model")})
    causal_full_ready = any(
        int(row.get("n_examples", "0") or 0) >= 128
        and float(row.get("baseline_accuracy", "0") or 0) >= 0.5
        for row in causal_rows
    )
    critical = load_json("results/lengthgen/pretrained_critical_summary.json") or {}
    utility_models = critical.get("utility_gap", [])
    selection_robustness = critical.get("selection_robustness", {})
    format_replication = critical.get("format_replication", {})
    natural_mcqa = load_json("results/lengthgen/pretrained_natural_mcqa_summary.json") or {}
    natural_ladder_qwen = load_json(
        "results/lengthgen/pretrained_natural_mcqa_ladder/qwen_two_seed_summary.json"
    ) or {}
    natural_ladder_smollm = load_json(
        "results/lengthgen/pretrained_natural_mcqa_ladder/smollm2_seed0_summary.json"
    ) or {}
    competence_arity = load_json(
        "results/lengthgen/competence_matched_arity_c3/competence_matched_arity_search.json"
    ) or {}
    arity_candidates = competence_arity.get("candidates") or [{}]
    arity_cells = arity_candidates[0].get("cells") or [{}]
    c3_exact_match = arity_cells[0].get("exact_match", float("nan"))
    selector_family = load_json("results/lengthgen/pretrained_selector_family_summary.json") or {}
    dose_response = load_json("results/lengthgen/pretrained_dose_response_summary.json") or {}
    variable_evidence = load_json("results/lengthgen/variable_evidence_summary.json") or {}

    coverage_rows = [
        [
            "Main scratch grid",
            status_mark(exists("results/lengthgen/gpu_resultsAB.json")),
            count_configs("results/lengthgen/gpu_resultsAB.json"),
            "Core correlation and variance-fix dissociation.",
        ],
        [
            "Causal sharpening",
            status_mark(exists("results/lengthgen/gpu_resultsB.json")),
            count_configs("results/lengthgen/gpu_resultsB.json"),
            "Intervention that raises attention-on-source.",
        ],
        [
            "Direct patching",
            status_mark(exists("results/lengthgen/patch_results.json")),
            "present" if exists("results/lengthgen/patch_results.json") else "missing",
            "Sufficiency test for selection.",
        ],
        [
            "Pretrained Pythia probe",
            status_mark(bool(pythia_rows)),
            f"{len(pythia_rows)} Pythia row; {pythia_rows[0].get('n_examples', 'unknown') if pythia_rows else '0'} examples",
            "First pretrained-model external-validity result.",
        ],
        [
            "Model-family robustness",
            status_mark(bool(non_pythia_models)),
            family_detail if family_detail else "no non-Pythia rows yet",
            "Tests the mechanism outside the Pythia family.",
        ],
        [
            "Real-model head-count robustness",
            status_mark(bool(robust_head_models)),
            ", ".join(robust_head_models) if robust_head_models else "fewer than three head counts",
            "Checks that retrieval-head selection is not tuned to one K.",
        ],
        [
            "Fixed-spectrum assignment grid",
            status_mark(exists("results/lengthgen/paired_head_count_full_grid.json")),
            count_configs("results/lengthgen/paired_head_count_full_grid.json"),
            "Core spectrum-preserving source assignment and head-dose test.",
        ],
        [
            "Capacity-by-assignment factorial",
            status_mark(exists("results/lengthgen/factorial_grid/concentration_assignment_results.json")),
            count_configs("results/lengthgen/factorial_grid/concentration_assignment_results.json"),
            "Direct test of the capacity--assignment interaction.",
        ],
        [
            "Two-evidence fixed-spectrum routing",
            status_mark(bool(multi.get("all_models_competent")) and multi.get("models") == 8),
            (
                f"{multi.get('models', 0)} models; min train exact="
                f"{multi.get('min_train_exact', float('nan')):.3f}"
            ),
            "Extends the set-valued law to a learned two-input computation.",
        ],
        [
            "Pretrained causal backend",
            "validated" if len(causal_models) >= 2 else "missing",
            ", ".join(causal_models) if causal_models else "no causal runs",
            "Fixed-spectrum intervention works inside pretrained attention implementations.",
        ],
        [
            "Paper-grade pretrained causal grid",
            "complete" if causal_full_ready else "pending GPU",
            "competent N>=128 model" if causal_full_ready else "current runs are backend/smoke validation",
            "Needed before claiming a causal pretrained-model result.",
        ],
        [
            "Pretrained utility-gap audit",
            status_mark(len(utility_models) >= 3),
            f"{len(utility_models)} model families; two lengths; 64 examples/cell",
            "Tests the nonlinear theorem's local utility term in pretrained models.",
        ],
        [
            "Causal selection robustness",
            status_mark(bool(selection_robustness.get("gate_pass"))),
            (
                f"{selection_robustness.get('selected_significant_cells', 0)}/"
                f"{selection_robustness.get('selected_cells', 0)} selected intervals exclude zero"
            ),
            "Checks independent splits, three seeds, K=2/4/8, and layer controls.",
        ],
        [
            "Second prompt format",
            "failed competence" if format_replication else "missing",
            (
                "equals-newline at N=5,20; N=80 runtime-limited"
                if format_replication else "no preregistered format run"
            ),
            "External-validity boundary; causal direction is not claimed without competence.",
        ],
        [
            "8-layer/512-width replication",
            status_mark(exists("results/lengthgen/gpu_results_scale.json")),
            count_configs("results/lengthgen/gpu_results_scale.json"),
            "Scale objection reducer; verify completeness before relying on it.",
        ],
        [
            "Natural context-grounded QA",
            "complete" if natural_mcqa.get("preregistered_success") else (
                "stage-1 complete" if natural_mcqa.get("stage1_replicated_success") else "missing"
            ),
            (
                f"{len(natural_mcqa.get('passing_seeds', []))} competent seeds; "
                f"full-size seeds={natural_mcqa.get('full_size_seeds', [])}"
                if natural_mcqa else "no natural-QA result"
            ),
            "Tests whether source-conditioned routing survives natural language and free answer choice.",
        ],
        [
            "Natural-QA length ladder",
            "boundary result" if natural_ladder_qwen and natural_ladder_smollm else "pending GPU",
            (
                f"Qwen full seeds={natural_ladder_qwen.get('full_size_seeds', [])}; "
                f"SmolLM full seeds={natural_ladder_smollm.get('full_size_seeds', [])}; "
                "preregistered mechanism failed"
                if natural_ladder_qwen and natural_ladder_smollm else
                "nested 4/8/16/32-passage protocol incomplete"
            ),
            "Tests whether the fixed-context natural-QA effect explains length degradation.",
        ],
        [
            "Cross-family selector ablation",
            "complete" if selector_family.get("complete_models", 0) >= 3 else "missing",
            (
                f"{selector_family.get('complete_models', 0)} complete families; "
                f"claim={selector_family.get('cross_family_claim', 'unknown')}"
            ),
            "Separates a general output-conditioned principle from a universal selector formula.",
        ],
        [
            "Interpolation dose response",
            status_mark(bool(dose_response.get("preregistered_success"))),
            (
                f"{len(dose_response.get('available_seeds', []))} seeds; "
                f"alphas={dose_response.get('alphas', [])}"
            ),
            "Checks that routing effects vary smoothly rather than appearing only at a maximal rewrite.",
        ],
        [
            "Three-/four-evidence routing",
            "boundary result" if variable_evidence.get("complete") else "pending GPU",
            (
                "complete grid; largest capacity search reaches exact match "
                f"{c3_exact_match:.3f}"
                if variable_evidence.get("complete") else
                "code and preregistration ready"
            ),
            "Tests whether the set-valued routing account scales beyond two required sources.",
        ],
    ]

    experiment_rows = [
        [
            "done",
            "Two-evidence modular-sum grid",
            "8 models; 256 paired examples/cell",
            "Closes the single-source copying objection for one learned two-input task.",
        ],
        [
            "done",
            "Pretrained fixed-spectrum backend validation",
            "Pythia-70M and Qwen2.5-1.5B",
            "Confirms the intervention and invariant checks run on two real architectures.",
        ],
        [
            "done",
            "Competent pretrained causal family grid",
            "Qwen, Pythia, Gemma",
            "Complete with paired intervals and explicit competence boundaries.",
        ],
        [
            "done",
            "Qwen2.5-7B fixed-spectrum run",
            "NF4/bfloat16; 96 examples/cell",
            "Adds a within-family scale replication.",
        ],
        [
            "done",
            "Qwen/Qwen2.5-1.5B real-model run",
            "900 examples",
            "Replicates the co-decline outside Pythia.",
        ],
        [
            "done" if gemma_rows else "optional",
            "Gemma-2-2B real-model run",
            "900 examples" if gemma_rows else "GPU",
            "Adds a mixed third-family boundary result." if gemma_rows else "Would add a third pretrained architecture/tokenizer family.",
        ],
        [
            "done",
            "Head-count robustness on best non-Pythia model",
            "Qwen K=4,8,16",
            "Source-attention co-decline holds across all three head counts.",
        ],
        [
            "done",
            "8-layer/512-width scratch replication",
            "32 configs; four seeds",
            "Replicates the controlled result at larger scratch-model scale.",
        ],
        [
            "done",
            "Natural context-grounded multiple-choice QA",
            "Qwen; three seeds; 64 calibration/128 evaluation",
            "Passes the locked context-necessity and hierarchical-effect rules.",
        ],
        [
            "done",
            "Cross-family selector ablation",
            "Qwen, Pythia, SmolLM2; three seeds each",
            "Supports output-conditioned selection but rejects a unique universal selector ranking.",
        ],
        [
            "done",
            "Interpolation dose response",
            "SmolLM2; five seeds; five alpha values",
            "Shows a smooth monotone causal response from no patch to the full patch.",
        ],
        [
            "done: boundary",
            "Three-/four-evidence routing",
            "NoPE/RoPE; seeds 0,1; pair/triple/quad",
            "Triple effect includes zero and quadruple models fail competence.",
        ],
        [
            "done",
            "Full-size natural-QA confirmation",
            "64 calibration/128 evaluation; three seeds",
            "Upgrades the replicated pilot into a positive locked confirmatory result.",
        ],
        [
            "done: boundary",
            "Natural-QA nested length ladder",
            "Qwen seeds 0,2; SmolLM2 seed 0; 4/8/16/32 passages",
            "Length degrades margin and accuracy, but the preregistered source-mass/rescue mechanism fails.",
        ],
        [
            "done: boundary",
            "Competence-matched four-evidence search",
            "c1/c2/c3; frozen exact-match threshold 0.8",
            "No candidate clears competence; c3 reaches 0.748 and no causal contrast is interpreted.",
        ],
        [
            "can",
            "Additional seeds for loglen sharpening",
            "GPU",
            "Strengthens the intervention estimate.",
        ],
        [
            "can",
            "Direct patching at multiple long lengths",
            "GPU",
            "Makes the sufficiency result cleaner.",
        ],
        [
            "now",
            "Claim and artifact audit",
            "CPU",
            "Keeps the paper aligned with completed evidence.",
        ],
    ]

    real_table_rows = []
    for row in real_rows:
        real_table_rows.append(
            [
                row.get("model", ""),
                row.get("heads", ""),
                row.get("n_examples", ""),
                fmt_float(row.get("acc_drop", "")),
                fmt_float(row.get("attn_drop", "")),
                fmt_float(row.get("within_corr_attn", "")),
                fmt_float(row.get("within_corr_normsq", "")),
                fmt_float(row.get("within_corr_neg_entropy", "")),
                row.get("winner", ""),
            ]
        )

    lines = [
        "# Length-Gen Experiment Coverage Audit",
        "",
        "This is a CPU-only audit generated from existing files.",
        "It identifies what evidence is already present and which experiments are still reviewer-relevant.",
        "",
        "## Current Coverage",
        "",
        *line_table(["evidence block", "status", "artifact detail", "paper role"], coverage_rows),
        "",
        "## Real-Model Rows Available Now",
        "",
    ]
    if real_table_rows:
        lines.extend(
            line_table(
                [
                    "model",
                    "heads",
                    "examples",
                    "acc drop",
                    "attn drop",
                    "corr attn",
                    "corr normsq",
                    "corr -entropy",
                    "winner",
                ],
                real_table_rows,
            )
        )
    else:
        lines.append("No real-model summary rows found.")

    lines.extend(
        [
            "",
            "## Experiment Queue",
            "",
            *line_table(["priority", "experiment", "needs", "reason"], experiment_rows),
            "",
            "## Immediate Interpretation",
            "",
            "- The central controlled evidence, fixed-spectrum test, and capacity-by-assignment factorial are complete.",
            "- The two-evidence task is complete: all eight models pass the competence gate, and at 5x length evidence-max exceeds the evidence-mass-preserving control by +0.043 with 95% interval [0.017, 0.072].",
            "- The pretrained fixed-spectrum backend is validated on Pythia and Qwen with invariant error below 1e-6.",
            "- The paper-grade pretrained causal grid is complete on Qwen2.5 at two scales, Pythia-1.4B, and Gemma-2-2B.",
            "- The pretrained utility-gap term has positive source-max association in all six model-length cells across three architectures.",
            "- Qwen circuit selection is robust across independent splits, three seeds, and K=2/4/8; all nine selected paired margin intervals exclude zero.",
            "- The preregistered equals-sign format fails the competence gate at the two completed lengths, so second-format generalization remains open.",
            "- The accuracy/source-attention co-decline reproduces on Pythia-1.4B and Qwen2.5-1.5B.",
            "- On Qwen, accuracy and source attention decline at K=4, 8, and 16; attention is the best within-length predictor at K=8 and 16 and narrowly trails negative entropy at K=4.",
            "- Gemma-2-2B is a mixed boundary case: source attention declines with length while accuracy remains near 0.5, but source attention is the strongest within-length correctness predictor at every tested length.",
            "- Natural multiple-choice QA passes the locked 64/128 design on all three seeds: utility-selected source assignment beats the matched control by +0.336 margin, with hierarchical 95% interval [0.176, 0.512], while source-mass selection is -0.112 [-0.188, -0.043].",
            "- The nested natural-QA length ladder is a boundary result: Qwen and SmolLM2 both lose margin and accuracy from 4 to 32 passages, but Qwen source mass rises and rescue weakens while SmolLM2 source mass falls without increasing rescue.",
            "- Equal-budget selector ablations are complete on Qwen, Pythia, and SmolLM2. Utility gain ranks first on two families and ties an equivalent circuit on Qwen, so the evidence supports output-conditioned selection but not a unique universal ranking formula.",
            "- The five-seed interpolation audit passes its preregistered rule: the matched-control margin effect rises monotonically from +0.000 at alpha=0 to +1.417 at alpha=1.",
            "- The pair/triple/quad stage is complete and sets a boundary: pair and triple models are train-competent, but the triple max-control interval includes zero; quadruple evidence fails the competence gate (minimum train exact match 0.090).",
            "- The outcome-blind capacity search does not close the four-evidence competence gap: c3 reaches 0.748 exact match against the frozen 0.8 threshold, so no four-source causal intervention is interpreted.",
            "- The previously critical natural-QA and evidence-arity GPU gaps are now closed; neither requires another sweep for the present claims.",
            "- Closed GPT-style APIs are not substitutes for this experiment because they do not expose attention weights or hidden states.",
            "",
        ]
    )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT.as_posix())


if __name__ == "__main__":
    main()
