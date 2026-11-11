"""The driver: the registered margins, which per-repo effects reach a pool, the one-repo case, and that a law
that raises is recorded as a failure instead of stopping the run."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_defects as D  # noqa: E402
import laws_run as RUN  # noqa: E402
import laws_security as S  # noqa: E402


def repo(name, language="c", **laws):
    return {"repo": name, "language": language, **laws}


def ok(effect, se):
    return {"evaluable": True, "effect": effect, "se": se}


def test_the_margins_and_directions_are_the_registered_ones():
    assert {k: (v["margin"], v["direction"]) for k, v in RUN.SPEC.items()} == {
        "LAW-1": (0.0, 1), "LAW-2": (0.0, 1), "LAW-3": (0.0, 1), "LAW-4": (0.0, 1), "LAW-5": (0.0, 1),
        "LAW-6": (0.0, 1), "LAW-7": (0.5, 1), "LAW-8": (0.02, 1), "LAW-9": (0.0, -1)}
    assert RUN.SPEC["LAW-8"]["equivalence"] == 0.02
    assert RUN.SPEC["LAW-7"]["metrics"] == D.METRICS and RUN.SPEC["LAW-9"]["metrics"] == S.METRICS
    assert [k for k, v in RUN.SPEC.items() if not v["confirmatory"]] == ["LAW-5", "LAW-9"]


def test_only_usable_effects_reach_a_pool():
    rows = [repo("a", **{"LAW-1": ok(1.0, 0.1)}),
            repo("b", **{"LAW-1": {"evaluable": False, "why": "too few"}}),
            repo("c", **{"LAW-1": ok(2.0, float("nan"))}),      # a NaN SE cannot be a variance
            repo("d", **{"LAW-1": ok(2.0, 0.0)}),               # nor can zero
            repo("e", **{})]                                    # the law never ran
    assert RUN._effects(rows, "LAW-1") == [("a", 1.0, 0.1)]


def test_a_metric_bearing_law_is_read_per_metric():
    rows = [repo("a", **{"LAW-7": {"evaluable": True, "metrics": {"coupling": ok(0.9, 0.2),
                                                                  "k_mean": {"evaluable": False}}}})]
    assert RUN._effects(rows, "LAW-7", "coupling") == [("a", 0.9, 0.2)]
    assert RUN._effects(rows, "LAW-7", "k_mean") == []


def test_law5s_two_legs_are_read_from_their_own_keys():
    rows = [repo("a", **{"LAW-5": {"evaluable": True, "q_slope": -0.3, "q_se": 0.1,
                                   "pc_slope": 0.2, "pc_se": 0.05}})]
    assert RUN._leg_effects(rows, "LAW-5", "q_slope", "q_se") == [("a", -0.3, 0.1)]
    assert RUN._leg_effects(rows, "LAW-5", "pc_slope", "pc_se") == [("a", 0.2, 0.05)]


def test_one_repo_is_not_pooled_but_still_reported():
    r = RUN._pool_one([("a", 1.0, 0.25)], margin=0.0, direction=1, equivalence=None)
    assert r["poolable"] is False and "needs at least 2 repos" in r["why"]
    assert r["single_study"]["repo"] == "a" and r["single_study"]["p"] < 0.001
    assert r["single_study"]["p_opposite"] > 0.999
    assert "pooled" not in r                      # nothing is presented as a pooled estimate


def test_the_direction_decides_which_tail_the_p_comes_from():
    pos = RUN._pool_one([("a", -1.0, 0.25)], 0.0, 1, None)["single_study"]
    neg = RUN._pool_one([("a", -1.0, 0.25)], 0.0, -1, None)["single_study"]
    assert pos["p"] > 0.999 and neg["p"] < 0.001  # LAW-9 predicts a negative effect, so -1 is its direction


def test_two_repos_pool_and_carry_an_equivalence_test():
    r = RUN._pool_one([("a", 0.6, 0.1), ("b", 0.7, 0.1)], margin=0.5, direction=1, equivalence=0.02)
    assert r["poolable"] and r["repos"] == 2 and "pooled" in r
    assert 0 <= r["p"] <= 1 and 0 <= r["equivalence_p"] <= 1
    assert RUN._pool_one([], 0.0, 1, None) == {"repos": 0, "poolable": False,
                                               "why": "no repo is evaluable for this law"}


def test_a_law_that_raises_is_recorded_and_the_run_goes_on():
    failures = {}
    good = RUN.guarded("LAW-1", lambda: {"evaluable": True, "effect": 1.0, "se": 0.1}, failures)
    bad = RUN.guarded("LAW-2", lambda: (_ for _ in ()).throw(ValueError("singular matrix")), failures)
    assert good["evaluable"] and "seconds" in good      # the good law returned and was timed
    assert bad["failed"] is True and bad["evaluable"] is False
    assert list(failures) == ["LAW-2"]                  # only the law that raised is recorded
    assert failures["LAW-2"]["error"] == "ValueError: singular matrix"
    assert "traceback" in failures["LAW-2"] and "seconds" in failures["LAW-2"]


def test_the_synthesis_runs_with_one_repo_per_language_and_claims_nothing():
    repos = [repo("libgit2", "c", **{"LAW-2": ok(1.5, 0.2)}), repo("prometheus", "go", **{"LAW-2": ok(1.3, 0.2)})]
    s = RUN.synthesise(repos)
    assert s["languages"] == ["c", "go"] and s["repos_per_language"] == {"c": 1, "go": 1}
    assert "one repo per language" in s["caveat"]
    for lang in ("c", "go"):
        assert s["per_law"]["LAW-2"]["languages"][lang]["poolable"] is False
    u = s["universal"]["LAW-2"]
    assert u["primary_p"] == 1.0 and not u["primary_universal"]   # non-poolable counts against
    assert u["extended_r_of_n"] == [2, 2]


def test_a_metric_law_enters_universality_through_its_weakest_metric():
    def with_metrics(name, lang, ps):
        return repo(name, lang, **{"LAW-7": {"evaluable": True,
                                             "metrics": {m: ok(e, se) for m, (e, se) in ps.items()}}})
    repos = [with_metrics("a", "c", {"coupling": (0.9, 0.05), "k_mean": (0.9, 0.05), "in_cycle": (0.9, 0.05)}),
             with_metrics("b", "c", {"coupling": (0.9, 0.05), "k_mean": (0.9, 0.05), "in_cycle": (0.51, 0.5)})]
    s = RUN.synthesise(repos)
    rec = s["per_law"]["LAW-7"]["languages"]["c"]
    assert all(rec[m]["poolable"] for m in D.METRICS)
    worst = max(rec[m]["p"] for m in D.METRICS)
    assert s["universal"]["LAW-7"]["primary_p"] >= worst   # the conjunction is as weak as its weakest metric


def test_a_metric_record_without_its_own_flag_falls_back_to_the_laws():
    """LAW-7's metrics gate themselves; LAW-9's are shift() records with no `evaluable` key, which exist only
    when the law is evaluable. Requiring the key on both made LAW-9 unreachable in the first pilot run."""
    law9 = [repo("libxml2", "c", **{"LAW-9": {"evaluable": True, "metrics": {
        "files": {"effect": -0.5, "se": 0.2}, "functions": {"effect": -0.1, "se": 0.1},
        "lines": {"effect": -1.0, "se": 0.4}}}})]
    for m in S.METRICS:
        assert RUN._effects(law9, "LAW-9", m), f"{m} should reach the pool"
    not_evaluable = [repo("redis", "c", **{"LAW-9": {"evaluable": False, "metrics": {
        "files": {"effect": -0.5, "se": 0.2}}}})]
    assert RUN._effects(not_evaluable, "LAW-9", "files") == []   # the law's own flag still governs
    # and a metric that gates itself off is still excluded even when the law is evaluable
    mixed = [repo("a", "c", **{"LAW-7": {"evaluable": True, "metrics": {
        "coupling": {"evaluable": True, "effect": 0.9, "se": 0.2},
        "k_mean": {"evaluable": False, "effect": 0.4, "se": 0.1}}}})]
    assert RUN._effects(mixed, "LAW-7", "coupling") and RUN._effects(mixed, "LAW-7", "k_mean") == []
