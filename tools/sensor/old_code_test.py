#!/usr/bin/env python3
"""Old and legacy code: what do GitGalaxy and repowise (black box, isolated HOME) find, and how often does repowise's tree-sitter parse fail?

    old_code_test.py            (venv with nothing special; needs the scratch layout of h2h_rw.py)

Targets: sphinx at its first snapshot (2008, Python 2), curl at its first snapshot (1999, old C), and one repository each of COBOL, Fortran and PL/I from
language-crucible. Per target: source files each tool indexes, functions each tool finds, files repowise flags `has_error` (tree-sitter parse errors), and
universal-ctags' function count where ctags supports the language (an independent count; not ground truth)."""
import collections
import json
import os
import pathlib
import sqlite3
import subprocess
import sys

BASE = pathlib.Path("/tmp/gitgalaxy-scratch/claude/h2h")
OLD = BASE / "old"
POOL = pathlib.Path("/srv/storage_16tb/projects/temporal-crucible-pool")
LC = pathlib.Path("/srv/storage_16tb/projects/gitgalaxy/language-crucible/data")
ENGINE = pathlib.Path("/srv/storage_16tb/projects/gitgalaxy-worktrees/sensors-libsurface")
PYBIN = "/srv/storage_16tb/projects/gitgalaxy/venvs/selfscan/bin/python"
RW = BASE / "rw-venv" / "bin" / "repowise"
RWHOME = BASE / "rwhome"


def rw_env():
    return {**os.environ, "HOME": str(RWHOME), "XDG_CONFIG_HOME": str(RWHOME / ".config"), "XDG_DATA_HOME": str(RWHOME / ".local/share"),
            "XDG_CACHE_HOME": str(RWHOME / ".cache"), "REPOWISE_TELEMETRY": "0"}


def prep(name, make):
    d = OLD / name
    if not (d / ".prepared").exists():
        d.mkdir(parents=True, exist_ok=True)
        make(d)
        (d / ".prepared").write_text("1")
    return d


def from_pool(repo, sha):
    def mk(d):
        arc = subprocess.run(["git", "-C", str(POOL / repo), "archive", sha], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(d)], input=arc, check=True)
    return mk


def from_copy(src):
    def mk(d):
        subprocess.run(["cp", "-r", f"{src}/.", str(d)], check=True)
        subprocess.run(["rm", "-rf", str(d / ".git")], check=False)
    return mk


def engine_scan(d):
    db = OLD / f"{d.name}_galaxy_master.db"
    if not db.exists():
        env = {**os.environ, "PYTHONPATH": str(ENGINE), "GITGALAXY_LICENSE_KEY": "COMMUNITY_FREE_TIER", "GITGALAXY_DISABLE_GIT_HISTORY": "1"}
        subprocess.run([PYBIN, "-m", "gitgalaxy.galaxyscope", str(d)], cwd=OLD, env=env, capture_output=True, check=False)
    return db


def rw_index(d):
    w = BASE / "rw_old" / d.name
    if not (w / ".git").exists():
        w.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-r", f"{d}/.", str(w)], check=True)
        for cmd in (["git", "init", "-q"], ["git", "-c", "user.email=a@b", "-c", "user.name=x", "add", "-A"], ["git", "-c", "user.email=a@b", "-c", "user.name=x", "commit", "-q", "-m", "s"]):
            subprocess.run(cmd, cwd=w, capture_output=True, check=False)
    db = w / ".repowise" / "wiki.db"
    if not db.exists():
        subprocess.run([str(RW), "init", ".", "--mode", "fast", "--no-prose", "-y", "--no-editor-setup", "--no-claude-md", "--no-agents", "--no-codex", "--no-hook",
                        "--no-distill-hook"], cwd=w, env=rw_env(), capture_output=True, timeout=3000, check=False)
    return db


def ctags_functions(d):
    out = subprocess.run(["ctags", "-R", "--output-format=json", "--fields=+K", "-f", "-", str(d)], capture_output=True, text=True, check=False).stdout
    n = collections.Counter()
    for line in out.splitlines():
        try:
            t = json.loads(line)
        except ValueError:
            continue
        if t.get("kind") in ("function", "subroutine", "method", "member"):
            n[t.get("kind")] += 1
    return sum(n.values())


def summarise(name, d):
    edb, rdb = engine_scan(d), rw_index(d)
    row = {"target": name}
    if edb.exists():
        con = sqlite3.connect(f"file:{edb}?mode=ro", uri=True)
        row["engine_files"] = con.execute("SELECT COUNT(*) FROM file_data WHERE language NOT IN ('plaintext','unknown','markdown','json','yaml','text','xml')").fetchone()[0]
        row["engine_functions"] = con.execute("SELECT COUNT(*) FROM function_data").fetchone()[0]
        row["engine_languages"] = [r[0] for r in con.execute("SELECT language FROM file_data GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 4")]
        con.close()
    if rdb.exists():
        con = sqlite3.connect(f"file:{rdb}?mode=ro", uri=True)
        row["rw_files"] = con.execute("SELECT COUNT(*) FROM graph_nodes WHERE node_type='file' AND language NOT IN ('unknown','markdown','json','yaml','text','plaintext')").fetchone()[0]
        row["rw_error_files"] = con.execute("SELECT COUNT(*) FROM graph_nodes WHERE node_type='file' AND has_error=1 AND language NOT IN ('unknown','markdown','json','yaml','text','plaintext')").fetchone()[0]
        row["rw_functions"] = con.execute("SELECT COUNT(*) FROM wiki_symbols WHERE kind IN ('function','method','subroutine')").fetchone()[0]
        row["rw_languages"] = [r[0] for r in con.execute("SELECT language FROM graph_nodes WHERE node_type='file' GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 4")]
        con.close()
    else:
        row["rw_note"] = "no index produced"
    row["ctags_functions"] = ctags_functions(d)
    return row


def main():
    OLD.mkdir(parents=True, exist_ok=True)
    targets = [
        ("sphinx-2008 (Python 2)", "sphinx_2008", from_pool("sphinx", "a86b36b4b")),
        ("curl-1999 (old C)", "curl_1999", from_pool("curl", "ae1912cb0")),
        ("COBOL (CardDemo)", "cobol_carddemo", from_copy(LC / "cobol" / "aws-mainframe-modernization-carddemo")),
        ("Fortran (WRF)", "fortran_wrf", from_copy(LC / "fortran" / "wrf")),
        ("PL/I (zopeneditor sample)", "pli_sample", from_copy(LC / "pli" / "zopeneditor_sample")),
    ]
    for label, name, mk in targets:
        d = prep(name, mk)
        row = summarise(label, d)
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
