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
                   "c": c_oracle}[lang](STUDY, key)
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
        cov = ({"parse_clean": orc["parse_clean"], "parse_total": orc["parse_total"],
                "makefile": orc.get("makefile"), "build_flags": orc.get("build_flags")}
               if "parse_clean" in orc else {})
        res[key] = {**rec, "evaluable": True, **cmp_, **cov, "engine_funcs": len(rows), "engine_edges": len(edges),
                    "oracle_direct": len(orc["direct"]), "oracle_dynamic": len(orc["dynamic"]),
                    "profile": _profile(STUDY, key, lang), "secs": round(time.time() - t0, 1)}
        print(f"{key}: scored in {res[key]['secs']}s", flush=True)
    out = DOCS_DIR / "accp_result.json"
    prev = json.loads(out.read_text()) if out.exists() else {}   # merge: a per-language run must not
    prev.update(res)                                             # discard the languages scored before it
    res = prev
    out.write_text(json.dumps(res, indent=1, default=str))
    print(f"-> {DOCS_DIR / 'accp_result.json'}: {sum(1 for v in res.values() if v.get('evaluable'))}/{len(res)} evaluable")
    return 0


# ============================================================================ diagnostics (Amendment 11)
# None of these is part of the gate. Each has a verdict independent of agreement, and each is reported
# whichever way it goes. Thresholds were fixed in the amendment text before any of this ran.

def d1_parse_coverage(key="khronosgroup__vulkan-loader@2021Q4"):
    """D1: did libclang actually parse vulkan-loader? Threshold: fatal-diagnostic-free parses on < 80% of the
    .c files the engine scanned means the comparison was invalid rather than unfavourable."""
    import sqlite3
    sys.path.insert(0, str(next((STUDY / "venv" / "lib").glob("python3*/site-packages"))))
    import clang.cindex as ci
    root = STUDY / "repos" / key
    db = sorted((STUDY / "engine" / key).glob("*_galaxy_master.db"))[0]
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    engine_c = {r[0] for r in con.execute("SELECT file_path FROM file_data WHERE file_path LIKE '%.c'")}
    engine_funcs = con.execute("SELECT COUNT(*) FROM function_data").fetchone()[0]
    con.close()
    incs = sorted({str(p.parent) for p in root.rglob("*.h")})[:300]
    args = ["-x", "c", "-std=gnu11", f"-I{root}", *[f"-I{d}" for d in incs]]
    idx = ci.Index.create()
    files = sorted(root.rglob("*.c"))
    clean, fatal, defs, errs = 0, 0, 0, {}
    for f in files:
        try:
            tu = idx.parse(str(f), args=args)
        except ci.TranslationUnitLoadError:
            fatal += 1
            errs["TranslationUnitLoadError"] = errs.get("TranslationUnitLoadError", 0) + 1
            continue
        bad = [d for d in tu.diagnostics if d.severity >= 3]
        if bad:
            fatal += 1
            k = bad[0].spelling[:70]
            errs[k] = errs.get(k, 0) + 1
        else:
            clean += 1
        defs += sum(1 for c in tu.cursor.get_children()
                    if c.kind == ci.CursorKind.FUNCTION_DECL and c.is_definition())
    cov = clean / len(engine_c) if engine_c else None
    return {"diagnostic": "D1 libclang parse coverage", "repo": key, "oracle_c_files": len(files),
            "engine_c_files": len(engine_c), "parsed_clean": clean, "parsed_with_errors": fatal,
            "oracle_functions_defined": defs, "engine_functions": engine_funcs,
            "clean_share_of_engine_c_files": round(cov, 4) if cov is not None else None,
            "threshold": 0.80, "verdict": ("COMPARISON INVALID (coverage below the 80% threshold)"
                                           if cov is not None and cov < 0.80 else
                                           "coverage adequate — the failure stands as measured"),
            "top_errors": dict(sorted(errs.items(), key=lambda x: -x[1])[:5])}


def d2_java_build():
    """D2: can either Java repo's late snapshot be built to a jar with a fixed, recorded invocation?"""
    out = []
    for key in [k for k, v in json.loads(STATE.read_text()).items()
                if v.get("language") == "java" and v.get("which") == "late"]:
        root = STUDY / "repos" / key
        rec = {"repo": key, "has_pom": (root / "pom.xml").exists(),
               "has_gradle": any((root / f).exists() for f in ("gradlew", "build.gradle", "build.gradle.kts"))}
        cmd = None
        if rec["has_pom"]:
            cmd = ["mvn", "-B", "-DskipTests", "-Drat.skip=true", "-Djacoco.skip=true",
                   "-Dmaven.javadoc.skip=true", "-Dcheckstyle.skip", "-Dspotbugs.skip", "-Dpmd.skip", "package"]
        elif (root / "gradlew").exists():
            cmd = ["./gradlew", "--no-daemon", "-x", "test", "jar"]
        if cmd is None:
            rec["verdict"] = "no build file at this snapshot — not evaluable by build failure"
            out.append(rec)
            continue
        rec["command"] = " ".join(cmd)
        try:
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=2700)
            rec["rc"] = p.returncode
            rec["tail"] = (p.stdout + p.stderr)[-400:]
        except subprocess.TimeoutExpired:
            rec["rc"] = "timeout(45m)"
        jars = [str(j.relative_to(root)) for j in list(root.rglob("target/*.jar")) + list(root.rglob("build/libs/*.jar"))
                if "sources" not in j.name and "javadoc" not in j.name and "tests" not in j.name]
        rec["jars"] = jars[:5]
        rec["verdict"] = "BUILDABLE" if jars else "not evaluable by build failure"
        out.append(rec)
    return {"diagnostic": "D2 offline-safe Java build", "repos": out}


def d3_syzkaller_cgo(key="google__syzkaller@2026Q4"):
    """D3: does ./... minus the packages that import C yield a callgraph?"""
    root = (STUDY / "repos" / key).resolve()
    env = {**{k: v for k, v in os.environ.items() if k != "GOFLAGS"},
           "GOPATH": str(STUDY / "gopath"), "GOMODCACHE": str(STUDY / "gopath/pkg/mod"),
           "GOTOOLCHAIN": "auto", "PATH": f"{STUDY}/go/bin:{STUDY}/gopath/bin:{os.environ['PATH']}"}
    subprocess.run(["go", "mod", "download"], cwd=root, env=env, capture_output=True, text=True, timeout=3600)
    lst = subprocess.run(["go", "list", "-e", "-f", "{{.ImportPath}}\t{{len .CgoFiles}}", "./..."],
                         cwd=root, env=env, capture_output=True, text=True, timeout=1800)
    keep, cgo = [], []
    for line in lst.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        (cgo if parts[1].strip() not in ("0", "") else keep).append(parts[0])
    if not keep:
        return {"diagnostic": "D3 syzkaller minus cgo", "repo": key, "packages_kept": 0,
                "cgo_packages": len(cgo), "verdict": "go list produced no packages",
                "stderr": lst.stderr[-300:]}
    fmt = "{{posn .Caller}}\t{{posn .Callee}}\t{{.Caller.Name}}\t{{.Callee.Name}}"
    p = subprocess.run(["callgraph", "-algo=static", f"-format={fmt}", *keep], cwd=root, env=env,
                       capture_output=True, text=True, timeout=7200)
    rs = str(root)
    edges = sum(1 for ln in p.stdout.splitlines() if ln.count(rs) >= 2)
    return {"diagnostic": "D3 syzkaller minus cgo", "repo": key, "packages_kept": len(keep),
            "cgo_packages": len(cgo), "in_repo_edges": edges, "rc": p.returncode,
            "verdict": ("SCOPING WORKS — record as a per-repo deviation" if edges > 0 else
                        "still no callgraph"), "stderr": p.stderr[-300:]}


def cmd_diag(a) -> int:
    res = {}
    for name, fn in (("D1", d1_parse_coverage), ("D2", d2_java_build), ("D3", d3_syzkaller_cgo)):
        if name not in a.only:
            continue
        print(f"== {name}", flush=True)
        try:
            res[name] = fn()
        except Exception as e:
            res[name] = {"diagnostic": name, "error": f"{type(e).__name__}: {e}"[:400]}
        print(json.dumps(res[name], indent=1)[:1200], flush=True)
    out = DOCS_DIR / "accp_diagnostics.json"
    prev = json.loads(out.read_text()) if out.exists() else {}
    prev.update(res)
    out.write_text(json.dumps(prev, indent=1, default=str))
    return 0


# ============================================================================ C oracle, per the registration
# ACC's Data table specifies: "compile flags from the repo's build where it can generate them without cmake
# (redis `make` dry-run), else -I heuristics". acc_eval.oracle_c implements only the fallback, which is why
# D1 found 0 cleanly parsed translation units in ACC's own repos. This implements the primary path. It also
# supplies the system include dirs, because the pip libclang wheel carries no clang resource headers at all
# (D1's root cause) -- without them even a correct flag set fails on <stddef.h>.
MAKEFILES = ("src/makefile.gnu", "Makefile", "makefile", "src/Makefile", "src/makefile")
SYSINC = ["-isystem", "/usr/lib/gcc/x86_64-linux-gnu/13/include",
          "-isystem", "/usr/include/x86_64-linux-gnu", "-isystem", "/usr/include"]


def c_flags(root: pathlib.Path):
    """(-I/-D/-std flags from a `make -n` dry run, which makefile supplied them)."""
    import re as _re
    for rel in MAKEFILES:
        mk = root / rel
        if not mk.exists():
            continue
        try:
            dry = subprocess.run(["make", "-n", "-f", mk.name], cwd=mk.parent, capture_output=True,
                                 text=True, timeout=300).stdout
        except subprocess.TimeoutExpired:
            continue
        flags = set()
        for ln in dry.splitlines():
            if " -c " in ln or _re.search(r"\b(gcc|cc|clang)\b", ln):
                for tok in ln.split():
                    if tok.startswith(("-I", "-D", "-std=")):
                        flags.add(tok)
        if not flags:
            continue
        out = []
        for f in sorted(flags):
            if f.startswith("-I") and not f[2:].startswith("/"):
                out.append("-I" + str((mk.parent / f[2:]).resolve()))
            else:
                out.append(f)
        return out, rel
    return [], None


def c_oracle(study, key):
    """libclang with build-derived flags. Same edge rule as acc_eval.oracle_c: a CallExpr whose referenced
    decl is a FunctionDecl defined in the repo; call sites with no referenced decl counted as indirect."""
    sys.path.insert(0, str(next((study / "venv" / "lib").glob("python3*/site-packages"))))
    import clang.cindex as ci
    root = (study / "repos" / key).resolve()
    built, mk = c_flags(root)
    incs = sorted({str(p.parent) for p in root.rglob("*.h")})[:300]
    args = ["-x", "c", "-std=gnu11", f"-I{root}", *[f"-I{d}" for d in incs], *built, *SYSINC]
    idx = ci.Index.create()
    defs, calls, indirect, direct_sites, clean, tot = {}, [], 0, 0, 0, 0
    for f in sorted(root.rglob("*.c")):
        tot += 1
        try:
            tu = idx.parse(str(f), args=args)
        except ci.TranslationUnitLoadError:
            continue
        if not [d for d in tu.diagnostics if d.severity >= 3]:
            clean += 1

        def walk(cur, fn):
            nonlocal indirect, direct_sites
            for c in cur.get_children():
                if (c.location.file and pathlib.Path(str(c.location.file.name)).resolve() != f
                        and c.kind != ci.CursorKind.CALL_EXPR):
                    continue
                if c.kind == ci.CursorKind.FUNCTION_DECL and c.is_definition():
                    try:
                        rel = str(pathlib.Path(str(c.location.file.name)).resolve().relative_to(root))
                    except ValueError:
                        continue
                    defs[c.get_usr()] = (rel, c.spelling, c.extent.start.line)
                    walk(c, c.get_usr())
                    continue
                if c.kind == ci.CursorKind.CALL_EXPR and fn:
                    ref = c.referenced
                    if ref is not None and ref.kind == ci.CursorKind.FUNCTION_DECL:
                        calls.append((fn, ref.get_usr()))
                        direct_sites += 1
                    else:
                        indirect += 1
                walk(c, fn)
        walk(tu.cursor, None)
    edges = {(defs[a], defs[b]) for a, b in calls if a in defs and b in defs and a != b}
    return {"direct": edges, "dynamic": set(), "indirect_sites": indirect, "direct_sites": direct_sites,
            "parse_clean": clean, "parse_total": tot, "makefile": mk, "build_flags": built}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--langs", nargs="+", default=list(RUNNABLE))
    p.set_defaults(fn=cmd_prep)
    s = sub.add_parser("score")
    s.add_argument("--langs", nargs="+", default=list(RUNNABLE))
    s.set_defaults(fn=cmd_score)
    d = sub.add_parser("diag")
    d.add_argument("--only", nargs="+", default=["D1", "D2", "D3"])
    d.set_defaults(fn=cmd_diag)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
