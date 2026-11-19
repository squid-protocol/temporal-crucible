#!/usr/bin/env python3
"""DOOM-R1b: popularity-matched null for the neighbour overlap (DB4b, DB4c). docs/sensor-overhaul/sensors/doom_ports_plan.md section 8, fixed before running.
    python tools/sensor/doom_r1b.py"""
import collections
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import doom_r1 as D  # noqa: E402
import lang_validation as LV  # noqa: E402

rng = np.random.default_rng(2982)


def main():
    g = BR.Graph(D.REFDB)
    keys = sorted(g.index, key=g.index.get)
    name_nodes = collections.defaultdict(list)
    for i, (p, n) in enumerate(keys):
        if g.loc[i] >= 3:
            name_nodes[D.norm(n)].append(i)
    refnames = set(name_nodes)
    cache = {}

    def n2(name):
        if name not in cache:
            near = g.near(np.array(name_nodes[name], dtype=np.int64))["either2"]
            cache[name] = sorted({D.norm(keys[i][1]) for i in np.nonzero(near)[0] if D.norm(keys[i][1]) in refnames} - {name})
        return cache[name]

    data = {}
    for repo in D.LIN:
        pairs, info = LV.build(repo, 3000)
        fix = collections.Counter()
        seen = set()
        for p in pairs:
            if p["fix"] in seen:
                continue
            seen.add(p["fix"])
            for k in {D.norm(x[1]) for x in info[p["fix"]][0]} & refnames:
                fix[k] += 1
        obs = set()
        for p in pairs:
            Fn = {D.norm(x[1]) for x in info[p["fix"]][0]} & refnames
            In = {D.norm(x[1]) for x in info[p["ind"]][0]} & refnames
            for f in In:
                nb = set(n2(f))
                for gname in Fn:
                    if gname != f and gname in nb:
                        obs.add((f, gname))
        data[repo] = {"obs": obs, "fix": fix}
    ok = [r for r in D.LIN if len(data[r]["obs"]) >= 30]
    print(f"lineages with at least 30 inherited pairs: {ok}")

    def overlap(sets):
        return sum(len(a & b) for i, a in enumerate(sets) for b in sets[i + 1 :])

    def draw(f, fix, trim):
        nb = [x for x in n2(f) if x not in trim]
        if not nb:
            return None
        w = np.array([fix.get(x, 0) + 0.5 for x in nb])
        return nb[int(rng.choice(len(nb), p=w / w.sum()))]

    observed = overlap([data[r]["obs"] for r in ok])
    pop_null = [overlap([{(f, draw(f, data[r]["fix"], set())) for f, _ in data[r]["obs"]} - {(f, None) for f, _ in data[r]["obs"]} for r in ok]) for _ in range(300)]
    uni_null = [overlap([{(f, rng.choice(n2(f))) for f, _ in data[r]["obs"] if n2(f)} for r in ok]) for _ in range(300)]
    total = collections.Counter()
    for r in ok:
        total.update(data[r]["fix"])
    trim = {k for k, _ in total.most_common(20)}
    obs_t = [{(f, gname) for f, gname in data[r]["obs"] if f not in trim and gname not in trim} for r in ok]
    observed_t = overlap(obs_t)
    uni_t = []
    for _ in range(300):
        ns = []
        for r, o in zip(ok, obs_t):
            s = set()
            for f, _ in o:
                nb = [x for x in n2(f) if x not in trim]
                if nb:
                    s.add((f, nb[int(rng.integers(len(nb)))]))
            ns.append(s)
        uni_t.append(overlap(ns))
    print(f"20 most-repaired inherited functions removed in the trimmed test: {sorted(trim)[:20]}")
    print(f"\nobserved overlap {observed}; uniform null {np.mean(uni_null):.1f} ({observed / np.mean(uni_null):.2f} times); popularity-matched null {np.mean(pop_null):.1f} (95th percentile {np.percentile(pop_null, 95):.0f}): {observed / np.mean(pop_null):.2f} times")
    print(f"trimmed: observed {observed_t}, uniform null {np.mean(uni_t):.1f}: {observed_t / max(np.mean(uni_t), 1e-9):.2f} times")
    print("\n=== VERDICTS ===")
    r1, r2 = observed / np.mean(pop_null), observed_t / max(np.mean(uni_t), 1e-9)
    print(f"  DB4b popularity-matched ratio {r1:.2f} (needs 1.5): {'supported' if r1 >= 1.5 else 'not supported'}")
    print(f"  DB4c trimmed ratio {r2:.2f} (needs 1.5): {'supported' if r2 >= 1.5 else 'not supported'}")
    print(f"  surprise bar (DB4b at or below 1.2): {'MET' if r1 <= 1.2 else 'not met'}")


if __name__ == "__main__":
    main()
