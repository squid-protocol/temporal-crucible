#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS defect panel (methods review M7): one row per (unit source file, yearly snapshot t). No model is fitted.

    file_years(net_db, history_db, language, labels)  ->  list of dict rows, and a summary

`labels` is optional and revises the fix label per commit sha: pass tools/laws_github.fix_labels(...) to compute
the defect laws from the M6 workflow label (PR title and body, linked-issue labels) instead of the keyword label.
The summary records how many labels it changed.

A file-year is kept iff t >= first snapshot + 1 year, t + WINDOW days <= the last commit the history covers, and
the file is a unit file at t.

  outcome   1 when a fix commit touches the file in (t, t + WINDOW]; the file is followed through renames by its
            lineage (tools/laws_history.py). A file deleted in the window with no fix keeps outcome 0 and is
            flagged `deleted`.
  fix_commit   the first such fix commit (for clustering), else None
  controls (the year up to t; bots excluded): loc, functions, churn (commits touching the file), prior_fixes,
            authors (distinct), coupled (other unit files changed with it in >= COUPLE_MIN commits, commits that
            touch more than SWEEP unit files left out), year
  network (size-neutral): k_max and k_mean (function in-degree), callers and callees (distinct other files that
            call into / are called from the file: static fan-in and fan-out), scc (size of the file's strongly
            connected component in the file graph), in_cycle (2 <= scc <= ceil(GIANT * files)), giant (scc above
            that)
"""
from __future__ import annotations

import collections
import datetime as dt
import math
import sqlite3
import sys
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph

sys.path.insert(0, str(Path(__file__).parent))
import laws_net as N  # noqa: E402

DAY = 86400
WINDOW = 365
COUPLE_MIN = 3
SWEEP = 50
GIANT = 0.2


def epoch(date: str) -> int:
    return int(dt.datetime.fromisoformat(str(date)).timestamp())


class History:
    """Read-only views of a tools/laws_history.py database."""

    def __init__(self, db: Path, labels: dict[str, bool] | None = None):
        """`labels` revises the fix label per commit sha (tools/laws_github.py's `fix_labels`, the M6 workflow
        rules: a merge unit labelled from its PR's title and body, and linked-issue labels). A sha the mapping
        does not name keeps the database's own label, which is what a bot's commit, a commit touching no unit
        source file, and every commit of a repo that is not on github.com all fall back to."""
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        self.meta = dict(con.execute("SELECT key, value FROM meta"))
        self.last_ct = int(self.meta["last_ct"])
        raw = {sha: (ct, author, bot, fix) for sha, ct, author, bot, fix in
               con.execute("SELECT sha, ct, author, bot, fix FROM commit_")}
        self.labels_applied = {"given": len(labels or {}), "changed": 0, "made": 0, "unmade": 0}
        if labels:
            for sha, (ct, author, bot, fix) in list(raw.items()):
                new_fix = int(bool(labels.get(sha, fix)))
                if new_fix != fix:
                    self.labels_applied["changed"] += 1
                    self.labels_applied["made" if new_fix else "unmade"] += 1
                    raw[sha] = (ct, author, bot, new_fix)
        self.commits = raw
        self.by_file: dict[int, list] = collections.defaultdict(list)  # lineage -> [(ct, sha)] ascending
        self.files_of: dict[str, list] = collections.defaultdict(list)  # sha -> [lineage]
        for sha, fid in con.execute("SELECT DISTINCT sha, file FROM touch"):
            self.by_file[fid].append((self.commits[sha][0], sha))
            self.files_of[sha].append(fid)
        for v in self.by_file.values():
            v.sort()
        self.paths: dict[str, list] = collections.defaultdict(list)  # path -> [(since, until, lineage)]
        self.until: dict[int, int | None] = {}
        for fid, path, since, until in con.execute("SELECT file, path, since, until FROM lineage ORDER BY since"):
            self.paths[path].append((since, until, fid))
            self.until[fid] = until  # the last interval's end: None while the file lives
        con.close()

    def lineage(self, path: str, t: int) -> int | None:
        for since, until, fid in self.paths.get(path, ()):
            if since <= t and (until is None or t < until):
                return fid
        return None

    def between(self, fid: int, lo: int, hi: int) -> list:
        """The (ct, sha) of commits touching lineage fid with lo < ct <= hi."""
        return [(ct, sha) for ct, sha in self.by_file.get(fid, ()) if lo < ct <= hi]


def file_graph(net) -> dict:
    """Per file of a network: k_max, k_mean, callers, callees, scc, functions."""
    files = sorted(net.files())
    idx = {f: i for i, f in enumerate(files)}
    indeg = net.in_degree()
    ks: dict[str, list] = collections.defaultdict(list)
    for node in net.nodes:
        if not net.nodes[node]["test"]:
            ks[node[0]].append(indeg.get(node, 0))
    callers: dict[str, set] = collections.defaultdict(set)
    callees: dict[str, set] = collections.defaultdict(set)
    for u, v in net.edges:
        if u[0] != v[0] and u[0] in idx and v[0] in idx:
            callers[v[0]].add(u[0])
            callees[u[0]].add(v[0])
    src = [idx[a] for b in callers for a in callers[b]]
    dst = [idx[b] for b in callers for _ in callers[b]]
    g = sparse.csr_matrix((np.ones(len(src), dtype=np.int8), (src, dst)), shape=(len(files), len(files)))
    _, comp = csgraph.connected_components(g, directed=True, connection="strong")
    size = np.bincount(comp)
    return {f: {"k_max": max(ks[f]) if ks[f] else 0, "k_mean": float(np.mean(ks[f])) if ks[f] else 0.0,
                "callers": len(callers[f]), "callees": len(callees[f]), "scc": int(size[comp[idx[f]]]),
                "functions": len(ks[f])} for f in files}


def file_years(net_db: Path, history_db: Path, language: str,
               labels: dict[str, bool] | None = None) -> tuple[list[dict], dict]:
    con = sqlite3.connect(f"file:{net_db}?mode=ro", uri=True)
    hist = History(history_db, labels)
    yearly = N.yearly(N.snapshots(con))
    rows: list[dict] = []
    summary = {"snapshots_yearly": len(yearly), "snapshots_used": 0, "unmatched_files": 0, "deleted_in_window": 0}
    if not yearly:
        return rows, summary
    first = epoch(yearly[0][1])
    for sha, date, boundary in yearly:
        t = epoch(date)
        if t < first + 365 * DAY or t + WINDOW * DAY > hist.last_ct:
            continue
        net = N.network(con, sha, date, language)
        fg = file_graph(net)
        n_files = len(fg)
        loc = dict(con.execute("SELECT path, coding_loc FROM file WHERE commit_hash = ?", (sha,)))
        cap = math.ceil(GIANT * n_files)
        summary["snapshots_used"] += 1
        # change coupling in the prior year: pairs of unit files in commits of at most SWEEP unit files
        pairs: collections.Counter = collections.Counter()
        lineages = {}
        for f in fg:
            lineages[f] = hist.lineage(f, t)
        wanted = {fid for fid in lineages.values() if fid is not None}
        seen_commits = set()
        for fid in wanted:
            for _, c in hist.between(fid, t - 365 * DAY, t):
                seen_commits.add(c)
        for c in seen_commits:
            if hist.commits[c][2]:
                continue
            fs = [x for x in hist.files_of[c] if x in wanted]
            if len(hist.files_of[c]) > SWEEP:
                continue
            for a in fs:
                for b in fs:
                    if a != b:
                        pairs[(a, b)] += 1
        coupled = collections.Counter(a for (a, _), n in pairs.items() if n >= COUPLE_MIN)
        for f, m in fg.items():
            fid = lineages[f]
            if fid is None:
                summary["unmatched_files"] += 1
                continue
            prior = [(ct, c) for ct, c in hist.between(fid, t - 365 * DAY, t) if not hist.commits[c][2]]
            after = hist.between(fid, t, t + WINDOW * DAY)
            fixes = [(ct, c) for ct, c in after if hist.commits[c][3]]
            gone = hist.until.get(fid)
            deleted = int(not fixes and gone is not None and t < gone <= t + WINDOW * DAY)
            summary["deleted_in_window"] += deleted
            rows.append({"file": fid, "path": f, "t": t, "year": int(str(boundary)[:4]), "outcome": int(bool(fixes)),
                         "fix_commit": fixes[0][1] if fixes else None, "deleted": deleted,
                         "loc": int(loc.get(f) or 0), "functions": m["functions"], "churn": len(prior),
                         "prior_fixes": sum(1 for _, c in prior if hist.commits[c][3]),
                         "authors": len({hist.commits[c][1] for _, c in prior}), "coupled": coupled.get(fid, 0),
                         "k_max": m["k_max"], "k_mean": m["k_mean"], "callers": m["callers"], "callees": m["callees"],
                         "scc": m["scc"], "in_cycle": int(2 <= m["scc"] <= cap), "giant": int(m["scc"] > cap)})
    summary.update(rows=len(rows), positives=sum(r["outcome"] for r in rows),
                   in_cycle_share=float(np.mean([r["in_cycle"] for r in rows])) if rows else None,
                   giant_share=float(np.mean([r["giant"] for r in rows])) if rows else None,
                   history_unit=hist.meta.get("unit"), fix_labels=hist.labels_applied)
    return rows, summary
