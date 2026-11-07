#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""DC-H1..H2 (docs/dc_hypotheses.md): danger-language comments at birth vs whole-life first CVE fix. Engine venv.
Runs only if CMT-G passed (docs/cmt_gate.md says PASS).

    <engine venv>/bin/python tools/dc_eval.py
"""
from __future__ import annotations

import bisect
import multiprocessing
import pathlib
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from gitgalaxy.core.prism import Prism
from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS
from scipy.stats import rankdata  # noqa: F401

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, _fname, _git, _parser, fix_events, map_fix  # noqa: E402
from ints_eval import CLS, ITERS, REPOS, SEED, YEAR, lives, mh_rate  # noqa: E402
from nh_eval import snapshots  # noqa: E402

ALPHA = 0.01 / 2
DANGER = re.compile(
    r"\b(must not|must be|callers? must|caller is responsible|assum(?:e|es|ed|ing|ptions?)|unsafe|not safe|"
    r"not thread[- ]safe|thread[- ]unsafe|careful(?:ly)?|beware|warning|danger(?:ous)?|untrusted|trust(?:ed|s)?|"
    r"validat(?:e|ed|es|ion)|sanitiz\w*|overflow|underflow|bounds?|out of range|null[- ]terminat\w*|do not|"
    r"never (?:call|use|pass)|undefined behaviou?r|race|reentran\w*|security|attacker|malicious|exploit\w*|vulnerab\w*|xxx)\b",
    re.I)
_P = {}


def prism():
    if "p" not in _P:
        _P["p"] = Prism(LEXICAL_FAMILY_HEURISTICS, LANGUAGE_DEFINITIONS)
    return _P["p"]


def comment_task(t):
    r, sha, path, names = t
    raw = _git(POOL_DIR / r, "show", f"{sha}:{path}", text=False)
    if not raw:
        return r, sha, path, {}
    lang = "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"
    txt = raw.decode("utf-8", "replace")
    try:
        pos = prism().split_positional_comment_stream(txt, lang).split("\n")
    except Exception:
        return r, sha, path, {}
    lines = txt.split("\n")
    spans = {}
    stack = [_parser(lang).parse(raw).root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm and nm not in spans:
                spans[nm] = (n.start_point[0], n.end_point[0])
            continue
        stack.extend(n.children)
    out = {}
    for nm in names:
        sp = spans.get(nm) or spans.get(nm.split("::")[-1])
        if not sp:
            continue
        a, b = sp
        idx = [i for i in range(a, min(b + 1, len(pos))) if pos[i].strip()]
        i, blank = a - 1, 0
        while i >= 0:
            if i < len(pos) and pos[i].strip():
                idx.append(i)
                blank = 0
            elif not lines[i].strip() and blank == 0:
                blank = 1
            else:
                break
            i -= 1
        text = "\n".join(pos[i] for i in sorted(set(idx)))
        words = [m.group(1).lower() for m in DANGER.finditer(text)]
        out[nm] = (len(set(idx)), bool(words), words)
    return r, sha, path, out


def main() -> int:
    gate = (DOCS_DIR / "cmt_gate.md").read_text()
    # DC-2: the gate is scoped to C and C++ (each P and R >= 90%), the languages DC uses
    m = re.search(r"C: P ([\d.]+)% / R ([\d.]+)%; C\+\+: P ([\d.]+)% / R ([\d.]+)%", gate)
    if not m or min(float(x) for x in m.groups()) < 90.0:
        print("DC-2 C/C++ gate did not pass: stops (registered).")
        return 1
    t0 = time.time()
    ev, last = [], {}
    for r in REPOS:
        e, last[r] = fix_events(r)
        ev += [x for x in e if x[3] in CLS]
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=8) for h in hs]
    print(f"hits {len(hits):,} ({time.time() - t0:.0f}s)", flush=True)
    U = []
    for r in REPOS:
        snaps, ids_at, info = lives(r)
        cts = [s["ct"] for s in snaps]
        first, file_cve = defaultdict(dict), defaultdict(list)
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
            if fid is not None and (klass not in first[fid] or ct < first[fid][klass]):
                first[fid][klass] = ct
        for v in file_cve.values():
            v.sort()
        groups = defaultdict(list)
        for fid, inf in info.items():
            if inf["birth_k"] > 0 and inf["loc"] >= 3:
                groups[(snaps[inf["birth_k"]]["sha"], inf["key"][0])].append(inf["key"][1])
        with multiprocessing.get_context("fork").Pool(8) as p:
            cm = {(rr, sha, path): out for rr, sha, path, out in
                  p.imap_unordered(comment_task, [(r, sha, path, names) for (sha, path), names in groups.items()], chunksize=4)}
        for fid, inf in info.items():
            if inf["birth_k"] == 0 or inf["loc"] < 3:
                continue
            b = cts[inf["birth_k"]]
            death = cts[inf["last_k"] + 1] if inf["last_k"] + 1 < len(cts) else float("inf")
            end = min(death, last[r])
            if end <= b:
                continue
            c = cm.get((r, snaps[inf["birth_k"]]["sha"], inf["key"][0]), {}).get(inf["key"][1])
            if c is None:
                continue
            prior = bisect.bisect_left(file_cve.get(inf["key"][0], []), b) > 0
            U.append((r, inf["key"][0], int(np.floor(np.log10(inf["loc"]) / 0.1)), prior, c[0], c[1], c[2], b, end,
                      {k: v for k, v in first.get(fid, {}).items() if b < v <= end}))
        print(f"{r}: births with comment info {sum(1 for u in U if u[0] == r):,} ({time.time() - t0:.0f}s)", flush=True)
    Uc = [u for u in U if u[4] >= 1]
    e = np.array([1.0 if u[5] else 0.0 for u in Uc])
    st = np.array([f"{u[0]}|{u[2]}|{u[3]}" for u in Uc])
    cl = np.array([f"{u[0]}:{u[1]}" for u in Uc])

    def evpt(klass, UU):
        return (np.array([1.0 if klass in u[9] else 0.0 for u in UU]),
                np.array([((u[9][klass] if klass in u[9] else u[8]) - u[7]) / YEAR for u in UU]))
    EV = {k: evpt(k, Uc) for k in CLS}
    rr = {k: mh_rate(e, *EV[k], st) for k in CLS}
    rng = np.random.default_rng(SEED)
    _, ci = np.unique(cl, return_inverse=True)
    grp = [np.flatnonzero(ci == k) for k in range(ci.max() + 1)]
    bl, br = [], []
    for _ in range(ITERS):
        pick = np.concatenate([grp[k] for k in rng.integers(0, len(grp), len(grp))])
        a_ = mh_rate(e[pick], EV["latent"][0][pick], EV["latent"][1][pick], st[pick])
        o_ = mh_rate(e[pick], EV["other-fix"][0][pick], EV["other-fix"][1][pick], st[pick])
        bl.append(a_)
        br.append(a_ / o_ if o_ > 0 else np.nan)
    lo1, hi1 = float(np.nanquantile(bl, ALPHA)), float(np.nanquantile(bl, 1 - ALPHA))
    lo2 = float(np.nanquantile(br, ALPHA))
    v1 = ("SUPPORTED: the authors' words were right" if rr["latent"] > 1 and lo1 > 1
          else "reversed: danger-commented code is safer" if rr["latent"] < 1 and hi1 < 1 else "not supported")
    ratio = rr["latent"] / rr["other-fix"]
    v2 = "SUPPORTED" if ratio > 1 and lo2 > 1 else "not supported"
    words = Counter(w for u in Uc if "latent" in u[9] for w in set(u[6]))
    # commented vs uncommented (separate contrast)
    ec = np.array([1.0 if u[4] >= 1 else 0.0 for u in U])
    stc = np.array([f"{u[0]}|{u[2]}|{u[3]}" for u in U])
    evc, ptc = evpt("latent", U)
    L = ["# DC-2 (DC-H1..H2) — danger comments at birth vs whole-life first CVE fix (SCORED)", "",
         f"- births with comment info {len(U):,}; with ≥ 1 comment line {len(Uc):,}; danger-commented {int(e.sum()):,} ({e.mean():.0%} of commented)", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **DC-H1** danger-commented vs plain-commented → first CVE fix rate | rate ratio **{rr['latent']:.2f}** [{lo1:.2f}, {hi1:.2f}]; first-CVE events {int((EV['latent'][0] * e).sum())} / {int((EV['latent'][0] * (1 - e)).sum())} | **{v1}** |",
         f"| **DC-H2** CVE-specific (÷ other-fix rate ratio) | **{ratio:.2f}** (lo {lo2:.2f}); other-fix {rr['other-fix']:.2f} | **{v2}** |",
         "", "## Descriptive", "",
         f"- regression {rr['regression']:.2f}; extrinsic {rr['extrinsic']:.2f}",
         f"- commented vs uncommented (all births): CVE rate ratio {mh_rate(ec, evc, ptc, stc):.2f}",
         "- most frequent danger words among CVE-hit functions: " + ", ".join(f"{w} {n}" for w, n in words.most_common(10))]
    for r in REPOS:
        mm = np.array([u[0] == r for u in Uc])
        if mm.sum():
            L.append(f"- {r}: CVE rate ratio {mh_rate(e[mm], EV['latent'][0][mm], EV['latent'][1][mm], st[mm]):.2f} "
                     f"(events {int((EV['latent'][0][mm] * e[mm]).sum())} / {int((EV['latent'][0][mm] * (1 - e[mm])).sum())})")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "dc.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
