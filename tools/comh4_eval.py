#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""COM-H4a..H4b (docs/com_hypotheses.md): comment drift vs CVE fixes. Engine venv.

A function-quarter is at risk when the function has a header comment block at every snapshot of the
8-interval window it was alive in and its code-only body changed in >= 2 of those intervals.
Drifted = the header text never changed in the window; maintained = it changed at least once.
MH rate ratio of CVE-fix (`latent`) quarters, strata repo x log10 loc (0.1 decade) x body-change
count (2, 3, 4, >= 5) x file had a CVE fix before the quarter; file-cluster bootstrap.

    <engine venv>/bin/python tools/comh4_eval.py [--audit <out.md>]

Reads the quarterly function lives (ints_eval.lives, the DBs in nh_eval.DBS) and the clone pool.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import multiprocessing
import pathlib
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, _fname, _git, _parser, fix_events, map_fix  # noqa: E402
from dc_eval import prism  # noqa: E402
from ints_eval import CLS, ITERS, REPOS, SEED, YEAR, lives, mh_rate  # noqa: E402
from nh_eval import DBS  # noqa: E402

ALPHA = 0.01 / 2
WINDOW = 8
NULL_BAND = (0.80, 1.25)
MIN_EVENTS = 20
_WS = re.compile(r"\s+")
_WORD = re.compile(r"\w+")


def _lang(r, path):
    return "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"


def file_task(t):
    """(repo, blob, path) -> {name: (header_text | None, body_hash, span_lines)} for every function_definition."""
    r, blob, path = t
    raw = _git(POOL_DIR / r, "cat-file", "blob", blob, text=False)
    if not raw:
        return blob, path, {}
    lang = _lang(r, path)
    txt = raw.decode("utf-8", "replace")
    try:
        pos = prism().split_positional_comment_stream(txt, lang).split("\n")
        code = prism().split_streams(txt, lang)["code_stream"].split("\n")
    except Exception:
        return blob, path, {}
    lines = txt.split("\n")
    out = {}
    stack = [_parser(lang).parse(raw).root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm and nm not in out:
                a, b = n.start_point[0], n.end_point[0]
                body = _WS.sub(" ", " ".join(code[a:b + 1])).strip()
                # DC's "directly above" block: engine comment lines above the first line, at most one blank between
                idx, i, blank = [], a - 1, 0
                while i >= 0:
                    if i < len(pos) and pos[i].strip():
                        idx.append(i)
                        blank = 0
                    elif i < len(lines) and not lines[i].strip() and blank == 0:
                        blank = 1
                    else:
                        break
                    i -= 1
                head = _WS.sub(" ", " ".join(pos[j] for j in sorted(idx))).strip()
                out[nm] = (head if len(_WORD.findall(head)) >= 2 else None,
                           hashlib.blake2b(body.encode(), digest_size=12).digest(), b - a + 1)
            continue
        stack.extend(n.children)
    return blob, path, out


def loc_at(r, snaps):
    """(path, name) -> engine loc per snapshot, with lives()'s own tie-break (lowest start_line)."""
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    per = []
    for s in snaps:
        rows = con.execute("SELECT fd.file_path, f.func_name, f.start_line, f.loc FROM function_data f JOIN file_data fd "
                           "ON f.file_id = fd.id WHERE fd.commit_hash = ? AND fd.language IN ('c','cpp') "
                           "AND f.func_name IS NOT NULL AND f.func_name != ''", (s["sha"],)).fetchall()
        d = {}
        for row in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):
            d.setdefault((row[0], row[1]), row[3] or 0)
        per.append(d)
    con.close()
    return per


def blobs_at(r, sha):
    out = {}
    for ln in _git(POOL_DIR / r, "ls-tree", "-r", sha).splitlines():
        meta, _, path = ln.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            out[path] = parts[2]
    return out


def function_states(r, snaps, ids_at):
    """fid -> {k: (header | None, body_hash)} for every snapshot the function is alive at."""
    paths_at = [{p for (p, _n) in ids} for ids in ids_at]
    blob_at = [blobs_at(r, s["sha"]) for s in snaps]
    todo = {(blob_at[k][p], p) for k in range(len(snaps)) for p in paths_at[k] if p in blob_at[k]}
    parsed = {}
    with multiprocessing.get_context("fork").Pool(8) as pool:
        for blob, path, out in pool.imap_unordered(file_task, [(r, b, p) for b, p in todo], chunksize=16):
            parsed[(blob, path)] = out
    st = defaultdict(dict)
    for k, ids in enumerate(ids_at):
        for (p, nm), fid in ids.items():
            got = parsed.get((blob_at[k].get(p), p), {})
            v = got.get(nm) or got.get(nm.split("::")[-1])
            if v is not None:
                st[fid][k] = (v[0], v[1])
    return st, blob_at


def classify(states, k):
    """Exposure at snapshot k: ('drifted' | 'maintained' | 'noheader' | None, body-change count)."""
    ks = [j for j in range(k - WINDOW, k + 1) if j in states]
    if k not in states or len(ks) < 2:
        return None, 0
    heads = [states[j][0] for j in ks]
    bc = hc = 0
    for j in range(k - WINDOW + 1, k + 1):
        if j in states and j - 1 in states:
            bc += states[j][1] != states[j - 1][1]
            hc += states[j][0] != states[j - 1][0]
    if bc < 2:
        return None, bc
    if all(h is not None for h in heads):
        return ("maintained" if hc else "drifted"), bc
    if all(h is None for h in heads):
        return "noheader", bc
    return None, bc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", help="write a 30-case drifted/maintained audit sheet here (not committed)")
    args = ap.parse_args()
    t0 = time.time()
    ev, last = [], {}
    for r in REPOS:
        e, last[r] = fix_events(r)
        ev += [x for x in e if x[3] in CLS]
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=8) for h in hs]
    print(f"hits {len(hits):,} ({time.time() - t0:.0f}s)", flush=True)
    U, audit_pool = [], []
    for r in REPOS:
        snaps, ids_at, info = lives(r)
        cts = [s["ct"] for s in snaps]
        locs = loc_at(r, snaps)
        fh, file_cve = defaultdict(list), defaultdict(list)
        for (_r, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            if klass == "latent":
                file_cve[path].append(ct)
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            fid = None
            for jj in (j, j + 1):
                if jj < len(ids_at) and fid is None:
                    for cand in ((path, nm), (path, nm.split("::")[-1])):
                        if cand in ids_at[jj]:
                            fid = ids_at[jj][cand]
                            break
            if fid is not None:
                fh[fid].append((ct, klass))
        for v in file_cve.values():
            v.sort()
        states, _blob_at = function_states(r, snaps, ids_at)
        print(f"{r}: {len(snaps)} snapshots, {len(states):,} functions with states ({time.time() - t0:.0f}s)", flush=True)
        n0 = len(U)
        for k in range(1, len(snaps)):
            start = cts[k]
            end = min(cts[k + 1] if k + 1 < len(cts) else float("inf"), last[r])
            if end <= start:
                continue
            for (path, nm), fid in ids_at[k].items():
                loc = locs[k].get((path, nm), 0)
                if loc < 3 or fid not in states:
                    continue
                grp, bc = classify(states[fid], k)
                if grp is None:
                    continue
                prior = bisect.bisect_left(file_cve.get(path, []), start) > 0
                got = {kl for ct, kl in fh.get(fid, ()) if start < ct <= end}
                U.append((r, path, int(np.floor(np.log10(loc) / 0.1)), min(bc, 5), prior, grp, (end - start) / YEAR, got))
                if grp in ("drifted", "maintained"):
                    audit_pool.append((r, path, nm, snaps[max(0, k - WINDOW)]["sha"], snaps[k]["sha"], grp))
        print(f"{r}: at-risk function-quarters {len(U) - n0:,} ({time.time() - t0:.0f}s)", flush=True)

    def arrays(a, b):
        UU = [u for u in U if u[5] in (a, b)]
        e = np.array([1.0 if u[5] == a else 0.0 for u in UU])
        st = np.array([f"{u[0]}|{u[2]}|{u[3]}|{u[4]}" for u in UU])
        cl = np.array([f"{u[0]}:{u[1]}" for u in UU])
        pt = np.array([u[6] for u in UU])
        evs = {k: np.array([1.0 if k in u[7] else 0.0 for u in UU]) for k in CLS}
        return UU, e, st, cl, pt, evs

    UU, e, st, cl, pt, EV = arrays("drifted", "maintained")
    rr = {k: mh_rate(e, EV[k], pt, st) for k in CLS}
    rng = np.random.default_rng(SEED)
    _, ci = np.unique(cl, return_inverse=True)
    grp = [np.flatnonzero(ci == k) for k in range(ci.max() + 1)]
    bl, br = [], []
    for _ in range(ITERS):
        pick = np.concatenate([grp[k] for k in rng.integers(0, len(grp), len(grp))])
        a_ = mh_rate(e[pick], EV["latent"][pick], pt[pick], st[pick])
        o_ = mh_rate(e[pick], EV["other-fix"][pick], pt[pick], st[pick])
        bl.append(a_)
        br.append(a_ / o_ if o_ > 0 else np.nan)
    lo1, hi1 = float(np.nanquantile(bl, ALPHA)), float(np.nanquantile(bl, 1 - ALPHA))
    lo99, hi99 = float(np.nanquantile(bl, 0.005)), float(np.nanquantile(bl, 0.995))
    lo2 = float(np.nanquantile(br, ALPHA))
    n_d, n_m = int((EV["latent"] * e).sum()), int((EV["latent"] * (1 - e)).sum())
    n_od, n_om = int((EV["other-fix"] * e).sum()), int((EV["other-fix"] * (1 - e)).sum())
    if min(n_d, n_m) < MIN_EVENTS:
        v1 = f"underpowered (< {MIN_EVENTS} CVE-fix events in a group)"
    elif rr["latent"] > 1 and lo1 > 1:
        v1 = "SUPPORTED"
    elif rr["latent"] < 1 and hi1 < 1:
        v1 = "reversed: drifted functions get fewer CVE fixes"
    elif NULL_BAND[0] < lo99 and hi99 < NULL_BAND[1]:
        v1 = "not supported: replicated null"
    else:
        v1 = "not supported: inconclusive"
    ratio = rr["latent"] / rr["other-fix"] if rr["other-fix"] > 0 else float("nan")
    if min(n_d, n_m) < MIN_EVENTS:
        v2 = "underpowered"
    else:
        v2 = "SUPPORTED" if ratio > 1 and lo2 > 1 else "not supported"

    L = ["# COM-H4 (COM-H4a..H4b) — comment drift vs CVE fixes (SCORED)", "",
         f"- at-risk function-quarters {len(U):,}: drifted {sum(u[5] == 'drifted' for u in U):,}, "
         f"maintained {sum(u[5] == 'maintained' for u in U):,}, no header {sum(u[5] == 'noheader' for u in U):,}",
         f"- registration `docs/com_hypotheses.md`; window {WINDOW} quarters; α = {ALPHA}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **COM-H4a** drifted vs maintained → CVE-fix rate | rate ratio **{rr['latent']:.2f}** [{lo1:.2f}, {hi1:.2f}] "
         f"(99% [{lo99:.2f}, {hi99:.2f}]); CVE-fix quarters {n_d} / {n_m} | **{v1}** |",
         f"| **COM-H4b** CVE-specific (÷ other-fix rate ratio) | **{ratio:.2f}** (lo {lo2:.2f}); other-fix {rr['other-fix']:.2f} "
         f"({n_od} / {n_om}) | **{v2}** |",
         "", "## Descriptive (no verdicts)", "",
         f"- regression {rr['regression']:.2f}; extrinsic {rr['extrinsic']:.2f}"]
    _, e3, st3, _, pt3, EV3 = arrays("noheader", "maintained")
    if e3.size:
        L.append(f"- no header vs maintained (equally edited): CVE rate ratio {mh_rate(e3, EV3['latent'], pt3, st3):.2f} "
                 f"(events {int((EV3['latent'] * e3).sum())} / {int((EV3['latent'] * (1 - e3)).sum())})")
    for r in REPOS:
        mm = np.array([u[0] == r for u in UU])
        if mm.sum():
            share = float(e[mm].mean())
            L.append(f"- {r}: drifted share of headed at-risk quarters {share:.0%}; CVE rate ratio "
                     f"{mh_rate(e[mm], EV['latent'][mm], pt[mm], st[mm]):.2f} "
                     f"(events {int((EV['latent'][mm] * e[mm]).sum())} / {int((EV['latent'][mm] * (1 - e[mm])).sum())})")
    bcs = Counter((u[3], u[5]) for u in UU)
    L.append("- body-change count × group: " + ", ".join(
        f"{b}{'+' if b == 5 else ''}: {bcs[(b, 'drifted')]:,} / {bcs[(b, 'maintained')]:,}" for b in range(2, 6)))
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · file-cluster bootstrap {ITERS}."]
    (DOCS_DIR / "com_h4.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    if args.audit:
        rs = np.random.default_rng(SEED)
        pick = [audit_pool[i] for i in rs.choice(len(audit_pool), size=min(30, len(audit_pool)), replace=False)]
        A = ["# COM-H4 instrument audit (30 random drifted / maintained calls)", ""]
        for (r, path, nm, lo, hi, g) in pick:
            A += [f"## {r} `{path}` `{nm}` @ {hi[:10]} — called **{g}**", "",
                  f"`git -C <pool>/{r} diff {lo[:10]} {hi[:10]} -- {path}` (window start → k)", ""]
        pathlib.Path(args.audit).write_text("\n".join(A) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
