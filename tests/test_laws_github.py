"""The M6 workflow rules: where a PR number comes from, how a linked issue's labels make or unmake the fix
label, and that a batched query is cached rather than re-asked."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_github as G  # noqa: E402


def pr(number=7, title="", body="", issues=()):
    return {"number": number, "title": title, "body": body, "mergedAt": "2020-01-01T00:00:00Z",
            "closingIssuesReferences": {"nodes": [{"number": n, "labels": {"nodes": [{"name": x} for x in ls]}}
                                                  for n, ls in issues]}}


def test_the_qualifier_is_stripped_so_m6s_four_bug_spellings_all_match():
    assert {G._norm(x) for x in ("bug", "type: bug", "kind/bug", "Type/Bug", "defect")} == {"bug", "defect"}
    assert G._norm("enhancement") == "enhancement" and G._norm("kind/feature") == "feature"
    # nothing broader: M6 names four spellings, not every label with "bug" in it
    assert G._norm("bug-report") not in G.BUG and G._norm("possible-bug") not in G.BUG


def test_a_pr_number_is_read_off_the_commit_message_not_the_api():
    assert G.pr_number("Merge pull request #123 from a/b", "") == 123
    assert G.pr_number("Merge pull request #5 from x/y", "body") == 5
    assert G.pr_number("fix the parser (#456)", "") == 456          # a squash merge
    assert G.pr_number("fix the parser", "Fixes #99") is None       # a closed issue is not the PR
    assert G.pr_number("bump deps", "") is None


def test_a_bug_labelled_issue_makes_the_fix_label_whatever_the_words_say():
    d = G.relabel(False, pr(title="Add a flag", issues=[(1, ["type: bug"])]), True)
    assert d["fix"] and d["rule"] == "issue-bug" and d["bug_labels"] == ["bug"]
    assert not d["keyword"]  # no fix keyword anywhere: the issue label alone made it


def test_a_feature_labelled_issue_unmakes_a_keyword_only_label():
    d = G.relabel(False, pr(title="fix the missing option", issues=[(2, ["enhancement"])]), True)
    assert d["keyword"] and not d["fix"] and d["rule"] == "issue-feature-suppressed"


def test_a_pr_linking_both_kinds_of_issue_is_a_fix():
    d = G.relabel(False, pr(title="fix a crash", issues=[(1, ["bug"]), (2, ["enhancement"])]), True)
    assert d["fix"] and d["rule"] == "issue-bug"


def test_the_pr_text_only_joins_the_message_where_the_walk_is_the_first_parent_chain():
    p = pr(title="fix a segfault in the parser")
    assert G.relabel(False, p, True)["fix"] is True            # merge-unit repo: the PR title carries the label
    d = G.relabel(False, p, False)
    assert d["fix"] is False and d["used_pr_text"] is False    # non-merge-unit: the unit's own message only
    assert d["rule"] == "keyword"


def test_closes_alone_is_still_not_a_fix_keyword():
    d = G.relabel(False, pr(title="Add a retry option", body="Closes #42"), True)
    assert not d["keyword"] and not d["fix"]                   # M6: `Closes #N` alone is not a keyword
    assert d["issues"] == []                                   # and an unlinked `Closes` yields no labels


def test_an_issue_with_no_label_leaves_the_keyword_decision_alone():
    d = G.relabel(True, pr(title="fix a leak", issues=[(3, [])]), True)
    assert d["fix"] and d["rule"] == "keyword" and d["bug_labels"] == []  # the message already said it


def test_fetch_prs_reads_the_cache_and_never_re_asks_a_known_miss(tmp_path: Path, monkeypatch):
    cache = tmp_path / "c"
    cache.mkdir()
    (cache / "pr-1.json").write_text(json.dumps(pr(1, "cached")))
    (cache / "pr-2.json").write_text("null")          # a known miss: the number was an issue, not a PR
    calls = []
    monkeypatch.setattr(G, "graphql", lambda body: calls.append(body) or {"data": {}})
    got, api = G.fetch_prs("o", "n", [1, 2], cache)
    assert set(got) == {1} and api["requested"] == 0 and api["queries"] == 0 and calls == []


def test_fetch_prs_batches_and_stops_at_the_floor(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(G, "remaining", lambda: G.FLOOR)      # no budget left above the floor
    got, api = G.fetch_prs("o", "n", [10, 11], tmp_path / "c", batch=1)
    assert got == {} and api["queries"] == 0 and "floor" in api["stopped"]

    seen = []

    def fake(body):
        seen.append(body["query"])
        return {"data": {"repository": {f"p{n}": pr(n) for n in (10, 11)}, "rateLimit": {"cost": 1, "remaining": 4000}}}

    monkeypatch.setattr(G, "remaining", lambda: 4000)
    monkeypatch.setattr(G, "graphql", fake)
    got, api = G.fetch_prs("o", "n", [10, 11], tmp_path / "c2", batch=50)
    assert set(got) == {10, 11} and api["queries"] == 1 and api["cost"] == 1   # one query for both
    assert "p10: pullRequest(number: 10)" in seen[0] and "p11:" in seen[0]
    assert (tmp_path / "c2" / "pr-10.json").exists()                           # and both were cached


def test_graphql_tolerates_a_not_found_alias(monkeypatch):
    payload = {"data": {"repository": {"p1": pr(1), "p2": None}}, "errors": [{"type": "NOT_FOUND"}]}

    def fake_run(*a, **k):
        return subprocess.CompletedProcess(a, 1, json.dumps(payload), "gh: Could not resolve")

    monkeypatch.setattr(G.subprocess, "run", fake_run)
    assert G.graphql({"query": "x"})["data"]["repository"]["p2"] is None   # non-zero exit, data still used


def test_graphql_raises_when_there_is_no_data_at_all(monkeypatch):
    monkeypatch.setattr(G.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "bad credentials"))
    with pytest.raises(RuntimeError, match="failed"):
        G.graphql({"query": "x"})


def test_bodies_reads_every_commit_body_in_one_pass(tmp_path: Path):
    r = tmp_path / "r"
    r.mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)  # noqa: E731
    subprocess.run(["git", "init", "-q", "-b", "main", str(r)], check=True, capture_output=True)
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    shas = []
    for i, body in enumerate(["Closes #1\n\nmulti\nline", "", "Fixes #2"]):
        (r / f"f{i}.c").write_text(f"int f{i};\n")
        git("add", "-A")
        git("commit", "-qm", f"subject {i}" + (f"\n\n{body}" if body else ""))
        shas.append(subprocess.run(["git", "-C", str(r), "rev-parse", "HEAD"],
                                   capture_output=True, text=True).stdout.strip())
    got = G.bodies(r)
    assert set(shas) <= set(got)
    assert "multi\nline" in got[shas[0]] and got[shas[1]].strip() == "" and "Fixes #2" in got[shas[2]]


def test_the_keyword_comes_from_the_history_database_not_from_a_truncated_subject():
    """laws_history stores only the first 300 characters of a subject; recomputing from it lost the keyword of
    250 postgres commits. This module takes that decision as given and only ever adds the PR's text to it."""
    assert G.relabel(True, None, False)["fix"] is True        # the database said fix: nothing can un-say it here
    assert G.relabel(True, None, True)["fix"] is True
    assert G.relabel(False, None, True)["fix"] is False       # and no PR means no new evidence either way
    d = G.relabel(False, pr(title="fix a crash"), True)
    assert d["fix"] and d["keyword_from_pr"] and not d["keyword_on_message_alone"]
    d = G.relabel(True, pr(title="Add a flag"), True)
    assert d["fix"] and d["rule"] == "keyword" and not d["keyword_from_pr"]


def test_fix_labels_exposes_the_revised_labels_for_the_defect_laws(tmp_path: Path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"repo": "r", "decisions": [{"sha": "a" * 40, "fix": True, "fix_before": False},
                                                        {"sha": "b" * 40, "fix": False, "fix_before": True}]}))
    assert G.fix_labels(f) == {"a" * 40: True, "b" * 40: False}
    skipped = tmp_path / "s.json"
    skipped.write_text(json.dumps({"repo": "s", "skipped": "not on github.com"}))
    assert G.fix_labels(skipped) == {}   # the caller keeps the keyword label
