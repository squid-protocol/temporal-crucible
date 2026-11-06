#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""VZ-H1..H3: vendored zlib copies (docs/vz_hypotheses.md). Public report = aggregates; per-host detail is private.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <engine venv>/bin/python tools/vz_eval.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ut_eval as U  # noqa: E402  (SFS_SRC on sys.path)
from lay_eval import K_RRF, all_ranks, jac, pess_rank, skeleton, toks  # noqa: E402
from vz_scan import FIXES, HOSTS, OUT  # noqa: E402
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

ZLIB = POOL_DIR / "zlib"
RELEASE = {"eff308af4": (1, 2, 13), "1eb7682f8": (1, 2, 13), "5c44459c3": (1, 2, 12), "6a043145c": (1, 2, 9),
           "9aaec95e8": (1, 2, 9), "e54e12994": (1, 2, 9), "d1d577490": (1, 2, 9)}
CVE = {"eff308af4": "CVE-2022-37434", "1eb7682f8": "CVE-2022-37434", "5c44459c3": "CVE-2018-25032", "6a043145c": "CVE-2016-9840",
       "9aaec95e8": "CVE-2016-9841", "e54e12994": "CVE-2016-9842", "d1d577490": "CVE-2016-9843"}
PRIVATE = POOL_DIR / "vz_private" / "vz_host_status.json"
SEED, ITERS, ALPHA = 2982, 5000, 0.01 / 3
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?")


MACROISH = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def engine_spans(db):
    """{path: [(start, end, name)]}: engine function starts; end = next start - 1 (or EOF)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    by = defaultdict(list)
    for p, n, st in con.execute("SELECT fd.file_path, f.func_name, f.start_line FROM function_data f JOIN file_data fd ON f.file_id = fd.id"):
        if st:
            by[p].append((int(st), str(n)))
    con.close()
    out = {}
    for p, v in by.items():
        v.sort()
        out[p] = [(a, (v[i + 1][0] - 1) if i + 1 < len(v) else 10 ** 9, n) for i, (a, n) in enumerate(v)]
    return out


def text_span(src: bytes, a, b):
    return "\n".join(src.decode("utf-8", "replace").splitlines()[a - 1:b])


def code_line(x):
    return U.nontrivial(x) and not x.startswith(("//", "/*", "*"))


def fix_functions(sha, espans):
    parent = U._git(ZLIB, "rev-parse", f"{sha}^").strip()
    hunks, cur, h = defaultdict(list), None, None
    for ln in U._git(ZLIB, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        m = U.FILE_HDR.match(ln)
        if m:
            cur = m.group(1) if m.group(1) and m.group(1).endswith(".c") else None
            continue
        if not cur:
            continue
        mh = HUNK.match(ln)
        if mh:
            h = {"s": max(int(mh.group(1)), 1), "R": [], "A": []}
            hunks[cur].append(h)
        elif h is not None and ln[:1] in "+-" and not ln.startswith(("+++", "---")):
            (h["R"] if ln[0] == "-" else h["A"]).append(U.norm(ln[1:]))
    out = {}
    for path, hs in hunks.items():
        psrc = U._git(ZLIB, "show", f"{parent}:{path}", text=False)
        fsrc = U._git(ZLIB, "show", f"{sha}:{path}", text=False)
        pre = [x for x in U.spans(psrc, "c") if not MACROISH.match(x[2])]
        post = {nm: body for _a, _b, nm, body in U.spans(fsrc, "c")}
        for hh in hs:
            hit = next(((nm, body) for a, b, nm, body in pre if a <= hh["s"] <= b), None)
            if hit is None:  # pre-run clarification: engine-span fallback (preprocessor-split files)
                e = next(((nm, text_span(psrc, a, b)) for a, b, nm in espans.get(path, []) if a <= hh["s"] <= b), None)
                hit = e
            if hit is None:
                continue
            nm, body = hit
            pb = post.get(nm) or post_fallback(fsrc, nm, body)
            d = out.setdefault((path, nm), {"R": set(), "A": set(), "pre": body, "post": pb})
            d["R"].update(x for x in hh["R"] if code_line(x))
            d["A"].update(x for x in hh["A"] if code_line(x))
    return out


def post_fallback(fsrc: bytes, nm, pre_body):
    """Post-fix body when tree-sitter cannot see the function: the same-size window starting at its signature line."""
    lines = fsrc.decode("utf-8", "replace").splitlines()
    first = pre_body.splitlines()[0].strip() if pre_body else ""
    for i, ln in enumerate(lines):
        if first and ln.strip() == first:
            return "\n".join(lines[i:i + len(pre_body.splitlines()) + 5])
    return ""


def status(body, R, A):
    lines = {U.norm(x) for x in body.splitlines()}
    fa = sum(x in lines for x in A) / len(A) if A else 0.0
    fr = sum(x in lines for x in R) / len(R) if R else 0.0
    if A and fa >= 0.5:
        return "patched"
    if R and fr >= 0.5:
        return "unpatched-looking"
    return "addition-only/unclear" if not R else "diverged"


def version(root):
    for p in sorted(root.rglob("zlib.h")) + sorted(root.rglob("zlib*.h")):
        m = re.search(r'define ZLIB_VERSION "([0-9.]+)', p.read_text(errors="replace"))
        if m:
            return tuple(int(x) for x in m.group(1).strip(".").split(".") if x)
    return None


class Table:
    """One scan: sfs vectors, engine calls, tree-sitter bodies (start-line aligned)."""

    def __init__(self, name, ref):
        dest = OUT / name
        db = dest / f"{name}_galaxy_master.db"
        self.root = dest / name
        self.ft = U.build(U.load_scan(db, ref.signal_columns, name=name), ref, min_loc=3).functions
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        meta = {}
        for p, n, s, c in con.execute("SELECT fd.file_path, f.func_name, f.start_line, f.calls_out_to FROM function_data f "
                                      "JOIN file_data fd ON f.file_id = fd.id"):
            try:
                calls = {str(x).lower() for x in json.loads(c)} if c else set()
            except ValueError:
                calls = set()
            meta.setdefault((p, str(n)), (s or 0, calls))
        con.close()
        self.espans = engine_spans(db)
        self.db = db
        self.cand = np.flatnonzero(self.ft.loc >= 6)
        self._spans = {}
        self.body, self.calls, self.names = [], [], []
        for i in self.cand:
            p, n = str(self.ft.path[i]), str(self.ft.name[i])
            s, calls = meta.get((p, n), (0, set()))
            self.body.append(self._body(p, n, s))
            self.calls.append(calls - {U.short(n)})
            self.names.append(U.short(n))
        self.sk = [skeleton(b, U.lang_of(str(self.ft.path[i]))) if b else set() for b, i in zip(self.body, self.cand)]
        self.tk = [toks(b, n) if b else set() for b, n in zip(self.body, self.names)]

    def _body(self, path, name, start):
        if path not in self._spans:
            f = self.root / path
            if not f.exists():
                hits = list(self.root.rglob(pathlib.Path(path).name))
                f = hits[0] if hits else None
            self._spans[path] = U.spans(f.read_bytes(), U.lang_of(path)) if f else []
        best = None
        for a, _b, nm, body in self._spans[path]:
            if a == start or (best is None and U.short(nm) == U.short(name)):
                best = body
                if a == start:
                    break
        if not best and start:  # engine-span fallback (pre-run clarification)
            sp = next(((a, b) for a, b, n in self.espans.get(path, []) if a == start), None)
            f = self.root / path
            if sp and f.exists():
                best = text_span(f.read_bytes(), *sp)
        return best or ""


def main() -> int:
    t0 = time.time()
    ref = U.load_reference("structure")
    hosts = {n: Table(n, ref) for n in HOSTS if (OUT / n / f"{n}_galaxy_master.db").exists()}
    vers = {n: version(OUT / n / n) for n in hosts}
    print({n: (len(t.cand), vers[n]) for n, t in hosts.items()}, f"({time.time() - t0:.0f}s)", flush=True)
    rows, priv = [], []
    for f in FIXES:
        q = Table(f"zlib@{f[:9]}^", ref)
        qkey = {}
        for k, i in enumerate(q.cand):
            qkey.setdefault((str(q.ft.path[i]), U.short(q.ft.name[i])), k)
        for (path, nm), d in fix_functions(f, q.espans).items():
            k = qkey.get((path, U.short(nm)))
            if k is None:
                continue
            qi = q.cand[k]
            qc, qsk = q.calls[k], skeleton(d["pre"], "c")
            qtk = toks(d["pre"], U.short(nm))
            for hn, t in hosts.items():
                jt = np.array([max(U.jacc(d["pre"], b), U.jacc(d["post"], b)) if b else 0.0 for b in t.body])
                ti = int(np.argmax(jt))
                if jt[ti] < 0.5:
                    continue
                s1 = -np.linalg.norm(t.ft.vectors[t.cand] - q.ft.vectors[qi], axis=1)
                s2 = np.array([jac(qc, c) for c in t.calls])
                s3 = np.array([jac(qsk, s) for s in t.sk])
                st = np.array([jac(qtk, s) for s in t.tk])
                sn = np.array([1.0 if n == U.short(nm) else 0.0 for n in t.names])
                fused = sum(1.0 / (K_RRF + all_ranks(s)) for s in (s1, s2, s3))
                stt = status(t.body[ti], d["R"], d["A"])
                v = vers[hn]
                exp = None if v is None else ("patched" if v >= RELEASE[f[:9]] else "unpatched-looking")
                renamed = t.names[ti] != U.short(nm)
                rows.append({"host": hn, "fix": f[:9], "renamed": renamed, "status": stt, "expected": exp,
                             **{m: pess_rank(s, ti) for m, s in (("L1", s1), ("L2", s2), ("L3", s3), ("FUSED", fused), ("NAME", sn), ("TOKEN", st))}})
                priv.append({"host": hn, "cve": CVE[f[:9]], "fix": f[:9], "function": nm, "host_function": t.names[ti],
                             "jaccard": float(jt[ti]), "status": stt, "host_version": v, "expected": exp})
        print(f"fix {f[:9]}: rows {len(rows)} ({time.time() - t0:.0f}s)", flush=True)
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE.write_text(json.dumps({"note": "PRIVATE per-host CVE status; do not publish (docs/vz_hypotheses.md)", "rows": priv}, indent=1))
    # ---------------------------------------------------------------- scoring
    from scipy.stats import norm as N
    H = np.array([r["host"] for r in rows])
    uh = sorted(set(H))
    rng = np.random.default_rng(SEED)

    def cluster_lo(x, mask):
        hs = [h for h in uh if (mask & (H == h)).any()]
        by = {h: x[mask & (H == h)] for h in hs}
        b = []
        for _ in range(ITERS):
            pick = rng.choice(hs, size=len(hs), replace=True)
            v = np.concatenate([by[h] for h in pick])
            b.append(v.mean())
        return float(np.quantile(b, ALPHA))
    rk = {m: np.array([r[m] for r in rows]) for m in ("L1", "L2", "L3", "FUSED", "NAME", "TOKEN")}
    ren = np.array([r["renamed"] for r in rows])
    allm = np.ones(len(rows), bool)
    L = ["# VZ-H1..H3 — vendored zlib (SCORED; aggregates only)", "",
         f"- hosts scanned: {len(hosts)}; truth pairs (query function × host, text Jaccard ≥ 0.5): **{len(rows)}**; renamed: {int(ren.sum())}",
         "", "| claim | result | lo | verdict |", "|---|---|---:|---|"]
    x1 = (rk["FUSED"] <= 1).astype(float) - (rk["L1"] <= 1).astype(float)
    lo1 = cluster_lo(x1, allm) if len(rows) else float("nan")
    v1 = "not evaluable" if len(rows) < 30 else ("SUPPORTED" if x1.mean() > 0 and lo1 > 0 else "not supported")
    L.append(f"| **VZ-H1** recall@1 FUSED − L1 | {x1.mean():+.1%} (n {len(rows)}) | {lo1:+.1%} | **{v1}** |")
    x2 = (rk["FUSED"] <= 10).astype(float) - (rk["NAME"] <= 10).astype(float)
    if ren.sum() >= 15:
        lo2 = cluster_lo(x2, ren)
        v2 = "SUPPORTED" if x2[ren].mean() > 0 and lo2 > 0 else "not supported"
        L.append(f"| **VZ-H2** renamed: recall@10 FUSED − NAME | {x2[ren].mean():+.1%} (n {int(ren.sum())}) | {lo2:+.1%} | **{v2}** |")
    else:
        L.append(f"| **VZ-H2** renamed: recall@10 FUSED − NAME | n {int(ren.sum())} renamed pairs | — | **not evaluable** (< 15) |")
    ev3 = [r for r in rows if r["status"] in ("patched", "unpatched-looking") and r["expected"]]
    k3 = sum(r["status"] == r["expected"] for r in ev3)
    n3 = len(ev3)
    z = N.ppf(1 - 0.01 / 2)
    p3 = k3 / n3 if n3 else float("nan")
    w3 = (p3 + z * z / (2 * n3) - z * np.sqrt(p3 * (1 - p3) / n3 + z * z / (4 * n3 * n3))) / (1 + z * z / n3) if n3 else float("nan")
    v3 = "not evaluable" if n3 < 30 else ("SUPPORTED" if p3 >= 0.8 and w3 >= 0.6 else "not supported")
    L.append(f"| **VZ-H3** patch check agrees with host version | {k3}/{n3} = {p3:.1%} | Wilson {w3:.1%} | **{v3}** |")
    dis = Counter(f"status {r['status']} vs version-expected {r['expected']}" for r in ev3 if r["status"] != r["expected"])
    L += ["", "## Descriptive", "",
          "| subset | n | " + " | ".join(f"{m} @1 / @10" for m in rk) + " |", "|---|---:|" + "---:|" * len(rk)]
    for lab, m in (("all", allm), ("renamed", ren), ("same name", ~ren)):
        if m.sum():
            L.append(f"| {lab} | {int(m.sum())} | " + " | ".join(f"{(rk[k][m] <= 1).mean():.0%} / {(rk[k][m] <= 10).mean():.0%}" for k in rk) + " |")
    L += ["", f"- status mix (all pairs): {dict(Counter(r['status'] for r in rows))}",
          f"- H3 disagreements by kind (counts only): {dict(dis)}",
          f"- hosts with ≥ 1 truth pair: {len(set(H))} of {len(hosts)}",
          "", f"Runtime {time.time() - t0:.0f}s · seed {SEED} · host-cluster bootstrap · per-host detail is private."]
    (DOCS_DIR / "vz.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
