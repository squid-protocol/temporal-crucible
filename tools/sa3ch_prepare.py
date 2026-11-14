#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SA3-CH preparation from git alone: the earlier snapshot, what lies between the two trees, and which files
match. It reads no scan and no outcome.

    python tools/sa3ch_prepare.py --repo NAME      # -> <pilot>/sa3ch_prep/NAME.json
    python tools/sa3ch_prepare.py --table

docs/sa3_change_registration.md, Amendment 1:

  t-1        the last commit on the FIRST-PARENT ancestry of the t0 snapshot whose committer time is at or before
             the snapshot's time minus 365 days (rule 1). By construction an ancestor of t0.
  activity   per t0 unit file, the non-merge commits in t-1..t0 that touch it, followed back through renames;
             tree-wide commits (>= 10% of the t0 unit files and >= 20 of them) removed; bots counted separately.
  lines      added + deleted from `git diff --numstat -M t-1 t0` (rule 1), which also gives the t-1 path.
  identical  the file's blob hash is the same at both ends (rule 5, the blob-identical gate).
  born       no t-1 path: the file did not exist a year earlier (rule 2).

Implementation note, recorded in the freeze document: the amendment says activity is counted "by the history's
lineage id". The history databases hold only the first-parent chain for merge-workflow repos, so renames are
followed here from git directly (`-M`), for every repo the same way. The intent -- count what lies between the
two trees, through renames -- is unchanged.
"""
from __future__ import annotations

import argparse, json, subprocess, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import laws_units as U  # noqa: E402
from _engine import POOL_DIR  # noqa: E402
from laws_history import BOT  # noqa: E402
from mod1_lift import frame, STUDY, WIDE_SHARE, WIDE_MIN_FILES  # noqa: E402

SCANS = STUDY / "sa3_scans"
OUT = STUDY / "sa3ch_prep"
GAP_DAYS = 365


def git(repo: str, *args, text=True, timeout=3600) -> str:
    return subprocess.run(["git", "-C", str(POOL_DIR / repo), *args], capture_output=True, text=text,
                          errors="replace" if text else None, timeout=timeout).stdout


def blobs(repo: str, sha: str) -> dict[str, str]:
    out = {}
    for line in git(repo, "ls-tree", "-r", "-z", sha).split("\x00"):
        if "\t" in line:
            meta, path = line.split("\t", 1)
            out[path] = meta.split()[2]
    return out


def prepare(repo: str) -> dict:
    side = json.loads((SCANS / f"{repo}.json").read_text())
    t0 = side["snapshot"]
    f = frame(repo)
    ex = U.Excluder(side["attrs"], include_tutorials=True)
    gen = set(side["generated"])
    unit = lambda p: U.language_of(p) in f["langs"] and ex.why(p, p in gen) is None  # noqa: E731  (judged at t0)
    t0_ct = int(git(repo, "show", "-s", "--format=%ct", t0).strip())
    t1 = git(repo, "rev-list", "--first-parent", "-1", f"--before={t0_ct - GAP_DAYS * 86400}", t0).strip()
    out = {"repo": repo, "t0": t0, "t0_ct": t0_ct, "status": "ok"}
    if not t1:
        return {**out, "status": "no_earlier_snapshot", "why": "the repo's first-parent line does not reach back 365 days"}
    t1_ct = int(git(repo, "show", "-s", "--format=%ct", t1).strip())
    out.update({"t1": t1, "t1_ct": t1_ct, "gap_days": round((t0_ct - t1_ct) / 86400, 1)})
    b0, b1 = blobs(repo, t0), blobs(repo, t1)
    units = sorted(p for p in b0 if unit(p))
    # --- lines changed and the t-1 path, from one diff between the two trees
    old_of, lines = {}, {}
    toks = git(repo, "diff", "--numstat", "-M", "-z", t1, t0).split("\x00")
    i = 0
    while i < len(toks):
        head = toks[i]
        if not head:
            i += 1
            continue
        a, d, path = head.split("\t", 2)
        if path == "":                                   # a rename: the two paths follow as separate tokens
            old, new = toks[i + 1], toks[i + 2]
            i += 3
        else:
            old = new = path
            i += 1
        n = (int(a) if a.isdigit() else 0) + (int(d) if d.isdigit() else 0)
        lines[new] = n
        old_of[new] = old
    # --- the commits between the trees, newest first, following each t0 file back through renames
    alias = {p: p for p in units}                        # t0 path -> the name it has at the commit being read
    at = defaultdict(set)
    for p in units:
        at[p].add(p)
    touched: dict[str, list[tuple[str, bool]]] = defaultdict(list)   # t0 path -> [(sha, bot)]
    per_commit: dict[str, set[str]] = defaultdict(set)
    raw = git(repo, "log", "--no-merges", "-M", "--name-status", "-z",
              "--format=%x01%H%x00%aN <%aE>%x00%cN <%cE>%x00", f"{t1}..{t0}")
    n_commits = 0
    for chunk in raw.split("\x01")[1:]:
        sha, au, co, rest = chunk.split("\x00", 3)
        bot = bool(BOT.search(au) or BOT.search(co))
        n_commits += 1
        toks = [t.lstrip("\n") for t in rest.split("\x00")]
        j, renames = 0, []
        while j < len(toks):
            st = toks[j]
            if not st:
                j += 1
                continue
            if st[0] in "RC" and j + 2 < len(toks):
                old, new = toks[j + 1], toks[j + 2]
                j += 3
                if st[0] == "R":
                    renames.append((old, new))
            else:
                old = new = toks[j + 1] if j + 1 < len(toks) else ""
                j += 2
            for p in list(at.get(new, ())):
                touched[p].append((sha, bot))
                per_commit[sha].add(p)
        for old, new in renames:                         # older commits know the file by its old name
            for p in list(at.pop(new, ())):
                alias[p] = old
                at[old].add(p)
    wide = {s for s, ps in per_commit.items() if len(ps) >= WIDE_MIN_FILES and len(ps) >= WIDE_SHARE * len(units)}
    files = {}
    for p in units:
        old = old_of.get(p, p)
        born = old not in b1
        ts = [(s, bot) for s, bot in touched.get(p, ()) if s not in wide]
        files[p] = {"t1_path": None if born else old, "lines": lines.get(p, 0),
                    "commits": sum(1 for _, bot in ts if not bot), "bot_commits": sum(1 for _, bot in ts if bot),
                    "identical": (not born) and b1.get(old) == b0[p], "renamed": (not born) and old != p}
    m = [v for v in files.values() if v["t1_path"]]
    out.update({"commits_between": n_commits, "tree_wide_between": len(wide), "unit_files_t0": len(units),
                "matched": len(m), "born": len(units) - len(m), "renamed": sum(v["renamed"] for v in m),
                "identical": sum(v["identical"] for v in m), "edited": sum(1 for v in m if v["commits"] >= 1),
                "changed_with_no_commit": sum(1 for v in m if not v["identical"] and v["commits"] + v["bot_commits"] == 0),
                "files": files})
    return out


def table() -> int:
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))]
    print(f"{'repo':<18}{'gap d':>7}{'between':>9}{'wide':>5}{'units':>7}{'matched':>8}{'born':>6}{'renamed':>8}"
          f"{'identical':>10}{'edited':>7}{'no-commit':>10}")
    for r in rows:
        if r["status"] != "ok":
            print(f"{r['repo']:<18}{r['status']}: {r.get('why')}"); continue
        print(f"{r['repo']:<18}{r['gap_days']:>7}{r['commits_between']:>9}{r['tree_wide_between']:>5}{r['unit_files_t0']:>7}"
              f"{r['matched']:>8}{r['born']:>6}{r['renamed']:>8}{r['identical']:>10}{r['edited']:>7}{r['changed_with_no_commit']:>10}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--table", action="store_true")
    a = ap.parse_args()
    if a.table:
        return table()
    OUT.mkdir(parents=True, exist_ok=True)
    r = prepare(a.repo)
    (OUT / f"{a.repo}.json").write_text(json.dumps(r) + "\n")
    print(f"{a.repo}: {r['status']} gap {r.get('gap_days')} d, matched {r.get('matched')}, born {r.get('born')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
