# Null-Attractor Depth Diagnostic Report

Model: `Qwen/Qwen2.5-0.5B-Instruct`. Single-layer-selected forward passes (no generation): for each tested
layer, only that layer's attention is patched with the risk-gated null attractor (`thermosafety/intervention.py`), and `m_null`, entropy, and spectral gap are logged per prompt.
This tests whether the original null-attractor observables show the same depth-wise growth/
collapse curve found by the basin-energy diagnostic (see `results/basin_energy_diagnostic_note.md`).

## Per-Layer Summary

| layer | n | mean risk | jailbreak m_null | benign m_null | sep(m_null) | jailbreak entropy | benign entropy | sep(entropy) | jailbreak spectral gap | benign spectral gap | sep(spectral gap) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 38 | 0.281 | 0.0000 | 0.0000 | 0.0000 | 1.4289 | 1.4215 | 0.0074 | 0.4229 | 0.5018 | -0.0789 |
| 6 | 38 | 0.281 | 0.4283 | 0.3829 | 0.0453 | 1.0939 | 1.2539 | -0.1601 | 0.3722 | 0.3949 | -0.0228 |
| 10 | 38 | 0.281 | 0.6585 | 0.5000 | 0.1586 | 0.8622 | 1.2207 | -0.3585 | 0.3287 | 0.3985 | -0.0698 |
| 14 | 38 | 0.281 | 0.2961 | 0.1189 | 0.1772 | 1.4325 | 1.7898 | -0.3573 | 0.3218 | 0.4177 | -0.0959 |
| 16 | 38 | 0.281 | 0.1711 | 0.1039 | 0.0672 | 0.9240 | 0.9606 | -0.0367 | 0.2734 | 0.2699 | 0.0035 |
| 18 | 38 | 0.281 | 0.5994 | 0.4264 | 0.1730 | 0.8943 | 1.2000 | -0.3057 | 0.2348 | 0.3122 | -0.0774 |
| 20 | 38 | 0.281 | 0.5956 | 0.4297 | 0.1658 | 1.0310 | 1.3727 | -0.3418 | 0.3890 | 0.4471 | -0.0581 |
| 21 | 38 | 0.281 | 0.7222 | 0.6579 | 0.0643 | 0.6713 | 0.8151 | -0.1438 | 0.3540 | 0.4234 | -0.0694 |
| 22 | 38 | 0.281 | 0.0016 | 0.0001 | 0.0015 | 1.5644 | 1.6299 | -0.0655 | 0.4048 | 0.4963 | -0.0915 |
| 23 | 38 | 0.281 | 0.0422 | 0.0082 | 0.0340 | 1.5064 | 1.6143 | -0.1079 | 0.3450 | 0.4345 | -0.0895 |

## Reading

`sep(m_null)` = mean(m_null | jailbreak) - mean(m_null | benign); a positive, depth-growing
value here (mirroring the basin-energy depth curve) supports one unified depth-dependent
phase-transition story across both diagnostics. A collapse (sep dropping toward zero, entropy
cratering, or spectral gap saturating) at the final few layers would replicate the
compression-valley boundary effect already found by the basin-energy diagnostic.
