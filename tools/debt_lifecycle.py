#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Lifecycle of self-admitted debt comments (TODO / FIXME / XXX / HACK) in C/C++ (EXPLORATORY).

Every debt comment line is followed through the full non-merge history of each repo: when it is added, when it is
removed, and by whom.
- A line removed and re-added with the same text in one commit (anywhere) is a **move**, not a removal.
- A removed line paired with an added line of the same marker in the same file and commit is a **rewording**; the item
  continues.
- File renames come from a separate `git log --diff-filter=R` pass, because a rename that leaves the debt lines alone
  never shows them in a diff.

Part A (all repos) reads no fix label. Part B reads fix labels (chg_eval.fix_events) for the CORE repos only: it asks
which kinds of commits remove debt. The UNSEEN repos are not read in Part B, so a later registration can use them.

    python tools/debt_lifecycle.py [--repos ...]      # -> docs/debt_lifecycle_exploratory.md

Comment detection on diff lines is heuristic: the marker must follow `//` or `/*`, or the line must start with `*`
(a block-comment continuation). Debt lines inside block comments without a leading `*` are missed.
"""
from __future__ import annotations

import argparse
import multiprocessing
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, fix_events  # noqa: E402

CORE = ("curl", "openssl", "ndpi", "harfbuzz", "libarchive")
UNSEEN = ("libgit2", "libxml2", "postgres", "redis")
MARK = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
EXCL = re.compile(r"(^|/)(tests?|docs?|fuzz|fuzzing|scripts|examples?|\.github)/")
PATHSPEC = [f"*{e}" for e in CEXT + CPPEXT]
YEAR = 365.25 * 86400
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True).stdout.decode("utf-8", "replace")


def keep(path):
    return path is not None and path.endswith(CEXT + CPPEXT) and not EXCL.search(path)


def debt_line(s):
    """(marker, normalised text) if the diff line is a comment carrying a debt marker."""
    m = MARK.search(s)
    if not m:
        return None
    st = s.strip()
    pre = s[:m.start()]
    if not ("//" in pre or "/*" in pre or st.startswith("*")):
        return None
    t = re.sub(r"^(/\*+|\*+|//+)\s*", "", st)
    t = re.sub(r"\s*\*+/\s*$", "", t)
    return m.group(1), " ".join(t.split())


def track(r):
    repo = POOL_DIR / r
    order = git(repo, "log", "--no-merges", "--reverse", "--format=%H").split()
    meta = {}
    for ln in git(repo, "log", "--no-merges", "--format=%H %ct %ae").splitlines():
        h, ct, ae = ln.split(" ", 2)
        meta[h] = (int(ct), ae.strip().lower())
    renames = defaultdict(list)
    cur = None
    for ln in git(repo, "log", "--no-merges", "-M", "--diff-filter=R", "--name-status", "--format=@@C %H",
                  "--", *PATHSPEC).splitlines():
        if ln.startswith("@@C "):
            cur = ln[4:].strip()
        elif ln.startswith("R") and cur:
            parts = ln.split("\t")
            if len(parts) == 3:
                renames[cur].append((parts[1], parts[2]))
    ev = defaultdict(lambda: {"rm": [], "add": [], "deleted": set()})
    cur = old = new = None
    for ln in git(repo, "log", "--no-merges", "-M", "-p", "-U0", "--no-color", "-G", r"(TODO|FIXME|XXX|HACK)",
                  "--format=@@C %H", "--", *PATHSPEC).splitlines():
        if ln.startswith("@@C "):
            cur = ln[4:].strip()
            continue
        if ln.startswith("--- "):
            old = None if ln[4:] == "/dev/null" else ln[6:]
            continue
        if ln.startswith("+++ "):
            new = None if ln[4:] == "/dev/null" else ln[6:]
            if new is None and old:
                ev[cur]["deleted"].add(old)
            continue
        if ln.startswith("-") and keep(old):
            d = debt_line(ln[1:])
            if d:
                ev[cur]["rm"].append((old, *d))
        elif ln.startswith("+") and keep(new):
            d = debt_line(ln[1:])
            if d:
                ev[cur]["add"].append((new, *d))
    alive = defaultdict(deque)  # (path, text) -> item ids
    items = []
    moves = rewords = 0
    def apply_renames(h):
        for a, b in renames.get(h, ()):
            for (p, t) in [k for k in alive if k[0] == a and alive[k]]:
                alive[(b, t)].extend(alive.pop((p, t)))

    for h in order:
        if h not in ev:
            apply_renames(h)
            continue
        e = ev[h]
        ct, author = meta.get(h, (None, ""))
        rm, add = list(e["rm"]), list(e["add"])
        # moves: same text removed and added anywhere in the commit
        add_by_text = Counter(t for _, _, t in add)
        moved = []
        for x in rm:
            if add_by_text[x[2]] > 0:
                add_by_text[x[2]] -= 1
                moved.append(x)
        for x in moved:
            rm.remove(x)
            for y in add:
                if y[2] == x[2]:
                    add.remove(y)
                    break
            q = alive.get((x[0], x[2]))
            if q:
                iid = q.popleft()
                alive[(next((y[0] for y in e["add"] if y[2] == x[2]), x[0]), x[2])].append(iid)
            moves += 1
        # rewordings: same marker, same file
        for x in list(rm):
            y = next((y for y in add if y[1] == x[1] and y[0] == x[0]), None)
            if y is None:
                continue
            rm.remove(x)
            add.remove(y)
            q = alive.get((x[0], x[2]))
            if q:
                alive[(y[0], y[2])].append(q.popleft())
            rewords += 1
        for (p, mk, t) in rm:
            q = alive.get((p, t))
            if not q:
                continue
            it = items[q.popleft()]
            it.update(end=ct, end_sha=h, end_author=author, file_deleted=p in e["deleted"])
        for (p, mk, t) in add:
            alive[(p, t)].append(len(items))
            items.append({"r": r, "marker": mk, "start": ct, "author": author, "end": None, "short": len(t) <= 6})
        apply_renames(h)  # after the diff: removals in a rename commit name the old path
    head_ct = meta[order[-1]][0] if order else 0
    return r, items, head_ct, moves, rewords, len(order)


def km_median(t, e):
    """Kaplan-Meier median (years) and survival at 1 and 5 years."""
    order = np.argsort(t)
    t, e = t[order], e[order]
    n = len(t)
    s, out, med = 1.0, {}, np.nan
    at_risk = n
    i = 0
    marks = {1: None, 5: None}
    while i < n:
        j = i
        while j < n and t[j] == t[i]:
            j += 1
        d = e[i:j].sum()
        for k in marks:
            if marks[k] is None and t[i] > k:
                marks[k] = s
        if d:
            s *= 1 - d / at_risk
        if np.isnan(med) and s <= 0.5:
            med = t[i]
        at_risk -= j - i
        i = j
    for k in marks:
        out[k] = s if marks[k] is None else marks[k]
    return med, out[1], out[5]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="+", default=list(CORE + UNSEEN))
    a = ap.parse_args()
    with multiprocessing.get_context("fork").Pool(min(len(a.repos), 9)) as p:
        res = {r: (items, head, mv, rw, nc) for r, items, head, mv, rw, nc in p.imap_unordered(track, a.repos)}
    for r in a.repos:
        log(f"{r}: debt items {len(res[r][0]):,}; moves {res[r][2]:,}; rewordings {res[r][3]:,}")
    L = ["# Self-admitted debt comments in C: how long they live and what removes them (EXPLORATORY)", "",
         "**Status: exploratory.** Every TODO / FIXME / XXX / HACK comment line in C/C++ files (tests, docs, fuzz, "
         "scripts and examples excluded) is followed through each repo's non-merge history. Script: "
         "`tools/debt_lifecycle.py`. Part A reads no fix label. Part B reads fix labels for the core repos only "
         f"({', '.join(CORE)}); the unseen repos ({', '.join(UNSEEN)}) are not read there.", "",
         "- **removed** = the debt line left the file. **Moves** (same text removed and re-added in one commit) and "
         "**rewordings** (same marker, same file, same commit) are not removals. **repaid** = removed while the file "
         "still exists.",
         "- Comment detection on diff lines is heuristic (see the script docstring).", "",
         "## A. Survival (Kaplan-Meier; still present at HEAD = censored)", "",
         "| repo | commits | debt items | moves / rewordings | removed (any) | of removed: file deleted | of removed: "
         "same author | median life, years | still present after 1 y | after 5 y |",
         "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|"]
    allit = []
    for r in a.repos:
        items, head, mv, rw, nc = res[r]
        if not items:
            L.append(f"| {r} | {nc:,} | 0 | | | | | | | |")
            continue
        allit += [dict(x, head=head) for x in items]
        t = np.array([((x["end"] if x["end"] is not None else head) - x["start"]) / YEAR for x in items])
        e = np.array([x["end"] is not None for x in items], float)
        med, s1, s5 = km_median(np.maximum(t, 0), e)
        rem = [x for x in items if x["end"] is not None]
        fd = sum(x["file_deleted"] for x in rem)
        same = sum(x["end_author"] == x["author"] for x in rem)
        L.append(f"| {r} | {nc:,} | {len(items):,} | {mv:,} / {rw:,} | {len(rem) / len(items):.0%} | "
                 f"{fd / max(len(rem), 1):.0%} | {same / max(len(rem), 1):.0%} | "
                 f"{med:.1f} | {s1:.0%} | {s5:.0%} |" if np.isfinite(med) else
                 f"| {r} | {nc:,} | {len(items):,} | {mv:,} / {rw:,} | {len(rem) / len(items):.0%} | "
                 f"{fd / max(len(rem), 1):.0%} | {same / max(len(rem), 1):.0%} | > observed | {s1:.0%} | {s5:.0%} |")
    L += ["", "Same author = the removing commit's author email equals the adding commit's.", "",
          "### By marker (all repos pooled)", "",
          "| marker | items | removed | median life, years | after 5 y | bare (≤ 6 chars, e.g. `TODO`) |",
          "|---|---:|---:|---:|---:|---:|"]
    for mk in ("TODO", "FIXME", "XXX", "HACK"):
        xs = [x for x in allit if x["marker"] == mk]
        if not xs:
            continue
        t = np.array([((x["end"] if x["end"] is not None else x["head"]) - x["start"]) / YEAR for x in xs])
        e = np.array([x["end"] is not None for x in xs], float)
        med, _, s5 = km_median(np.maximum(t, 0), e)
        L.append(f"| {mk} | {len(xs):,} | {e.mean():.0%} | {med:.1f} | {s5:.0%} | {np.mean([x['short'] for x in xs]):.0%} |"
                 if np.isfinite(med) else
                 f"| {mk} | {len(xs):,} | {e.mean():.0%} | > observed | {s5:.0%} | {np.mean([x['short'] for x in xs]):.0%} |")
    L += ["", "### Debt still open at HEAD, by age", "", "| repo | open items | median age, years | open > 10 years |",
          "|---|---:|---:|---:|"]
    for r in a.repos:
        items, head = res[r][0], res[r][1]
        op = [(head - x["start"]) / YEAR for x in items if x["end"] is None]
        if op:
            L.append(f"| {r} | {len(op):,} | {np.median(op):.1f} | {np.mean(np.array(op) > 10):.0%} |")

    # Part B: which commits remove debt (core only)
    core = [r for r in a.repos if r in CORE]
    if core:
        L += ["", "## B. What kind of commit repays debt? (core repos only; fix labels read here)", "",
              "Compared with all non-merge commits touching C/C++ files. Repaid = removed while the file still exists.",
              "", "| repo | repaid items | by a fix commit (any class) | all C commits that are fixes | by a CVE fix | "
              "all C commits that are CVE fixes |", "|---|---:|---:|---:|---:|---:|"]
        for r in core:
            evs, _ = fix_events(r)
            cls = {sha: k for _, sha, _, k in evs}
            allc = git(POOL_DIR / r, "log", "--no-merges", "--format=%H", "--", *PATHSPEC).split()
            rep = [x for x in res[r][0] if x["end"] is not None and not x["file_deleted"]]
            if not rep or not allc:
                continue
            fx = np.mean([x["end_sha"] in cls for x in rep])
            cv = np.mean([cls.get(x["end_sha"]) == "latent" for x in rep])
            bfx = np.mean([h in cls for h in allc])
            bcv = np.mean([cls.get(h) == "latent" for h in allc])
            L.append(f"| {r} | {len(rep):,} | {fx:.1%} | {bfx:.1%} | {cv:.2%} | {bcv:.2%} |")
        L += ["", "Item-level shares, not commit-level: one commit that removes many debt lines counts many times."]
    L += ["", f"Runtime {time.time() - T0:.0f}s."]
    (DOCS_DIR / "debt_lifecycle_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
