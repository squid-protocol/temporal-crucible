#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The CASCADE fix label: rank structured evidence above the keyword gate (docs/recall_audit.md).

    python tools/label_cascade.py --report                 # tier sizes and recall recovery per repo
    python tools/label_cascade.py --sample T2 --repo curl  # draw an audit sample for one tier
    python tools/label_cascade.py --emit <dir>             # write <repo>.db: sha -> tier

**Why.** The keyword gate was measured at 0.41 recall on curl and 0.26 on commons-lang: it misses most real
fixes, and it misses them by WRITING STYLE -- a commit that repairs a NULL dereference but never says "fix"
is invisible to it. Structured evidence does not care how the subject was phrased.

Tiers, strongest first. A commit takes the HIGHEST tier it matches, and the tier travels with the label so
each one can carry its own precision instead of hiding inside a single number.

  T1 revert    `This reverts commit <sha>` -- something was wrong enough to undo. The cleanest signal in the
               system; xc's regression-via-revert audits at 0.73-0.87.
  T2 fixref    `Fixes #N` / `Resolves #N` -- the message CLAIMS a defect, by verb. Distinct from a bare
               reference, which is the first thing an audit of this cascade showed: curl writes `Closes #N`
               on every merged PR, and only about 2 of 9 such commits that the keyword gate misses are real
               fixes. Stronger still once the issue's own labels are read (`--resolve`, not built).
  T3 cve       a CVE id appears. Rare and near-certain.
  T4 keyword   the v3c keyword gate -- measured, 0.70-0.86 precision, 0.41 recall.
  T5 bareref   a bare `#N` or `Closes #N` and nothing else. Kept LAST and flagged: on curl it is mostly
               workflow noise, and a study should normally exclude it.

Nothing here judges. It ranks evidence that was already harvested (`hist_meta.py`) and records which rung a
commit arrived on, so a study can say "T1-T3 only" and mean something precise.
"""
from __future__ import annotations

import argparse, random, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hist_fixlabel import fix_shas  # noqa: E402

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
REPOS = ("commons-lang", "curl", "libgit2", "libxml2", "ndpi", "openssl",
         "postgres", "prometheus", "redis", "ripgrep", "sphinx")
TIERS = ("T1_revert", "T2_fixref", "T3_cve", "T4_keyword", "T5_bareref")


def tiers_for(repo: str, merge_units: bool = False, meta_dir: Path | None = None) -> tuple[dict[str, str], dict]:
    """sha -> tier, plus the pools needed to talk about recall. merge_units / meta_dir are MOD-1 Amendment 3's:
    keep merges where the history made them the unit, and read links from a meta harvest that saw them."""
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{repo}.db'}?mode=ro", uri=True)
    mg = "" if merge_units else " and merge=0"
    allc = {s for s, in h.execute("select sha from commit_ where bot=0" + mg)}
    kw_raw = {s for s, in h.execute("select sha from commit_ where fix=1 and bot=0" + mg)}
    kw = fix_shas(h, "v3c", merge_units) or set()
    h.close()
    link: dict[str, set[str]] = {k: set() for k in ("revert", "issue_fix", "issue", "cve", "trailer")}
    m = (meta_dir or STUDY / "meta") / f"{repo}.db"
    if m.exists():
        c = sqlite3.connect(f"file:{m}?mode=ro", uri=True)
        for sha, kind in c.execute("select sha, kind from link"):
            if sha not in allc:
                continue
            if kind.startswith("trailer:"):
                k = kind.split(":", 1)[1]
                if k in ("reported-by", "closes", "fixes", "bug"):
                    link["trailer"].add(sha)
            elif kind in link:
                link[kind].add(sha)
        c.close()
    out: dict[str, str] = {}
    for sha in allc:
        if sha in link["revert"]:
            out[sha] = "T1_revert"
        elif sha in link["cve"]:
            out[sha] = "T3_cve"
        elif sha in link["issue_fix"]:
            out[sha] = "T2_fixref"
        elif sha in kw:
            out[sha] = "T4_keyword"
        elif sha in link["issue"] or sha in link["trailer"]:
            out[sha] = "T5_bareref"
    return out, {"all": allc, "kw_raw": kw_raw, "kw_v3c": kw}


def cmd_report(a) -> int:
    print(f"{'repo':13}{'commits':>8}" + "".join(f"{t.split('_')[0]:>8}" for t in TIERS)
          + f"{'cascade':>9}{'kw v3c':>8}{'new vs kw':>11}")
    for r in (a.repos.split(",") if a.repos else REPOS):
        try:
            tier, pool = tiers_for(r)
        except Exception as e:
            print(f"{r:13} error: {e}"); continue
        counts = {t: sum(1 for v in tier.values() if v == t) for t in TIERS}
        cascade = set(tier)
        new = cascade - pool["kw_v3c"]
        print(f"{r:13}{len(pool['all']):>8,}" + "".join(f"{counts[t]:>8,}" for t in TIERS)
              + f"{len(cascade):>9,}{len(pool['kw_v3c']):>8,}{len(new):>11,}")
    print("\n`new vs kw` = commits the cascade labels a fix that the v3c keyword gate does NOT -- the recall"
          "\nthe keyword gate was leaving on the floor. Each tier still needs its own precision audit"
          "\n(`--sample Tn --repo R`); until then the cascade is a BROADER label, not yet a better one.")
    return 0


def cmd_sample(a) -> int:
    tier, pool = tiers_for(a.repo)
    want = [s for s, t in tier.items() if t.startswith(a.sample)]
    only_new = [s for s in want if s not in pool["kw_v3c"]]
    use = only_new if a.new_only else want
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{a.repo}.db'}?mode=ro", uri=True)
    subj = dict(h.execute("select sha, subject from commit_"))
    h.close()
    body = {}
    m = STUDY / "meta" / f"{a.repo}.db"
    if m.exists():
        c = sqlite3.connect(f"file:{m}?mode=ro", uri=True)
        body = dict(c.execute("select sha, body from body"))
        c.close()
    rnd = random.Random(a.seed)
    pick = rnd.sample(use, min(a.n, len(use)))
    print(f"\n## {a.repo} — {a.sample}, {len(pick)} of {len(use)}"
          f"{' (only those the keyword gate misses)' if a.new_only else ''}, seed {a.seed}\n")
    print("Judge each: does this commit repair behaviour that was wrong?\n")
    for s in pick:
        b = " / ".join(l.strip() for l in (body.get(s) or "").split("\n") if l.strip())[:200]
        print(f"- [ ] `{s[:10]}` {(subj.get(s) or '')[:110]}")
        if b:
            print(f"       body: {b}")
    return 0


def cmd_emit(a) -> int:
    a.emit.mkdir(parents=True, exist_ok=True)
    for r in (a.repos.split(",") if a.repos else REPOS):
        tier, _ = tiers_for(r)
        db = a.emit / f"{r}.db"
        con = sqlite3.connect(db)
        con.executescript("CREATE TABLE IF NOT EXISTS cascade (sha TEXT PRIMARY KEY, tier TEXT);"
                          "DELETE FROM cascade;")
        con.executemany("INSERT INTO cascade VALUES (?,?)", tier.items())
        con.commit(); con.close()
        print(f"  {r}: {len(tier):,} labelled -> {db}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--sample", help="T1/T2/T3/T4/T5")
    ap.add_argument("--repo", default="curl")
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--seed", type=int, default=2988)
    ap.add_argument("--new-only", action="store_true", help="only commits the keyword gate misses")
    ap.add_argument("--emit", type=Path)
    a = ap.parse_args()
    if a.sample:
        return cmd_sample(a)
    if a.emit:
        return cmd_emit(a)
    return cmd_report(a)


if __name__ == "__main__":
    raise SystemExit(main())
