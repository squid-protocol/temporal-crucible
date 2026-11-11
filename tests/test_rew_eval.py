"""REW scorer: the pure functions, and the constants the registration pins."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import rew_eval as R  # noqa: E402


def test_constants_match_the_approved_registration():
    # Changing any of these needs an amendment, not a new expected value.
    assert R.WINDOW == 180 * 86400
    assert R.ALPHA == 0.01 and R.ALPHA_H2 == 0.01 / 4      # Bonferroni across the four fix classes
    assert R.MIN_POS == 20                                 # the >= 20-positive rule
    assert R.EQUIV == 0.02                                 # REW-H4 delta, fixed before any statistic
    assert R.SEED == 2982
    assert R.PRIMARY == "curl" and R.H12_REP == "libarchive" and R.H3_REP == "openssl"
    assert set(R.REG_PARTS) == {"regression", "regression-linked"}   # Amendment 1 item 3


def test_recall20_counts_positives_inside_a_20_percent_line_budget():
    loc = np.array([10.0] * 10)
    pr = np.arange(10)
    pos = np.array([1.0, 1.0] + [0.0] * 8)
    assert R.recall20(np.array([9.0, 8.0] + [0.1] * 8), loc, pr, pos) == 1.0
    assert R.recall20(np.array([0.1, 0.2] + [9.0] * 8), loc, pr, pos) == 0.0


def test_recall20_lets_a_big_function_eat_the_budget():
    loc = np.array([100.0] + [10.0] * 10)
    pr = np.arange(11)
    pos = np.array([1.0] + [0.0] * 10)
    assert R.recall20(np.array([9.0] + [0.5] * 10), loc, pr, pos) == 0.0


def test_rename_chain_is_followed_to_the_final_path():
    fwd = {"a.c": "b.c", "b.c": "c.c"}
    assert R.canon("a.c", fwd) == "c.c"
    assert R.canon("z.c", fwd) == "z.c"


def test_rename_cycle_terminates():
    assert R.canon("a.c", {"a.c": "b.c", "b.c": "a.c"}) in {"a.c", "b.c"}


def test_boot_is_seed_stable_and_one_sided_lower_bound_is_below_the_mean():
    mean, lo, ci = R.boot([0.1, 0.2, 0.15, 0.12, 0.18], np.random.default_rng(R.SEED), R.ALPHA)
    assert abs(mean - 0.15) < 1e-9
    assert lo < mean and ci[0] < ci[1]
    again, lo2, _ = R.boot([0.1, 0.2, 0.15, 0.12, 0.18], np.random.default_rng(R.SEED), R.ALPHA)
    assert (again, lo2) == (mean, lo)


def test_verdict_requires_both_a_positive_mean_and_a_positive_lower_bound():
    assert R.verdict_one_sided(0.05, 0.01) == "SUPPORTED"
    assert R.verdict_one_sided(0.05, -0.01) == "not supported"
    assert R.verdict_one_sided(-0.05, -0.10) == "not supported"
