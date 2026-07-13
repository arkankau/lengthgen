# Null-Attractor Depth Diagnostic Report

Model: `distilgpt2`. Single-layer-selected forward passes (no generation): for each tested
layer, only that layer's attention is patched with the risk-gated null attractor (`thermosafety/intervention.py`), and `m_null`, entropy, and spectral gap are logged per prompt.
This tests whether the original null-attractor observables show the same depth-wise growth/
collapse curve found by the basin-energy diagnostic (see `results/basin_energy_diagnostic_note.md`).

## Per-Layer Summary

| layer | n | mean risk | jailbreak m_null | benign m_null | sep(m_null) | jailbreak entropy | benign entropy | sep(entropy) | jailbreak spectral gap | benign spectral gap | sep(spectral gap) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 38 | 0.281 | 0.3515 | 0.1395 | 0.2120 | 1.2759 | 1.7514 | -0.4755 | 0.4576 | 0.5459 | -0.0883 |
| 1 | 38 | 0.281 | 0.4641 | 0.2077 | 0.2564 | 1.4488 | 1.9874 | -0.5386 | 0.6722 | 0.7308 | -0.0586 |
| 2 | 38 | 0.281 | 0.5297 | 0.2808 | 0.2489 | 1.1983 | 1.7538 | -0.5555 | 0.5763 | 0.6151 | -0.0389 |
| 3 | 38 | 0.281 | 0.5025 | 0.1950 | 0.3075 | 1.1445 | 1.7033 | -0.5588 | 0.7210 | 0.7042 | 0.0167 |
| 4 | 38 | 0.281 | 0.4205 | 0.1169 | 0.3036 | 1.1496 | 1.4331 | -0.2835 | 0.7713 | 0.7619 | 0.0094 |
| 5 | 38 | 0.281 | 0.3231 | 0.0461 | 0.2770 | 1.4573 | 1.8216 | -0.3643 | 0.7233 | 0.6959 | 0.0274 |

## Reading

`sep(m_null)` = mean(m_null | jailbreak) - mean(m_null | benign); a positive, depth-growing
value here (mirroring the basin-energy depth curve) supports one unified depth-dependent
phase-transition story across both diagnostics. A collapse (sep dropping toward zero, entropy
cratering, or spectral gap saturating) at the final few layers would replicate the
compression-valley boundary effect already found by the basin-energy diagnostic.
