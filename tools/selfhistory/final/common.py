"""Shared IO helpers for the final sensitivity analysis. READ-ONLY on all inputs.
Environment overrides: FINAL_SPEED_DIR (default <history>/speed), FINAL_OUT (default final/out), FINAL_SNAP_DIR (snapshot dir; if unset a fresh
snapshot is taken at first use, so a hand-run script never reads a stale snapshot)."""
import gzip, hashlib, json, os, re, shutil, statistics as st, subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import analysis as A
from analysis import *          # noqa: F401,F403  (re-export pure helpers)

H = Path("/srv/storage_16tb/projects/gitgalaxy-history")
MIRROR = H / "mirror.git"
SPEED = Path(os.environ.get("FINAL_SPEED_DIR", H / "speed"))
OUT = Path(os.environ.get("FINAL_OUT", H / "final" / "out"))
OUT.mkdir(parents=True, exist_ok=True)
TIP = "7203d2555753ca2b29e180de3cb8d7845aca6a06"
CORPORA = ["keyword-rosetta", "cics-crucible", "onepl", "language-crucible"]
EAST = ZoneInfo("America/New_York")
SNAP_FILES = ["refined.jsonl", "refined_pass2.jsonl", "steps_detected.json", "dense.jsonl", "sens.jsonl"]


def take_snapshot(dest=None):
    """Copy the (possibly still growing) inputs into dest (default OUT/snapshot, emptied first). Returns dest."""
    dest = Path(dest or OUT / "snapshot")
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for f in SNAP_FILES:
        if (SPEED / f).exists(): shutil.copy2(SPEED / f, dest / f)
    return dest


_snap = None
def snap():
    global _snap
    if _snap is None:
        d = os.environ.get("FINAL_SNAP_DIR")
        _snap = Path(d) if d else take_snapshot()
    return _snap


def snapshot_hash():
    h = hashlib.sha1()
    d = snap()
    for f in SNAP_FILES:
        if (d / f).exists(): h.update(f.encode()); h.update((d / f).read_bytes())
    return h.hexdigest()[:10]


def stamp_md(): return f"<!-- input snapshot hash {snapshot_hash()} -->"


def git(*a):
    return subprocess.run(["git", "--git-dir", str(MIRROR), *a], check=True, capture_output=True, text=True, errors="replace").stdout


def jl(p):
    p = Path(p)
    if not p.exists(): return []
    with p.open() as f:
        return [json.loads(l) for l in f if l.strip()]


def load_detected():
    return json.load(open(snap() / "steps_detected.json"))


def load_refined_passes():
    return jl(snap() / "refined.jsonl"), jl(snap() / "refined_pass2.jsonl")


def load_refined():
    """THE single loader: pass 1 + pass 2 (pass 2 supersedes), deduped by (corpus, from_sha, to_sha). See analysis.merge_passes."""
    p1, p2 = load_refined_passes()
    return merge_passes(p1, p2)[0]


def load_refined_info():
    p1, p2 = load_refined_passes()
    rows, info = merge_passes(p1, p2)
    return rows, info


_head = None
def head_list():
    global _head
    if _head is None:
        _head = git("rev-list", "--first-parent", "--reverse", TIP).split()
    return _head


def pos():
    return {s: i for i, s in enumerate(head_list())}


def commit_dates():
    out = git("log", "--first-parent", "--format=%H\t%cI", TIP)
    d = {}
    for l in out.splitlines():
        s, c = l.split("\t")
        d[s] = datetime.fromisoformat(c).astimezone(EAST)
    return d


def load_series(dates=None):
    """Series as detect_steps.py builds it (dense+sens, anchors excluded, failed runs as markers), but every date is the US Eastern
    commit date from the mirror (dates: sha -> aware datetime) so one date base is used throughout."""
    rows = jl(snap() / "dense.jsonl") + jl(snap() / "sens.jsonl")
    return build_series(rows, {s: v.strftime("%Y-%m-%d") for s, v in dates.items()} if dates else None)


def commit_files():
    d, cur = {}, None
    for l in (H / "gh" / "commit_files.txt").read_text(errors="replace").splitlines():
        if l.startswith("@@"):
            sha, subj = l[2:].split("\t", 1)
            cur = d[sha] = (subj, [])
        elif l.strip() and cur is not None:
            cur[1].append(l.strip())
    return d


def diff_cache():
    return json.load(gzip.open(H / "evolution_real" / "cache" / "diff_gitgalaxy-engine_de3c170c426c97d9.json.gz"))


def items():
    return {i["n"]: i for i in jl(H / "gh" / "items.jsonl")}


def numstat(sha):
    """Lines added/deleted against the FIRST parent (merges included); root commit against the empty tree."""
    parents = git("rev-list", "--parents", "-n", "1", sha).split()[1:]
    out = git("diff", "--numstat", "--no-renames", parents[0], sha) if parents else git("diff-tree", "--root", "--numstat", "-r", "--no-renames", "--format=", sha)
    add = dele = 0
    for l in out.splitlines():
        a, d, *_ = l.split("\t")
        if a != "-": add += int(a); dele += int(d)
    return add, dele


def era_of(dt):
    return era_of_date(dt.strftime("%Y-%m-%d"))


def cache_gap(cache, sha, files):
    """Commit touches core files but is absent from the diff cache (the 27 core merges and the root): its function count is unknown."""
    return sha not in cache and any(kind(p) == "core" for p in files)
