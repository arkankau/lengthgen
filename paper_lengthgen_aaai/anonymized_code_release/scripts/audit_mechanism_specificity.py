"""Rigorous re-test of the mechanism-specificity thesis, addressing four confounds in the
first-pass incremental-value audit (see the discussion in the session notes):

  1. Baseline-control asymmetry -> report PARTIAL R^2 (share of *remaining* variance thermo
     explains), not raw delta R^2, so different baseline strengths are comparable.
  2. Linear-control-is-a-bad-baseline -> the control baseline is FLEXIBLE (adds squares +
     pairwise interactions of the control features), so "thermo helps" cannot be merely
     "thermo captured nonlinearity the linear control missed".
  3. Small correlated n / leave-one-ROW-out leakage -> GROUPED leave-one-SETTING-out CV, plus
     bootstrap CIs by resampling settings, and a permutation test.
  4. Non-comparable targets -> a COMMON target defined identically for both families
     (repetition_collapse = 1 - unique_token_ratio), present in both datasets.

Pre-registered verdict: the mechanism-specificity gap is supported only if, on the common target,
null-attention's partial-R^2 bootstrap CI lower bound exceeds residual-steering's CI upper bound
(non-overlapping, null higher).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(row, key, default=0.0):
    v = row.get(key, default)
    if v in ("", None):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def load_family(name: str) -> dict:
    if name == "steering":
        rows = [r for r in read_csv("results/residual_steering_audit_expanded_detail.csv")
                if str(r.get("mode")) == "residual_steering"]
        controls = ["risk", "layer", "alpha", "gate", "steering_strength"]
        thermo = ["native_entropy", "native_specific_heat", "basin_margin", "basin_entropy", "steering_alignment"]
        group_key = lambda r: str(r.get("setting_id"))
    elif name == "null":
        rows = []
        for src in ["intervention_grid_qwen_detail", "intervention_grid_qwen_fixed_detail",
                    "intervention_grid_qwen_norepeat_detail"]:
            for r in read_csv(f"results/{src}.csv"):
                if str(r.get("mode")) == "null_intervention":
                    r["_src"] = src
                    rows.append(r)
        controls = ["risk", "eta_null", "lambda_penalty", "intervention_mix", "kappa", "beta_collapse"]
        thermo = ["mean_m_null", "mean_entropy", "mean_psi", "mean_spectral_gap"]
        group_key = lambda r: f"{r.get('_src')}::{r.get('setting_id')}"
    else:
        raise ValueError(name)
    # common target present in both: repetition collapse = 1 - unique_token_ratio
    for r in rows:
        r["_target"] = 1.0 - to_float(r, "unique_token_ratio", 1.0)
    return {"rows": rows, "controls": controls, "thermo": thermo, "group_key": group_key}


def expand_nonlinear(X: np.ndarray) -> np.ndarray:
    """Add squares and pairwise interactions to make the control baseline flexible."""
    cols = [X]
    cols.append(X * X)
    d = X.shape[1]
    for i in range(d):
        for j in range(i + 1, d):
            cols.append((X[:, i] * X[:, j])[:, None])
    return np.column_stack(cols)


def design(rows, feats, nonlinear=False):
    X = np.array([[to_float(r, f) for f in feats] for r in rows], dtype=float)
    if X.shape[0] == 0:
        return X
    if nonlinear and X.shape[1] > 0:
        X = expand_nonlinear(X)
    return X


def standardize(train, test):
    mu = train.mean(axis=0)
    sd = train.std(axis=0)
    keep = sd > 1e-9
    if not keep.any():
        return np.ones((train.shape[0], 1)), np.ones((test.shape[0], 1))
    tr = (train[:, keep] - mu[keep]) / sd[keep]
    te = (test[:, keep] - mu[keep]) / sd[keep]
    return np.column_stack([np.ones(len(tr)), tr]), np.column_stack([np.ones(len(te)), te])


def ridge_predict(Xtr, ytr, Xte, alpha=1.0):
    if len(ytr) < 2:
        return np.full(len(Xte), float(ytr.mean()) if len(ytr) else 0.0)
    Dtr, Dte = standardize(Xtr, Xte)
    P = np.eye(Dtr.shape[1]) * alpha
    P[0, 0] = 0.0
    coef = np.linalg.solve(Dtr.T @ Dtr + P, Dtr.T @ ytr)
    return Dte @ coef


def grouped_cv_r2(rows, feats, y, groups, nonlinear, alpha=1.0):
    """Leave-one-setting-out CV R^2."""
    uniq = sorted(set(groups))
    if len(uniq) < 3:
        return float("nan")
    preds = np.zeros(len(y))
    idx = np.arange(len(y))
    for g in uniq:
        te = np.array([gg == g for gg in groups])
        tr = ~te
        Xtr = design([rows[i] for i in idx[tr]], feats, nonlinear)
        Xte = design([rows[i] for i in idx[te]], feats, nonlinear)
        if Xtr.shape[1] == 0:
            preds[te] = y[tr].mean()
        else:
            preds[te] = ridge_predict(Xtr, y[tr], Xte, alpha)
    denom = float(np.sum((y - y.mean()) ** 2))
    if denom < 1e-12:
        return float("nan")
    return 1.0 - float(np.sum((y - preds) ** 2) / denom)


def partial_r2(fam, rows=None):
    rows = rows if rows is not None else fam["rows"]
    y = np.array([r["_target"] for r in rows], dtype=float)
    groups = [fam["group_key"](r) for r in rows]
    ctrl = grouped_cv_r2(rows, fam["controls"], y, groups, nonlinear=True)      # flexible control baseline
    full = grouped_cv_r2(rows, fam["controls"] + fam["thermo"], y, groups, nonlinear=True)
    # partial R^2 = fraction of remaining (control-unexplained) variance that thermo explains
    ctrl_c = max(ctrl, 0.0)  # clamp negative CV baselines to 0 headroom reference
    denom = 1.0 - ctrl_c
    part = (full - ctrl) / denom if denom > 1e-6 else float("nan")
    return {"ctrl_cv_r2": ctrl, "full_cv_r2": full, "delta_cv_r2": full - ctrl, "partial_r2": part}


def bootstrap_partial(fam, n_boot=300, seed=0):
    rng = np.random.default_rng(seed)
    rows = fam["rows"]
    groups = sorted(set(fam["group_key"](r) for r in rows))
    by_g = {g: [r for r in rows if fam["group_key"](r) == g] for g in groups}
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(len(groups), size=len(groups), replace=True)
        # relabel resampled groups uniquely so duplicates form distinct CV folds
        boot_rows = []
        for k, gi in enumerate(pick):
            for r in by_g[groups[gi]]:
                rr = dict(r)
                rr["_bootgrp"] = f"b{k}"
                boot_rows.append(rr)
        fam_b = {**fam, "group_key": lambda r: r["_bootgrp"]}
        p = partial_r2(fam_b, boot_rows)["partial_r2"]
        if p == p:  # not nan
            vals.append(p)
    vals = np.array(vals)
    return {"mean": float(vals.mean()), "lo": float(np.percentile(vals, 2.5)),
            "hi": float(np.percentile(vals, 97.5)), "n": len(vals)}


def permutation_p(fam, n_perm=300, seed=0):
    """Null: shuffle thermo rows (break their pairing with the target), recompute delta CV R^2."""
    rng = np.random.default_rng(seed)
    obs = partial_r2(fam)["delta_cv_r2"]
    rows = fam["rows"]
    thermo = fam["thermo"]
    thermo_vals = [[to_float(r, f) for f in thermo] for r in rows]
    ge = 0
    for _ in range(n_perm):
        perm = rng.permutation(len(rows))
        prows = []
        for i, r in enumerate(rows):
            rr = dict(r)
            for j, f in enumerate(thermo):
                rr[f] = thermo_vals[perm[i]][j]
            prows.append(rr)
        d = partial_r2({**fam, "rows": prows}, prows)["delta_cv_r2"]
        if d >= obs:
            ge += 1
    return {"observed_delta": obs, "p_value": (ge + 1) / (n_perm + 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=300)
    ap.add_argument("--n-perm", type=int, default=300)
    ap.add_argument("--output", default="results/mechanism_specificity_rigorous.md")
    args = ap.parse_args()

    out = ["# Mechanism-Specificity: Rigorous Re-Test", "",
           "Common target = repetition_collapse (1 - unique_token_ratio), identical in both families.",
           "Control baseline is FLEXIBLE (squares + interactions); CV is leave-one-SETTING-out; partial R^2",
           "= share of control-unexplained variance that thermo explains; CIs bootstrap over settings.", ""]
    res = {}
    for name in ["null", "steering"]:
        fam = load_family(name)
        ngroups = len(set(fam["group_key"](r) for r in fam["rows"]))
        base = partial_r2(fam)
        boot = bootstrap_partial(fam, n_boot=args.n_boot)
        perm = permutation_p(fam, n_perm=args.n_perm)
        res[name] = {"n": len(fam["rows"]), "groups": ngroups, **base, "boot": boot, "perm": perm}
        out.append(f"## {name}-attention" if name == "null" else f"## residual-{name}")
        out.append(f"- rows={len(fam['rows'])}, settings={ngroups}")
        out.append(f"- flexible-control CV R^2 = {base['ctrl_cv_r2']:.3f}; +thermo CV R^2 = {base['full_cv_r2']:.3f}; raw delta = {base['delta_cv_r2']:.3f}")
        out.append(f"- **partial R^2 = {base['partial_r2']:.3f}**  (bootstrap mean {boot['mean']:.3f}, 95% CI [{boot['lo']:.3f}, {boot['hi']:.3f}])")
        out.append(f"- permutation test: observed delta {perm['observed_delta']:.3f}, p = {perm['p_value']:.3f}")
        out.append("")

    n, s = res["null"], res["steering"]
    gap_supported = n["boot"]["lo"] > s["boot"]["hi"]
    out.append("## Pre-registered verdict")
    out.append(f"- null partial-R^2 CI = [{n['boot']['lo']:.3f}, {n['boot']['hi']:.3f}]")
    out.append(f"- steering partial-R^2 CI = [{s['boot']['lo']:.3f}, {s['boot']['hi']:.3f}]")
    out.append(f"- non-overlapping (null CI above steering CI): **{gap_supported}**")
    out.append("")
    out.append("MECHANISM-SPECIFICITY " + ("SUPPORTED" if gap_supported
               else "NOT SUPPORTED by non-overlapping CIs on the common target (report honestly)."))
    Path(args.output).write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
