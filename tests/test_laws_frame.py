"""The sampling frame and the seeded draw (M9). The draw order is the one thing in the study that must never
change once the candidate fingerprint is pushed, so it is pinned here against an independent computation."""
import datetime as dt
import hashlib
import json
import random
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_frame as F  # noqa: E402


def test_the_windows_are_monthly_and_cover_the_frame_period():
    w = F.month_slices("2008-01", "2008-04-01")
    assert w[0] == ("2008-01-01", "2008-01-31")
    assert w[1] == ("2008-02-01", "2008-02-29")          # 2008 was a leap year
    assert w[-1][0] == "2008-04-01" and len(w) == 4
    full = F.month_slices()
    assert full[0][0] == "2008-01-01" and full[-1][1] >= F.PANEL_END
    assert all(a <= b for a, b in full)
    starts = [a for a, _ in full]
    assert len(starts) == len(set(starts))               # no month appears twice


def test_a_truncated_window_halves_until_it_cannot():
    parts = F.split_window("2015-01-01", "2015-01-31")
    assert parts == [("2015-01-01", "2015-01-16"), ("2015-01-17", "2015-01-31")]
    assert F.split_window("2015-01-01", "2015-01-01") is None   # a single day cannot be split


def test_the_frame_splits_capped_windows_and_reports_completeness():
    """A window over the 1,000 cap is re-queried in halves; the frame is complete only when none is truncated."""
    calls = []

    def fake(q):
        calls.append(q)
        lo, hi = q.split("created:")[1].split("..")
        span = (dt.date.fromisoformat(hi) - dt.date.fromisoformat(lo)).days
        if span > 20:                 # a whole month is over the cap; a half-month is not
            return 1500, [f"org/early{i}" for i in range(1000)]
        return 10, [f"org/r{lo}"]

    rec = F.frame("go", fake, start="2015-01", end="2015-02-01")
    assert rec["complete"] is True and rec["truncated_windows"] == []
    assert any("2015-01-01..2015-01-16" in c for c in calls)   # January was split
    assert "org/r2015-01-01" in rec["candidates"] and "org/r2015-01-17" in rec["candidates"]
    assert rec["search_calls"] == len(calls) and rec["search_calls"] >= 4
    assert len(rec["candidates"]) == rec["frame_size"]


def test_a_single_day_over_the_cap_leaves_the_frame_incomplete():
    rec = F.frame("go", lambda q: (1200, ["org/a"]), start="2015-01", end="2015-01-02")
    assert rec["complete"] is False and rec["truncated_windows"]
    assert rec["truncated_windows"][0]["total"] == 1200


def test_jsts_is_javascript_and_typescript_combined():
    b = {"JavaScript": 400, "TypeScript": 300, "CSS": 300}
    assert F.language_share(b, "jsts") == pytest.approx(0.7)       # combined clears 60%
    assert F.language_share(b, "python") == 0.0
    assert F.language_share({"C": 70, "C++": 30}, "c") == pytest.approx(0.7)
    assert F.language_share({"C": 70, "C++": 30}, "cpp") == pytest.approx(0.3)
    assert F.language_share({}, "go") == 0.0
    assert F.SHARE == 0.60


def test_the_candidate_order_is_lower_cased_byte_order_and_deduplicated():
    names = ["Org/Zed", "org/alpha", "ORG/ALPHA", "org/Beta"]
    assert F.sorted_candidates(names) == ["org/alpha", "org/beta", "org/zed"]


def test_the_draw_order_is_exactly_m9s_permutation_and_is_reproducible():
    names = [f"org/r{i:03d}" for i in range(200)]
    got = F.permutation(names)
    expected = random.Random(2982).sample(sorted(n.lower() for n in names), len(names))
    assert got == expected                                  # pinned against an independent computation
    assert F.permutation(names) == got                      # and stable
    assert sorted(got) == sorted(n.lower() for n in names)  # a permutation, nothing dropped or added
    assert got != sorted(n.lower() for n in names)          # and actually shuffled
    assert F.permutation(names, seed=1) != got
    assert F.SEED == 2982 and sys.version_info[:2] == (3, 12)  # M9 names Python 3.12


def test_the_fingerprint_is_the_sha256_of_the_candidate_file(tmp_path: Path):
    f = tmp_path / "go.json"
    f.write_text(json.dumps({"candidates": ["org/a"]}))
    assert F.fingerprint(f) == hashlib.sha256(f.read_bytes()).hexdigest()
    f.write_text(json.dumps({"candidates": ["org/a", "org/b"]}))
    assert F.fingerprint(f) != hashlib.sha256(json.dumps({"candidates": ["org/a"]}).encode()).hexdigest()


def test_each_history_rule_rejects_for_its_own_reason(tmp_path: Path, monkeypatch):
    import subprocess as sp
    repo = tmp_path / "r"
    repo.mkdir()

    def commits(n):
        monkeypatch.setattr(F.subprocess, "run",
                            lambda *a, **k: sp.CompletedProcess(a, 0, f"{n}\n", ""))

    commits(1500)
    assert "fewer than 2000 first-parent commits" in F.eligible_history(repo, "go")["why"]
    commits(5000)
    assert "needs a scan" in F.eligible_history(repo, "go")["why"]        # no snapshot function given
    assert "fewer than 20 quarters" in F.eligible_history(repo, "go", lambda r, l: (10, 40, 38))["why"]
    assert "only 50%" in F.eligible_history(repo, "go", lambda r, l: (30, 40, 20))["why"]
    ok = F.eligible_history(repo, "go", lambda r, l: (30, 40, 38))
    assert ok["eligible"] is True and ok["quarter_coverage"] == 0.95
    assert (F.MIN_COMMITS, F.MIN_SNAPSHOTS, F.MIN_FILES, F.QUARTER_COVERAGE) == (2000, 20, 50, 0.75)


def test_the_search_runner_caches_a_query_and_pages_it(tmp_path: Path, monkeypatch):
    """Every page of a window is fetched, because the frame needs names and not just a count. Each query is
    cached so a run stopped on quota resumes without re-spending it."""
    calls = []

    def fake_gh(path):
        calls.append(path)
        if path == "rate_limit":
            return {"resources": {"core": {"remaining": 5000, "reset": 0},
                                  "search": {"remaining": 30, "reset": 0}}}
        page = int(re.search(r"[?&]page=(\d+)", path).group(1))   # not `per_page=`
        items = [{"full_name": f"org/r{page}_{i}"} for i in range(100 if page < 3 else 50)]
        return {"total_count": 250, "items": items}

    monkeypatch.setattr(F, "_gh", fake_gh)
    run = F.search_runner(tmp_path / "c")
    total, names = run("stars:>=500 language:go created:2015-01-01..2015-01-31")
    assert total == 250 and len(names) == 250                 # all three pages
    assert sum(1 for c in calls if c.startswith("search/")) == 3
    before = len(calls)
    total2, names2 = run("stars:>=500 language:go created:2015-01-01..2015-01-31")
    assert (total2, names2) == (total, names) and len(calls) == before   # served from cache, no new call


def test_the_languages_call_is_cached_and_respects_the_core_floor(tmp_path: Path, monkeypatch):
    seen = []

    def fake_gh(path):
        seen.append(path)
        if path == "rate_limit":
            return {"resources": {"core": {"remaining": 5000, "reset": 0},
                                  "search": {"remaining": 30, "reset": 0}}}
        return {"Go": 900, "Shell": 100}

    monkeypatch.setattr(F, "_gh", fake_gh)
    b = F.language_bytes("prometheus/prometheus", tmp_path / "l")
    assert b == {"Go": 900, "Shell": 100}
    n = len([s for s in seen if s.startswith("repos/")])
    F.language_bytes("prometheus/prometheus", tmp_path / "l")
    assert len([s for s in seen if s.startswith("repos/")]) == n     # cached
    assert F.language_share(b, "go") == pytest.approx(0.9)
    assert F.CORE_FLOOR == 1500                                      # churn and the shepherd share the pool


def test_github_language_names_are_used_and_quoted():
    """The `language:` filter needs GitHub's own names, and `C++`/`C#` do not survive unquoted."""
    assert F.github_languages("go") == ("Go",)
    assert F.github_languages("cpp") == ("C++",) and F.github_languages("csharp") == ("C#",)
    assert 'language:"C++"' in F.query("C++", "2015-01-01", "2015-01-31")
    assert 'language:"C#"' in F.query("C#", "2015-01-01", "2015-01-31")


def test_jsts_is_two_searches_unioned_because_the_filter_is_primary_language_only():
    assert F.github_languages("jsts") == ("JavaScript", "TypeScript")
    seen = []

    def fake(q):
        seen.append(q)
        lang = q.split('language:"')[1].split('"')[0]
        return 1, [f"org/{lang.lower()}-repo"]

    rec = F.frame("jsts", fake, start="2015-01", end="2015-01-31")
    assert rec["github_languages"] == ["JavaScript", "TypeScript"]
    assert any('language:"JavaScript"' in q for q in seen)
    assert any('language:"TypeScript"' in q for q in seen)
    assert rec["candidates"] == ["org/javascript-repo", "org/typescript-repo"]   # unioned
    # every other language is a single search
    one = F.frame("go", lambda q: (1, ["org/g"]), start="2015-01", end="2015-01-31")
    assert one["github_languages"] == ["Go"] and one["search_calls"] == 1


def test_the_shortlist_is_lazy_in_draw_order_and_stops(tmp_path: Path, monkeypatch):
    """M9 evaluates eligibility in draw order and stops once enough pass. Checking the whole frame instead
    would be 81,060 languages-API calls across the ten languages, for a list the draw never reaches the end of."""
    names = [f"org/r{i:04d}" for i in range(2000)]
    calls = []

    def fake_bytes(full_name, cache):
        calls.append(full_name)
        n = int(full_name[-4:])
        return {"Go": 900, "Shell": 100} if n % 3 == 0 else {"Go": 100, "Shell": 900}

    monkeypatch.setattr(F, "language_bytes", fake_bytes)
    monkeypatch.setattr(F, "quota", lambda: {"core": 5000, "search": 30})
    r = F.shortlist("go", names, tmp_path, want=16, buffer=2.0)
    assert r["passed_count"] == 32                       # 16 wanted x 2.0 buffer, then it stops
    assert "32 candidates passed" in r["stopped"]
    assert r["checked"] < 200 and r["checked"] == len(calls)   # nowhere near all 2,000
    assert 0.20 < r["pass_rate"] < 0.45                  # ~one in three by construction, one permutation
    assert r["order_len"] == 2000 and r["share_bar"] == F.SHARE
    # the order is the draw permutation, not the sorted order
    assert [p["repo"] for p in r["passed"]][:5] != sorted(p["repo"] for p in r["passed"])[:5]
    assert all(p["share"] >= F.SHARE for p in r["passed"])


def test_the_shortlist_stops_on_the_quota_floor_and_on_a_limit(tmp_path: Path, monkeypatch):
    names = [f"org/r{i:04d}" for i in range(500)]
    monkeypatch.setattr(F, "language_bytes", lambda n, c: {"Go": 100, "Shell": 900})   # nothing passes
    monkeypatch.setattr(F, "quota", lambda: {"core": 5000, "search": 30})
    r = F.shortlist("go", names, tmp_path, want=16, limit=25)
    assert r["passed_count"] == 0 and r["checked"] == 25 and "--limit 25" in r["stopped"]
    monkeypatch.setattr(F, "quota", lambda: {"core": F.CORE_FLOOR, "search": 30})
    r2 = F.shortlist("go", names, tmp_path, want=16)
    assert r2["checked"] == 0 and "core quota floor" in r2["stopped"]
