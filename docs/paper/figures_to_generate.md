# Paper Figures and Tables

This file lists paper-facing figures/tables that can be generated from existing artifacts. Do not rerun model sweeps unless a required source file is missing.

## Figure 0: Key Paper Move Schematic

Purpose:

- Show the paper's central logic: null basin as diagnostic probe, null intervention as negative control, structured attractors/barriers as the future control object.
- Visually separate detection from generation control.

Source:

- `docs/paper/key_paper_move.md`
- `docs/paper/thermodynamic_attractor_derivations.md`

Status:

- Needs figure artwork.

## Figure 1: Null-Attractor Mechanism Diagram

Purpose:

- Show standard attention logits extended with a null key/value.
- Show risk-conditioned null bias reshaping the attention energy landscape.

Source:

- Method equations in `C:\Users\User\Downloads\CENTRAL_CODEX_PROMPT.md`
- Implementation in `thermosafety/attention.py`

Status:

- Needs figure artwork.

## Figure 2: Phase Curve, `m_null` vs Risk

Purpose:

- Show order-parameter jump in toy diagnostics and partial real-hidden-state transfer.

Source:

- `results/phase_transition_toy_expanded_m_null_vs_risk.svg`
- `results/phase_transition_distilgpt2_normalized_expanded_m_null_vs_risk.svg`
- `results/phase_transition_comparison.md`

Status:

- Existing SVGs available.

## Figure 3: Entropy and Spectral-Gap Diagnostics

Purpose:

- Show that collapse is visible in thermodynamic observables, not only null mass.

Source:

- `results/phase_transition_toy_expanded_entropy_vs_risk.svg`
- `results/phase_transition_toy_expanded_spectral_gap_vs_risk.svg`
- `results/phase_transition_distilgpt2_normalized_expanded_entropy_vs_risk.svg`
- `results/phase_transition_distilgpt2_normalized_expanded_spectral_gap_vs_risk.svg`

Status:

- Existing SVGs available.

## Table 1: Threshold Baseline vs Null-Attractor Diagnostic

Purpose:

- Separate classification thresholding from thermodynamic diagnosis.

Source:

- `results/baseline_comparison_summary.md`

Status:

- Existing table available.

## Table 2: Latent Probe Threshold Sweep

Purpose:

- Show why `R(X)` should be latent-trajectory based rather than only surface heuristic.

Source:

- `results/latent_probe_risk_upgrade_note.md`
- `results/latent_probe_threshold_grid_summary.csv`

Status:

- Existing table available.

## Table 3: Head-Local Selected-Head Response

Purpose:

- Show selected heads reduce benign null attraction compared with all-head intervention.

Source:

- `results/gpt2_medium_head_risk_separation.md`
- `results/gpt2_medium_head_selection_note.md`

Status:

- Existing table available.

## Table 4: Intervention Failure / Limitation Table

Purpose:

- Show that high null mass is not safe generation.
- Support detection-first claim boundary.

Source:

- `results/gpt2_family_behavior_failure_note.md`
- `results/gpt2_medium_selected_head_review.csv`

Status:

- Existing evidence available.
