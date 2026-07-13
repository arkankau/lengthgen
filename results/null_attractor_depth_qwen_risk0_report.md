# Null-Attractor Depth Diagnostic Report

Model: `Qwen/Qwen2.5-0.5B-Instruct`. Single-layer-selected forward passes (no generation): for each tested
layer, only that layer's attention is patched with the risk-gated null attractor (`thermosafety/intervention.py`), and `m_null`, entropy, and spectral gap are logged per prompt.
This tests whether the original null-attractor observables show the same depth-wise growth/
collapse curve found by the basin-energy diagnostic (see `results/basin_energy_diagnostic_note.md`).

## Per-Layer Summary

| layer | n | mean risk | jailbreak m_null | benign m_null | sep(m_null) | jailbreak entropy | benign entropy | sep(entropy) | jailbreak spectral gap | benign spectral gap | sep(spectral gap) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 38 | 0.281 | 0.0000 | 0.0000 | 0.0000 | 1.8059 | 1.4395 | 0.3665 | 0.4992 | 0.5047 | -0.0056 |
| 6 | 38 | 0.281 | 0.3562 | 0.3775 | -0.0213 | 1.5076 | 1.2776 | 0.2299 | 0.4513 | 0.3982 | 0.0531 |
| 10 | 38 | 0.281 | 0.4123 | 0.4867 | -0.0744 | 1.5606 | 1.2591 | 0.3015 | 0.4162 | 0.4012 | 0.0150 |
| 14 | 38 | 0.281 | 0.0957 | 0.1139 | -0.0181 | 2.0421 | 1.8090 | 0.2331 | 0.4216 | 0.4217 | -0.0000 |
| 16 | 38 | 0.281 | 0.0571 | 0.1018 | -0.0447 | 1.2720 | 0.9743 | 0.2977 | 0.3096 | 0.2714 | 0.0382 |
| 18 | 38 | 0.281 | 0.3867 | 0.4181 | -0.0314 | 1.4577 | 1.2270 | 0.2306 | 0.3234 | 0.3158 | 0.0075 |
| 20 | 38 | 0.281 | 0.3517 | 0.4187 | -0.0670 | 1.7272 | 1.4019 | 0.3253 | 0.4772 | 0.4503 | 0.0269 |
| 21 | 38 | 0.281 | 0.5535 | 0.6476 | -0.0941 | 1.1960 | 0.8463 | 0.3497 | 0.4634 | 0.4256 | 0.0378 |
| 22 | 38 | 0.281 | 0.0001 | 0.0001 | 0.0000 | 1.9898 | 1.6458 | 0.3440 | 0.5251 | 0.5004 | 0.0248 |
| 23 | 38 | 0.281 | 0.0080 | 0.0080 | -0.0000 | 1.9151 | 1.6299 | 0.2853 | 0.4557 | 0.4382 | 0.0175 |

## Reading

`sep(m_null)` = mean(m_null | jailbreak) - mean(m_null | benign); a positive, depth-growing
value here (mirroring the basin-energy depth curve) supports one unified depth-dependent
phase-transition story across both diagnostics. A collapse (sep dropping toward zero, entropy
cratering, or spectral gap saturating) at the final few layers would replicate the
compression-valley boundary effect already found by the basin-energy diagnostic.
