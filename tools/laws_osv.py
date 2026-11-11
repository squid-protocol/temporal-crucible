#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-9's labels and fix sizes (docs/laws_hypotheses.md LAW-9; methods review M6 item 6). No statistic is
computed here: tools/laws_security.py reads what this writes.

    python tools/laws_osv.py --repo NAME --language c --out DIR     -> DIR/osv/NAME.json

The CVE class. OSV is the label (laws_history.py's docstring: "OSV advisories (the latent class)"). A commit is a
CVE fix when an OSV advisory names it as fixed, by either signal:
  `git-range`  an affected range of `type: GIT` whose `repo` is one of the repo's registered URLs has the commit
               in a `fixed` event. This is the primary signal.
  `reference`  a reference of type FIX (or ADVISORY) whose URL is a commit URL on one of those hosts/paths.
Both are recorded per commit, so an audit can read the law off the primary signal alone.

Repo URLs (ALIASES). One repo appears in OSV under several URLs: libxml2 under gitlab.gnome.org/GNOME/libxml2,
the same path lowercased, with and without `.git`, and under its github.com/gnome mirror; redis also under its
historical github.com/antirez path. URL spelling must not change a count, so the alias set of a panel repo is
registered here, in the scorer, before any LAW-9 statistic. Aliasing is safe because every claimed SHA must also
be an ancestor of the pinned head (`on_branch`): a fork's or a sibling project's commit is dropped there.

The comparison set. `cve` = the advisory-labelled commits of the history walk. `other` = the walk's keyword fix
commits (laws_history.py's `fix = 1`) that are not advisory-labelled. A CVE fix whose message carries no fix
keyword is still a CVE fix: the advisory is the label, not the message.

Fix size, per commit, over unit source files only (methods review M3: never tests, vendored, generated, docs or
examples, and only the repo's language):
  `files`      unit source files touched,
  `functions`  distinct (file, enclosing function) pairs over the hunks of `git diff -U0`, taken from git's own
               funcname section headings -- git's language-aware heuristic, not a parse. Hunks with no heading
               (top-level edits) are counted once per file as "", so a header-only change is one "function".
  `lines`      added plus removed lines in those files (`--numstat`).
No 50-file cap is applied (xc_harvest.py's cap truncates the other-fix distribution, methods review M6 item 6);
`files_over_50` records the share each class would lose under that cap, so the two are comparable.

The OSV dumps are the per-ecosystem `all.zip` of osv-vulnerabilities.storage.googleapis.com, cached under
~/.cache/temporal-crucible/osv-<stamp>/ with a sha256 beside each, pinned and deliberately not committed (the
third-party rule, as for the linguist lists). `GIT` is the ecosystem-less bucket and carries the C and C++ repos;
a language's package ecosystem is added with --ecosystem.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import laws_security as S  # noqa: E402  (for the registered MIN_CVE: one source of truth)
import laws_units as U  # noqa: E402
from _engine import POOL_DIR  # noqa: E402

BUCKET = "https://osv-vulnerabilities.storage.googleapis.com"
CACHE = Path.home() / ".cache" / "temporal-crucible"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
# a commit URL on a forge: github/gitlab /commit/<sha>, cgit/gitweb ?id=/h=<sha>, gitweb ;a=commit;h=<sha>
COMMIT_URL = re.compile(r"(?:/commits?/|[?;&](?:id|h)=)([0-9a-f]{7,40})\b")
FIX_REF = ("FIX", "ADVISORY")
FILE_CAP = 50
# Registered URL alias sets. A key is the repo's directory name under the pool; values are normalised URLs.
ALIASES: dict[str, tuple[str, ...]] = {
    "libxml2": ("gitlab.gnome.org/gnome/libxml2", "github.com/gnome/libxml2"),
    "redis": ("github.com/redis/redis", "github.com/antirez/redis"),
    "libgit2": ("github.com/libgit2/libgit2",),
    "postgres": ("github.com/postgres/postgres", "git.postgresql.org/postgresql", "git.postgresql.org/pgsql"),
    "postgresql": ("github.com/postgres/postgres", "git.postgresql.org/postgresql", "git.postgresql.org/pgsql"),
    "prometheus": ("github.com/prometheus/prometheus",),
    "commons-lang": ("github.com/apache/commons-lang",),
    "sphinx": ("github.com/sphinx-doc/sphinx",),
    "ripgrep": ("github.com/burntsushi/ripgrep",),
}


def normalise_url(url: str) -> str:
    """A forge URL as host/path, lowercased, without scheme, userinfo, `.git` or a trailing slash."""
    u = re.sub(r"^[a-z+]+://", "", url.strip().lower())
    u = re.sub(r"^git@([^:/]+):", r"\1/", u)
    u = u.split("#")[0].split("?")[0].rstrip("/")
    u = re.sub(r"^[^@/]*@", "", u, count=1) if "@" in u.split("/")[0] else u
    return u[:-4] if u.endswith(".git") else u


def repo_urls(name: str, extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    urls = ALIASES.get(name.lower(), ())
    if not urls and not extra:
        raise SystemExit(f"{name}: no registered OSV URL alias set; add it to laws_osv.ALIASES before labelling")
    return tuple(dict.fromkeys([*urls, *(normalise_url(u) for u in extra)]))


def fetch_dump(ecosystem: str, stamp: str, offline: bool = False, bucket: str = BUCKET) -> Path:
    """The cached `all.zip` of one OSV ecosystem, with its sha256 beside it."""
    d = CACHE / f"osv-{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    z = d / f"{ecosystem.replace('/', '_')}.zip"
    if not z.exists():
        if offline:
            raise SystemExit(f"{z} is not cached and --offline was given")
        url = f"{bucket}/{urllib.parse.quote(ecosystem)}/all.zip"
        with urllib.request.urlopen(url, timeout=600) as r, open(z, "wb") as f:  # noqa: S310
            while chunk := r.read(1 << 20):
                f.write(chunk)
    digest = z.with_suffix(".sha256")
    if not digest.exists():
        h = hashlib.sha256()
        with open(z, "rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
        digest.write_text(f"{h.hexdigest()}  {z.name}\n")
    return z


def labels(dumps: list[Path], urls: tuple[str, ...]) -> dict[str, dict]:
    """{sha: {"advisories": [id, ...], "signals": [...]}} for every commit an advisory names as fixed."""
    want = set(urls)
    found: dict[str, dict] = {}

    def add(sha: str, advisory: str, signal: str) -> None:
        rec = found.setdefault(sha.lower(), {"advisories": [], "signals": []})
        if advisory not in rec["advisories"]:
            rec["advisories"].append(advisory)
        if signal not in rec["signals"]:
            rec["signals"].append(signal)

    for path in dumps:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(".json"):
                    continue
                raw = z.read(name)
                if not any(u.encode() in raw.lower() for u in want):
                    continue  # cheap reject: the record never mentions a registered host/path
                rec = json.loads(raw)
                rid = rec.get("id")
                if not rid or rec.get("withdrawn"):
                    continue
                for aff in rec.get("affected", []):
                    for rng in aff.get("ranges", []):
                        if rng.get("type") != "GIT" or normalise_url(rng.get("repo", "")) not in want:
                            continue
                        for ev in rng.get("events", []):
                            if SHA_RE.match(str(ev.get("fixed", "")).lower()):
                                add(ev["fixed"], rid, "git-range")
                for ref in rec.get("references", []):
                    if ref.get("type") not in FIX_REF:
                        continue
                    url = normalise_url(ref.get("url", ""))
                    if not any(url.startswith(u) for u in want):
                        continue
                    if m := COMMIT_URL.search(ref.get("url", "").lower()):
                        add(m.group(1), rid, "reference")
    return found


def _git(repo: Path, *args: str) -> str:
    """git stdout, decoded with replacement: a diff is bytes, not text, and plenty of them are not UTF-8."""
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    return p.stdout.decode("utf-8", "replace")


def mainline(repo: Path, sha: str) -> str | None:
    """The oldest commit of HEAD's first-parent chain that has `sha` as an ancestor: the merge (or the commit
    itself) that brought `sha` onto the default branch. Where the walk is the first-parent chain, that merge is
    the walk unit a fix inside a merged branch belongs to."""
    out = _git(repo, "rev-list", "--first-parent", "--ancestry-path", f"{sha}..HEAD").split()
    return out[-1] if out else None


CHERRY = re.compile(r"cherry[ -]?picked from commit ([0-9a-f]{7,40})", re.I)
SEP = "\x1e"


def cherry_picks(repo: Path) -> dict[str, str]:
    """{cited sha: the commit on HEAD that cites it}, from `cherry picked from commit X` trailers, in one pass.
    A repo that maintains release branches has OSV name the release-branch commit; the default branch carries a
    cherry-pick of it under a different sha, and without this the fix is invisible to the walk."""
    out: dict[str, str] = {}
    log = _git(repo, "log", "--format=%x1e%H%x00%B", "HEAD")
    for chunk in log.split(SEP)[1:]:
        sha, _, body = chunk.partition("\x00")
        for cited in CHERRY.findall(body):
            out.setdefault(cited.lower(), sha.strip())
    return out


def resolve(repo: Path, shas: list[str]) -> dict[str, str | None]:
    """Each claimed sha mapped to its full sha when it is an ancestor of HEAD, else None (a fork's or a release
    branch's commit, or an abbreviation that no longer resolves)."""
    out: dict[str, str | None] = {}
    for sha in shas:
        p = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
                           capture_output=True, text=True)
        full = p.stdout.strip()
        if not full:
            out[sha] = None
            continue
        anc = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", full, "HEAD"],
                             capture_output=True)
        out[sha] = full if anc.returncode == 0 else None
    return out


def _unit_paths(changed: list[tuple[str, str]], language: str, ex: U.Excluder) -> set[str]:
    return {p for _, p in changed if U.language_of(p) == language and ex.why(p) is None}


def fix_size(repo: Path, sha: str, language: str, ex: U.Excluder) -> dict:
    """files / functions / lines of one commit over its unit source files (see the module docstring)."""
    numstat = _git(repo, "-c", "diff.renameLimit=0", "show", "--numstat", "--format=", "-M", "--first-parent", sha)
    changed, lines = [], 0
    for row in numstat.splitlines():
        parts = row.split("\t")
        if len(parts) != 3:
            continue
        add, rem, path = parts
        path = path.split(" => ")[-1].rstrip("}") if " => " in path else path
        changed.append((row, path))
    units = _unit_paths(changed, language, ex)
    for row, path in changed:
        add, rem, _ = row.split("\t")
        if path in units and add != "-":  # "-" is a binary file
            lines += int(add) + int(rem)
    if not units:
        return {"files": 0, "functions": 0, "lines": 0, "hunks": 0}
    diff = _git(repo, "-c", "diff.renameLimit=0", "show", "-U0", "--format=", "-M", "--first-parent", sha,
                "--", *sorted(units))
    funcs, hunks, path = set(), 0, ""
    for row in diff.splitlines():
        if row.startswith("+++ b/"):
            path = row[6:]
        elif row.startswith("@@"):
            hunks += 1
            head = row.split("@@", 2)[2].strip() if row.count("@@") >= 2 else ""
            funcs.add((path, head))
    return {"files": len(units), "functions": len(funcs), "lines": lines, "hunks": hunks}


def harvest(repo: Path, language: str, history: Path, dumps: list[Path], urls: tuple[str, ...],
            all_sizes: bool = False) -> dict:
    """The LAW-9 record of one repo: every fix commit of the walk with its class and its size.

    Sizes are measured only when the repo clears the registered MIN_CVE bar, because no LAW-9 statistic is read
    for a repo below it and the measurement is two git invocations per fix commit (postgres: 16,980 of them).
    `all_sizes` measures them anyway."""
    con = sqlite3.connect(f"file:{history}?mode=ro", uri=True)
    walk = {sha: ct for sha, ct in con.execute("SELECT sha, ct FROM commit_")}
    keyword_fixes = {sha for (sha,) in con.execute("SELECT sha FROM commit_ WHERE fix = 1")}
    head = dict(con.execute("SELECT key, value FROM meta")).get("head")
    con.close()
    claimed = labels(dumps, urls)
    seen = resolve(repo, sorted(claimed))
    picks = cherry_picks(repo)
    picks12 = {k[:12]: v for k, v in picks.items()}
    cve: dict[str, dict] = {}
    routes: collections.Counter = collections.Counter()
    for sha, rec in claimed.items():
        full = seen.get(sha)
        unit = route = None
        if full and full in walk:
            unit, route = full, "direct"                      # the advisory names a walk unit outright
        elif full:
            m = mainline(repo, full)
            if m and m in walk:
                unit, route = m, "merge-attributed"           # a fix inside a merged branch: its merge is the unit
        if unit is None:                                      # off the branch: look for a cherry-pick of it
            cand = picks.get(sha) or picks12.get(sha[:12]) or (picks.get(full) if full else None)
            if cand and cand in walk:
                unit, route = cand, "cherry-pick"
        if unit is None:
            routes["unattributed"] += 1
            continue
        routes[route] += 1
        cve.setdefault(unit, {"advisories": [], "signals": [], "routes": []})
        cve[unit]["advisories"] = sorted(set(cve[unit]["advisories"]) | set(rec["advisories"]))
        cve[unit]["signals"] = sorted(set(cve[unit]["signals"]) | set(rec["signals"]))
        cve[unit]["routes"] = sorted(set(cve[unit]["routes"]) | {route})
    ex = U.Excluder()
    shas = sorted(set(cve) | keyword_fixes, key=lambda s: walk[s])
    sized = all_sizes or len(cve) >= S.MIN_CVE
    commits = []
    for sha in shas:
        size = fix_size(repo, sha, language, ex) if sized else {}
        commits.append({"sha": sha, "ct": walk[sha], "cve": sha in cve,
                        "advisories": cve.get(sha, {}).get("advisories", []),
                        "signals": cve.get(sha, {}).get("signals", []),
                        "routes": cve.get(sha, {}).get("routes", []), **size})
    # a fix with no unit source file has no size to compare
    kept = [c for c in commits if c.get("files", 0) > 0] if sized else []
    n_cve = sum(c["cve"] for c in kept)
    gate = None if sized else (f"sizes not measured: {len(cve)} advisory-labelled fix commits is below the "
                               f"registered MIN_CVE of {S.MIN_CVE}, so no LAW-9 statistic is read for this repo")
    return {"repo": repo.name, "language": language, "head": head, "urls": list(urls),
            "claimed_shas": len(claimed), "resolved_shas": sum(v is not None for v in seen.values()),
            "on_branch_in_walk": len(cve), "advisories": sorted({a for r in cve.values() for a in r["advisories"]}),
            "git_range_only": sum(1 for r in cve.values() if r["signals"] == ["git-range"]),
            "reference_only": sum(1 for r in cve.values() if r["signals"] == ["reference"]),
            "commits": kept, "n_cve": n_cve, "n_other": len(kept) - n_cve, "sized": sized, "not_sized_why": gate,
            "labelled_fix_commits": len(cve), "keyword_fix_commits": len(keyword_fixes),
            "attribution": dict(routes), "cherry_pick_trailers": len(picks),
            "dropped_no_unit_file": len(commits) - len(kept),
            "files_over_50": {k: round(sum(c["files"] > FILE_CAP for c in kept if c["cve"] is (k == "cve"))
                                       / max(1, sum(c["cve"] is (k == "cve") for c in kept)), 4)
                              for k in ("cve", "other")},
            "dumps": [p.name for p in dumps]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="a clone under the pool, or a path")
    ap.add_argument("--language", required=True, choices=sorted(U.EXTS))
    ap.add_argument("--out", type=Path, required=True, help="the study directory (its history/ is read)")
    ap.add_argument("--ecosystem", default="GIT", help="comma-separated OSV ecosystems; GIT is the ecosystem-less bucket")
    ap.add_argument("--stamp", required=True, help="the dump pin, e.g. 20261110: names the cache directory")
    ap.add_argument("--url", action="append", default=[], help="an extra repo URL beside the registered aliases")
    ap.add_argument("--offline", action="store_true", help="use only the cached dumps")
    ap.add_argument("--all-sizes", action="store_true", help="measure fix sizes even below MIN_CVE")
    a = ap.parse_args()
    repo = Path(a.repo) if Path(a.repo).is_dir() else POOL_DIR / a.repo
    dumps = [fetch_dump(e.strip(), a.stamp, a.offline) for e in a.ecosystem.split(",") if e.strip()]
    rec = harvest(repo, a.language, a.out / "history" / f"{repo.name}.db", dumps,
                  repo_urls(repo.name, tuple(a.url)), a.all_sizes)
    out = a.out / "osv" / f"{repo.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    if not rec["sized"]:
        print(f"{rec['repo']}: {rec['labelled_fix_commits']} CVE fixes ({rec['claimed_shas']} claimed, "
              f"{rec['resolved_shas']} resolved); {rec['not_sized_why']} -> {out}")
        return 0
    print(f"{rec['repo']}: {rec['n_cve']} CVE fixes and {rec['n_other']} other fixes "
          f"({rec['claimed_shas']} claimed, {rec['resolved_shas']} resolved, {rec['on_branch_in_walk']} on the walk; "
          f"{len(rec['advisories'])} advisories) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
