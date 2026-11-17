#!/usr/bin/env python3
"""Does adding function-pointer references (tree-sitter) change the blast-radius result? Same named-cause pairs and nulls as ripple_links.py, three graphs:
calls only (the engine's), calls plus references (a function that registers a callback -> the callback), and plus siblings (functions filled into the same
table of function pointers). Only curl has enough named links.

    python tools/sensor/ripple_links_refs.py curl"""
import collections
import copy
import json
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import ripple_links as RL  # noqa: E402
import ts_refs as TR  # noqa: E402

name = sys.argv[1]
SN = json.load(open(f"{RL.B}/scan_{name}/snapshots.json"))
IDX = {x["db"]: i for i, x in enumerate(SN)}
_base_graph = RL.graph
MODE = "calls"
_cache = {}


def graph_mode(db):
    key = (db, MODE)
    if key in _cache:
        return _cache[key]
    base = _base_graph(db)
    if MODE == "calls":
        _cache[key] = base
        return base
    nodes, loc, args, fwd, rev, by_file, dec, by_dec = base
    fwd2 = collections.defaultdict(set, {k: set(v) for k, v in fwd.items()})
    rev2 = collections.defaultdict(set, {k: set(v) for k, v in rev.items()})
    r = TR.refs_for_snapshot(name, IDX[db])
    defs = {n: ps for n, ps in r["defs"].items() if len(ps) == 1}
    node_of = {n: (ps[0], n) for n, ps in defs.items()}
    tables = collections.defaultdict(set)
    for path, enc, target, ctx, line, table in r["refs"]:
        if target not in node_of or node_of[target] not in nodes:
            continue
        tgt = node_of[target]
        if enc is not None:
            src = (path, enc)
            if src in nodes and src != tgt:
                fwd2[src].add(tgt)
                rev2[tgt].add(src)
        elif table:
            tables[(path, table)].add(tgt)
    if MODE == "calls+refs+siblings":
        for members in tables.values():
            if 2 <= len(members) <= 40:
                ms = list(members)
                for a in ms:
                    for b in ms:
                        if a != b:
                            fwd2[a].add(b)
                            rev2[b].add(a)
    out = (nodes, loc, args, fwd2, rev2, by_file, dec, by_dec)
    _cache[key] = out
    return out


RL.graph = graph_mode
for MODE in ("calls", "calls+refs", "calls+refs+siblings"):
    res, stats, n = RL.analyse(name)
    print(f"\n######## graph: {MODE}  ({n} named-cause pairs, usable {len(res)}) ########")
    RL.summarise(res, "all pairs")
    RL.summarise([r for r in res if r["obs"] and not r["obs"]["same_file"]], "fix in a different file from every changed function")
