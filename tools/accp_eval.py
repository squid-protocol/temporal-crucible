#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ACC-P — panel call-graph accuracy, the LAWS language gate (docs/laws_hypotheses.md Amendments 0-2, 4).

Runs the registered per-language oracle against the PANEL ENGINE's resolved call graph (confident links only)
on 2 panel repos per language at 2 snapshots each. Reuses the existing scorers rather than a new one:
`acc2_eval.resolved` / `.matcher` for the engine side, `acc_eval.compare` for the statistics, and each
language's registered oracle.

    python tools/accp_eval.py prep  --langs python c go java      # export + scan (slow; resumable)
    python tools/accp_eval.py score --langs python                # -> docs/accp.md

Repos are draws 1 and 2 of each language's seeded order (`docs/laws_seating/<lang>.json`), as Amendment 2
item 2 fixes. Snapshots are the panel's first quarter and the 2026-10-01 boundary, on the quarterly boundary
rule of `cgr_build.make_walk`: the last first-parent commit before the boundary, starting at the first
boundary holding >= 50 files of the language's extensions.

Oracles for C++, Rust and JS/TS are not chosen (docs/oracle_criteria.md): those languages are not run here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, REPO_ROOT  # noqa: E402

STUDY = pathlib.Path("/srv/storage_16tb/projects/gitgalaxy/acc-study")
ENGINE_GG = pathlib.Path("/srv/storage_16tb/projects/gitgalaxy/engine-laws-b873edc5b")
ENGINE_PIN = "b873edc5b"
POOL = pathlib.Path(os.environ.get("LAWS_SEAT_POOL", "/srv/storage_16tb/projects/laws-seat-pool"))
LATE = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)   # the registered late boundary
MIN_FILES = 50                                            # cgr_build.make_walk's start rule
EXT = {"c": (".c", ".h"), "java": (".java",), "go": (".go",), "python": (".py",)}
RUNNABLE = ("c", "java", "go", "python")                  # oracles installed and previously exercised
STATE = DOCS_DIR / "accp_prep.json"


def git(repo, *a, text=True):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=text,
                          **({"errors": "replace"} if text else {})).stdout


def seated(lang):
    d = json.loads((DOCS_DIR / "laws_seating" / f"{lang}.json").read_text())
    return d["seated"][:2]                                 # ACC-P uses draws 1 and 2


def boundaries(repo, exts):
    """(first eligible boundary, its sha), (late boundary, its sha) — cgr_build.make_walk's rule."""
    head = git(repo, "rev-parse", "HEAD").strip()
    log = git(repo, "log", "--reverse", "--format=%ct").split()
    if not log or not head:
        return None, None
    first = dt.datetime.fromtimestamp(int(log[0]), dt.timezone.utc)
    y, m = first.year, ((first.month - 1) // 3 + 1) * 3 + 1
    if m > 12:
        y, m = y + 1, 1
    early = None
    while True:
        b = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc)
        if b > LATE:
            break
        sha = git(repo, "rev-list", "--first-parent", "-1", f"--before={b.isoformat()}", head).strip()
        if sha and early is None:
            n = sum(1 for f in git(repo, "ls-tree", "-r", "--name-only", sha).splitlines() if f.endswith(exts))
            if n >= MIN_FILES:
                early = (b, sha)
        if b == LATE:
            return early, ((b, sha) if sha else None)
        m += 3
        if m > 12:
            y, m = y + 1, 1
    return early, None


def label(b):
    return f"{b.year}Q{(b.month - 1) // 3 + 1}"


def prep_one(lang, full, state):
    name = full.replace("/", "__")
    repo = POOL / lang / name
    if not repo.exists():
        state[f"{lang}:{full}"] = {"error": f"no clone at {repo}"}
        return
    early, late = boundaries(repo, EXT[lang])
    for which, bs in (("early", early), ("late", late)):
        if bs is None:
            state[f"{name}@{which}"] = {"repo": full, "language": lang, "error": "no snapshot at this boundary"}
            continue
        b, sha = bs
        key = f"{name}@{label(b)}"
        rec = {"repo": full, "language": lang, "which": which, "boundary": b.date().isoformat(),
               "sha": sha, "key": key, "engine": ENGINE_PIN}
        src = STUDY / "repos" / key
        out = STUDY / "engine" / key
        if (out / "done").exists():
            rec["scan"] = "cached"
            state[key] = rec
            continue
        src.mkdir(parents=True, exist_ok=True)
        if not any(src.iterdir()):
            arch = subprocess.run(["git", "-C", str(repo), "archive", sha], capture_output=True)
            if not arch.stdout:
                rec["error"] = "git archive produced nothing (blobs unavailable?)"
                state[key] = rec
                continue
            subprocess.run(["tar", "-x", "-C", str(src)], input=arch.stdout, capture_output=True)
        out.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "PYTHONPATH": str(ENGINE_GG), "GITGALAXY_LICENSE_KEY": "COMMUNITY_FREE_TIER",
               "GITGALAXY_DISABLE_GIT_HISTORY": "1"}
        t0 = time.time()
        with tempfile.TemporaryDirectory(dir=str(out)) as tmp:
            p = subprocess.run([sys.executable, "-m", "gitgalaxy.galaxyscope", str(src), "--output", str(tmp) + "/"],
                               env=env, capture_output=True, text=True, errors="replace")
            dbs = sorted(pathlib.Path(tmp).glob("*_galaxy_master.db"))
            if dbs:
                dest = out / dbs[0].name
                dbs[0].replace(dest)
                (out / "done").write_text(sha)
                rec["scan"] = "ok"
                rec["db"] = dest.name
            else:
                rec["scan"] = "failed"
                rec["error"] = (p.stdout + p.stderr)[-600:]
        rec["scan_secs"] = round(time.time() - t0, 1)
        state[key] = rec
        print(f"  {key}: {rec.get('scan')} ({rec.get('scan_secs')}s)", flush=True)
        STATE.write_text(json.dumps(state, indent=1))


def cmd_prep(a) -> int:
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    for lang in a.langs:
        if lang not in RUNNABLE:
            print(f"{lang}: no installed oracle — skipped (docs/oracle_criteria.md)", flush=True)
            continue
        for full in seated(lang):
            print(f"{lang} {full}", flush=True)
            prep_one(lang, full, state)
    STATE.write_text(json.dumps(state, indent=1))
    ok = sum(1 for v in state.values() if v.get("scan") in ("ok", "cached"))
    print(f"prep: {ok}/{len(state)} snapshots scanned -> {STATE}", flush=True)
    return 0


# ============================================================================ score
# Repo-independent oracle wrappers. ACC/ACC-2 wired their oracles to one repo each: acc2's Python oracle
# names `sphinx` as the package and its Java node mapper assumes a Maven `src/main/java` tree. ACC-P runs on
# repos nobody chose for their build layout, so each wrapper below discovers the layout instead of assuming
# it. Per docs/oracle_criteria.md §3 the oracle and its command line are fixed per LANGUAGE; what varies here
# is only where the sources are, which is recorded per repo.

def _py_oracle(study, key):
    import acc2_eval as A2
    root = (study / "repos" / key).resolve()
    pkgs = [d for d in sorted(root.iterdir()) if d.is_dir() and (d / "__init__.py").exists()]
    files = [str(f) for p in pkgs for f in sorted(p.rglob("*.py"))] or [str(f) for f in sorted(root.rglob("*.py"))]
    if not files:
        return {"direct": set(), "dynamic": set(), "err": "no .py files"}
    out = study / f"oracle_pycg_{key}.json"
    p = subprocess.run([str(study / "venv/bin/python"), "-m", "pycg", "--package", str(root), *files[:4000],
                        "-o", str(out)], capture_output=True, text=True, timeout=7200)
    if p.returncode != 0 or not out.exists():
        return {"direct": set(), "dynamic": set(), "err": f"pycg rc={p.returncode} {p.stderr[-200:]}"}
    cg = json.loads(out.read_text())

    def node(q):
        parts = q.split(".")
        for i in range(len(parts) - 1, 0, -1):
            f = root / ("/".join(parts[:i]) + ".py")
            if f.exists():
                rest = parts[i:]
                return (str(f.relative_to(root)), rest[-2] if len(rest) >= 2 else None, rest[-1])
        return None
    edges = set()
    for caller, callees in cg.items():
        a = node(caller)
        if a is None:
            continue
        for callee in callees:
            b = node(callee)
            if b is not None and a != b:
                edges.add((a, b))
    return {"direct": edges, "dynamic": set(), "pkgs": [p.name for p in pkgs], "files": len(files)}


def _go_oracle(study, key):
    """Amendment 4: direct edges from -algo=static, dynamic from -algo=vta minus static."""
    import re as _re
    root = (study / "repos" / key).resolve()
    env = {**{k: v for k, v in os.environ.items() if k != "GOFLAGS"},
           "GOPATH": str(study / "gopath"), "GOMODCACHE": str(study / "gopath/pkg/mod"),
           "GOTOOLCHAIN": "auto", "PATH": f"{study}/go/bin:{study}/gopath/bin:{os.environ['PATH']}"}
    dl = subprocess.run(["go", "mod", "download"], cwd=root, env=env, capture_output=True, text=True, timeout=3600)
    fmt = "{{posn .Caller}}\t{{posn .Callee}}\t{{.Caller.Name}}\t{{.Callee.Name}}"
    got, errs = {}, {}
    for algo in ("static", "vta"):
        p = subprocess.run(["callgraph", f"-algo={algo}", f"-format={fmt}", "./..."], cwd=root, env=env,
                           capture_output=True, text=True, timeout=7200)
        es, rs = set(), str(root)

        def pos(s):
            m = _re.match(r"(.*):(\d+):\d+$", s)
            if not m:
                return None
            try:
                return str(pathlib.Path(m.group(1)).resolve().relative_to(root)), int(m.group(2))
            except ValueError:
                return None
        for line in p.stdout.splitlines():
            if line.count(rs) < 2:
                continue
            parts = line.split("\t")
            if len(parts) != 4:
                continue
            a, b = pos(parts[0]), pos(parts[1])
            if a and b and a != b:
                es.add(((a[0], parts[2], a[1]), (b[0], parts[3], b[1])))
        got[algo] = es
        errs[algo] = p.stderr[-200:] if not es else ""
    direct = got.get("static", set())
    return {"direct": direct, "dynamic": got.get("vta", set()) - direct,
            "err": (f"mod download: {dl.stderr[-150:]} " if dl.returncode else "") + errs.get("static", ""),
            "counts": {k: len(v) for k, v in got.items()}}


def _java_oracle(study, key):
    import acc2_eval as A2
    root = study / "repos" / key
    jars = [j for j in list(root.rglob("target/*.jar")) + list(root.rglob("build/libs/*.jar"))
            if not __import__("re").search(r"(sources|javadoc|tests)", j.name)]
    built = ""
    if not jars:
        if (root / "pom.xml").exists():
            b = subprocess.run(["mvn", "-q", "-B", "-DskipTests", "-Drat.skip=true", "-Djacoco.skip=true",
                                "-Dmaven.javadoc.skip=true", "-Dcheckstyle.skip", "-Dspotbugs.skip",
                                "-Dpmd.skip", "package"], cwd=root, capture_output=True, text=True, timeout=5400)
            built = f"mvn rc={b.returncode} {b.stderr[-200:]}"
        elif (root / "gradlew").exists() or (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
            built = "gradle build not attempted (no offline-safe invocation registered)"
        else:
            built = "no recognised build file"
        jars = [j for j in list(root.rglob("target/*.jar")) + list(root.rglob("build/libs/*.jar"))
                if not __import__("re").search(r"(sources|javadoc|tests)", j.name)]
    if not jars:
        return {"direct": set(), "dynamic": set(), "err": f"no jar: {built}"}
    return A2.oracle_java(study, key)


def _profile(study, key, lang):
    """Registered output (b): the resolution profile, plus the (path, name) node merge rate."""
    import sqlite3
    db = sorted((study / "engine" / key).glob("*_galaxy_master.db"))
    if not db:
        return {}
    con = sqlite3.connect(f"file:{db[0]}?mode=ro", uri=True)
    tot = con.execute("SELECT COUNT(*) FROM fcall_data WHERE kind='call'").fetchone()[0]
    res = con.execute("SELECT COUNT(*) FROM fcall_data WHERE kind='call' AND dst_func_id IS NOT NULL").fetchone()[0]
    by_step = dict(con.execute("SELECT step, COUNT(*) FROM fcall_data WHERE kind='call' AND dst_func_id IS NULL "
                               "GROUP BY step ORDER BY 2 DESC LIMIT 6").fetchall())
    nf, nd = con.execute("SELECT COUNT(*), COUNT(DISTINCT fd.file_path || char(10) || f.func_name) "
                         "FROM function_data f JOIN file_data fd ON f.file_id = fd.id").fetchone()
    con.close()
    return {"call_rows": tot, "resolved_share": round(res / tot, 4) if tot else None,
            "unresolved_by_step": by_step, "functions": nf,
            "node_merge_rate": round(1 - nd / nf, 4) if nf else None}


def cmd_score(a) -> int:
    import acc_eval as A
    import acc2_eval as A2
    state = json.loads(STATE.read_text())
    res = {}
    for key, rec in state.items():
        lang = rec.get("language")
        if lang not in a.langs or rec.get("scan") not in ("ok", "cached"):
            continue
        t0 = time.time()
        rows, edges, kinds = A2.resolved(STUDY, key, lang)
        try:
            orc = {"python": _py_oracle, "go": _go_oracle, "java": _java_oracle,
                   "c": lambda s, k: A.oracle_c(s, k)}[lang](STUDY, key)
        except Exception as e:
            res[key] = {**rec, "evaluable": False, "error": f"{type(e).__name__}: {e}"[:300],
                        "profile": _profile(STUDY, key, lang)}
            print(f"{key}: oracle raised: {e}"[:200], flush=True)
            continue
        if not orc["direct"] and not orc["dynamic"]:
            res[key] = {**rec, "evaluable": False, "error": str(orc.get("err"))[:300],
                        "profile": _profile(STUDY, key, lang)}
            print(f"{key}: oracle produced no edges: {str(orc.get('err'))[:150]}", flush=True)
            continue
        m = A2.matcher(rows, lang)
        mapped = {k: {(m(x), m(y)) for x, y in orc[k]} for k in ("direct", "dynamic")}
        nodes = {(r["file"], fid) for fid, r in rows.items()}
        cmp_ = A.compare(nodes, edges, {}, {k: {(x, y) for x, y in mapped[k] if x and y} for k in mapped},
                         use_line=False)
        res[key] = {**rec, "evaluable": True, **cmp_, "engine_funcs": len(rows), "engine_edges": len(edges),
                    "oracle_direct": len(orc["direct"]), "oracle_dynamic": len(orc["dynamic"]),
                    "profile": _profile(STUDY, key, lang), "secs": round(time.time() - t0, 1)}
        print(f"{key}: scored in {res[key]['secs']}s", flush=True)
    (DOCS_DIR / "accp_result.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"-> {DOCS_DIR / 'accp_result.json'}: {sum(1 for v in res.values() if v.get('evaluable'))}/{len(res)} evaluable")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--langs", nargs="+", default=list(RUNNABLE))
    p.set_defaults(fn=cmd_prep)
    s = sub.add_parser("score")
    s.add_argument("--langs", nargs="+", default=list(RUNNABLE))
    s.set_defaults(fn=cmd_score)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
