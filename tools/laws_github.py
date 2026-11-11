#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""PR titles, PR bodies and linked-issue labels for the fix label (methods review M6, "Workflow handling").
No statistic is computed here; `tools/laws_history.py` writes the keyword label and this revises it.

    python tools/laws_github.py --repo NAME --out DIR           -> DIR/github/NAME.json

The registered rules this implements, verbatim from M6:

  "For repos where >= 30% of first-parent commits are merges, the unit is the first-parent commit (merge or
   squash), labelled from the merge commit message plus the PR title and body. Where available, the linked
   issue's labels are used (an issue labelled `bug`, `type: bug`, `kind/bug` or `defect` makes the fix label; an
   issue with a `feature` / `enhancement` label suppresses a keyword-only fix label)."
  "`Fixes|Closes|Resolves #N` alone is not a fix keyword."

So: a bug-labelled linked issue *makes* the label whatever the words say; a feature-labelled one *unmakes* it only
where the label rested on a keyword alone. A PR that links both kinds of issue is a fix -- the bug rule is checked
first, because M6 states it as making the label rather than as evidence to weigh. The commit must still touch a
unit source file and not be a bot's: this revises the message half of `laws_history.py`'s rule, nothing else.

Label spelling. M6 names four bug spellings and two feature ones; projects write them with a qualifier
(`type: bug`, `kind/bug`, `Type/Bug`). `_norm` lowercases, drops a leading `type`/`kind`/`category`/`c`/`a`
qualifier and collapses the rest, so all four of M6's bug spellings land on `bug` or `defect`. Nothing broader is
matched: `bug-report`, `needs-triage` and `possible-bug` are not bug labels here.

Quota (CI measurement policy: the GitHub API is a paced resource). One batched GraphQL query carries up to
`BATCH` pull requests with their linked issues' labels and costs **1 point** of 5,000/hour, so a whole repo is
tens of points. Every PR is cached under `DIR/github/cache/<owner>__<name>/pr-<n>.json`, so a re-run costs
nothing; `--max-queries` and `FLOOR` stop a run rather than draining the budget, and the run reports what it
spent. PR numbers come from the commit messages, not from the API: `Merge pull request #N` and a squash subject's
trailing `(#N)`. Only repos hosted on github.com are enriched -- libxml2 is on gitlab.gnome.org and is skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from laws_history import MERGE_SHARE, is_fix_message  # noqa: E402
from laws_osv import _git  # noqa: E402

BATCH = 50
FLOOR = 500          # leave this much GraphQL budget untouched
BUG = {"bug", "defect"}
FEATURE = {"feature", "enhancement"}
QUALIFIER = re.compile(r"^(type|kind|category|class|c|a)\b[\s:/_-]*", re.I)
MERGE_PR = re.compile(r"^Merge pull request #(\d+)\b", re.M)
SQUASH_PR = re.compile(r"\(#(\d+)\)\s*$")
GITHUB = re.compile(r"github\.com[:/]+([^/]+)/([^/\s]+?)(?:\.git)?/?$", re.I)
PR_FIELDS = ("number title body mergedAt closingIssuesReferences(first: 20) "
             "{ nodes { number labels(first: 30) { nodes { name } } } }")


def _norm(label: str) -> str:
    """A label with its qualifier removed: `type: bug` and `kind/bug` both become `bug`."""
    return QUALIFIER.sub("", label.strip().lower()).strip()


def coordinates(repo: Path) -> tuple[str, str] | None:
    """(owner, name) when the clone's origin is on github.com, else None."""
    m = GITHUB.search(_git(repo, "remote", "get-url", "origin").strip())
    return (m.group(1), m.group(2)) if m else None


def pr_number(subject: str, body: str) -> int | None:
    """The pull request a walk unit came from, read off its own message: a merge commit names it, and a squash
    merge leaves it at the end of the subject. No API call."""
    if m := MERGE_PR.search(f"{subject}\n{body}"):
        return int(m.group(1))
    if m := SQUASH_PR.search(subject.strip()):
        return int(m.group(1))
    return None


def graphql(body: dict) -> dict:
    """One GraphQL call through the gh CLI. A NOT_FOUND for one alias (a number that is an issue, not a PR) is
    not a failure: gh exits non-zero but still returns the data for every alias that resolved."""
    p = subprocess.run(["gh", "api", "graphql", "--input", "-"], input=json.dumps(body),
                       capture_output=True, text=True)
    out = p.stdout.strip()
    if not out:
        raise RuntimeError(f"gh api graphql failed: {p.stderr[:300]}")
    rec = json.loads(out)
    if rec.get("data") is None:
        raise RuntimeError(f"gh api graphql returned no data: {str(rec.get('errors'))[:300]}")
    return rec


def remaining() -> int:
    rec = graphql({"query": "query { rateLimit { remaining } }"})
    return int(rec["data"]["rateLimit"]["remaining"])


def fetch_prs(owner: str, name: str, numbers: list[int], cache: Path, max_queries: int | None = None,
              batch: int = BATCH) -> tuple[dict[int, dict], dict]:
    """{number: pr record} for `numbers`, from the cache first and the API for the rest."""
    cache.mkdir(parents=True, exist_ok=True)
    found: dict[int, dict] = {}
    want = []
    for n in sorted(set(numbers)):
        f = cache / f"pr-{n}.json"
        if f.exists():
            rec = json.loads(f.read_text())
            if rec is not None:
                found[n] = rec
        else:
            want.append(n)
    api = {"cached": len(found), "requested": len(want), "queries": 0, "cost": 0, "stopped": None}
    if not want:
        api["remaining"] = None
        return found, api
    left = remaining()
    api["remaining_before"] = left
    for i in range(0, len(want), batch):
        if max_queries is not None and api["queries"] >= max_queries:
            api["stopped"] = f"--max-queries {max_queries} reached"
            break
        if left - 1 < FLOOR:
            api["stopped"] = f"GraphQL budget would drop below the {FLOOR}-point floor"
            break
        chunk = want[i:i + batch]
        aliases = " ".join(f"p{n}: pullRequest(number: {n}) {{ {PR_FIELDS} }}" for n in chunk)
        rec = graphql({"query": f'query {{ repository(owner: "{owner}", name: "{name}") {{ {aliases} }} '
                                f"rateLimit {{ cost remaining }} }}"})
        api["queries"] += 1
        api["cost"] += int(rec["data"].get("rateLimit", {}).get("cost") or 1)
        left = int(rec["data"].get("rateLimit", {}).get("remaining") or left - 1)
        repo_node = rec["data"].get("repository") or {}
        for n in chunk:
            pr = repo_node.get(f"p{n}")
            (cache / f"pr-{n}.json").write_text(json.dumps(pr) + "\n")  # a null is cached too: do not re-ask
            if pr is not None:
                found[n] = pr
    api["remaining"] = left
    return found, api


def issue_labels(pr: dict | None) -> list[dict]:
    """[{number, labels}] for the issues a PR closes."""
    if not pr:
        return []
    return [{"number": n.get("number"),
             "labels": [x["name"] for x in (n.get("labels") or {}).get("nodes") or []]}
            for n in (pr.get("closingIssuesReferences") or {}).get("nodes") or []]


def relabel(keyword: bool, pr: dict | None, merge_unit: bool) -> dict:
    """The revised message-side fix decision for one walk unit (see the module docstring for the rules).

    `keyword` is laws_history.py's own decision on the unit's message, taken as given: that module stores only
    the first 300 characters of a subject, so recomputing the keyword from the database silently loses the
    keyword of a longer subject (postgres has 250 such commits). This module only ever ADDS the PR's title and
    body to it, and only where the walk is the first-parent chain -- there the merge commit's own message
    ("Merge pull request #7 from x/y") carries nothing at all."""
    issues = issue_labels(pr)
    labels = {_norm(x) for i in issues for x in i["labels"]}
    used_pr = bool(merge_unit and pr)
    pr_keyword = bool(used_pr and is_fix_message(f"{pr.get('title') or ''}\n{pr.get('body') or ''}"))
    keyword_now = bool(keyword or pr_keyword)
    out = {"keyword": keyword_now, "keyword_on_message_alone": bool(keyword), "keyword_from_pr": pr_keyword,
           "pr": pr.get("number") if pr else None, "used_pr_text": used_pr,
           "issues": issues, "bug_labels": sorted(labels & BUG), "feature_labels": sorted(labels & FEATURE)}
    if labels & BUG:
        return {**out, "fix": True, "rule": "issue-bug"}
    if labels & FEATURE and keyword_now:
        return {**out, "fix": False, "rule": "issue-feature-suppressed"}
    return {**out, "fix": keyword_now, "rule": "keyword+pr" if pr_keyword and not keyword else "keyword"}


def bodies(repo: Path) -> dict[str, str]:
    """{sha: commit body} for the whole repo in ONE git pass. A `git show` per commit costs a process each and
    made postgres (65,885 commits) impractical; this is the same SEP-delimited log laws_history.py walks with."""
    out: dict[str, str] = {}
    log = _git(repo, "log", "--format=%x1e%H%x00%b", "--all")
    for chunk in log.split("\x1e")[1:]:
        sha, _, body = chunk.partition("\x00")
        out[sha.strip()] = body
    return out


def units(history: Path) -> tuple[list[dict], dict]:
    """The walk units that could carry a fix label, with their keyword label, and the history's meta."""
    con = sqlite3.connect(f"file:{history}?mode=ro", uri=True)
    meta = dict(con.execute("SELECT key, value FROM meta"))
    rows = [{"sha": s, "ct": ct, "fix": bool(f), "keyword": bool(k), "n_units": n, "subject": sub, "bot": bool(b)}
            for s, ct, f, k, n, sub, b in con.execute(
                "SELECT sha, ct, fix, keyword, n_units, subject, bot FROM commit_ ORDER BY ct")]
    con.close()
    return rows, meta


def enrich(repo: Path, history: Path, out: Path, max_queries: int | None = None) -> dict:
    rows, meta = units(history)
    coord = coordinates(repo)
    merge_unit = float(meta.get("merge_share", 0)) >= MERGE_SHARE
    rec: dict = {"repo": repo.name, "github": coord and f"{coord[0]}/{coord[1]}",
                 "merge_share": float(meta.get("merge_share", 0)), "merge_unit": merge_unit,
                 "unit": meta.get("unit"), "commits": len(rows)}
    if coord is None:
        return {**rec, "skipped": "the clone's origin is not on github.com, so there is no PR or issue to read"}
    body_of = bodies(repo)
    wanted = {}
    for r in rows:
        if r["bot"] or r["n_units"] == 0:
            continue  # a bot's commit and a commit with no unit source file can carry no fix label either way
        r["_body"] = body_of.get(r["sha"], "")
        if n := pr_number(r["subject"], r["_body"]):
            wanted[r["sha"]] = n
    prs, api = fetch_prs(coord[0], coord[1], list(wanted.values()),
                         out.parent / "cache" / f"{coord[0]}__{coord[1]}", max_queries)
    changed, decisions = [], []
    for r in rows:
        if r["bot"] or r["n_units"] == 0:
            continue
        pr = prs.get(wanted.get(r["sha"]))
        r.pop("_body", None)
        d = relabel(r["keyword"], pr, merge_unit)
        d["sha"], d["fix_before"] = r["sha"], r["fix"]
        decisions.append(d)
        if d["fix"] != r["fix"]:
            changed.append(d)
    rec.update({"labelled_units": len(decisions), "with_pr": sum(bool(d["pr"]) for d in decisions),
                "with_linked_issue": sum(bool(d["issues"]) for d in decisions),
                "fix_before": sum(d["fix_before"] for d in decisions),
                "fix_after": sum(d["fix"] for d in decisions),
                "changed": len(changed),
                "made_by_issue_bug": sum(1 for d in changed if d["rule"] == "issue-bug"),
                "suppressed_by_issue_feature": sum(1 for d in changed if d["rule"] == "issue-feature-suppressed"),
                "made_by_pr_text": sum(1 for d in changed if d["rule"] == "keyword+pr" and d["fix"]),
                "unmade_by_pr_text": sum(1 for d in changed if d["rule"] == "keyword+pr" and not d["fix"]),
                "api": api, "decisions": decisions})
    return rec


def fix_labels(record: Path) -> dict[str, bool]:
    """{sha: revised fix label} from this tool's output, for the defect laws to read in place of the history
    database's `fix` column. An empty mapping where the repo was skipped: the caller then keeps the keyword
    label, which is what a non-GitHub repo has to fall back on.

    Nothing in this repository consumes this yet: laws_panel.py still builds its file-years from the history
    database. Wiring it in changes what LAW-6, LAW-7 and LAW-8 are computed from, so it is a separate step and
    must happen before the scorer freeze, not after."""
    rec = json.loads(record.read_text())
    return {d["sha"]: bool(d["fix"]) for d in rec.get("decisions", [])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", type=Path, required=True, help="the study directory (its history/ is read)")
    ap.add_argument("--max-queries", type=int, default=None)
    a = ap.parse_args()
    from laws_osv import POOL_DIR
    repo = Path(a.repo) if Path(a.repo).is_dir() else POOL_DIR / a.repo
    f = a.out / "github" / f"{repo.name}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    rec = enrich(repo, a.out / "history" / f"{repo.name}.db", f, a.max_queries)
    f.write_text(json.dumps(rec, indent=1) + "\n")
    if rec.get("skipped"):
        print(f"{rec['repo']}: skipped -- {rec['skipped']}")
        return 0
    print(f"{rec['repo']} ({rec['github']}, merge_unit={rec['merge_unit']}): {rec['labelled_units']} units, "
          f"{rec['with_pr']} with a PR, {rec['with_linked_issue']} with a linked issue; fixes "
          f"{rec['fix_before']} -> {rec['fix_after']} ({rec['changed']} changed: "
          f"+{rec['made_by_issue_bug']} issue-bug, -{rec['suppressed_by_issue_feature']} issue-feature, "
          f"+{rec['made_by_pr_text']}/-{rec['unmade_by_pr_text']} PR text); "
          f"{rec['api']['queries']} queries, {rec['api']['cost']} points, "
          f"{rec['api'].get('remaining')} left{' -- STOPPED: ' + rec['api']['stopped'] if rec['api']['stopped'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
