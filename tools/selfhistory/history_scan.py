#!/usr/bin/env python3
"""Temporal scans of GitGalaxy itself: daily full scans (exact anchors).

    history_scan.py picks            # write picks.tsv (last first-parent commit per US-Eastern day)
    history_scan.py daily [-j 4]     # full-scan every pick; resumable (finished DBs are kept)

Layout (all under this script's directory):
    picks.tsv         date<TAB>sha          the commits to scan
    dbs/<date>_<sha10>.db                   one SQLite DB per snapshot (repo_name = gitgalaxy)
    log.jsonl         one line per scan: date, sha, seconds, ok
    work/             scratch extracts (deleted after each scan)

Reads the v6 object store only (shared clones); never writes to v6.
"""
import argparse, json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("GG_REPO", "/srv/storage_16tb/projects/gitgalaxy/v6"))   # a GitGalaxy clone with the history
REF = "origin/main"
MIRROR = HERE / "mirror.git"      # private bare copy of v6, made once; scans use worktrees of it
DBS, WORK, PICKS, LOG = HERE / "dbs", HERE / "work", HERE / "picks.tsv", HERE / "log.jsonl"


def git(*a, **kw):
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, **kw)


def make_picks():
    env = dict(os.environ, TZ="America/Detroit")   # owner rule: days in US Eastern
    out = subprocess.run(["git", "-C", str(REPO), "log", REF, "--first-parent", "--reverse",
                          "--format=%H %cd", "--date=format-local:%Y-%m-%d"],
                         check=True, capture_output=True, text=True, env=env).stdout
    last = {}
    for line in out.splitlines():
        sha, day = line.split()
        last[day] = sha                      # later commit of the day wins
    PICKS.write_text("".join(f"{d}\t{s}\n" for d, s in sorted(last.items())))
    print(f"{len(last)} daily picks -> {PICKS}")


def read_picks():
    return [tuple(l.split("\t")) for l in PICKS.read_text().split("\n") if l]


def add_worktree(path, sha):
    subprocess.run(["git", "--git-dir", str(MIRROR), "worktree", "add", "-q", "--detach", str(path), sha],
                   check=True, capture_output=True)


def drop_worktree(path):
    shutil.rmtree(path, ignore_errors=True)
    subprocess.run(["git", "--git-dir", str(MIRROR), "worktree", "prune"], capture_output=True)


def checkout_scan(sha, job, scanner="galaxyscope"):
    """Full scan of one commit from a real git checkout (dir named gitgalaxy -> repo_name gitgalaxy).
    A checkout, NOT `git archive`: the scanner treats the two differently (pyproject.toml is scanned in a
    checkout and dropped from an archive extract), and the delta chain must be compared like-for-like."""
    src = job / "gitgalaxy"
    add_worktree(src, sha)
    env = dict(os.environ, GITGALAXY_DISABLE_GIT_HISTORY="1")
    subprocess.run(["nice", "-n", "10", scanner, str(src), "--db-only"], cwd=job, env=env,
                   capture_output=True, text=True, errors="replace")
    drop_worktree(src)
    db = job / "gitgalaxy_galaxy_master.db"
    if db.exists():
        import sqlite3
        c = sqlite3.connect(db); c.execute("pragma wal_checkpoint(truncate)"); c.close()
        return db
    return None


def scan_one(day, sha, scanner="galaxyscope"):
    final = DBS / f"{day}_{sha[:10]}.db"
    if final.exists():
        return "kept", 0.0
    t0 = time.time()
    job = WORK / f"{day}_{sha[:10]}"
    shutil.rmtree(job, ignore_errors=True)
    job.mkdir(parents=True)
    ok = False
    try:
        db = checkout_scan(sha, job, scanner)
        if db:
            DBS.mkdir(exist_ok=True)
            shutil.move(str(db), str(final) + ".part"); os.replace(str(final) + ".part", final)
            ok = True
    finally:
        shutil.rmtree(job, ignore_errors=True)
    dt = time.time() - t0
    with LOG.open("a") as f:
        f.write(json.dumps({"day": day, "sha": sha, "seconds": round(dt, 1), "ok": ok}) + "\n")
    return ("ok" if ok else "FAILED"), dt


def daily(jobs):
    picks = read_picks()
    DBS.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    done = 0
    def one(p):
        nonlocal done
        st, dt = scan_one(*p)
        done += 1
        print(f"[{done}/{len(picks)}] {p[0]} {p[1][:10]} {st} {dt:.0f}s", flush=True)
        return st
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        res = list(ex.map(one, picks))
    bad = [p for p, r in zip(picks, res) if r == "FAILED"]
    print(f"finished: {res.count('ok')} scanned, {res.count('kept')} already had, {len(bad)} failed")
    for d, s in bad:
        print("  FAILED", d, s)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["picks", "daily"])
    ap.add_argument("-j", "--jobs", type=int, default=4)
    a = ap.parse_args()
    make_picks() if a.cmd == "picks" else daily(a.jobs)
