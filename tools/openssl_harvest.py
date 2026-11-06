#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Repo #3 harvest: openssl security fixes (tc#26), fixed side only.

Sources, in order of authority:
  1. openssl's own CVE records (github.com/openssl/release-metadata, secjson/CVE-*.json,
     CVE JSON 5): the commit URLs in `references` name the fix commit(s), one per
     release branch.
  2. For a record that names no usable commit: master commits whose message cites
     the CVE id (the survey's commit-trail, docs/repo3_survey.md §4). A commit that
     only documents the CVE (CHANGES/NEWS) is followed one hop to the code commits of
     the PR it cites ("pull/NNNNN" -> "Merged from .../pull/NNNNN").

Every candidate SHA is VERIFIED BY ITS DIFF, not by existence (the version-proxy
lesson): it must exist, not be a merge, touch >= 1 source file outside doc/test/
fuzz-corpora/CHANGES/NEWS, and not be a release or version bump. Rejected SHAs are
kept in the output with the reason.

Events:
  security-fix -- every verified fix commit on origin/master (mainline). A CVE fixed
                  only on release branches yields its newest branch's commit, flagged
                  on_master=false (usable for delta analyses, not for master snapshots).
  control      -- one size-matched non-event commit per fix (event_harvest's rule,
                  openssl's doc/test prefixes).
No `introduced` class: openssl publishes no introducing commits (accepted gap, tc#26).

CWE: the record's own problemTypes, else NVD 2.0 (cached under dbs/nvd_cache/,
rate-limited to the keyless 5 requests / 30 s).

    python tools/openssl_harvest.py --metadata <pool>/openssl-release-metadata
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DBS_DIR, EVENTS_DIR, POOL_DIR  # noqa: E402

NON_CODE_PREFIXES = ("doc/", "test/", "fuzz/corpora/", ".github/", "demos/", "CHANGES", "NEWS", "README",
                     "VERSION", "util/perl/OpenSSL/Test")
VERSION_FILES = ("VERSION.dat", "include/openssl/opensslv.h", "include/openssl/opensslv.h.in", "crypto/opensslv.h",
                 "openssl.spec", "Makefile", "Makefile.org", "README", "NEWS", "CHANGES", "CHANGES.md", "NEWS.md")
SHA_RE = re.compile(r"(?<![0-9a-f])([0-9a-f]{40})(?![0-9a-f])")
NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={}"
MASTER = "origin/master"


def _git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=check, errors="replace")


def is_code(path: str) -> bool:
    return not path.startswith(NON_CODE_PREFIXES) and not path.endswith((".md", ".pod", ".txt"))


def diff_stat(repo, sha):
    """(code_files, code_churn, all_paths) or None for a merge / missing commit."""
    if _git(repo, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode:
        return None
    parents = _git(repo, "rev-list", "--parents", "-n", "1", sha).stdout.split()
    if len(parents) != 2:
        return None
    files = churn = 0
    paths = []
    for line in _git(repo, "diff", "--numstat", f"{sha}^..{sha}", check=False).stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add, rm, path = parts
        paths.append(path)
        if not is_code(path):
            continue
        files += 1
        churn += (int(add) if add.isdigit() else 0) + (int(rm) if rm.isdigit() else 0)
    return files, churn, paths


def verify(repo, sha) -> tuple[bool, str, dict]:
    st = diff_stat(repo, sha)
    if st is None:
        return False, "missing or merge commit", {}
    files, churn, paths = st
    subject = _git(repo, "log", "-1", "--format=%s", sha).stdout.strip()
    info = {"code_files": files, "code_churn": churn, "subject": subject[:120]}
    if re.match(r"(?i)(prepare for|release|bump version|update version)", subject) or \
            (paths and all(p.endswith(VERSION_FILES) or not is_code(p) for p in paths) and files <= 1
             and any(p.endswith(VERSION_FILES) for p in paths)):
        return False, "release / version bump", info
    if files == 0:
        return False, "no source file outside doc/test/changelogs", info
    return True, "ok", info


def on_master(repo, sha) -> bool:
    return _git(repo, "merge-base", "--is-ancestor", sha, MASTER, check=False).returncode == 0


def _files(repo, sha) -> set[str]:
    return set(_git(repo, "diff", "--name-only", f"{sha}^..{sha}", check=False).stdout.split())


def _patch_id(repo, sha) -> str | None:
    diff = _git(repo, "show", "--format=", sha, check=False).stdout
    r = subprocess.run(["git", "-C", str(repo), "patch-id", "--stable"], input=diff, capture_output=True, text=True)
    return r.stdout.split()[0] if r.stdout.strip() else None


def master_equivalent(repo, sha) -> tuple[str | None, str | None]:
    """openssl's records name the release-branch commits only; the master fix is a separate
    cherry-pick. Find it: a `cherry picked from` trailer, else a same-subject, same-author
    master commit within 90 days with an identical patch-id (or >= 50% shared files)."""
    body = _git(repo, "log", "-1", "--format=%B", sha).stdout
    for x in re.findall(r"cherry picked from commit ([0-9a-f]{40})", body):
        if on_master(repo, x):
            return x, "cherry-pick trailer"
    subj, author, ct = _git(repo, "log", "-1", "--format=%s%x00%ae%x00%ct", sha).stdout.strip().split("\x00")
    lo, hi = int(ct) - 90 * 86400, int(ct) + 90 * 86400
    rows = _git(repo, "log", MASTER, "--no-merges", f"--since=@{lo}", f"--until=@{hi}",
                "--format=%H%x00%s%x00%ae").stdout.splitlines()
    same = [r.split("\x00")[0] for r in rows if r.split("\x00")[1:] == [subj, author]]
    if not same:
        return None, None
    pid, files = _patch_id(repo, sha), _files(repo, sha)
    for m in same:
        if pid and _patch_id(repo, m) == pid:
            return m, "same patch-id"
    for m in same:
        mf = _files(repo, m)
        if files and len(files & mf) >= 0.5 * len(files | mf):
            return m, "same subject+author, >=50% shared files"
    return None, None


def _branch_rank(repo, sha) -> tuple:
    """Higher release branch first (openssl-4.0 > openssl-3.6 > ... > OpenSSL_1_0_2-stable)."""
    best = (0,)
    for b in _git(repo, "branch", "-r", "--contains", sha).stdout.split():
        nums = tuple(int(n) for n in re.findall(r"\d+", b))
        best = max(best, nums or (0,))
    return best


def trail_candidates(repo, cve: str) -> tuple[list[str], str]:
    """Master commits citing the CVE; documentation-only ones followed to their PR's code commits."""
    ids = [cve, cve.replace("CVE-", "CAN-", 1)]  # pre-2005 commits cite the candidate id
    shas = list(dict.fromkeys(s for i in ids for s in _git(repo, "log", MASTER, "--format=%H", "-F",
                                                              f"--grep={i}").stdout.split()))
    out, via = [], "trail"
    for sha in shas:
        st = diff_stat(repo, sha)
        if st and st[0] > 0:
            out.append(sha)
            continue
        body = _git(repo, "log", "-1", "--format=%B", sha).stdout
        for pr in set(re.findall(r"pull/(\d+)|#(\d{4,6})\b", body)):
            num = pr[0] or pr[1]
            hop = _git(repo, "log", MASTER, "--format=%H", "-F",
                       f"--grep=openssl/openssl/pull/{num})").stdout.split()
            for h in hop:
                hs = diff_stat(repo, h)
                if hs and hs[0] > 0 and h not in out:
                    out.append(h)
                    via = "trail+pr"
    if not out:
        # Pre-PR era: the fix was committed together with its CHANGES entry. The commit
        # that ADDED the id to the changelog is the fix iff it also touches source.
        for i in ids:
            for h in _git(repo, "log", MASTER, "--format=%H", "-S", i, "--", "CHANGES", "CHANGES.md").stdout.split():
                hs = diff_stat(repo, h)
                subj = _git(repo, "log", "-1", "--format=%s", h).stdout
                # a branch sync / import bundles unrelated changes: never a fix commit
                if re.search(r"(?i)\b(update[ds]? from|merge|sync|import of|backport of)\b", subj):
                    continue
                if hs and hs[0] > 0 and h not in out:
                    out.append(h)
                    via = "changes-entry"
    return out, via


def nvd_cwe(cve: str, cache: pathlib.Path, offline: bool) -> tuple[str | None, str | None]:
    f = cache / f"{cve}.json"
    if not f.exists():
        if offline:
            return None, None
        req = urllib.request.Request(NVD.format(cve), headers={"User-Agent": "temporal-crucible-harvest"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    f.write_bytes(r.read())
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(30 * (attempt + 1))
        time.sleep(6.5)  # keyless NVD limit: 5 requests per 30 s
        if not f.exists():
            return None, None
    try:
        vulns = json.loads(f.read_text()).get("vulnerabilities", [])
    except json.JSONDecodeError:
        return None, None
    for v in vulns:
        for w in v.get("cve", {}).get("weaknesses", []):
            for d in w.get("description", []):
                val = d.get("value", "")
                if val.startswith("CWE-"):
                    return val, None
    return None, None


def pick_control(repo, sha, taken, event_shas):
    target = diff_stat(repo, sha)
    if not target or target[0] == 0:
        return None
    best, best_cost = None, None
    for cand in _git(repo, "rev-list", "--no-merges", "-n", "400", sha).stdout.split()[1:]:
        if cand in taken or cand in event_shas:
            continue
        st = diff_stat(repo, cand)
        if not st or st[0] == 0:
            continue
        cost = abs(st[0] - target[0]) * 50 + abs(st[1] - target[1])
        if best_cost is None or cost < best_cost:
            best, best_cost = cand, cost
        if best_cost == 0:
            break
    return best


def severity(cna: dict) -> str | None:
    for m in cna.get("metrics", []):
        o = m.get("other", {})
        if o.get("type") == "https://www.openssl.org/policies/secpolicy.html":
            return o.get("content", {}).get("text")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metadata", type=pathlib.Path, required=True)
    ap.add_argument("--repo", default="openssl")
    ap.add_argument("--out", type=pathlib.Path, default=EVENTS_DIR / "openssl.json")
    ap.add_argument("--offline-nvd", action="store_true", help="use only the NVD cache")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--review", type=pathlib.Path, default=EVENTS_DIR / "openssl_review.json",
                    help="manual diff-inspection verdicts for needs_review events")
    a = ap.parse_args()
    repo = POOL_DIR / a.repo
    cache = DBS_DIR / "nvd_cache"
    cache.mkdir(parents=True, exist_ok=True)
    meta_head = _git(a.metadata, "rev-parse", "HEAD").stdout.strip()
    head = _git(repo, "rev-parse", MASTER).stdout.strip()

    records = sorted((a.metadata / "secjson").glob("CVE-*.json"))
    if a.limit:
        records = records[: a.limit]
    events, rejected, unresolved = [], [], []
    src_counts = {"secjson": 0, "trail": 0, "trail+pr": 0, "changes-entry": 0}
    for i, f in enumerate(records, 1):
        cve = f.stem
        cna = json.loads(f.read_text())["containers"]["cna"]
        urls = [r.get("url", "") for r in cna.get("references", [])]
        cands = list(dict.fromkeys(m for u in urls if "openssl" in u for m in SHA_RE.findall(u)))
        via = "secjson"
        ok = []
        for sha in cands:
            good, why, info = verify(repo, sha)
            (ok.append((sha, info)) if good else rejected.append({"cve": cve, "sha": sha, "reason": why, **info}))
        if not ok:
            trail, via = trail_candidates(repo, cve)
            for sha in trail:
                good, why, info = verify(repo, sha)
                (ok.append((sha, info)) if good else rejected.append({"cve": cve, "sha": sha, "reason": why, **info}))
        if not ok:
            unresolved.append(cve)
            continue
        mains = [(s, inf, "listed") for s, inf in ok if on_master(repo, s)]
        if not mains:
            for s, inf in ok:
                m, how = master_equivalent(repo, s)
                if m and m not in {x[0] for x in mains}:
                    good, why, minf = verify(repo, m)
                    if good:
                        mains.append((m, minf, how))
        if mains:
            chosen, master_flag = mains, True
        else:
            top = max(ok, key=lambda t: _branch_rank(repo, t[0]))
            chosen, master_flag = [(top[0], top[1], "branch only")], False
        src_counts[via] += 1
        cwe = None
        for p in cna.get("problemTypes", []):
            for d in p.get("descriptions", []):
                cwe = cwe or d.get("cweId")
        cwe_src = "record" if cwe else None
        if not cwe:
            cwe, _ = nvd_cwe(cve, cache, a.offline_nvd)
            cwe_src = "nvd" if cwe else None
        for k, (sha, info, master_via) in enumerate(chosen):
            prior = next((e for e in events if e["sha"] == sha), None)
            if prior:  # one commit fixing several CVEs is one event
                prior["cves"].append(cve)
                continue
            events.append({"cves": [cve], "needs_review": via == "changes-entry","id": cve if len(chosen) == 1 else f"{cve}#{k + 1}", "class": "security-fix", "sha": sha,
                           "cve": cve, "on_master": master_flag, "master_via": master_via, "source": via, "severity": severity(cna),
                           "cwe": cwe, "cwe_source": cwe_src, "summary": cna.get("title"),
                           "code_files": info.get("code_files"), "code_churn": info.get("code_churn")})
        if i % 25 == 0:
            print(f"  {i}/{len(records)} records, {len(events)} fix events", flush=True)

    review = json.loads(a.review.read_text())["events"] if a.review.exists() else {}
    kept = []
    for e in events:
        if e["needs_review"]:
            v = review.get(e["sha"])
            if v is None:
                e["review"] = "PENDING"
            elif v["verdict"] == "reject":
                rejected.append({"cve": ",".join(e["cves"]), "sha": e["sha"], "reason": "manual review: " + v["note"]})
                continue
            else:
                e["review"] = v["note"]
        kept.append(e)
    events = kept
    event_shas = {e["sha"] for e in events}
    taken: set[str] = set()
    controls = []
    for e in events:
        c = pick_control(repo, e["sha"], taken, event_shas)
        if c:
            taken.add(c)
            controls.append({"id": f"control-for-{e['id']}", "class": "control", "sha": c, "matched_to": e["sha"]})
    fixes = [e for e in events if e["class"] == "security-fix"]
    out = {"repo": a.repo, "source": "github.com/openssl/release-metadata secjson (CVE JSON 5) + master commit trail",
           "metadata_head": meta_head, "pool_head": head,
           "counts": {"cve_records": len(records), "cves_resolved": len({c for e in fixes for c in e["cves"]}),
                      "cves_unresolved": len(unresolved), "security-fix": len(fixes),
                      "security-fix_on_master": sum(e["on_master"] for e in fixes), "control": len(controls),
                      "with_cwe": sum(bool(e["cwe"]) for e in fixes), "rejected_shas": len(rejected),
                      "needs_review": sum(e["needs_review"] for e in fixes),
                      "review_pending": sum(e.get("review") == "PENDING" for e in fixes),
                      "resolved_via": src_counts, "introduced": 0},
           "unresolved": unresolved, "rejected": rejected, "events": fixes + controls}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
