# Length-Gen GPU Analysis

Per-token accuracy (mean over seeds). var-collapse = min-layer ratio var@longest/var@train:
`pre` = before the fix (raw collapse); `post` = after the fix (want ~1.0 => fix stabilizes it).
Benefit = PAIRED per-seed tok(fix)-tok(no-fix) at the length where the no-fix baseline breaks.

## addition (dependent-order)
| PE | fix | 1x | 2x | 3x | 10x | 20x | 50x | em@1x | var-collapse(pre/post) |
|---|---|---|---|---|---|---|---|---|---|
| nope | off | 1.00 | 0.18 | 0.10 | 0.03 | 0.01 | nan | 1.00 | nan / nan |
| nope | on | 1.00 | 0.27 | 0.14 | 0.08 | 0.06 | nan | 1.00 | nan / nan |
- nope: post-LN benefit at 20x = **+0.047** [+0.007, +0.086], 0/2 seeds negative
| rope | off | 1.00 | 0.11 | 0.09 | 0.08 | 0.07 | nan | 1.00 | nan / nan |
| rope | on | 1.00 | 0.13 | 0.09 | 0.07 | 0.06 | nan | 1.00 | nan / nan |
- rope: post-LN benefit at 20x = **-0.004** [-0.022, +0.014], 1/2 seeds negative

## argmax (invariant-order)
| PE | fix | 1x | 2x | 3x | 10x | 20x | 50x | em@1x | var-collapse(pre/post) |
|---|---|---|---|---|---|---|---|---|---|
| nope | off | 1.00 | 1.00 | 0.98 | 0.83 | 0.68 | 0.59 | 1.00 | 0.33 / 0.33 |
| nope | on | 1.00 | 0.99 | 0.97 | 0.80 | 0.67 | 0.58 | 1.00 | 0.20 / 0.99 |
- nope: post-LN benefit at 50x = **-0.013** [-0.035, +0.004], 2/4 seeds negative
| rope | off | 1.00 | 0.98 | 0.95 | 0.77 | 0.67 | 0.60 | 1.00 | 0.27 / 0.27 |
| rope | on | 1.00 | 0.98 | 0.96 | 0.67 | 0.59 | 0.57 | 1.00 | 0.45 / 1.00 |
- rope: post-LN benefit at 50x = **-0.033** [-0.066, -0.008], 4/4 seeds negative

## flagret (invariant-order)
| PE | fix | 1x | 2x | 3x | 10x | 20x | 50x | em@1x | var-collapse(pre/post) |
|---|---|---|---|---|---|---|---|---|---|
| nope | off | 1.00 | 1.00 | 0.94 | 0.67 | 0.63 | 0.60 | 1.00 | 0.47 / 0.47 |
| nope | on | 1.00 | 0.98 | 0.88 | 0.62 | 0.57 | 0.52 | 1.00 | 0.49 / 1.00 |
- nope: post-LN benefit at 50x = **-0.081** [-0.109, -0.043], 4/4 seeds negative
| rope | off | 1.00 | 1.00 | 0.99 | 0.65 | 0.60 | 0.56 | 1.00 | 0.48 / 0.48 |
| rope | on | 1.00 | 1.00 | 0.96 | 0.53 | 0.51 | 0.50 | 1.00 | 0.43 / 1.00 |
- rope: post-LN benefit at 50x = **-0.061** [-0.074, -0.047], 4/4 seeds negative

## Verdict
- addition (dependent): best post-LN benefit where baseline breaks = 0.047
- argmax (invariant): best post-LN benefit where baseline breaks = -0.013
- flagret (invariant): best post-LN benefit where baseline breaks = -0.061

**GENUINE NULL: across order-invariant tasks the fix stabilizes downstream variance (post-collapse ~1.0) yet yields no length-gen benefit (best -0.013); harmful under RoPE. Variance stabilization is decoupled from length generalization -> scopes/contests 2504.02827.**

---
## STRENGTHENED (4 seeds, 50x ladder, pre/post variance) — 2026-07-11 — FINAL
Data: results/lengthgen/gpu_results.json (argmax+flagret @4 seeds + addition @2 seeds; 40 configs).
2-seed backup: gpu_results_2seed_backup.json.
- Fix stabilizes downstream variance (post-collapse ratio 0.99-1.00) while raw variance collapses to
  0.20-0.49 -> the fix mechanically works.
- post-LN benefit @50x (paired per-seed): argmax nope -0.013 [2/4 neg], argmax rope -0.033 [4/4 neg],
  flagret nope -0.081 [4/4 neg], flagret rope -0.061 [4/4 neg]. NOT ONE order-invariant cell positive.
- addition: fix gives +0.047 per-token bump on nope but em stays 0 (no rescue); rope -0.004.
VERDICT unchanged and hardened: variance stabilization is decoupled from length generalization.
