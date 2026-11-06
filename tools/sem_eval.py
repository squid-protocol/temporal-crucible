#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SEM-H1..H3: semantic 'fixed differently' patch check on VZ-T's units (docs/sem_hypotheses.md). Aggregates only.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <engine venv>/bin/python tools/sem_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import re
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import vz_eval as Z  # noqa: E402
import vzt_eval as T  # noqa: E402
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402

TOK = re.compile(r"->|<=|>=|==|!=|&&|\|\||<<|>>|\+\+|--|[A-Za-z_]\w*|\d+\w*|[^\s\w]")
DROP = {"(", ")", "if", "while", "for", "return"}
SPLIT = {"&&", "||", "{", "}", ";", "?", ":", ","}
CMP = {"<", ">", "<=", ">=", "==", "!="}
AUDIT = POOL_DIR / "vz_private" / "sem_audit.json"


def norm_toks(text):
    out = []
    for t in TOK.findall(text):
        if t in DROP:
            continue
        out.append("NULL" if t == "Z_NULL" else t)
    return out


def fragments(A):
    frags = set()
    for line in A:
        cur = []
        for t in norm_toks(line) + [";"]:
            if t in SPLIT:
                if len(cur) >= 3 and any(x in CMP for x in cur):
                    frags.add(tuple(cur))
                cur = []
            else:
                cur.append(t)
    return frags


def present(frag, stream):
    return ("\x01" + "\x01".join(frag) + "\x01") in stream


def sem(text, R, A, frags):
    if frags:
        stream = "\x01" + "\x01".join(norm_toks(text)) + "\x01"
        if sum(present(f, stream) for f in frags) / len(frags) >= 0.5:
            return "patched"
    return T.check(text, R, A)


def main() -> int:
    t0 = time.time()
    up, _ = T.upstream()
    fixes = {}
    for f in Z.FIXES:
        es = Z.engine_spans(Z.OUT / f"zlib@{f[:9]}^" / f"zlib@{f[:9]}^_galaxy_master.db")
        per_file = defaultdict(lambda: {"R": set(), "A": set()})
        for (path, _nm), d in Z.fix_functions(f, es).items():
            per_file[path]["R"] |= d["R"]
            per_file[path]["A"] |= d["A"]
        fixes[f[:9]] = {k: {**v, "F": fragments(v["A"])} for k, v in per_file.items()}
    tasks = [(n, s, c) for n in T.HOSTS for s, c in T.host_states(n)]
    with multiprocessing.get_context("fork").Pool(8) as p:
        states = list(p.imap_unordered(T.state_task, tasks, chunksize=2))
    units = []
    for name, sha, ct, ver, texts in states:
        for fx, per_file in fixes.items():
            rel = Z.RELEASE[fx]
            for fname, ra in per_file.items():
                if fname not in texts or not (ra["R"] or ra["A"]):
                    continue
                txt = texts[fname]
                verb = up.get(fname, {}).get(T.normws(txt))
                units.append({"key": (name, sha[:12], fx, fname), "cve": Z.CVE[fx],
                              "line": T.check(txt, ra["R"], ra["A"]), "sem": sem(txt, ra["R"], ra["A"], ra["F"]),
                              "truth": None if not verb else ("patched" if verb >= rel else "unpatched"),
                              "ver": None if not ver else ("patched" if ver >= rel else "unpatched")})
    vt = [u for u in units if u["truth"]]
    wrong = sum(u["sem"] in ("patched", "unpatched") and u["sem"] != u["truth"] for u in vt)
    wrong_line = sum(u["line"] in ("patched", "unpatched") and u["line"] != u["truth"] for u in vt)
    vu = [u for u in vt if u["truth"] == "unpatched"]
    vp = [u for u in vt if u["truth"] == "patched"]
    k_s, k_p = sum(u["sem"] == "unpatched" for u in vu), sum(u["sem"] == "patched" for u in vp)
    up99 = 1 - T.wilson(len(vt) - wrong, len(vt))
    v1 = "SUPPORTED" if wrong / len(vt) <= 0.01 and up99 <= 0.02 else "not supported"
    v2 = ("SUPPORTED" if k_s / len(vu) >= 0.9 and T.wilson(k_s, len(vu)) >= 0.75 and k_p / len(vp) >= 0.9 and T.wilson(k_p, len(vp)) >= 0.75
          else "not supported")
    aud = json.loads(AUDIT.read_text())["units"]
    idx = {u["key"]: u for u in units}
    sem_ok = line_ok = n3 = 0
    for a in aud:
        if a.get("truth") not in ("patched", "unpatched"):
            continue
        u = idx.get((a["host"], a["sha"], a["fix"], a["file"]))
        if not u:
            continue
        n3 += 1
        sem_ok += u["sem"] == a["truth"]
        line_ok += u["line"] == a["truth"]
    v3 = "not evaluable" if n3 < 10 else ("SUPPORTED" if sem_ok > line_ok else "not supported")
    first = json.loads((POOL_DIR / "vz_private" / "vzt_timelines.json").read_text())["audit_sample"]
    f_keys = [(a["host"], a["sha"], a["fix"], a["file"]) for a in first]
    in_sample = Counter((idx[k]["line"], idx[k]["sem"]) for k in f_keys if k in idx)
    frag_n = {Z.CVE[fx]: sum(len(v["F"]) for v in pf.values()) for fx, pf in fixes.items()}
    abst_line = sum(u["line"] == "undetermined" for u in units) / len(units)
    abst_sem = sum(u["sem"] == "undetermined" for u in units) / len(units)
    changed = Counter((u["line"], u["sem"]) for u in units if u["line"] != u["sem"])
    L = ["# SEM-H1..H3 — semantic 'fixed differently' patch check (SCORED; aggregates only)", "",
         f"- units {len(units):,} (VZ-T's); verbatim-truth units {len(vt):,}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **SEM-H1** no new errors on verbatim truth | wrong calls {wrong} / {len(vt)} (line check: {wrong_line}); Wilson 99% upper {up99:.2%} | **{v1}** |",
         f"| **SEM-H2** meets VZ-T bars | sensitivity {k_s}/{len(vu)} = {k_s / len(vu):.1%} (lo {T.wilson(k_s, len(vu)):.1%}); specificity {k_p}/{len(vp)} = {k_p / len(vp):.1%} (lo {T.wilson(k_p, len(vp)):.1%}) | **{v2}** |",
         f"| **SEM-H3** beats line check, fresh audit | SEM correct {sem_ok}/{n3}, line correct {line_ok}/{n3} | **{v3}** |",
         "", "## Descriptive", "",
         f"- guard fragments per CVE: {frag_n}",
         f"- abstention rate: line {abst_line:.1%} → SEM {abst_sem:.1%}",
         f"- verdict changes line → SEM (all units): {dict(changed)}",
         f"- VZ-T's first audit sample (in-sample, the design example): (line, SEM) = {dict(in_sample)}",
         "", f"Runtime {time.time() - t0:.0f}s."]
    (DOCS_DIR / "sem.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
