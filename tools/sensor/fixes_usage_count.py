#!/usr/bin/env python3
"""Count `Fixes: <sha>` trailer usage in candidate repositories (treeless bare clones under temporal-crucible-pool/_fixes_count): total commits, trailers, resolvable
and ordered pairs, lag, years, and (from a sample, which fetches trees on demand) the share of pairs where both commits touch .c/.h files.

    python tools/sensor/fixes_usage_count.py REPO [REPO ...]"""
import collections
import datetime
import random
import re
import subprocess
import sys
import time

BASE = "/srv/storage_16tb/projects/temporal-crucible-pool/_fixes_count"
FIX = re.compile(r"^Fixes:\s+([0-9a-f]{7,40})", re.M)


def git(repo, *a, inp=None, t=900):
    return subprocess.run(["git", "-C", f"{BASE}/{repo}.git", *a], capture_output=True, text=True, errors="replace", input=inp, timeout=t).stdout


def count(repo):
    total = int(git(repo, "rev-list", "--count", "--no-merges", "HEAD").strip() or 0)
    raw = git(repo, "log", "--no-merges", "-E", "--grep=^Fixes: [0-9a-f]{7,40}", "--format=%H%x1f%ct%x1f%s%x1f%B%x1e")
    heads, reverts = [], 0
    for rec in raw.split("\x1e"):
        p = rec.strip("\n").split("\x1f")
        if len(p) < 4:
            continue
        if p[2].lower().startswith("revert"):
            reverts += 1
            continue
        for m in FIX.finditer(p[3]):
            heads.append((p[0], int(p[1]), m.group(1)))
    res = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)", inp="\n".join(h[2] + "^{commit}" for h in heads) + "\n").splitlines() if heads else []
    pairs = []
    for (sha, ct, _), line in zip(heads, res):
        parts = line.split()
        if len(parts) == 2 and parts[1] == "commit" and parts[0] != sha:
            pairs.append((sha, ct, parts[0]))
    inds = sorted({p[2] for p in pairs})
    cts = {}
    for i in range(0, len(inds), 3000):
        for line in git(repo, "log", "--no-walk=unsorted", "--format=%H %ct", *inds[i : i + 3000]).splitlines():
            h, t = line.split()
            cts[h] = int(t)
    ordered = [(s, ct, i, cts[i]) for s, ct, i in pairs if i in cts and cts[i] < ct]
    yrs = collections.Counter(datetime.datetime.fromtimestamp(o[3], datetime.timezone.utc).year for o in ordered)
    lags = sorted((o[1] - o[3]) / 86400 for o in ordered)
    return total, len(heads), len(ordered), yrs, lags, ordered, reverts


def ch_share(repo, ordered, n=250):
    sample = random.Random(1).sample(ordered, min(n, len(ordered)))
    shas = list({x for o in sample for x in (o[0], o[2])})
    t0 = time.time()
    files = collections.defaultdict(list)
    res = git(repo, "diff-tree", "--stdin", "-r", "--name-only", "--root", inp="\n".join(shas) + "\n", t=1500)
    cur = None
    for line in res.splitlines():
        if re.fullmatch(r"[0-9a-f]{40}", line):
            cur = line
        elif cur:
            files[cur].append(line)
    both = sum(1 for o in sample if any(f.endswith((".c", ".h")) for f in files[o[0]]) and any(f.endswith((".c", ".h")) for f in files[o[2]]))
    cross = sum(1 for o in sample if set(files[o[0]]) & set(files[o[2]]) == set())
    return both / len(sample), cross / len(sample), len(sample), time.time() - t0


def main():
    from concurrent.futures import ThreadPoolExecutor

    repos = [a for a in sys.argv[1:] if not a.startswith("--")]
    results = {}
    for repo in repos:
        try:
            total, nh, no, yrs, lags, ordered, rev = count(repo)
        except Exception as e:  # noqa: BLE001
            print(f"{repo}: failed: {e}", flush=True)
            continue
        results[repo] = ordered
        recent = sum(n for y, n in yrs.items() if y >= 2019)
        print(f"\n{repo}: {total:,} non-merge commits; {nh:,} Fixes: trailers ({100 * nh / max(total, 1):.1f}% of commits; {rev} reverts left out); {no:,} resolved and ordered pairs", flush=True)
        if no:
            print(f"  lag: median {lags[len(lags) // 2]:.0f} d, within 30 days {100 * sum(1 for l in lags if l < 30) / len(lags):.0f}%, a year or more {100 * sum(1 for l in lags if l >= 365) / len(lags):.0f}%", flush=True)
            print("  inducing commits by year: " + ", ".join(f"{y}: {n}" for y, n in sorted(yrs.items())[-9:]) + f"; from 2019 on: {recent}", flush=True)
    print("\n=== sample of 60 pairs per repository with 200 or more pairs: do both commits touch .c/.h (trees are fetched on demand, so this is slow) ===", flush=True)
    todo = [r for r in repos if r in results and len(results[r]) >= 200]

    def run(repo):
        try:
            c, x, n, dt = ch_share(repo, results[repo], n=60)
            return repo, f"{repo:10s} both commits touch .c/.h in {100 * c:.0f}% (n {n}, {dt:.0f} s); share no file in {100 * x:.0f}%; projected pairs with C/H on both sides: about {int(len(results[repo]) * c):,}"
        except Exception as e:  # noqa: BLE001
            return repo, f"{repo}: sample failed: {e}"

    with ThreadPoolExecutor(max_workers=5) as ex:
        for repo, line in ex.map(run, todo):
            print("  " + line, flush=True)


if __name__ == "__main__":
    main()
