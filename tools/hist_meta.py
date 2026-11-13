#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Harvest commit BODIES and the structured links inside them (docs/LABEL_CARD.md, the cascade).

    python tools/hist_meta.py --out <laws-study/pilot>/meta [--repos a,b]
    python tools/hist_meta.py --out ... --report

The history DBs store the commit SUBJECT and nothing else, so every label this programme has built is a
judgement about one line of text. Trailers, issue references, revert targets and CVE ids live in the BODY and
were never harvested: that is why `CVE`, `co-authored-by` and `reported-by` all measured 0% -- not absent,
unread. postgres shows 0% issue references in its subjects and puts them in bodies.

Writes a SEPARATE database per repo and never touches `history/<repo>.db`, which is an input to published
results. Structured links are extracted, not judged:

  revert   `This reverts commit <sha>` / `Revert "..."`   -- the cleanest fix signal there is
  issue    `#123`, `fixes #123`, `bug 123`, `GH-123`      -- near ground truth when it resolves to a bug
  cve      `CVE-2024-1234`
  trailer  Co-authored-by / Reported-by / Reviewed-by / Signed-off-by / Closes / Fixes

Nothing here decides what a fix is. It supplies the tiers a cascade label would rank above a keyword gate.
"""
from __future__ import annotations

import argparse, re, sqlite3, subprocess, sys, time
from pathlib import Path

POOL = Path("/srv/storage_16tb/projects/temporal-crucible-pool")
REPOS = ("commons-lang", "curl", "libgit2", "libxml2", "ndpi", "openssl",
         "postgres", "prometheus", "redis", "ripgrep", "sphinx")
SEP, EOR = "\x01", "\x02"
RX = {
    "revert_sha": re.compile(r"This reverts commit ([0-9a-f]{7,40})", re.I),
    "revert_sub": re.compile(r'^Revert\s+"', re.I | re.M),
    # A BARE reference and a FIX-SEMANTIC reference are different evidence and must not share a tier.
    # curl writes `Closes #N` on every merged PR -- that is a workflow artefact, not a bug signal; audited
    # at roughly 2 of 9 on the commits the keyword gate misses. `Fixes #N` / `Resolves #N` claims a defect.
    "issue_fix":  re.compile(r"\b(?:fix(?:es|ed)?|resolve[sd]?)\s+(?:#|\bGH-|\bbug\s*#?)(\d{1,7})\b", re.I),
    # SA3 opt-in (checklist item 18): non-GitHub trackers (Jira PROJ-123, Python bpo-123, BSD PR 123, GnuPG-bug-id)
    # and kernel/C `Fixes: <sha>` references, only matched when --sa3-links is passed.
    "issue_fix_sa3": re.compile(
        r"\b(?:fix(?:es|ed)?|resolve[sd]?)\s+(?:#|\bGH-|\bbug\s*#?|\bbpo-|\bPR\s*#?)(\d{1,7})\b"
        r"|\b(?:fix(?:es|ed)?|resolve[sd]?)\s*:?\s+([A-Z][A-Z0-9_]{1,15}-\d{1,7})\b"
        r"|^GnuPG-bug-id:\s*(\d+)\b"
        r"|^Fixes:\s*([0-9a-f]{7,40})\b",
        re.I | re.M,
    ),
    "issue":      re.compile(r"(?:#|\bGH-|\bbug\s*#?)(\d{1,7})\b", re.I),
    "cve":        re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I),
    "trailer":    re.compile(r"^(Co-authored-by|Reported-by|Reviewed-by|Signed-off-by|Tested-by|Closes|Fixes|Bug):\s*(.+)$",
                             re.I | re.M),
}


def extract_links(sha: str, subject: str, body: str, sa3_links: bool = False) -> list[tuple[str, str, str]]:
    """Extract structured links from (subject, body). When `sa3_links` is False (default), behaviour is identical to
    the original harvest used by LAWS and MOD-1."""
    links: list[tuple[str, str, str]] = []
    text = subject + "\n" + body
    for m in RX["revert_sha"].finditer(text):
        links.append((sha, "revert", m.group(1)))
    if RX["revert_sub"].search(text):
        links.append((sha, "revert", ""))
    fixref = {m.group(1) for m in RX["issue_fix"].finditer(text)}
    if sa3_links:
        for m in RX["issue_fix_sa3"].finditer(text):
            val = next((g for g in m.groups() if g is not None), None)
            if val:
                fixref.add(val)
    for v in sorted(fixref):
        links.append((sha, "issue_fix", v))
    for m in RX["issue"].finditer(text):
        if m.group(1) not in fixref:
            links.append((sha, "issue", m.group(1)))
    for m in RX["cve"].finditer(text):
        links.append((sha, "cve", m.group(0).upper()))
    for m in RX["trailer"].finditer(body):
        links.append((sha, f"trailer:{m.group(1).lower()}", m.group(2).strip()[:200]))
    return links


def schema(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS body (sha TEXT PRIMARY KEY, subject TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS link (sha TEXT, kind TEXT, value TEXT);
    CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
    CREATE INDEX IF NOT EXISTS link_sha ON link(sha);
    CREATE INDEX IF NOT EXISTS link_kind ON link(kind);
    """)


def harvest(repo: Path, con, with_merges: bool = False, sa3_links: bool = False) -> tuple[int, int]:
    p = subprocess.Popen(["git", "-C", str(repo), "log", *([] if with_merges else ["--no-merges"]),
                          f"--format={SEP}%H%n%s%n%b{EOR}"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                         errors="replace", bufsize=1 << 20)
    bodies, links, nb, nl = [], [], 0, 0
    buf = ""
    for chunk in p.stdout:
        buf += chunk
        while EOR in buf:
            rec, buf = buf.split(EOR, 1)
            rec = rec.lstrip("\n")
            if not rec.startswith(SEP):
                continue
            lines = rec[1:].split("\n")
            sha, subject = lines[0].strip(), (lines[1] if len(lines) > 1 else "")
            body = "\n".join(lines[2:]).strip()
            bodies.append((sha, subject, body))
            links.extend(extract_links(sha, subject, body, sa3_links=sa3_links))
            if len(bodies) >= 5000:
                con.executemany("INSERT OR REPLACE INTO body VALUES (?,?,?)", bodies)
                con.executemany("INSERT INTO link VALUES (?,?,?)", links)
                con.commit(); nb += len(bodies); nl += len(links); bodies, links = [], []
    p.wait()
    if bodies:
        con.executemany("INSERT OR REPLACE INTO body VALUES (?,?,?)", bodies)
        con.executemany("INSERT INTO link VALUES (?,?,?)", links)
        con.commit(); nb += len(bodies); nl += len(links)
    return nb, nl


def report(out: Path) -> int:
    print(f"{'repo':14}{'commits':>9}{'with body':>11}{'revert':>8}{'fix-ref':>9}{'bare-ref':>10}{'cve':>7}{'trailers':>10}")
    for r in REPOS:
        db = out / f"{r}.db"
        if not db.exists():
            print(f"{r:14}{'—':>9}{'—':>11}{'—':>8}{'—':>8}{'—':>7}{'—':>10}"); continue
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        n = c.execute("select count(*) from body").fetchone()[0]
        nb = c.execute("select count(*) from body where body != ''").fetchone()[0]
        k = {x: c.execute("select count(distinct sha) from link where kind=?", (x,)).fetchone()[0]
             for x in ("revert", "issue_fix", "issue", "cve")}
        tr = c.execute("select count(distinct sha) from link where kind like 'trailer:%'").fetchone()[0]
        c.close()
        pc = lambda v: f"{v/n:.0%}" if n else "—"
        print(f"{r:14}{n:>9,}{pc(nb):>11}{pc(k['revert']):>8}{pc(k['issue_fix']):>9}{pc(k['issue']):>10}"
              f"{pc(k['cve']):>7}{pc(tr):>10}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=Path, default=POOL)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repos")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--with-merges", action="store_true",
                    help="read merge commits too (MOD-1 Amendment 3: where a merge is the labelled unit)")
    ap.add_argument("--sa3-links", action="store_true",
                    help="opt-in (SA3): match Jira, bpo-, PR, GnuPG-bug-id and Fixes: <sha> in issue_fix")
    a = ap.parse_args()
    if a.report:
        return report(a.out)
    a.out.mkdir(parents=True, exist_ok=True)
    for r in (a.repos.split(",") if a.repos else REPOS):
        db = a.out / f"{r}.db"
        con = sqlite3.connect(db); schema(con)
        if con.execute("select value from meta where key='done'").fetchone():
            print(f"  {r}: already harvested"); con.close(); continue
        src = a.pool / r
        if not src.is_dir():
            print(f"  {r}: no clone at {src}"); con.close(); continue
        t0 = time.time()
        nb, nl = harvest(src, con, a.with_merges, sa3_links=a.sa3_links)
        con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)",
                        [("bodies", str(nb)), ("links", str(nl)),
                         ("seconds", str(round(time.time() - t0, 1))), ("done", "1")])
        con.commit(); con.close()
        print(f"  {r}: {nb:,} bodies, {nl:,} links, {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
