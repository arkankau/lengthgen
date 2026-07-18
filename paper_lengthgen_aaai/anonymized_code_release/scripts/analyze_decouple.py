"""Decompose real-LM recall failures into attention / copy / readout loci (direction A).

Reads decouple_results.json (from colab/decouple_probe.py) and, among the FAILURES at each length,
partitions them into three mutually exclusive loci by a clean priority:

  readout-limited   : the value was present in the residual (logit-lens rank of vq < V_THR) yet not output
                      -> a SECOND locus beyond attention: later layers dropped a retrieved value.
  attention-limited : value absent AND retrieval-head attention on source is low (a_js < A_THR)
                      -> the paper's mechanism: attention never reached the source.
  copy-limited      : value absent BUT attention reached the source (a_js >= A_THR)
                      -> reached the source, but the OV/copy did not write the value to the residual.

A_THR is the "healthy attention" reference = median a_js among CORRECT examples at the shortest length.
V_THR = 10 (value counts as present if vq entered the top-10 of the logit lens at some layer).
Robustness to both thresholds is reported.

Usage: python scripts/analyze_decouple.py results/lengthgen/decouple_results.json
"""
import json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "results/lengthgen/decouple_results.json"
d = json.load(open(path))
recs = d["records"]
Ns = sorted({r["N"] for r in recs})


def classify(fails, a_thr, v_thr):
    att = cop = rea = 0
    for r in fails:
        if r["vrank"] < v_thr:
            rea += 1
        elif r["a_js"] < a_thr:
            att += 1
        else:
            cop += 1
    return att, cop, rea


# A_THR from correct examples at the shortest length
short = [r for r in recs if r["N"] == Ns[0] and r["correct"]]
A_THR = float(np.median([r["a_js"] for r in short])) if short else 0.3
V_THR = 10
print(f"model={d.get('model')}  heads={d.get('heads')}")
print(f"A_THR (median a_js among correct @N={Ns[0]}) = {A_THR:.3f}   V_THR (top-k) = {V_THR}\n")

print(f"{'N':>5} {'acc':>6} {'nfail':>6} | {'attn':>6} {'copy':>6} {'readout':>8}   (fractions of failures)")
frac_att, frac_cop, frac_rea, accs = [], [], [], []
for N in Ns:
    rN = [r for r in recs if r["N"] == N]
    fails = [r for r in rN if not r["correct"]]
    acc = float(np.mean([r["correct"] for r in rN]))
    accs.append(acc)
    nf = len(fails)
    if nf == 0:
        frac_att.append(0); frac_cop.append(0); frac_rea.append(0)
        print(f"{N:>5} {acc:>6.3f} {nf:>6} | (no failures)"); continue
    att, cop, rea = classify(fails, A_THR, V_THR)
    frac_att.append(att / nf); frac_cop.append(cop / nf); frac_rea.append(rea / nf)
    print(f"{N:>5} {acc:>6.3f} {nf:>6} | {att/nf:>6.2f} {cop/nf:>6.2f} {rea/nf:>8.2f}")

# instrument sanity: correct examples should have high a_js and low vrank
print("\ninstrument sanity (CORRECT examples): mean a_js / frac value-in-residual(top10)")
for N in Ns:
    cor = [r for r in recs if r["N"] == N and r["correct"]]
    if cor:
        print(f"  N={N:>4}  a_js={np.mean([r['a_js'] for r in cor]):.3f}  "
              f"value-present={np.mean([r['vrank'] < V_THR for r in cor]):.2f}  (n={len(cor)})")

# threshold robustness at the longest length
longN = Ns[-1]
fL = [r for r in recs if r["N"] == longN and not r["correct"]]
print(f"\nthreshold robustness at N={longN} (readout fraction of failures):")
for vt in (5, 10, 20):
    for am in (0.5, 1.0):
        att, cop, rea = classify(fL, A_THR * am, vt)
        n = max(1, len(fL))
        print(f"  V_THR={vt:>2} A_THR={A_THR*am:.3f} -> attn={att/n:.2f} copy={cop/n:.2f} readout={rea/n:.2f}")

# verdict
if frac_rea and frac_att:
    rea_long = frac_rea[-1]; att_long = frac_att[-1]
    print()
    if rea_long >= 0.25:
        print(f"VERDICT: a SECOND locus is present. At N={longN}, {rea_long:.0%} of failures have the value "
              f"in the residual yet unoutput (readout-limited); {att_long:.0%} are attention-limited. "
              f"Length-gen failure on recall is not attention alone.")
    else:
        print(f"VERDICT: failure is attention/copy dominated. At N={longN}, only {rea_long:.0%} of failures are "
              f"readout-limited; {att_long+frac_cop[-1]:.0%} are attention- or copy-limited (never wrote the "
              f"value). The paper's mechanism carries most of the failure.")

# figure: stacked failure-locus fractions vs N, with accuracy
fig, ax = plt.subplots(figsize=(4.4, 3.2))
x = np.arange(len(Ns))
ax.bar(x, frac_att, label="attention-limited", color="#c0392b")
ax.bar(x, frac_cop, bottom=frac_att, label="copy-limited", color="#e59866")
ax.bar(x, frac_rea, bottom=np.array(frac_att) + np.array(frac_cop), label="readout-limited", color="#2e86c1")
ax.set_xticks(x); ax.set_xticklabels(Ns)
ax.set_xlabel("context length $N$ (pairs)"); ax.set_ylabel("fraction of failures")
ax.set_title("Where recall fails, by locus")
ax.legend(fontsize=7, loc="lower left")
ax2 = ax.twinx()
ax2.plot(x, accs, "k--o", lw=1.5, ms=4, label="accuracy")
ax2.set_ylabel("accuracy"); ax2.set_ylim(0, 1)
fig.tight_layout()
out = path.rsplit("/", 1)[0] + "/fig_decouple.pdf" if "/" in path else "fig_decouple.pdf"
fig.savefig(out); fig.savefig(out.replace(".pdf", ".png"), dpi=140)
print(f"\nsaved figure: {out}")
