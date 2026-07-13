# Null-Attractor Depth Diagnostic Report

Model: `Qwen/Qwen2.5-0.5B-Instruct`. Single-layer-selected forward passes (no generation): for each tested
layer, only that layer's attention is patched with the risk-gated null attractor (`thermosafety/intervention.py`), and `m_null`, entropy, and spectral gap are logged per prompt.
This tests whether the original null-attractor observables show the same depth-wise growth/
collapse curve found by the basin-energy diagnostic (see `results/basin_energy_diagnostic_note.md`).

A risk-forced-to-0 control pass runs automatically alongside the real-risk pass (see
`results/null_attractor_depth_diagnostic_note.md`, 'Risk=0 control'), to separate genuinely
risk-conditioned separation from layer-specific baseline null mass. Use
`risk_attributable_sep_m_null`, not raw `sep_m_null`, to select the strongest layer.

## Per-Layer Summary

| layer | n | mean risk | jailbreak m_null | benign m_null | sep(m_null) | baseline sep(m_null), risk=0 | risk-attributable sep(m_null) | baseline fraction (jailbreak) | sep(entropy) | sep(spectral gap) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 38 | 0.281 | 0.1869 | 0.0176 | 0.1693 | -0.0048 | 0.1740 | 6.76% | -0.1016 | -0.0789 |
| 6 | 38 | 0.281 | 0.2709 | 0.0282 | 0.2428 | -0.0046 | 0.2474 | 8.34% | -0.3462 | -0.0227 |
| 10 | 38 | 0.281 | 0.2812 | 0.0303 | 0.2510 | -0.0057 | 0.2567 | 8.24% | -0.3903 | -0.0697 |
| 14 | 38 | 0.281 | 0.2702 | 0.0307 | 0.2395 | -0.0089 | 0.2485 | 7.52% | -0.4124 | -0.0959 |
| 16 | 38 | 0.281 | 0.0960 | 0.0086 | 0.0873 | -0.0011 | 0.0884 | 7.57% | -0.0144 | 0.0034 |
| 18 | 38 | 0.281 | 0.2508 | 0.0245 | 0.2263 | -0.0056 | 0.2320 | 7.15% | -0.3234 | -0.0788 |
| 20 | 38 | 0.281 | 0.2701 | 0.0259 | 0.2442 | -0.0051 | 0.2493 | 7.36% | -0.2797 | -0.0639 |
| 21 | 38 | 0.281 | 0.2075 | 0.0192 | 0.1883 | -0.0045 | 0.1928 | 6.82% | -0.1858 | -0.0695 |
| 22 | 38 | 0.281 | 0.2272 | 0.0212 | 0.2060 | -0.0049 | 0.2109 | 6.98% | -0.1869 | -0.0914 |
| 23 | 38 | 0.281 | 0.2400 | 0.0223 | 0.2177 | -0.0057 | 0.2234 | 6.68% | -0.2579 | -0.0895 |

## Reading

`sep(m_null)` = mean(m_null | jailbreak) - mean(m_null | benign). `risk_attributable_sep_m_null` = sep(m_null, real risk) - sep(m_null, risk=0); this is the corrected observable to use for layer selection, since raw sep(m_null) can be inflated or masked by each layer's risk-independent baseline null mass (see the note above).
