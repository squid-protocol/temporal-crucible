#!/usr/bin/env python3
"""Self-checks for the evolution report: does the report agree with git, does it reconcile, did the scan see the code, and how does GitGalaxy's call graph compare with an
independent tree-sitter name-matching baseline on this repository's own latest snapshot. Pure checks: nothing here changes a figure; it adds a "how far to trust" table and warnings."""
import collections
import io
import posixpath
import re
import sqlite3
import subprocess
import tarfile
from concurrent.futures import ProcessPoolExecutor

EXTS = {"c": (".c", ".h", ".cc", ".cpp", ".hpp"), "go": (".go",), "python": (".py",), "rust": (".rs",)}
TS_LANG = {".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp", ".go": "go", ".py": "python", ".rs": "rust"}
# Names the scanner skips by default (gitgalaxy_config.IGNORED_DIRECTORIES) that are also ordinary source-directory names (engine issue #8708).
AMBIGUOUS_SKIPPED = {"log", "logs", "tmp", "temp", "docs", "DOCS", "classes", "target", "build", "_build", "dist", "obj", "site", "legal", "license", "licenses", "LICENSE", "LICENSES"}
# Vendored and dependency directories the scanner leaves out on purpose (by name or by evidence); not held against the scan.
VENDORED = {"third_party", "thirdparty", "3rdparty", "3rd_party", "third-party", "3rd-party", "vendor", "vendored", "node_modules", "bower_components", "jspm_packages", "Pods", "Carthage", ".git", "__pycache__", "venv", ".venv", "site-packages"}
# Standing ratings measured in the research on the engine gate's pinned repositories against compiler-grade references (docs/sensor-overhaul/sensors/reach_vs_treesitter.md):
# cross-file call edges, the strict set `gitgalaxy reach` counts. Not measured on the repository shown.
STANDING = {
    "c": {"reference": "libclang", "precision": 0.89, "recall": 0.70, "tree_sitter_recall": 0.83, "note": "6 valid C repositories; 61% recall on 7 small repositories with libclang gaps"},
    "python": {"reference": "pyan3", "precision": 0.53, "recall": 0.65, "tree_sitter_recall": 0.48, "note": "one to three repositories"},
    "go": {"reference": "golang.org/x/tools VTA", "precision": 0.81, "recall": 0.64, "tree_sitter_recall": 0.64, "note": "one to three repositories"},
    "rust": {"reference": "rust-analyzer", "precision": 0.58, "recall": 0.67, "tree_sitter_recall": 0.63, "note": "one to three repositories"},
}


def git(repo, *a):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else ""


def _name(n, src):
    """Identifier of a function-like node (last component of a qualified name)."""
    node = n
    for _ in range(12):
        if node is None:
            return None
        if node.type in ("identifier", "field_identifier", "type_identifier", "property_identifier"):
            return src[node.start_byte : node.end_byte].decode("utf8", "replace")
        if node.type in ("qualified_identifier", "scoped_identifier"):
            nm = node.child_by_field_name("name")
            node = nm if nm is not None else (node.children[-1] if node.children else None)
            continue
        nxt = node.child_by_field_name("declarator") or node.child_by_field_name("name")
        if nxt is None and node.type in ("parenthesized_declarator",):
            nxt = next((c for c in node.children if c.is_named), None)
        node = nxt
    return None


def _parse(items):
    from tree_sitter_language_pack import get_parser
    parsers = {}
    out = []
    for path, data in items:
        if path == "go.mod":
            continue
        ext = "." + path.rsplit(".", 1)[-1]
        lang = TS_LANG.get(ext)
        if not lang:
            continue
        p = parsers.get(lang) or parsers.setdefault(lang, get_parser(lang))
        tree = p.parse(data)
        defs, calls = [], collections.defaultdict(set)
        stack = [(tree.root_node, None)]
        while stack:
            n, fn = stack.pop()
            t = n.type
            if t in ("function_definition", "function_declaration", "method_declaration", "function_item"):
                d = n.child_by_field_name("declarator") if lang in ("c", "cpp") else n
                nm = _name(d, data) if lang in ("c", "cpp") else _name(n.child_by_field_name("name"), data)
                if nm:
                    defs.append(nm)
                    fn = nm
            elif t in ("call_expression", "call") and fn:
                f = n.child_by_field_name("function")
                cn = None
                if f is not None:
                    if f.type in ("identifier", "scoped_identifier", "qualified_identifier"):
                        cn = _name(f, data)
                    elif f.type in ("field_expression", "selector_expression", "attribute", "member_expression"):
                        fld = f.child_by_field_name("field") or f.child_by_field_name("attribute")
                        cn = _name(fld, data) if fld is not None else None
                if cn:
                    calls[fn].add(cn)
            for c in n.children:
                stack.append((c, fn))
        out.append((path, defs, {k: sorted(v) for k, v in calls.items()}))
    return out


def read_items(repo, commit, lang):
    """(path, bytes) of every source file of the language at the commit, from one git archive."""
    exts = EXTS[lang]
    raw = subprocess.run(["git", "-C", repo, "archive", "--format=tar", commit], capture_output=True).stdout
    items = []
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        for m in tf:
            if m.isfile() and (m.name.endswith(exts) or m.name == "go.mod") and m.size < 2_000_000:
                items.append((m.name, tf.extractfile(m).read()))
    return items


def tree_sitter_baseline(items, db, lang):
    """Compare the scan database with a tree-sitter name-matching baseline at the same commit: function definitions, call edges between functions, cross-file edges."""
    if not items:
        return None
    chunks = [items[i : i + 150] for i in range(0, len(items), 150)]
    parsed = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(_parse, chunks):
            parsed += r
    scanned_paths = set()
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {i: p for i, p in con.execute("SELECT id, file_path FROM file_data")}
    gg_funcs = {(files[f], n.split("::")[-1]) for f, n in con.execute("SELECT file_id, func_name FROM function_data") if f in files}
    ids = {}
    for fid, f, n in con.execute("SELECT id, file_id, func_name FROM function_data"):
        if f in files:
            ids[fid] = (files[f], n.split("::")[-1])
    gg_edges = set()
    for s, d in con.execute("SELECT src_func_id, dst_func_id FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL AND COALESCE(candidates, 1) <= 1"):
        if s in ids and d in ids and ids[s] != ids[d]:
            gg_edges.add((ids[s], ids[d]))
    con.close()
    scanned_paths = set(files.values())
    ts_defs = set()
    defs_by_name = collections.defaultdict(list)
    for path, defs, _ in parsed:
        if path not in scanned_paths:
            continue  # a file the scan did not read (see the coverage check) cannot be held against the call graph
        for d in set(defs):
            ts_defs.add((path, d))
            defs_by_name[d].append(path)
    ts_edges, ambiguous = set(), 0
    for path, _, calls in parsed:
        if path not in scanned_paths:
            continue
        for fn, cs in calls.items():
            for c in cs:
                cand = defs_by_name.get(c, [])
                if len(cand) == 1:
                    tgt = cand[0]
                elif path in cand and cand.count(path) == 1:
                    tgt = path
                else:
                    ambiguous += bool(cand)
                    continue
                if (path, fn) != (tgt, c):
                    ts_edges.add(((path, fn), (tgt, c)))
    ts_fn = {k for k in ts_defs}
    both_fn = gg_funcs & ts_fn
    # edges compared on functions both sides know, so a missing definition is not counted twice
    gg_e = {e for e in gg_edges if e[0] in ts_fn and e[1] in ts_fn}
    ts_e = {e for e in ts_edges if e[0] in gg_funcs and e[1] in gg_funcs}
    inter = gg_e & ts_e
    fp_gg = {(a[0], b[0]) for a, b in gg_e if a[0] != b[0]}
    fp_ts = {(a[0], b[0]) for a, b in ts_e if a[0] != b[0]}
    sets = {"ts_edges": ts_e, "gg_edges": gg_e, "gg_funcs": gg_funcs}
    return {
        "_sets": sets,
        "functions": {"tree_sitter": len(ts_fn), "gitgalaxy": len(gg_funcs & {k for k in ts_fn} | (gg_funcs - ts_fn)), "both": len(both_fn), "recall": len(both_fn) / max(len(ts_fn), 1), "precision": len(both_fn) / max(len(gg_funcs), 1)},
        "edges": {"baseline": len(ts_e), "gitgalaxy": len(gg_e), "both": len(inter), "recall": len(inter) / max(len(ts_e), 1), "precision": len(inter) / max(len(gg_e), 1), "ambiguous_calls_skipped_by_baseline": ambiguous},
        "file_pairs": {"baseline": len(fp_ts), "gitgalaxy": len(fp_gg), "both": len(fp_gg & fp_ts), "recall": len(fp_gg & fp_ts) / max(len(fp_ts), 1), "precision": len(fp_gg & fp_ts) / max(len(fp_gg), 1)},
        "files_parsed": len(parsed),
    }


INC = re.compile(rb'^[ \t]*#[ \t]*include[ \t]*([<"])([^>"\n]+)[>"]', re.M)
PYIMP = re.compile(rb"^[ \t]*(?:from[ \t]+([.\w]+)[ \t]+import[ \t]+([\w, *]+)|import[ \t]+([\w., ]+))", re.M)


GO_BLOCK = re.compile(rb"import[ \t]*\((.*?)\)", re.S)
GO_LINE = re.compile(rb'^[ \t]*(?:[\w.]+[ \t]+)?"([^"\n]+)"', re.M)
GO_SINGLE = re.compile(rb'^[ \t]*import[ \t]+(?:[\w.]+[ \t]+)?"([^"\n]+)"', re.M)


def _gg_file_edges(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {i: p for i, p in con.execute("SELECT id, file_path FROM file_data")}
    gg = {(files[a], files[b]) for a, b in con.execute("SELECT src_file_id, dst_file_id FROM edge_data WHERE edge_kind = 'import'") if a in files and b in files and files[a] != files[b]}
    con.close()
    return gg, set(files.values())


def _go_imports(items, db, module=None):
    """Go imports are package-level: compare the pairs (importing directory, imported directory) inside the module with the scan's file edges mapped to directories."""
    paths = [p for p, _ in items if p.endswith(".go")]
    gm = dict(items).get("go.mod")
    mm = re.search(rb"^module[ \t]+(\S+)", gm or b"", re.M)
    if not paths or not mm:
        return None
    mod = mm.group(1).decode()
    go_items = [(p, d) for p, d in items if p.endswith(".go")]
    return _go_compare(go_items, db, {posixpath.dirname(p) for p in paths}, mod)


def _go_compare(items, db, dirs, mod):
    edges = set()
    prefix = mod
    for path, data in items:
        imps = [m for b in GO_BLOCK.findall(data) for m in GO_LINE.findall(b)] + GO_SINGLE.findall(data)
        for imp in imps:
            ip = imp.decode("utf8", "replace")
            if prefix and (ip == prefix or ip.startswith(prefix + "/")):
                d = ip[len(prefix) :].lstrip("/")
            else:
                continue
            if d in dirs and d != posixpath.dirname(path):
                edges.add((posixpath.dirname(path), d))
    gg, scanned = _gg_file_edges(db)
    pset = {p for p, _ in items}
    gg_d = {(posixpath.dirname(a), posixpath.dirname(b)) for a, b in gg if a in pset and b in pset and posixpath.dirname(a) != posixpath.dirname(b)}
    scanned_dirs = {posixpath.dirname(p) for p in scanned}
    b_d = {e for e in edges if e[0] in scanned_dirs and e[1] in scanned_dirs}
    both = gg_d & b_d
    return {"level": "package (directory) pairs", "baseline": len(b_d), "gitgalaxy": len(gg_d), "both": len(both), "recall": len(both) / max(len(b_d), 1), "precision": len(both) / max(len(gg_d), 1), "gitgalaxy_only_examples": [{"from": a, "to": b} for a, b in sorted(gg_d - b_d)[:3]]}


RS_MOD = re.compile(rb"^[ \t]*(?:pub(?:\([^)]*\))?[ \t]+)?mod[ \t]+(\w+)[ \t]*;", re.M)
RS_USE = re.compile(rb"^[ \t]*(?:pub(?:\([^)]*\))?[ \t]+)?use[ \t]+(\w+)::([\w:]*)", re.M)


def _rust_imports(items, db, repo_files=None):
    """Rust: `mod x;` declarations and `use crate::a::b` paths resolved to files, and `use other_crate::...` to that crate's lib.rs; compared with the scan's file edges."""
    d = dict(items)
    pset = set(d)
    crates = {}  # crate ident -> src dir
    for p, data in items:
        pass
    edges = set()
    for p, data in items:
        base = posixpath.dirname(p) if posixpath.basename(p) in ("lib.rs", "main.rs", "mod.rs") else posixpath.dirname(p) + "/" + posixpath.basename(p)[:-3]
        for m in RS_MOD.findall(data):
            nm = m.decode()
            for cand in (f"{base}/{nm}.rs", f"{base}/{nm}/mod.rs"):
                if cand in pset:
                    edges.add((p, cand))
                    break
    # crate roots: any directory with a src/lib.rs or src/main.rs; the crate ident is the directory name with - as _
    roots = {}
    for p in pset:
        if p.endswith("/src/lib.rs") or p == "src/lib.rs":
            cdir = p[: -len("/src/lib.rs")] if p != "src/lib.rs" else ""
            roots[(cdir.split("/")[-1] or "crate").replace("-", "_")] = p
    for p, data in items:
        src_root = p.split("/src/")[0] + "/src" if "/src/" in p else ("src" if p.startswith("src/") else posixpath.dirname(p))
        for first, rest in RS_USE.findall(data):
            f = first.decode()
            segs = [x for x in rest.decode().split("::") if x]
            if f == "crate":
                cur = src_root
                tgt = None
                for sg in segs:
                    if f"{cur}/{sg}.rs" in pset:
                        tgt = f"{cur}/{sg}.rs"
                        break
                    if f"{cur}/{sg}/mod.rs" in pset:
                        tgt = f"{cur}/{sg}/mod.rs"
                        break
                    cur = f"{cur}/{sg}"
                if tgt and tgt != p:
                    edges.add((p, tgt))
            elif f in roots and roots[f] != p:
                edges.add((p, roots[f]))
    gg, scanned = _gg_file_edges(db)
    gg_c = {e for e in gg if e[0] in pset and e[1] in pset}
    b_c = {e for e in edges if e[0] in scanned and e[1] in scanned}
    both = gg_c & b_c
    return {"level": "files", "baseline": len(b_c), "gitgalaxy": len(gg_c), "both": len(both), "recall": len(both) / max(len(b_c), 1), "precision": len(both) / max(len(gg_c), 1), "gitgalaxy_only_examples": [{"from": a, "to": b} for a, b in sorted(gg_c - b_c)[:3]]}


def import_baseline(items, db, lang):
    """File-to-file import edges: each #include (C family) or import (Python) that names exactly one file of the repository, against the scan's import edges."""
    if lang == "go":
        return _go_imports(items, db)
    if lang == "rust":
        return _rust_imports(items, db, repo_files=None)
    if lang not in ("c", "python") or not items:
        return None
    allp = [p for p, _ in items]
    pset = set(allp)
    base = {}
    ambiguous = 0
    edges = set()
    if lang == "c":
        by_tail = collections.defaultdict(list)
        for p in allp:
            parts = p.split("/")
            for i in range(len(parts)):
                by_tail["/".join(parts[i:])].append(p)
        for path, data in items:
            for kind, name in INC.findall(data):
                nm = name.decode("utf8", "replace").strip()
                tgt = None
                if kind == b'"':
                    cand = posixpath.normpath(posixpath.join(posixpath.dirname(path), nm))
                    if cand in pset:
                        tgt = cand
                if tgt is None:
                    c = by_tail.get(nm, [])
                    if len(c) == 1:
                        tgt = c[0]
                    elif len(c) > 1:
                        ambiguous += 1
                if tgt and tgt != path:
                    edges.add((path, tgt))
    else:
        mod = collections.defaultdict(set)
        for p in allp:
            stem = p[:-3]
            dotted = stem.replace("/", ".")
            if stem.endswith("/__init__"):
                dotted = stem[: -len("/__init__")].replace("/", ".")
            parts = dotted.split(".")
            for i in range(len(parts)):
                mod[".".join(parts[i:])].add(p)

        def look(m):
            c = mod.get(m, set())
            return next(iter(c)) if len(c) == 1 else (None if not c else "AMBIG")
        for path, data in items:
            here = posixpath.dirname(path)
            for frm, names, imp in PYIMP.findall(data):
                cands = []
                if imp:
                    cands = [x.strip().split(" as ")[0].strip() for x in imp.decode("utf8", "replace").split(",")]
                else:
                    f = frm.decode("utf8", "replace")
                    if f.startswith("."):
                        up = len(f) - len(f.lstrip("."))
                        base_dir = here
                        for _ in range(up - 1):
                            base_dir = posixpath.dirname(base_dir)
                        rest = f.lstrip(".")
                        cands = [(base_dir + "/" + rest.replace(".", "/") if rest else base_dir)]
                        for nm in [x.strip().split(" as ")[0] for x in names.decode("utf8", "replace").split(",")]:
                            cands.append((base_dir + "/" + (rest.replace(".", "/") + "/" if rest else "") + nm))
                        for cdir in cands:
                            for t in (cdir + ".py", cdir + "/__init__.py"):
                                if t in pset and t != path:
                                    edges.add((path, t))
                                    break
                        continue
                    cands = [f] + [f + "." + x.strip().split(" as ")[0] for x in names.decode("utf8", "replace").split(",")]
                for c in cands:
                    r = look(c)
                    if r == "AMBIG":
                        ambiguous += 1
                    elif r and r != path:
                        edges.add((path, r))
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {i: p for i, p in con.execute("SELECT id, file_path FROM file_data")}
    gg = {(files[a], files[b]) for a, b in con.execute("SELECT src_file_id, dst_file_id FROM edge_data WHERE edge_kind = 'import'") if a in files and b in files and files[a] != files[b]}
    con.close()
    parsed = set(allp)
    gg_c = {e for e in gg if e[0] in parsed and e[1] in parsed}
    b_c = {e for e in edges if e[0] in set(files.values()) and e[1] in set(files.values())}
    both = gg_c & b_c
    return {"baseline": len(b_c), "gitgalaxy": len(gg_c), "both": len(both), "recall": len(both) / max(len(b_c), 1), "precision": len(both) / max(len(gg_c), 1), "ambiguous_includes_skipped_by_baseline": ambiguous, "gitgalaxy_only_examples": [{"from": a, "to": b} for a, b in sorted(gg_c - b_c)[:3]]}


def libclang_reference(repo, commit, db, python_exe, adapter, base=None, cache_dir=None, timeout=3000):
    """Compare the scan with libclang's resolved call graph for the same commit (compiler-grade reference, C only). Uses the engine's own adapter (tests/tools/clang_callgraph.py): each .c file one translation unit,
    every header directory an include path, no build system, so files that need generated headers may not parse; the share of files libclang parsed is reported and bounds what the comparison means."""
    import json as _json
    import os
    import tempfile
    cache = os.path.join(cache_dir, f"clang_{commit[:12]}.json") if cache_dir else None
    contract = None
    if cache and os.path.exists(cache):
        contract = _json.load(open(cache))
    if contract is None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = subprocess.run(["git", "-C", repo, "archive", "--format=tar", commit], capture_output=True).stdout
            with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
                tf.extractall(tmp, filter="data")
            r = subprocess.run([python_exe, adapter, tmp, "c"], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"error": (r.stderr or "libclang adapter failed")[-300:]}
        contract = _json.loads(r.stdout)
        if cache:
            os.makedirs(cache_dir, exist_ok=True)
            _json.dump(contract, open(cache, "w"))
    ref_defs = {(d[0], d[1]) for d in contract["defs"]}
    ref_edges = {((e[0][0], e[0][1]), (e[1][0], e[1][1])) for e in contract["edges"] if (e[0][0], e[0][1]) != (e[1][0], e[1][1])}
    kinds = {((k[0][0], k[0][1]), (k[1][0], k[1][1])): k[2] for k in contract.get("edge_kinds", [])}
    n_files, fatal = contract["files"], set(contract["fatal"])
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {i: p for i, p in con.execute("SELECT id, file_path FROM file_data")}
    ids = {fid: (files[f], n) for fid, f, n in con.execute("SELECT id, file_id, func_name FROM function_data") if f in files}
    gg_funcs = set(ids.values())
    gg_edges = set()
    for sid, did in con.execute("SELECT src_func_id, dst_func_id FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL AND COALESCE(candidates, 1) <= 1"):
        if sid in ids and did in ids and ids[sid] != ids[did]:
            gg_edges.add((ids[sid], ids[did]))
    scanned = set(files.values())
    con.close()
    ref_defs = {d for d in ref_defs if d[0] in scanned}  # files the scan did not read (vendored, skipped) are the coverage check's business, not the call graph's
    ref_edges = {e for e in ref_edges if e[0][0] in scanned and e[1][0] in scanned}
    scope_fn = ref_defs & gg_funcs
    both_fn = scope_fn
    ref_e = {e for e in ref_edges if e[0] in gg_funcs and e[1] in gg_funcs}
    gg_e = {e for e in gg_edges if e[0] in ref_defs and e[1] in ref_defs}
    inter = ref_e & gg_e
    macro = {e for e in ref_e if kinds.get(e) == "macro"}
    gg_files = {p for p, _ in gg_funcs}
    ref_files = {p for p, _ in ref_defs}
    covered = len(gg_files & ref_files) / max(len(gg_files), 1)  # files where the scan found functions and libclang found at least one too
    out = {"reference": "libclang 18", "files_total": n_files, "files_failed": len(fatal), "files_with_fatal_error": len(fatal), "parsed_share": covered,
           "functions": {"reference": len(ref_defs), "gitgalaxy": len(gg_funcs), "both": len(both_fn), "recall": len(both_fn) / max(len(ref_defs), 1), "precision": len(both_fn) / max(len(gg_funcs), 1)},
           "edges": {"reference": len(ref_e), "gitgalaxy": len(gg_e), "both": len(inter), "recall": len(inter) / max(len(ref_e), 1), "precision": len(inter) / max(len(gg_e), 1)},
           "macro_hidden": {"reference": len(macro), "gitgalaxy_found": len(macro & gg_e)}}
    if base and "_sets" in base:
        ts_e = base["_sets"]["ts_edges"]
        out["name_matcher"] = {"recall_vs_libclang": len(ref_e & ts_e) / max(len(ref_e), 1), "precision_vs_libclang": len(ref_e & ts_e) / max(len(ts_e), 1)}
        out["macro_hidden"]["name_matcher_found"] = len(macro & ts_e)
    return out


def scan_coverage(repo, commit, db, lang):
    """Code files in the repository at the scanned commit that the scan did not read, grouped by directory, and whether the directory name is on the scanner's default ignore list."""
    exts = EXTS[lang]
    tree = [f for f in git(repo, "ls-tree", "-r", "--name-only", commit).splitlines() if f.endswith(exts)]
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    seen = {p for (p,) in con.execute("SELECT file_path FROM file_data")}
    excl = {p for (p,) in con.execute("SELECT file_path FROM excluded_artifacts")} if con.execute("SELECT name FROM sqlite_master WHERE name='excluded_artifacts'").fetchone() else set()
    con.close()
    missing = [f for f in tree if f not in seen and f not in excl]
    vend = [f for f in missing if any(p in VENDORED for p in f.split("/")[:-1])]
    unexp = [f for f in missing if f not in set(vend)]
    by = collections.Counter()
    for f in unexp:
        by["/".join(f.split("/")[:-1][:3]) or "."] += 1
    amb = {k for k in by if any(p in AMBIGUOUS_SKIPPED for p in k.split("/"))}
    return {"code_files": len(tree), "scanned": len(tree) - len(missing), "recorded_excluded": sum(1 for f in tree if f in excl), "missing": len(missing), "vendored_on_purpose": len(vend), "unexplained": len(unexp), "top_missing": [{"directory": k, "files": v, "default_ignore_name": k in amb} for k, v in by.most_common(8)]}


def checks(out, internal, repo, scans_commit=None, db=None, lang="c", validate=True, reference=None):
    """The self-check table. Each check: id, what, value, status ('ok', 'warn', 'fail', 'info'), detail."""
    rows = []
    n_git = len([x for x in git(repo, "rev-list", "--no-merges", "HEAD").split("\n") if x])
    rows.append({"id": "commits", "what": "Commit count matches git", "value": f"{out['commits']:,} vs {n_git:,}", "status": "ok" if out["commits"] == n_git else "fail", "detail": "The report's commits are the non-merge commits reachable from HEAD."})
    tot = sum(v["edits"] for v in out["categories"].values())
    rows.append({"id": "reconcile", "what": "Every function edit is in exactly one category", "value": f"{tot:,} of {out['function_edits']:,}", "status": "ok" if tot == out["function_edits"] else "fail", "detail": "The categories partition the function edits; a mismatch means a classification gap."})
    s = sum(out["composition_edits"].values())
    rows.append({"id": "shares", "what": "Work-mix shares add up", "value": f"{s * 100:.1f}%", "status": "ok" if abs(s - 1) < 0.002 else "fail", "detail": "Organic, sweeps, fixes and mechanical."})
    lq = out["label_quality"]
    rows.append({"id": "pairs", "what": "Fixes matched to a cause", "value": f"{out.get('pairs_all', 0):,} pairs", "status": "ok" if out.get("pairs_all", 0) >= 100 else ("warn" if out.get("pairs_all", 0) >= 30 else "fail"), "detail": "Repair timing needs at least 30 pairs (the report hides it below that); 100 or more give stable figures."})
    if validate and db and scans_commit:
        cov = scan_coverage(repo, scans_commit, db, lang)
        miss = cov["unexplained"] / max(cov["code_files"] - cov["vendored_on_purpose"], 1)
        rows.append({"id": "coverage", "what": "Code files the scan read", "value": f"{cov['scanned']:,} of {cov['code_files']:,} code files" + (f"; {cov['vendored_on_purpose']:,} vendored on purpose, {cov['unexplained']:,} unexplained" if cov["missing"] else ""), "status": "ok" if miss < 0.02 else ("warn" if miss < 0.1 else "fail"), "detail": (f"Not read and not vendored: {cov['unexplained']:,} files, largest groups " + ", ".join(f"{d['directory']} ({d['files']})" + (" [directory name is on the scanner's default ignore list, #8708]" if d["default_ignore_name"] else "") for d in cov["top_missing"][:4]) if cov["unexplained"] else "Every code file at the scanned commit is in the scan, apart from vendored directories left out on purpose."), "data": cov})
        items = read_items(repo, scans_commit, lang)
        base = tree_sitter_baseline(items, db, lang)
        imp = import_baseline(items, db, lang)
        if imp:
            rows.append({"id": "imports", "what": "Import graph vs a text-and-path baseline", "value": f"GitGalaxy found {imp['recall'] * 100:.0f}% of the baseline's {imp['baseline']:,} edges; {imp['precision'] * 100:.0f}% of its {imp['gitgalaxy']:,} edges are in the baseline", "status": "ok" if imp["recall"] >= 0.9 else ("warn" if imp["recall"] >= 0.75 else "fail"),
                         "detail": ("Baseline at the level of " + imp.get("level", "files") + ": ") + "each include or import that names exactly one target in the repository (relative path first, then a unique match by trailing path; Go: the module path to a package directory; Rust: `mod x;`, `use crate::...` and other workspace crates). Edges only GitGalaxy has are usually includes it resolved among several same-named files (for example " + (f"{imp['gitgalaxy_only_examples'][0]['from']} to {imp['gitgalaxy_only_examples'][0]['to']}" if imp["gitgalaxy_only_examples"] else "none found") + "). No standing research rating exists yet for the import graph.", "data": imp})
        if base:
            f, e, fp = base["functions"], base["edges"], base["file_pairs"]
            rows.append({"id": "functions", "what": "Functions found vs a tree-sitter parse", "value": f"recall {f['recall'] * 100:.0f}%, precision {f['precision'] * 100:.0f}%", "status": "ok" if f["recall"] >= 0.9 else ("warn" if f["recall"] >= 0.75 else "fail"), "detail": f"{f['both']:,} of {f['tree_sitter']:,} function definitions found by a plain parse are in the scan; {f['gitgalaxy'] - f['both']:,} scan functions the parse did not find (macro-generated and renamed forms).", "data": f})
            st = STANDING.get(lang, {})
            rec = e["recall"]
            status = "ok" if rec >= 0.85 else ("warn" if rec >= 0.65 else "fail")
            rows.append({"id": "calls", "what": "Call edges found vs a tree-sitter name-matching baseline", "value": f"GitGalaxy found {rec * 100:.0f}% of the baseline's {e['baseline']:,} edges; {e['precision'] * 100:.0f}% of its {e['gitgalaxy']:,} edges are in the baseline", "status": status,
                         "detail": "Baseline: each call to a name that exactly one function defines (or one in the same file) is an edge; calls through function pointers, fields and macros are not. " + ("GitGalaxy finds fewer of these plain calls because it keeps only edges that resolve to one definition. Treat hub lists, repair radius and call counts as lower bounds." if status != "ok" else "Agreement with this cheap baseline is high; it does not predict agreement with a compiler-grade reference (see the libclang rows when present)."), "data": e})
            rows.append({"id": "filepairs", "what": "Cross-file call pairs (what `gitgalaxy reach` counts)", "value": f"recall {fp['recall'] * 100:.0f}%, precision {fp['precision'] * 100:.0f}% against the baseline", "status": "ok" if fp["recall"] >= 0.85 else ("warn" if fp["recall"] >= 0.65 else "fail"), "detail": "The same comparison at file level.", "data": fp})
            if reference and lang == "c":
                ref = libclang_reference(repo, scans_commit, db, reference["python"], reference["adapter"], base, reference.get("cache_dir"))
                if "error" in ref:
                    rows.append({"id": "cg_error", "what": "Comparison with libclang", "value": "did not run", "status": "info", "detail": ref["error"]})
                else:
                    e, f, m = ref["edges"], ref["functions"], ref["macro_hidden"]
                    pshare = ref["parsed_share"]
                    st_e = "ok" if e["recall"] >= 0.85 else ("warn" if e["recall"] >= 0.65 else "fail")
                    rows.append({"id": "cg_calls", "what": "Call edges found vs libclang (compiler-grade reference)", "value": f"GitGalaxy found {e['recall'] * 100:.0f}% of libclang's {e['reference']:,} edges; {e['precision'] * 100:.0f}% of its {e['gitgalaxy']:,} edges are libclang's; libclang found functions in {pshare * 100:.0f}% of the files the scan found functions in" + ("" if pshare >= 0.7 else " (too few to rate)"), "status": st_e if pshare >= 0.7 else "info",
                                 "detail": "Reference: the engine's own libclang adapter, each .c file one translation unit with every header directory as an include path and no build system, so files that need generated headers or configuration (`config.h`, feature macros) may parse only in part: " + f"{ref['files_with_fatal_error']} of {ref['files_total']} translation units had a fatal error. When libclang finds functions in fewer than 70% of the files the scan does, the comparison is shown but not rated; calls through function pointers are not in either set. Edges are compared between functions both sides define." + (f" Macro-hidden calls: libclang sees {m['reference']:,}, GitGalaxy found {m['gitgalaxy_found']:,}" + (f", a name matcher {m['name_matcher_found']:,}." if "name_matcher_found" in m else ".") if m["reference"] else ""), "data": ref})
                    rows.append({"id": "cg_functions", "what": "Function definitions found vs libclang", "value": f"recall {f['recall'] * 100:.0f}%, precision {f['precision'] * 100:.0f}%", "status": "ok" if f["recall"] >= 0.9 else ("warn" if f["recall"] >= 0.75 else "fail"), "detail": "libclang counts every function with a body in a parsed file, including header inlines.", "data": f})
                    out["libclang_check"] = ref
            out["baseline_check"] = base
    return rows


def rating(rows, lang):
    """Two ratings: agreement on this repository with an independent name-matching parse (live), and the standing rating of the call graph against compiler-grade references measured in our research."""
    order = {"ok": 0, "info": 0, "warn": 1, "fail": 2}
    cg = [r for r in rows if r["id"] in ("calls", "filepairs", "functions", "coverage", "imports", "cg_calls", "cg_functions")]
    if not cg:
        return None
    worst = max(cg, key=lambda r: order[r["status"]])
    label = {"ok": "Good", "warn": "Fair", "fail": "Limited"}[worst["status"]]
    st = STANDING.get(lang)
    st_label = None
    if st:
        st_label = "Good" if st["recall"] >= 0.85 else ("Fair" if st["recall"] >= 0.65 else "Limited")
    calls = next((r for r in rows if r["id"] == "calls"), None)
    text = f"Consistency with a tree-sitter name matcher on this repository: {label}. (In our reference set this cheap check passed every C repository at 98 to 99% while compiler-grade recall ranged from 69% to 88%, so it does not predict the compiler-grade result.)"
    if st:
        text += f" Standing rating against a compiler-grade reference ({st['reference']}), from our research on pinned {lang.upper() if lang == 'c' else lang} repositories: {st_label}. GitGalaxy's strict call edges had precision {st['precision'] * 100:.0f}% and recall {st['recall'] * 100:.0f}% there; a tree-sitter name matcher had recall {st['tree_sitter_recall'] * 100:.0f}%."
    cgc = next((r for r in rows if r["id"] == "cg_calls" and "data" in r), None)
    comp = None
    if cgc:
        e = cgc["data"]["edges"]
        comp = {"label": {"ok": "Good", "warn": "Fair", "fail": "Limited", "info": "Not rated"}[cgc["status"]], "recall": e["recall"], "precision": e["precision"], "parsed_share": cgc["data"]["parsed_share"], "reference": cgc["data"]["reference"]}
        text += f" Compiler-grade rating on this repository: {comp['label']}: GitGalaxy found {e['recall'] * 100:.0f}% of the call edges libclang finds (precision {e['precision'] * 100:.0f}%) in the {comp["parsed_share"] * 100:.0f}% of files where libclang found functions."
    return {"label": label, "worst_check": worst["id"], "standing": st, "standing_label": st_label, "compiler_grade": comp, "text": text}
