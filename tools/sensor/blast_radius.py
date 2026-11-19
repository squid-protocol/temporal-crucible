#!/usr/bin/env python3
"""blast_radius: a fast, exact measurement of where the fixes for a change land (replaces ripple_links.py / ripple_trailer.py / ripple_rank.py for named-cause pairs).

What it computes, per (fix, causing commit) pair, with the nearest quarterly scan at or after the causing commit as the call graph:
  * the functions each commit touched (git hunk-header context, one streaming `git log -p -U0 --stdin` pass for all commits, cached),
  * whether the fixed functions outside the causing commit's changed set lie within 1, 2, 3 calls (callers, callees, either) of it,
  * the EXACT expected rate for (a) same-file functions of similar size (decile +-1) outside the changed set and (b) random functions of the same size decile, from counts
    (no sampling), so the comparison costs a few array operations per pair.
Graphs are compact (scipy sparse, one cache file per snapshot); pairs are processed per snapshot in parallel; the report step is separate and re-runs in seconds with any grouping.

    blast_radius.py run    --repo linux --tag linux-core --pairs PAIRS.json --out DIR [--workers 6] [--limit N] [--lang c]
    blast_radius.py report --out DIR [--by repo|lag|cross|subsystem|signature ...]

PAIRS.json: a list of {"fix", "ind", "fix_ct", "ind_ct", "lag", optional "fix_files", "ind_files", "repo"}. `tag` names turn_v2/scan_<tag>/snapshots.json (quarterly scan databases)."""
import argparse
import collections
import json
import os
import pickle
import sqlite3
import subprocess
import sys
import threading
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import ripple_forward as RF  # noqa: E402  (function-name extraction per language, git attributes file)

POOL = RF.POOL
B = RF.B
K = (1, 2, 3)
RELS = [f"{d}{k}" for d in ("callers", "callees", "either") for k in K]
NDEC = 10


# ------------------------------------------------------------------ stage 1: functions touched by each commit
def touched_all(repo, shas, lang, cache_file):
    """sha -> sorted list of (path, function) for every sha, one streaming git log pass; cached on disk."""
    cache = pickle.load(open(cache_file, "rb")) if Path(cache_file).exists() else {}
    need = [s for s in dict.fromkeys(shas) if s not in cache]
    if need:
        cmd = ["git", "-c", f"core.attributesFile={RF.ATTRS}", "-C", f"{POOL}/{repo}", "log", "--no-walk=unsorted", "--stdin", "-p", "-U0", "--no-color", "-M", "--format=@@COMMIT %H"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors="replace")
        threading.Thread(target=lambda: (proc.stdin.write("\n".join(need) + "\n"), proc.stdin.close()), daemon=True).start()
        sha, cur = None, None
        for line in proc.stdout:
            if line.startswith("@@COMMIT "):
                sha, cur = line[9:].strip(), None
                cache.setdefault(sha, set())
            elif sha:
                if line.startswith("+++ b/"):
                    cur = line[6:].rstrip("\n")
                    if not cur.endswith(RF.EXTS[lang]):
                        cur = None
                elif cur and line.startswith("@@"):
                    m = RF.HUNK.match(line.rstrip("\n"))
                    n = RF.func_name(m.group(1), lang) if m else None
                    if n:
                        cache[sha].add((cur, n))
        proc.wait()
        for s in need:
            cache.setdefault(s, set())
        pickle.dump({k: sorted(v) if isinstance(v, set) else v for k, v in cache.items()}, open(cache_file, "wb"))
    return {s: [tuple(x) for x in cache[s]] for s in dict.fromkeys(shas)}


def authors_all(repo, shas, cache_file):
    """sha -> author e-mail (lower case), one `git log --no-walk --stdin` pass, cached."""
    cache = pickle.load(open(cache_file, "rb")) if Path(cache_file).exists() else {}
    need = [s for s in dict.fromkeys(shas) if s not in cache]
    if need:
        res = subprocess.run(["git", "-C", f"{POOL}/{repo}", "log", "--no-walk=unsorted", "--stdin", "--format=%H %ae"], input="\n".join(need) + "\n", capture_output=True, text=True, errors="replace").stdout
        for line in res.splitlines():
            h, _, e = line.partition(" ")
            cache[h] = e.strip().lower()
        pickle.dump(cache, open(cache_file, "wb"))
    return cache


def args_by_key(db):
    """(path, function) -> parameter count, last row wins (as the earlier scripts)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
    out = {(files[ff], nm): int(a or 0) for ff, nm, a in con.execute("SELECT file_id, func_name, args FROM function_data") if ff in files}
    con.close()
    return out


# ------------------------------------------------------------------ stage 2: compact graphs
class Graph:
    """One snapshot's call graph as arrays: nodes keyed (path, function), confident resolved call edges, size deciles, file ids."""

    def __init__(self, db):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
        key_of, loc, argc = {}, {}, {}
        for fid, ff, nm, lo, ar in con.execute("SELECT id, file_id, func_name, loc, args FROM function_data"):
            if ff in files:
                k = (files[ff], nm)
                key_of[fid] = k
                loc[k] = max(loc.get(k, 0), int(lo or 0))
                argc[k] = int(ar or 0)
        keys = sorted(loc)
        self.index = {k: i for i, k in enumerate(keys)}
        n = len(keys)
        src, dst = [], []
        maxc = int(os.environ.get("BLAST_MAXC", "1"))  # edges with at most this many candidate targets; 1 = confident edges only (the default of every earlier result)
        for s, d in con.execute(f"SELECT src_func_id, dst_func_id FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL AND COALESCE(candidates, 1) <= {maxc}"):
            if s in key_of and d in key_of and key_of[s] != key_of[d]:
                src.append(self.index[key_of[s]])
                dst.append(self.index[key_of[d]])
        con.close()
        fp = os.environ.get("BLAST_FNPTR")  # directory of function-pointer edge files (fnptr_edges.py); unset = the call graph as in every earlier result
        if fp:
            import hashlib
            import pickle
            f = os.path.join(fp, hashlib.md5(db.encode()).hexdigest() + ".pkl")
            if os.path.exists(f):
                for a_key, b_key in pickle.load(open(f, "rb"))["edges"]:
                    if a_key in self.index and b_key in self.index and a_key != b_key:
                        src.append(self.index[a_key])
                        dst.append(self.index[b_key])
        self.n = n
        self.loc = np.array([loc[k] for k in keys], dtype=np.int64)
        self.args = np.array([argc[k] for k in keys], dtype=np.int64)
        cuts = np.percentile(self.loc, np.arange(10, 100, 10)) if n else np.array([])
        self.dec = np.searchsorted(cuts, self.loc).astype(np.int64)
        fpaths = sorted({k[0] for k in keys})
        fidx = {p: i for i, p in enumerate(fpaths)}
        self.fid = np.array([fidx[k[0]] for k in keys], dtype=np.int64)
        self.nfiles = len(fpaths)
        self.key_fd = self.fid * NDEC + self.dec
        self.keyspace = self.nfiles * NDEC
        A = sp.csr_matrix((np.ones(len(src), dtype=np.int8), (src, dst)), shape=(n, n))
        A.data[:] = 1
        self.callees_m = A.T.tocsr()  # callees_m @ v: functions called by some function in v
        self.callers_m = A  # callers_m @ v: functions that call some function in v
        self.tot_key = np.bincount(self.key_fd, minlength=self.keyspace)
        self.tot_dec = np.bincount(self.dec, minlength=NDEC)

    def near(self, start):
        """{relation: boolean array of the functions within k calls of `start`, excluding `start`}."""
        v0 = np.zeros(self.n, dtype=np.int8)
        v0[start] = 1
        res = {}
        seen = {"callers": v0.copy(), "callees": v0.copy()}
        front = {"callers": v0, "callees": v0}
        cum = {}
        for k in K:
            for d, m in (("callers", self.callers_m), ("callees", self.callees_m)):
                nxt = (m @ front[d]) > 0
                nxt &= seen[d] == 0
                seen[d] = seen[d] | nxt.astype(np.int8)
                front[d] = nxt.astype(np.int8)
                res[f"{d}{k}"] = seen[d].astype(bool) & (v0 == 0)
            res[f"either{k}"] = res[f"callers{k}"] | res[f"callees{k}"]
        return res


# ------------------------------------------------------------------ per-snapshot worker
def measure_snapshot(args):
    db, prev_db, items = args
    g = Graph(db)
    prev = args_by_key(prev_db) if prev_db else None
    rows = []
    for it in items:
        I = np.array(sorted({g.index[k] for k in it["I"] if k in g.index}), dtype=np.int64)
        F = np.array(sorted({g.index[k] for k in it["F"] if k in g.index}), dtype=np.int64)
        if not len(I) or not len(F):
            rows.append({"pid": it["pid"], "status": "not found in the snapshot"})
            continue
        Fo = np.setdiff1d(F, I)
        sig = None
        if prev is not None:
            sig = any((k in prev) and prev[k] != int(g.args[g.index[k]]) for k in it["I"] if k in g.index)  # a changed function whose parameter count differs from the previous snapshot's
        row = {"pid": it["pid"], "status": "ok", "sig": sig, "nI": len(I), "nF": len(F), "nFo": len(Fo), "same_func": bool(len(np.intersect1d(F, I))), "same_file": bool(len(np.intersect1d(g.fid[F], g.fid[I]))), "cands": g.n - len(I)}
        if len(Fo):
            near = g.near(I)
            rels = list(RELS)
            if it.get("CO") is not None:  # co-change control: functions that changed together with the changed set before the causing commit
                co = np.zeros(g.n, dtype=bool)
                co[[g.index[k] for k in it["CO"] if k in g.index]] = True
                co[I] = False
                row["co_n"] = int(co.sum())
                near["cochange"] = co
                near["near2_nocochange"] = near["either2"] & ~co
                near["cochange_notnear2"] = co & ~near["either2"]
                row["o_both"] = float((near["either2"] & co)[Fo].any())
                rels += ["cochange", "near2_nocochange", "cochange_notnear2"]
            im_key = np.bincount(g.key_fd[I], minlength=g.keyspace) if len(I) else None
            im_dec = np.bincount(g.dec[I], minlength=NDEC)
            for rel in rels:
                m = near[rel]
                row[f"o_{rel}"] = float(m[Fo].any())
                nk = np.bincount(g.key_fd[m], minlength=g.keyspace)
                nd = np.bincount(g.dec[m], minlength=NDEC)
                keep_b, keep_a = [], []
                for f in Fo:
                    d, fl = int(g.dec[f]), int(g.fid[f])
                    lo, hi = max(d - 1, 0), min(d + 1, NDEC - 1)
                    tot = sum(int(g.tot_key[fl * NDEC + x]) - int(im_key[fl * NDEC + x]) for x in range(lo, hi + 1)) - 1  # same file, size decile +-1, outside the changed set, not f
                    nearc = sum(int(nk[fl * NDEC + x]) for x in range(lo, hi + 1)) - int(m[f])
                    keep_b.append(nearc / tot if tot > 0 else None)
                    pool = int(g.tot_dec[d]) - int(im_dec[d])
                    keep_a.append(int(nd[d]) / pool if pool > 0 else None)
                row[f"eB_{rel}"] = 1 - float(np.prod([1 - x for x in keep_b])) if all(x is not None for x in keep_b) else np.nan
                row[f"eA_{rel}"] = 1 - float(np.prod([1 - x for x in keep_a])) if all(x is not None for x in keep_a) else np.nan
        rows.append(row)
    return rows


# ------------------------------------------------------------------ driver
def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pairs = json.load(open(args.pairs))
    if args.limit:
        pairs = pairs[: args.limit]
    repo = args.repo
    sn = json.load(open(f"{B}/scan_{args.tag}/snapshots.json"))
    cts = np.array([int(subprocess.run(["git", "-C", f"{POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn]) if not (out / "snapshot_cts.npy").exists() else np.load(out / "snapshot_cts.npy")
    np.save(out / "snapshot_cts.npy", cts)
    shas = [p[k] for p in pairs for k in ("fix", "ind")]
    touched = touched_all(repo, shas, args.lang, out / "touched.pkl")
    authors = authors_all(repo, shas, out / "authors.pkl")
    by_snap = collections.defaultdict(list)
    meta, dropped = [], collections.Counter()
    for pid, p in enumerate(pairs):
        s = int(np.searchsorted(cts, p["ind_ct"], side="left"))
        I, F = touched[p["ind"]], touched[p["fix"]]
        if s >= len(sn):
            dropped["no snapshot"] += 1
        elif not I or not F:
            dropped["no function in a commit"] += 1
        elif len(I) > 60 or len(F) > 30:
            dropped["sweep (too many functions)"] += 1
        else:
            by_snap[s].append({"pid": pid, "I": I, "F": F})
            meta.append({"pid": pid, "snapshot": s, "lag": p["lag"], "fix": p["fix"], "ind": p["ind"], "repo": p.get("repo", repo), "fix_files": p.get("fix_files"), "ind_files": p.get("ind_files"), "same_author": authors.get(p["fix"]) == authors.get(p["ind"]) and authors.get(p["fix"]) is not None})
    print(f"{repo}: {len(pairs)} pairs; to measure {len(meta)} in {len(by_snap)} snapshots; dropped {dict(dropped)}", flush=True)
    jobs = [(sn[s]["db"], sn[s - 1]["db"] if s >= 1 else None, items) for s, items in sorted(by_snap.items())]
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, r in enumerate(ex.map(measure_snapshot, jobs)):
            rows += r
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(jobs)} snapshots", flush=True)
    df = pd.DataFrame(rows).merge(pd.DataFrame(meta), on="pid")
    df.to_pickle(out / "measure.pkl")
    json.dump(dict(dropped), open(out / "dropped.json", "w"))
    print(f"measured {int((df.status == 'ok').sum())} pairs ({int((df.get('nFo', pd.Series(dtype=float)) > 0).sum())} with a fixed function outside the changed set); {int((df.status != 'ok').sum())} not found in the snapshot", flush=True)


# ------------------------------------------------------------------ report
def sub(path):
    parts = path.split("/")
    return "/".join(parts[:2]) if parts[0] in ("fs", "net", "include") and len(parts) > 2 else parts[0]


def ratio(d, rel, col, rng, boot=500):
    d = d.dropna(subset=[f"{col}_{rel}", f"o_{rel}"])
    if len(d) < 15 or d[f"{col}_{rel}"].sum() <= 0:
        return None
    o, e = d[f"o_{rel}"].to_numpy(float), d[f"{col}_{rel}"].to_numpy(float)
    w = rng.multinomial(len(o), np.ones(len(o)) / len(o), size=boot)
    ee = w @ e
    ok = ee > 0
    vals = (w @ o)[ok] / ee[ok]
    return o.sum() / e.sum(), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), len(d), float(o.mean()), float(e.mean())


def fmt(r):
    return "           n/a" if r is None else f"{r[0]:5.2f} [{r[1]:4.2f},{r[2]:4.2f}] ({100 * r[4]:.0f}% vs {100 * r[5]:.0f}%, n {r[3]})"


def report(args):
    rng = np.random.default_rng(2982)
    df = pd.concat([pd.read_pickle(Path(o) / "measure.pkl") for o in args.out])
    df = df[df.status == "ok"].copy()
    df["cross"] = ~df["same_file"].astype(bool)
    df["lagb"] = pd.cut(df.lag, [-1, 30, 365, 1e9], labels=["under 30 d", "30 to 365 d", "a year or more"])
    if "fix_files" in df and df.fix_files.notna().any():
        df["subsystem"] = [collections.Counter(sub(f) for f in ff).most_common(1)[0][0] if ff else "?" for ff in df.fix_files]
    out = df[df.nFo > 0]
    print(f"{len(df)} measured pairs; {len(out)} with a fixed function outside the changed set; same function in {100 * df.same_func.mean():.0f}% of pairs; cross-file {int(df.cross.sum())}")
    groups = [("all", None)] + [(b, b) for b in args.by]
    for label, col in groups:
        print(f"\n=== {label} ===" if col else "\n=== all pairs ===")
        parts = [("all", out)] if col is None else [(str(k), v) for k, v in out.groupby(col, observed=True)]
        for name, d in sorted(parts, key=lambda kv: -len(kv[1]))[: args.top]:
            if len(d) < args.min_n:
                continue
            line = " | ".join(f"{rel} {fmt(ratio(d, rel, 'eB', rng))}" for rel in args.rels)
            allg = df if col is None else df[df[col].astype(str) == name]
            print(f"  {name:20s} n {len(d):5d} (all {len(allg):5d}, same function {100 * allg.same_func.mean():3.0f}%): {line}")
    print("\n(ratio against same-file functions of similar size, 95% interval over pairs; then observed % vs expected %)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub_p = ap.add_subparsers(dest="cmd", required=True)
    r = sub_p.add_parser("run")
    r.add_argument("--repo", required=True)
    r.add_argument("--tag", required=True)
    r.add_argument("--pairs", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--workers", type=int, default=6)
    r.add_argument("--limit", type=int)
    r.add_argument("--lang", default="c")
    p = sub_p.add_parser("report")
    p.add_argument("--out", nargs="+", required=True)
    p.add_argument("--by", nargs="*", default=[])
    p.add_argument("--rels", nargs="*", default=["callers1", "callees1", "either1", "either2"])
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--min-n", type=int, default=20)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else report(a)


if __name__ == "__main__":
    main()
