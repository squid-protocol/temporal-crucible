#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS commit history (methods review M6 and M7): one walk of a repo's default branch into a small database that
the defect laws read. No statistic is computed here.

    python tools/laws_history.py --repo NAME --language go --out DIR      -> DIR/history/NAME.db

  commit(sha, ct, author, bot, merge, fix, keyword, n_units, subject)
        one row per commit of the walk (see "Unit of labelling"), oldest first. `ct` committer time; `author` the mailmap-resolved
        "name <email>"; `fix` 1 when the commit is a fix under the rules below; `n_units` the unit source files
        it touches.
  touch(sha, file, path, status)
        the unit source files a commit touches. `file` is the file's LINEAGE id: it follows the file through
        renames (git -M with diff.renameLimit=0), so a fix after a rename still counts for the file that was there
        before. A path that is deleted and later added again is a new lineage.
  lineage(file, path, since, until)
        which path a lineage had from commit time `since` (inclusive) to `until` (exclusive; NULL = still).
  meta(key, value)   head, the merge share, the unit of labelling, counts.

Fix label (M6). The commit's message (subject and body) matches FIXLIKE after `Fixes|Closes|Resolves #N` phrases
are removed (a closed issue of unknown type is not a fix keyword); the author and committer are not bots; and it
touches at least one unit source file (tools/laws_units.py: the repo's language, not test, vendored, generated,
documentation or example code).

Unit of labelling (M6). Where at least MERGE_SHARE of the first-parent commits are merges, the walk is the
first-parent chain and a merge is one unit, labelled from its own message and diffed against its first parent.
Elsewhere the walk is every non-merge commit reachable from the head, in commit-time order, each diffed against
its parent: the commits inside a merged branch are units there (the pilot: sphinx, 28% merges, has 687 fixes on
its first-parent chain and 2,354 among all its non-merge commits).

Not done here, and to be said at the scorer freeze: PR titles and bodies and linked-issue labels (they need the
GitHub API); OSV advisories (the latent class); the extrinsic and regression classes of tools/xc_harvest.py.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import laws_units as U  # noqa: E402
from _engine import POOL_DIR  # noqa: E402

FIXLIKE = re.compile(r"\b(fix(es|ed)?|bug|broke(n)?|break(s|age)?|regress\w*|crash\w*|wrong|incorrect|segfault|leak|"
                     r"overflow|oops|restore)\b", re.I)  # tools/xc_harvest.py's keyword rule
CLOSES = re.compile(r"\b(fix(es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s+(#\d+|https?://\S+/(issues|pull)/\d+)", re.I)
BOT = re.compile(r"\[bot\]|dependabot|renovate|github-actions", re.I)
MERGE_SHARE = 0.30
SEP = "\x1e"
SCHEMA = [
    "CREATE TABLE commit_ (sha TEXT PRIMARY KEY, ct INTEGER, author TEXT, bot INTEGER, merge INTEGER, fix INTEGER, "
    "keyword INTEGER, n_units INTEGER, subject TEXT)",
    "CREATE TABLE touch (sha TEXT, file INTEGER, path TEXT, status TEXT)",
    "CREATE TABLE lineage (file INTEGER, path TEXT, since INTEGER, until INTEGER)",
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)",
    "CREATE INDEX idx_touch_file ON touch(file)", "CREATE INDEX idx_touch_sha ON touch(sha)",
    "CREATE INDEX idx_lineage_path ON lineage(path)",
]


def is_fix_message(message: str) -> bool:
    return FIXLIKE.search(CLOSES.sub(" ", message)) is not None


def merge_share(repo: Path) -> tuple[int, int]:
    """(first-parent commits, merges among them)."""
    count = lambda *a: int(subprocess.run(["git", "-C", str(repo), "rev-list", "--count", "--first-parent", *a, "HEAD"],  # noqa: E731
                                          capture_output=True, text=True).stdout.strip() or 0)
    return count(), count("--merges")


def walk(repo: Path, first_parent: bool):
    """The commits of the walk, oldest first: (sha, ct, author, committer, n_parents, subject, body, changes) with
    changes = [(status letter, path, old path or None)]. first_parent: the first-parent chain, a merge diffed against
    its first parent; else every non-merge commit reachable from HEAD, by commit time."""
    fmt = f"{SEP}%H%x00%ct%x00%aN <%aE>%x00%cN <%cE>%x00%P%x00%s%x00%b%x00"
    how = ["--first-parent", "--diff-merges=first-parent"] if first_parent else ["--no-merges", "--date-order"]
    p = subprocess.run(["git", "-C", str(repo), "-c", "diff.renameLimit=0", "log", *how, "--reverse",
                        "-M", "--name-status", "-z", f"--format={fmt}"], capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[:300])
    for chunk in p.stdout.decode("utf-8", "replace").split(SEP)[1:]:
        sha, ct, author, committer, parents, subject, body, rest = chunk.split("\x00", 7)
        toks = [t for t in rest.split("\x00")]
        toks = [t.lstrip("\n") for t in toks]
        changes, i = [], 0
        while i < len(toks):
            st = toks[i]
            if not st:
                i += 1
                continue
            if st[0] in "RC" and i + 2 < len(toks):
                changes.append((st[0], toks[i + 2], toks[i + 1]))
                i += 3
            elif i + 1 < len(toks):
                changes.append((st[0], toks[i + 1], None))
                i += 2
            else:
                break
        yield sha, int(ct), author, committer, len(parents.split()), subject, body, changes


def harvest(repo: Path, language: str, db: Path) -> dict:
    """Write the history database of `repo`; returns its meta."""
    if db.exists():
        db.unlink()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    for stmt in SCHEMA:
        con.execute(stmt)
    ex = U.Excluder()  # paths only: a .gitattributes of one snapshot is not applied to the whole history
    chain, merges = merge_share(repo)
    merge_units = bool(chain) and merges / chain >= MERGE_SHARE
    commits = sorted(walk(repo, merge_units), key=lambda c: c[1])  # stable: commit time, then the walk's order
    current: dict[str, int] = {}  # path -> lineage id, as the walk goes
    next_id = 0
    unit_cache: dict[str, bool] = {}

    def unit(path: str) -> bool:
        if path not in unit_cache:
            unit_cache[path] = U.language_of(path) == language and ex.why(path) is None
        return unit_cache[path]

    n_fix = n_kw = 0
    for sha, ct, author, committer, n_par, subject, body, changes in commits:
        touched = []
        for st, path, old in changes:
            if st == "R" and old in current:
                fid = current.pop(old)
                con.execute("UPDATE lineage SET until = ? WHERE file = ? AND until IS NULL", (ct, fid))
                current[path] = fid
                con.execute("INSERT INTO lineage VALUES (?, ?, ?, NULL)", (fid, path, ct))
            elif path not in current or st == "A":
                if path in current and st == "A":
                    con.execute("UPDATE lineage SET until = ? WHERE file = ? AND until IS NULL", (ct, current[path]))
                fid = current[path] = next_id
                next_id += 1
                con.execute("INSERT INTO lineage VALUES (?, ?, ?, NULL)", (fid, path, ct))
            else:
                fid = current[path]
            if unit(path) or (old is not None and unit(old)):
                touched.append((sha, fid, path, st))
            if st == "D":
                con.execute("UPDATE lineage SET until = ? WHERE file = ? AND until IS NULL", (ct, fid))
                current.pop(path, None)
        bot = bool(BOT.search(author) or BOT.search(committer))
        kw = is_fix_message(subject + "\n" + body)
        fix = int(kw and not bot and bool(touched))
        n_fix += fix
        n_kw += int(kw)
        con.execute("INSERT INTO commit_ VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (sha, ct, author, int(bot), int(n_par > 1), fix, int(kw), len(touched), subject[:300]))
        con.executemany("INSERT INTO touch VALUES (?, ?, ?, ?)", touched)
    meta = {"language": language, "commits": len(commits), "first_parent_commits": chain, "merges": merges,
            "merge_share": round(merges / chain, 4) if chain else 0, "unit": "first-parent commit, merges included"
            if merge_units else "non-merge commit", "fixes": n_fix, "keyword_commits": n_kw,
            "bots": int(con.execute("SELECT COUNT(*) FROM commit_ WHERE bot = 1").fetchone()[0]),
            "first_ct": commits[0][1] if commits else None, "last_ct": commits[-1][1] if commits else None,
            "head": commits[-1][0] if commits else None, "linguist": U.LINGUIST[:12]}
    con.executemany("INSERT INTO meta VALUES (?, ?)", [(k, str(v)) for k, v in meta.items()])
    con.commit()
    con.close()
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="a clone under the pool, or a path")
    ap.add_argument("--language", required=True, choices=sorted(U.EXTS))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    repo = Path(a.repo) if Path(a.repo).is_dir() else POOL_DIR / a.repo
    meta = harvest(repo, a.language, a.out / "history" / f"{repo.name}.db")
    print(f"{repo.name}: " + ", ".join(f"{k} {v}" for k, v in meta.items() if k not in ("head", "linguist", "first_ct", "last_ct")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
