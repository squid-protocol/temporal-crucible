#!/usr/bin/env python3
"""Named-cause pairs from `Fixes: <sha>` trailers (the kernel convention): (fix commit, inducing commit, lag).

    python tools/sensor/fixes_trailer_links.py REPO [--json OUT]

A fix names its cause on a line `Fixes: <7-40 hex> (...)`. Reverts and self-references are left out; the inducing commit must exist in the repository, precede the fix
and touch C-family files, as must the fix. Prints counts and the year spread (which sets how many snapshots a graph needs)."""
import collections
import json
import re
import subprocess
import sys

POOL = "/srv/storage_16tb/projects/temporal-crucible-pool"
FIX = re.compile(r"^Fixes:\s+([0-9a-f]{7,40})", re.M)


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, errors="replace").stdout


def links(name):
    repo = f"{POOL}/{name}"
    raw = git(repo, "log", "--no-merges", "-E", "--grep=^Fixes: [0-9a-f]{7,40}", "--format=%H%x1f%ct%x1f%s%x1f%B%x1e")
    out, dropped = [], collections.Counter()
    for rec in raw.split("\x1e"):
        parts = rec.strip("\n").split("\x1f")
        if len(parts) < 4:
            continue
        sha, ct, subj, body = parts[0], int(parts[1]), parts[2], parts[3]
        if subj.lower().startswith("revert"):
            dropped["revert"] += 1
            continue
        for m in FIX.finditer(body):
            full = git(repo, "rev-parse", "--verify", "-q", m.group(1) + "^{commit}").strip()
            if not full or full == sha:
                dropped["unresolved or self"] += 1
                continue
            ict = int(git(repo, "show", "-s", "--format=%ct", full).strip() or 0)
            if ict >= ct:
                dropped["inducing not before fix"] += 1
                continue
            files_i = [f for f in git(repo, "show", "--no-color", "--format=", "--name-only", full).splitlines() if f.endswith((".c", ".h"))]
            files_f = [f for f in git(repo, "show", "--no-color", "--format=", "--name-only", sha).splitlines() if f.endswith((".c", ".h"))]
            if not files_i or not files_f:
                dropped["no C file in a commit"] += 1
                continue
            out.append({"fix": sha, "ind": full, "fix_ct": ct, "ind_ct": ict, "lag": (ct - ict) / 86400})
    return out, dropped


if __name__ == "__main__":
    name = sys.argv[1]
    L, dropped = links(name)
    import datetime

    yrs = collections.Counter(datetime.datetime.fromtimestamp(x["ind_ct"], datetime.timezone.utc).year for x in L)
    lags = sorted(x["lag"] for x in L)
    print(f"{name}: {len(L)} usable pairs; dropped {dict(dropped)}")
    if L:
        print(f"  lag median {lags[len(lags) // 2]:.0f} d, 25th {lags[len(lags) // 4]:.0f} d, 75th {lags[3 * len(lags) // 4]:.0f} d; share within 2 days {100 * sum(1 for l in lags if l < 2) / len(lags):.0f}%")
        print("  inducing commits by year: " + ", ".join(f"{y}: {n}" for y, n in sorted(yrs.items())))
    if "--json" in sys.argv:
        json.dump(L, open(sys.argv[sys.argv.index("--json") + 1], "w"))
