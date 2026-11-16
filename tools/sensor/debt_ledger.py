#!/usr/bin/env python3
"""Prototype debt sensor: a ledger of open self-admitted debt (TODO / FIXME / XXX / HACK) with age, owner, file activity,
and a repo-relative staleness read from the repo's OWN repayment history (EXPLORATORY).

    python tools/sensor/debt_ledger.py libgit2 libxml2 curl
"""
import sys, re, subprocess, time, collections, pathlib
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import debt_lifecycle as DL
YEAR = DL.YEAR
def km_curve(items, head_ct):
    """Kaplan-Meier survival of debt items; event = removed while the file still exists; file deletion censors."""
    t = np.array([((it["end"] or head_ct) - it["start"]) / YEAR for it in items]); e = np.array([it["end"] is not None and not it.get("file_deleted", False) for it in items])
    o = np.argsort(t); t, e = t[o], e[o]; n = len(t); s = 1.0; pts = []; i = 0; at = n
    while i < n:
        j = i
        while j < n and t[j] == t[i]: j += 1
        d = e[i:j].sum()
        if d: s *= 1 - d / at
        pts.append((t[i], s)); at -= j - i; i = j
    return pts
def surv(pts, age):
    s = 1.0
    for t, v in pts:
        if t > age: break
        s = v
    return s
def open_items(repo):
    out = DL.git(repo, "grep", "-n", "-I", "-E", r"\b(TODO|FIXME|XXX|HACK)\b", "HEAD", "--", *DL.PATHSPEC).splitlines(); items = []
    for ln in out:
        try: _, rest = ln.split(":", 1); path, num, text = rest.split(":", 2)
        except ValueError: continue
        if not DL.keep(path): continue
        d = DL.debt_line(text)
        if d: items.append((path, int(num), d[0], len(d[1]) <= 6 if len(d) > 1 else False, text.strip()[:110]))
    return items
def blame(repo, path, lines):
    res = {}
    out = DL.git(repo, "blame", "--line-porcelain", "-w", "HEAD", "--", path).splitlines(); cur = None; meta = {}
    for ln in out:
        m = re.match(r"^[0-9a-f]{40} \d+ (\d+)", ln)
        if m: cur = int(m.group(1)); meta = {}
        elif ln.startswith("author-mail "): meta["mail"] = ln[12:].strip("<>").lower()
        elif ln.startswith("author-time "): meta["t"] = int(ln[12:])
        elif ln.startswith("\t") and cur in lines: res[cur] = dict(meta)
    return res
def run(name):
    repo = DL.POOL_DIR / name; _, items, head_ct, _, _, _ = DL.track(name); pts = km_curve(items, head_ct)
    closed = [x for x in items if x["end"] is not None and not x.get("file_deleted", False)]
    s1, s5 = surv(pts, 1), surv(pts, 5)
    life = np.array([(x["end"] - x["start"]) / YEAR for x in closed]); p50, p90 = np.percentile(life, 50), np.percentile(life, 90)
    since = head_ct - 2 * YEAR
    active = set(DL.git(repo, "log", "--no-merges", f"--since=@{int(since)}", "--format=%ae").lower().split())
    hot = collections.Counter(p for p in DL.git(repo, "log", "--no-merges", f"--since=@{int(head_ct - YEAR)}", "--name-only", "--format=").splitlines() if p)
    oi = open_items(repo); byf = collections.defaultdict(list)
    for it in oi: byf[it[0]].append(it)
    rows = []
    for path, its in byf.items():
        b = blame(repo, path, {i[1] for i in its})
        for (p, ln, mk, bare, text) in its:
            m = b.get(ln)
            if not m: continue
            age = (head_ct - m["t"]) / YEAR; rows.append(dict(path=p, line=ln, marker=mk, bare=bare, age=age, stale=1 - surv(pts, age), fossil=age > p90, owner_active=m["mail"] in active, file_commits_1y=hot.get(p, 0), text=text))
    return name, rows, s1, s5, len(items), len(closed), p50, p90
if __name__ == "__main__":
    for n in sys.argv[1:]:
        name, rows, s1, s5, ni, nc, p50, p90 = run(n)
        if not rows: print(n, "no open items"); continue
        age = np.array([r["age"] for r in rows]); st = np.array([r["stale"] for r in rows])
        print(f"\n=== {name}: {len(rows)} open debt markers at HEAD ({ni} tracked over history, {nc} repaid). Repo habit: {100*(1-s1):.0f}% repaid within 1 year, {100*(1-s5):.0f}% within 5 years")
        print(f"  by marker: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(r['marker'].upper() for r in rows).most_common()) + f"; bare (no explanation): {100*np.mean([r['bare'] for r in rows]):.0f}%")
        print(f"  age: median {np.median(age):.1f} y, older than 5 y: {100*np.mean(age>5):.0f}%, older than 10 y: {100*np.mean(age>10):.0f}%")
        print(f"  this repo's habit: debt it repaid took a median {p50:.2f} y, 90% within {p90:.1f} y. Open items older than that ('fossils'): {100*np.mean([r['fossil'] for r in rows]):.0f}%")
        print(f"  author no longer active (no commit in 2 y): {100*np.mean([not r['owner_active'] for r in rows]):.0f}%; in files changed >= 5 times in the last year: {sum(1 for r in rows if r['file_commits_1y']>=5)}")
        pri = sorted([r for r in rows if r["file_commits_1y"] >= 5 and r["fossil"]], key=lambda r: (-r["age"], -r["file_commits_1y"]))[:5]; print(f"  fossils in files changed >= 5 times in the last year: {sum(1 for r in rows if r['fossil'] and r['file_commits_1y']>=5)}")
        print("  worklist: fossil debt in files being changed now (cheapest moment to decide):")
        for r in pri: print(f"    {r['path']}:{r['line']}  {r['marker'].upper():5s} age {r['age']:4.1f} y  author {'active' if r['owner_active'] else 'inactive'}  file edits last year {r['file_commits_1y']:3d}  | {r['text'][:70]}")
