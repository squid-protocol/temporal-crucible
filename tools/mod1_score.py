#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""MOD-1 scorer: is the in-degree lift over LOC lower in older repositories?

    python tools/mod1_score.py [--out docs/mod1_result.json]

Runs the test of docs/moderator_registration.md as amended (Amendments 1-3, all written before any drawn
repo was scored): OLS of the lift on `old` + `C_family`, percentile bootstrap over repos.

MOD-H1 is DIRECTIONAL. It is supported only if the `old` coefficient's 95% CI lies wholly BELOW zero. A CI
wholly above zero contradicts it. A CI that includes zero is "not detected" -- this design cannot show that
age does not matter (power is about 70% for a difference of 0.05, a third for 0.03).

Every repo that is left out is listed with its own reason, read from structure before any outcome.
"""
from __future__ import annotations

import argparse, json, random, statistics as st, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mod1_lift import measure  # noqa: E402

DRAW = Path("docs/draw40.json")
LIFTS = Path("docs/mod1")
PRIOR = ("commons-lang", "curl", "libxml2", "ndpi", "postgres", "prometheus", "redis", "sphinx")
S1_UNMEASURED = {"racket", "ghostty", "swift", "wrf-fortran", "fieldtrip", "rails", "bugzilla", "discourse",
                 "tigerbeetle", "bun"}  # Amendment 1: main language first measured on 2026-11-13
OLD_BEFORE = 2006
MIN_COVERAGE, MIN_WINDOW = 0.30, 730


def ols(rows, cols):
    """least squares with an intercept, solved by Gaussian elimination -- no numpy dependency"""
    k = len(cols) + 1
    X = [[1.0] + [float(r[c]) for c in cols] for r in rows]
    y = [r["lift"] for r in rows]
    A = [[sum(X[i][a] * X[i][b] for i in range(len(X))) for b in range(k)] +
         [sum(X[i][a] * y[i] for i in range(len(X)))] for a in range(k)]
    for i in range(k):
        p = max(range(i, k), key=lambda r: abs(A[r][i]))
        if abs(A[p][i]) < 1e-12:
            return None
        A[i], A[p] = A[p], A[i]
        for r in range(k):
            if r != i:
                f = A[r][i] / A[i][i]
                for c in range(i, k + 1):
                    A[r][c] -= f * A[i][c]
    return [A[i][k] / A[i][i] for i in range(k)]


def boot(rows, cols, reps=4000, seed=917):
    rnd = random.Random(seed)
    out = {c: [] for c in cols}
    for _ in range(reps):
        s = [rows[rnd.randrange(len(rows))] for _ in rows]
        b = ols(s, cols)
        if b:
            for j, c in enumerate(cols):
                out[c].append(b[j + 1])
    return {c: (sorted(v)[int(.025 * len(v))], sorted(v)[int(.975 * len(v))]) if v else (float("nan"),) * 2
            for c, v in out.items()}


def reading(lo, hi):
    return "supported" if hi < 0 else "contradicted" if lo > 0 else "not detected"


def test(rows, title, cols=("old", "C_family"), key="old"):
    """the registered OLS + bootstrap on `rows`; a stub when there are too few repos to fit"""
    if len(rows) < 8:
        print(f"\n  {title}: only {len(rows)} repos -- not fitted")
        return {"n": len(rows), "reading": "not fitted"}
    cols = list(cols)
    b, ci = ols(rows, cols), boot(rows, cols)
    if not b:
        print(f"\n  {title}: singular -- not fitted")
        return {"n": len(rows), "reading": "not fitted"}
    print(f"\n  {title}   n={len(rows)}")
    for j, c in enumerate(cols):
        print(f"    {c:<14} coef {b[j+1]:+.4f}   CI [{ci[c][0]:+.4f}, {ci[c][1]:+.4f}]")
    r = reading(*ci[key])
    print(f"    MOD-H1 ({key} lowers the lift): {r}")
    return {"n": len(rows), "coef": dict(zip(["intercept"] + cols, b)),
            "ci95": {c: list(v) for c, v in ci.items()}, "reading": r}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("docs/mod1_result.json"))
    ap.add_argument("--lifts", type=Path, default=LIFTS,
                    help="per-repo measurements to read (default: the registered ones). The exploratory "
                         "tree-wide-commit re-measure lives in docs/mod1_wide/drop")
    a = ap.parse_args()
    drawn = [d["repo"] for d in json.loads(DRAW.read_text())["draw"]]
    a.lifts.mkdir(exist_ok=True)
    rows, excluded = [], []
    for repo in sorted(set(drawn) | set(PRIOR)):
        f = a.lifts / f"lift_{repo}.json"
        try:
            m = json.loads(f.read_text()) if f.exists() else measure(repo)
        except Exception as e:  # a failure is its own reason, never folded into the floor
            m = {"repo": repo, "status": "failed", "why": f"{type(e).__name__}: {e}"}
        if m["status"] not in ("unprepared", "failed"):
            f.write_text(json.dumps(m, indent=1) + "\n")
        if m["status"] != "ok":
            excluded.append({"repo": repo, "status": m["status"], "why": m.get("why")})
            continue
        rows.append({"repo": repo, "lift": m["lift"], "ci95": m["ci95"], "positives": m["positives"],
                     "old": int(m["start_year"] < OLD_BEFORE), "C_family": int(m["family"] == "C"),
                     "start_year": m["start_year"], "age_at_cut": m["age_at_cut"], "language": m["language"],
                     "drawn": repo in drawn, "merge_units": m["merge_units"],
                     "call_coverage": m["call_coverage"], "window_days": m["window_days"]})
    print(f"analysis set: {len(rows)} repos   excluded: {len(excluded)}")
    for e in excluded:
        print(f"    out  {e['repo']:<18}{e['status']:<16}{e['why']}")
    print(f"\n  {'cell':<18}{'n':>4}{'mean lift':>12}{'lift > 0':>10}{'CI excl. 0':>12}")
    for old in (1, 0):
        for fam in (1, 0):
            g = [r for r in rows if r["old"] == old and r["C_family"] == fam]
            if g:
                solid = sum(1 for r in g if r["ci95"][0] is not None and (r["ci95"][0] > 0 or r["ci95"][1] < 0))
                print(f"  {('old' if old else 'young')+'/'+('C' if fam else 'managed'):<18}{len(g):>4}"
                      f"{st.mean(r['lift'] for r in g):>+12.4f}{sum(1 for r in g if r['lift'] > 0):>7}/{len(g)}"
                      f"{solid:>9}/{len(g)}")
    res = {"n": len(rows), "excluded": excluded, "rows": rows}
    res["primary"] = test(rows, "PRIMARY (all repos that pass the checks)")
    sens = {
        "S1_new_languages_removed": [r for r in rows if r["repo"] not in S1_UNMEASURED],
        "S2_drawn_only": [r for r in rows if r["drawn"]],
        "S3_call_coverage": [r for r in rows if r["call_coverage"] >= MIN_COVERAGE],
        "S4_full_window": [r for r in rows if r["window_days"] >= MIN_WINDOW],
        "S5_merge_workflow_removed": [r for r in rows if not r["merge_units"]],
    }
    res["sensitivity"] = {k: test(v, k) for k, v in sens.items()}
    gate = [res["primary"]["reading"], res["sensitivity"]["S1_new_languages_removed"]["reading"],
            res["sensitivity"]["S2_drawn_only"]["reading"]]
    res["verdict"] = ("MOD-H1 supported" if all(g == "supported" for g in gate) else
                      "MOD-H1 contradicted" if all(g == "contradicted" for g in gate) else
                      "MOD-H1 not detected" if gate[0] == "not detected" else
                      f"MOD-H1 {gate[0]} in the primary but NOT ROBUST (S1 {gate[1]}, drawn-only {gate[2]})")
    res["secondary"] = {
        "continuous_age": test(rows, "SECONDARY continuous age at the cut (years)", ("age_at_cut", "C_family"),
                               "age_at_cut"),
        "interaction": test([{**r, "old_x_C": r["old"] * r["C_family"]} for r in rows],
                            "SECONDARY with the age x family interaction", ("old", "C_family", "old_x_C")),
    }
    print(f"\n  VERDICT: {res['verdict']}")
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
