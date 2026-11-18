#!/usr/bin/env python3
"""Verify the functions a commit is said to have changed (git hunk-header context) by comparing each function's text in the commit and in its first parent (tree-sitter C).
A function counts as changed only if found in both versions with different text; functions that cannot be compared (file renamed or added, function present in one version
only) are kept and counted. Writes a touched.pkl for blast_radius.py with the verified sets. Hypotheses VR1-VR5: docs/sensor-overhaul/sensors/ripple_radius.md.

    python tools/sensor/verify_functions.py REPO PAIRS.json SRC_OUTDIR DST_OUTDIR       (SRC_OUTDIR has touched.pkl / touched_all.pkl from an earlier blast_radius.py run)"""
import collections
import json
import pickle
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import repair_structure as RS  # noqa: E402

_B = {}


def get(repo, spec):
    p = _B.get(repo)
    if p is None:
        p = _B[repo] = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.stdin.write(spec.encode() + b"\n")
    p.stdin.flush()
    head = p.stdout.readline().split()
    if len(head) != 3 or head[1] != b"blob":
        return None
    data = p.stdout.read(int(head[2]))
    p.stdout.read(1)
    return data


def work(job):
    repo, items = job
    out = []
    for sha, funcs in items:
        by_path = collections.defaultdict(list)
        for path, name in funcs:
            by_path[path].append(name)
        kept, st = [], collections.Counter()
        for path, names in by_path.items():
            new, old = get(repo, f"{sha}:{path}"), get(repo, f"{sha}^:{path}")
            if new is None or old is None:
                kept += [(path, n) for n in names]
                st["unverifiable (file renamed, added or no parent)"] += len(names)
                continue
            fn_new, fn_old = RS.functions(new, set(names)), RS.functions(old, set(names))
            for n in names:
                if n in fn_new and n in fn_old:
                    a, b = fn_new[n], fn_old[n]
                    if new[a.start_byte:a.end_byte] == old[b.start_byte:b.end_byte]:
                        st["identical (not edited)"] += 1
                    else:
                        kept.append((path, n))
                        st["verified"] += 1
                else:
                    kept.append((path, n))
                    st["in one version only (kept)"] += 1
        out.append((sha, sorted(kept), dict(st)))
    return out


def main():
    repo, pairs_path, src, dst = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
    dst.mkdir(parents=True, exist_ok=True)
    pairs = json.load(open(pairs_path))
    touched = {}
    for f in ("touched.pkl", "touched_all.pkl"):
        if (src / f).exists():
            touched.update(pickle.load(open(src / f, "rb")))
    shas = list(dict.fromkeys(s for p in pairs for s in (p["ind"], p["fix"])))
    todo = [(s, [tuple(k) for k in touched.get(s, [])]) for s in shas]
    print(f"{repo}: verifying the functions of {len(todo)} commits ({sum(len(f) for _, f in todo)} function entries)", flush=True)
    chunks = [(f"{BR.POOL}/{repo}", todo[i : i + 40]) for i in range(0, len(todo), 40)]
    verified, total = {}, collections.Counter()
    with ProcessPoolExecutor(max_workers=6) as ex:
        for i, res in enumerate(ex.map(work, chunks)):
            for sha, kept, st in res:
                verified[sha] = kept
                total.update(st)
            if (i + 1) % 200 == 0:
                print(f"  {(i + 1) * 40}/{len(todo)} commits", flush=True)
    pickle.dump(verified, open(dst / "touched.pkl", "wb"))
    for f in ("snapshot_cts.npy", "authors.pkl"):
        if (src / f).exists():
            shutil.copy(src / f, dst / f)
    n = sum(total.values())
    print("function entries: " + ", ".join(f"{k} {v} ({100 * v / n:.1f}%)" for k, v in total.most_common()), flush=True)
    json.dump(dict(total), open(dst / "verify_stats.json", "w"))


if __name__ == "__main__":
    main()
