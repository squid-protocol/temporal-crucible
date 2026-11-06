#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""VZT-H1..H2: vendored zlib through time (docs/vzt_hypotheses.md). Aggregates public; timelines private.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <engine venv>/bin/python tools/vzt_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import random
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import vz_eval as Z  # noqa: E402
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

HIST = POOL_DIR / "vzt_hist"
HOSTS = {  # name -> (repo, path, VZ head)
    "zlib-ng": (HIST / "zlib-ng", "", "b342eef204dc"), "chromium-zlib": (HIST / "chromium-zlib", "", "ec453dc9abac"),
    "mysql": (HIST / "mysql", "extra/zlib", "06bcb0eb0ad2"), "mongo": (HIST / "mongo", "src/third_party/zlib", "d48ca0a141ad"),
    "assimp": (HIST / "assimp", "contrib/zlib", "0623040c1eaf"),
    "openjdk": (HIST / "openjdk", "src/java.base/share/native/libzip/zlib", "b0c5b1ba2f3f"),
    "qtbase": (HIST / "qtbase", "src/3rdparty/zlib", "7d5fd833811e"), "cmake": (HIST / "cmake", "Utilities/cmzlib", "9589cb98e1fd"),
    "rsync": (HIST / "rsync", "zlib", "ea645201fefb"), "mariadb": (HIST / "mariadb", "zlib", "f03e90205031"),
    "godot": (HIST / "godot", "thirdparty/zlib", "b47a795aa585"), "libgit2": (POOL_DIR / "libgit2", "deps/zlib", "42a89d7cc937")}
FILES = ("inflate.c", "deflate.c", "trees.c", "inftrees.c", "inffast.c", "crc32.c")
PRIVATE = POOL_DIR / "vz_private" / "vzt_timelines.json"
SEED, AUDIT = 2982, 20


def git(repo, *a, text=True):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *a], capture_output=True, text=text,
                          **({"errors": "replace"} if text else {})).stdout


def normws(t):
    return "\n".join(" ".join(l.split()) for l in t.splitlines() if l.strip())


def vtuple(s):
    m = re.match(r"([0-9]+(?:\.[0-9]+)*)", s or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def upstream():
    """{basename: {normalised text: release tuple}} over zlib release tags; and release dates."""
    zl = Z.ZLIB
    tags = [t for t in git(zl, "tag").split() if re.fullmatch(r"v1\.\d+(\.\d+)*", t)]
    files, dates = defaultdict(dict), {}
    for t in tags:
        v = vtuple(t[1:])
        dates[v] = int(git(zl, "log", "-1", "--format=%ct", t).strip() or 0)
        for f in FILES:
            txt = git(zl, "show", f"{t}:{f}")
            if txt:
                files[f].setdefault(normws(txt), v)
    return files, dates


def host_states(name):
    repo, path, head = HOSTS[name]
    spec = [f":(glob){path + '/' if path else ''}**/{f}" for f in FILES]
    out, seen = [], None
    for line in git(repo, "log", "--first-parent", "--format=%H %ct", head, "--", *spec).splitlines()[::-1]:
        sha, ct = line.split()
        tree = git(repo, "rev-parse", f"{sha}:{path}" if path else f"{sha}^{{tree}}").strip()
        if tree and tree != seen:
            out.append((sha, int(ct)))
            seen = tree
    return out


def state_task(t):
    name, sha, ct = t
    repo, path, _ = HOSTS[name]
    ls = git(repo, "ls-tree", "-r", "--name-only", sha, "--", path or ".").splitlines()
    pick = {}
    for f in FILES + ("zlib.h", "zlib.h.in", "zlib-ng.h.in"):
        c = sorted((p for p in ls if p.rsplit("/", 1)[-1] == f and "/test" not in p and "contrib/" not in p[len(path):]), key=len)
        if c:
            pick[f] = c[0]
    texts = {f: git(repo, "show", f"{sha}:{p}") for f, p in pick.items()}
    ver = None
    for f in ("zlib.h", "zlib.h.in", "zlib-ng.h.in"):
        m = re.search(r'define ZLIB_VERSION "([^"]+)"', texts.get(f, ""))
        if m:
            ver = vtuple(m.group(1))
            break
    return name, sha, ct, ver, {f: texts[f] for f in FILES if f in texts}


def check(text, R, A):
    lines = {Z.U.norm(x) for x in text.splitlines()}
    fa = sum(x in lines for x in A) / len(A) if A else 0.0
    fr = sum(x in lines for x in R) / len(R) if R else 0.0
    if A and fa >= 0.5:
        return "patched"
    if R and fr >= 0.5:
        return "unpatched"
    return "undetermined"


def wilson(k, n, a=0.01):
    from scipy.stats import norm as N
    if not n:
        return float("nan")
    z, p = N.ppf(1 - a / 2), k / n
    return (p + z * z / (2 * n) - z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)


def main() -> int:
    t0 = time.time()
    up, rel_date = upstream()
    fixes = {}
    for f in Z.FIXES:
        es = Z.engine_spans(Z.OUT / f"zlib@{f[:9]}^" / f"zlib@{f[:9]}^_galaxy_master.db")
        per_file = defaultdict(lambda: {"R": set(), "A": set()})
        for (path, _nm), d in Z.fix_functions(f, es).items():
            per_file[path]["R"] |= d["R"]
            per_file[path]["A"] |= d["A"]
        fixes[f[:9]] = dict(per_file)
    tasks = []
    for n in HOSTS:
        st = host_states(n)
        tasks += [(n, s, c) for s, c in st]
        print(f"{n}: {len(st)} states ({time.time() - t0:.0f}s)", flush=True)
    with multiprocessing.get_context("fork").Pool(8) as p:
        states = list(p.imap_unordered(state_task, tasks, chunksize=2))
    units = []
    for name, sha, ct, ver, texts in states:
        for fx, per_file in fixes.items():
            rel = Z.RELEASE[fx]
            for fname, ra in per_file.items():
                if fname not in texts or not (ra["R"] or ra["A"]):
                    continue
                txt = texts[fname]
                verb = up.get(fname, {}).get(normws(txt))
                units.append({"host": name, "sha": sha[:12], "ct": ct, "fix": fx, "cve": Z.CVE[fx], "file": fname,
                              "code": check(txt, ra["R"], ra["A"]),
                              "verbatim": list(verb) if verb else None,
                              "truth": None if not verb else ("patched" if verb >= rel else "unpatched"),
                              "version": list(ver) if ver else None,
                              "ver_verdict": None if not ver else ("patched" if ver >= rel else "unpatched")})
    # --- claims
    vu = [u for u in units if u["truth"] == "unpatched"]
    vp = [u for u in units if u["truth"] == "patched"]
    k1, k2 = sum(u["code"] == "unpatched" for u in vu), sum(u["code"] == "patched" for u in vp)
    def verdict(k, n):
        if n < 20:
            return "not evaluable"
        return "SUPPORTED" if k / n >= 0.9 and wilson(k, n) >= 0.75 else "not supported"
    nv = [u for u in units if u["truth"] is None]
    xt = Counter((u["code"], u["ver_verdict"] or "no version") for u in nv)
    dis = [u for u in nv if u["ver_verdict"] and u["code"] != "undetermined" and u["code"] != u["ver_verdict"]]
    rnd = random.Random(SEED)
    audit = rnd.sample(dis, AUDIT) if len(dis) > AUDIT else dis
    # exposure windows: first state the code check calls patched, minus the upstream release date
    win = {}
    for u in sorted(units, key=lambda u: u["ct"]):
        key = (u["host"], u["cve"])
        if u["code"] == "patched" and key not in win:
            win[key] = (u["ct"] - rel_date[Z.RELEASE[u["fix"]]]) / 86400
    by_cve = defaultdict(list)
    for (h, c), d in win.items():
        by_cve[c].append(d)
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE.write_text(json.dumps({"note": "PRIVATE per-host vendored-zlib timelines (docs/vzt_hypotheses.md)", "units": units,
                                   "disagreements": dis, "audit_sample": audit,
                                   "windows_days": {f"{h}|{c}": d for (h, c), d in win.items()}}, indent=1))
    L = ["# VZT-H1..H2 — vendored zlib through time (SCORED; aggregates only)", "",
         f"- host states (distinct vendored-zlib trees): {len(states):,} over {len(HOSTS)} hosts; units (state × CVE file): **{len(units):,}**",
         f"- verbatim-upstream units: unpatched {len(vu):,}, patched {len(vp):,}; non-verbatim {len(nv):,}", "",
         "| claim | result | Wilson 99% lo | verdict |", "|---|---|---:|---|",
         f"| **VZT-H1** sensitivity (verbatim-unpatched called unpatched) | {k1}/{len(vu)} = {k1 / max(len(vu), 1):.1%} | {wilson(k1, len(vu)):.1%} | **{verdict(k1, len(vu))}** |",
         f"| **VZT-H2** specificity (verbatim-patched called patched) | {k2}/{len(vp)} = {k2 / max(len(vp), 1):.1%} | {wilson(k2, len(vp)):.1%} | **{verdict(k2, len(vp))}** |",
         "", "## Non-verbatim copies: code verdict × version verdict (descriptive)", "", "| code \\ version | " +
         " | ".join(("patched", "unpatched", "no version")) + " |", "|---|---:|---:|---:|"]
    for c in ("patched", "unpatched", "undetermined"):
        L.append(f"| {c} | " + " | ".join(str(xt[(c, v)]) for v in ("patched", "unpatched", "no version")) + " |")
    L += ["", f"- code-vs-version disagreements: **{len(dis)}**; audit sample {len(audit)} (private; audit labels added below by hand)",
          f"- verbatim units the check left undetermined: unpatched {sum(u['code'] == 'undetermined' for u in vu)}, "
          f"patched {sum(u['code'] == 'undetermined' for u in vp)}", "",
          "## Exposure windows (days from upstream fix release to the first state the code check calls patched; descriptive)", "",
          "| CVE | hosts | median | min | max |", "|---|---:|---:|---:|---:|"]
    for c in sorted(by_cve):
        v = by_cve[c]
        L.append(f"| {c} | {len(v)} | {statistics.median(v):.0f} | {min(v):.0f} | {max(v):.0f} |")
    L += ["", "Negative = the host carried the fix before the upstream release (it took the fix commit, or backported early).",
          "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "vzt.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
