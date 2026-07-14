"""Direction B analysis: does the attention logit gap predict the length-gen break point?

For each config we fit Delta(n) = intercept + slope * ln(n) on SHORT lengths only (in and just past the
training regime, L <= FIT_MAX * l_train), then extrapolate to the predicted break n*_pred = exp(-intercept/
slope) (where Delta crosses 0, i.e. a_j* -> 0.5). We compare it to the OBSERVED break n*_obs (where exact-match
crosses 0.5, linearly interpolated in log-length). A declining gap (slope<0) predicts a finite break; a flat or
rising gap (slope>=0, e.g. under sharpening) predicts no break in range.

Usage: python scripts/analyze_break.py results/lengthgen/break_results.json
"""
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIT_MAX = 4  # fit Delta(n) on lengths up to FIT_MAX * l_train (short, in-regime), then extrapolate

path = sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/break_results.json"
res = json.load(open(path))


def cross_half(xs, ys):
    """length where ys crosses 0.5 from above, linearly interpolated in ln(x); None if never."""
    for i in range(1, len(ys)):
        if ys[i - 1] >= 0.5 > ys[i]:
            lx0, lx1 = np.log(xs[i - 1]), np.log(xs[i])
            t = (ys[i - 1] - 0.5) / (ys[i - 1] - ys[i] + 1e-12)
            return float(np.exp(lx0 + t * (lx1 - lx0)))
    return None


rows = []
print(f"{'task':>8} {'pe':>5} {'scale':>7} {'seed':>4} | {'slope':>7} {'n*_pred':>9} {'n*_obs':>8}")
for r in res:
    c = r["cfg"]; s = r["series"]
    L = c["l_train"]
    Ls = np.array([p["L"] for p in s], float)
    dl = np.array([p["delta"] for p in s], float)
    em = np.array([p["em"] for p in s], float)
    fit = Ls <= FIT_MAX * L
    n_pred = None; slope = float("nan")
    if fit.sum() >= 2 and np.all(np.isfinite(dl[fit])):
        slope, intercept = np.polyfit(np.log(Ls[fit]), dl[fit], 1)
        if slope < -1e-6:
            n_pred = float(np.exp(-intercept / slope))
    n_obs = cross_half(Ls, em)
    rows.append({**c, "slope": slope, "n_pred": n_pred, "n_obs": n_obs})
    ps = f"{n_pred:9.1f}" if n_pred else "     none"
    os = f"{n_obs:8.1f}" if n_obs else "    none"
    print(f"{c['task']:>8} {c['pe']:>5} {c['scale']:>7} {c['seed']:>4} | {slope:+7.3f} {ps} {os}")

# agreement on the baselines that actually break (both predicted and observed finite)
both = [r for r in rows if r["scale"] == "none" and r["n_pred"] and r["n_obs"]]
if len(both) >= 2:
    lp = np.log10([r["n_pred"] for r in both]); lo = np.log10([r["n_obs"] for r in both])
    cc = float(np.corrcoef(lp, lo)[0, 1]) if np.std(lp) > 1e-9 and np.std(lo) > 1e-9 else float("nan")
    ratios = [r["n_pred"] / r["n_obs"] for r in both]
    print(f"\nbaselines that break: n={len(both)}  corr(log n*_pred, log n*_obs)={cc:+.3f}  "
          f"median ratio pred/obs={np.median(ratios):.2f}")

# H-B3: does sharpening flatten the gap and push the break out?
print("\nsharpening effect (slope of Delta vs ln n; less negative = gap holds up):")
for task in sorted({r["task"] for r in rows}):
    for pe in sorted({r["pe"] for r in rows if r["task"] == task}):
        base = [r for r in rows if r["task"] == task and r["pe"] == pe and r["scale"] == "none"]
        shrp = [r for r in rows if r["task"] == task and r["pe"] == pe and r["scale"] == "loglen"]
        if base and shrp:
            sb = np.mean([r["slope"] for r in base]); ss = np.mean([r["slope"] for r in shrp])
            pb = np.median([r["n_pred"] for r in base if r["n_pred"]] or [float("nan")])
            psh = [r["n_pred"] for r in shrp if r["n_pred"]]
            psh = np.median(psh) if psh else float("inf")
            print(f"  {task:>8} {pe:>5}: slope none={sb:+.3f} -> loglen={ss:+.3f}   "
                  f"n*_pred none={pb:.0f} -> loglen={'inf(no break)' if psh==float('inf') else f'{psh:.0f}'}")

# verdict
if both:
    lp = np.log10([r["n_pred"] for r in both]); lo = np.log10([r["n_obs"] for r in both])
    cc = float(np.corrcoef(lp, lo)[0, 1]) if np.std(lp) > 1e-9 and np.std(lo) > 1e-9 else float("nan")
    print()
    if cc >= 0.6 and 0.3 <= np.median([r["n_pred"] / r["n_obs"] for r in both]) <= 3:
        print(f"VERDICT: the logit gap PREDICTS the break. Fit on short lengths only, the extrapolated break "
              f"tracks the observed break across configs (corr={cc:+.2f}).")
    else:
        print(f"VERDICT: partial. The gap declines and predicts a finite break, but the predicted and observed "
              f"break lengths agree only loosely (corr={cc:+.2f}); report honestly.")

# figure: predicted vs observed break (log-log), baselines
fig, ax = plt.subplots(1, 2, figsize=(8.2, 3.4))
b = both
if b:
    xp = [r["n_obs"] for r in b]; yp = [r["n_pred"] for r in b]
    ax[0].scatter(xp, yp, c="#2e86c1", zorder=3)
    lo_, hi_ = min(xp + yp) * 0.6, max(xp + yp) * 1.6
    ax[0].plot([lo_, hi_], [lo_, hi_], "k--", lw=1, label="y = x")
    ax[0].set_xscale("log"); ax[0].set_yscale("log")
    ax[0].set_xlabel("observed break length"); ax[0].set_ylabel("predicted break length")
    ax[0].set_title("Predicted vs observed break"); ax[0].legend(fontsize=8)
# Delta vs ln n for one representative baseline + its sharpened twin
rep = next((r for r in res if r["cfg"]["scale"] == "none"), None)
if rep:
    c = rep["cfg"]; twin = next((r for r in res if r["cfg"]["task"] == c["task"] and
                                 r["cfg"]["pe"] == c["pe"] and r["cfg"]["seed"] == c["seed"] and
                                 r["cfg"]["scale"] == "loglen"), None)
    for r, col, lab in [(rep, "#c0392b", "baseline"), (twin, "#27ae60", "sharpened")]:
        if r is None:
            continue
        s = r["series"]; Ls = np.array([p["L"] for p in s], float)
        dl = np.array([p["delta"] for p in s], float)
        ax[1].plot(np.log(Ls), dl, "o-", color=col, label=lab)
    ax[1].axhline(0, color="gray", lw=0.8, ls=":")
    ax[1].set_xlabel("ln(context length)"); ax[1].set_ylabel(r"attention logit gap $\Delta$")
    ax[1].set_title(f"Gap vs length ({c['task']}, {c['pe']})"); ax[1].legend(fontsize=8)
fig.tight_layout()
out = path.rsplit("/", 1)[0] + "/fig_break.pdf" if "/" in path else "fig_break.pdf"
fig.savefig(out); fig.savefig(out.replace(".pdf", ".png"), dpi=140)
print(f"\nsaved figure: {out}")
