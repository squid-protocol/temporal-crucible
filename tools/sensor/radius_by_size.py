#!/usr/bin/env python3
"""Repair radius within size bands of the causing change (lines added plus removed), plain same-file baseline, for repositories with measure.pkl and diff_feats.pkl.
    python tools/sensor/radius_by_size.py linux dpdk"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

rng = np.random.default_rng(2982)
for repo in sys.argv[1:]:
    d = f"/tmp/gitgalaxy-scratch/claude/blast/{repo}{os.environ.get('BLAST_SUFFIX', '')}"
    m = pd.read_pickle(f"{d}/measure.pkl")
    m = m[(m.status == "ok") & (m.nFo > 0)].copy()
    f = pd.read_pickle(f"{d}/diff_feats.pkl")
    m["lines"] = [f[s]["n_add"] + f[s]["n_rem"] if s in f else np.nan for s in m.ind]
    print(f"\n{repo}: {len(m)} pairs with a fixed function outside the changed set; share of causes 100+ lines {100 * (m.lines >= 100).mean():.0f}%")
    for lab, k in (("under 20", m.lines < 20), ("20 to 99", (m.lines >= 20) & (m.lines < 100)), ("100 to 499", (m.lines >= 100) & (m.lines < 500)), ("500 or more", m.lines >= 500)):
        x = m[k]
        print(f"  {lab:12s} n {len(x):5d} share {100 * len(x) / len(m):4.1f}%  same function {100 * x.same_func.mean():3.0f}%  either1 {BR.fmt(BR.ratio(x, 'either1', 'eB', rng))}  either2 {BR.fmt(BR.ratio(x, 'either2', 'eB', rng))}")
