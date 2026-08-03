"""Iterative thermodynamic exploration with automated evaluation.

Question: does alignment leave a *thermodynamic* signature in attention -- a per-layer difference in
specific heat / entropy between a base model and its instruct-tuned sibling of the SAME architecture
(Qwen2.5-0.5B base vs Qwen2.5-0.5B-Instruct), so architecture is held fixed and only post-training
differs?

Verifier (frozen; the same null-control discipline that caught our earlier confound): an observable
"passes" ONLY if, at some layer, the base and instruct per-prompt distributions have NON-OVERLAPPING
bootstrap 95% CIs. That is a real, localized alignment signature, not noise. "Do nothing interesting"
(flat/overlapping profiles) fails. We also report whether specific heat has an interior peak (a
criticality signature) in each model.

State: results/thermo_explore_state.csv. Stop: a passing observable is found, or all are exhausted.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thermosafety.prompts import load_prompt_dir
from thermosafety.real_model import extract_trace_from_loaded, load_model
from thermosafety.thermo_observables import bootstrap_ci, trace_profiles

OBSERVABLES = ("specific_heat", "entropy")


def collect_profiles(model_name, device, local_files_only, prompts, max_length):
    torch, tokenizer, model = load_model(model_name, device=device, local_files_only=local_files_only)
    model.config._attn_implementation = "eager"  # needed for output_attentions
    # per observable: list over prompts of per-layer arrays
    per_obs: dict[str, list] = {o: [] for o in OBSERVABLES}
    n_layers = None
    for i, p in enumerate(prompts):
        trace = extract_trace_from_loaded(prompt=p, torch=torch, tokenizer=tokenizer, model=model,
                                          max_length=max_length, device=device)
        if not trace.attentions:
            raise RuntimeError("no attentions returned; ensure eager attention")
        prof = trace_profiles(trace.attentions)
        for o in OBSERVABLES:
            per_obs[o].append(np.array(prof[o]))
        n_layers = len(prof["specific_heat"])
        if (i + 1) % 20 == 0:
            print(f"    {model_name}: {i+1}/{len(prompts)}")
    # stack -> (n_prompts, n_layers)
    return {o: np.vstack(per_obs[o]) for o in OBSERVABLES}, n_layers


def interior_peak(profile_mean: np.ndarray) -> int:
    """Argmax excluding the two boundary layers (an interior peak = criticality signature)."""
    if len(profile_mean) <= 4:
        return int(np.argmax(profile_mean))
    interior = profile_mean[1:-1]
    return int(np.argmax(interior) + 1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Loop-engineered thermodynamic exploration.")
    ap.add_argument("--base-model", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--instruct-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--local-files-only", action="store_true")
    ap.add_argument("--suites", default="benign,benign_complex,direct_jailbreak,obfuscated_jailbreak,safety_research")
    ap.add_argument("--per-suite", type=int, default=6)
    ap.add_argument("--max-length", type=int, default=64)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--output", default="results/thermo_explore_state.csv")
    ap.add_argument("--profile-output", default="results/thermo_explore_profiles.csv")
    args = ap.parse_args()

    cases = []
    all_cases = load_prompt_dir("prompts")
    for s in [x.strip() for x in args.suites.split(",") if x.strip()]:
        cases.extend([c.prompt for c in all_cases if c.suite == s][: args.per_suite])
    print(f"prompts: {len(cases)}")

    print("collecting base profiles...")
    base, nlb = collect_profiles(args.base_model, args.device, args.local_files_only, cases, args.max_length)
    print("collecting instruct profiles...")
    inst, nli = collect_profiles(args.instruct_model, args.device, args.local_files_only, cases, args.max_length)
    assert nlb == nli, f"layer count mismatch {nlb} vs {nli}"
    n_layers = nlb
    rng = np.random.default_rng(args.seed)

    state_rows, profile_rows = [], []
    any_pass = False
    for o in OBSERVABLES:
        sig_layers = []
        for L in range(n_layers):
            b_mean, b_lo, b_hi = bootstrap_ci(base[o][:, L], n_boot=args.n_boot, rng=rng)
            i_mean, i_lo, i_hi = bootstrap_ci(inst[o][:, L], n_boot=args.n_boot, rng=rng)
            non_overlap = (b_hi < i_lo) or (i_hi < b_lo)
            if non_overlap:
                sig_layers.append(L)
            profile_rows.append({
                "observable": o, "layer": L,
                "base_mean": round(b_mean, 5), "base_lo": round(b_lo, 5), "base_hi": round(b_hi, 5),
                "instruct_mean": round(i_mean, 5), "instruct_lo": round(i_lo, 5), "instruct_hi": round(i_hi, 5),
                "significant": non_overlap,
            })
        base_peak = interior_peak(base[o].mean(axis=0))
        inst_peak = interior_peak(inst[o].mean(axis=0))
        passed = len(sig_layers) > 0
        any_pass = any_pass or passed
        max_eff = max((abs(base[o][:, L].mean() - inst[o][:, L].mean()) for L in range(n_layers)), default=0.0)
        state_rows.append({
            "observable": o, "n_significant_layers": len(sig_layers),
            "significant_layers": ";".join(map(str, sig_layers)),
            "max_abs_effect": round(max_eff, 5),
            "base_interior_peak_layer": base_peak, "instruct_interior_peak_layer": inst_peak,
            "passed": passed,
        })
        print(f"[{o}] significant layers: {len(sig_layers)}/{n_layers} {sig_layers} | "
              f"max|effect|={max_eff:.4f} | peak base L{base_peak} vs instruct L{inst_peak} -> "
              f"{'PASS' if passed else 'fail'}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(state_rows[0].keys()))
        w.writeheader(); w.writerows(state_rows)
    with open(args.profile_output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(profile_rows[0].keys()))
        w.writeheader(); w.writerows(profile_rows)

    if any_pass:
        print("\nSTOP: at least one observable shows a real (CI-separated) alignment signature.")
    else:
        print("\nSTOP: no observable passed the null control; no thermodynamic alignment signature found.")
    print(f"state: {args.output}  profiles: {args.profile_output}")


if __name__ == "__main__":
    main()
