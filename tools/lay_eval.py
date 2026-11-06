#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAY-H1..H3: layered fingerprint (L1 sfs, L2 call set, L3 control-flow skeleton) on UT's OpenSSL->fork copies
(docs/lay_hypotheses.md). Aggregates only.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <engine venv>/bin/python tools/lay_eval.py --scratch <dir>
"""
from __future__ import annotations

import argparse
import bisect
import json
import pathlib
import sqlite3
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ut_eval as U  # noqa: E402  (sets up SFS_SRC on sys.path)
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402

CF = {"if_statement", "else_clause", "for_statement", "while_statement", "do_statement", "switch_statement", "case_statement",
      "return_statement", "goto_statement", "break_statement", "continue_statement", "compound_statement"}
SEED, ITERS, ALPHA, K_RRF = 2982, 5000, 0.01 / 3, 60


def skeleton(body, lang):
    tree = U._parser(lang).parse(body.encode("utf-8", "replace"))
    seq = []

    def walk(n, depth):
        if n.type in CF:
            seq.append(f"{n.type}@{min(depth, 6)}")
            depth += 1
        for c in n.children:
            walk(c, depth)
    walk(tree.root_node, 0)
    return {tuple(seq[i:i + 3]) for i in range(max(len(seq) - 2, 0))} or ({tuple(seq)} if seq else set())


def jac(a, b):
    return len(a & b) / len(a | b) if (a or b) else 0.0


def toks(body, own):
    return set(U.TOK.findall(body)) - {own}


def db_calls(db, sha=None):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    q = "SELECT fd.file_path, f.func_name, f.calls_out_to FROM function_data f JOIN file_data fd ON f.file_id = fd.id"
    rows = con.execute(q + (" WHERE fd.commit_hash = ?" if sha else ""), ((sha,) if sha else ())).fetchall()
    con.close()
    out = {}
    for p, n, c in rows:
        try:
            s = {str(x).lower() for x in json.loads(c)} if c else set()
        except ValueError:
            s = set()
        out.setdefault((p, str(n)), s)
    return out


def pess_rank(scores, i):
    return int((scores >= scores[i]).sum())


def all_ranks(scores):
    order = np.sort(scores)
    return len(scores) - np.searchsorted(order, scores, side="left")  # count of scores >= each score


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    ref = U.load_reference("structure")
    forks = {}
    for n in U.FORKS:
        fk = U.Fork(n, ref)
        cand = np.flatnonzero(fk.ft.loc >= 6)
        calls = db_calls(POOL_DIR / "ut_forks" / n / f"{n}_galaxy_master.db")
        C2, SK, TK = [], [], []
        for i in cand:
            p, nm = str(fk.ft.path[i]), str(fk.ft.name[i])
            body = fk.body(i) or ""
            own = U.short(nm)
            C2.append(calls.get((p, nm), set()) - {own})
            SK.append(skeleton(body, U.lang_of(p)) if body else set())
            TK.append(toks(body, nm.split("::")[-1]) if body else set())
        forks[n] = (fk, cand, C2, SK, TK)
        print(f"{n}: {len(cand):,} candidates ({time.time() - t0:.0f}s)", flush=True)
    ev = [e for e in json.loads((REPO_ROOT / "events" / "openssl_xc.json").read_text())["events"]
          if e["class"] == "latent" and e["ct"] >= U.FORK_START]
    snaps = U.snapshots("openssl")
    cts = [s["ct"] for s in snaps]
    by_snap = defaultdict(list)
    for e in ev:
        j = bisect.bisect_left(cts, e["ct"]) - 1
        if j >= 0:
            by_snap[j].append(e)
    seen, R = set(), []
    for j in sorted(by_snap):
        db = U.export("openssl", snaps[j]["sha"], a.scratch / f"openssl_{snaps[j]['sha'][:12]}")
        q = U.build(U.load_scan(db, ref.signal_columns, name=f"openssl@{snaps[j]['sha'][:9]}"), ref, min_loc=3).functions
        q = U.subset(q, np.array([str(p).startswith(U.QUERY_PREFIX) for p in q.path]))
        qcalls = db_calls(db)
        qidx = {}
        for i, (p, n) in enumerate(zip(q.path, q.name)):
            qidx.setdefault((str(p), str(n)), i)
            qidx.setdefault((str(p), U.short(n)), i)
        for e in by_snap[j]:
            _parent, funcs = U.fix_functions(e["sha"])
            for (path, nm), d in funcs.items():
                qi = qidx.get((path, nm), qidx.get((path, U.short(nm))))
                if qi is None:
                    continue
                for fn, (fk, cand, C2, SK, TK) in forks.items():
                    if (path, nm, fn) in seen:
                        continue
                    best = None
                    for ti in fk.by_name.get(U.short(nm), []):
                        tb = fk.body(ti)
                        if tb:
                            jj = U.jacc(d["body"], tb)
                            if best is None or jj > best[0]:
                                best = (jj, ti)
                    if not best or best[0] < 0.5:
                        continue
                    pos = np.flatnonzero(cand == best[1])
                    if len(pos) == 0:
                        continue  # truth shorter than 6 lines
                    seen.add((path, nm, fn))
                    t = int(pos[0])
                    own = U.short(nm)
                    qc = qcalls.get((str(q.path[qi]), str(q.name[qi])), set()) - {own}
                    qs = U.lang_of(path)
                    qsk = skeleton(d["body"], qs)
                    qtk = toks(d["body"], nm.split("::")[-1])
                    s1 = -np.linalg.norm(fk.ft.vectors[cand] - q.vectors[qi], axis=1)
                    s2 = np.array([jac(qc, c) for c in C2])
                    s3 = np.array([jac(qsk, s) for s in SK])
                    st = np.array([jac(qtk, s) for s in TK])
                    fused = sum(1.0 / (K_RRF + all_ranks(s)) for s in (s1, s2, s3))
                    R.append({"fork": fn, **{m: pess_rank(s, t) for m, s in
                                             (("L1", s1), ("L2", s2), ("L3", s3), ("FUSED", fused), ("TOKEN", st))}})
        print(f"snapshot {j}: queries {len(R)} ({time.time() - t0:.0f}s)", flush=True)
    M = ("L1", "L2", "L3", "FUSED", "TOKEN")
    rk = {m: np.array([r[m] for r in R]) for m in M}
    bs = np.array([r["fork"] == "boringssl" for r in R])
    rng = np.random.default_rng(SEED)

    def paired(m1, m0, k, mask):
        x = (rk[m1][mask] <= k).astype(float) - (rk[m0][mask] <= k).astype(float)
        if len(x) == 0:
            return float("nan"), float("nan"), 0
        b = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(ITERS)]
        return float(x.mean()), float(np.quantile(b, ALPHA)), len(x)
    allm = np.ones(len(R), bool)
    L = ["# LAY-H1..H3 — layered fingerprint vs the coarse one on OpenSSL→fork copies (SCORED; aggregates only)", "",
         f"- queries with a name-identified copy (≥ 6 lines): **{len(R)}** (LibreSSL {int((~bs).sum())}, BoringSSL {int(bs.sum())})", "",
         "| claim | comparison | n | difference | lo (α 0.01/3) | verdict |", "|---|---|---:|---:|---:|---|"]
    for cid, m1, k, mask, need in (("LAY-H1", "L2", 1, allm, 30), ("LAY-H2", "FUSED", 1, allm, 30), ("LAY-H3", "FUSED", 10, bs, 15)):
        d_, lo, n = paired(m1, "L1", k, mask)
        v = "not evaluable" if n < need else ("SUPPORTED" if d_ > 0 and lo > 0 else "not supported")
        L.append(f"| **{cid}** | recall@{k} {m1} − L1{' (BoringSSL)' if mask is bs else ''} | {n} | {d_:+.1%} | {lo:+.1%} | **{v}** |")
    L += ["", "## Recall by method (descriptive; TOKEN is a near-circular reference ceiling)", "",
          "| subset | n | " + " | ".join(f"{m} @1 / @10" for m in M) + " |", "|---|---:|" + "---:|" * len(M)]
    for lab, mask in (("all", allm), ("LibreSSL", ~bs), ("BoringSSL", bs)):
        if mask.sum():
            L.append(f"| {lab} | {int(mask.sum())} | " + " | ".join(f"{(rk[m][mask] <= 1).mean():.0%} / {(rk[m][mask] <= 10).mean():.0%}" for m in M) + " |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · pessimistic tie ranks · RRF k = {K_RRF}."]
    (DOCS_DIR / "lay.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
