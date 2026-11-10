"""LAWS synthesis rules against published reference values and the registration's own numbers."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_synth as S  # noqa: E402

# Colditz et al. 1994 BCG trials, log risk ratios and variances (metafor's dat.bcg); metafor reports
# DL tau^2 0.3088, REML tau^2 0.3132, REML estimate -0.7145 (model-based SE 0.1798)
BCG_Y = [-0.8893, -1.5854, -1.3481, -1.4416, -0.2175, -0.7861, -1.6209, 0.0120, -0.4694, -1.3713, -0.3394, 0.4459, -0.0173]
BCG_V = [0.3256, 0.1946, 0.4154, 0.0200, 0.0512, 0.0069, 0.2230, 0.0040, 0.0564, 0.0730, 0.0124, 0.5325, 0.0714]


def test_tau2_matches_the_published_bcg_values():
    assert S.tau2_dl(BCG_Y, BCG_V) == pytest.approx(0.3088, abs=0.002)
    assert S.tau2_reml(BCG_Y, BCG_V) == pytest.approx(0.3132, abs=0.002)
    assert 0.25 < S.tau2_pm(BCG_Y, BCG_V) < 0.40  # Paule-Mandel is the fallback only; same order as REML


def test_pool_gives_the_reml_estimate_and_a_hartung_knapp_interval_no_narrower_than_dl():
    p = S.pool(BCG_Y, BCG_V)
    assert p["tau2_method"] == "REML" and p["mu"] == pytest.approx(-0.7145, abs=0.002)
    assert p["se"] >= 0.1798 - 0.002  # the ad-hoc correction never goes below the model-based SE
    half, dl_half = (p["ci99"][1] - p["ci99"][0]) / 2, (p["dl"]["ci99"][1] - p["dl"]["ci99"][0]) / 2
    assert half >= dl_half - 1e-12
    assert p["pi95"][0] < p["ci99"][0] and p["pi95"][1] > p["ci99"][1]  # a prediction interval is wider


def test_identical_effects_pool_to_themselves_with_no_heterogeneity():
    p = S.pool([0.5] * 6, [0.04] * 6)
    assert p["mu"] == pytest.approx(0.5) and p["tau2"] == 0 and p["I2_at_tau2"] == 0


def test_one_sided_p_follows_the_margin_and_the_direction():
    p = S.pool([0.9, 1.1, 1.0, 0.95, 1.05, 1.0, 0.9, 1.1], [0.01] * 8)
    assert S.one_sided_p(p) < 1e-6  # against 0, predicted positive
    assert S.one_sided_p(p, margin=0.5) < 1e-4  # LAW-7's margin
    assert S.one_sided_p(p, margin=1.5) > 0.99 and S.one_sided_p(p, direction=-1) > 0.99


def test_tost_declares_equivalence_only_inside_the_margin():
    near = S.pool([0.005, -0.004, 0.002, 0.0, -0.003, 0.004, 0.001, -0.002], [1e-5] * 8)
    far = S.pool([0.05, 0.06, 0.04, 0.05, 0.055, 0.045, 0.05, 0.05], [1e-5] * 8)
    assert S.tost_p(near, 0.02) < 0.01 and S.tost_p(far, 0.02) > 0.5  # LAW-8's margin


def test_partial_conjunction_is_the_registered_formula():
    assert S.partial_conjunction([0.001, 0.002, 0.003, 1.0], 3) == pytest.approx(2 * 0.003)  # p^{3/4} = 2 p_(3) (M2)
    assert S.partial_conjunction([0.001, 0.002, 1.0, 1.0], 3) == 1.0  # two failed languages: no law can be universal
    ps = [0.0001 * i for i in range(1, 11)]
    assert S.extended_r(10) == 7 and S.partial_conjunction(ps, 7) == pytest.approx(4 * 0.0007)  # (n-r+1) p_(r)
    with pytest.raises(ValueError):
        S.partial_conjunction([0.1], 2)


def test_holm_stops_at_the_first_p_above_its_step():
    got = S.holm({"a": 0.0005, "b": 0.0012, "c": 0.004, "d": 0.5}, alpha=0.01)  # steps 0.0025, 0.0033, 0.005, 0.01
    assert got == {"a": True, "b": True, "c": True, "d": False}
    assert S.holm({"a": 0.003, "b": 0.0001}, alpha=0.01) == {"b": True, "a": True}
    assert S.holm({"a": 0.006, "b": 0.02}, alpha=0.01) == {"a": False, "b": False}


def test_universal_counts_a_failed_language_against_and_blocks_on_an_opposite_one():
    langs = ["c", "java", "go", "python", "cpp", "rust", "jsts", "csharp", "kotlin", "php"]
    strong = {lang: 1e-6 for lang in langs}
    laws = {"LAW-1": strong, "LAW-2": {**strong, "go": 1.0}, "LAW-3": {**strong, "go": 1.0, "python": 1.0}}
    out = S.universal(laws, {"LAW-1": {"rust": 0.001}}, langs)
    assert out["LAW-2"]["primary_universal"] and not out["LAW-3"]["primary_universal"]  # 3 of 4 is enough, 2 of 4 is not
    assert out["LAW-3"]["primary_p"] == 1.0 and out["LAW-3"]["extended_universal"]  # 8 of 10 still passes the extended test
    assert out["LAW-1"]["primary_universal"] and not out["LAW-1"]["extended_universal"]  # rust opposite: extended only
    assert out["LAW-1"]["opposite_languages"] == ["rust"] and out["LAW-1"]["extended_r_of_n"] == [7, 10]


def test_pool_refuses_what_it_cannot_pool():
    for y, v in (([1.0], [0.1]), ([1.0, 2.0], [0.1, 0.0]), ([1.0, math.nan], [0.1, 0.1])):
        with pytest.raises(ValueError):
            S.pool(y, v)
