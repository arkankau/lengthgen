# Pretrained Utility Reviewer Audit

All figures below use saved evaluation records. The underlying circuits were selected on separate calibration examples.

| Model | Eval. examples | Pearson | Slope | Intercept | MAE | Source already max in all selected heads | Median transferred mass | P90 transferred mass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma-2-2B | 384 | 0.738 | 0.947 | +0.001 | 0.112 | 21.9% | 0.312 | 0.728 |
| Pythia-1.4B | 384 | 0.670 | 0.885 | +0.184 | 0.724 | 4.2% | 0.346 | 0.653 |
| Qwen2.5-1.5B | 384 | 0.827 | 0.735 | +0.218 | 0.378 | 7.8% | 0.783 | 2.268 |

The slope and error statistics are calibration diagnostics, not additional evidence of causal effect. A source-already-max row produces a zero source-max intervention for the selected circuit and is retained rather than discarded.
