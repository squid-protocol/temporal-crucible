#!/usr/bin/env python3
"""Linux kernel `Fixes: <sha>` pairs by subsystem: how many named-cause pairs sit in the scanned core subsystems (no blast-radius analysis here).

    python tools/sensor/kernel_fixes_count.py        -> docs/sensor-overhaul/sensors/linux_fixes_pairs_output.txt (and a JSON of pairs under /tmp/.../argl)

A pair = a non-merge commit with a line `Fixes: <7-40 hex>`, resolved to a commit that precedes it. Subsystem of a commit = the 2-level directory (fs/ext4, net/ipv4, mm, kernel, ...)
holding most of its changed .c/.h files within the scanned set (fs mm kernel net lib block security crypto ipc init include/linux include/net include/asm-generic include/trace include/crypto)."""
import collections
import datetime
import json
import re
import subprocess
import sys

REPO = "/srv/storage_16tb/projects/temporal-crucible-pool/linux"
SCANNED = ("fs/", "mm/", "kernel/", "net/", "lib/", "block/", "security/", "crypto/", "ipc/", "init/", "include/linux/", "include/net/", "include/asm-generic/", "include/trace/", "include/crypto/")
FIX = re.compile(r"^Fixes:\s+([0-9a-f]{7,40})", re.M)
SINCE = int(datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc).timestamp())


def git(*a, inp=None):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace", input=inp).stdout


def sub(path):
    parts = path.split("/")
    if parts[0] in ("fs", "net", "include") and len(parts) > 2:
        return "/".join(parts[:2]) if parts[0] != "include" else "/".join(parts[:2])
    return parts[0]


def changed(shas):
    """sha -> list of scanned .c/.h paths, through one `git diff-tree --stdin`."""
    out, cur = {}, None
    res = git("diff-tree", "--stdin", "--no-commit-id", "-r", "--name-only", "-m", "--root", inp="\n".join(shas) + "\n")
    # with --stdin and --no-commit-id the commit id line is suppressed: run per chunk to keep boundaries
    return res


def files_of(shas):
    out = {}
    CH = 400
    for i in range(0, len(shas), CH):
        chunk = shas[i : i + CH]
        res = git("diff-tree", "--stdin", "-r", "--name-only", "--root", inp="\n".join(chunk) + "\n")
        cur = None
        for line in res.splitlines():
            if re.fullmatch(r"[0-9a-f]{40}", line):
                cur = line
                out[cur] = []
            elif cur and line.endswith((".c", ".h")) and line.startswith(SCANNED):
                out[cur].append(line)
    return out


def main():
    raw = git("log", "--no-merges", "-E", "--grep=^Fixes: [0-9a-f]{7,40}", "--format=%H%x1f%ct%x1f%s%x1f%B%x1e")
    pairs, dropped = [], collections.Counter()
    heads = []
    for rec in raw.split("\x1e"):
        p = rec.strip("\n").split("\x1f")
        if len(p) < 4:
            continue
        sha, ct, subj, body = p[0], int(p[1]), p[2], p[3]
        if subj.lower().startswith("revert"):
            dropped["revert"] += 1
            continue
        for m in FIX.finditer(body):
            heads.append((sha, ct, m.group(1)))
    # resolve the named commits in one batch
    names = [h[2] for h in heads]
    res = git("cat-file", "--batch-check=%(objectname) %(objecttype)", inp="\n".join(n + "^{commit}" for n in names) + "\n").splitlines()
    resolved = []
    for (sha, ct, name), line in zip(heads, res):
        parts = line.split()
        if len(parts) == 2 and parts[1] == "commit" and parts[0] != sha:
            resolved.append((sha, ct, parts[0]))
        else:
            dropped["unresolved or self"] += 1
    inds = sorted({r[2] for r in resolved})
    cts = {}
    for i in range(0, len(inds), 2000):
        chunk = inds[i : i + 2000]
        for line in git("log", "--no-walk=unsorted", "--format=%H %ct", *chunk).splitlines():
            h, t = line.split()
            cts[h] = int(t)
    fixes = sorted({r[0] for r in resolved})
    ff, fi = files_of(fixes), files_of(inds)
    rows = []
    for sha, ct, ind in resolved:
        ict = cts.get(ind)
        if ict is None or ict >= ct:
            dropped["inducing not before fix"] += 1
            continue
        a, b = ff.get(sha, []), fi.get(ind, [])
        rows.append({"fix": sha, "ind": ind, "fix_ct": ct, "ind_ct": ict, "lag": (ct - ict) / 86400, "fix_files": a, "ind_files": b})
    json.dump(rows, open("/tmp/gitgalaxy-scratch/claude/argl/links_linux_all.json", "w"))
    both = [r for r in rows if r["fix_files"] and r["ind_files"]]
    since = [r for r in both if r["ind_ct"] >= SINCE]
    print(f"Fixes: trailers in the kernel history: {len(heads)}; resolved and ordered pairs {len(rows)}; dropped {dict(dropped)}")
    print(f"  both commits touch a scanned .c/.h file: {len(both)}; and the inducing commit is from 2014 on (the snapshots start 2014-01): {len(since)}")
    lags = sorted(r["lag"] for r in since)
    print(f"  lag: median {lags[len(lags) // 2]:.0f} d; within 30 days {100 * sum(1 for l in lags if l < 30) / len(lags):.0f}%; a year or more {100 * sum(1 for l in lags if l >= 365) / len(lags):.0f}%")
    share = sum(1 for r in since if not (set(r["fix_files"]) & set(r["ind_files"])))
    print(f"  fix and inducing commit share no file: {share} ({100 * share / len(since):.0f}%): the cross-file pairs")
    bysub = collections.Counter()
    cross = collections.Counter()
    for r in since:
        c = collections.Counter(sub(f) for f in r["fix_files"])
        top = c.most_common(1)[0][0]
        bysub[top] += 1
        if not (set(r["fix_files"]) & set(r["ind_files"])):
            cross[top] += 1
    print("\nPairs by subsystem of the fix (inducing from 2014, both commits in the scanned set); cross-file = no shared file:")
    print(f"  {'subsystem':22s} {'pairs':>7s} {'cross-file':>11s}")
    for k, v in bysub.most_common(30):
        print(f"  {k:22s} {v:7d} {cross[k]:11d}")
    top = bysub.most_common(1)
    yrs = collections.Counter(datetime.datetime.fromtimestamp(r["ind_ct"], datetime.timezone.utc).year for r in since)
    print("\nInducing commits by year: " + ", ".join(f"{y}: {n}" for y, n in sorted(yrs.items())))


if __name__ == "__main__":
    main()
