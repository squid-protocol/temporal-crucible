#!/usr/bin/env python3
"""Test reach by depth and repaired-function test reachability. Hypotheses TR1-TR3: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running."""
import collections
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import test_selection as TS  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
REPOS = [("dpdk", "trailer"), ("mesa", "trailer"), ("libgit2", "blame"), ("redis", "blame"), ("libxml2", "blame"), ("prometheus", "blame"), ("sphinx", "blame")]
KS = [1, 2, 3, 5, 10]
rng = np.random.default_rng(7)


def test_dist(g, keys):
    ist = np.array([TS.is_test(k[0]) for k in keys], dtype=bool)
    dist = np.full(g.n, 99, dtype=np.int64)
    front = ist.astype(np.int8)
    seen = ist.copy()
    dist[ist] = 0
    for d in range(1, 11):
        nxt = (g.callees_m @ front) > 0
        nxt &= ~seen
        seen |= nxt
        dist[nxt] = d
        front = nxt.astype(np.int8)
        if not nxt.any():
            break
    return dist, ist


def main():
    obs_all = {k: [] for k in (3, 5, 10)}
    exp_all = {k: [] for k in (3, 5, 10)}
    summary = {}
    print("=== DEPTH: share of non-test functions reached by a test within k calls (latest scan) ===")
    depth = {}
    for repo, kind in REPOS:
        sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
        g = BR.Graph(sn[-1]["db"])
        keys = sorted(g.index, key=g.index.get)
        dist, ist = test_dist(g, keys)
        depth[repo] = [float((dist[~ist] <= k).mean()) for k in KS]
        print(f"  {repo:11s} " + "  ".join(f"{k}: {100 * v:5.1f}%" for k, v in zip(KS, depth[repo])), flush=True)
    print("\n=== REPAIRS: repaired functions test-reachable, observed against size-matched expected ===")
    for repo, kind in REPOS:
        fixes = TS.load(repo, kind)
        sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
        cf = f"{B}/blast/{repo}/snapshot_cts.npy" if os.path.exists(f"{B}/blast/{repo}/snapshot_cts.npy") else f"{B}/blast/lang_{repo}_snapcts.npy"
        if os.path.exists(cf):
            cts = np.load(cf)
        else:
            cts = np.array([int(subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn])
            np.save(cf, cts)
        by = collections.defaultdict(list)
        for sha, (ct, ks) in fixes.items():
            s = int(np.searchsorted(cts, ct, side="right")) - 1
            if s >= 0:
                by[s].append(ks)
        per_fix = {k: [] for k in (3, 5, 10)}  # (observed hits, expected hits, count)
        for s, items in sorted(by.items()):
            g = BR.Graph(sn[s]["db"])
            keys = sorted(g.index, key=g.index.get)
            if g.n == 0:
                continue
            dist, ist = test_dist(g, keys)
            if not ist.any():
                continue
            dec_pool = {d: np.nonzero((g.dec == d) & ~ist)[0] for d in range(10)}
            expd = {k: {d: float((dist[p] <= k).mean()) if len(p) else 0.0 for d, p in dec_pool.items()} for k in (3, 5, 10)}
            for ks in items:
                nodes = [g.index[k] for k in ks if k in g.index and not TS.is_test(k[0])]
                if not nodes:
                    continue
                for k in (3, 5, 10):
                    per_fix[k].append((sum(dist[i] <= k for i in nodes), sum(expd[k][int(g.dec[i])] for i in nodes), len(nodes)))
        summary[repo] = {}
        line = f"  {repo:11s} fixes {len(per_fix[5]):5d}; "
        for k in (3, 5, 10):
            a = np.array(per_fix[k], dtype=float)
            if not len(a):
                continue
            o, e = a[:, 0].sum() / a[:, 2].sum(), a[:, 1].sum() / a[:, 2].sum()
            bs = []
            for _ in range(1000):
                idx = rng.integers(0, len(a), len(a))
                b = a[idx]
                bs.append(b[:, 0].sum() / b[:, 2].sum() - b[:, 1].sum() / b[:, 2].sum())
            lo, hi = np.percentile(bs, [2.5, 97.5])
            summary[repo][k] = (o, e, o - e, lo, hi)
            obs_all[k].append(a[:, 0].sum())
            exp_all[k].append(a[:, 1].sum())
            line += f"k={k}: observed {100 * o:5.1f}% expected {100 * e:5.1f}% diff {100 * (o - e):+5.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]; "
        print(line, flush=True)
    print("\n=== VERDICTS ===")
    ok = [r for r in ("dpdk", "mesa", "redis") if r in depth]
    t1 = [depth[r][4] >= 2 * depth[r][2] for r in ok]
    print(f"  TR1 10-call share at least twice the 3-call share: " + ", ".join(f"{r} {100 * depth[r][4]:.1f}% vs {100 * depth[r][2]:.1f}%" for r in ok) + f": {'supported' if all(t1) else 'not supported'}")
    neg = [r for r in summary if 5 in summary[r] and summary[r][5][2] < 0]
    sig = [r for r in neg if summary[r][5][4] < 0]
    pos = [r for r in summary if 5 in summary[r] and summary[r][5][2] > 0]
    print(f"  TR2 at 5 calls repaired functions less reachable in {len(neg)} of {len(summary)} repositories, interval excludes 0 in {len(sig)} (needs 5 and 4): {'supported' if len(neg) >= 5 and len(sig) >= 4 else 'not supported'}")
    ratio = sum(obs_all[5]) / sum(exp_all[5])
    print(f"  TR3 pooled observed/expected at 5 calls {ratio:.2f} (needs 0.90 or less): {'supported' if ratio <= 0.9 else 'not supported'}")
    print(f"  surprise bar (more reachable than expected in at least 5 of 7): {'MET' if len(pos) >= 5 else 'not met'} ({len(pos)} of {len(summary)})")


if __name__ == "__main__":
    main()
