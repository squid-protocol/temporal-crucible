"""The independent statistic (tools/compare/indep_stat.py, written by a second builder from the registration's
words alone) against the reference statistics module, on stress cases built to make every reading bite.
Written by the reviewing session, which is allowed to read the reference. See docs/process/indep_stat_report.md."""
import importlib.util, math, random
from pathlib import Path
import numpy as np
W = Path(__file__).resolve().parent.parent


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


S = _load("ref_sa3_stats_t", W / "tools" / "sa3_stats.py")          # pure: numpy and scipy only
IS = _load("tools_compare_indep_stat_t", W / "tools" / "compare" / "indep_stat.py")
MATCH = dict(IS.READINGS_PRIOR, n300="in_use")                       # the reading the reference takes


def _case(rng):
    n = rng.choice([rng.randint(23, 299), rng.randint(300, 330), rng.randint(301, 650), rng.randint(280, 320)])
    kind = rng.choice(["tie", "few", "mid", "edge"])
    paths = sorted({f"src/m{rng.randint(0, 3)}/f{rng.randint(0, 99999)}.c" for _ in range(n * 2)})[:n]
    rng.shuffle(paths)
    pick = {"tie": lambda: rng.choice([10, 20, 30, 40, 60, 80, 120]), "edge": lambda: rng.choice([10, 15, 20, 30, 40, 60, 90, 135]),
            "few": lambda: rng.randint(5, 5000), "mid": lambda: rng.randint(5, 400)}[kind]
    sizes = [pick() for _ in paths]
    drop = rng.choice([0, 0, rng.randint(1, 15), rng.randint(1, 40)])
    use = list(range(n)); rng.shuffle(use); use = sorted(use[drop:])
    vals = [float(rng.choice([0, 0, 1, 2, 3, 5, 8])) if rng.random() < 0.6 else round(rng.random() * 10, 1) for _ in paths]
    p = rng.uniform(0.08, 0.4)
    lab = [1 if rng.random() < p * (1 + 0.5 * math.log(s) / 8) else 0 for s in sizes]
    return [{"size": float(sizes[i]), "path": paths[i], "value": vals[i], "label": lab[i]} for i in use], n


def _ref(files):
    loc = np.array([f["size"] for f in files]); y = np.array([f["label"] for f in files]); x = np.array([f["value"] for f in files])
    if y.sum() in (0, len(y)):
        return None
    band, k = S.bands(loc, [f["path"] for f in files])
    d = S.Design(loc, y, band, k, S.CALIPER)
    if not d.clears_pair_floor():
        return None
    e = d.effect(x)
    return None if e != e else float(e)


CASES = [_case(random.Random(20261115 + i)) for i in range(600)]
REFS = [_ref(f) for f, _ in CASES]


def test_matching_reading_equals_reference_bit_for_bit():
    for (f, n), r in zip(CASES, REFS):
        assert IS.effect(f, MATCH, n_ranked=n) == r


def test_every_other_single_reading_differs_somewhere():
    for key, opts in IS.READINGS.items():
        for v in opts:
            if v == MATCH[key]:
                continue
            r = dict(MATCH, **{key: v})
            assert any(IS.effect(f, r, n_ranked=n) != ref for (f, n), ref in zip(CASES, REFS)), (key, v)


def test_the_builders_prior_is_recorded_and_differs_only_in_one_choice():
    assert {k for k in MATCH if MATCH[k] != IS.READINGS_PRIOR[k]} == {"n300"}
