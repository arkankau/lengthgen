# Intervention-Family Incremental-Value Comparison

Question: after simple controls are fitted first, which intervention family retains stronger thermodynamic incremental value?

| target | null-attention CV delta R2 | null best thermo | residual-steering CV delta R2 | residual best thermo | gap |
|---|---:|---|---:|---|---:|
| utility_loss | 0.109 | thermo_collapse | 0.010 | basin_margin | 0.099 |
| coherence | 0.102 | thermo_collapse | 0.007 | basin_margin | 0.096 |
| collapse_failure | 0.069 | mean_entropy | -0.001 | steering_alignment | 0.071 |

Interpretation: null-attention retains a larger out-of-sample thermodynamic residual signal on the shared degradation targets. Residual steering shows only tiny or negative incremental value after controlling for risk and steering strength.
