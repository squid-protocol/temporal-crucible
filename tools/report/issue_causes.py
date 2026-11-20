#!/usr/bin/env python3
"""PROTOTYPE: link fixes to the changes that caused them through the project's own pull requests and issues, for repositories without `Fixes:` trailers.

For each merged pull request that looks like a fix (title, branch name or label), find an earlier change it blames:
  A. the fix PR's own text cites an earlier merged PR or a commit ("regression from #123", "broke in abc1234", a pull/commit URL);
  B. an issue the fix PR closes ("fixes #M") cites an earlier merged PR or commit in its text or comments.
Each cause is mapped to the commits of that PR, and the pair (fix, cause) is written in the form tools/sensor/blast_radius.py reads.
Validation: where the blame-sampled pairs of the evolution report also name a cause for the same fix, how often do the two agree?

    python tools/report/issue_causes.py --repo-path DIR --slug owner/repo --name NAME --out DIR [--lang python]
Needs `gh` (authenticated). Network reads are cached under OUT/gh_cache."""
import argparse
import collections
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import evolution_report as ER  # noqa: E402

FIXPR = re.compile(r"\b(fix(es|ed)?|bug|crash|error|regress\w*|broken|patch|repair|resolve[sd]?|revert)\b", re.I)
REF = re.compile(r"(?<![\w/])#(\d+)\b")
URL = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/(pull|issues|commit)/([0-9a-f]+)")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
CLOSES = re.compile(r"\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\b[:\s]+(?:https://github\.com/[\w.-]+/[\w.-]+/(?:issues|pull)/|[\w.-]+/[\w.-]+)?#?(\d+)", re.I)


def gh(path, cache, paginate=False):
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return json.load(open(cache))
    cmd = ["gh", "api", path] + (["--paginate", "--slurp"] if paginate else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        return None
    data = json.loads(r.stdout)
    if paginate:
        data = [x for page in data for x in page]
    json.dump(data, open(cache, "w"))
    return data


def pr_commits(repo, merge_sha):
    """Commits a merged PR brought in: a merge commit's second-parent range, or the squash/rebase commit itself."""
    parents = ER.git(repo, "rev-list", "--parents", "-n", "1", merge_sha).split()[1:]
    if len(parents) >= 2:
        return ER.git(repo, "rev-list", f"{parents[0]}..{parents[1]}").split()
    return [merge_sha]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-path"), ap.add_argument("--slug"), ap.add_argument("--name"), ap.add_argument("--out"), ap.add_argument("--lang", default="python")
    a = ap.parse_args()
    out = Path(a.out)
    cache = out / "gh_cache"
    repo = a.repo_path
    prs = gh(f"repos/{a.slug}/pulls?state=closed&per_page=100", cache / "pulls.json", paginate=True) or []
    merged = {p["number"]: p for p in prs if p.get("merged_at")}
    commits = ER.load_commits(repo)
    diff = ER.diff_pass(repo, a.lang, out / "cache", a.name)
    nfun = {s: len(diff.get(s, {}).get("funcs", [])) for s in commits}

    def rep_commit(shas):
        best = [s for s in shas if s in commits and nfun.get(s, 0) > 0]
        return max(best, key=lambda s: (nfun[s], -commits[s]["ct"])) if best else None

    def ts(x):
        return datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()

    def refs_in(text):
        text = text or ""
        nums = {int(n) for n in REF.findall(text)}
        for slug, kind, ident in URL.findall(text):
            if slug.lower() != a.slug.lower():
                continue
            if kind in ("pull", "issues") and ident.isdigit():
                nums.add(int(ident))
        shas = {m for m in SHA.findall(text) if any(c.isalpha() for c in m) and any(c.isdigit() for c in m)}
        shas |= {i for slug, kind, i in URL.findall(text) if kind == "commit" and slug.lower() == a.slug.lower()}
        return nums, shas

    def resolve_sha(s):
        r = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "-q", s + "^{commit}"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() in commits else None

    fixes = [p for p in merged.values() if FIXPR.search(p["title"] or "") or FIXPR.search(p["head"]["ref"] or "") or any("bug" in (l["name"] or "").lower() for l in p.get("labels", []))]
    stats = collections.Counter()
    results = []
    for p in sorted(fixes, key=lambda p: p["number"]):
        stats["fix_like_prs"] += 1
        n = p["number"]
        text = (p["title"] or "") + "\n" + (p["body"] or "")
        nums, shas = refs_in(text)
        evidence, cause_prs, cause_commits = [], set(), set()
        for m in nums:
            if m != n and m in merged and ts(merged[m]["merged_at"]) < ts(p["merged_at"]):
                cause_prs.add(m); evidence.append(f"A:PR#{m}")
        for s in shas:
            c = resolve_sha(s)
            if c and commits[c]["ct"] < ts(p["merged_at"]):
                cause_commits.add(c); evidence.append(f"A:{s[:7]}")
        issues = {int(x) for x in CLOSES.findall(text)} | {m for m in nums if m not in merged}
        for m in sorted(issues)[:3]:
            iss = gh(f"repos/{a.slug}/issues/{m}", cache / f"issue_{m}.json")
            if not iss or "pull_request" in iss and iss.get("number") in merged:
                continue
            com = gh(f"repos/{a.slug}/issues/{m}/comments?per_page=100", cache / f"issue_{m}_comments.json", paginate=True) or []
            itext = (iss.get("title") or "") + "\n" + (iss.get("body") or "") + "\n" + "\n".join(c.get("body") or "" for c in com)
            n2, s2 = refs_in(itext)
            for k in n2:
                if k not in (n, m) and k in merged and ts(merged[k]["merged_at"]) < ts(iss["created_at"]):
                    cause_prs.add(k); evidence.append(f"B:issue#{m}->PR#{k}")
            for s in s2:
                c = resolve_sha(s)
                if c and commits[c]["ct"] < ts(iss["created_at"]):
                    cause_commits.add(c); evidence.append(f"B:issue#{m}->{s[:7]}")
        if not (cause_prs or cause_commits):
            stats["no_cause_text"] += 1
            continue
        stats["with_cause_text"] += 1
        fix_shas = pr_commits(repo, p["merge_commit_sha"]) if p.get("merge_commit_sha") else []
        fx = rep_commit(fix_shas)
        cands = set(cause_commits)
        for m in cause_prs:
            cs = pr_commits(repo, merged[m]["merge_commit_sha"]) if merged[m].get("merge_commit_sha") else []
            c = rep_commit(cs)
            if c:
                cands.add(c)
        cands = {c for c in cands if nfun.get(c, 0) > 0}
        if not fx:
            stats["fix_has_no_function_edits"] += 1
            continue
        if not cands:
            stats["cause_has_no_function_edits"] += 1
            continue
        for c in sorted(cands, key=lambda c: commits[c]["ct"]):
            if commits[c]["ct"] >= commits[fx]["ct"]:
                continue
            results.append({"fix": fx, "ind": c, "fix_ct": commits[fx]["ct"], "ind_ct": commits[c]["ct"], "lag": (commits[fx]["ct"] - commits[c]["ct"]) / 86400, "evidence": evidence, "fix_pr": n})
            stats["pairs"] += 1
    # agreement with the blame pairs of the evolution report (same fix commit, cause named by both)
    ns = argparse.Namespace(repo=repo, lang=a.lang, out=a.out, cache=None, name=a.name, blame=1500, scans=None, radius=False, gif=None, link_base=None)
    built = ER.build(ns)
    blame = collections.defaultdict(set)
    for f, i in built["_internal"]["pairs"]:
        blame[f].add(i)
    both = agree = 0
    for r in results:
        if r["fix"] in blame:
            both += 1
            agree += r["ind"] in blame[r["fix"]]
    json.dump(results, open(out / "issue_pairs.json", "w"))
    print(f"== {a.name}: {len(merged)} merged PRs; fix-like {stats['fix_like_prs']}; with a cause in the text {stats['with_cause_text']}; pairs {stats['pairs']} (fix has no function edits {stats['fix_has_no_function_edits']}, cause has none {stats['cause_has_no_function_edits']})")
    print(f"   blame-sampled pairs on the same fix commits: {both} overlap, {agree} name the same cause commit")
    ev = collections.Counter(e.split(":")[0] for r in results for e in r["evidence"][:1])
    print("   first evidence kind:", dict(ev), "| median lag days", sorted(r["lag"] for r in results)[len(results) // 2] if results else None)


if __name__ == "__main__":
    main()
