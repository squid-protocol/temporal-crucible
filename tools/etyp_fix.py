#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ETYP-FIX (EXPLORATORY): every fix as a vector of edit types, joined to class, impact and reports.

    python tools/etyp_fix.py --repo curl --in /scratch/etyp_curl.jsonl --json docs/etyp_fix_curl.json

**Exploratory. No registration, no hypothesis fixed in advance, no p-value claimed. ~30 labels by ~10
groups are compared with no multiplicity correction: read the tables as a map, not as verdicts.**

`tools/edit_types.py` gives each (commit, function) edit a set of atomic labels without reading any
outcome. This tool is the first place an outcome is joined to them, and it is kept separate so the
classifier stays outcome-blind. Running it on a repo BURNS that repo for any later confirmatory ETYP
claim (CONTRIBUTING, hypothesis-first rule 4): curl and libarchive only. openssl and nDPI are held out.

Each commit becomes a vector: for every atomic label and every primary family, the FRACTION of the
commit's function edits that carry it. Three questions:

  A. SIGNATURE. Which edit types are over-represented in fixes, by fix class (`events/<repo>_xc.json`:
     other-fix kept by FIXLIKE v3c, regression, extrinsic, latent), by CVE severity
     (`events/<repo>.json`) and by whether the fix answers an outside report (a `Reported-by:`, `Bug:`
     or `Fixes #n` line in the message)?
  B. CAUSE. Which edit types are over-represented in commits later named as INTRODUCING a defect
     (`introduced` CVE events; regression `inducing` links in `events/<repo>_reg_links.json`)?
  C. FOLLOW-UP. After a NON-fix edit of a given type, how often is the same function edited by a fix
     within 365 days, against other non-fix edits to functions of the same size and edit history?

Guards. A and B: fix commits are small, and a one-function commit cannot have the label mix of a
twenty-function one, so every lift is standardised on commit size TWO ways at once -- function edits
per commit (1, 2-3, 4-9, 10+) and tokens changed (<=8, <=32, <=128, more): the reference group is
re-weighted to the group's own distribution over those 16 cells. C: standardised on function size
(log2 tokens), prior edit count (0, 1-2, 3-7, 8+) -- the history baseline every result in this
programme has to beat -- and the tokens the edit itself changed. Without the changed-token control a
"type" effect is partly just "a bigger edit"; the first run (function-edit count only) is recorded
in docs/etyp_fix.md for that reason. Intervals are 95% percentile bootstraps,
resampling commits (A, B) or functions (C), 300 draws, seed 2982. Sweep commits (> 50 function edits)
are dropped everywhere.

Needs numpy.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edit_types as et          # noqa: E402
import fixlike_v2                # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED, DRAWS, YEAR = 2982, 300, 365 * 86400
FIX_CLASSES = ("other-fix", "regression", "extrinsic", "latent")
REPORTED = re.compile(r"^(reported-by:|bug:|fixes:? +#\d+|fixes:? +https?://)", re.I | re.M)
COLS = list(et.LABELS) + ["P:" + f for f in et.PRIORITY]


def size_bin(n: int) -> int:
    return 0 if n == 1 else 1 if n <= 3 else 2 if n <= 9 else 3


def mag_bin(n: int) -> int:
    """Tokens added plus removed (multiset difference): the size of the change itself."""
    return 0 if n <= 8 else 1 if n <= 32 else 2 if n <= 128 else 3


def hist_bin(n: int) -> int:
    return 0 if n == 0 else 1 if n <= 2 else 2 if n <= 7 else 3


def load_events(repo: str) -> dict:
    ev = ROOT / "events"
    xc = json.loads((ev / f"{repo}_xc.json").read_text())
    head_ct = max(e["ct"] for e in xc["events"])
    cls, dropped = {}, set()
    for e in xc["events"]:
        if fixlike_v2.drop_reason(e, rules="v3c"):
            dropped.add(e["sha"])
        else:
            cls[e["sha"]] = e["class"]
    out = {"since": xc["since"], "head_ct": head_ct, "class": cls, "dropped": dropped,
           "sev": {}, "control": set(), "cve_intro": set(), "reg_inducing": set()}
    p = ev / f"{repo}.json"
    if p.exists():
        for e in json.loads(p.read_text())["events"]:
            if e["class"] == "security-fix":
                s = (e.get("severity") or "").capitalize()
                out["sev"][e["sha"]] = "High+" if s in ("High", "Critical") else s or "?"
            elif e["class"] == "control":
                out["control"].add(e["sha"])
            elif e["class"] == "introduced":
                out["cve_intro"].add(e["sha"])
    p = ev / f"{repo}_reg_links.json"
    if p.exists():
        out["reg_inducing"] = {l["inducing"] for l in json.loads(p.read_text())["links"]}
    return out


def reported_shas(repo: str) -> set:
    out = subprocess.run(["git", "-C", str(et.POOL / repo), "log", "--no-merges",
                          "--format=%x01%H%x02%B"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    res = set()
    for chunk in out.split("\x01")[1:]:
        sha, _sep, body = chunk.partition("\x02")
        if REPORTED.search(body):
            res.add(sha)
    return res


def commit_matrix(rows: list[dict]):
    """(shas, X[commit, COLS] fractions, n_edits[commit], ct[commit], changed tokens[commit])."""
    by: dict = defaultdict(list)
    for r in rows:
        by[r["sha"]].append(r)
    shas = [s for s, rs in by.items() if len(rs) <= 50]
    idx = {c: i for i, c in enumerate(COLS)}
    X = np.zeros((len(shas), len(COLS)))
    n = np.zeros(len(shas), dtype=int)
    ct = np.zeros(len(shas), dtype=np.int64)
    mag = np.zeros(len(shas), dtype=int)
    for i, s in enumerate(shas):
        rs = by[s]
        n[i], ct[i] = len(rs), rs[0]["ct"]
        mag[i] = sum(r["tadd"] + r["tdel"] for r in rs)
        for r in rs:
            for lab in r["labels"]:
                X[i, idx[lab]] += 1
            X[i, idx["P:" + r["primary"]]] += 1
        X[i] /= len(rs)
    return shas, X, n, ct, mag


def std_lift(X, bins, g: np.ndarray, ref: np.ndarray, rng) -> dict:
    """Mean fraction in group g over the reference re-weighted to g's commit-size mix, with a CI."""
    def one(gi, ri):
        w = np.bincount(bins[gi], minlength=16) / len(gi)
        exp = np.zeros(X.shape[1])
        for s in range(16):
            sel = ri[bins[ri] == s]
            if w[s] and len(sel):
                exp += w[s] * X[sel].mean(axis=0)
        obs = X[gi].mean(axis=0)
        return obs, exp
    gi, ri = np.flatnonzero(g), np.flatnonzero(ref)
    obs, exp = one(gi, ri)
    boots = []
    for _ in range(DRAWS):
        o, e = one(rng.choice(gi, len(gi)), rng.choice(ri, len(ri)))
        boots.append(np.divide(o, e, out=np.full_like(o, np.nan), where=e > 0))
    lo, hi = np.nanpercentile(np.array(boots), [2.5, 97.5], axis=0)
    return {c: {"share": float(obs[j]), "expected": float(exp[j]),
                "lift": float(obs[j] / exp[j]) if exp[j] > 0 else None,
                "lo": float(lo[j]), "hi": float(hi[j])} for j, c in enumerate(COLS)}


def follow_up(rows: list[dict], evs: dict, fix_shas: set, rng) -> dict:
    """C: P(function fixed within a year | a non-fix edit of type X), standardised on size and history."""
    by_fn: dict = defaultdict(list)
    for r in rows:
        by_fn[(r["path"], r["func"])].append(r)
    S = 20 * 4 * 4
    fn_n = np.zeros((len(by_fn), len(COLS) + 1, S))       # last column: every eligible edit (the base)
    fn_y = np.zeros_like(fn_n)
    idx = {c: i for i, c in enumerate(COLS)}
    for f, edits in enumerate(by_fn.values()):
        fix_ct = [e["ct"] for e in edits if e["sha"] in fix_shas]
        for k, e in enumerate(edits):
            if e["sha"] in fix_shas or e["sha"] in evs["dropped"]:
                continue
            if e["ct"] < evs["since"] or e["ct"] + YEAR > evs["head_ct"]:
                continue
            y = any(e["ct"] < t <= e["ct"] + YEAR for t in fix_ct)
            s = (min(int(math.log2(max(e["ntok"], 1))), 19) * 4 + hist_bin(k)) * 4 + mag_bin(e["tadd"] + e["tdel"])
            for c in [idx[l] for l in e["labels"]] + [idx["P:" + e["primary"]], len(COLS)]:
                fn_n[f, c, s] += 1
                fn_y[f, c, s] += y

    def rel(w):
        n, y = np.tensordot(w, fn_n, 1), np.tensordot(w, fn_y, 1)
        base = np.divide(y[-1], n[-1], out=np.zeros(S), where=n[-1] > 0)
        obs = y[:-1].sum(axis=1) / np.maximum(n[:-1].sum(axis=1), 1)
        exp = (n[:-1] * base).sum(axis=1) / np.maximum(n[:-1].sum(axis=1), 1)
        return obs, exp, n[:-1].sum(axis=1), y[-1].sum() / max(n[-1].sum(), 1), n[-1].sum()

    obs, exp, cnt, base_rate, total = rel(np.ones(len(by_fn)))
    boots = []
    for _ in range(DRAWS):
        o, e, _c, _b, _t = rel(rng.multinomial(len(by_fn), np.full(len(by_fn), 1 / len(by_fn))).astype(float))
        boots.append(np.divide(o, e, out=np.full_like(o, np.nan), where=e > 0))
    lo, hi = np.nanpercentile(np.array(boots), [2.5, 97.5], axis=0)
    return {"eligible_edits": int(total), "base_rate": float(base_rate),
            "by": {c: {"n": int(cnt[j]), "rate": float(obs[j]), "expected": float(exp[j]),
                       "rel": float(obs[j] / exp[j]) if exp[j] > 0 else None,
                       "lo": float(lo[j]), "hi": float(hi[j])} for j, c in enumerate(COLS)}}


def table(title: str, res: dict, groups: list[str], cols: list[str], key: str = "lift") -> None:
    print(f"\n  {title}")
    print("    " + f"{'':16}" + "".join(f"{g[:17]:>19}" for g in groups))
    for c in cols:
        cells = []
        for g in groups:
            v = res[g]["by"][c]
            if v[key] is None:
                cells.append(f"{'-':>19}")
            else:
                star = "*" if (v["lo"] > 1 or v["hi"] < 1) else " "
                cells.append(f"{v[key]:6.2f}{star}[{v['lo']:4.2f},{v['hi']:5.2f}]")
        print("    " + f"{c.replace('P:', ''):16}" + "".join(f"{x:>19}" for x in cells))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default="curl", choices=("curl", "libarchive"))   # the burned repos only
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    evs = load_events(a.repo)
    rows = [r for r in et.load(a.inp)]
    shas, X, n, ct, mag = commit_matrix(rows)
    bins = np.array([size_bin(k) * 4 + mag_bin(m) for k, m in zip(n, mag)])
    window = (ct >= evs["since"]) & (ct <= evs["head_ct"])
    is_cls = {c: np.array([evs["class"].get(s) == c for s in shas]) & window for c in FIX_CLASSES}
    anyfix = np.any(list(is_cls.values()), axis=0)
    amb = np.array([s in evs["dropped"] for s in shas])
    nonfix = window & ~anyfix & ~amb
    rep = reported_shas(a.repo)
    is_rep = np.array([s in rep for s in shas])

    groups = {"all fixes": anyfix, **is_cls,
              "fix, reported": anyfix & is_rep, "fix, unreported": anyfix & ~is_rep}
    for sev in ("Low", "Medium", "High+"):
        groups[f"CVE {sev}"] = np.array([evs["sev"].get(s) == sev for s in shas])
    groups["CVE (all)"] = np.array([s in evs["sev"] for s in shas])
    groups["CVE control"] = np.array([s in evs["control"] for s in shas])
    groups["CVE-introducing"] = np.array([s in evs["cve_intro"] for s in shas])
    groups["regr-inducing"] = np.array([s in evs["reg_inducing"] for s in shas]) & ~anyfix
    res = {}
    for g, mask in groups.items():
        if mask.sum() >= 20:
            # A CVE or inducing commit may itself sit outside the labelled window: compare to all non-fix.
            res[g] = {"commits": int(mask.sum()), "by": std_lift(X, bins, mask, nonfix & ~mask, rng)}
    fix_shas = {s for s, c in evs["class"].items()}
    fu = follow_up(rows, evs, fix_shas, rng)

    print(f"{a.repo}: {len(shas):,} commits with function edits; {int(window.sum()):,} in the labelled window "
          f"-> {int(anyfix.sum()):,} fix, {int(nonfix.sum()):,} non-fix, {int((amb & window).sum()):,} "
          f"dropped by v3c (EXPLORATORY; * = 95% interval excludes 1; no multiplicity correction)")
    print("  group sizes: " + ", ".join(f"{g} {v['commits']:,}" for g, v in res.items()))
    fam = ["P:" + f for f in et.PRIORITY if f != "RESIDUAL"]
    atoms = [l for l in et.LABELS if l not in ("EXPR_EDIT", "UNCLASSIFIED")]
    A = [g for g in ("all fixes", "other-fix", "regression", "extrinsic", "latent") if g in res]
    table("A. Primary family of a fix's edits, lift over non-fix commits of the same size and magnitude", res, A, fam)
    table("A. Atomic labels, same lift", res, A, atoms)
    B = [g for g in ("fix, reported", "fix, unreported", "CVE (all)", "CVE Low", "CVE Medium", "CVE High+",
                     "CVE control") if g in res]
    table("A. Impact and reports: primary family", res, B, fam)
    table("A. Impact and reports: atomic labels", res, B, atoms)
    C = [g for g in ("CVE-introducing", "regr-inducing") if g in res]
    if C:
        table("B. Commits later named as introducing a defect: primary family", res, C, fam)
        table("B. Same: atomic labels", res, C, atoms)
    print(f"\n  C. After a NON-fix edit, is the function fixed within 365 days?  "
          f"{fu['eligible_edits']:,} eligible edits, base rate {fu['base_rate']:.1%}")
    print(f"    {'type of the edit':16} {'n':>7} {'rate':>7} {'expected':>9} {'relative':>9}   95% interval")
    for c in fam + atoms:
        v = fu["by"][c]
        if v["n"] < 100 or v["rel"] is None:
            continue
        star = "*" if (v["lo"] > 1 or v["hi"] < 1) else " "
        print(f"    {c.replace('P:', ''):16} {v['n']:7,} {v['rate']:7.1%} {v['expected']:9.1%} "
              f"{v['rel']:8.2f}{star}   [{v['lo']:.2f}, {v['hi']:.2f}]")
    if a.json:
        Path(a.json).write_text(json.dumps({"repo": a.repo, "type": "exploratory", "groups": res,
                                            "follow_up": fu}, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
