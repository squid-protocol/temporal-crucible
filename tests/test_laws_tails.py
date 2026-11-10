"""LAW-1 tail fits on synthetic degree sequences with known answers."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import laws_tails as T  # noqa: E402


@pytest.fixture(scope="module")
def power_law():
    return T._pl_sample(np.random.default_rng(7), 6000, 2.5, 1)


@pytest.fixture(scope="module")
def geometric():
    return np.random.default_rng(7).geometric(0.25, 6000).astype(float)  # light-tailed: support 1, 2, ...


def test_the_sampler_draws_the_discrete_power_law(power_law):
    from scipy import special
    assert power_law.min() == 1
    for k in (1, 2, 5):  # P(X = k) = k^-alpha / zeta(alpha)
        assert np.mean(power_law == k) == pytest.approx(k ** -2.5 / special.zeta(2.5, 1), abs=0.015)


def test_csn_recovers_alpha_and_the_fit_is_not_rejected(power_law):
    r = T.fit(power_law, boot=60)
    assert r["evaluable"] and r["alpha"] == pytest.approx(2.5, abs=0.12) and r["xmin"] <= 3
    assert r["gof_p"] >= 0.1 and r["strength"] in ("weak", "strong") and r["coverage_ok"]
    assert r["vuong_power_law_vs"]["exponential"]["R"] > 0 and r["vuong_power_law_vs"]["exponential"]["p"] < 0.01
    assert r["effect_vs_exponential"] > 5 * r["se_vs_exponential"] > 0  # a heavy tail beats the exponential clearly
    assert r["effect"] > 0 and r["better_heavy"] in T.HEAVY


def test_a_light_tail_shows_no_effect_against_the_negative_binomial(geometric):
    r = T.fit(geometric, boot=60)
    assert r["evaluable"]
    # the geometric is a negative binomial (r = 1): no heavy family may beat the baseline by more than noise, which
    # is the point of testing against it and not against the exponential (methods review M5)
    assert r["effect"] < 2.6 * r["se"] + 1e-3
    assert r["vuong_power_law_vs"]["exponential"]["R"] < 0  # the power law itself fits worse than the exponential


def test_too_small_a_sequence_is_not_evaluable():
    r = T.fit([1, 1, 2, 3, 5, 8] * 5)
    assert not r["evaluable"] and r["n"] == 30 and "tail of 50" in r["why"]
    assert not T.fit([0, 0, 0])["evaluable"]


def test_every_family_is_a_probability_distribution_on_the_tail():
    v = np.arange(3, 60000, dtype=float)
    for name, p in {"power_law": (2.3,), "exponential": (0.2,), "lognormal": (0.5, 1.2), "stretched_exponential": (0.1, 0.6),
                    "truncated_power_law": (1.8, 0.01), "negative_binomial": (0.7, 0.1)}.items():
        total = float(np.exp(T.FAMILIES[name][1](p, v, 3.0)).sum())
        assert total == pytest.approx(1.0, abs=2e-3), name


def test_the_fit_is_reproducible(power_law):
    a, b = T.fit(power_law[:1500], boot=30), T.fit(power_law[:1500], boot=30)
    assert a["se"] == b["se"] and a["gof_p"] == b["gof_p"]  # seed 2982
