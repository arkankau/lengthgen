# Qwen Activation-Patching Baseline

Model: Qwen/Qwen2.5-1.5B; seeds: 3; examples per seed: [128, 128, 128].

| Quantity | Mean | Seed range |
|---|---:|---:|
| Fixed-spectrum swap | +0.020836 | [+0.011861, +0.029618] |
| Source-value corruption | -7.663935 | [-7.779309, -7.486076] |
| Activation-patch rescue | +0.308314 | [+0.275385, +0.369315] |
| Median damage recovered | +0.028151 | [+0.025454, +0.033196] |
| Swap L1 displacement | +0.114185 | [+0.101311, +0.121825] |
| Activation RMS displacement | +0.117588 | [+0.114928, +0.119151] |
| Invariant error | +0.000000 | [+0.000000, +0.000000] |

The two interventions have different estimands. The fixed-spectrum swap measures assignment sensitivity on an unchanged prompt. Activation patching measures restoration after replacing the source value and importing clean selected-head outputs.
