"""LAW-9 on simulated fix commits with a known locality shift, a known null, and the two registered sensitivities."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_security as S  # noqa: E402


def fixes(ratio: float = 0.5, n_cve: int = 60, n_other: int = 400, seed: int = 0, big: int = 0,
          reference_only: int = 0, rewire: float | None = None) -> list[dict]:
    """Fix commits whose sizes are lognormal; a CVE fix's median size is `ratio` times another fix's. `big` CVE
    commits touch more than the 50-file cap; `reference_only` of them are labelled by a commit URL alone."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_cve + n_other):
        cve = i < n_cve
        scale = ratio if cve else 1.0
        lines = float(rng.lognormal(np.log(40 * scale), 0.9))
        rec = {"sha": f"{i:040x}", "ct": 1_600_000_000 + i, "cve": cve,
               "files": int(max(1, rng.lognormal(np.log(3 * scale), 0.6))),
               "functions": int(max(1, rng.lognormal(np.log(4 * scale), 0.7))),
               "lines": int(max(1, lines)), "hunks": 2,
               "signals": ["git-range"] if cve else [], "advisories": ["CVE-2020-0001"] if cve else []}
        if rewire is not None:
            rec["rewire"] = float(rng.normal(rewire if cve else 0.0, 1.0) + 0.01 * rec["lines"])
        out.append(rec)
    for rec in out[:big]:
        rec["files"] = S.FILE_CAP + 10
    for rec in out[n_cve - reference_only:n_cve]:
        rec["signals"] = ["reference"]
    return out


def test_hodges_lehmann_is_the_median_of_the_pairwise_differences():
    assert S.hodges_lehmann([1, 2], [10, 20]) == pytest.approx(np.median([-9, -19, -8, -18]))
    assert np.isnan(S.hodges_lehmann([], [1, 2]))


def test_law9_finds_cve_fixes_smaller_on_all_three_metrics():
    r = S.law9(fixes(ratio=0.5), boot=80)
    assert r["evaluable"] and r["holds"] and r["direction"] == "local" and r["p"] < 0.05
    for metric in S.METRICS:
        m = r["metrics"][metric]
        assert m["effect"] < 0 and m["p"] < 0.05 and m["ci"][1] < 0
        assert m["n_cve"] == 60 and m["n_other"] == 400
    assert r["p"] == max(r["metrics"][m]["p"] for m in S.METRICS)  # intersection-union


def test_law9_reads_equal_sized_fixes_as_not_local():
    r = S.law9(fixes(ratio=1.0, seed=3), boot=80)
    assert r["evaluable"] and not r["holds"] and r["p"] > 0.05
    assert all(abs(r["metrics"][m]["effect"]) < 3 * r["metrics"][m]["se"] for m in S.METRICS)


def test_law9_needs_the_conjunction_not_just_one_metric():
    rows = fixes(ratio=0.4, seed=5)
    for rec in rows:  # lines no longer differ by class; files and functions still do
        rec["lines"] = 40
    r = S.law9(rows, boot=80)
    assert r["metrics"]["files"]["effect"] < 0 and r["metrics"]["files"]["p"] < 0.05
    assert not r["holds"] and r["direction"] == "mixed" and r["p"] == r["metrics"]["lines"]["p"]


def test_law9_is_not_evaluable_below_the_registered_counts():
    assert "fewer than 20 advisory-labelled" in S.law9(fixes(n_cve=19))["why"]
    assert "fewer than 20 other fix commits" in S.law9(fixes(n_other=19))["why"]
    assert S.law9(fixes(n_cve=19))["evaluable"] is False


def test_the_file_cap_sensitivity_drops_the_widest_commits():
    r = S.law9(fixes(ratio=0.5, big=25), boot=60)
    assert r["capped"]["commits"] < r["commits"] and r["capped"]["n_cve"] == r["n_cve"] - 25
    assert r["capped"]["evaluable"] and S.FILE_CAP == 50


def test_the_signal_sensitivity_drops_reference_only_labels():
    r = S.law9(fixes(ratio=0.5, reference_only=15), boot=60)
    assert r["n_cve"] == 60 and r["by_signal"]["n_cve"] == 45
    assert r["by_signal"]["n_other"] == r["n_other"]  # other fixes are never dropped by a label signal


def test_rewiring_says_so_when_no_record_carries_a_rate():
    r = S.rewiring(fixes(), boot=20)
    assert r["available"] is False and "call graph either side" in r["why"]


def test_rewiring_is_matched_on_size_and_pools_the_strata():
    r = S.rewiring(fixes(ratio=1.0, rewire=-1.5, seed=7), boot=40)
    assert r["available"] and r["evaluable"] and r["bins"] == S.SIZE_BINS
    assert r["effect"] < 0 and r["se"] > 0
    assert sum(s["n_cve"] for s in r["strata"]) == 60  # every commit lands in exactly one stratum
    assert all(s["lines_range"][0] <= s["lines_range"][1] for s in r["strata"])


def test_the_confirmatory_gate_keeps_law9_descriptive_at_three_of_eight():
    per_repo = {f"r{i}": {"evaluable": i < 3, "n_cve": 30 if i < 3 else 4, "why": "fewer than 20 advisory-labelled"}
                for i in range(8)}
    g = S.confirmatory_gate(per_repo)
    assert g["class"] == "descriptive" and g["evaluable"] == 3 and g["needed"] == 5
    assert len(g["dropped"]) == 5 and g["kept"] == ["r0", "r1", "r2"] and len(g["cve_fixes"]) == 8
    for i in range(8):
        per_repo[f"r{i}"]["evaluable"] = i < 5
    assert S.confirmatory_gate(per_repo)["class"] == "confirmatory"


def test_the_rank_effect_size_is_reported_where_the_shift_is_degenerate():
    """Tiny tied counts pin the shift at 0 even when the rank test sees a difference (the libxml2 case)."""
    rows = fixes(ratio=0.5, seed=11)
    # 1 file for a CVE fix; most other fixes also touch 1, a minority touch more. Most pairwise differences are
    # then 0, so their median is 0, while the rank test still sees the other class's heavier tail.
    for rec in rows:
        rec["files"] = 1 if rec["cve"] else (1 if rec["ct"] % 5 < 3 else 3)
    m = S.law9(rows, boot=60)["metrics"]["files"]
    assert m["effect"] == 0.0 and m["se"] == 0.0        # the shift cannot express a sub-unit difference
    assert m["p"] < 0.05 and m["p_smaller"] > 0.5       # the rank test and its effect size can
    assert S.shift([1, 1, 1], [1, 1, 1])["p_smaller"] == pytest.approx(0.5)  # no difference at all
