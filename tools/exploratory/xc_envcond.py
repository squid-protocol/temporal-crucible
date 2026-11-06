#!/usr/bin/env python3
"""EXPLORATORY (not registered; the XC extrinsic labels of these repos are already seen).

Environment-coupling surface, measured statically: per C file at each quarterly snapshot, count the
conditional-compilation lines (#if / #ifdef / #ifndef / #elif) that test
  P  platform / compiler / arch macros (_WIN32, __APPLE__, __GNUC__, __aarch64__, endianness, ...)
  H  configure-detected features (HAVE_*)
  V  version checks (...VERSION... compared with < > = !)
and score each, raw and per line, with the XC statistic (recall@20 lift over the stronger LOC order)
for every fix class.

    python tools/exploratory/xc_envcond.py --repo curl      (run from the repo root)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, "tools")
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from ea_eval import recall_at  # noqa: E402
from xc_eval import CLASSES, DAY, DBS, WINDOW  # noqa: E402

COND = r"^\s*#\s*(?:if|ifdef|ifndef|elif)\b.*"
PATTERNS = {
    "P": COND + r"\b(?:_WIN32|WIN32|_WIN64|_WIN32_WINNT|_MSC_VER|__MINGW32__|__MINGW64__|__CYGWIN__|__APPLE__|__MACH__|"
                r"TARGET_OS_\w+|__linux__|__linux|__FreeBSD__|__NetBSD__|__OpenBSD__|__DragonFly__|__sun|__SVR4|__hpux|"
                r"_AIX|__VMS|__OS400__|__ANDROID__|__unix__|__unix|__GNUC__|__GNUC_MINOR__|__clang__|__clang_major__|"
                r"__INTEL_COMPILER|__SUNPRO_C|__WATCOMC__|__BORLANDC__|__STDC_VERSION__|__x86_64__|__i386__|_M_X64|"
                r"_M_IX86|__aarch64__|__arm__|_M_ARM64|__powerpc__|__ppc__|__PPC64__|__s390__|__s390x__|__mips__|"
                r"__sparc__|__sparc|__riscv|BYTE_ORDER|__BYTE_ORDER__|WORDS_BIGENDIAN|B_ENDIAN|L_ENDIAN)\b",
    "H": COND + r"\bHAVE_[A-Z0-9_]+",
    "V": r"^\s*#\s*(?:if|elif)\b.*\b[A-Z0-9_]*VERSION[A-Z0-9_]*\b\s*(?:[<>]=?|[!=]=)",
}


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def counts(repo, sha, pat):
    out = {}
    for line in _git(repo, "-c", "core.quotepath=off", "grep", "-c", "-P", pat, sha, "--", "*.c", "*.h").splitlines():
        _, _, rest = line.partition(":")
        path, _, n = rest.rpartition(":")
        if n.isdigit():
            out[path] = int(n)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    repo = POOL_DIR / a.repo
    snaps = [s for s in json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())["revisions"]
             if s.get("status", "ok") == "ok"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    events = json.loads((REPO_ROOT / "events" / f"{a.repo}_xc.json").read_text())["events"]
    con = sqlite3.connect(f"file:{DBS[a.repo]}?mode=ro", uri=True)
    preds = [f"{k} {m}" for k in ("P", "H", "V", "P+H+V") for m in ("count", "per line")]
    rec = defaultdict(lambda: defaultdict(list))  # class -> predictor -> [lift per snapshot]
    share = defaultdict(list)
    for s in snaps:
        rows = con.execute("SELECT file_path, total_loc FROM file_data WHERE commit_hash=? AND language='c'",
                           (s["sha"],)).fetchall()
        if not rows:
            continue
        paths = [r[0] for r in rows]
        loc = np.array([float(r[1] or 0) for r in rows])
        c = {k: counts(repo, s["sha"], p) for k, p in PATTERNS.items()}
        raw = {k: np.array([float(c[k].get(p, 0)) for p in paths]) for k in PATTERNS}
        raw["P+H+V"] = raw["P"] + raw["H"] + raw["V"]
        share["files with any P"].append(float(np.mean(raw["P"] > 0)))
        sc = {}
        for k, v in raw.items():
            sc[f"{k} count"] = v
            sc[f"{k} per line"] = v / np.maximum(loc, 1.0)
        pos = {k: set() for k in CLASSES}
        for e in events:
            if s["ct"] < e["ct"] <= s["ct"] + WINDOW * DAY:
                pos[e["class"]].update(e["c_files"])
        for k in CLASSES:
            y = np.array([1.0 if p in pos[k] else 0.0 for p in paths])
            if y.sum() == 0:
                continue
            base = max(recall_at(loc, loc, paths, y, 0.2), recall_at(-loc, loc, paths, y, 0.2))
            for n in preds:
                rec[k][n].append(recall_at(sc[n], loc, paths, y, 0.2) - base)
    con.close()
    L = [f"# EXPLORATORY — environment-coupling conditionals vs fix classes: {a.repo}", "",
         "Not registered; these labels are seen. Lift = recall@20 − the snapshot's stronger LOC order.", "",
         f"Share of C files with any platform/compiler/arch conditional: median {np.median(share['files with any P']):.1%}", "",
         "| predictor | " + " | ".join(f"{k} (n)" for k in CLASSES) + " |", "|---|" + "---:|" * len(CLASSES)]
    for n in preds:
        L.append(f"| {n} | " + " | ".join(
            f"{np.mean(rec[k][n]):+.3f} ({len(rec[k][n])})" if rec[k][n] else "—" for k in CLASSES) + " |")
    out = DOCS_DIR / f"xc_envcond_{a.repo}_exploratory.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
