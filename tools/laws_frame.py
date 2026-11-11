#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The LAWS sampling frame and the seeded draw (methods review M9; Amendment 3 for the counts).

    python tools/laws_frame.py slices   --language go                       # the created: windows, no API calls
    python tools/laws_frame.py search   --language go --out DIR --confirm   # SPENDS SEARCH QUOTA
    python tools/laws_frame.py draw     --out DIR --language go --n 16      # after the fingerprint is pushed

**Nothing here runs against GitHub without `--confirm`.** The frame fixes the sample of a pre-registered study:
once the candidate file's SHA-256 is pushed and the draw is taken, the sample cannot be quietly rebuilt -- a
mistake needs a dated amendment admitting it. So the search step is gated, and `draw` refuses to run unless the
fingerprint it is drawing from matches one recorded on disk.

M9's rules, implemented:

**Frame.** GitHub search sliced by `created:` month windows with
`stars:>=500 fork:false archived:false language:<L>`; any slice returning the 1,000-result cap is split in half
and re-queried until no slice is truncated. The frame is complete only when no slice is truncated, and the frame
size per language is reported.

**Share.** A candidate needs >= SHARE of its bytes in the language, from the languages API, not the `language:`
filter (which is primary-language only). **JS/TS is JavaScript + TypeScript bytes combined.** C++ counts
linguist "C++" only.

**History** (clone-time checks, `eligible_history`): at least MIN_COMMITS commits on
`git rev-list --first-parent --count` of the default branch; the quarterly rule giving at least MIN_SNAPSHOTS
quarters with at least MIN_FILES source files; and at least one commit in at least QUARTER_COVERAGE of the
quarters from the first eligible quarter to the panel end. "First commit" is the first quarter with MIN_FILES
source files of the language, not the root commit date.

**Draw.** Candidates sorted by `full_name` lower-cased in byte order, then
`random.Random(2982).sample(list, len(list))` -- a full permutation -- and taken in that order until `n` pass the
clone-time checks. A failure after the first law statistic is computed never causes replacement.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

SEED = 2982
CAP = 1000  # GitHub search returns at most this many results per query
SHARE = 0.60
MIN_COMMITS = 2000
MIN_SNAPSHOTS = 20
MIN_FILES = 50
QUARTER_COVERAGE = 0.75
PANEL_END = "2026-10-01"
FRAME_START = "2008-01"  # GitHub's own beginning; no repo was created before it
JSTS = ("JavaScript", "TypeScript")


def month_slices(start: str = FRAME_START, end: str | None = None) -> list[tuple[str, str]]:
    """The `created:` windows, one per month, as (inclusive from, inclusive to) ISO dates."""
    y, m = (int(x) for x in start.split("-"))
    last = dt.date.fromisoformat(end or PANEL_END)
    out = []
    while True:
        first = dt.date(y, m, 1)
        if first > last:
            break
        nxt = dt.date(y + (m == 12), (m % 12) + 1, 1)
        out.append((first.isoformat(), (nxt - dt.timedelta(days=1)).isoformat()))
        y, m = nxt.year, nxt.month
    return out


def split_window(lo: str, hi: str) -> list[tuple[str, str]] | None:
    """A truncated window halved by date. None when it cannot be split further (a single day)."""
    a, b = dt.date.fromisoformat(lo), dt.date.fromisoformat(hi)
    if a >= b:
        return None
    mid = a + (b - a) // 2
    return [(a.isoformat(), mid.isoformat()), ((mid + dt.timedelta(days=1)).isoformat(), b.isoformat())]


def github_languages(language: str) -> tuple[str, ...]:
    """GitHub's own `language:` values for a panel language. The filter is PRIMARY-language only, so JS/TS needs
    two searches whose results are unioned; the >= 60% combined-bytes share is then checked per candidate."""
    return JSTS if language == "jsts" else (LINGUIST[language],)


def query(gh_language: str, lo: str, hi: str) -> str:
    """One window's query. The language value is quoted because `C++` and `C#` do not survive unquoted."""
    return f'stars:>=500 fork:false archived:false language:"{gh_language}" created:{lo}..{hi}'



def frame(language: str, run_search, start: str = FRAME_START, end: str | None = None) -> dict:
    """Every candidate for one language. `run_search(q) -> (total_count, [full_name, ...])` is injected so the
    slicing logic is testable without the API. A window at the cap is split and re-queried; the frame is
    complete only when no window is truncated. A language with several GitHub `language:` values (JS/TS) is the
    union of their searches."""
    ghls = github_languages(language)
    todo = [(lo, hi, g) for g in ghls for lo, hi in month_slices(start, end)]
    names: set[str] = set()
    windows, truncated, calls = [], [], 0
    while todo:
        lo, hi, ghl = todo.pop(0)
        total, got = run_search(query(ghl, lo, hi))
        calls += 1
        if total > CAP:
            parts = split_window(lo, hi)
            if parts is None:
                truncated.append({"from": lo, "to": hi, "lang": ghl, "total": total})  # a single day over the cap
                names.update(got)
                windows.append({"from": lo, "to": hi, "lang": ghl, "total": total, "returned": len(got),
                                "truncated": True})
                continue
            todo = [(a, b, ghl) for a, b in parts] + todo
            continue
        names.update(got)
        windows.append({"from": lo, "to": hi, "lang": ghl, "total": total, "returned": len(got),
                        "truncated": False})
    return {"language": language, "github_languages": list(ghls),
            "candidates": sorted(names), "frame_size": len(names),
            "windows": len(windows), "search_calls": calls, "truncated_windows": truncated,
            "complete": not truncated}


CORE_FLOOR = 1500  # leave this much core quota for churn and the shepherd, which share the same 5,000/hour
SEARCH_PER_PAGE = 100


def _gh(path: str) -> dict:
    """One authenticated GitHub REST call through the gh CLI."""
    p = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", path],
                       capture_output=True, text=True)
    if p.returncode or not p.stdout.strip():
        raise RuntimeError(f"gh api {path[:80]} failed: {p.stderr[:200]}")
    return json.loads(p.stdout)


def quota() -> dict:
    r = _gh("rate_limit")["resources"]
    return {"core": r["core"]["remaining"], "core_reset": r["core"]["reset"],
            "search": r["search"]["remaining"], "search_reset": r["search"]["reset"]}


def _wait_for(kind: str, need: int = 1) -> None:
    """Block until `kind` quota allows `need` more calls. Search is 30/minute, so this is usually seconds."""
    while True:
        q = quota()
        if q[kind] >= need:
            return
        sleep = max(2, q[f"{kind}_reset"] - int(time.time()) + 2)
        print(f"  {kind} quota exhausted; sleeping {sleep}s", flush=True)
        time.sleep(min(sleep, 120))


def search_runner(cache: Path):
    """A `run_search(q) -> (total_count, [full_name, ...])` for `frame()`, cached per query and paced.

    Every page of a window is fetched, because the frame needs the NAMES, not just the count -- a window with
    400 results costs four search calls. Each query's result is cached on disk, so a run that stops on quota (or
    on `--max-minutes`) resumes without re-spending it."""
    cache.mkdir(parents=True, exist_ok=True)

    def run(q: str):
        key = cache / (hashlib.sha256(q.encode()).hexdigest()[:24] + ".json")
        if key.exists():
            rec = json.loads(key.read_text())
            return rec["total"], rec["names"]
        names: list[str] = []
        total = None
        page = 1
        while True:
            _wait_for("search")
            enc = urllib.parse.quote(q)
            rec = _gh(f"search/repositories?q={enc}&per_page={SEARCH_PER_PAGE}&page={page}")
            total = rec["total_count"] if total is None else total
            names.extend(i["full_name"] for i in rec.get("items", ()))
            if len(names) >= min(total, CAP) or not rec.get("items"):
                break
            page += 1
        key.write_text(json.dumps({"query": q, "total": total, "names": names}) + "\n")
        return total, names

    return run


def language_bytes(full_name: str, cache: Path) -> dict[str, int]:
    """The languages API for one repo, cached. This is the step that spends core quota in bulk."""
    cache.mkdir(parents=True, exist_ok=True)
    key = cache / (full_name.replace("/", "__") + ".json")
    if key.exists():
        return json.loads(key.read_text())
    _wait_for("core", CORE_FLOOR + 1)
    rec = _gh(f"repos/{full_name}/languages")
    key.write_text(json.dumps(rec) + "\n")
    return rec


def language_share(bytes_by_language: dict[str, int], language: str) -> float:
    """The share of a repo's bytes in the panel language. JS/TS is JavaScript + TypeScript combined (M9)."""
    total = sum(bytes_by_language.values())
    if not total:
        return 0.0
    keys = JSTS if language == "jsts" else (LINGUIST.get(language, language),)
    return sum(bytes_by_language.get(k, 0) for k in keys) / total


LINGUIST = {"c": "C", "cpp": "C++", "csharp": "C#", "go": "Go", "java": "Java", "kotlin": "Kotlin",
            "php": "PHP", "python": "Python", "rust": "Rust"}


def sorted_candidates(names) -> list[str]:
    """M9's order: `full_name` lower-cased, byte order. The draw is defined on this order, so it is the one
    thing in the frame that must never change."""
    return sorted({n.lower() for n in names})


def permutation(names, seed: int = SEED) -> list[str]:
    """M9's draw order: a full permutation of the sorted candidates by `random.Random(seed).sample`."""
    ordered = sorted_candidates(names)
    return random.Random(seed).sample(ordered, len(ordered))


def fingerprint(path: Path) -> str:
    """The SHA-256 of the candidate file, which M9 requires be committed and pushed BEFORE the draw."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shortlist(language: str, candidates: list[str], cache: Path, want: int, buffer: float = 2.5,
              limit: int | None = None) -> dict:
    """Walk the draw permutation and keep candidates that pass the >= SHARE language check, stopping once
    `want * buffer` have passed -- or at `limit` checks, or at the core-quota floor.

    This is where M9 puts eligibility: "taking eligible repos in that order until N pass the clone-time checks".
    Checking the whole frame instead would be 81,060 languages-API calls for a list the draw never reaches the
    end of. The buffer exists because the history checks, which need a clone, will reject some of these too; the
    order is the permutation's, so a later clone-time rejection is replaced by the next candidate in it and
    never by a re-draw."""
    order = permutation(candidates)
    target = int(want * buffer)
    passed, checked, rejected = [], 0, []
    stopped = None
    for name in order:
        if len(passed) >= target:
            stopped = f"{target} candidates passed the share check ({want} wanted x {buffer} buffer)"
            break
        if limit is not None and checked >= limit:
            stopped = f"--limit {limit} checks reached"
            break
        if quota()["core"] <= CORE_FLOOR:
            stopped = f"core quota floor ({CORE_FLOOR}) reached"
            break
        share = language_share(language_bytes(name, cache), language)
        checked += 1
        (passed if share >= SHARE else rejected).append({"repo": name, "share": round(share, 4)})
    return {"language": language, "order_len": len(order), "checked": checked,
            "passed": passed, "passed_count": len(passed),
            "rejected_count": len(rejected), "rejected_sample": rejected[:10],
            "pass_rate": round(len(passed) / checked, 4) if checked else None,
            "want": want, "buffer": buffer, "stopped": stopped, "share_bar": SHARE}


def eligible_history(repo: Path, language: str, snapshots_fn=None) -> dict:
    """The clone-time history checks. `snapshots_fn(repo, language) -> (quarters_with_files, quarters_total,
    quarters_with_commit)` is injected so the rules are testable without a clone."""
    out: dict = {"eligible": False}
    p = subprocess.run(["git", "-C", str(repo), "rev-list", "--first-parent", "--count", "HEAD"],
                       capture_output=True, text=True)
    commits = int(p.stdout.strip() or 0)
    out["first_parent_commits"] = commits
    if commits < MIN_COMMITS:
        return {**out, "why": f"fewer than {MIN_COMMITS} first-parent commits ({commits})"}
    if snapshots_fn is None:
        return {**out, "why": "the quarterly rule needs a scan; run it at clone time"}
    with_files, total, with_commit = snapshots_fn(repo, language)
    out.update(snapshots_with_files=with_files, quarters=total, quarters_with_commit=with_commit)
    if with_files < MIN_SNAPSHOTS:
        return {**out, "why": f"fewer than {MIN_SNAPSHOTS} quarters with {MIN_FILES} source files ({with_files})"}
    cover = with_commit / total if total else 0.0
    out["quarter_coverage"] = round(cover, 4)
    if cover < QUARTER_COVERAGE:
        return {**out, "why": f"a commit in only {cover:.0%} of quarters, under {QUARTER_COVERAGE:.0%}"}
    return {**out, "eligible": True}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("slices", "search", "draw"))
    ap.add_argument("--language")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--confirm", action="store_true", help="required for `search`: it spends GitHub search quota")
    ap.add_argument("--eligible", type=Path, default=Path("docs/laws_panel"),
                    help="draw only: the committed POST-EXCLUSION eligible list (Amendment 9 item 3)")
    ap.add_argument("--record", type=Path, help="draw only: write the draw record here")
    ap.add_argument("--no-share", action="store_true",
                    help="search only: skip the per-candidate languages API, which is what spends core quota")
    a = ap.parse_args()
    if a.step == "slices":
        w = month_slices()
        print(f"{len(w)} monthly windows, {w[0][0]} to {w[-1][1]}; the query per window is:")
        for g in (github_languages(a.language) if a.language else ("<L>",)):
            print(f"  {query(g, w[0][0], w[0][1])}")
        print("no API call was made")
        return 0
    if a.step == "search":
        if not a.confirm:
            print("refusing to search without --confirm: this fixes the sample of a pre-registered study,\n"
                  "spends search quota, and a mistake afterwards needs a dated amendment. Re-run with --confirm.")
            return 1
        if not (a.language and a.out):
            print("--language and --out are required")
            return 1
        d = a.out / "frame"
        d.mkdir(parents=True, exist_ok=True)
        print(f"quota before: {quota()}")
        rec = frame(a.language, search_runner(d / "search_cache"))
        rec.update(share=SHARE, share_phase=(
            "not run here, by design: M9 evaluates eligibility LAZILY in draw order, 'taking eligible repos in "
            "that order until N pass the clone-time checks'. Walking all 81,060 candidates across the ten "
            "languages would be about 16 hours of core quota for a list the draw never reaches the end of. The "
            "frame size is a CEILING on eligibility; `shortlist` does the checking, in order, and stops."))
        f = d / f"{a.language}.json"
        f.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
        print(f"{a.language}: frame {rec['frame_size']} candidates from {rec['windows']} windows "
              f"({rec['search_calls']} search calls); complete={rec['complete']}; "
              f"share-checked {checked}, eligible {len(eligible)} -> {f}")
        print(f"quota after: {quota()}")
        print("the candidate file's SHA-256 must be committed and pushed BEFORE any draw:")
        print(f"  {fingerprint(f)}")
        return 0
    # The draw samples the POST-EXCLUSION eligible list, not the raw frame. Amendment 8 item 1 found
    # that the registered PANEL exclusion was implemented nowhere, and that every excluded repo still
    # sat in the raw search output; drawing "uniformly at random from the eligible list" against the
    # unfiltered file would have selected excluded repos and the guard would have failed silently at
    # the one step it exists to protect. tools/laws_exclude.py produces the eligible list and its
    # fingerprint; both are committed under docs/laws_panel (Amendment 9 item 3).
    f = a.eligible / f"{a.language}_eligible.json"
    if not f.exists():
        print(f"{f} does not exist: run tools/laws_exclude.py to apply the registered exclusion first")
        return 1
    sums = a.eligible / "SHA256SUMS"
    if not sums.exists():
        print(f"refusing to draw: {sums} is missing. M9 requires the candidate file's SHA-256 to be "
              "committed and pushed BEFORE the draw.")
        return 1
    want = {ln.split()[1]: ln.split()[0] for ln in sums.read_text().split("\n") if ln.strip()}
    if want.get(f.name) != fingerprint(f):
        print(f"refusing to draw: {f.name} does not match its committed SHA-256 in SHA256SUMS.")
        return 1
    rec = json.loads(f.read_text())
    cands = rec["candidates"]
    order = permutation(cands)
    print(f"{a.language}: {len(order)} eligible candidates ({rec['n_removed']} removed by the registered "
          f"exclusion), file sha {fingerprint(f)[:12]}, list sha {rec['fingerprint_sha256'][:12]}, "
          f"seed {SEED}; first {a.n} in draw order:")
    for i, name in enumerate(order[:a.n], 1):
        print(f"  {i:3d} {name}")
    print("these are the repos to run the clone-time checks against, in this order")
    if a.record:
        a.record.parent.mkdir(parents=True, exist_ok=True)
        a.record.write_text(json.dumps(
            {"language": a.language, "seed": SEED, "n_printed": a.n,
             "eligible_file": str(f.name), "eligible_file_sha256": fingerprint(f),
             "eligible_list_sha256": rec["fingerprint_sha256"],
             "n_eligible": len(cands), "n_removed_by_exclusion": rec["n_removed"],
             "draw_order_head": order[:max(a.n, 40)],
             "order_definition": "random.Random(2982).sample over the lower-cased, de-duplicated, "
                                 "byte-sorted eligible candidates (M9)",
             "note": "the clone-time checks are walked in this order; a candidate that fails one is "
                     "replaced by the next in the order, never by a re-draw"}, indent=1) + "\n")
        print(f"draw record -> {a.record}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
