#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Do STRUCTURAL metrics beat size at predicting fixes -- and does the answer change with the label?

    python tools/struct_null.py --repo curl

The programme's standing claim is that structure reduces to size. `attenuation.py` showed that claim is
weakly identified: our label transmits only ~30% of a real structural effect, so an observed null is
consistent with a true lift as large as the one history effect we defended. The obvious test is to re-run the
structural comparison under a BETTER outcome and see whether the null holds.

Three labels, same files, same cut, same baseline:

  raw       the keyword gate                                  (precision 0.27-0.86, recall ~0.41)
  v3c       the cleaned keyword gate                          (higher precision, recall ~0.29)
  cascade   revert + `Fixes #N` + CVE + keyword, tiers ranked  (broader; recall not yet measured)

Structural predictors come from the engine's call graph at the snapshot nearest the cut -- they do not depend
on anybody's commit prose, which is why their error is independent of the label's and the association is
attenuated rather than inflated.

  in_degree   calls INTO the file's functions (a centrality proxy)
  out_degree  calls OUT of them
  funcs       function count
  loc         the BASELINE every predictor must beat
"""
from __future__ import annotations

import argparse, datetime as dt, json, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hist_replicate import auc, boot_ci, CUT_Q, WINDOW_DAYS, MIN_POSITIVES  # noqa: E402
from hist_fixlabel import fix_shas  # noqa: E402
from label_cascade import tiers_for  # noqa: E402

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")


def structure(repo: str, cut: int):
    """per-file structural metrics at the snapshot nearest the cut"""
    w = sqlite3.connect(f"file:{STUDY/'dbs'/f'{repo}.db'}?mode=ro", uri=True)
    best, sha = None, None
    for c, d in w.execute("select commit_hash, date from snap where rc=0"):
        try:
            e = dt.datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if best is None or abs(e - cut) < best:
            best, sha = abs(e - cut), c
    if not sha:
        return {}, None
    loc = {}
    fid2path = {}
    for fid, path, l in w.execute(
            "select id, path, total_loc from file where commit_hash=? and generated=0", (sha,)):
        if l:
            loc[path] = float(l)
            fid2path[fid] = path
    func2path, nfunc = {}, {}
    for uid, fid in w.execute("select id, file_id from func where commit_hash=?", (sha,)):
        p = fid2path.get(fid)
        if p:
            func2path[uid] = p
            nfunc[p] = nfunc.get(p, 0) + 1
    indeg, outdeg = {}, {}
    for src, dst in w.execute("select src, dst from edge where commit_hash=?", (sha,)):
        ps, pd = func2path.get(src), func2path.get(dst)
        if pd:
            indeg[pd] = indeg.get(pd, 0) + 1
        if ps:
            outdeg[ps] = outdeg.get(ps, 0) + 1
    w.close()
    return {p: {"loc": loc[p], "in_degree": float(indeg.get(p, 0)), "out_degree": float(outdeg.get(p, 0)),
                "funcs": float(nfunc.get(p, 0))} for p in loc}, sha


def outcomes(repo: str, cut: int, end: int, label: str) -> set[str]:
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{repo}.db'}?mode=ro", uri=True)
    if label == "cascade":
        tier, _pool = tiers_for(repo)
        keep = {s for s, t in tier.items() if t in ("T1_revert", "T2_fixref", "T3_cve", "T4_keyword")}
        rows = h.execute("select t.path, t.sha from touch t join commit_ c on c.sha=t.sha "
                         "where c.merge=0 and c.bot=0 and c.ct>? and c.ct<=?", (cut, end))
        out = {p for p, s in rows if s in keep}
    else:
        keepf = fix_shas(h, "raw" if label == "raw" else "v3c")
        rows = h.execute("select t.path, t.sha from touch t join commit_ c on c.sha=t.sha "
                         "where c.merge=0 and c.bot=0 and c.fix=1 and c.ct>? and c.ct<=?", (cut, end))
        out = {p for p, s in rows if keepf is None or s in keepf}
    h.close()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="curl")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{a.repo}.db'}?mode=ro", uri=True)
    cts = [r[0] for r in h.execute("select ct from commit_ where merge=0 and bot=0 order by ct")]
    h.close()
    cut = cts[int(len(cts) * CUT_Q)]
    end = cut + WINDOW_DAYS * 86400
    feats, sha = structure(a.repo, cut)
    if not feats:
        print(f"{a.repo}: no scanned snapshot"); return 1
    print(f"{a.repo}: {len(feats):,} files at snapshot {sha[:9]}, cut "
          f"{dt.datetime.fromtimestamp(cut, dt.timezone.utc).date()}\n")
    res = {}
    for label in ("raw", "v3c", "cascade"):
        post = outcomes(a.repo, cut, end, label)
        paths = sorted(feats)
        y = [1 if p in post else 0 for p in paths]
        pos = sum(y)
        if pos < MIN_POSITIVES:
            print(f"  {label:9} only {pos} positives -- under the floor"); continue
        base = auc([feats[p]["loc"] for p in paths], y)
        line = f"  {label:9} positives {pos:4}   AUC(loc) {base:.3f}"
        lifts = {}
        for metric in ("in_degree", "out_degree", "funcs"):
            v = [feats[p][metric] for p in paths]
            m = auc(v, y)
            lift = (m or 0) - (base or 0)
            lo, hi = boot_ci(lambda ix: (auc([v[i] for i in ix], [y[i] for i in ix]) or 0)
                             - (auc([feats[paths[i]]["loc"] for i in ix], [y[i] for i in ix]) or 0),
                             len(paths), reps=600)
            lifts[metric] = {"auc": m, "lift": lift, "ci95": [lo, hi]}
            line += f"\n            {metric:11} AUC {m:.3f}  lift {lift:+.4f}  CI [{lo:+.3f}, {hi:+.3f}]"
        print(line)
        res[label] = {"positives": pos, "auc_loc": base, "metrics": lifts}
    if a.out:
        a.out.write_text(json.dumps({"repo": a.repo, "results": res}, indent=1) + "\n")
        print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
