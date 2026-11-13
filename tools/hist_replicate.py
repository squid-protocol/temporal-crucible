#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""HR-1: recidivism at file grain over the CGR cohort (docs/hist_replication.md, registered before this ran).

    python tools/hist_replicate.py --study <laws-study/pilot> --out docs/hr1.json [--md docs/hr1.md]

Does a file's count of PRIOR fix commits order its next-window fixes better than LOC does? That is the
program's one cross-repo replicated predictor, carried from 2 C repos to 8 repos in 5 languages. Replication
on SEEN repos: breadth or falsification, never fresh confirmation.

Every choice below is the registered one and none may be tuned after seeing a number: cut at the 80th
percentile of commit time, outcome = any `fix` commit in the following 24 months, predictors = raw prior-fix
count and a 365-day half-life decay, baseline = total_loc at the nearest walk snapshot, bots and merges
excluded, a repo with fewer than 30 post-cut positives is `not evaluable`.
"""
from __future__ import annotations

import argparse, json, math, sqlite3
from pathlib import Path

REPOS = ("commons-lang", "libgit2", "libxml2", "postgres", "prometheus", "redis", "ripgrep", "sphinx")
WINDOW_DAYS = 730          # 24 months after the cut
CUT_Q = 0.80               # the cut is the 80th percentile of commit time
HALF_LIFE_DAYS = 365.0
MIN_POSITIVES = 30         # below this a repo is not evaluable, stated in advance
BUDGET = 0.20              # effort-aware: 20% of lines reviewed


def auc(scores: list[float], labels: list[int]) -> float | None:
    """Rank AUC with ties at half credit (Mann-Whitney U / n_pos n_neg)."""
    pos = sum(labels)
    neg = len(labels) - pos
    if not pos or not neg:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    s = sum(ranks[i] for i in range(len(labels)) if labels[i])
    return (s - pos * (pos + 1) / 2.0) / (pos * neg)


def recall_at_budget(scores, labels, loc, budget=BUDGET):
    """Share of defective files caught when `budget` of the repo's lines are reviewed, richest-first."""
    total = sum(loc) or 1
    idx = sorted(range(len(scores)), key=lambda i: (-scores[i], loc[i]))
    seen = hit = 0
    for i in idx:
        if seen + loc[i] > total * budget:
            break
        seen += loc[i]
        hit += labels[i]
    pos = sum(labels)
    return hit / pos if pos else None


def boot_ci(f, n, reps=2000, seed=2982):
    """Percentile bootstrap over files, for the lift's interval."""
    import random
    rnd = random.Random(seed)
    out = []
    for _ in range(reps):
        idx = [rnd.randrange(n) for _ in range(n)]
        v = f(idx)
        if v is not None:
            out.append(v)
    if len(out) < reps // 4:
        return None, None
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def one_repo(study: Path, repo: str) -> dict:
    h = sqlite3.connect(f"file:{study/'history'/f'{repo}.db'}?mode=ro", uri=True)
    w = sqlite3.connect(f"file:{study/'dbs'/f'{repo}.db'}?mode=ro", uri=True)
    rec: dict = {"repo": repo}
    cts = [r[0] for r in h.execute("select ct from commit_ where merge=0 and bot=0 order by ct")]
    if len(cts) < 200:
        return {**rec, "evaluable": False, "why": f"only {len(cts)} usable commits"}
    cut = cts[int(len(cts) * CUT_Q)]
    end = cut + WINDOW_DAYS * 86400
    rec.update(commits=len(cts), cut_epoch=cut, window_days=WINDOW_DAYS)

    # prior fix touches per file identity, and post-cut fix touches
    prior: dict[int, list[int]] = {}
    post: dict[int, int] = {}
    q = ("select t.file, c.ct, c.fix from touch t join commit_ c on c.sha=t.sha "
         "where c.merge=0 and c.bot=0 and c.fix=1")
    for fid, ct, _ in h.execute(q):
        if ct < cut:
            prior.setdefault(fid, []).append(ct)
        elif ct <= end:
            post[fid] = post.get(fid, 0) + 1

    # files alive at the cut, by lineage
    alive = {fid: path for fid, path, since, until in
             h.execute("select file, path, since, until from lineage")
             if since <= cut and (until is None or until >= cut)}
    if not alive:
        return {**rec, "evaluable": False, "why": "no file alive at the cut"}

    # LOC from the walk snapshot nearest the cut
    snaps = [(r[0], r[1]) for r in w.execute("select commit_hash, date from snap where rc=0")]
    def epoch(d):
        import datetime as dt
        try:
            return dt.datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    cand = [(abs((epoch(d) or 0) - cut), c) for c, d in snaps if epoch(d)]
    if not cand:
        return {**rec, "evaluable": False, "why": "no scanned snapshot to take LOC from"}
    _, sha = min(cand)
    loc_by_path = {p: l for p, l in w.execute(
        "select path, total_loc from file where commit_hash=? and generated=0", (sha,))}
    rec["loc_snapshot"] = sha[:9]

    rows = []
    for fid, path in alive.items():
        loc = loc_by_path.get(path)
        if not loc:
            continue                      # not in the structural snapshot (not a source file we scan)
        times = prior.get(fid, [])
        raw = len(times)
        decay = sum(0.5 ** ((cut - t) / 86400.0 / HALF_LIFE_DAYS) for t in times)
        rows.append((raw, decay, float(loc), 1 if post.get(fid) else 0))
    pos = sum(r[3] for r in rows)
    rec.update(files=len(rows), positives=pos)
    if pos < MIN_POSITIVES:
        return {**rec, "evaluable": False,
                "why": f"{pos} post-cut positives, under the registered floor of {MIN_POSITIVES}"}

    raws = [r[0] for r in rows]; decays = [r[1] for r in rows]
    locs = [r[2] for r in rows]; labs = [r[3] for r in rows]
    a_loc, a_raw, a_dec = auc(locs, labs), auc(raws, labs), auc(decays, labs)
    rec.update(evaluable=True, auc_loc=a_loc, auc_recidivism=a_raw, auc_recidivism_decay=a_dec,
               lift=(a_raw - a_loc) if (a_raw and a_loc) else None,
               lift_decay=(a_dec - a_loc) if (a_dec and a_loc) else None)
    lo, hi = boot_ci(lambda idx: (lambda s, l: (auc([raws[i] for i in idx], [labs[i] for i in idx]) or 0)
                                  - (auc([locs[i] for i in idx], [labs[i] for i in idx]) or 0))(None, None),
                     len(rows))
    rec["lift_ci95"] = [lo, hi]
    rec["recall20_loc"] = recall_at_budget(locs, labs, locs)
    rec["recall20_recidivism"] = recall_at_budget(raws, labs, locs)
    h.close(); w.close()
    return rec


def pooled(res: list[dict]) -> dict:
    ev = [r for r in res if r.get("evaluable") and r.get("lift") is not None]
    if len(ev) < 2:
        return {"poolable": False, "why": f"{len(ev)} evaluable repos"}
    xs = [r["lift"] for r in ev]
    m = sum(xs) / len(xs)
    sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
    se = sd / math.sqrt(len(xs))
    return {"poolable": True, "k": len(ev), "mean_lift": m, "se": se,
            "ci95": [m - 1.96 * se, m + 1.96 * se],
            "positive": sum(1 for x in xs if x > 0),
            "verdict": ("breadth shown" if sum(1 for x in xs if x > 0) >= 6 and m - 1.96 * se > 0
                        else "NOT shown at the registered bar")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args()
    res = []
    for r in REPOS:
        rec = one_repo(a.study, r)
        res.append(rec)
        print(f"  {r:14} " + ("not evaluable: " + rec.get("why", "")
                              if not rec.get("evaluable") else
                              f"files {rec['files']:5} pos {rec['positives']:4}  "
                              f"AUC loc {rec['auc_loc']:.3f} -> recidivism {rec['auc_recidivism']:.3f}  "
                              f"lift {rec['lift']:+.4f}"), flush=True)
    p = pooled(res)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"registration": "docs/hist_replication.md", "hypothesis": "HR-1",
                                 "repos": res, "pooled": p}, indent=1) + "\n")
    print(f"\npooled: {json.dumps(p)}\n-> {a.out}")
    if a.md:
        L = ["# HR-1 — recidivism at file grain, CGR cohort (replication on seen repos)", "",
             "Registered in `hist_replication.md` before this ran. Breadth or falsification; never fresh confirmation.", "",
             "| repo | files | positives | AUC(LOC) | AUC(recidivism) | lift | 95% CI | recall@20% LOC → recid |",
             "|---|---|---|---|---|---|---|---|"]
        for r in res:
            if not r.get("evaluable"):
                L.append(f"| {r['repo']} | — | — | — | — | — | — | *{r.get('why','')}* |"); continue
            lo, hi = r.get("lift_ci95") or (None, None)
            ci = f"{lo:+.3f}, {hi:+.3f}" if lo is not None else "—"
            L.append(f"| {r['repo']} | {r['files']} | {r['positives']} | {r['auc_loc']:.3f} | "
                     f"{r['auc_recidivism']:.3f} | **{r['lift']:+.4f}** | {ci} | "
                     f"{r['recall20_loc']:.3f} → {r['recall20_recidivism']:.3f} |")
        L += ["", f"**Pooled:** {json.dumps(p)}"]
        a.md.write_text("\n".join(L) + "\n")
        print(f"-> {a.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
