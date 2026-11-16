"""The independent statistic (comparison scorer spec, section 6): a plain loop over pairs, with every reading
of the registration's words as a switch.

Written by the second builder from section 6 of docs/process/comparison_scorer_spec.md alone. The reference
implementation was not read. The builder's prior choice of readings is READINGS_PRIOR below and is explained in
INDEP_STAT_PRIOR.md, which was written before this module was run.

The registration's words:

  1. Bands: equal-count on LOC, 10 if the repo has >= 300 files, else 5; ties broken by path.
  2. Pairs: a (positive, negative) pair is eligible if both files are in the same band and their LOC ratio is
     within 1.5.
  3. bAUC: concordance (ties at half) scored separately on pairs where the positive is the larger file and
     where it is the smaller, the two weighted equally, plus equal-LOC pairs by their share.
     effect = bAUC - 0.5.
  4. Pair floor: >= 100 eligible pairs, >= 25 on each side.

Interface:

    effect(files, readings, n_ranked=None, ranked=None, min_pairs=100, min_side=25) -> float | None

`files` is the files in use (files with a missing value already dropped): a list of mappings with "size",
"path", "value" and "label" (label 1 / True = positive). `readings` is a mapping with one value for each of
the seven keys in READINGS (and, optionally, the extra keys in EXTRA_READINGS). None means "no value".

`n_ranked` is the number of ranked files of the repo, which only the reading n300="ranked" uses. The files in
use cannot say how many files were dropped, so the caller must pass it; when it is not passed, the count of
the files in use is taken (correct only if no file was dropped, and then the two readings of that choice
cannot differ -- pass n_ranked whenever the two are to be told apart).
"""
from __future__ import annotations

import math
import re

# ---------------------------------------------------------------------------------------------- the switches
# The seven choices of section 6, each with the readings its table lists. Values marked (extra) are readings
# the table does not list; see the builder's report.
READINGS = {
    # a remainder when files do not divide evenly into bands (n files in rank order, k bands, rank from 0)
    "remainder": (
        "ceil_chunks",    # chunks of ceil(n / k), a short last band (and perhaps fewer than k bands)
        "first_extra",    # sizes floor(n / k); the first n mod k bands take one extra file
        "quantile",       # cut points at size quantiles, equal sizes sharing a band; a size equal to a cut
                          # point belongs to the band below it
        "floor_rank",     # band = floor(rank * k / n)
        "last_extra",     # sizes floor(n / k); the last n mod k bands take one extra file
        "floor_chunks",   # chunks of floor(n / k), the last band taking the rest
        "quantile_left",  # (extra) as "quantile", but a size equal to a cut point belongs to the band above
    ),
    # "within 1.5"
    "ratio": (
        "strict",         # larger < 1.5 * smaller
        "inclusive",      # larger <= 1.5 * smaller
    ),
    # "plus equal-LOC pairs by their share"; cL, cS, cE = concordance where the positive is larger, smaller,
    # of equal size; share = equal-size pairs / all eligible pairs
    "equal": (
        "three_equal",              # (cL + cS + cE) / 3
        "mean_plus_share",          # (cL + cS) / 2 + share * cE
        "half_each_side",           # each equal-size pair joins both sides with weight one half; then the
                                    # mean of the two sides
        "weighted",                 # (1 - share) * (cL + cS) / 2 + share * cE
        "mean_plus_share_centred",  # (cL + cS) / 2 + share * (cE - 0.5)
    ),
    # pooled or per band
    "pooling": (
        "per_band_equal",  # the formula inside each band, bands weighted equally
        "pooled",          # one formula over all eligible pairs
        "per_band_pairs",  # the formula inside each band, bands weighted by their eligible pairs
    ),
    # ">= 100 eligible pairs"
    "floor": (
        "equal_excluded",  # equal-size pairs do not count toward the 100
        "equal_counts",    # they do
    ),
    # "the repo has >= 300 files"
    "n300": (
        "ranked",          # the repo's ranked files (n_ranked)
        "in_use",          # the files in use for this predictor (len(files))
    ),
    # "ties broken by path"
    "tiebreak": (
        "natural",         # digits compared as numbers
        "string",          # Python string order
    ),
}

# Choices the table does not list, which the words also leave open. Each is optional in `readings`; the first
# value is the default.
EXTRA_READINGS = {
    # which files are banded
    "band_universe": (
        "in_use",          # the files in use are ranked and banded (the interface of section 6)
        "ranked",          # all the repo's ranked files are banded, then the files in use keep their band;
                           # needs `ranked`, a list of mappings with "size" and "path"
    ),
    # a band (or the pool) in which one side has no pair, so that the formula has no value there
    "empty_side": (
        "skip",            # per band: the band is left out; pooled: no value
        "present",         # the side that exists stands for the mean of the two sides
        "none",            # the whole statistic has no value
    ),
}

# The second builder's prior: the reading judged the plain meaning of the words (INDEP_STAT_PRIOR.md).
READINGS_PRIOR = {
    "remainder": "floor_rank",
    "ratio": "inclusive",
    "equal": "weighted",
    "pooling": "pooled",
    "floor": "equal_counts",
    "n300": "ranked",
    "tiebreak": "string",
}

MIN_PAIRS = 100
MIN_SIDE = 25
RATIO = 1.5
MANY_FILES = 300
BANDS_MANY = 10
BANDS_FEW = 5


def all_combinations(extra: bool = False):
    """Every combination of readings, as dicts (the seven choices; with extra=True the extra choices too)."""
    import itertools
    table = dict(READINGS)
    if extra:
        table.update(EXTRA_READINGS)
    keys = list(table)
    for values in itertools.product(*(table[k] for k in keys)):
        yield dict(zip(keys, values))


# ------------------------------------------------------------------------------------------------- ordering
_DIGITS = re.compile(r"(\d+)")


def _natural_key(path: str):
    """Digits as numbers: 'a2' before 'a10'. Parts alternate text, number, text ..., so keys compare cleanly.
    The path itself is the last resort (for 'a01' against 'a1')."""
    parts = _DIGITS.split(path)
    key = []
    for i, part in enumerate(parts):
        key.append(int(part) if i % 2 else part)
    return (key, path)


def _rank_order(items, tiebreak: str):
    """items: list of (size, path). Returns the indices in rank order: by size, ties by path."""
    if tiebreak == "natural":
        return sorted(range(len(items)), key=lambda i: (items[i][0], _natural_key(items[i][1])))
    if tiebreak == "string":
        return sorted(range(len(items)), key=lambda i: (items[i][0], items[i][1]))
    raise ValueError(f"tiebreak: unknown reading {tiebreak!r}")


# -------------------------------------------------------------------------------------------------- banding
def _quantile(sorted_sizes, q: float) -> float:
    """Linear interpolation between order statistics (the common default definition)."""
    n = len(sorted_sizes)
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_sizes[lo] + (sorted_sizes[hi] - sorted_sizes[lo]) * frac


def bands_of(items, k: int, remainder: str, tiebreak: str):
    """items: list of (size, path). Returns the band of each item, in the order given."""
    n = len(items)
    band = [0] * n
    if n == 0:
        return band
    order = _rank_order(items, tiebreak)

    if remainder in ("quantile", "quantile_left"):
        sizes = sorted(float(s) for s, _ in items)
        cuts = [_quantile(sizes, j / k) for j in range(1, k)]
        for i in range(n):
            s = float(items[i][0])
            if remainder == "quantile":
                band[i] = sum(1 for c in cuts if c < s)     # a size on a cut point stays below it
            else:
                band[i] = sum(1 for c in cuts if c <= s)    # a size on a cut point goes above it
        return band

    q, r = divmod(n, k)
    for rank, i in enumerate(order):
        if remainder == "ceil_chunks":
            b = rank // int(math.ceil(n / k))
        elif remainder == "floor_chunks":
            b = min(rank // q, k - 1) if q > 0 else k - 1
        elif remainder == "floor_rank":
            b = (rank * k) // n
        elif remainder == "first_extra":
            # the first r bands hold q + 1 files, the rest q
            b = rank // (q + 1) if rank < r * (q + 1) else r + (rank - r * (q + 1)) // q
        elif remainder == "last_extra":
            # the first k - r bands hold q files, the rest q + 1
            b = rank // q if rank < (k - r) * q else (k - r) + (rank - (k - r) * q) // (q + 1)
        else:
            raise ValueError(f"remainder: unknown reading {remainder!r}")
        band[i] = b
    return band


# ------------------------------------------------------------------------------------------------ the formula
class _Tally:
    """Counts and concordance sums of the eligible pairs of one unit (one band, or the pool)."""

    def __init__(self):
        self.n_larger = 0      # pairs where the positive is the larger file
        self.n_smaller = 0     # pairs where the positive is the smaller file
        self.n_equal = 0       # pairs of equal size
        self.s_larger = 0.0    # sums of concordance: 1 if the positive's value is higher, 0.5 if tied, else 0
        self.s_smaller = 0.0
        self.s_equal = 0.0

    def add(self, other: "_Tally") -> None:
        self.n_larger += other.n_larger
        self.n_smaller += other.n_smaller
        self.n_equal += other.n_equal
        self.s_larger += other.s_larger
        self.s_smaller += other.s_smaller
        self.s_equal += other.s_equal

    @property
    def n_all(self) -> int:
        return self.n_larger + self.n_smaller + self.n_equal


_NO_SIDE = object()   # the formula has no value because a side has no pair


def _bauc(t: _Tally, equal: str, empty_side: str):
    """bAUC of one unit under a reading of the equal-size rule. Returns a float, or _NO_SIDE."""
    if equal == "half_each_side":
        w_l = t.n_larger + 0.5 * t.n_equal
        w_s = t.n_smaller + 0.5 * t.n_equal
        sides = []
        if w_l > 0:
            sides.append((t.s_larger + 0.5 * t.s_equal) / w_l)
        if w_s > 0:
            sides.append((t.s_smaller + 0.5 * t.s_equal) / w_s)
        if len(sides) == 2 or (sides and empty_side == "present"):
            return sum(sides) / len(sides)
        return _NO_SIDE

    sides = []
    if t.n_larger > 0:
        sides.append(t.s_larger / t.n_larger)
    if t.n_smaller > 0:
        sides.append(t.s_smaller / t.n_smaller)
    if len(sides) < 2 and not (sides and empty_side == "present"):
        return _NO_SIDE
    two = sum(sides) / len(sides)
    if t.n_equal == 0:
        return two                       # no equal-size pairs: every reading is the mean of the two sides
    c_e = t.s_equal / t.n_equal
    share = t.n_equal / t.n_all
    if equal == "three_equal":
        return (sum(sides) + c_e) / (len(sides) + 1)
    if equal == "mean_plus_share":
        return two + share * c_e
    if equal == "weighted":
        return (1.0 - share) * two + share * c_e
    if equal == "mean_plus_share_centred":
        return two + share * (c_e - 0.5)
    raise ValueError(f"equal: unknown reading {equal!r}")


# ------------------------------------------------------------------------------------------------ the effect
def _check(readings) -> dict:
    out = {}
    for key, values in READINGS.items():
        if key not in readings:
            raise ValueError(f"readings: {key!r} is missing")
        if readings[key] not in values:
            raise ValueError(f"readings: {key}={readings[key]!r} is not one of {values}")
        out[key] = readings[key]
    for key, values in EXTRA_READINGS.items():
        out[key] = readings.get(key, values[0])
        if out[key] not in values:
            raise ValueError(f"readings: {key}={out[key]!r} is not one of {values}")
    unknown = set(readings) - set(out)
    if unknown:
        raise ValueError(f"readings: unknown keys {sorted(unknown)}")
    return out


def tallies(files, readings, n_ranked=None, ranked=None):
    """The per-band tallies of eligible pairs: {band: _Tally}. Exposed for tests and reports."""
    r = _check(readings)
    n_in_use = len(files)
    if r["n300"] == "ranked":
        n_for_k = n_ranked if n_ranked is not None else (len(ranked) if ranked is not None else n_in_use)
    else:
        n_for_k = n_in_use
    k = BANDS_MANY if n_for_k >= MANY_FILES else BANDS_FEW

    if r["band_universe"] == "ranked":
        if ranked is None:
            raise ValueError("band_universe='ranked' needs the repo's ranked files (ranked=[{size, path}, ...])")
        universe = [(f["size"], f["path"]) for f in ranked]
        by_path = dict(zip((p for _, p in universe), bands_of(universe, k, r["remainder"], r["tiebreak"])))
        band = [by_path[f["path"]] for f in files]
    else:
        band = bands_of([(f["size"], f["path"]) for f in files], k, r["remainder"], r["tiebreak"])

    positives, negatives = {}, {}
    for i, f in enumerate(files):
        (positives if f["label"] else negatives).setdefault(band[i], []).append(f)

    out = {}
    for b in sorted(set(positives) & set(negatives)):
        t = _Tally()
        for p in positives[b]:
            for q in negatives[b]:
                sp, sq = p["size"], q["size"]
                if sp == sq:
                    side = "equal"
                else:
                    big, small = (sp, sq) if sp > sq else (sq, sp)
                    if r["ratio"] == "inclusive":
                        ok = big <= RATIO * small
                    else:
                        ok = big < RATIO * small
                    if not ok:
                        continue
                    side = "larger" if sp > sq else "smaller"
                vp, vq = p["value"], q["value"]
                c = 1.0 if vp > vq else (0.5 if vp == vq else 0.0)
                if side == "equal":
                    t.n_equal += 1
                    t.s_equal += c
                elif side == "larger":
                    t.n_larger += 1
                    t.s_larger += c
                else:
                    t.n_smaller += 1
                    t.s_smaller += c
        if t.n_all:
            out[b] = t
    return out


def effect(files, readings, n_ranked=None, ranked=None, min_pairs=MIN_PAIRS, min_side=MIN_SIDE):
    """effect = bAUC - 0.5 under the given readings, or None ("no value").

    None when there is no positive or no negative, when the pair floor is not met, or when the formula has no
    value (see EXTRA_READINGS["empty_side"])."""
    r = _check(readings)
    files = list(files)
    if not any(f["label"] for f in files) or all(f["label"] for f in files):
        return None

    per_band = tallies(files, r, n_ranked=n_ranked, ranked=ranked)
    pool = _Tally()
    for t in per_band.values():
        pool.add(t)

    # the pair floor, on the totals over all bands
    counted = pool.n_all if r["floor"] == "equal_counts" else pool.n_larger + pool.n_smaller
    if counted < min_pairs or pool.n_larger < min_side or pool.n_smaller < min_side:
        return None

    if r["pooling"] == "pooled":
        b = _bauc(pool, r["equal"], r["empty_side"])
        return None if b is _NO_SIDE else b - 0.5

    total, weight = 0.0, 0.0
    for band in sorted(per_band):
        t = per_band[band]
        b = _bauc(t, r["equal"], r["empty_side"])
        if b is _NO_SIDE:
            if r["empty_side"] == "none":
                return None
            continue
        w = 1.0 if r["pooling"] == "per_band_equal" else float(t.n_all)
        total += w * b
        weight += w
    if weight == 0:
        return None
    return total / weight - 0.5
