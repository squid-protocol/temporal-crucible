#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""UT-H1..H3: unpatched twins of OpenSSL CVE-fixed functions in BoringSSL / LibreSSL (docs/ut_hypotheses.md).
Public report = aggregates only; audit candidates go to a private file outside the repo.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <engine venv>/bin/python tools/ut_eval.py --scratch <dir>
"""
from __future__ import annotations

import argparse
import bisect
import dataclasses
import json
import os
import pathlib
import random
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.environ["SFS_SRC"])
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from structural_fingerprint.fingerprint import build  # noqa: E402
from structural_fingerprint.reference import load_reference  # noqa: E402
from structural_fingerprint.scan_io import load_scan  # noqa: E402
from structural_fingerprint.twins import TwinParams, accept, search  # noqa: E402

from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from chg_eval import CEXT, CPPEXT, FILE_HDR, _fname, _git, _parser  # noqa: E402
from nh_eval import snapshots  # noqa: E402
from sfs_eval import export  # noqa: E402

FORK_START = 1403222400  # 2014-06-20 00:00 UTC (BoringSSL's first commit)
FORKS = {"boringssl": (POOL_DIR / "boringssl", "e375adcf13f841eabd872e2e7c6030aab6be3117"),
         "libressl": (POOL_DIR / "openbsd", "a22aeee114ad90a9145672868d02197bfd76a96f")}
QUERY_PREFIX = ("crypto/", "ssl/", "include/")
PRIVATE = POOL_DIR / "ut_private" / "ut_audit_candidates.json"
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")
TOK = re.compile(r"[A-Za-z_]\w*|\d+|[^\s\w]")
SEED, AUDIT_CAP = 2982, 25


def norm(line):
    return " ".join(line.split())


def nontrivial(line):
    return len(line) >= 10 and re.search(r"[A-Za-z]", line) is not None


def spans(src: bytes, lang: str):
    tree = _parser(lang).parse(src)
    out, stack = [], [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm:
                out.append((n.start_point[0] + 1, n.end_point[0] + 1, nm, n.text.decode("utf-8", "replace")))
        stack.extend(n.children)
    return out


def lang_of(path):
    return "c" if path.endswith(CEXT) else "cpp"


def fix_functions(sha):
    """{(path, name): {'R': set, 'A': set, 'body': pre-fix text}} for one OpenSSL fix commit."""
    repo = POOL_DIR / "openssl"
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return parent, {}
    hunks = defaultdict(list)
    cur, h = None, None
    for ln in _git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        m = FILE_HDR.match(ln)
        if m:
            cur = m.group(1) if m.group(1) and m.group(1).endswith(CEXT + CPPEXT) else None
            continue
        if not cur:
            continue
        mh = HUNK.match(ln)
        if mh:
            h = {"s": max(int(mh.group(1)), 1), "R": [], "A": []}
            hunks[cur].append(h)
        elif h is not None and ln[:1] in "+-" and not ln.startswith(("+++", "---")):
            (h["R"] if ln[0] == "-" else h["A"]).append(norm(ln[1:]))
    out = {}
    for path, hs in hunks.items():
        src = _git(repo, "show", f"{parent}:{path}", text=False)
        if not src:
            continue
        sp = spans(src, lang_of(path))
        for hh in hs:
            for a, b, nm, body in sp:
                if a <= hh["s"] <= b:
                    d = out.setdefault((path, nm), {"R": set(), "A": set(), "body": body})
                    d["R"].update(x for x in hh["R"] if nontrivial(x))
                    d["A"].update(x for x in hh["A"] if nontrivial(x))
                    break
    return parent, out


def jacc(a, b):
    ta, tb = set(TOK.findall(a)), set(TOK.findall(b))
    return len(ta & tb) / max(len(ta | tb), 1)


def status(body, R, A):
    lines = {norm(x) for x in body.splitlines()}
    fa = sum(x in lines for x in A) / len(A) if A else 0.0
    fr = sum(x in lines for x in R) / len(R) if R else 0.0
    if A and fa >= 0.5:
        return "patched"
    if R and fr >= 0.5:
        return "unpatched-looking"
    if not R and A:
        return "fix absent (addition-only)"
    return "diverged"


def subset(ft, mask):
    kw = {}
    for f in dataclasses.fields(ft):
        v = getattr(ft, f.name)
        kw[f.name] = v[mask] if isinstance(v, np.ndarray) and f.name != "edges" else (None if f.name == "edges" else v)
    return type(ft)(**kw)


def short(n):
    return str(n).split("::")[-1].strip().lower()


class Fork:
    def __init__(self, name, ref):
        self.name = name
        self.repo, self.sha = FORKS[name]
        db = POOL_DIR / "ut_forks" / name / f"{name}_galaxy_master.db"
        self.ft = build(load_scan(db, ref.signal_columns, name=name), ref, min_loc=3).functions
        self.by_name = defaultdict(list)
        for i, n in enumerate(self.ft.name):
            self.by_name[short(n)].append(i)
        self._src = {}
        self.root = "" if name == "boringssl" else ""

    def body(self, i):
        path, nm = str(self.ft.path[i]), str(self.ft.name[i])
        if path not in self._src:
            src = _git(self.repo, "show", f"{self.sha}:{path}", text=False)
            self._src[path] = spans(src, lang_of(path)) if src else []
        for _a, _b, n2, body in self._src[path]:
            if n2 == nm or short(n2) == short(nm):
                return body
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    ref = load_reference("structure")
    forks = {n: Fork(n, ref) for n in FORKS}
    print({n: len(f.ft.loc) for n, f in forks.items()}, flush=True)
    ev = [e for e in json.loads((REPO_ROOT / "events" / "openssl_xc.json").read_text())["events"]
          if e["class"] == "latent" and e["ct"] >= FORK_START]
    snaps = snapshots("openssl")
    cts = [s["ct"] for s in snaps]
    by_snap = defaultdict(list)
    for e in ev:
        j = bisect.bisect_left(cts, e["ct"]) - 1
        if j >= 0:
            by_snap[j].append(e)
    rows = []
    params = TwinParams()
    for j in sorted(by_snap):
        db = export("openssl", snaps[j]["sha"], a.scratch / f"openssl_{snaps[j]['sha'][:12]}")
        q = build(load_scan(db, ref.signal_columns, name=f"openssl@{snaps[j]['sha'][:9]}"), ref, min_loc=3).functions
        q = subset(q, np.array([str(p).startswith(QUERY_PREFIX) for p in q.path]))
        qidx = defaultdict(list)
        for i, (p, n) in enumerate(zip(q.path, q.name)):
            qidx[(str(p), str(n))].append(i)
            qidx[(str(p), short(n))].append(i)
        twin = {}
        for fn, fk in forks.items():
            res = accept(search(q, fk.ft, params))
            twin[fn] = dict(zip(res.q_index.tolist(), res.t_index.tolist()))
        for e in by_snap[j]:
            _parent, funcs = fix_functions(e["sha"])
            for (path, nm), d in funcs.items():
                qi = (qidx.get((path, nm)) or qidx.get((path, short(nm))) or [None])[0]
                for fn, fk in forks.items():
                    row = {"fix": e["sha"], "path": path, "name": nm, "fork": fn, "in_query": qi is not None,
                           "nR": len(d["R"]), "nA": len(d["A"])}
                    if qi is not None and qi in twin[fn]:
                        ti = twin[fn][qi]
                        tb = fk.body(ti)
                        row.update(twin=True, t_name=str(fk.ft.name[ti]), t_path=str(fk.ft.path[ti]),
                                   t_j=jacc(d["body"], tb) if tb else None,
                                   t_status=status(tb, d["R"], d["A"]) if tb else "no body",
                                   renamed=short(fk.ft.name[ti]) != short(nm))
                    else:
                        row["twin"] = False
                    best = None
                    for ti in fk.by_name.get(short(nm), []):
                        tb = fk.body(ti)
                        if tb:
                            jj = jacc(d["body"], tb)
                            if best is None or jj > best[0]:
                                best = (jj, ti, tb)
                    if best:
                        row.update(n_match=True, n_j=best[0], n_status=status(best[2], d["R"], d["A"]),
                                   n_same_as_twin=row.get("twin") and twin[fn].get(qi) == best[1])
                    else:
                        row["n_match"] = False
                    rows.append(row)
        print(f"snapshot {j} ({len(by_snap[j])} fixes) -> rows {len(rows)} ({time.time() - t0:.0f}s)", flush=True)
    # ------------------------------------------------------------------------------ scoring (aggregates only)
    from scipy.stats import norm as N
    def wilson(k, n, a=0.01):
        if n == 0:
            return float("nan")
        z = N.ppf(1 - a / 2)
        p = k / n
        return (p + z * z / (2 * n) - z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)
    tw = [r for r in rows if r.get("twin") and r.get("t_j") is not None]
    k1 = sum(r["t_j"] >= 0.5 for r in tw)
    p1, lo1 = (k1 / len(tw) if tw else float("nan")), wilson(k1, len(tw))
    v1 = "not evaluable" if len(tw) < 30 else ("SUPPORTED" if p1 >= 0.8 and lo1 >= 0.6 else "not supported")
    ren = [r for r in tw if r["t_j"] >= 0.5 and r["renamed"]]
    cand = [r for r in tw if r["t_j"] >= 0.5 and r["t_status"] == "unpatched-looking"]
    rnd = random.Random(SEED)
    audit = rnd.sample(cand, AUDIT_CAP) if len(cand) > AUDIT_CAP else cand
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE.write_text(json.dumps({"note": "PRIVATE: possible unpatched copies; do not publish (docs/ut_hypotheses.md disclosure rule)",
                                   "candidates": cand, "audit_sample": audit}, indent=1))
    nm_copies = [r for r in rows if r.get("n_match") and r["n_j"] >= 0.5]
    rec = sum(1 for r in nm_copies if r.get("twin") and r.get("n_same_as_twin")) / max(len(nm_copies), 1)
    L = ["# UT-H1..H3 — unpatched twins of OpenSSL CVE-fixed functions (SCORED; aggregates only)", "",
         f"- post-fork OpenSSL CVE fixes: {len(ev)}; (fix, function, fork) rows: {len(rows):,}; "
         f"function in pre-fix query snapshot: {sum(r['in_query'] for r in rows):,}",
         f"- fork function tables: " + ", ".join(f"{n} {len(f.ft.loc):,}" for n, f in forks.items()), "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **UT-H1** twins are real copies | {k1} / {len(tw)} accepted twins are textual copies (Jaccard ≥ 0.5) = **{p1:.1%}** (Wilson 99% lo {lo1:.1%}) | **{v1}** |",
         f"| **UT-H2** renamed copies found | **{len(ren)}** twin copies under a different name | **{'SUPPORTED' if ren else 'not supported'}** |",
         f"| **UT-H3** audited-unpatched copies | {len(cand)} unpatched-looking twin copies; audit sample {len(audit)} — **pending manual audit** | **pending** |",
         "", "## Descriptive", ""]
    for fn in FORKS:
        t = [r for r in tw if r["fork"] == fn and r["t_j"] >= 0.5]
        n_ = [r for r in nm_copies if r["fork"] == fn]
        L.append(f"- **{fn}**: twin copies {len(t)}, status {dict(Counter(r['t_status'] for r in t))}; "
                 f"name-match copies {len(n_)}, status {dict(Counter(r['n_status'] for r in n_))}")
    L.append(f"- twin recall on name-identified copies (same function retrieved): **{rec:.1%}** of {len(nm_copies)}")
    L.append(f"- rows with no fork counterpart by name or twin: {sum(1 for r in rows if not r.get('twin') and not r.get('n_match')):,} "
             "(code removed or never present in the fork)")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}. Audit candidates are written to a private file outside the repo."]
    (DOCS_DIR / "ut.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
