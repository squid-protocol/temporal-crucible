#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""DCR-H1 (docs/dc_hypotheses.md § DC-R): danger comments at birth vs whole-life first CVE fix, on unseen repos,
reconstructed from git + tree-sitter + the engine C comment stream. Engine venv.

    <engine venv>/bin/python tools/dcr_eval.py
"""
from __future__ import annotations

import bisect
import datetime as dt
import json
import multiprocessing
import pathlib
import re
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from chg_eval import _fname, _git, _parser, map_fix  # noqa: E402
from dc_eval import DANGER, prism  # noqa: E402
from ints_eval import mh_rate  # noqa: E402

REPOS = ("libxml2", "libexif", "file", "libtiff", "libpng")
YEAR = 365.25 * 86400
SEED, ITERS, ALPHA, MIN_EV = 2982, 2000, 0.01, 15
SKIP = re.compile(r"(^|/)(tests?|fuzz|testsuite)(/|$)", re.I)
_CACHE = {}


def blob_info(t):
    """(repo, blob) -> {name: (start0, end0, ncomment, danger)} from tree-sitter spans + engine comment stream."""
    r, blob = t
    raw = _git(POOL_DIR / r, "cat-file", "-p", blob, text=False)
    if not raw:
        return blob, {}
    try:
        pos = prism().split_positional_comment_stream(raw.decode("utf-8", "replace"), "c").split("\n")
    except Exception:
        pos = []
    lines = raw.decode("utf-8", "replace").split("\n")
    out, stack = {}, [_parser("c").parse(raw).root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm and nm not in out:
                a, b = n.start_point[0], n.end_point[0]
                idx = [i for i in range(a, min(b + 1, len(pos))) if pos[i].strip()]
                i, blank = a - 1, 0
                while i >= 0 and i < len(pos):
                    if pos[i].strip():
                        idx.append(i)
                        blank = 0
                    elif i < len(lines) and not lines[i].strip() and blank == 0:
                        blank = 1
                    else:
                        break
                    i -= 1
                text = "\n".join(pos[k] for k in set(idx) if k < len(pos))
                out[nm] = (a, b, len(set(idx)), bool(DANGER.search(text)))
            continue
        stack.extend(n.children)
    return blob, out


def quarterly(repo, head):
    cs = [(int(c), h) for h, c in (l.split() for l in _git(repo, "log", "--first-parent", "--format=%H %ct", head).splitlines() if l)]
    cs.sort()
    ts = [c for c, _ in cs]
    t0 = dt.datetime.fromtimestamp(cs[0][0], dt.timezone.utc)
    q = dt.datetime(t0.year, (t0.month - 1) // 3 * 3 + 1, 1, tzinfo=dt.timezone.utc)
    out, end = [], dt.datetime.fromtimestamp(cs[-1][0], dt.timezone.utc)
    while q <= end:
        m = q.month + 3
        q = dt.datetime(q.year + (m > 12), (m - 1) % 12 + 1, 1, tzinfo=dt.timezone.utc)
        i = bisect.bisect_left(ts, q.timestamp()) - 1
        if i >= 0 and (not out or out[-1][0] != cs[i][1]):
            out.append((cs[i][1], cs[i][0]))
    return out


def main() -> int:
    t0 = time.time()
    U, per_repo = [], {}
    for r in REPOS:
        repo = POOL_DIR / r
        meta = json.loads((REPO_ROOT / "events" / f"{r}.json").read_text())
        head = meta.get("pool_head") or _git(repo, "rev-parse", "HEAD").strip()
        snaps = quarterly(repo, head)
        head_ct = int(_git(repo, "show", "-s", "--format=%ct", head).strip())
        trees = []
        for sha, ct in snaps:
            files = {}
            for ln in _git(repo, "ls-tree", "-r", sha).splitlines():
                parts = ln.split(None, 3)
                if len(parts) == 4 and parts[3].endswith(".c") and not SKIP.search(parts[3]):
                    files[parts[3]] = parts[2]
            trees.append(files)
        blobs = sorted({(r, b) for f in trees for b in f.values()} - set(_CACHE))
        with multiprocessing.get_context("fork").Pool(8) as p:
            for blob, info in p.imap_unordered(blob_info, blobs, chunksize=8):
                _CACHE[(r, blob)] = info
        per = [{(path, nm): v for path, b in f.items() for nm, v in _CACHE.get((r, b), {}).items()} for f in trees]
        # identity + births
        ids_at, info, prev, prev_ids, nxt = [], {}, None, {}, 0
        for k, d in enumerate(per):
            cur, moved = {}, {}
            if prev is not None:
                vn, nn = defaultdict(list), defaultdict(list)
                for key in prev:
                    if key not in d:
                        vn[key[1]].append(key)
                for key in d:
                    if key not in prev:
                        nn[key[1]].append(key)
                moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
            for key in d:
                if prev is not None and key in prev:
                    cur[key] = prev_ids[key]
                elif key in moved:
                    cur[key] = prev_ids[moved[key]]
                else:
                    cur[key] = nxt
                    a, b, nc, dg = d[key]
                    info[nxt] = {"birth_k": k, "key": key, "loc": b - a + 1, "nc": nc, "danger": dg}
                    nxt += 1
                info[cur[key]]["last_k"] = k
            ids_at.append(cur)
            prev, prev_ids = d, cur
        cts = [c for _, c in snaps]
        ev = [(r, e["sha"], int(_git(repo, "show", "-s", "--format=%ct", e["sha"]).strip() or 0), "latent")
              for e in meta["events"] if e.get("class") == "security-fix"]
        ev = [x for x in ev if x[2]]
        with multiprocessing.get_context("fork").Pool(8) as p:
            hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=2) for h in hs]
        first, file_cve = {}, defaultdict(list)
        for (_r, path, nm, ct, _k) in hits:
            file_cve[path].append(ct)
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            fid = None
            for jj in (j, j + 1):
                if jj < len(ids_at) and fid is None:
                    fid = ids_at[jj].get((path, nm))
            if fid is not None and (fid not in first or ct < first[fid]):
                first[fid] = ct
        for v in file_cve.values():
            v.sort()
        n0 = len(U)
        for fid, inf in info.items():
            if inf["birth_k"] == 0 or inf["loc"] < 3 or inf["nc"] < 1:
                continue
            b = cts[inf["birth_k"]]
            death = cts[inf["last_k"] + 1] if inf["last_k"] + 1 < len(cts) else float("inf")
            end = min(death, head_ct)
            if end <= b:
                continue
            prior = bisect.bisect_left(file_cve.get(inf["key"][0], []), b) > 0
            hit = fid in first and b < first[fid] <= end
            U.append((r, inf["key"][0], int(np.floor(np.log10(inf["loc"]) / 0.1)), prior, inf["danger"],
                      1.0 if hit else 0.0, ((first[fid] if hit else end) - b) / YEAR))
        per_repo[r] = (len(snaps), len(ev), len(U) - n0)
        print(f"{r}: snapshots {len(snaps)}, security fixes {len(ev)}, commented births {len(U) - n0:,} ({time.time() - t0:.0f}s)", flush=True)
    e = np.array([1.0 if u[4] else 0.0 for u in U])
    y = np.array([u[5] for u in U])
    pt = np.array([u[6] for u in U])
    st = np.array([f"{u[0]}|{u[2]}|{u[3]}" for u in U])
    cl = np.array([f"{u[0]}:{u[1]}" for u in U])
    rr = mh_rate(e, y, pt, st)
    rng = np.random.default_rng(SEED)
    _, ci = np.unique(cl, return_inverse=True)
    grp = [np.flatnonzero(ci == k) for k in range(ci.max() + 1)]
    bs = []
    for _ in range(ITERS):
        pick = np.concatenate([grp[k] for k in rng.integers(0, len(grp), len(grp))])
        bs.append(mh_rate(e[pick], y[pick], pt[pick], st[pick]))
    bs = np.array(bs)
    fin = bs[np.isfinite(bs) & (bs > 0)]
    lo, hi = float(np.quantile(fin, ALPHA / 2)), float(np.quantile(fin, 1 - ALPHA / 2))
    eh, el = int((y * e).sum()), int((y * (1 - e)).sum())
    if eh < MIN_EV or el < MIN_EV:
        v = "not evaluable (< 15 first-CVE events on a side)"
    else:
        v = "SUPPORTED (replicates DC-H1)" if rr > 1 and lo > 1 else "not supported"
    # inverse-variance pooling with DC-2 (99.5% CI from its report) -- descriptive
    se_r = float(np.std(np.log(fin)))
    se_dc = (np.log(1.89) - np.log(1.08)) / (2 * 2.807)
    w1, w2 = 1 / se_dc ** 2, 1 / se_r ** 2 if se_r > 0 else 0
    pooled = float(np.exp((w1 * np.log(1.45) + w2 * np.log(rr)) / (w1 + w2))) if np.isfinite(rr) and rr > 0 else float("nan")
    L = ["# DCR-H1 — danger comments at birth, replicated on unseen repos (SCORED)", "",
         "- per repo (quarterly snapshots, security-fix commits, commented births): " + ", ".join(f"{r} {v_[0]}/{v_[1]}/{v_[2]:,}" for r, v_ in per_repo.items()),
         f"- commented births {len(U):,}; danger-commented {int(e.sum()):,} ({e.mean():.0%})", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **DCR-H1** danger-commented vs plain-commented → first CVE fix rate | rate ratio **{rr:.2f}** [{lo:.2f}, {hi:.2f}] (99%); first-CVE events {eh} / {el} | **{v}** |",
         "", f"- descriptive inverse-variance pooled with DC-2 (1.45): **{pooled:.2f}**"]
    for r in REPOS:
        m = np.array([u[0] == r for u in U])
        if m.sum():
            L.append(f"- {r}: rate ratio {mh_rate(e[m], y[m], pt[m], st[m]):.2f} (events {int((y[m] * e[m]).sum())} / {int((y[m] * (1 - e[m])).sum())})")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "dcr.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
