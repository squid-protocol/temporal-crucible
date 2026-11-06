#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LIB-R (LIB recipe, unchanged, on PostgreSQL + libgit2) and LIB-E (engine calls_out_to coupling vs the regex)
-- docs/librep_hypotheses.md.

    python tools/librep_eval.py --scratch <dir>
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import pathlib
import re
import shutil
import sqlite3
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lib_eval  # noqa: E402
from _engine import DOCS_DIR, REPO_ROOT  # noqa: E402
from lib_eval import recall20, snapshot_task, work_commits  # noqa: E402

ORIG_DEPS = dict(lib_eval.DEPS)
ORIG_EXTS = dict(lib_eval.EXTS)
OSSL = next(p for d, _s, p in ORIG_DEPS["curl"] if d == "openssl")
ZLIB = next(p for d, _s, p in ORIG_DEPS["curl"] if d == "zlib")
SSH2 = next(p for d, _s, p in ORIG_DEPS["curl"] if d == "libssh2")
MBED = next(p for d, _s, p in ORIG_DEPS["curl"] if d == "mbedtls")
LZ4 = next(p for d, _s, p in ORIG_DEPS["libarchive"] if d == "lz4")
ZSTD = next(p for d, _s, p in ORIG_DEPS["libarchive"] if d == "zstd")
R_DEPS = {  # the registered table (docs/librep_hypotheses.md), verbatim
    "postgres": [("openssl", "openssl|libressl", OSSL), ("zlib", "zlib", ZLIB),
                 ("icu", "icu", r"#include\s*[<\"]unicode/|\b(?:u|ucol|ubrk|uloc|ucnv|unorm2?)_\w+\s*\("),
                 ("libxml2", "libxml2|libxml", r"#include\s*[<\"]libxml/|\bxml\w+\s*\("),
                 ("lz4", "lz4", LZ4), ("zstd", "zstd", ZSTD),
                 ("gssapi", "gssapi|gss|kerberos|krb5", r"#include\s*[<\"]gssapi|\bgss_\w+\s*\("),
                 ("ldap", "ldap", r"#include\s*[<\"](?:ldap|winldap)\.h|\bldap_\w+\s*\("),
                 ("readline", "readline|libedit|editline",
                  r"#include\s*[<\"](?:readline/|editline/|histedit)|\b(?:readline|rl_\w+|add_history|history_\w+)\s*\("),
                 ("llvm", "llvm", r"#include\s*[<\"]llvm|\bLLVM\w+\s*\("),
                 ("perl", "perl|plperl", r"#include\s*[<\"](?:EXTERN|perl|XSUB)\.h|\b(?:Perl_\w+|sv_\w+|av_\w+|hv_\w+|newSV\w*)\s*\("),
                 ("python", "python|plpython", r"#include\s*[<\"]Python\.h|\bPy\w+_\w+\s*\("),
                 ("tcl", "tcl|pltcl", r"#include\s*[<\"]tcl\.h|\bTcl_\w+\s*\(")],
    "libgit2": [("openssl", "openssl", OSSL), ("mbedtls", "mbedtls|mbed tls", MBED), ("zlib", "zlib", ZLIB),
                ("libssh2", "libssh2", SSH2),
                ("pcre", "pcre|pcre2", r"#include\s*[<\"]pcre|\bpcre2?_\w+\s*\("),
                ("http-parser", "http-parser|http_parser|llhttp",
                 r"#include\s*[<\"](?:http_parser|llhttp)\.h|\b(?:http_parser|llhttp)_\w+\s*\("),
                ("winhttp", "winhttp", r"#include\s*[<\"]winhttp\.h|\bWinHttp\w+\s*\("),
                ("securetransport", "securetransport|secure transport",
                 r"#include\s*[<\"]Security/|\b(?:SecTrust|SecCertificate|SSLCreateContext|SSLHandshake|SSLRead|SSLWrite)\w*\s*\("),
                ("ntlm", "ntlm|ntlmclient", r"#include\s*[<\"]ntlm|\bntlm_\w+\s*\("),
                ("iconv", "iconv", r"#include\s*[<\"]iconv\.h|\biconv\w*\s*\(")],
}
R_EXTS = {"postgres": (".c", ".h"), "libgit2": (".c", ".h")}
WT = pathlib.Path("/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees")
EDB = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db", "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
       "harfbuzz": WT / "sc-class/dbs/harfbuzz_out/harfbuzz_galaxy_master.db",
       "libarchive": WT / "sc-class/dbs/libarchive_out/libarchive_galaxy_master.db"}
SEED, ITERS, MIN_SNAPS = 2982, 5000, 20
ALPHA_E = 0.01 / 2


def engine_calls(db, sha):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = {}
    for path, calls in con.execute("SELECT fd.file_path, f.calls_out_to FROM function_data f JOIN file_data fd ON f.file_id = fd.id "
                                   "WHERE fd.commit_hash = ?", (sha,)):
        if calls:
            try:
                out.setdefault(path, []).extend(json.loads(calls))
            except ValueError:
                pass
    con.close()
    return out


def lib_e():
    lib_eval.DEPS, lib_eval.EXTS = ORIG_DEPS, ORIG_EXTS
    units = {}
    for r in ORIG_DEPS:
        con = sqlite3.connect(f"file:{EDB[r]}?mode=ro", uri=True)
        have = {x[0] for x in con.execute("SELECT DISTINCT commit_hash FROM repo_data")}
        con.close()
        walk = json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())
        snaps = [s for s in walk["revisions"] if s.get("status", "ok") == "ok" and s["sha"] in have]
        repo = lib_eval.POOL_DIR / r
        for s in snaps:
            s["ct"] = int(lib_eval._git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
        work = work_commits(r)
        with multiprocessing.get_context("fork").Pool(6) as p:
            data = {sha: (ln, cp) for sha, ln, cp in p.imap_unordered(snapshot_task, [(r, s["sha"]) for s in snaps])}
        pats = {d: re.compile(pat) for d, _s, pat in ORIG_DEPS[r]}
        per = {d: [] for d in pats}
        for s in snaps:
            lines, coup = data[s["sha"]]
            if not lines:
                continue
            calls = engine_calls(EDB[r], s["sha"])
            paths = sorted(lines)
            loc = np.array([float(max(lines[p], 1)) for p in paths])
            pr = np.argsort(np.argsort(np.array(paths)))
            for d, rx in pats.items():
                touched = set()
                for c in work[d]:
                    if s["ct"] < c["ct"] <= s["ct"] + lib_eval.WINDOW * lib_eval.DAY:
                        touched.update(c["files"])
                y = np.array([1.0 if p in touched else 0.0 for p in paths])
                if y.sum() == 0:
                    continue
                se = np.array([sum(1 for c in calls.get(p, ()) if rx.search(str(c) + "(")) for p in paths], float) / loc
                sg = np.array([coup[d].get(p, 0) for p in paths], float) / loc
                base = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
                re_, rg = recall20(se, loc, pr, y), recall20(sg, loc, pr, y)
                per[d].append({"e1": re_ - base, "e2": re_ - rg, "re": re_, "rg": rg, "base": base})
        for d, v in per.items():
            if len(v) >= MIN_SNAPS:
                units[(r, d)] = v
        print(f"LIB-E {r}: {len(snaps)} engine snapshots", flush=True)
    rng = np.random.default_rng(SEED)
    L = ["## LIB-E — engine call-graph coupling (original LIB repos)", "",
         f"- evaluable units (≥ {MIN_SNAPS} engine snapshots with D-work): **{len(units)}** — " + ", ".join(f"{r}/{d}" for r, d in units), "",
         "| claim | units | mean | lo (α 0.01/2) | verdict |", "|---|---:|---:|---:|---|"]
    for cid, key, thr in (("LIBE-H1 engine coupling − stronger size order", "e1", 0.0), ("LIBE-H2 engine − regex (non-inferiority margin −0.05)", "e2", -0.05)):
        arrs = [np.array([x[key] for x in v]) for v in units.values()]
        if len(arrs) < 3:
            L.append(f"| **{cid}** | {len(arrs)} | — | — | **not evaluable** |")
            continue
        mean = float(np.mean([a.mean() for a in arrs]))
        b = np.array([np.mean([a[rng.integers(0, len(a), len(a))].mean() for a in arrs]) for _ in range(ITERS)])
        lo = float(np.quantile(b, ALPHA_E))
        ok = (mean > 0 and lo > 0) if thr == 0.0 else lo > thr
        L.append(f"| **{cid}** | {len(arrs)} | {mean:+.3f} | {lo:+.3f} | **{'SUPPORTED' if ok else 'not supported'}** |")
    L += ["", "| repo | D | snapshots | recall@20 engine | regex | stronger size |", "|---|---|---:|---:|---:|---:|"]
    for (r, d), v in units.items():
        L.append(f"| {r} | {d} | {len(v)} | {np.mean([x['re'] for x in v]):.3f} | {np.mean([x['rg'] for x in v]):.3f} | {np.mean([x['base'] for x in v]):.3f} |")
    return L


def lib_r(scratch):
    lib_eval.DEPS, lib_eval.EXTS = R_DEPS, R_EXTS
    lib_eval.DOCS_DIR = scratch
    scratch.mkdir(parents=True, exist_ok=True)
    lib_eval.main()
    txt = (scratch / "lib.md").read_text().replace("# LIB-H1..H3 — library-coupling surface (SCORED)",
                                                   "## LIB-R — LIB recipe unchanged on PostgreSQL + libgit2").replace("LIB-H", "LIBR-H")
    txt = txt.replace("## Per unit", "### Per unit")
    return txt.splitlines()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=pathlib.Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    E = lib_e()
    R = lib_r(a.scratch)
    L = ["# LIB-R and LIB-E (SCORED)", ""] + R + [""] + E + ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "librep.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
