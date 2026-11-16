#!/usr/bin/env python3
"""Files and functions: GitGalaxy vs repowise (black box, indexes made by h2h_rw.py / old_code_test.py), with universal-ctags as an independent reference.

    count_compare.py            prints one table; scratch layout as in h2h_rw.py

Per target, restricted to source files of the repository's main language (by extension):
  files      source files each tool indexed (GitGalaxy: file_data; repowise: graph_nodes file nodes)
  functions  functions and methods each tool found, as the set of (file, bare name)
  both / only GG / only RW   set overlap of the two tools
  vs ctags   the share of ctags' (file, name) functions each tool also found (ctags is an independent tag extractor, not ground truth; it knows no COBOL or PL/I)"""
import collections
import json
import pathlib
import sqlite3
import subprocess

B = pathlib.Path("/tmp/gitgalaxy-scratch/claude/h2h")
EXTS = {"c": (".c", ".h"), "python": (".py",), "typescript": (".ts", ".tsx"), "javascript": (".js", ".mjs", ".cjs", ".jsx"), "go": (".go",), "java": (".java",),
        "rust": (".rs",), "cobol": (".cbl", ".cob", ".cobol", ".cpy"), "fortran": (".f", ".f90", ".f95", ".for", ".F", ".F90"), "pli": (".pli", ".pl1", ".cbl")}
CTAGS_KINDS = {"c": {"function"}, "python": {"function", "member"}, "typescript": {"function", "method", "generator"}, "javascript": {"function", "method", "generator"},
               "go": {"func", "function", "method"}, "java": {"method"}, "rust": {"function", "method"}, "fortran": {"function", "subroutine"}}

MODERN = [("expat", "c", B / "expat", B / "expat_galaxy_master.db", B / "rw/expat"), ("redis", "c", B / "redis", B / "redis_galaxy_master.db", B / "rw/redis"),
          ("hiredis", "c", B / "hiredis", B / "hiredis_galaxy_master.db", B / "rw/hiredis"), ("libuv", "c", B / "libuv", B / "libuv_galaxy_master.db", B / "rw/libuv"),
          ("ndpi", "c", B / "ndpi", B / "ndpi_galaxy_master.db", B / "rw/ndpi"), ("zlib", "c", B / "zlib", B / "zlib_galaxy_master.db", B / "rw/zlib")]
for nm, lang in (("fastapi__fastapi", "python"), ("pallets__flask", "python"), ("encode__httpx", "python"), ("colinhacks__zod", "typescript"), ("axios__axios", "javascript"),
                 ("spf13__cobra", "go"), ("gin-gonic__gin", "go"), ("google__gson", "java"), ("serde-rs__json", "rust"), ("BurntSushi__ripgrep", "rust")):
    MODERN.append((nm, lang, B / "corpus" / nm, B / "scans" / f"{nm}_galaxy_master.db", B / "rw" / nm))
LEGACY = [("sphinx-2008 (Python 2)", "python", B / "old/sphinx_2008", B / "old/sphinx_2008_galaxy_master.db", B / "rw_old/sphinx_2008"),
          ("curl-1999 (old C)", "c", B / "old/curl_1999", B / "old/curl_1999_galaxy_master.db", B / "rw_old/curl_1999"),
          ("COBOL CardDemo", "cobol", B / "old/cobol_carddemo", B / "old/cobol_carddemo_galaxy_master.db", B / "rw_old/cobol_carddemo"),
          ("Fortran WRF", "fortran", B / "old/fortran_wrf", B / "old/fortran_wrf_galaxy_master.db", B / "rw_old/fortran_wrf"),
          ("PL/I sample", "pli", B / "old/pli_sample", B / "old/pli_sample_galaxy_master.db", B / "rw_old/pli_sample")]


def ro(db):
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def bare(n):
    return n.split("::")[-1].split(".")[-1].split("#")[-1]


def tool_sets(lang, edb, rw):
    ex = EXTS[lang]
    c = ro(edb)
    gg_files = {r[0] for r in c.execute("SELECT file_path FROM file_data") if r[0].lower().endswith(tuple(e.lower() for e in ex))}
    gg_funcs = {(p, bare(n)) for p, n in c.execute("SELECT f.file_path, d.func_name FROM function_data d JOIN file_data f ON f.id = d.file_id") if p in gg_files}
    c.close()
    rdb = rw / ".repowise" / "wiki.db"
    if not rdb.exists():
        return gg_files, gg_funcs, None, None
    c = ro(rdb)
    rw_files = {r[0].split("::")[0] for r in c.execute("SELECT node_id FROM graph_nodes WHERE node_type='file'") if r[0].lower().endswith(tuple(e.lower() for e in ex))}
    rw_funcs = {(p, bare(n)) for p, n, k in c.execute("SELECT file_path, name, kind FROM wiki_symbols") if k in ("function", "method", "subroutine") and p in rw_files}
    c.close()
    return gg_files, gg_funcs, rw_files, rw_funcs


def ctags_set(tree, lang, files):
    kinds = CTAGS_KINDS.get(lang)
    if not kinds:
        return None
    out = subprocess.run(["ctags", "-R", "--output-format=json", "--fields=+K", "-f", "-", "."], cwd=tree, capture_output=True, text=True, check=False).stdout
    s = set()
    for line in out.splitlines():
        try:
            t = json.loads(line)
        except ValueError:
            continue
        p = t.get("path", "").removeprefix("./")
        if t.get("kind") in kinds and p.lower().endswith(tuple(e.lower() for e in EXTS[lang])):
            s.add((p, t["name"]))
    return s


def row(label, lang, tree, edb, rw):
    gf, gfun, rf, rfun = tool_sets(lang, edb, rw)
    ct = ctags_set(tree, lang, gf)
    r = {"target": label, "lang": lang, "files_gg": len(gf), "files_rw": None if rf is None else len(rf), "funcs_gg": len(gfun), "funcs_rw": None if rfun is None else len(rfun)}
    if rfun is not None:
        r.update(both=len(gfun & rfun), only_gg=len(gfun - rfun), only_rw=len(rfun - gfun))
    if ct:
        r["ctags"] = len(ct)
        r["gg_vs_ctags"] = round(len(ct & gfun) / len(ct), 2)
        if rfun is not None:
            r["rw_vs_ctags"] = round(len(ct & rfun) / len(ct), 2)
    return r


def main():
    print(f"{'target':26s} {'lang':10s} {'files GG':>8s} {'RW':>5s} | {'funcs GG':>8s} {'RW':>6s} {'both':>6s} {'only GG':>8s} {'only RW':>8s} | {'ctags':>6s} {'GG finds':>8s} {'RW finds':>8s}")
    tot = collections.Counter()
    for group, items in (("MODERN", MODERN), ("LEGACY / OLD", LEGACY)):
        print(f"-- {group}")
        for it in items:
            try:
                r = row(*it)
            except Exception as exc:  # a target whose index is missing is reported, not hidden
                print(f"{it[0]:26s} failed: {exc}")
                continue
            f = lambda k: "-" if r.get(k) is None else str(r[k])  # noqa: E731
            print(f"{r['target']:26s} {r['lang']:10s} {f('files_gg'):>8s} {f('files_rw'):>5s} | {f('funcs_gg'):>8s} {f('funcs_rw'):>6s} {f('both'):>6s} {f('only_gg'):>8s} {f('only_rw'):>8s} | "
                  f"{f('ctags'):>6s} {f('gg_vs_ctags'):>8s} {f('rw_vs_ctags'):>8s}")


if __name__ == "__main__":
    main()
