#!/usr/bin/env python3
"""Inventory of the DOOM ports' full histories (clones under temporal-crucible-pool/doom-ports, manifest in doom-dna/manifest/manifest.csv): commits, span, commits up to the pinned
SHA, and which ports share commits (a shared history is not independent evidence).

    python tools/sensor/doom_inventory.py"""
import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

POOL = Path("/srv/storage_16tb/projects/temporal-crucible-pool/doom-ports")
MAN = "/srv/storage_16tb/projects/doom-dna/manifest/manifest.csv"


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def one(r):
    n = r["name"]
    repo = POOL / n
    if not (repo / ".git").exists() or git(repo, "rev-parse", "--is-shallow-repository").strip() != "false":
        return n, None
    sha = r["sha"]
    has = bool(git(repo, "cat-file", "-t", sha).strip())
    rng = f"{sha}" if has else "HEAD"
    commits = git(repo, "rev-list", "--no-merges", rng).split()
    dates = git(repo, "log", "--no-merges", "--format=%ct", rng).split()
    ds = sorted(int(d) for d in dates) if dates else [0]
    return n, {"lang": (r["languages"].split() or [""])[0], "pinned_in_history": has, "commits": len(commits), "first": ds[0], "last": ds[-1], "set": set(commits)}


def main():
    rows = list(csv.DictReader(open(MAN)))
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = dict(ex.map(one, rows))
    import datetime
    y = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).year if t else 0  # noqa: E731
    print(f"{'port':24s} {'lang':10s} {'commits':>8s} {'first':>6s} {'last':>6s} pinned sha in history")
    for r in rows:
        v = res[r["name"]]
        if v is None:
            print(f"{r['name']:24s} (not cloned or shallow)")
        else:
            print(f"{r['name']:24s} {v['lang']:10s} {v['commits']:8d} {y(v['first']):6d} {y(v['last']):6d} {'yes' if v['pinned_in_history'] else 'NO (HEAD used)'}")
    have = [n for n, v in res.items() if v]
    print(f"\n{len(have)} ports with full history; total commits {sum(res[n]['commits'] for n in have)}")
    print("\nSHARED HISTORY (ports that share at least 20 commits; shared / smaller port's commits):")
    seen = []
    for i, a in enumerate(have):
        for b in have[i + 1 :]:
            k = len(res[a]["set"] & res[b]["set"])
            if k >= 20:
                seen.append((k / min(res[a]["commits"], res[b]["commits"]), a, b, k))
    for fr, a, b, k in sorted(seen, reverse=True):
        print(f"  {a:18s} {b:18s} {k:6d} commits shared ({100 * fr:.0f}% of the smaller history)")
    if not seen:
        print("  none")


if __name__ == "__main__":
    main()
