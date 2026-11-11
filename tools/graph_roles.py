#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Import-graph roles and role changes between two scan snapshots (tc#171, step 1).

**EXPLORATORY instrument, no verdicts.** This tool only *measures*: it emits,
per file, the import-graph role at a parent snapshot and at a child snapshot,
the transition between them, and the degree / centrality deltas. Any test of
"do fixes rewire the graph more than controls" is a later, separately
registered step (see tc#171 and docs/HYPOTHESES.md); nothing here computes
a p-value.

**Roles** — per snapshot, percentile cutoffs computed *within that snapshot*
(nearest-rank over every file in it), so the definitions stay scale-free
across curl's 39 -> 1,144-file growth:

    hub           popularity (in-degree)   >= p<pct> and > 0
    orchestrator  import_count (out-degree) >= p<pct> and > 0
    bridge        betweenness_score         >= p<pct> and > 0 (None -> not a bridge)
    isolate       in-degree 0 and out-degree 0
    spoke         in-degree <= 1, none of the above
    other         everything else

Betweenness is sparse in C include graphs: in the curl fixture only 4-6% of
files have betweenness > 0, so the p90 cutoff is 0 and "bridge" reduces to
"any positive betweenness" (still the top ~5%). `thresholds_*` in the output
records every cutoff so this is visible per pair.

hub / orchestrator / bridge are not exclusive; a file holding several gets a
'+'-joined role in sorted order (e.g. "bridge+hub"). `universal` flags
near-universal includes (in-degree >= --universal-frac of the snapshot's
importing files, e.g. curl_setup.h) so every downstream table can be reported
with and without them. `normalized_blast_radius` is not used: it is exactly
pagerank_score * 1000 (verified in tools/centrality_bands.py).

**Edges.** When the DB has an `edge_data` table holding rows for both commits
(gitgalaxy#2992, engines after 2026-09-14), per-file edge diffs are added:
out/in edges added and removed, and `new_out_edges_to_hubs` (added out-edges
whose target was already a hub at the parent snapshot). Edges are compared in
child-path space: parent paths are mapped through the rename-aware diff, so a
rename is not counted as remove+add. Without edges (e.g. the curl dataset
built 2026-09-12, and tests/fixtures/fixture.db) the edge fields are null and
`edges_available` is false — node-level metrics still work.

Usage:
    # one pair, straight from a DB (renames need --repo):
    python tools/graph_roles.py --db X.db --before <parent> --after <child> [--repo curl]
    # every event in an events file (parent resolved from the pool clone):
    python tools/graph_roles.py --events events/curl.json --out dbs/graph_roles_curl.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

DEFAULT_PCT = 0.90
DEFAULT_UNIVERSAL_FRAC = 0.5
SCHEMA_VERSION = 1


@dataclass
class Snapshot:
    sha: str
    nodes: dict[str, dict]  # path -> {in, out, betweenness, pagerank, loc}
    edges: set[tuple[str, str]] | None  # (src_path, dst_path); None = no edge_data
    roles: dict[str, str] = field(default_factory=dict)
    universal: set[str] = field(default_factory=set)
    thresholds: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------- loading

def _has_table(con: sqlite3.Connection, name: str) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def load_snapshot(con: sqlite3.Connection, sha: str, repo_name: str | None = None) -> Snapshot:
    """Read one commit's file nodes (+ import edges when persisted)."""
    where, args = "commit_hash = ?", [sha]
    if repo_name:
        where += " AND repo_name = ?"
        args.append(repo_name)
    rows = con.execute(
        "SELECT id, file_path, popularity, import_count, betweenness_score, "
        f"pagerank_score, total_loc FROM file_data WHERE {where} ORDER BY id",
        args,
    ).fetchall()
    nodes: dict[str, dict] = {}
    id_to_path: dict[int, str] = {}
    for fid, path, pop, imp, btw, pr, loc in rows:
        id_to_path[fid] = path
        if path in nodes:  # duplicate path rows: keep the first, like the recorder's lookup
            continue
        nodes[path] = {
            "in": int(pop or 0),
            "out": int(imp or 0),
            "betweenness": None if btw is None else float(btw),
            "pagerank": None if pr is None else float(pr),
            "loc": int(loc or 0),
        }

    edges: set[tuple[str, str]] | None = None
    if _has_table(con, "edge_data"):
        e_where, e_args = "commit_hash = ? AND edge_kind = 'import'", [sha]
        if repo_name:
            e_where += " AND repo_name = ?"
            e_args.append(repo_name)
        erows = con.execute(
            f"SELECT src_file_id, dst_file_id FROM edge_data WHERE {e_where}",
            e_args,
        ).fetchall()
        if erows:
            edges = set()
            for s, d in erows:
                sp, dp = id_to_path.get(s), id_to_path.get(d)
                if sp is not None and dp is not None and sp != dp:
                    edges.add((sp, dp))
    return Snapshot(sha=sha, nodes=nodes, edges=edges)


# ------------------------------------------------------------------ roles

def nearest_rank(values: list[float], pct: float) -> float:
    """Nearest-rank percentile (no interpolation); math.inf for an empty list."""
    if not values:
        return math.inf
    s = sorted(values)
    k = max(1, math.ceil(pct * len(s)))
    return s[k - 1]


def assign_roles(snap: Snapshot, pct: float = DEFAULT_PCT,
                 universal_frac: float = DEFAULT_UNIVERSAL_FRAC) -> Snapshot:
    nodes = snap.nodes
    t_in = nearest_rank([n["in"] for n in nodes.values()], pct)
    t_out = nearest_rank([n["out"] for n in nodes.values()], pct)
    t_btw = nearest_rank([n["betweenness"] for n in nodes.values() if n["betweenness"] is not None], pct)
    n_importers = sum(1 for n in nodes.values() if n["out"] > 0)
    snap.thresholds = {"in": t_in, "out": t_out, "betweenness": t_btw, "n_importers": n_importers}

    for path, n in nodes.items():
        tags = []
        if n["in"] > 0 and n["in"] >= t_in:
            tags.append("hub")
        if n["out"] > 0 and n["out"] >= t_out:
            tags.append("orchestrator")
        b = n["betweenness"]
        if b is not None and b > 0 and b >= t_btw:
            tags.append("bridge")
        if tags:
            role = "+".join(sorted(tags))
        elif n["in"] == 0 and n["out"] == 0:
            role = "isolate"
        elif n["in"] <= 1:
            role = "spoke"
        else:
            role = "other"
        snap.roles[path] = role
        if n_importers and n["in"] >= universal_frac * n_importers:
            snap.universal.add(path)
    return snap


def is_hub(role: str | None) -> bool:
    return bool(role) and "hub" in role.split("+")


# ------------------------------------------------------------------ deltas

def _delta(a, b):
    return None if a is None or b is None else b - a


def role_deltas(before: Snapshot, after: Snapshot,
                renames: dict[str, str] | None = None) -> tuple[list[dict], dict]:
    """Per-file role/degree/edge deltas, plus a pair-level summary.

    `renames` maps parent path -> child path (from a rename-aware diff).
    Files are joined in child-path space.
    """
    renames = renames or {}
    to_child = lambda p: renames.get(p, p)
    child_to_parent = {to_child(p): p for p in before.nodes}

    edges_ok = before.edges is not None and after.edges is not None
    if edges_ok:
        e_before = {(to_child(s), to_child(d)) for s, d in before.edges}
        e_after = after.edges
        added, removed = e_after - e_before, e_before - e_after
        hubs_before = {to_child(p) for p, r in before.roles.items() if is_hub(r)}
    else:
        added = removed = set()
        hubs_before = set()

    def edge_counts(path: str) -> dict:
        if not edges_ok:
            return {k: None for k in ("out_edges_added", "out_edges_removed", "in_edges_added",
                                      "in_edges_removed", "new_out_edges_to_hubs")}
        return {
            "out_edges_added": sum(1 for s, _ in added if s == path),
            "out_edges_removed": sum(1 for s, _ in removed if s == path),
            "in_edges_added": sum(1 for _, d in added if d == path),
            "in_edges_removed": sum(1 for _, d in removed if d == path),
            "new_out_edges_to_hubs": sum(1 for s, d in added if s == path and d in hubs_before),
        }

    rows: list[dict] = []
    for cpath in sorted(set(after.nodes) | set(child_to_parent)):
        ppath = child_to_parent.get(cpath)
        nb = before.nodes.get(ppath) if ppath else None
        na = after.nodes.get(cpath)
        status = "persisted" if nb and na else ("added" if na else "removed")
        rb = before.roles.get(ppath) if ppath else None
        ra = after.roles.get(cpath)
        row = {
            "path": cpath,
            "old_path": ppath,
            "renamed": bool(ppath and ppath != cpath),
            "status": status,
            "role_before": rb,
            "role_after": ra,
            "role_changed": status == "persisted" and rb != ra,
            "transition": f"{rb or '-'}->{ra or '-'}",
            "universal": (ppath in before.universal) or (cpath in after.universal),
            "in_before": nb["in"] if nb else None,
            "in_after": na["in"] if na else None,
            "out_before": nb["out"] if nb else None,
            "out_after": na["out"] if na else None,
            "d_in": _delta(nb and nb["in"], na and na["in"]),
            "d_out": _delta(nb and nb["out"], na and na["out"]),
            "d_betweenness": _delta(nb and nb["betweenness"], na and na["betweenness"]),
            "d_pagerank": _delta(nb and nb["pagerank"], na and na["pagerank"]),
            "loc_before": nb["loc"] if nb else None,
            "loc_after": na["loc"] if na else None,
        }
        row.update(edge_counts(cpath))
        rows.append(row)

    changed = [r for r in rows if r["role_changed"]]
    summary = {
        "n_before": len(before.nodes),
        "n_after": len(after.nodes),
        "n_persisted": sum(r["status"] == "persisted" for r in rows),
        "n_added": sum(r["status"] == "added" for r in rows),
        "n_removed": sum(r["status"] == "removed" for r in rows),
        "n_role_changed": len(changed),
        "transitions": dict(Counter(r["transition"] for r in changed).most_common()),
        "edges_available": edges_ok,
        "edges_before": len(before.edges) if before.edges is not None else None,
        "edges_after": len(after.edges) if after.edges is not None else None,
        "edges_added": len(added) if edges_ok else None,
        "edges_removed": len(removed) if edges_ok else None,
        "new_edges_to_hubs": sum(1 for _, d in added if d in hubs_before) if edges_ok else None,
        "thresholds_before": before.thresholds,
        "thresholds_after": after.thresholds,
    }
    return rows, summary


def renames_from_diff(statuses: dict[str, dict]) -> dict[str, str]:
    """exposure_delta.diff_statuses output -> {parent_path: child_path} for renames."""
    return {v["old_path"]: k for k, v in statuses.items() if v.get("renamed")}


def compare(con: sqlite3.Connection, parent: str, child: str, *, repo_name: str | None = None,
            renames: dict[str, str] | None = None, pct: float = DEFAULT_PCT,
            universal_frac: float = DEFAULT_UNIVERSAL_FRAC) -> dict | None:
    b = load_snapshot(con, parent, repo_name)
    a = load_snapshot(con, child, repo_name)
    if not b.nodes or not a.nodes:
        return None
    assign_roles(b, pct, universal_frac)
    assign_roles(a, pct, universal_frac)
    rows, summary = role_deltas(b, a, renames)
    return {"schema_version": SCHEMA_VERSION, "parent": parent, "child": child,
            "pct": pct, "summary": summary, "files": rows}


# -------------------------------------------------------------------- CLI

def _open_ro(db: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", type=pathlib.Path, help="scan DB (default: the repo's history DB)")
    ap.add_argument("--before", help="parent commit sha (pair mode)")
    ap.add_argument("--after", help="child commit sha (pair mode)")
    ap.add_argument("--events", type=pathlib.Path, help="events JSON (events mode)")
    ap.add_argument("--classes", help="comma-separated event classes to keep (events mode)")
    ap.add_argument("--repo", help="pool repo name/path, for renames and parent resolution")
    ap.add_argument("--repo-name", help="filter DB rows to this repo_name")
    ap.add_argument("--pct", type=float, default=DEFAULT_PCT)
    ap.add_argument("--universal-frac", type=float, default=DEFAULT_UNIVERSAL_FRAC)
    ap.add_argument("--out", type=pathlib.Path, help="output path (JSON in pair mode, JSONL in events mode)")
    args = ap.parse_args(argv)

    if bool(args.events) == bool(args.before or args.after):
        ap.error("give either --events, or --before and --after")

    if args.events:
        return _events_mode(args)

    if not (args.before and args.after and args.db):
        ap.error("pair mode needs --db, --before and --after")
    renames = None
    if args.repo:
        from exposure_delta import diff_statuses
        from scan_pair import resolve_repo
        renames = renames_from_diff(diff_statuses(resolve_repo(args.repo), args.before, args.after))
    with _open_ro(args.db) as con:
        res = compare(con, args.before, args.after, repo_name=args.repo_name,
                      renames=renames, pct=args.pct, universal_frac=args.universal_frac)
    if res is None:
        sys.exit(f"one or both commits not in {args.db}")
    text = json.dumps(res, indent=1)
    if args.out:
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


def _events_mode(args) -> int:
    from exposure_delta import diff_statuses
    from scan_pair import history_db, out_dir_for, resolve_repo
    from signal_anatomy import parent_child

    data = json.loads(args.events.read_text())
    repo = resolve_repo(args.repo or data["repo"])
    db = args.db or history_db(out_dir_for(repo))
    if db is None:
        sys.exit(f"no scan DB for {repo.name}")
    keep = set(args.classes.split(",")) if args.classes else None
    out = args.out.open("w") if args.out else sys.stdout
    stats = Counter()
    with _open_ro(db) as con:
        for ev in data["events"]:
            if keep and ev["class"] not in keep:
                continue
            parent, child = parent_child(repo, ev["sha"])
            if parent is None:
                stats["no_parent"] += 1
                continue
            renames = renames_from_diff(diff_statuses(repo, parent, child))
            res = compare(con, parent, child, repo_name=args.repo_name, renames=renames,
                          pct=args.pct, universal_frac=args.universal_frac)
            if res is None:
                stats["not_scanned"] += 1
                continue
            stats["ok"] += 1
            stats["with_edges"] += res["summary"]["edges_available"]
            res.update({"event_id": ev["id"], "class": ev["class"]})
            out.write(json.dumps(res) + "\n")
    if args.out:
        out.close()
    print(f"graph_roles: {dict(stats)} (db={db})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
