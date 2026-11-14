"""The registry of scorers and gates the two owner-run jobs may call by name (blinding_spec.md, build phase A).

Phase A holds one REFERENCE scorer, for tests: the within-size-decile rank correlation between a measure and
the positive flag, and three reference gates, also for tests only: a size surrogate, a hash placebo and [r3]
the null spread (the reference statistic over k band-only copies beside k directory-preserving copies, the
latter built here, in memory, and never written). None of them is a qualified study gate (checks/ledger.md); SA3's scorer and gates are wired in
when the stored tables exist.

Calling convention, for scorers and gates alike:

    fn(data, params) -> {output_name: scalar}

`data` is {repo: {"files": [{"path", "loc", "measures": {name: value}}], "labels": label_table}}, where
label_table is the structure build_labels encrypts (rows of {"outcome", "path"} plus per-outcome marginals).
The function must not write anything; the job runs it under a guard that stops it if it tries
(jobcore.guarded_call) and accepts only the declared output names, as scalars.
"""
from __future__ import annotations

import hashlib
import math
import statistics

import scramble
from scramble import loc_bands


def _avg_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            ranks[order[t]] = r
        i = j + 1
    return ranks


def _pearson(x, y):
    n = len(x)
    mx = math.fsum(x) / n
    my = math.fsum(y) / n
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.fsum((a - mx) ** 2 for a in x)
    syy = math.fsum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def within_decile_rank_corr(files, positives, measure_of):
    """See within_decile_rank_corr_of; the flag is 1 for a path in `positives`, else 0."""
    pos = set(positives)
    return within_decile_rank_corr_of(files, lambda r: 1.0 if r["path"] in pos else 0.0, measure_of)


def within_decile_rank_corr_of(files, flag_of, measure_of):
    """sum_d n_d * rho_d / sum_d n_d over LOC deciles d in which both the measure and the flag vary; rho_d is
    Spearman's rho (Pearson correlation of average ranks of the measure with the 0/1 flag). Deciles are
    scramble.loc_bands. Files are taken in path order so the floating-point result is reproducible.

    Returns (statistic or None, n_files, n_positive, n_deciles_used)."""
    files = sorted(files, key=lambda r: r["path"])
    band = loc_bands(files)
    by_band = {}
    for r in files:
        by_band.setdefault(band[r["path"]], []).append(r)
    num, den, used = [], [], 0
    for b in sorted(by_band):
        rows = by_band[b]
        x = _avg_ranks([float(measure_of(r)) for r in rows])
        y = [float(flag_of(r)) for r in rows]
        rho = _pearson(x, y)
        if rho is None:
            continue
        num.append(len(rows) * rho)
        den.append(len(rows))
        used += 1
    stat = math.fsum(num) / math.fsum(den) if den else None
    return stat, len(files), sum(1 for r in files if flag_of(r) == 1.0), used


def expected_under_scramble(files, cells, positives, measure_of):
    """The exact expectation, over the scramble's random permutations, of within_decile_rank_corr on the
    scrambled labels. Cells nest inside LOC bands and keep their positive count, so in each band the flag's
    variance is the same in every copy and only the numerator varies; its expectation replaces each file's
    flag by its cell's positive share. Used to measure what the scramble retains without Monte Carlo noise."""
    files = sorted(files, key=lambda r: r["path"])
    pos = set(positives)
    share = {}
    for members in cells.values():
        s = sum(p in pos for p in members) / len(members)
        for p in members:
            share[p] = s
    band = loc_bands(files)
    by_band = {}
    for r in files:
        by_band.setdefault(band[r["path"]], []).append(r)
    num, den = [], []
    for b in sorted(by_band):
        rows = by_band[b]
        x = _avg_ranks([float(measure_of(r)) for r in rows])
        y = [1.0 if r["path"] in pos else 0.0 for r in rows]
        e = [share[r["path"]] for r in rows]
        n = len(rows)
        mx, my = math.fsum(x) / n, math.fsum(y) / n
        sxx = math.fsum((a - mx) ** 2 for a in x)
        syy = math.fsum((c - my) ** 2 for c in y)
        if sxx == 0 or syy == 0:
            continue
        num.append(n * math.fsum((a - mx) * (c - my) for a, c in zip(x, e)) / math.sqrt(sxx * syy))
        den.append(n)
    return math.fsum(num) / math.fsum(den) if den else None


def positives_of(label_table, outcome):
    return [row["path"] for row in label_table["rows"] if row["outcome"] == outcome]


# ------------------------------------------------------------------------------------------------- scorers
def reference_scorer(data, params):
    """REFERENCE scorer (tests only). params: {"outcome", "measure"}. Outputs per repo:
    <repo>.rho, <repo>.n_files, <repo>.n_positive, <repo>.n_deciles_used."""
    out = {}
    for repo in sorted(data):
        d = data[repo]
        stat, n, npos, used = within_decile_rank_corr(
            d["files"], positives_of(d["labels"], params["outcome"]),
            lambda r: r["measures"][params["measure"]])
        out[f"{repo}.rho"] = stat
        out[f"{repo}.n_files"] = n
        out[f"{repo}.n_positive"] = npos
        out[f"{repo}.n_deciles_used"] = used
    return out


# ------------------------------------------------------------------------------------------------- gates
def _overall_rank_corr(files, positives, measure_of):
    files = sorted(files, key=lambda r: r["path"])
    pos = set(positives)
    return _pearson(_avg_ranks([float(measure_of(r)) for r in files]),
                    [1.0 if r["path"] in pos else 0.0 for r in files])


def gate_size_surrogate(data, params):
    """REFERENCE gate (tests only, not qualified): rank correlation of loc with the flag, per repo.
    Output: <repo>.size_rho."""
    return {f"{repo}.size_rho": _overall_rank_corr(data[repo]["files"],
                                                   positives_of(data[repo]["labels"], params["outcome"]),
                                                   lambda r: r["loc"])
            for repo in sorted(data)}


def gate_hash_placebo(data, params):
    """REFERENCE gate (tests only, not qualified): the reference statistic with the measure replaced by a
    hash of the path, which carries no structure. Output: <repo>.placebo_rho."""
    def h(r):
        return int.from_bytes(hashlib.sha256(("placebo:" + r["path"]).encode()).digest()[:8], "big")
    return {f"{repo}.placebo_rho": within_decile_rank_corr(
        data[repo]["files"], positives_of(data[repo]["labels"], params["outcome"]), h)[0]
        for repo in sorted(data)}


def gate_null_spread(data, params):
    """REFERENCE gate (tests only, not qualified), [r3]: how much the reference statistic varies under the
    null. k copies permuted within the LOC band only (what sessions get) and k directory-preserving copies
    (scramble.directory_cells: the Revision 2 cells at a minimum of 20 files, with the 80% rule), both made
    here in memory from the true labels and discarded. params: {"outcome", "measure", "k" (default 20)}.
    Outputs per repo: <repo>.band_only_mean, .band_only_sd, .directory_mean, .directory_sd,
    .directory_cells (number of directory-preserving cells; file table and true labels, a count only)."""
    k = int(params.get("k", scramble.DEFAULT_K))
    out = {}
    for repo in sorted(data):
        files = data[repo]["files"]
        pos = positives_of(data[repo]["labels"], params["outcome"])
        table = [{"path": r["path"], "loc": r["loc"]} for r in files]

        def m(r):
            return r["measures"][params["measure"]]
        for name, cells in (("band_only", scramble.released_cells(table)),
                            ("directory", scramble.directory_cells(table, pos))):
            vals = [within_decile_rank_corr(files, c, m)[0] for c in scramble.scramble(cells, pos, k)]
            vals = [v for v in vals if v is not None]
            out[f"{repo}.{name}_mean"] = statistics.fmean(vals) if vals else None
            out[f"{repo}.{name}_sd"] = statistics.stdev(vals) if len(vals) >= 2 else None
            if name == "directory":
                out[f"{repo}.directory_cells"] = len(cells)
    return out


SCORERS = {"reference_within_decile_rank_corr": reference_scorer}
GATES = {"reference_size_surrogate": gate_size_surrogate, "reference_hash_placebo": gate_hash_placebo,
         "reference_null_spread": gate_null_spread}
