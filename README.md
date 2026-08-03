# Null-Attractor Attention Toy Repo

Phase 1 prototype for testing whether a risk-conditioned null slot can behave like an attention order parameter.

This is a mechanism test, not a validated LLM defense. The current `R(X)` is a transparent heuristic used to reshape a toy attention energy landscape and measure collapse into an appended null slot.

## Run

```powershell
python -m thermosafety.runner --output results/toy_diagnostics.csv
python scripts/sweep_thresholds.py --output results/threshold_sweep.csv
python scripts/sweep_ablation.py --output results/ablation_sweep.csv
python scripts/plot_phase1.py --diagnostics results/toy_diagnostics.csv --output-dir results/figures
python scripts/make_report.py --output results/phase1_report.md
python -m unittest discover -s tests -q
```

If `python` is not on PATH, activate the project environment and use its interpreter directly.

## Outputs

- `results/toy_diagnostics.csv`
- `results/threshold_sweep.csv`
- `results/ablation_sweep.csv`
- `results/figures/*.svg`
- `results/phase1_report.md`
- `results/hf_diagnostics.csv` after optional Phase 2 dependencies are installed
- `results/toy_vs_real_report.md` after running the comparison script

## Current Default Result

At the default operating point, benign-complex prompts avoid collapse while direct jailbreak prompts collapse. Obfuscated and long-context jailbreak suites partially collapse, which is the intended bottleneck signal for replacing the heuristic risk score with a latent trajectory probe.

## Optional Phase 2

Phase 2 runs the same null-attractor diagnostic on hidden states from a small HuggingFace causal LM. This is still post-hoc analysis; it does not patch model attention logits during generation.

```powershell
python -m pip install torch transformers
python -m thermosafety.hf_runner --model sshleifer/tiny-gpt2 --risk-source mixed --output results/hf_diagnostics.csv
python scripts/compare_toy_real.py --toy results/toy_diagnostics.csv --real results/hf_diagnostics.csv --output results/toy_vs_real_report.md
python scripts/calibrate_hf_null.py --model sshleifer/tiny-gpt2
python scripts/train_trajectory_probe.py --model sshleifer/tiny-gpt2 --feature-set latent
python scripts/analyze_calibration_errors.py
python scripts/analyze_phase_transition.py --diagnostics results/toy_diagnostics_expanded.csv --output-prefix results/phase_transition_toy_expanded
python scripts/compare_phase_transitions.py
python -m thermosafety.intervention_runner --model distilgpt2 --local-files-only --suites direct_jailbreak --limit 1 --layers 4,5
```

`--risk-source surface` uses the Phase 1 heuristic, `--risk-source trajectory` uses hidden-state trajectory features only, and `--risk-source mixed` combines both.
