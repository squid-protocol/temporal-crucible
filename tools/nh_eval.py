#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""NH: natural history of code structure -- LIFE-H1..H3 (function lifecycles) and HUB-H1..H3 (include-graph hubs).
docs/nh_hypotheses.md, registered 2026-11-06.

    python tools/nh_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import os
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402

WT = pathlib.Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
       "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
       "openssl": WT / "frec/dbs/openssl_out/openssl_galaxy_master.db",
       "harfbuzz": WT / "sc-class/dbs/harfbuzz_out/harfbuzz_galaxy_master.db",
       "libarchive": WT / "sc-class/dbs/libarchive_out/libarchive_galaxy_master.db"}
YEAR, SEED, ITERS = 365.25 * 86400, 2982, 5000
BANDS = [(0, 1, "< 1 y"), (1, 3, "1–3 y"), (3, 5, "3–5 y"), (5, 1e9, "≥ 5 y")]


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def snapshots(r):
    repo = POOL_DIR / r
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    have = {x[0] for x in con.execute("SELECT DISTINCT commit_hash FROM repo_data")}
    con.close()
    seen, out = set(), []
    for s in json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())["revisions"]:
        if s.get("status", "ok") == "ok" and s["sha"] in have and s["sha"] not in seen:
            seen.add(s["sha"])
            out.append({"sha": s["sha"], "ct": int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())})
    return sorted(out, key=lambda s: s["ct"])


def band(age):
    for i, (lo, hi, _) in enumerate(BANDS):
        if lo <= age < hi:
            return i
    return len(BANDS) - 1


# ---------------------------------------------------------------------------------------------------- LIFE
def life(r):
    snaps = snapshots(r)
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    per_snap = []
    for s in snaps:
        rows = con.execute("SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.complexity, f.func_archetype "
                           "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE fd.commit_hash = ? "
                           "AND fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''", (s["sha"],)).fetchall()
        d = {}
        for path, name, start, loc, cx, arch in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):
            d.setdefault((path, name), (loc or 0, cx or 0, arch or ""))
        per_snap.append(d)
    con.close()
    fid, nxt = {}, 0
    birth, last = {}, {}
    trans = []  # (k, fid, age_years, survived, shape_changed, locx_changed, arch_changed, a0, a1)
    prev = None
    for k, d in enumerate(per_snap):
        cur = {}
        if prev is not None:
            vanished = [key for key in prev if key not in d]
            new = [key for key in d if key not in prev]
            vn, nn = defaultdict(list), defaultdict(list)
            for key in vanished:
                vn[key[1]].append(key)
            for key in new:
                nn[key[1]].append(key)
            moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
        else:
            moved = {}
        for key in d:
            if prev is not None and key in prev:
                cur[key] = prev_ids[key]
            elif key in moved:
                cur[key] = prev_ids[moved[key]]
            else:
                cur[key] = nxt
                birth[nxt] = k
                nxt += 1
            last[cur[key]] = k
        if prev is not None:
            inv = {v: key for key, v in cur.items()}
            for key, f in prev_ids.items():
                if birth[f] == 0:
                    continue  # left-truncated: age unknown
                age = (snaps[k - 1]["ct"] - snaps[birth[f]]["ct"]) / YEAR
                if f in inv:
                    a, b = prev[key], d[inv[f]]
                    trans.append((k - 1, age, 1, a != b, a[:2] != b[:2], a[2] != b[2], a[2], b[2]))
                else:
                    trans.append((k - 1, age, 0, False, False, False, prev[key][2], ""))
        prev, prev_ids = d, cur
    # Kaplan-Meier over functions born after snapshot 0
    K = len(snaps) - 1
    life_years, event = [], []
    for f, b in birth.items():
        if b == 0:
            continue
        end = last[f]
        died = end < K
        life_years.append((snaps[min(end + 1, K)]["ct"] - snaps[b]["ct"]) / YEAR if died else (snaps[K]["ct"] - snaps[b]["ct"]) / YEAR)
        event.append(died)
    return {"snaps": len(snaps), "trans": trans, "km": (np.array(life_years), np.array(event)), "n_funcs": nxt}


def km(t, e, at):
    """Kaplan-Meier: (median survival, {a: S(a)}). t = durations in years, e = 1 if the event (death) was observed."""
    order = np.argsort(t, kind="stable")
    t, e = t[order], e[order].astype(int)
    times = np.unique(t)
    s, n_risk, curve = 1.0, len(t), []
    for u in times:
        m = t == u
        d = int(e[m].sum())
        if n_risk and d:
            s *= 1 - d / n_risk
        curve.append((u, s))
        n_risk -= int(m.sum())
    median = next((u for u, v in curve if v <= 0.5), None)
    surv = {a: next((v for u, v in reversed(curve) if u <= a), 1.0) for a in at}
    return median, surv


def life_counts(tr):
    """Per transition-snapshot k: counts per age band -> array [k, 2*B + 2] of
    (deaths_b, atrisk_b) for B bands, (changes_b, alive_b) for B bands, (arch_kept, locx_changed)."""
    B = len(BANDS)
    out = defaultdict(lambda: np.zeros(4 * B + 2))
    for k, age, surv, sh, lc, ac, _a0, _a1 in tr:
        v = out[k]
        b = band(age)
        v[2 * b + 1] += 1
        if not surv:
            v[2 * b] += 1
        else:
            v[2 * B + 2 * b + 1] += 1
            if sh:
                v[2 * B + 2 * b] += 1
            if lc:
                v[4 * B + 1] += 1
                if not ac:
                    v[4 * B] += 1
    return np.array([out[k] for k in sorted(out)])


def rates(c):
    """From summed counts: death hazard per band, change rate per band, archetype-kept share."""
    B = len(BANDS)
    d = [c[2 * b] / c[2 * b + 1] if c[2 * b + 1] else float("nan") for b in range(B)]
    ch = [c[2 * B + 2 * b] / c[2 * B + 2 * b + 1] if c[2 * B + 2 * b + 1] else float("nan") for b in range(B)]
    old = (c[2 * B + 4] + c[2 * B + 6]) / (c[2 * B + 5] + c[2 * B + 7]) if (c[2 * B + 5] + c[2 * B + 7]) else float("nan")  # >= 3 y
    return d, ch, old, (c[4 * B] / c[4 * B + 1] if c[4 * B + 1] else float("nan"))


def ratio(o, a, b):
    (x1, n1), (x2, n2) = o[a], o[b]
    return (x1 / n1) / (x2 / n2) if n1 and n2 and x2 else float("nan")


# ---------------------------------------------------------------------------------------------------- HUB
def hub_snapshot(task):
    r, sha = task
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    files = {p: loc or 0 for p, loc in con.execute("SELECT file_path, total_loc FROM file_data WHERE commit_hash=? AND language IN ('c','cpp')", (sha,))}
    edges = con.execute("SELECT s.file_path, d.file_path FROM edge_data e JOIN file_data s ON e.src_file_id = s.id JOIN file_data d ON e.dst_file_id = d.id "
                        "WHERE e.commit_hash = ? AND e.edge_kind = 'import'", (sha,)).fetchall()
    con.close()
    srcs = defaultdict(set)
    for a, b in edges:
        if a in files and b in files and a != b:
            srcs[b].add(a)
    blobs = {}
    for line in _git(POOL_DIR / r, "-c", "core.quotepath=off", "ls-tree", "-r", sha).splitlines():
        meta, _, path = line.partition("\t")
        if path in files:
            blobs[path] = meta.split()[2]
    return sha, files, {p: srcs.get(p, set()) for p in files}, blobs


def hub(r):
    snaps = snapshots(r)
    with multiprocessing.get_context("fork").Pool(6) as p:
        data = {sha: (f, s, b) for sha, f, s, b in p.imap_unordered(hub_snapshot, [(r, x["sha"]) for x in snaps])}
    cts = [x["ct"] for x in snaps]
    pers, slopes_x, slopes_y, mh = [], [], [], []
    for i, s in enumerate(snaps):
        j = next((j for j in range(i + 1, len(snaps)) if cts[j] >= cts[i] + YEAR), None)
        if j is None:
            break
        f0, s0, b0 = data[s["sha"]]
        f1, s1, b1 = data[snaps[j]["sha"]]
        deg0 = {p: len(v) for p, v in s0.items()}
        deg1 = {p: len(v) for p, v in s1.items()}
        th0 = max(np.quantile(list(deg0.values()), 0.9), 1)
        th1 = max(np.quantile(list(deg1.values()), 0.9), 1)
        hubs0 = {p for p, k in deg0.items() if k >= th0}
        hubs1 = {p for p, k in deg1.items() if k >= th1}
        if hubs0:
            pers.append((i, len(hubs0 & hubs1) / len(hubs0)))
        common = [p for p in f0 if p in f1]
        xs = np.array([np.log(deg0[p] + 1) for p in common])
        ys = np.array([np.log(len(s1[p] - s0[p]) + 1) for p in common])
        slopes_x.append(xs)
        slopes_y.append(ys)
        # frozen core: MH risk ratio hub vs non-hub, strata = ext x LOC decile (snapshot is the outer stratum)
        both = [p for p in common if p in b0 and p in b1]
        if len(both) < 20:
            continue
        loc = np.array([f0[p] for p in both], float)
        dec = np.searchsorted(np.quantile(loc, np.linspace(0, 1, 11)[1:-1]), loc, side="right")
        ext = np.array([p.endswith((".h", ".hh", ".hpp")) for p in both])
        hb = np.array([p in hubs0 for p in both])
        ch = np.array([b0[p] != b1[p] for p in both])
        num = den = 0.0
        for key in set(zip(ext, dec)):
            m = (ext == key[0]) & (dec == key[1])
            n1, n0 = hb[m].sum(), (~hb[m]).sum()
            if n1 and n0:
                N = n1 + n0
                num += (ch[m] & hb[m]).sum() * n0 / N
                den += (ch[m] & ~hb[m]).sum() * n1 / N
        mh.append((num, den))
    return {"pers": pers, "sx": slopes_x, "sy": slopes_y, "mh": mh, "snaps": len(snaps)}


def slope(xs, ys):
    x, y = np.concatenate(xs), np.concatenate(ys)
    return float(np.polyfit(x, y, 1)[0]) if len(x) > 2 and x.std() > 0 else float("nan")


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    L = ["# NH — natural history: function lifecycles and include-graph hubs (SCORED)", ""]
    life_res, hub_res = {}, {}
    for r in DBS:
        life_res[r] = life(r)
        hub_res[r] = hub(r)
        print(f"{r}: done ({time.time() - t0:.0f}s)", flush=True)

    # ---------------- LIFE
    L += ["## Part 1 — function lifecycles", "",
          "| repo | snapshots | functions tracked | median lifespan (born after first snapshot) | alive at 5 y | alive at 10 y |",
          "|---|---:|---:|---:|---:|---:|"]
    counts = {}
    for r, d in life_res.items():
        t, e = d["km"]
        med, sa = km(t, e, [5, 10])
        counts[r] = life_counts(d["trans"])
        L.append(f"| {r} | {d['snaps']} | {d['n_funcs']:,} | {('%.1f y' % med) if med is not None else '> span'} | {sa[5]:.0%} | {sa[10]:.0%} |")
    L += ["", "Quarterly death hazard and shape-change rate by age (functions born after the first snapshot):", "",
          "| repo | " + " | ".join(f"death {lab}" for *_, lab in BANDS) + " | " + " | ".join(f"shape change {lab}" for *_, lab in BANDS) + " |",
          "|---|" + "---:|" * (2 * len(BANDS))]
    per = {}
    for r, c in counts.items():
        d, ch, old, ak = rates(c.sum(axis=0))
        per[r] = (d[0] / d[2], old / ch[0], ak)
        L.append(f"| {r} | " + " | ".join(f"{x:.3f}" for x in d) + " | " + " | ".join(f"{x:.3f}" for x in ch) + " |")
    pooled = sum(c.sum(axis=0) for c in counts.values())
    pd_, pch, pold, pak = rates(pooled)
    boots = []
    for _ in range(ITERS):
        tot = sum(c[rng.integers(0, len(c), len(c))].sum(axis=0) for c in counts.values())
        d, ch, old, ak = rates(tot)
        boots.append((d[0] / d[2], old / ch[0], ak))
    boots = np.array(boots)
    h1 = [v[0] for v in per.values()]
    h2 = [v[1] for v in per.values()]
    h3 = [v[2] for v in per.values()]
    lo1, hi2, lo3 = np.quantile(boots[:, 0], 0.01), np.quantile(boots[:, 1], 0.99), np.quantile(boots[:, 2], 0.01)
    L += ["", "| claim | per repo (curl / nDPI / openssl / harfbuzz / libarchive) | pooled | bound | verdict |", "|---|---|---:|---:|---|",
          f"| **LIFE-H1** infant mortality: hazard(< 1 y) / hazard(3–5 y) | {' / '.join(f'{x:.2f}' for x in h1)} | {pd_[0] / pd_[2]:.2f} | lo {lo1:.2f} | "
          f"**{'SUPPORTED' if sum(x > 1 for x in h1) >= 4 and lo1 > 1 else 'not supported'}** |",
          f"| **LIFE-H2** structural freeze: change rate(≥ 3 y) / (< 1 y) | {' / '.join(f'{x:.2f}' for x in h2)} | {pold / pch[0]:.2f} | hi {hi2:.2f} | "
          f"**{'SUPPORTED' if sum(x < 1 for x in h2) >= 4 and hi2 < 1 else 'not supported'}** |",
          f"| **LIFE-H3** archetype kept when (loc, complexity) changed | {' / '.join(f'{x:.2f}' for x in h3)} | {pak:.3f} | lo {lo3:.3f} | "
          f"**{'SUPPORTED' if lo3 > 0.80 else 'not supported'}** |"]
    tc = Counter()
    for d in life_res.values():
        for x in d["trans"]:
            if x[2] == 1 and x[5]:
                tc[(x[6], x[7])] += 1
    L += ["", "Most common archetype transitions (pooled):", ""] + [f"- {a} → {b}: {n:,}" for (a, b), n in tc.most_common(10)]

    # ---------------- HUB
    L += ["", "## Part 2 — include-graph hubs", "",
          "| repo | hub persistence after 1 y (median) | attachment slope (log gain ~ log in-degree) | lo | frozen core RR (hub vs non-hub, changed in 1 y) |",
          "|---|---:|---:|---:|---:|"]
    h1ok = h2ok = 0
    num_all = den_all = 0.0
    mh_boot_parts = []
    for r, d in hub_res.items():
        pm = float(np.median([x for _, x in d["pers"]])) if d["pers"] else float("nan")
        sl = slope(d["sx"], d["sy"])
        ss = np.array([[len(x), x.sum(), y.sum(), (x * x).sum(), (x * y).sum()] for x, y in zip(d["sx"], d["sy"])])
        bs = []
        for _ in range(ITERS):
            n_, sx, sy, sxx, sxy = ss[rng.integers(0, len(ss), len(ss))].sum(axis=0)
            den_ = n_ * sxx - sx * sx
            bs.append((n_ * sxy - sx * sy) / den_ if den_ else np.nan)
        lo = float(np.nanquantile(bs, 0.005))
        num, den = sum(x for x, _ in d["mh"]), sum(y for _, y in d["mh"])
        num_all += num
        den_all += den
        mh_boot_parts.append(np.array(d["mh"]))
        h1ok += pm > 0.70
        h2ok += sl > 0 and lo > 0
        L.append(f"| {r} | {pm:.2f} | {sl:.3f} | {lo:.3f} | {num / den if den else float('nan'):.2f} |")
    bmh = []
    for _ in range(ITERS):
        nn = dd = 0.0
        for a in mh_boot_parts:
            s = a[rng.integers(0, len(a), len(a))].sum(axis=0)
            nn += s[0]
            dd += s[1]
        bmh.append(nn / dd)
    rr = num_all / den_all
    hi = float(np.quantile(bmh, 0.99))
    L += ["", "| claim | result | verdict |", "|---|---|---|",
          f"| **HUB-H1** hubs stable (median 1-y persistence > 0.70 on ≥ 4/5) | {h1ok}/5 repos | **{'SUPPORTED' if h1ok >= 4 else 'not supported'}** |",
          f"| **HUB-H2** rich get richer (slope lo > 0 on ≥ 4/5) | {h2ok}/5 repos | **{'SUPPORTED' if h2ok >= 4 else 'not supported'}** |",
          f"| **HUB-H3** frozen core (pooled MH RR < 1, upper bound < 1) | RR {rr:.2f}, hi {hi:.2f} | **{'SUPPORTED' if rr < 1 and hi < 1 else 'not supported'}** |",
          "", f"Runtime {time.time() - t0:.0f}s · snapshot bootstraps within repo, {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "nh.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
