from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_INPUTS = {
    "phase_transition": Path("results/phase_transition_comparison.md"),
    "baseline_comparison": Path("results/baseline_comparison_summary.md"),
    "latent_probe": Path("results/latent_probe_risk_upgrade_note.md"),
    "intervention_failure": Path("results/gpt2_family_behavior_failure_note.md"),
    "selected_heads": Path("results/gpt2_medium_head_selection_note.md"),
    "related_work": Path("docs/attention_thermodynamics_knowledge.md"),
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def first_markdown_table(text: str) -> str:
    rows = []
    in_table = False
    for line in text.splitlines():
        if line.strip().startswith("|"):
            rows.append(line)
            in_table = True
        elif in_table:
            break
    return "\n".join(rows)


def section_between(text: str, heading: str, next_heading_level: str = "##") -> str:
    pattern = re.compile(rf"^{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(rf"^{re.escape(next_heading_level)}\s+", text[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def short_excerpt(text: str, marker: str, max_lines: int = 8) -> str:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if marker in line:
            return "\n".join(lines[idx : idx + max_lines]).strip()
    return ""


def validate_inputs(paths: dict[str, Path]) -> list[str]:
    missing = [f"{name}: {path}" for name, path in paths.items() if not path.exists()]
    return missing


def build_report(paths: dict[str, Path]) -> str:
    missing = validate_inputs(paths)
    if missing:
        missing_lines = "\n".join(f"- {item}" for item in missing)
        raise FileNotFoundError(f"Missing required evidence inputs:\n{missing_lines}")

    phase = read_text(paths["phase_transition"])
    baseline = read_text(paths["baseline_comparison"])
    latent = read_text(paths["latent_probe"])
    failure = read_text(paths["intervention_failure"])
    heads = read_text(paths["selected_heads"])
    related = read_text(paths["related_work"])

    phase_table = first_markdown_table(phase)
    baseline_table = first_markdown_table(baseline)
    latent_table = first_markdown_table(section_between(latent, "## Focused threshold sweep"))
    head_ranking = first_markdown_table(section_between(heads, "## Head Ranking"))
    selected_head_table = first_markdown_table(section_between(heads, "## Selected-Head Grid"))
    failure_excerpt = section_between(failure, "## Interpretation")
    related_positioning = section_between(related, "## One-Sentence Positioning")

    lines = [
        "# Paper Evidence Report",
        "",
        "This report consolidates existing artifacts for the detection-first paper package. It does not rerun experiments and does not present generation intervention as a defense result.",
        "",
        "## Key Paper Move",
        "",
        "Null attraction reveals the thermodynamic response, but safe control requires structured attractors or barriers that reshape the energy landscape without destroying benign task basins.",
        "",
        "Source: `docs/paper/key_paper_move.md`",
        "",
        "## Locked Claim Boundary",
        "",
        "- Contribution: thermodynamic attention diagnostics for jailbreak-like latent states.",
        "- Negative control: generation-time null intervention shows thermodynamic detection does not automatically yield safe control.",
        "- Generation intervention artifacts are labeled as `diagnostic_ablation` or `failure_case` evidence, not defense results.",
        "",
        "## Attractor Derivation Scaffold",
        "",
        "Candidate attractors and barriers are derived in `docs/paper/thermodynamic_attractor_derivations.md`: null attractor, refusal attractor, safe-redirection attractor, high-entropy safety shell, free-energy barrier, metastable safety basin, and energy-landscape reshaping.",
        "",
        "Status: theory scaffold for next experiments, not evidence of working generation control.",
        "",
        "## Toy and Real Phase-Transition Evidence",
        "",
        phase_table,
        "",
        "Source: `results/phase_transition_comparison.md`",
        "",
        "## Threshold Baseline Comparison",
        "",
        baseline_table,
        "",
        "Source: `results/baseline_comparison_summary.md`",
        "",
        "## Latent Trajectory Risk Probe",
        "",
        latent_table,
        "",
        "Source: `results/latent_probe_risk_upgrade_note.md`",
        "",
        "## Negative Control: Intervention Failure",
        "",
        failure_excerpt,
        "",
        "Evidence label: `failure_case`.",
        "",
        "Source: `results/gpt2_family_behavior_failure_note.md`",
        "",
        "## Selected-Head Diagnostic Ablation",
        "",
        "Top head ranking:",
        "",
        head_ranking,
        "",
        "Selected-head grid:",
        "",
        selected_head_table,
        "",
        "Evidence label: `diagnostic_ablation`.",
        "",
        "Source: `results/gpt2_medium_head_selection_note.md`",
        "",
        "## Related-Work Anchor",
        "",
        related_positioning or short_excerpt(related, "We turn attention-as-energy"),
        "",
        "Source: `docs/attention_thermodynamics_knowledge.md`",
        "",
        "## Paper-Facing Figure/Table Checklist",
        "",
        "- Figure: `m_null` vs risk / threshold phase curve.",
        "- Figure: entropy and spectral-gap diagnostics.",
        "- Table: threshold baseline vs thermodynamic diagnostic.",
        "- Table: latent trajectory risk threshold sweep.",
        "- Table: head-local selected-head response.",
        "- Table: intervention failure showing high null mass is not safe generation.",
        "",
        "## Claim Audit",
        "",
        "- OK: null-attractor dynamics provide thermodynamic observables for detection/diagnosis.",
        "- OK: selected heads reduce global degeneration relative to all-head attraction.",
        "- OK: failed generation intervention motivates richer attractor semantics and barrier designs.",
        "- Not OK: claiming current intervention prevents jailbreaks.",
        "- Not OK: calling current outputs a deployed or validated defense.",
        "",
    ]
    return "\n".join(lines)


def write_report(output: Path, paths: dict[str, Path] | None = None) -> None:
    selected_paths = REQUIRED_INPUTS if paths is None else paths
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report(selected_paths), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a detection-first paper evidence report from existing artifacts.")
    parser.add_argument("--output", default="docs/paper/evidence_report.md")
    args = parser.parse_args()

    output = Path(args.output)
    write_report(output)
    print(f"wrote paper evidence report to {output}")


if __name__ == "__main__":
    main()
