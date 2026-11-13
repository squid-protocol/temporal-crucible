#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SA3 outcomes: which unit files each label marks, per repo. It reads NO structural predictor.

    python tools/sa3_outcomes.py --repo NAME        # -> <pilot>/sa3_outcomes/NAME.json
    python tools/sa3_outcomes.py --table            # the marginals of every repo built so far

Implements docs/sa3_registration.md as amended (Amendment 1), and nothing else:

  universe   unit files at the rescanned snapshot (repo's language, C and C++ together; not test, vendored,
             doc, example, tutorial or generated; LOC > 0), with the snapshot's .gitattributes applied.
  HP         a commit in the window carrying a fix reference, a CVE id, or a revert of code that existed at
             the cut (rule 3). `HP_allreverts` keeps every revert, as first registered.
  inherit    in a merge-workflow repo a merge inherits the links of the commits it brings in (rule 4): at
             most 50 of them, never a bot's, never the keyword tier, and only for the files the merge's
             first-parent diff shares with the linking commit.
  KW         a keyword-tier commit with no HP link.
  control    the pool the matched control is drawn from: non-bot commits in the window in no fix tier.
  wide       a commit touching >= 10% of the unit files and >= 20 of them is removed from everything.

Body links come from a harvest made for SA3 (`pilot/meta_sa3`, merges included, the wider tracker patterns of
`hist_meta --sa3-links`); fix-semantic trailers count as fix references (`--sa3-tiers`).
"""
from __future__ import annotations

import argparse, json, sqlite3, subprocess, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import laws_units as U  # noqa: E402
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402
from hist_fixlabel import fix_shas  # noqa: E402
from laws_history import BOT  # noqa: E402
from mod1_lift import frame, ro, STUDY, WIDE_SHARE, WIDE_MIN_FILES, MIN_COMPLETE  # noqa: E402

META = STUDY / "meta_sa3"
SCANS = STUDY / "sa3_scans"
OUT = STUDY / "sa3_outcomes"
MAX_BROUGHT = 50           # rule 4: no inheritance from a merge that brings in more commits than this
FLOOR_FILES, FLOOR_COMMITS, MAX_COMMIT_SHARE = 30, 20, 0.25   # rule 6
PY = sys.executable


def harvest_bodies(repo: str) -> None:
    db = META / f"{repo}.db"
    if db.exists():
        try:
            if ro(db).execute("select value from meta where key='done'").fetchone():
                return
        except sqlite3.Error:
            pass
    subprocess.run([PY, "tools/hist_meta.py", "--pool", str(POOL_DIR), "--out", str(META), "--repos", repo,
                    "--with-merges", "--sa3-links"], capture_output=True, text=True, cwd=REPO_ROOT, timeout=7200)


def universe(repo: str, langs: tuple[str, ...]) -> tuple[set[str], dict]:
    side = json.loads((SCANS / f"{repo}.json").read_text())
    ex = U.Excluder(side["attrs"], include_tutorials=True)
    gen = set(side["generated"])

    def unit(p: str) -> bool:
        return U.language_of(p) in langs and ex.why(p, p in gen) is None

    w = ro(SCANS / f"{repo}_master.db")
    root = side["src_root"].rstrip("/") + "/"
    scanned, files = 0, set()
    for path, loc in w.execute("select file_path, total_loc from file_data"):
        p = path[len(root):] if path.startswith(root) else path.lstrip("/")
        if unit(p):
            scanned += 1
            if loc:
                files.add(p)
    w.close()
    tree = subprocess.run(["git", "-C", str(POOL_DIR / repo), "ls-tree", "-r", "--name-only", side["snapshot"]],
                          capture_output=True, text=True, timeout=900).stdout.splitlines()
    tree_units = sum(1 for p in tree if unit(p))
    return files, {"snapshot": side["snapshot"], "engine": side["engine"], "unit_files": len(files),
                   "tree_unit_files": tree_units,
                   "complete": round(scanned / tree_units, 3) if tree_units else 0.0}


def topology(repo: str) -> dict[str, tuple[list[str], int, bool]]:
    """sha -> (parents, commit time, bot-authored) for every commit reachable from HEAD"""
    p = subprocess.run(["git", "-C", str(POOL_DIR / repo), "log", "--format=%H%x00%P%x00%ct%x00%aN <%aE>%x00%cN <%cE>"],
                       capture_output=True, text=True, errors="replace", timeout=3600)
    topo = {}
    for line in p.stdout.splitlines():
        sha, par, ct, au, co = line.split("\x00")
        topo[sha] = (par.split(), int(ct), bool(BOT.search(au) or BOT.search(co)))
    return topo


def brought_by(topo: dict, chain: list[str]) -> tuple[dict[str, list[str]], dict[str, str]]:
    """merge on the chain -> the off-chain commits it brings in; and off-chain commit -> that merge.
    brought(M) = reachable from parents 2..k and not from parent 1; each off-chain commit belongs to the
    EARLIEST chain merge that reaches it (the chain is walked oldest first)."""
    on_chain = set(chain)
    owner: dict[str, str] = {}
    brought: dict[str, list[str]] = {}
    for m in chain:
        pars = topo.get(m, ([], 0, False))[0]
        if len(pars) < 2:
            continue
        mine, stack = [], list(pars[1:])
        while stack:
            c = stack.pop()
            if c in on_chain or c in owner or c not in topo:
                continue
            owner[c] = m
            mine.append(c)
            stack.extend(topo[c][0])
        brought[m] = mine
    return brought, owner


def files_of(repo: str, shas: list[str]) -> dict[str, set[str]]:
    if not shas:
        return {}
    p = subprocess.run(["git", "-C", str(POOL_DIR / repo), "log", "--no-walk=unsorted", "--stdin", "--name-only",
                        "--format=%x01%H"], input="\n".join(shas) + "\n", capture_output=True, text=True,
                       errors="replace", timeout=3600)
    out: dict[str, set[str]] = {}
    for chunk in p.stdout.split("\x01")[1:]:
        lines = chunk.split("\n")
        out[lines[0].strip()] = {x for x in lines[1:] if x.strip()}
    return out


def build(repo: str) -> dict:
    out = {"repo": repo, "status": "ok"}
    if not (SCANS / f"{repo}.json").exists():
        return {**out, "status": "unprepared", "why": "no SA3 rescan"}
    f = frame(repo)
    out.update({k: f[k] for k in ("language", "family", "merge_units", "cut", "end", "window_days", "start_year",
                                  "usable_commits")})
    files, u = universe(repo, f["langs"])
    out.update(u)
    if not u["tree_unit_files"] or u["complete"] < MIN_COMPLETE:
        return {**out, "status": "scan_incomplete",
                "why": f"rescan holds {u['complete']:.0%} of {u['tree_unit_files']} unit files in the tree"}
    harvest_bodies(repo)
    if not (META / f"{repo}.db").exists():
        return {**out, "status": "no_meta", "why": "no SA3 body harvest"}

    h = ro(STUDY / "history" / f"{repo}.db")
    where_c = "c." + f["where"].replace(" and ", " and c.")
    chain = [s for s, in h.execute(f"select sha from commit_ where {f['where']} order by ct")]
    ct_of = dict(h.execute("select sha, ct from commit_"))
    touch: dict[str, set[str]] = defaultdict(set)
    for p, s in h.execute(f"select t.path, t.sha from touch t join commit_ c on c.sha=t.sha where {where_c} "
                          "and c.ct>? and c.ct<=?", (f["cut"], f["end"])):
        if p in files:
            touch[s].add(p)
    kw = fix_shas(h, "v3c", f["merge_units"]) or set()
    h.close()
    window = set(touch)                                   # unit commits in the window that touch the universe
    wide = {s for s, ps in touch.items() if len(ps) >= WIDE_MIN_FILES and len(ps) >= WIDE_SHARE * len(files)}

    # --- links, from the SA3 body harvest
    m = ro(META / f"{repo}.db")
    links: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for sha, kind, value in m.execute("select sha, kind, value from link"):
        if kind in ("revert", "issue_fix", "cve"):
            links[sha].append((kind, value or ""))
        elif kind in ("trailer:fixes", "trailer:bug", "trailer:reported-by"):
            links[sha].append(("issue_fix", value or ""))  # fix-semantic trailers are fix references (--sa3-tiers)
    m.close()

    topo = topology(repo)
    brought, owner = brought_by(topo, chain) if f["merge_units"] else ({}, {})
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for s in topo:
        by_prefix[s[:7]].append(s)

    def resolve(value: str) -> str | None:
        v = value.lower()
        if len(v) < 7:
            return None
        hit = [s for s in by_prefix.get(v[:7], ()) if s.startswith(v)]
        return hit[0] if len(hit) == 1 else None

    def at_or_before_cut(target: str) -> bool:
        """the reverted commit, or the merge that brought it in, existed at the cut"""
        unit = owner.get(target, target)
        t = ct_of.get(unit, topo[target][1])
        return t <= f["cut"]

    def classify(linker: str, exclude: set[str]) -> tuple[set[str], set[str]]:
        """(kinds counted under the primary rule, kinds counted when every revert counts)"""
        strict, loose = set(), set()
        for kind, value in links.get(linker, ()):
            if kind != "revert":
                strict.add(kind); loose.add(kind)
                continue
            loose.add("revert")
            tgt = resolve(value)
            if tgt and tgt not in exclude and at_or_before_cut(tgt):
                strict.add("revert")
        return strict, loose

    # --- qualifying events: (unit commit, kinds strict, kinds loose, positive files)
    events = []
    stats = {"merges_in_window": 0, "merges_over_cap": 0, "inherited_events": 0, "reverts_seen": 0,
             "reverts_of_pre_cut_code": 0, "reverts_unresolved": 0}
    over_cap = []
    for u_sha in window - wide:
        strict, loose = classify(u_sha, set())
        if strict or loose:
            events.append((u_sha, strict, loose, touch[u_sha], "own"))
        kids = brought.get(u_sha)
        if kids is None:
            continue
        stats["merges_in_window"] += 1
        if len(kids) > MAX_BROUGHT:
            stats["merges_over_cap"] += 1
            over_cap.append({"sha": u_sha[:10], "brought": len(kids)})
            continue
        linking = [k for k in kids if k in links and not topo[k][2]]
        if not linking:
            continue
        kid_files = files_of(repo, linking)
        inside = set(kids)
        for k in linking:
            s2, l2 = classify(k, inside)
            pos = touch[u_sha] & kid_files.get(k, set())
            if (s2 or l2) and pos:
                events.append((u_sha, s2, l2, pos, "inherited"))
                stats["inherited_events"] += 1
    for linker, ls in links.items():
        if linker in window or owner.get(linker) in window:
            for kind, value in ls:
                if kind == "revert":
                    stats["reverts_seen"] += 1
                    tgt = resolve(value)
                    if not tgt:
                        stats["reverts_unresolved"] += 1
                    elif at_or_before_cut(tgt):
                        stats["reverts_of_pre_cut_code"] += 1

    def outcome(pick) -> dict:
        per_commit: dict[str, set[str]] = defaultdict(set)
        for u_sha, strict, loose, pos, _ in events:
            if pick(strict, loose):
                per_commit[u_sha] |= pos
        allf = set().union(*per_commit.values()) if per_commit else set()
        big = max((len(v) for v in per_commit.values()), default=0)
        ok = (len(allf) >= FLOOR_FILES and len(files) - len(allf) >= FLOOR_FILES
              and len(per_commit) >= FLOOR_COMMITS and (big / len(allf) if allf else 1) <= MAX_COMMIT_SHARE)
        return {"files": sorted(allf), "n_files": len(allf), "n_commits": len(per_commit),
                "largest_commit_share": round(big / len(allf), 3) if allf else None, "clears_floor": ok,
                "commits": {s: sorted(v) for s, v in per_commit.items()}}

    order = ("revert", "cve", "issue_fix")                 # the cascade's exclusive-tier order
    first = lambda kinds: next((k for k in order if k in kinds), None)  # noqa: E731
    res = {
        "HP": outcome(lambda s, l: bool(s)),
        "HP_allreverts": outcome(lambda s, l: bool(l)),
        "HP_revert": outcome(lambda s, l: first(s) == "revert"),
        "HP_cve": outcome(lambda s, l: first(s) == "cve"),
        "HP_fixref": outcome(lambda s, l: first(s) == "issue_fix"),
    }
    hp_any = {e[0] for e in events}                        # any HP link at all, strict or not, own or inherited
    kw_commits = {s: touch[s] for s in window - wide if s in kw and s not in hp_any}
    kwf = set().union(*kw_commits.values()) if kw_commits else set()
    big = max((len(v) for v in kw_commits.values()), default=0)
    res["KW"] = {"files": sorted(kwf), "n_files": len(kwf), "n_commits": len(kw_commits),
                 "largest_commit_share": round(big / len(kwf), 3) if kwf else None,
                 "clears_floor": len(kwf) >= FLOOR_FILES and len(files) - len(kwf) >= FLOOR_FILES
                 and len(kw_commits) >= FLOOR_COMMITS and (big / len(kwf) if kwf else 1) <= MAX_COMMIT_SHARE}
    pool = {s: sorted(touch[s]) for s in window - wide
            if s not in hp_any and s not in kw and not topo.get(s, ([], 0, False))[2]}
    anyf = set().union(*map(set, pool.values())) if pool else set()
    res["control_pool"] = {"n_commits": len(pool), "n_files_any": len(anyf), "commits": pool}
    out.update({"wide_commits": len(wide), "inheritance": {**stats, "over_cap": over_cap[:20]}, "outcomes": res,
                "in_window_merge_share": round(sum(1 for s in window if len(topo.get(s, ([],))[0]) > 1)
                                               / max(len(window), 1), 3)})
    return out


def table() -> int:
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))]
    print(f"{'repo':<18}{'lang':<8}{'units':>6}{'compl':>6}{'HP files':>9}{'commits':>8}{'top':>6}{'floor':>6}"
          f"{'all-rev':>8}{'KW':>6}{'pool':>7}{'inh':>5}  status")
    for r in rows:
        if r["status"] != "ok":
            print(f"{r['repo']:<18}{r.get('language', ''):<8}{r.get('unit_files', ''):>6}{r.get('complete', ''):>6}"
                  f"{'':>55}  {r['status']}: {r.get('why')}")
            continue
        o = r["outcomes"]; hp = o["HP"]
        print(f"{r['repo']:<18}{r['language']:<8}{r['unit_files']:>6}{r['complete']:>6}{hp['n_files']:>9}"
              f"{hp['n_commits']:>8}{(hp['largest_commit_share'] or 0):>6.2f}{'yes' if hp['clears_floor'] else 'no':>6}"
              f"{o['HP_allreverts']['n_files']:>8}{o['KW']['n_files']:>6}{o['control_pool']['n_commits']:>7}"
              f"{r['inheritance']['inherited_events']:>5}  ok")
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"\nclear the HP floor: {sum(1 for r in ok if r['outcomes']['HP']['clears_floor'])} of {len(ok)} built "
          f"({len(rows) - len(ok)} excluded before the label was read)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--table", action="store_true")
    a = ap.parse_args()
    if a.table:
        return table()
    OUT.mkdir(parents=True, exist_ok=True)
    r = build(a.repo)
    (OUT / f"{a.repo}.json").write_text(json.dumps(r) + "\n")
    hp = r.get("outcomes", {}).get("HP", {})
    print(f"{a.repo}: {r['status']} {r.get('why') or ''} HP files {hp.get('n_files')} from {hp.get('n_commits')} commits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
