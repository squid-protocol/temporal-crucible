#!/usr/bin/env python3
"""Add repowise to the reach head-to-head: same references, same file-level unit, same scoring as h2h_reach.py / h2h_multi.py.

    ENGINE=... [IMPORT_GRAPH_CORPUS_PATH=... PATH=... for the reference tools] h2h_rw.py LANG REPO_DIR [CLANG_CONTRACT_JSON]

repowise (AGPL-3.0, read-only measurement: we run the published package as a black box on a scratch copy and read its index; no code of it is used or copied) is
run in a throwaway HOME with telemetry disabled and no agent, hook, editor or model setup: `repowise init --mode fast --no-prose`. Its index (`.repowise/wiki.db`,
table `graph_edges`, edge_type 'calls') holds symbol-level call edges between `path::symbol` nodes, each with a confidence and a resolution origin. Two variants:
rw-all (every call edge) and rw-conf (confidence >= 0.85: drops its labelled name-only fallback, 0.5)."""
import json
import os
import pathlib
import sqlite3
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import h2h_reach as H  # noqa: E402
import h2h_multi as M  # noqa: E402  (needs ENGINE in the environment)

BASE = pathlib.Path("/tmp/gitgalaxy-scratch/claude/h2h")
RW_BIN = BASE / "rw-venv" / "bin" / "repowise"
RW_HOME = BASE / "rwhome"
RW_ROOT = BASE / "rw"


def rw_env():
    return {**os.environ, "HOME": str(RW_HOME), "XDG_CONFIG_HOME": str(RW_HOME / ".config"), "XDG_DATA_HOME": str(RW_HOME / ".local/share"),
            "XDG_CACHE_HOME": str(RW_HOME / ".cache"), "REPOWISE_TELEMETRY": "0"}


def scratch_copy(repo: pathlib.Path) -> pathlib.Path:
    dst = RW_ROOT / repo.name
    if (dst / ".git").is_dir():
        return dst
    dst.mkdir(parents=True, exist_ok=True)
    if (repo / ".git").exists():
        arc = subprocess.run(["git", "-C", str(repo), "archive", "HEAD"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(dst)], input=arc, check=True)
    else:
        subprocess.run(["cp", "-r", f"{repo}/.", str(dst)], check=True)
    for cmd in (["git", "init", "-q"], ["git", "-c", "user.email=a@b", "-c", "user.name=x", "add", "-A"],
                ["git", "-c", "user.email=a@b", "-c", "user.name=x", "commit", "-q", "-m", "snapshot"]):
        subprocess.run(cmd, cwd=dst, capture_output=True, check=False)
    return dst


def rw_index(work: pathlib.Path) -> pathlib.Path:
    db = work / ".repowise" / "wiki.db"
    if not db.exists():
        subprocess.run([str(RW_BIN), "telemetry", "disable"], env=rw_env(), capture_output=True, check=False)
        subprocess.run([str(RW_BIN), "init", ".", "--mode", "fast", "--no-prose", "-y", "--no-editor-setup", "--no-claude-md", "--no-agents", "--no-codex",
                        "--no-hook", "--no-distill-hook"], cwd=work, env=rw_env(), capture_output=True, timeout=3000, check=False)
    return db


def rw_pairs(db, min_conf):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT source_node_id, target_node_id FROM graph_edges WHERE edge_type = 'calls' AND confidence >= ?", (min_conf,)).fetchall()
    finally:
        con.close()
    return {(a.split("::", 1)[0], b.split("::", 1)[0]) for a, b in rows if a.split("::", 1)[0] != b.split("::", 1)[0]}


def main():
    lang, repo = sys.argv[1], pathlib.Path(sys.argv[2])
    outdir = pathlib.Path(os.environ.get("H2H_OUT", str(BASE / "scans")))
    outdir.mkdir(parents=True, exist_ok=True)
    if lang == "c":
        contract = json.load(open(sys.argv[3]))
        fatal = set(contract.get("fatal", []))
        files = sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if p.suffix in H.EXTS and p.is_file())
        scope = {f for f in files if f not in fatal}
        truth = {(a, b) for a, b in H.pairs_clang(contract) if a in scope and b in scope}
        defs, calls = H.ts_parse(repo, files)
        db = pathlib.Path(sys.argv[4]) if len(sys.argv) > 4 else BASE / f"{repo.name}_galaxy_master.db"
        ts_u, ts_a = H.pairs_ts(defs, calls, True), H.pairs_ts(defs, calls, False)
    else:
        contract, _ = M.CR.reference_contract(lang, repo)
        db = M.engine_scan(repo, outdir)
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        scanned = {r[0] for r in con.execute("SELECT file_path FROM file_data")}
        con.close()
        files = sorted(p for p in scanned if p.endswith(M.EXT[lang]))
        scope = set(files)
        truth = {(a, b) for a, b in M.contract_pairs(contract) if a in scope and b in scope}
        defs, calls = M.ts_baseline(lang, repo, files)
        ts_u, ts_a = H.pairs_ts(defs, calls, True), H.pairs_ts(defs, calls, False)
    tr = H.reach(truth)
    work = scratch_copy(repo)
    rdb = rw_index(work)
    print(f"{repo.name} [{lang}]: {len(scope)} files, {len(truth)} reference cross-file edges, {sum(1 for v in tr.values() if v)} files with a caller")
    print(H.score("engine", H.pairs_engine(db), truth, scope, tr))
    print(H.score("ts-unique", ts_u, truth, scope, tr))
    print(H.score("ts-all", ts_a, truth, scope, tr))
    if rdb.exists():
        print(H.score("rw-all", rw_pairs(rdb, 0.0), truth, scope, tr))
        print(H.score("rw-conf", rw_pairs(rdb, 0.85), truth, scope, tr))
    else:
        print("  repowise produced no index for this repository", flush=True)


if __name__ == "__main__":
    main()
