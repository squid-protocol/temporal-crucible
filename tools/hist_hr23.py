#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""HR-2 (change entropy HCM1_LD_30) and HR-3 (function-grain recidivism), on the line-delta harvest.

    python tools/hist_hr23.py hr2 --out docs/hr2.json --md docs/hr2.md
    python tools/hist_hr23.py hr3 --out docs/hr3.json --md docs/hr3.md

Both definitions are fixed in docs/hist_replication.md and were committed BEFORE either was run. Cut, outcome
window, baseline, exclusions and floors are HR-1's, unchanged, so all three are comparable on the same files.
Replication on SEEN repos: breadth or falsification, never fresh confirmation.
"""
from __future__ import annotations

import argparse, json, math, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hist_replicate import (REPOS, WINDOW_DAYS, CUT_Q, MIN_POSITIVES, BUDGET,  # noqa: E402
                            auc, recall_at_budget, boot_ci)

PERIOD_DAYS = 30
STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")


def ro(p: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def cut_of(h: sqlite3.Connection) -> tuple[int, int] | None:
    cts = [r[0] for r in h.execute("select ct from commit_ where merge=0 and bot=0 order by ct")]
    if len(cts) < 200:
        return None
    cut = cts[int(len(cts) * CUT_Q)]
    return cut, cut + WINDOW_DAYS * 86400


def nearest_snapshot(w: sqlite3.Connection, when: int) -> str | None:
    import datetime as dt
    best, sha = None, None
    for c, d in w.execute("select commit_hash, date from snap where rc=0"):
        try:
            e = dt.datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if best is None or abs(e - when) < best:
            best, sha = abs(e - when), c
    return sha


def outcomes(h: sqlite3.Connection, cut: int, end: int) -> set[str]:
    """paths touched by a fix commit in the outcome window"""
    return {r[0] for r in h.execute(
        "select t.path from touch t join commit_ c on c.sha=t.sha "
        "where c.merge=0 and c.bot=0 and c.fix=1 and c.ct>? and c.ct<=?", (cut, end))}


def hr2_repo(repo: str) -> dict:
    h, w = ro(STUDY / "history" / f"{repo}.db"), ro(STUDY / "dbs" / f"{repo}.db")
    d = STUDY / "deltas" / f"{repo}.db"
    rec = {"repo": repo}
    if not d.exists():
        return {**rec, "evaluable": False, "why": "no line-delta harvest"}
    dd = ro(d)
    c = cut_of(h)
    if not c:
        return {**rec, "evaluable": False, "why": "too few usable commits"}
    cut, end = c
    sha = nearest_snapshot(w, cut)
    if not sha:
        return {**rec, "evaluable": False, "why": "no scanned snapshot"}
    loc = {p: l for p, l in w.execute(
        "select path, total_loc from file where commit_hash=? and generated=0", (sha,))}
    ct_of = dict(h.execute("select sha, ct from commit_ where merge=0 and bot=0"))

    # changed lines per (period, path), periods tiled backwards from the cut
    per: dict[int, dict[str, int]] = {}
    for s, path, a, dl in dd.execute("select sha, path, added, deleted from delta where binary=0"):
        t = ct_of.get(s)
        if t is None or t >= cut:
            continue
        i = int((cut - t) // (PERIOD_DAYS * 86400))      # 0 = most recent period
        per.setdefault(i, {})[path] = per[i].get(path, 0) + a + dl
    if not per:
        return {**rec, "evaluable": False, "why": "no pre-cut line deltas"}
    K = max(per) + 1
    hcm: dict[str, float] = {}
    for i, files in per.items():
        tot = sum(files.values())
        if tot <= 0 or len(files) < 2:
            continue                                     # H = 0 by definition for a single changed file
        H = -sum((v / tot) * math.log(v / tot) for v in files.values()) / math.log(len(files))
        wgt = (K - i) / K                                # linear decay: newest period weighs 1
        for path, v in files.items():
            hcm[path] = hcm.get(path, 0.0) + wgt * (v / tot) * H

    post = outcomes(h, cut, end)
    # recidivism on the same files, so "does entropy ADD" can be read off directly
    prior: dict[str, int] = {}
    for path, in h.execute("select t.path from touch t join commit_ c on c.sha=t.sha "
                           "where c.merge=0 and c.bot=0 and c.fix=1 and c.ct<?", (cut,)):
        prior[path] = prior.get(path, 0) + 1
    rows = [(hcm.get(p, 0.0), float(l), prior.get(p, 0), 1 if p in post else 0)
            for p, l in loc.items()]
    pos = sum(r[3] for r in rows)
    rec.update(files=len(rows), positives=pos, periods=K)
    if pos < MIN_POSITIVES:
        return {**rec, "evaluable": False, "why": f"{pos} positives under the floor of {MIN_POSITIVES}"}
    E = [r[0] for r in rows]; L = [r[1] for r in rows]; R = [r[2] for r in rows]; Y = [r[3] for r in rows]
    a_e, a_l, a_r = auc(E, Y), auc(L, Y), auc(R, Y)
    lo, hi = boot_ci(lambda ix: (auc([E[i] for i in ix], [Y[i] for i in ix]) or 0)
                     - (auc([L[i] for i in ix], [Y[i] for i in ix]) or 0), len(rows))
    rec.update(evaluable=True, auc_loc=a_l, auc_entropy=a_e, auc_recidivism=a_r,
               lift_over_loc=a_e - a_l, lift_over_recidivism=a_e - a_r, lift_ci95=[lo, hi],
               recall20_loc=recall_at_budget(L, Y, L), recall20_entropy=recall_at_budget(E, Y, L))
    return rec


def hr3_repo(repo: str) -> dict:
    h, w = ro(STUDY / "history" / f"{repo}.db"), ro(STUDY / "dbs" / f"{repo}.db")
    d = STUDY / "deltas" / f"{repo}.db"
    rec = {"repo": repo}
    if not d.exists():
        return {**rec, "evaluable": False, "why": "no line-delta harvest"}
    dd = ro(d)
    c = cut_of(h)
    if not c:
        return {**rec, "evaluable": False, "why": "too few usable commits"}
    cut, end = c
    ct_of = dict(h.execute("select sha, ct from commit_ where merge=0 and bot=0 and fix=1"))
    snaps = []
    import datetime as dt
    for ch, dstr in w.execute("select commit_hash, date from snap where rc=0"):
        try:
            snaps.append((dt.datetime.fromisoformat(dstr.replace("Z", "+00:00")).timestamp(), ch))
        except Exception:
            pass
    if not snaps:
        return {**rec, "evaluable": False, "why": "no scanned snapshot"}
    snaps.sort()

    # function spans per snapshot, lazily
    spans: dict[str, dict[str, list[tuple[int, int, str]]]] = {}
    def spans_of(sha: str):
        if sha not in spans:
            m: dict[str, list[tuple[int, int, str]]] = {}
            for path, name, start, loc in w.execute(
                    "select f.path, u.name, u.start_line, u.loc from func u join file f on f.id=u.file_id "
                    "where u.commit_hash=? and f.generated=0", (sha,)):
                if start and loc:
                    m.setdefault(path, []).append((start, start + loc, name))
            spans[sha] = m
        return spans[sha]

    def hits(sha_commit: str, path: str, start: int, n: int, when: int) -> set[tuple[str, str]]:
        i = min(range(len(snaps)), key=lambda k: abs(snaps[k][0] - when))
        out = set()
        for s, e, name in spans_of(snaps[i][1]).get(path, ()):
            if start < e and (start + max(n, 1)) > s:
                out.add((path, name))
        return out

    prior: dict[tuple[str, str], int] = {}
    post: set[tuple[str, str]] = set()
    for s, path, st, n in dd.execute("select sha, path, new_start, new_lines from hunk"):
        t = ct_of.get(s)
        if t is None:
            continue
        if t < cut:
            for k in hits(s, path, st, n, t):
                prior[k] = prior.get(k, 0) + 1
        elif t <= end:
            post |= hits(s, path, st, n, t)

    cut_sha = min(snaps, key=lambda x: abs(x[0] - cut))[1]
    cand: dict[tuple[str, str], int] = {}
    merged = 0
    for path, name, loc in w.execute(
            "select f.path, u.name, u.loc from func u join file f on f.id=u.file_id "
            "where u.commit_hash=? and f.generated=0", (cut_sha,)):
        k = (path, name)
        if k in cand:
            merged += 1
        cand[k] = max(cand.get(k, 0), loc or 0)
    rows = [(prior.get(k, 0), float(v or 1), 1 if k in post else 0) for k, v in cand.items() if v]
    pos = sum(r[2] for r in rows)
    rec.update(functions=len(rows), positives=pos,
               node_merge_rate=round(merged / max(len(cand) + merged, 1), 4))
    if pos < MIN_POSITIVES:
        return {**rec, "evaluable": False, "why": f"{pos} positives under the floor of {MIN_POSITIVES}"}
    P = [r[0] for r in rows]; L = [r[1] for r in rows]; Y = [r[2] for r in rows]
    a_p, a_l = auc(P, Y), auc(L, Y)
    lo, hi = boot_ci(lambda ix: (auc([P[i] for i in ix], [Y[i] for i in ix]) or 0)
                     - (auc([L[i] for i in ix], [Y[i] for i in ix]) or 0), len(rows))
    rec.update(evaluable=True, auc_loc=a_l, auc_recidivism=a_p, lift=a_p - a_l, lift_ci95=[lo, hi],
               recall20_loc=recall_at_budget(L, Y, L), recall20_recidivism=recall_at_budget(P, Y, L))
    return rec


def pool(res, key):
    ev = [r for r in res if r.get("evaluable") and r.get(key) is not None]
    if len(ev) < 2:
        return {"poolable": False, "why": f"{len(ev)} evaluable"}
    xs = [r[key] for r in ev]
    m = sum(xs) / len(xs)
    sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
    se = sd / math.sqrt(len(xs))
    return {"poolable": True, "k": len(xs), "mean": m, "se": se,
            "ci95": [m - 1.96 * se, m + 1.96 * se], "positive": sum(1 for x in xs if x > 0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=("hr2", "hr3"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args()
    fn = hr2_repo if a.which == "hr2" else hr3_repo
    res = []
    for r in REPOS:
        rec = fn(r)
        res.append(rec)
        if not rec.get("evaluable"):
            print(f"  {r:14} not evaluable: {rec.get('why')}", flush=True)
        elif a.which == "hr2":
            print(f"  {r:14} files {rec['files']:5} pos {rec['positives']:4}  AUC loc {rec['auc_loc']:.3f} "
                  f"entropy {rec['auc_entropy']:.3f} recid {rec['auc_recidivism']:.3f}  "
                  f"lift/loc {rec['lift_over_loc']:+.4f}  lift/recid {rec['lift_over_recidivism']:+.4f}", flush=True)
        else:
            print(f"  {r:14} funcs {rec['functions']:6} pos {rec['positives']:4}  AUC loc {rec['auc_loc']:.3f} "
                  f"-> recid {rec['auc_recidivism']:.3f}  lift {rec['lift']:+.4f} "
                  f"(merge {rec['node_merge_rate']:.1%})", flush=True)
    key = "lift_over_loc" if a.which == "hr2" else "lift"
    p = pool(res, key)
    extra = pool(res, "lift_over_recidivism") if a.which == "hr2" else None
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"registration": "docs/hist_replication.md",
                                 "hypothesis": a.which.upper().replace("HR", "HR-"),
                                 "repos": res, "pooled": p,
                                 **({"pooled_over_recidivism": extra} if extra else {})}, indent=1) + "\n")
    print(f"\npooled {key}: {json.dumps(p)}")
    if extra:
        print(f"pooled lift over recidivism: {json.dumps(extra)}")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
