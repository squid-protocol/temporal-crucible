#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""MOD-1 scorer: is the sign of the structural effect moderated by repo AGE or LANGUAGE?

    python tools/mod1_score.py [--out docs/mod1_result.json]

Runs exactly the test registered in docs/moderator_registration.md, written before any drawn repo was
scanned: OLS of the in-degree lift over LOC on `old` + `C_family`, bootstrap CI over repos, MOD-H1
(age) primary and supported iff the `old` coefficient's 95% CI excludes zero.

Repos under the positives floor are EXCLUDED AND LISTED, never rescued with a different label.
"""
from __future__ import annotations

import argparse, json, random, statistics as st, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PREP = Path("docs/mod1_prep.json")
DRAW = Path("docs/draw40.json")
PRIOR = {  # the eight already assessed, cascade label, from docs/struct_null_*.json
    "commons-lang": None, "curl": None, "libxml2": None, "ndpi": None,
    "postgres": None, "prometheus": None, "redis": None, "sphinx": None}


AMEND = Path("docs/mod1_language_amend.json")
STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")


def call_coverage(repo: str, lang: str) -> tuple[int, int]:
    """(files of `lang` at the snapshot, call edges landing in them) -- Amendment 2's instrument check"""
    import sqlite3
    import laws_units as U
    db = STUDY / "dbs" / f"{repo}.db"
    if not db.exists():
        return 0, 0
    w = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    ex = U.Excluder()
    mine = {fid for fid, path in w.execute("select id, path from file where generated=0")
            if U.language_of(path) in ({"c", "cpp"} if lang in ("c", "cpp") else {lang}) and ex.why(path) is None}
    f2 = dict(w.execute("select id, file_id from func"))
    edges = sum(1 for (dst,) in w.execute("select dst from edge") if f2.get(dst) in mine)
    w.close()
    return len(mine), edges


def lift_for(repo: str) -> float | None:
    f = Path(f"docs/struct_null_{repo}.json")
    if not f.exists():
        p = subprocess.run([sys.executable, "tools/struct_null.py", "--repo", repo, "--out", str(f)],
                           capture_output=True, text=True, timeout=2400)
        if not f.exists():
            return None
    try:
        d = json.loads(f.read_text())
        return d["results"]["cascade"]["metrics"]["in_degree"]["lift"]
    except Exception:
        return None


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
    return {c: (sorted(v)[int(.025 * len(v))], sorted(v)[int(.975 * len(v))]) if v else (float('nan'),) * 2
            for c, v in out.items()}


S1_UNMEASURED = {"racket", "ghostty", "swift", "wrf-fortran", "fieldtrip", "rails", "bugzilla", "discourse",
                 "tigerbeetle", "bun"}  # docs/moderator_registration.md, Amendment 1


def test(rows, title):
    """the registered OLS + bootstrap on `rows`; {} when there are too few repos to fit"""
    if len(rows) < 8:
        return {}
    b = ols(rows, ["old", "C_family"])
    ci = boot(rows, ["old", "C_family"])
    print(f"\n  {title}")
    for j, c in enumerate(["old", "C_family"]):
        lo, hi = ci[c]
        sig = "SUPPORTED" if (lo > 0 or hi < 0) else "not supported"
        print(f"    {c:<10} coef {b[j+1]:+.4f}   CI [{lo:+.4f}, {hi:+.4f}]   {sig}")
    primary = "MOD-H1 supported" if (ci["old"][0] > 0 or ci["old"][1] < 0) else \
              "MOD-H1 not supported -- age is not the moderator"
    print(f"  -> {primary}")
    return {"coef": {"intercept": b[0], "old": b[1], "C_family": b[2]},
            "ci95": {c: list(v) for c, v in ci.items()}, "primary": primary}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("docs/mod1_result.json"))
    a = ap.parse_args()
    amend = json.loads(AMEND.read_text())["repos"] if AMEND.exists() else {}
    meta = {d["repo"]: {**d, **amend.get(d["repo"], {})} for d in json.loads(DRAW.read_text())["draw"]}
    for r in PRIOR:  # the prior eight, re-dated from their own history DBs by struct_null's frame
        meta.setdefault(r, {"repo": r})
    rows, excluded = [], []
    for repo, m in sorted(meta.items()):
        if "lang" in m:  # Amendment 2 instrument check, drawn repos only, decided before the lift is read
            fl, ed = call_coverage(repo, m["lang"])
            if fl and ed * 10 < fl:
                excluded.append({"repo": repo, "why": f"engine does not resolve {m['lang']} calls: "
                                                      f"{ed} inbound edges over {fl} {m['lang']} files"})
                continue
        lf = lift_for(repo)
        if lf is None:
            excluded.append({"repo": repo, "why": "under the positives floor or unscanned"})
            continue
        if "age" not in m:   # the prior eight: ages recorded in docs/WHERE_WE_STAND
            known = {"commons-lang": (2002, "managed"), "curl": (1999, "C"), "libxml2": (1998, "C"),
                     "ndpi": (2015, "C"), "postgres": (1996, "C"), "prometheus": (2012, "managed"),
                     "redis": (2009, "C"), "sphinx": (2007, "managed")}
            y, fam = known[repo]
            m = {"repo": repo, "year": y, "family": fam, "age": "old" if y < 2006 else "young"}
        rows.append({"repo": repo, "lift": lf, "old": 1 if m["age"] == "old" else 0,
                     "C_family": 1 if m["family"] == "C" else 0, "year": m["year"]})
    print(f"analysis set: {len(rows)} repos   excluded: {len(excluded)}\n")
    print(f"  {'cell':<18}{'n':>4}{'mean lift':>12}{'positive':>10}")
    for age in ("old", "young"):
        for fam in ("C", "managed"):
            g = [r for r in rows if r["old"] == (age == "old") and r["C_family"] == (fam == "C")]
            if g:
                print(f"  {age+'/'+fam:<18}{len(g):>4}{st.mean(r['lift'] for r in g):>+12.4f}"
                      f"{sum(1 for r in g if r['lift'] > 0):>7}/{len(g)}")
    res = {"n": len(rows), "excluded": excluded, "rows": rows}
    res.update(test(rows, "REGISTERED TEST (OLS, bootstrap CI over repos)"))
    # Amendment 1 (declared before any drawn repo was scored): the same test without the repos whose main
    # language the instrument does not measure. Reported beside the primary, never instead of it.
    s1 = [r for r in rows if r["repo"] not in S1_UNMEASURED]
    res["s1"] = {"n": len(s1), "dropped": sorted(r["repo"] for r in rows if r["repo"] in S1_UNMEASURED),
                 **test(s1, f"SENSITIVITY S1 (unmeasured-language repos removed, n={len(s1)})")}
    if "primary" in res and "primary" in res["s1"]:
        agree = res["primary"].startswith("MOD-H1 supported") == res["s1"]["primary"].startswith("MOD-H1 supported")
        res["robust_to_language_call"] = agree
        print(f"\n  primary and S1 {'agree' if agree else 'DISAGREE -- MOD-H1 is not robust to the language call'}")
    a.out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
