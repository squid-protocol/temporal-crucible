#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""CGT-1..5 (docs/cgt_hypotheses.md): call networks over a codebase's life. Aggregates only.

    SFS_SRC=<popan>/structural-fingerprint-scanner/src <venv>/bin/python tools/cgt_eval.py \
        --gg GG_CHECKOUT_AT_8f96d76ba --scratch DIR > cgt_result.json

Phases are cached under --scratch (networks per snapshot, the CGT-3 commit scans), so a rerun after a crash resumes.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import pickle
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).parent))
import nh_eval as N  # noqa: E402
import sfs_eval as S  # noqa: E402
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402

SEED = 2982
CEXT = (".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp")
REPOS = ("curl", "openssl", "libarchive", "harfbuzz", "ndpi")
YEAR = 365.25 * 86400
CGT3_N = 120
CLASSES = ("latent", "regression", "other-fix", "extrinsic", "control")


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def is_c(p):
    return p.lower().endswith(CEXT)


def parse_calls(raw):
    try:
        vals = json.loads(raw) if raw else []
    except ValueError:
        return set()
    out = set()
    for v in vals:
        for tok in str(v).replace("(", " ").split():
            out.add(tok.split(".")[-1].split("::")[-1].split("->")[-1])
    return out


# ------------------------------------------------------------------------------------------------- networks
def network(funcs):
    """funcs: list of (path, name, callees). Returns (nodes set, edges set of ((p,n),(p2,n2)))."""
    nodes = {(p, n) for p, n, _ in funcs}
    by_name = collections.defaultdict(set)
    for p, n in nodes:
        by_name[n].add(p)
    edges = set()
    for p, n, cs in funcs:
        for c in cs:
            if c == n:
                continue
            if p in by_name.get(c, ()):
                edges.add(((p, n), (p, c)))
            elif len(by_name.get(c, ())) == 1:
                edges.add(((p, n), (next(iter(by_name[c])), c)))
    return nodes, edges


def snapshot_networks(r, scratch):
    cache = scratch / f"net_{r}.pkl"
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    snaps = N.snapshots(r)
    want = {s["sha"] for s in snaps}
    con = sqlite3.connect(f"file:{S.DBS[r]}?mode=ro", uri=True)
    files = collections.defaultdict(list)
    for fid, path, sha in con.execute("SELECT id, file_path, commit_hash FROM file_data"):
        if sha in want and path and is_c(path):
            files[sha].append((fid, path))
    nets = []
    for s in snaps:
        fl = files.get(s["sha"], [])
        pmap = dict(fl)
        funcs = []
        ids = list(pmap)
        for i in range(0, len(ids), 900):
            chunk = ids[i:i + 900]
            q = f"SELECT file_id, func_name, loc, calls_out_to FROM function_data WHERE file_id IN ({','.join('?' * len(chunk))})"
            for fid, name, loc, calls in con.execute(q, chunk):
                if name and (loc or 0) >= 3:
                    funcs.append((pmap[fid], str(name).split("::")[-1], parse_calls(calls)))
        nodes, edges = network(funcs)
        nets.append({"sha": s["sha"], "ct": s["ct"], "nodes": nodes, "edges": edges,
                     "names": {n for _, n in nodes}})
    con.close()
    cache.write_bytes(pickle.dumps(nets))
    return nets


def renames(repo, a, b):
    m = {}
    for line in git(repo, "diff", "-M", "--name-status", a, b).splitlines():
        parts = line.split("\t")
        if parts and parts[0].startswith("R") and len(parts) == 3:
            m[parts[1]] = parts[2]
    return m


def numstat(repo, a, b):
    per, total, added_files = collections.Counter(), 0, 0
    for line in git(repo, "diff", "-M", "--numstat", a, b).splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not is_c(parts[2].split(" => ")[-1].rstrip("}")):
            continue
        add, rem = (int(x) if x.isdigit() else 0 for x in parts[:2])
        path = parts[2]
        if "=>" in path:  # rename: a/{x => y}/z or x => y
            mm = re.match(r"(.*)\{(.*) => (.*)\}(.*)", path)
            path = (mm.group(1) + mm.group(3) + mm.group(4)).replace("//", "/") if mm else path.split(" => ")[-1]
        per[path] += add + rem
        total += add + rem
    for line in git(repo, "diff", "-M", "--name-status", a, b).splitlines():
        parts = line.split("\t")
        if parts and parts[0] == "A" and is_c(parts[-1]):
            added_files += 1
    return per, total, added_files


def pairs(r, nets):
    repo = POOL_DIR / r
    out = []
    for t0, t1 in zip(nets, nets[1:]):
        rn = renames(repo, t0["sha"], t1["sha"])
        mv = lambda k: (rn.get(k[0], k[0]), k[1])  # noqa: E731
        n0 = {mv(k) for k in t0["nodes"]}
        e0 = {(mv(a), mv(b)) for a, b in t0["edges"]}
        P = n0 & t1["nodes"]
        e0p = {e for e in e0 if e[0] in P and e[1] in P}
        e1p = {e for e in t1["edges"] if e[0] in P and e[1] in P}
        diff = e0p ^ e1p
        R = len(diff)
        G = sum(1 for a, b in t1["edges"] if a not in P or b not in P) + sum(1 for a, b in e0 if a not in P or b not in P)
        U = len(e0p | e1p)
        per, C, newf = numstat(repo, t0["sha"], t1["sha"])
        rew_files = collections.Counter(a[0] for a, _ in diff)
        out.append({"t0": t0["ct"], "t1": t1["ct"], "sha1": t1["sha"], "R": R, "G": G, "C": C, "r": R / U if U else 0.0,
                    "new_files": newf, "file_churn": per, "rewired_files": rew_files})
    return out


# ------------------------------------------------------------------------------------------------- statistics
def gini(x):
    x = np.sort(np.asarray(x, float))
    if x.sum() == 0:
        return 0.0
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def top_decile_share(x):
    x = np.sort(np.asarray(x, float))[::-1]
    k = max(1, math.ceil(0.1 * len(x)))
    return float(x[:k].sum() / x.sum()) if x.sum() else 0.0


def block_boot(R, C, rng, B=5000, L=4):
    n = len(R)
    starts = np.arange(0, n - L + 1)
    out = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + L) for s in rng.choice(starts, math.ceil(n / L))])[:n]
        out.append(gini(np.asarray(R)[idx]) - gini(np.asarray(C)[idx]))
    return np.array(out)


def residuals(R, C):
    y, x = np.log1p(R), np.log1p(C)
    A = np.vstack([x, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ coef


def cmh(strata, greater=True):
    """strata: list of (a, b, c, d) = (exposed+, exposed-, unexposed+, unexposed-). One-sided CMH z and MH odds ratio."""
    sa = se = sv = num = den = 0.0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n < 2 or (a + b) == 0 or (c + d) == 0 or (a + c) == 0 or (b + d) == 0:
            continue
        e = (a + b) * (a + c) / n
        v = (a + b) * (c + d) * (a + c) * (b + d) / (n * n * (n - 1))
        sa, se, sv = sa + a, se + e, sv + v
        num += a * d / n
        den += b * c / n
    if sv == 0:
        return {"or": None, "z": None, "p": None}
    z = (sa - se) / math.sqrt(sv)
    return {"or": num / den if den else float("inf"), "z": z, "p": float(norm.sf(z) if greater else norm.cdf(z))}


# ------------------------------------------------------------------------------------------------- release tags
VER = re.compile(r"(\d+)[._](\d+)(?:[._](\d+))?([a-z]?)$")
PRE = re.compile(r"(alpha|beta|pre|rc|fips|tiny|test|dev|engine|snap)", re.I)


def releases(r):
    repo = POOL_DIR / r
    out = []
    for line in git(repo, "for-each-ref", "refs/tags", "--format=%(refname:short)\t%(*committerdate:unix)%(committerdate:unix)").splitlines():
        tag, _, ct = line.partition("\t")
        if PRE.search(tag) or not ct.strip():
            continue
        m = VER.search(tag)
        if not m or m.group(4):
            continue
        third = m.group(3)
        if third is None or int(third) == 0:
            out.append(int(ct.strip()[:10]))
    return sorted(out)


# ------------------------------------------------------------------------------------------------- CGT-3
def cgt3_sample(r, rng):
    xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
    ev = json.loads((REPO_ROOT / "events" / f"{r}.json").read_text())["events"]
    pools = {c: [e["sha"] for e in xc if e.get("class") == c and any(is_c(f) for f in e.get("c_files", []))]
             for c in CLASSES[:4]}
    pools["control"] = [e["sha"] for e in ev if e.get("class") == "control"]
    out = {}
    for c, shas in pools.items():
        shas = sorted(set(shas))
        rng.shuffle(shas)
        out[c] = shas
    return out


def cgt3_scan(r, sample, gg, py, scratch):
    repo = POOL_DIR / r
    root = scratch / "cgt3" / r
    db = sorted((root / "out").glob("*_galaxy_master.db"))
    meta_f = root / "meta.json"
    if db and meta_f.exists():
        return db[0], json.loads(meta_f.read_text())
    shutil.rmtree(root, ignore_errors=True)
    meta = {}
    for c, shas in sample.items():
        taken = 0
        for sha in shas:
            if taken >= CGT3_N:
                break
            par = git(repo, "rev-parse", f"{sha}^1").strip()
            if not par:
                continue
            files = []
            for line in git(repo, "diff", "-M", "--name-status", par, sha).splitlines():
                parts = line.split("\t")
                if parts and is_c(parts[-1]):
                    files.append((parts[1] if len(parts) == 3 else parts[-1], parts[-1]))
            if not files:
                continue
            _, size, _ = numstat(repo, par, sha)
            for old, new in files:
                for side, rev, path in (("a", par, old), ("b", sha, new)):
                    blob = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"], capture_output=True).stdout
                    if blob:
                        dest = root / "src" / side / sha[:12] / path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(blob)
            meta[sha[:12]] = {"class": c, "size": size, "parent_ct": int(git(repo, "show", "-s", "--format=%ct", par).strip() or 0)}
            taken += 1
    (root / "out").mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(gg), "GITGALAXY_LICENSE_KEY": "COMMUNITY_FREE_TIER",
           "GITGALAXY_DISABLE_GIT_HISTORY": "1"}
    with open(root / "scan.log", "w") as log:
        subprocess.run([py, "-m", "gitgalaxy.galaxyscope", str(root / "src"), "--output", str(root / "out") + "/"],
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    meta_f.write_text(json.dumps(meta))
    return sorted((root / "out").glob("*_galaxy_master.db"))[0], meta


def cgt3_rewire(db, meta, nets):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    sides = collections.defaultdict(lambda: {"a": [], "b": []})
    for path, name, loc, calls in con.execute("SELECT fd.file_path, f.func_name, f.loc, f.calls_out_to FROM function_data f "
                                              "JOIN file_data fd ON f.file_id = fd.id"):
        parts = Path(path).parts
        i = next((k for k in range(len(parts) - 2) if parts[k] in ("a", "b") and re.fullmatch(r"[0-9a-f]{12}", parts[k + 1])), None)
        if i is None:
            continue
        side, sha, rel = parts[i], parts[i + 1], "/".join(parts[i + 2:])
        if name and (loc or 0) >= 3 and side in ("a", "b"):
            sides[sha][side].append((rel, str(name).split("::")[-1], parse_calls(calls)))
    con.close()
    cts = [n["ct"] for n in nets]
    out = {}
    for sha, m in meta.items():
        k = max(0, np.searchsorted(cts, m["parent_ct"], side="right") - 1)
        names = set(nets[k]["names"]) | {n for s in ("a", "b") for _, n, _ in sides[sha][s]}
        ea = {(p, n, c) for p, n, cs in sides[sha]["a"] for c in cs if c in names and c != n}
        eb = {(p, n, c) for p, n, cs in sides[sha]["b"] for c in cs if c in names and c != n}
        out[sha] = {"class": m["class"], "size": m["size"], "rewire": int(bool(ea ^ eb)), "added": len(eb - ea),
                    "removed": len(ea - eb)}
    return out


# ------------------------------------------------------------------------------------------------- CGT-5
def wl_all(graphs, iters=3):
    """graphs: list of (nodes list, edges list) -> list of Counter histograms with shared relabel dictionary."""
    table, hists = {}, []
    for nodes, edges in graphs:
        ix = {n: i for i, n in enumerate(nodes)}
        outn, inn = collections.defaultdict(list), collections.defaultdict(list)
        for a, b in edges:
            outn[ix[a]].append(ix[b])
            inn[ix[b]].append(ix[a])
        lab = [table.setdefault(("d", len(inn[i]), len(outn[i])), len(table)) for i in range(len(nodes))]
        h = collections.Counter(lab)
        for _ in range(iters):
            lab = [table.setdefault((lab[i], tuple(sorted(lab[j] for j in outn[i])), tuple(sorted(lab[j] for j in inn[i]))),
                                    len(table)) for i in range(len(nodes))]
            h.update(lab)
        hists.append(h)
    return hists


def cos(a, b):
    d = sum(a[k] * b[k] for k in (a.keys() & b.keys()))
    na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
    return d / (na * nb) if na and nb else 0.0


def keyword_mix(r, nets):
    cols = None
    con = sqlite3.connect(f"file:{S.DBS[r]}?mode=ro", uri=True)
    have = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
    cols = sorted(c for c in have if re.match(r"^(struct|state|def|arch)_", c))
    want = {n["sha"] for n in nets}
    fids = collections.defaultdict(list)
    for fid, path, sha in con.execute("SELECT id, file_path, commit_hash FROM file_data"):
        if sha in want and path and is_c(path):
            fids[sha].append(fid)
    out = []
    for n in nets:
        ids = fids.get(n["sha"], [])
        v = np.zeros(len(cols))
        for i in range(0, len(ids), 900):
            ch = ids[i:i + 900]
            q = f"SELECT {', '.join('COALESCE(SUM(' + c + '),0)' for c in cols)} FROM function_data WHERE file_id IN ({','.join('?' * len(ch))})"
            v += np.array(con.execute(q, ch).fetchone(), float)
        out.append(v / v.sum() if v.sum() else v)
    con.close()
    return out


def identify(items, sim):
    """items: list of (repo, ct, rep). Hit if the nearest among other repos + own repo >= 5 y away is own repo."""
    hits = tot = 0
    for i, (r, ct, x) in enumerate(items):
        own = [j for j, (r2, ct2, _) in enumerate(items) if r2 == r and abs(ct2 - ct) >= 5 * YEAR]
        if not own:
            continue
        other = [j for j, (r2, _, _) in enumerate(items) if r2 != r]
        so = max(sim(x, items[j][2]) for j in own)
        sx = max(sim(x, items[j][2]) for j in other)
        tot += 1
        hits += so > sx  # ties pessimistic
    return hits, tot


# ------------------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gg", type=Path, required=True)
    ap.add_argument("--py", default=sys.executable)
    ap.add_argument("--scratch", type=Path, required=True)
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    res, nets, prs = {}, {}, {}
    for r in REPOS:
        nets[r] = snapshot_networks(r, a.scratch)
        pk = a.scratch / f"pairs_{r}.pkl"
        if pk.exists():
            prs[r] = pickle.loads(pk.read_bytes())
        else:
            prs[r] = pairs(r, nets[r])
            pk.write_bytes(pickle.dumps(prs[r]))
        print(f"{r}: {len(nets[r])} snapshots, {len(prs[r])} pairs", file=sys.stderr, flush=True)
    # CGT-1
    a1 = 0.01 / 3
    c1 = {}
    for r in REPOS:
        R = [p["R"] for p in prs[r]]
        C = [p["C"] for p in prs[r]]
        boots = block_boot(R, C, rng)
        c1[r] = {"pairs": len(R), "median_r": float(np.median([p["r"] for p in prs[r]])),
                 "top_decile_share_R": top_decile_share(R), "top_decile_share_C": top_decile_share(C),
                 "gini_R": gini(R), "gini_C": gini(C), "gini_diff": gini(R) - gini(C),
                 "gini_diff_lo": float(np.quantile(boots, a1)), "total_R": int(sum(R)),
                 "total_G": int(sum(p["G"] for p in prs[r]))}
    res["CGT-1"] = {"per_repo": c1,
                    "1a": {"repos_pass": sum(v["median_r"] < 0.02 for v in c1.values())},
                    "1b": {"repos_pass": sum(v["top_decile_share_R"] >= 0.40 for v in c1.values())},
                    "1c": {"repos_pass": sum(v["gini_diff_lo"] > 0 for v in c1.values())}}
    for k in ("1a", "1b", "1c"):
        res["CGT-1"][k]["verdict"] = "supported" if res["CGT-1"][k]["repos_pass"] >= 4 else "not supported"
    # CGT-2
    rows = []
    for r in REPOS:
        rel = releases(r)
        res.setdefault("releases_found", {})[r] = len(rel)
        resid = residuals([p["R"] for p in prs[r]], [p["C"] for p in prs[r]])
        for p, e in zip(prs[r], resid):
            rows.append((r, e, int(any(p["t0"] < t <= p["t1"] for t in rel)), p["new_files"]))
    reps = np.array([x[0] for x in rows])
    E = np.array([x[1] for x in rows])
    REL = np.array([x[2] for x in rows])
    NEW = np.array([x[3] for x in rows], float)

    def reldiff(lbl):
        return E[lbl == 1].mean() - E[lbl == 0].mean() if lbl.sum() and (lbl == 0).sum() else 0.0

    def spear(x):
        from scipy.stats import spearmanr
        return float(spearmanr(x, E).statistic)

    obs_a, obs_b = reldiff(REL), spear(NEW)
    ga = gb = 0
    groups = {r: np.flatnonzero(reps == r) for r in REPOS}
    for _ in range(10000):
        L, X = REL.copy(), NEW.copy()
        for idx in groups.values():
            L[idx] = rng.permutation(L[idx])
            X[idx] = rng.permutation(X[idx])
        ga += reldiff(L) >= obs_a
        gb += spear(X) >= obs_b
    pa, pb = (1 + ga) / 10001, (1 + gb) / 10001
    res["CGT-2"] = {"pairs": len(rows), "release_pairs": int(REL.sum()),
                    "2a": {"mean_resid_diff": obs_a, "p": pa, "verdict": "supported" if pa < 0.005 and obs_a > 0 else "not supported"},
                    "2b": {"spearman": obs_b, "p": pb, "verdict": "supported" if pb < 0.005 and obs_b > 0 else "not supported"}}
    # CGT-3
    allc = []
    for r in REPOS:
        sample = cgt3_sample(r, np.random.default_rng(SEED))
        db, meta = cgt3_scan(r, sample, a.gg, a.py, a.scratch)
        rw = cgt3_rewire(db, meta, nets[r])
        sizes = np.array([v["size"] for v in rw.values()], float)
        qs = np.quantile(sizes, [0.2, 0.4, 0.6, 0.8]) if len(sizes) else []
        for sha, v in rw.items():
            allc.append({**v, "repo": r, "q": int(np.searchsorted(qs, v["size"], side="right"))})

    def strata(x, y):
        st = collections.defaultdict(lambda: [0, 0, 0, 0])
        for v in allc:
            if v["class"] not in (x, y):
                continue
            s = st[(v["repo"], v["q"])]
            if v["class"] == x:
                s[0 if v["rewire"] else 1] += 1
            else:
                s[2 if v["rewire"] else 3] += 1
        return [tuple(s) for s in st.values()]

    cnt = collections.Counter(v["class"] for v in allc)
    rate = {c: float(np.mean([v["rewire"] for v in allc if v["class"] == c])) if cnt[c] else None for c in CLASSES}
    h3a = cmh(strata("regression", "latent"), greater=True)
    h3b = cmh(strata("latent", "other-fix"), greater=False)
    ok = lambda h, gt: h["p"] is not None and h["p"] < 0.005 and (h["or"] > 1 if gt else h["or"] < 1)  # noqa: E731
    res["CGT-3"] = {"commits": dict(cnt), "rewire_rate": rate,
                    "median_size": {c: float(np.median([v["size"] for v in allc if v["class"] == c])) if cnt[c] else None for c in CLASSES},
                    "3a": {**h3a, "verdict": ("not evaluable" if min(cnt["regression"], cnt["latent"]) < 30 else
                                              "supported" if ok(h3a, True) else "not supported")},
                    "3b": {**h3b, "verdict": ("not evaluable" if min(cnt["latent"], cnt["other-fix"]) < 30 else
                                              "supported" if ok(h3b, False) else "not supported")},
                    "descriptive": {"extrinsic_vs_other": cmh(strata("extrinsic", "other-fix")),
                                    "control_vs_other": cmh(strata("control", "other-fix"))}}
    # CGT-4
    st4 = collections.defaultdict(lambda: [0, 0, 0, 0])
    pos_by_repo = collections.Counter()
    for r in REPOS:
        xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
        fix = collections.defaultdict(list)
        for e in xc:
            for f in e.get("c_files", []):
                fix[f].append(e["ct"])
        lo, hi = min(e["ct"] for e in xc), max(e["ct"] for e in xc)
        rows4 = []
        for p in prs[r]:
            if p["t1"] < lo or p["t1"] + YEAR > hi:
                continue
            for f, ch in p["file_churn"].items():
                if ch <= 0:
                    continue
                y = int(any(p["t1"] < t <= p["t1"] + YEAR for t in fix.get(f, ())))
                rows4.append((f in p["rewired_files"], ch, y))
        if not rows4:
            continue
        qs = np.quantile([x[1] for x in rows4], [0.2, 0.4, 0.6, 0.8])
        for rew, ch, y in rows4:
            s = st4[(r, int(np.searchsorted(qs, ch, side="right")))]
            if rew:
                pos_by_repo[r] += 1
                s[0 if y else 1] += 1
            else:
                s[2 if y else 3] += 1
    h4 = cmh([tuple(s) for s in st4.values()], greater=True)
    ev4 = [r for r in REPOS if pos_by_repo[r] >= 20]
    res["CGT-4"] = {**h4, "rewired_file_quarters": dict(pos_by_repo), "repos_evaluable": ev4,
                    "verdict": ("not evaluable" if not ev4 else
                                "supported" if h4["p"] is not None and h4["p"] < 0.01 and h4["or"] > 1 else "not supported")}
    # CGT-5
    items, kitems = [], []
    for r in REPOS:
        hists = wl_all([(sorted(n["nodes"]), sorted(n["edges"])) for n in nets[r]])
        mixes = keyword_mix(r, nets[r])
        for n, h, m in zip(nets[r], hists, mixes):
            items.append((r, n["ct"], h))
            kitems.append((r, n["ct"], m))
    h5, t5 = identify(items, cos)
    kh, kt = identify(kitems, lambda x, y: float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y))) if x.any() and y.any() else 0.0)
    res["CGT-5"] = {"hits": h5, "queries": t5, "rate": h5 / t5 if t5 else None,
                    "verdict": "supported" if t5 and h5 / t5 >= 0.90 else "not supported",
                    "descriptive_keyword_mix": {"hits": kh, "queries": kt, "rate": kh / kt if kt else None}}
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
