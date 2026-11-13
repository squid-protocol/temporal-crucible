#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ETYP-FIX (EXPLORATORY): every fix as a vector of edit types, joined to class, impact and follow-up.

    python tools/etyp_fix.py --repo curl --in /scratch/etyp_curl.jsonl --json docs/etyp_fix_curl.json

**Exploratory. No registration, no hypothesis fixed in advance, no p-value claimed. About 34 columns by
10 contrasts by 2 repos are compared with no multiplicity correction: read the tables as a map. A cell
marked in one repo only is not a finding.**

`tools/edit_types.py` gives each (commit, function) edit a set of atomic labels without reading any
outcome. This tool is the first place an outcome is joined to them, and it is kept separate so the
classifier stays outcome-blind. Running it on a repo BURNS that repo for any later confirmatory ETYP
claim (CONTRIBUTING, hypothesis-first): curl and libarchive only. openssl and nDPI are held out.

Each commit becomes a vector: for every atomic label and every primary family, the FRACTION of the
commit's function edits that carry it. Three questions:

  A. SIGNATURE. Which edit types are over-represented in fixes, by fix class (`events/<repo>_xc.json`:
     other-fix kept by FIXLIKE v3c, regression, extrinsic, latent)? Two direct contrasts sit beside the
     class table because eyeballing two intervals is not a test: fixes that answer an outside report
     against fixes that do not, and CVE fixes against their matched controls.
  B. CAUSE. Which edit types are over-represented in commits later named as INTRODUCING a defect
     (`introduced` CVE events; regression `inducing` links)?
  C. FOLLOW-UP. After a NON-fix edit of a given type, how often is the same function edited by a fix
     within 365 days, against OTHER non-fix edits in the same stratum?

This version follows an independent review (`docs/etyp_review.md`). What changed, and why:

  - The non-fix REFERENCE gets the same subject filter the fixes got. FIXLIKE v3c removes fix commits
    whose subject says typo / whitespace / reformat / refactor / cleanup / comment; the first run left
    such commits in the reference, which made fixes look "pure" by construction.
  - Members of the defect-introducing groups must themselves be non-fix, non-dropped commits. In the
    first run 40% of them were fixes or v3c-dropped, so section B partly measured "is a fix".
  - `latent` and "CVE" are the same commits in curl; the set is reported once.
  - Extrinsic fixes are also compared with non-fix commits whose subject names a platform or compiler,
    because that is how the extrinsic label is assigned and such commits edit `#if` blocks regardless.
  - C drops sweep commits (the first run did not, against its own docstring), compares each type with
    the OTHER edits in its stratum (the first run's base included the type itself, pulling every ratio
    toward 1), and controls recent activity and era, not lifetime edit count. A negative-control
    outcome is reported beside it: does ANY non-fix edit follow within a year?
  - A cell is marked only when its interval excludes 1 AND at least MIN_K commits in the group and in
    the reference carry the label. A group with zero occurrences used to get a mark for [0.00, 0.00].

Guards. A and B: every lift is standardised on commit size two ways at once -- function edits per
commit (1, 2-3, 4-9, 10+) and tokens changed (<=8, <=32, <=128, more): the reference is re-weighted to
the group's own distribution over those 16 cells, renormalised over cells the reference occupies.
C: strata are function size (log2 tokens) x tokens the edit changed x edits to the function in the
prior 365 days x whether a fix touched it in the prior 365 days x four-year era. Intervals are 95%
percentile bootstraps, resampling commits (A, B) or functions (C), 300 draws, seed 2982. Sweep commits
(> 50 function edits) are dropped everywhere.

Needs numpy.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edit_types as et          # noqa: E402
import fixlike_v2                # noqa: E402
import xc_harvest                # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED, DRAWS, YEAR = 2982, 300, 365 * 86400
MIN_K = 5                                        # fewer commits than this carrying a label: no mark
FIX_CLASSES = ("other-fix", "regression", "extrinsic", "latent")
REPORTED = re.compile(r"^(reported-by:|bug:|fixes:? +#\d+|fixes:? +https?://)", re.I | re.M)
COLS = list(et.LABELS) + ["P:" + f for f in et.PRIORITY]


def size_bin(n: int) -> int:
    return 0 if n == 1 else 1 if n <= 3 else 2 if n <= 9 else 3


def mag_bin(n: int) -> int:
    """Tokens added plus removed (multiset difference): the size of the change itself."""
    return 0 if n <= 8 else 1 if n <= 32 else 2 if n <= 128 else 3


def count_bin(n: int) -> int:
    return 0 if n == 0 else 1 if n <= 2 else 2 if n <= 7 else 3


def cosmetic_subject(subj: str) -> bool:
    """FIXLIKE v3c rules B, B2 and B3 on a subject: the commits it removes from `other-fix`."""
    if fixlike_v2.NONFIX_SUBJ.search(subj) or fixlike_v2.NONFIX_SUBJ2.search(subj):
        return True
    return bool(fixlike_v2.COMMENT_EDIT.search(subj) and not fixlike_v2.COMMENT_OP.search(subj))


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
           "cve_fix": set(), "control": set(), "cve_intro": set(), "reg_inducing": set()}
    p = ev / f"{repo}.json"
    if p.exists():
        for e in json.loads(p.read_text())["events"]:
            key = {"security-fix": "cve_fix", "control": "control", "introduced": "cve_intro"}.get(e["class"])
            if key:
                out[key].add(e["sha"])
    p = ev / f"{repo}_reg_links.json"
    if p.exists():
        out["reg_inducing"] = {l["inducing"] for l in json.loads(p.read_text())["links"]}
    return out


def messages(repo: str) -> dict:
    """{sha: (subject, has a report line)} for every non-merge commit."""
    out = subprocess.run(["git", "-C", str(et.POOL / repo), "log", "--no-merges",
                          "--format=%x01%H%x02%B"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    res = {}
    for chunk in out.split("\x01")[1:]:
        sha, _sep, body = chunk.partition("\x02")
        res[sha] = (body.split("\n", 1)[0], bool(REPORTED.search(body)))
    return res


def commit_matrix(rows: list[dict], cols=None, feats=None):
    """(shas, X[commit, cols] fractions, n_edits[commit], ct[commit], changed tokens[commit]); sweeps dropped."""
    cols = COLS if cols is None else cols
    feats = row_cols if feats is None else feats
    by: dict = defaultdict(list)
    for r in rows:
        by[r["sha"]].append(r)
    shas = [s for s, rs in by.items() if len(rs) <= et.SWEEP]
    idx = {c: i for i, c in enumerate(cols)}
    X = np.zeros((len(shas), len(cols)))
    n = np.zeros(len(shas), dtype=int)
    ct = np.zeros(len(shas), dtype=np.int64)
    mag = np.zeros(len(shas), dtype=int)
    for i, s in enumerate(shas):
        rs = by[s]
        n[i], ct[i] = len(rs), rs[0]["ct"]
        mag[i] = sum(r["tadd"] + r["tdel"] for r in rs)
        for r in rs:
            for c in feats(r):
                X[i, idx[c]] += 1
        X[i] /= len(rs)
    return shas, X, n, ct, mag


def row_cols(r: dict) -> list[str]:
    return list(r["labels"]) + ["P:" + r["primary"]]


def masks(repo: str, shas: list[str], ct: np.ndarray, evs: dict | None = None) -> dict:
    """Every commit group this study uses, as boolean arrays over `shas`."""
    evs = load_events(repo) if evs is None else evs
    msg = messages(repo)
    arr = lambda f: np.array([bool(f(s)) for s in shas])
    window = (ct >= evs["since"]) & (ct <= evs["head_ct"])
    cls = np.array([evs["class"].get(s, "") for s in shas])
    fix = (cls != "") & window
    dropped = arr(lambda s: s in evs["dropped"])
    cosmetic = arr(lambda s: cosmetic_subject(msg.get(s, ("", False))[0]))
    clean = window & ~fix & ~dropped                  # labelled "not a fix" by the message
    m = {"window": window, "cls": cls, "fix": fix, "dropped": dropped,
         "nonfix_raw": clean, "nonfix": clean & ~cosmetic,
         "reported": arr(lambda s: msg.get(s, ("", False))[1]),
         "platform": arr(lambda s: xc_harvest.EXT_ENV.search(msg.get(s, ("", False))[0])),
         "cve_fix": arr(lambda s: s in evs["cve_fix"]), "control": arr(lambda s: s in evs["control"]),
         "cve_intro": arr(lambda s: s in evs["cve_intro"]),
         "reg_inducing": arr(lambda s: s in evs["reg_inducing"])}
    return m


def contrasts(m: dict) -> list[tuple]:
    """(name, group, reference, section). The reference is never allowed to contain the group."""
    ref = m["nonfix"]
    notfix = ~m["fix"] & ~m["dropped"]
    out = [("all fixes", m["fix"], ref, "A")]
    for c in FIX_CLASSES:
        out.append((c, (m["cls"] == c) & m["window"], ref, "A"))
    out += [("extrinsic | platform", (m["cls"] == "extrinsic") & m["window"], m["nonfix"] & m["platform"], "A2"),
            ("reported | unreported", m["fix"] & m["reported"], m["fix"] & ~m["reported"], "A2"),
            ("CVE fix | control", m["cve_fix"], m["control"] & ~m["cve_fix"], "A2"),
            ("CVE-introducing", m["cve_intro"] & notfix, ref, "B"),
            ("regr-inducing", m["reg_inducing"] & notfix, ref, "B")]
    return [(name, g, r & ~g, sec) for name, g, r, sec in out]


def std_lift(X, bins, g: np.ndarray, ref: np.ndarray, rng, cols=None) -> dict:
    """Mean fraction in group g over the reference re-weighted to g's commit-size mix, with a CI."""
    cols = COLS if cols is None else cols
    nb = int(bins.max()) + 1

    def one(gi, ri):
        w = np.bincount(bins[gi], minlength=nb) / len(gi)
        have = np.bincount(bins[ri], minlength=nb) > 0
        lost = float(w[~have].sum())
        w = np.where(have, w, 0.0)
        w = w / w.sum() if w.sum() else w             # renormalise over cells the reference occupies
        exp = np.zeros(X.shape[1])
        for s in np.flatnonzero(w):
            exp += w[s] * X[ri[bins[ri] == s]].mean(axis=0)
        return X[gi].mean(axis=0), exp, lost

    gi, ri = np.flatnonzero(g), np.flatnonzero(ref)
    obs, exp, lost = one(gi, ri)
    boots = []
    for _ in range(DRAWS):
        o, e, _l = one(rng.choice(gi, len(gi)), rng.choice(ri, len(ri)))
        boots.append(np.divide(o, e, out=np.full_like(o, np.nan), where=e > 0))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # a label nobody carries: all-NaN column
        lo, hi = np.nanpercentile(np.array(boots), [2.5, 97.5], axis=0)
    kg, kr = (X[gi] > 0).sum(axis=0), (X[ri] > 0).sum(axis=0)
    out = {}
    for j, c in enumerate(cols):
        lift = float(obs[j] / exp[j]) if exp[j] > 0 else None
        out[c] = {"share": float(obs[j]), "expected": float(exp[j]), "lift": lift,
                  "lo": float(lo[j]), "hi": float(hi[j]), "k_group": int(kg[j]), "k_ref": int(kr[j]),
                  "marked": bool(lift is not None and kg[j] >= MIN_K and kr[j] >= MIN_K
                                 and (lo[j] > 1 or hi[j] < 1))}
    out["_lost_weight"] = lost
    return out


def follow_up(rows: list[dict], evs: dict, rng, cols=None, feats=row_cols) -> dict:
    """C: after a non-fix edit of type X, relative rate of (a) a fix and (b) any non-fix edit to the same
    function within a year, against the OTHER non-fix edits in the same stratum."""
    cols = COLS if cols is None else cols
    idx = {c: i for i, c in enumerate(cols)}
    per_commit: dict = defaultdict(int)
    for r in rows:
        per_commit[r["sha"]] += 1
    by_fn: dict = defaultdict(list)
    for r in rows:
        if per_commit[r["sha"]] <= et.SWEEP:
            by_fn[(r["path"], r["func"])].append(r)
    strata: dict = {}
    e_fn, e_s, e_y, e_y2, e_cols = [], [], [], [], []
    for f, edits in enumerate(by_fn.values()):
        is_fix = [e["sha"] in evs["class"] for e in edits]
        plain = [not fx and e["sha"] not in evs["dropped"] for e, fx in zip(edits, is_fix)]
        cts = [e["ct"] for e in edits]
        for k, e in enumerate(edits):
            if not plain[k] or e["ct"] < evs["since"] or e["ct"] + YEAR > evs["head_ct"]:
                continue
            before = [j for j in range(k) if cts[j] > e["ct"] - YEAR]
            after = [j for j in range(k + 1, len(edits)) if e["ct"] < cts[j] <= e["ct"] + YEAR]
            key = (min(max(int(math.log2(max(e["ntok"], 1))), 3), 12), mag_bin(e["tadd"] + e["tdel"]),
                   count_bin(len(before)), any(is_fix[j] for j in before), e["ct"] // (4 * YEAR))
            e_fn.append(f)
            e_s.append(strata.setdefault(key, len(strata)))
            e_y.append(any(is_fix[j] for j in after))
            e_y2.append(any(plain[j] for j in after))
            e_cols.append([idx[c] for c in feats(e)])
    E, S, F = len(e_fn), len(strata), len(by_fn)
    e_fn, e_s = np.array(e_fn), np.array(e_s)
    M = np.zeros((E, len(cols)))
    for i, cs in enumerate(e_cols):
        M[i, cs] = 1.0
    ys = {"fix": np.array(e_y, dtype=float), "any_edit": np.array(e_y2, dtype=float)}

    def rel(w):
        we = w[e_fn]
        out = {}
        for name, y in ys.items():
            N, Y = np.bincount(e_s, we, S), np.bincount(e_s, we * y, S)
            r = np.full(len(cols), np.nan)
            obs, exp, cov = r.copy(), r.copy(), r.copy()
            for c in range(len(cols)):
                n = np.bincount(e_s, we * M[:, c], S)
                yc = np.bincount(e_s, we * M[:, c] * y, S)
                nb, yb = N - n, Y - yc                   # everyone ELSE in the stratum
                ok = (nb > 0) & (n > 0)
                if n[ok].sum() > 0:
                    obs[c] = yc[ok].sum() / n[ok].sum()
                    exp[c] = (n[ok] * yb[ok] / nb[ok]).sum() / n[ok].sum()
                    cov[c] = n[ok].sum() / n.sum()
            out[name] = (obs, exp, cov)
        return out

    full = rel(np.ones(F))
    draws = [rel(rng.multinomial(F, np.full(F, 1 / F)).astype(float)) for _ in range(DRAWS)]
    res = {"eligible_edits": E, "strata": S, "functions": F,
           "base_rate": float(ys["fix"].mean()), "base_rate_any_edit": float(ys["any_edit"].mean()), "by": {}}
    with np.errstate(divide="ignore", invalid="ignore"):
        for j, c in enumerate(cols):
            cell = {"n": int(M[:, j].sum())}
            for name in ys:
                obs, exp, cov = full[name]
                b = np.array([d[name][0][j] / d[name][1][j] for d in draws])
                lo, hi = np.nanpercentile(b, [2.5, 97.5]) if np.isfinite(b).any() else (np.nan, np.nan)
                ok = bool(exp[j] > 0)
                cell[name] = {"rate": float(obs[j]), "expected": float(exp[j]),
                              "rel": float(obs[j] / exp[j]) if ok else None,
                              "lo": float(lo), "hi": float(hi), "coverage": float(cov[j]),
                              "marked": bool(ok and cell["n"] >= 100 and (lo > 1 or hi < 1))}
            res["by"][c] = cell
    return res


def analyse(repo: str, rows: list[dict], rng, cols=None, feats=None):
    """The whole join for one column set: (results by contrast, follow-up, masks, shas)."""
    cols = COLS if cols is None else cols
    feats = row_cols if feats is None else feats
    evs = load_events(repo)
    shas, X, n, ct, mag = commit_matrix(rows, cols, feats)
    bins = np.array([size_bin(k) * 4 + mag_bin(m) for k, m in zip(n, mag)])
    m = masks(repo, shas, ct, evs)
    res = {}
    for name, g, ref, sec in contrasts(m):
        if g.sum() >= 20 and ref.sum() >= 20:
            res[name] = {"section": sec, "commits": int(g.sum()), "reference_commits": int(ref.sum()),
                         "by": std_lift(X, bins, g, ref, rng, cols)}
            res[name]["lost_weight"] = res[name]["by"].pop("_lost_weight")
    return res, follow_up(rows, evs, rng, cols, feats), m, shas, X


def table(title: str, res: dict, groups: list[str], cols: list[str]) -> None:
    print(f"\n  {title}")
    print("    " + f"{'':16}" + "".join(f"{g[:21]:>23}" for g in groups))
    for c in cols:
        cells = []
        for g in groups:
            v = res[g]["by"][c]
            if v["lift"] is None:
                cells.append("-")
            else:
                cells.append(f"{v['lift']:5.2f}{'*' if v['marked'] else ' '}[{v['lo']:4.2f},{v['hi']:5.2f}] k={v['k_group']}")
        print("    " + f"{c.replace('P:', ''):16}" + "".join(f"{x:>23}" for x in cells))


def follow_table(fu: dict, cols: list[str]) -> None:
    print(f"\n  C. After a NON-fix edit, within 365 days: is the function FIXED, and (negative control) is it "
          f"EDITED at all?\n     {fu['eligible_edits']:,} eligible edits in {fu['strata']:,} strata; base rates "
          f"{fu['base_rate']:.1%} fixed, {fu['base_rate_any_edit']:.1%} edited. Relative to the other edits "
          f"in the same stratum.")
    print(f"    {'type of the edit':16} {'n':>7}   {'fixed: relative':<26} {'edited: relative':<26}")
    for c in cols:
        v = fu["by"][c]
        if v["n"] < 100 or v["fix"]["rel"] is None:
            continue
        cell = lambda x: f"{x['rel']:5.2f}{'*' if x['marked'] else ' '}[{x['lo']:.2f}, {x['hi']:.2f}]"
        print(f"    {c.replace('P:', ''):16} {v['n']:7,}   {cell(v['fix']):<26} {cell(v['any_edit']):<26}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default="curl", choices=("curl", "libarchive"))   # the burned repos only
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    res, fu, m, shas, _X = analyse(a.repo, et.load(a.inp), rng)
    counts = {"commits_with_function_edits": len(shas), "in_window": int(m["window"].sum()),
              "fix": int(m["fix"].sum()), "not_a_fix_by_message": int(m["nonfix_raw"].sum()),
              "reference": int(m["nonfix"].sum()),
              "dropped_by_v3c": int((m["dropped"] & m["window"]).sum())}
    print(f"{a.repo}: {counts['commits_with_function_edits']:,} commits with 1-{et.SWEEP} function edits; "
          f"{counts['fix']:,} fix, {counts['reference']:,} in the reference "
          f"({counts['not_a_fix_by_message']:,} not-a-fix by message, less cosmetic subjects), "
          f"{counts['dropped_by_v3c']:,} dropped by v3c")
    print(f"  EXPLORATORY. * = 95% interval excludes 1 and >= {MIN_K} commits carry the label on both sides. "
          f"k = group commits carrying it. No multiplicity correction.")
    print("  " + "; ".join(f"{g}: {v['commits']:,} vs {v['reference_commits']:,}" for g, v in res.items()))
    fam = ["P:" + f for f in et.PRIORITY if f != "RESIDUAL"]
    atoms = [l for l in et.LABELS if l not in ("EXPR_EDIT", "UNCLASSIFIED")]
    for sec, title in (("A", "A. Fix classes, lift over the non-fix reference of the same size and magnitude"),
                       ("A2", "A. Direct contrasts (group | reference)"),
                       ("B", "B. Commits later named as introducing a defect (non-fix members only)")):
        gs = [g for g, v in res.items() if v["section"] == sec]
        if gs:
            table(title + ": primary family", res, gs, fam)
            table(title + ": atomic labels", res, gs, atoms)
    follow_table(fu, fam + atoms)
    if a.json:
        Path(a.json).write_text(json.dumps({"repo": a.repo, "type": "exploratory", "counts": counts,
                                            "contrasts": res, "follow_up": fu}, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
