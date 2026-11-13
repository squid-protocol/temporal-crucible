#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ETYP-LABEL (EXPLORATORY, development): does a commit's edit-type vector look like a fix?

    python tools/etyp_label.py fit   --repo curl --in /scratch/etyp_curl.jsonl --model docs/etyp_label_model.json
    python tools/etyp_label.py eval  --repo libarchive --in /scratch/etyp_libarchive.jsonl --model docs/etyp_label_model.json
    python tools/etyp_label.py score --pool-repo libxml2 --in /scratch/etyp_libxml2.jsonl --model ... --out scores.json

**Exploratory. No registration, no p-value. `fit` and `eval` run on the burned repos (curl, libarchive)
only.** `score` reads no label at all: it writes a score per commit for a repo the model has never seen,
which is what a registered test would then compare with hand judgments.

Why. `other-fix` is 85-97% of the outcome mass and FIXLIKE v3c, which reads only the commit message, is
0.761 precise on it (`docs/otherfix_audit.md`). `docs/etyp_fix.md` found fixes have a type signature
(in-place LOGIC edits and added branches; little rewiring, renaming or formatting). The type vector
never reads the message, so it is an independent second instrument for the same question.

Model: L2 logistic regression on the commit's atomic-label fractions (26 named labels; the residuals
and the redundant primary-family columns are left out), fitted with plain Newton steps so the weights
are a short readable table. Three variants are reported so the type signal cannot hide behind size:

    size   log2(function edits), log2(tokens changed + 1)        -- the baseline to beat
    type   the label fractions only
    both   type + size

Target in `fit` / `eval` is the MESSAGE label (any v3c-kept fix class vs `not a fix`; v3c-dropped
commits are in neither). That label is itself ~0.76 precise, so the AUC against it is a floor on
agreement with a noisy reference, not accuracy. The honest test needs hand judgments on unseen repos;
that is the registered step, not this one.

Needs numpy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edit_types as et          # noqa: E402
import etyp_fix as ef            # noqa: E402

ATOMS = [l for l in et.LABELS if l not in ("EXPR_EDIT", "UNCLASSIFIED")]
SIZE = ["log2_edits", "log2_tokens"]
VARIANTS = {"size": SIZE, "type": ATOMS, "both": ATOMS + SIZE}
L2 = 1.0


def design(rows: list[dict]):
    """(shas, {feature: column}, commit times) for every commit with 1-50 function edits."""
    shas, X, n, ct, mag = ef.commit_matrix(rows)
    cols = {a: X[:, ef.COLS.index(a)] for a in ATOMS}
    cols["log2_edits"] = np.log2(n)
    cols["log2_tokens"] = np.log2(mag + 1)
    return shas, cols, ct


def matrix(cols: dict, feats: list[str], mu=None, sd=None):
    M = np.column_stack([cols[f] for f in feats])
    if mu is None:
        mu, sd = M.mean(axis=0), M.std(axis=0)
        sd[sd == 0] = 1.0
    return (M - mu) / sd, mu, sd


def fit_logit(Z: np.ndarray, y: np.ndarray, l2: float = L2):
    """Newton-Raphson for L2 logistic regression; the intercept is not penalised."""
    A = np.column_stack([np.ones(len(Z)), Z])
    w = np.zeros(A.shape[1])
    pen = np.eye(A.shape[1]) * l2
    pen[0, 0] = 0.0
    for _ in range(50):
        p = 1 / (1 + np.exp(-A @ w))
        step = np.linalg.solve(A.T @ (A * (p * (1 - p))[:, None]) + pen, A.T @ (y - p) - pen @ w)
        w += step
        if np.abs(step).max() < 1e-8:
            break
    return w


def auc(score: np.ndarray, y: np.ndarray) -> float:
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score))
    s = score[order]
    i = 0
    while i < len(s):                               # midranks for ties
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i: j + 1]] = (i + j) / 2 + 1
        i = j + 1
    pos = y.sum()
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2) / (pos * (len(y) - pos)))


def labelled(repo: str, shas: list[str], ct, target: str = "fix"):
    """(y, keep, dropped, masks) from the message label, on the same groups etyp_fix.py uses.

    target "fix": 1 = v3c-kept fix of any class, 0 = the non-fix reference (inside the labelled window,
    not v3c-dropped, subject not cosmetic). Commits after the event harvest are in neither: the first
    run counted 308 of them as "not a fix" (docs/etyp_review.md).
    target "extrinsic" / "regression": 1 = that class, 0 = every other fix; non-fixes are kept out.
    """
    m = ef.masks(repo, shas, ct)
    if target == "fix":
        return m["fix"].astype(float), m["fix"] | m["nonfix"], m["dropped"] & m["window"], m
    return ((m["cls"] == target) & m["window"]).astype(float), m["fix"], m["dropped"] & m["window"], m


def predict(model: dict, variant: str, cols: dict) -> np.ndarray:
    m = model["variants"][variant]
    Z, _mu, _sd = matrix(cols, m["features"], np.array(m["mu"]), np.array(m["sd"]))
    return 1 / (1 + np.exp(-(m["intercept"] + Z @ np.array(m["weights"]))))


def cmd_fit(a) -> int:
    shas, cols, ct = design(et.load(a.inp))
    y, keep, _dropped, _m = labelled(a.repo, shas, ct, a.target)
    model = {"trained_on": a.repo, "l2": L2, "commits": int(keep.sum()), "positives": int(y[keep].sum()),
             "target": a.target, "variants": {}}
    print(f"fit on {a.repo}, target {a.target}: {int(keep.sum()):,} commits, {int(y[keep].sum()):,} "
          f"positives (EXPLORATORY)")
    for name, feats in VARIANTS.items():
        Z, mu, sd = matrix({k: v[keep] for k, v in cols.items()}, feats)
        w = fit_logit(Z, y[keep])
        model["variants"][name] = {"features": feats, "mu": mu.tolist(), "sd": sd.tolist(),
                                   "intercept": float(w[0]), "weights": w[1:].tolist(),
                                   "auc_in_sample": auc(Z @ w[1:], y[keep])}
        print(f"  {name:5} in-sample AUC {model['variants'][name]['auc_in_sample']:.3f}")
    m = model["variants"]["both"]
    # A fixed operating point, chosen on the training repo only: the score above which the top third sits.
    model["threshold_both"] = float(np.quantile(predict(model, "both", {k: v[keep] for k, v in cols.items()}), 2 / 3))
    print("\n  weights of `both`, per standard deviation (positive = more fix-like):")
    for f, wt in sorted(zip(m["features"], m["weights"]), key=lambda kv: -kv[1]):
        print(f"    {f:15} {wt:+.3f}")
    Path(a.model).write_text(json.dumps(model, indent=1, sort_keys=True) + "\n")
    return 0


def cmd_eval(a) -> int:
    model = json.loads(Path(a.model).read_text())
    shas, cols, ct = design(et.load(a.inp))
    y, keep, dropped, m = labelled(a.repo, shas, ct, model["target"])
    rng = np.random.default_rng(ef.SEED)
    print(f"eval on {a.repo} with a model fitted on {model['trained_on']}, target {model['target']}: "
          f"{int(keep.sum()):,} commits, {int(y[keep].sum()):,} positives "
          f"(EXPLORATORY; the target is a message label, not ground truth)")
    out = {"repo": a.repo, "trained_on": model["trained_on"], "target": model["target"],
           "commits": int(keep.sum()), "positives": int(y[keep].sum()), "auc": {}}
    scores = {v: predict(model, v, cols) for v in VARIANTS}
    idx = np.flatnonzero(keep)
    for v in VARIANTS:
        boots = [auc(scores[v][b], y[b]) for b in (rng.choice(idx, len(idx)) for _ in range(200))]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out["auc"][v] = {"auc": auc(scores[v][keep], y[keep]), "lo": float(lo), "hi": float(hi)}
        print(f"  {v:5} AUC {out['auc'][v]['auc']:.3f}  [{lo:.3f}, {hi:.3f}]")
    d = [auc(scores["both"][b], y[b]) - auc(scores["size"][b], y[b])
         for b in (rng.choice(idx, len(idx)) for _ in range(200))]
    out["both_minus_size"] = {"diff": out["auc"]["both"]["auc"] - out["auc"]["size"]["auc"],
                              "lo": float(np.percentile(d, 2.5)), "hi": float(np.percentile(d, 97.5))}
    print(f"  both - size  {out['both_minus_size']['diff']:+.3f}  "
          f"[{out['both_minus_size']['lo']:+.3f}, {out['both_minus_size']['hi']:+.3f}]")
    if model["target"] != "fix":
        if a.json:
            Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        return 0
    thr, s = model["threshold_both"], scores["both"]
    cls = np.where(m["window"], m["cls"], "")
    print(f"\n  share scoring above the fixed threshold ({thr:.3f}, the training repo's top third):")
    out["above"] = {}
    for name, mask in (("not a fix", keep & (y == 0)), ("dropped by v3c", dropped),
                       ("other-fix", cls == "other-fix"), ("regression", cls == "regression"),
                       ("extrinsic", cls == "extrinsic"), ("latent", cls == "latent")):
        if mask.sum() >= 20:
            out["above"][name] = {"n": int(mask.sum()), "share": float((s[mask] > thr).mean())}
            print(f"    {name:15} {int(mask.sum()):6,}  {out['above'][name]['share']:6.1%}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0


def cmd_score(a) -> int:
    """No label is read here: a score per commit, for a repo the model has not seen."""
    model = json.loads(Path(a.model).read_text())
    shas, cols, _ct = design(et.load(a.inp))
    out = {v: predict(model, v, cols) for v in VARIANTS}
    Path(a.out).write_text(json.dumps(
        {"repo": a.pool_repo, "trained_on": model["trained_on"], "threshold_both": model["threshold_both"],
         "scores": {s: {v: round(float(out[v][i]), 6) for v in VARIANTS} for i, s in enumerate(shas)}},
        sort_keys=True) + "\n")
    print(f"{a.pool_repo}: {len(shas):,} commits scored -> {a.out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("fit", "eval", "score"))
    ap.add_argument("--repo", choices=("curl", "libarchive"))          # labelled steps: burned repos only
    ap.add_argument("--pool-repo")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--json")
    ap.add_argument("--out")
    ap.add_argument("--target", default="fix", choices=("fix", "extrinsic", "regression"))
    a = ap.parse_args()
    if a.step in ("fit", "eval") and not a.repo:
        ap.error("--repo is required for fit and eval")
    return {"fit": cmd_fit, "eval": cmd_eval, "score": cmd_score}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
