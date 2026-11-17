#!/usr/bin/env python3
"""Named-cause blast radius on repositories whose fixes carry a `Fixes: <sha>` trailer (OpenSSL, FreeBSD): the curl design (ripple_links.py) with trailer pairs from
fixes_trailer_links.py, by lag (a fix within a month, within a year, later), pooled over repositories. Hypotheses: docs/sensor-overhaul/sensors/ripple_radius.md
("OpenSSL and FreeBSD", written before this ran).

    python tools/sensor/ripple_trailer.py REPO [REPO ...]       (needs /tmp/.../argl/links_REPO.json and the quarterly scan_REPO snapshots)"""
import json
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import ripple_links as RL  # noqa: E402

RL.links = lambda name: json.load(open(f"/tmp/gitgalaxy-scratch/claude/argl/links_{name}.json"))
names = sys.argv[1:]
pooled = []
for name in names:
    res, stats, n = RL.analyse(name)
    for r in res:
        r["repo"] = name
    pooled += res
    print(f"\n=== {name}: {n} trailer pairs; usable {len(res)}; dropped {dict(stats)} ===")
    RL.summarise(res, "all pairs")
    RL.summarise([r for r in res if r["lag"] < 30], "fix within 30 days of the change")
    RL.summarise([r for r in res if 30 <= r["lag"] < 365], "fix 30 to 365 days later")
    RL.summarise([r for r in res if r["lag"] >= 365], "fix a year or more later")
if len(names) > 1:
    print(f"\n=== POOLED over {', '.join(names)} ===")
    RL.summarise(pooled, "all pairs")
    RL.summarise([r for r in pooled if r["lag"] < 30], "fix within 30 days of the change")
    RL.summarise([r for r in pooled if 30 <= r["lag"] < 365], "fix 30 to 365 days later")
    RL.summarise([r for r in pooled if r["lag"] >= 365], "fix a year or more later")
    RL.summarise([r for r in pooled if r["obs"] and not r["obs"]["same_file"]], "fix in a different file from every changed function")
    RL.summarise([r for r in pooled if r["sig"]], "inducing change altered a parameter count")
