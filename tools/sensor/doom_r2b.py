#!/usr/bin/env python3
"""DOOM-R2b: token-level similarity of the repairs. Hypotheses RD4-RD6: docs/sensor-overhaul/sensors/doom_ports_plan.md section 10, fixed before running.
    python tools/sensor/doom_r2b.py      (needs the caches of doom_r2.py)"""
import collections
import pickle
import re
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import doom_r1 as D  # noqa: E402
import lang_validation as LV  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
rng = np.random.default_rng(2982)
WORD = re.compile(r"[A-Za-z_]\w*|\d+")


def toks(lines):
    return frozenset(w.lower() for l in lines for w in WORD.findall(l))


def sim(x, y):
    (ra, aa), (rb, ab) = x, y
    if ra and rb:
        a, b = toks(ra), toks(rb)
    elif not ra and not rb:
        a, b = toks(aa), toks(ab)
    else:
        return 0.0
    return len(a & b) / len(a | b) if (a or b) else 0.0


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

    lineages = D.LIN + [D.CTRL]
    obs, fixes_of, lines = {}, {}, {}
    for repo in lineages:
        pairs, info = LV.build(repo, 3000)
        lines[repo] = pickle.load(open(f"{B}/blast/doom_r2_lines_{repo}.pkl", "rb"))
        o, fo = collections.defaultdict(set), collections.defaultdict(set)
        for p in pairs:
            Fn = {D.norm(x[1]) for x in info[p["fix"]][0]} & refnames
            In = {D.norm(x[1]) for x in info[p["ind"]][0]} & refnames
            for gname in Fn:
                fo[gname].add(p["fix"])
            for f in In:
                nb = set(n2(f))
                for gname in Fn:
                    if gname != f and gname in nb:
                        o[(f, gname)].add(p["fix"])
        obs[repo], fixes_of[repo] = o, fo

    def s_fn(A, B_, fa, fb, gname):
        best = None
        for x in fa:
            lx = lines[A].get(x, {}).get(gname)
            if lx is None:
                continue
            for y in fb:
                ly = lines[B_].get(y, {}).get(gname)
                if ly is not None:
                    v = sim(lx, ly)
                    best = v if best is None else max(best, v)
        return best

    ok = [r for r in D.LIN if len(obs[r]) >= 30]
    pairs_ab = [(a, b) for i, a in enumerate(ok) for b in ok[i + 1 :]]
    observed = []
    for a, b in pairs_ab:
        for (f, gname) in obs[a]:
            if (f, gname) in obs[b]:
                v = s_fn(a, b, obs[a][(f, gname)], obs[b][(f, gname)], gname)
                if v is not None:
                    observed.append(v)
    ctrl = []
    for (f, gname) in obs[D.CTRL]:
        if (f, gname) in obs["crispy-doom"]:
            v = s_fn(D.CTRL, "crispy-doom", obs[D.CTRL][(f, gname)], obs["crispy-doom"][(f, gname)], gname)
            if v is not None:
                ctrl.append(v)

    def draw(f, A):
        nb = n2(f)
        if not nb:
            return None
        w = np.array([len(fixes_of[A].get(x, ())) + 0.5 for x in nb])
        return nb[int(rng.choice(len(nb), p=w / w.sum()))]

    null = []
    for _ in range(100):
        draws = {r: {(f, draw(f, r)) for f, _ in obs[r] if n2(f)} for r in ok}
        for a, b in pairs_ab:
            for (f, gname) in draws[a] & draws[b]:
                v = s_fn(a, b, fixes_of[a].get(gname, ()), fixes_of[b].get(gname, ()), gname)
                if v is not None:
                    null.append(v)
    p90 = float(np.percentile(null, 90))
    med_o, med_n, med_c = np.median(observed), np.median(null), np.median(ctrl)
    share90 = float(np.mean([x > p90 for x in observed]))
    print(f"cross-lineage overlaps with repairs on both sides: {len(observed)}; null draws: {len(null)}; positive control overlaps: {len(ctrl)}")
    print(f"token-level similarity median: observed {med_o:.3f}, null {med_n:.3f} (90th percentile {p90:.3f}), positive control {med_c:.3f}")
    print(f"share of the observed overlaps above the null's 90th percentile: {100 * share90:.0f}% (10% by construction); share at least 0.8: observed {100 * np.mean([x >= 0.8 for x in observed]):.0f}%, null {100 * np.mean([x >= 0.8 for x in null]):.0f}%, control {100 * np.mean([x >= 0.8 for x in ctrl]):.0f}%")
    print("\n=== VERDICTS ===")
    print(f"  RD4 positive control median {med_c:.3f} (needs 0.8): {'supported' if med_c >= 0.8 else 'not supported'}")
    r5 = (med_o - med_n >= 0.05) and share90 >= 0.2
    print(f"  RD5 median difference {med_o - med_n:+.3f} (needs +0.05) and share above the null's 90th percentile {100 * share90:.0f}% (needs 20%): {'supported' if r5 else 'not supported'}")
    if r5:
        print(f"  RD6 overlaps above the null's 90th percentile {100 * share90:.0f}% (needs at most 50%): {'supported' if share90 <= 0.5 else 'not supported'}")
    print(f"  surprise bar (RD5 fails): {'MET' if not r5 else 'not met'}")


if __name__ == "__main__":
    main()
