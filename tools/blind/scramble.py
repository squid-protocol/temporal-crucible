"""Scrambled labels: positives re-assigned among files within cells (docs/process/blinding_spec.md, layer 2).

[r3] What is RELEASED (labels/<repo>.scrambled.json) is permuted within the LOC band only -> released_cells,
scramble_outcome. Rule 5 still applies: under 2% of true positives positive in all copies, or the repo's
scrambles are withheld and the reason written. A session can learn from them the number of positives in each
size band, and nothing about directories.

The Revision 2 directory-preserving cells are kept as code, used only inside the owner-run gates job, in
memory, never written (registry.gate_null_spread), with a minimum of DIRECTORY_MIN_CELL (20) files:

1. Cells start as LOC band x full directory.
2. A cell with fewer than min_cell files shortens its directory one level at a time, down to the band alone.
   File table only; no label is read.                                                -> cells_from_file_table
4. A cell still more than 80% positive is merged up one more level (reads labels).    -> merge_dense
(Rule 3, the per-repo cell report, now describes the released band-only cells: cell_report.)

The permutation uses random.SystemRandom (os.urandom). Nothing about it is seeded, stored or returned except
the scrambled copies themselves. See DECISIONS.md for every choice the specification left open.
"""
from __future__ import annotations

import bisect
import random

N_BANDS = 10
R2_MIN_CELL = 8               # Revision 2's minimum; kept so tests can show it leaks
DIRECTORY_MIN_CELL = 20       # [r3] the directory-preserving scramble of the gates job
DENSE_SHARE = 0.8            # rule 4: "more than 80% positive"
ALL_COPIES_LIMIT = 0.02      # rule 5: "under 2%"
DEFAULT_K = 20
CELL_RULE = ("r3: positives permuted within the LOC band only (rank deciles of loc; ties share a band); "
             "directory is not preserved; the number of positives in each band is kept; released only if under "
             "2% of true positives are positive in all copies")
DIRECTORY_RULE = ("r2 cells, minimum 20 files: LOC decile x full directory, a cell under 20 files shortens its "
                  "directory one level at a time down to the band alone, a band-alone remainder under 20 takes "
                  "the whole band, a cell over 80% positive merges up one more level; gates job only, in memory")
SIZE_CLASSES = ((1, 1), (2, 7), (8, 15), (16, 31), (32, 63), (64, None))


# ------------------------------------------------------------------------------------------------- bands
def loc_bands(file_table, n_bands=N_BANDS):
    """{path: band}. band = floor(n_bands * (#files with strictly smaller loc) / n): rank deciles in which
    files of equal loc always share a band. Uses path and loc only."""
    locs = sorted(int(r["loc"]) for r in file_table)
    n = len(locs)
    out = {}
    for r in file_table:
        below = bisect.bisect_left(locs, int(r["loc"]))
        out[r["path"]] = min(n_bands - 1, (n_bands * below) // n)
    return out


def _dirname(path):
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _parent(d):
    return d.rsplit("/", 1)[0] if "/" in d else ""


def _depth(d):
    return 0 if d == "" else d.count("/") + 1


def _under(d, top):
    """True if directory d is top itself or lies below it ('' is above everything)."""
    return top == "" or d == top or d.startswith(top + "/")


def _check_table(file_table):
    paths = [r["path"] for r in file_table]
    if len(set(paths)) != len(paths):
        raise ValueError("file table has duplicate paths")
    if not paths:
        raise ValueError("file table is empty")


# ------------------------------------------------------------------------------------------------- cells
def cells_first_version(file_table):
    """The FIRST version's cells (band x full directory, no merging). Kept only so tests can show it leaks."""
    _check_table(file_table)
    band = loc_bands(file_table)
    cells = {}
    for r in file_table:
        cells.setdefault((band[r["path"]], _dirname(r["path"])), []).append(r["path"])
    return {k: sorted(v) for k, v in cells.items()}


def _collapse(cells, key):
    """Merge every cell of key's band whose directory lies at or below key's directory into one cell at key."""
    b, top = key
    members = [k for k in cells if k[0] == b and _under(k[1], top)]
    merged = []
    for k in members:
        merged.extend(cells.pop(k))
    cells[key] = sorted(merged)
    return len(members)


def released_cells(file_table):
    """[r3] The cells of the RELEASED scramble: one per LOC band, {(band, ""): [paths]}. File table only."""
    _check_table(file_table)
    band = loc_bands(file_table)
    cells = {}
    for r in file_table:
        cells.setdefault((band[r["path"]], ""), []).append(r["path"])
    return {k: sorted(v) for k, v in cells.items()}


def directory_cells(file_table, positives, min_cell=DIRECTORY_MIN_CELL):
    """[r3] The directory-preserving cells (rules 1, 2 and 4 at minimum min_cell). Reads true labels: for the
    gates job only, in memory. Returns {(band, directory): [paths]}."""
    return merge_dense(cells_from_file_table(file_table, min_cell), positives)[0]


def cells_from_file_table(file_table, min_cell=DIRECTORY_MIN_CELL):
    """Rules 1 and 2. {(band, directory): [paths]}. Reads path and loc only.

    While some cell has fewer than min_cell files and a directory to shorten, take the deepest such cell
    (ties: smallest band, then directory, so the result is a function of the file table alone) and shorten
    its directory by one level: it joins the cell of its parent directory in the same band (files sitting
    directly in that directory, and small siblings that moved up before it), or becomes that cell. Siblings
    with min_cell files or more keep their own cells. The parent of a top-level directory is the band alone.

    Residual: if the band-alone cell of a band is still below min_cell while the band has other cells, the
    whole band collapses into one cell (the band alone). So a cell has fewer than min_cell files only if it
    is its entire band. (DECISIONS.md 3.)"""
    cells = cells_first_version(file_table)
    while True:
        small = [k for k, v in cells.items() if len(v) < min_cell and k[1] != ""]
        if not small:
            break
        b, d = min(small, key=lambda k: (-_depth(k[1]), k[0], k[1]))
        members = cells.pop((b, d))
        cells[(b, _parent(d))] = sorted(cells.get((b, _parent(d)), []) + members)
    for b in sorted({k[0] for k in cells}):
        if (b, "") in cells and len(cells[(b, "")]) < min_cell and any(k[0] == b and k[1] for k in cells):
            _collapse(cells, (b, ""))
    return cells


def merge_dense(cells, positives, share=DENSE_SHARE):
    """Rule 4 (builder only: reads true labels). Returns (new_cells, n_merges, n_unmergeable).

    One pass over the rule-2 cells: every cell more than `share` positive is merged up one more level
    (its sibling subtree under the parent directory collapses into one cell; for a cell already at the band
    alone there is no level above, and it is counted as unmergeable). Collapses are applied deepest first; a
    dense cell already swallowed by an earlier collapse has been merged up and is not collapsed again."""
    pos = set(positives)
    cells = {k: list(v) for k, v in cells.items()}
    dense = sorted((k for k, v in cells.items() if sum(p in pos for p in v) > share * len(v)),
                   key=lambda k: (-_depth(k[1]), k[0], k[1]))
    n_merges = n_unmergeable = 0
    for k in dense:
        if k not in cells:                      # absorbed by an earlier collapse
            continue
        if k[1] == "":
            n_unmergeable += 1
            continue
        _collapse(cells, (k[0], _parent(k[1])))
        n_merges += 1
    return cells, n_merges, n_unmergeable


# ------------------------------------------------------------------------------------------------- scramble
def scramble(cells, positives, k=DEFAULT_K):
    """k independent copies. In each, every cell receives exactly as many positives as it holds in truth,
    placed on files drawn uniformly without replacement by random.SystemRandom. Returns a list of k sorted
    path lists. Raises if a positive is not in any cell."""
    pos = set(positives)
    in_cells = set()
    for v in cells.values():
        in_cells.update(v)
    if not pos <= in_cells:
        raise ValueError(f"{len(pos - in_cells)} positive path(s) are not in the file table")
    rng = random.SystemRandom()
    counts = [(sorted(v), sum(p in pos for p in v)) for _key, v in sorted(cells.items())]
    copies = []
    for _ in range(k):
        chosen = []
        for members, c in counts:
            if c:
                chosen.extend(rng.sample(members, c))
        copies.append(sorted(chosen))
    return copies


# ------------------------------------------------------------------------------------------------- measures
def leak_measures(cells, positives, copies):
    """The two leak measures of the specification. Computed inside the builder; see release_decision for
    what of it may be written."""
    n_files = sum(len(v) for v in cells.values())
    alone = sum(len(v) for v in cells.values() if len(v) == 1)
    pos = set(positives)
    if copies:
        in_all = set(copies[0]).intersection(*map(set, copies[1:]))
    else:
        in_all = set()
    n_pos_all = len(pos & in_all)
    return {"n_files": n_files, "share_alone": alone / n_files if n_files else 0.0,
            "n_positives": len(pos), "n_positives_in_all_copies": n_pos_all,
            "share_positives_in_all_copies": (n_pos_all / len(pos)) if pos else 0.0}


def release_decision(measures, k, limit=ALL_COPIES_LIMIT):
    """Rule 5. Returns (released, written): `written` is what may go into the report.

    When the scrambles are released, the exact count is NOT written: the set of files positive in all copies
    is visible in the released copies, and the exact number of true positives among them would tell which
    of them are positive (all of them when it equals the set's size, none when it is 0). When they are
    withheld the exact share is the stated reason and nothing it could be combined with is released."""
    share = measures["share_positives_in_all_copies"]
    if share < limit:
        return True, {"released": True,
                      "share_true_positives_positive_in_all_copies": f"< {limit}"}
    return False, {"released": False,
                   "share_true_positives_positive_in_all_copies": share,
                   "reason": f"{measures['n_positives_in_all_copies']} of {measures['n_positives']} true "
                             f"positives are positive in all {k} copies "
                             f"(share {share:.4f}, limit {limit}): the scramble keeps too many labels in "
                             f"place; scrambles for this repo are not released"}


def cell_report(cells):
    """Rule 3, for the released band-only cells (file table only): the number of cells, the share of files per
    cell-size class, and the depth cells ended at (0 for every band-only cell). Nothing derived from labels."""
    n_files = sum(len(v) for v in cells.values())
    classes = {}
    for lo, hi in SIZE_CLASSES:
        name = f"{lo}" if lo == hi else (f"{lo}+" if hi is None else f"{lo}-{hi}")
        files = sum(len(v) for v in cells.values() if len(v) >= lo and (hi is None or len(v) <= hi))
        classes[name] = round(files / n_files, 6)
    depth_cells, depth_files = {}, {}
    for (_b, d), v in cells.items():
        depth_cells[str(_depth(d))] = depth_cells.get(str(_depth(d)), 0) + 1
        depth_files[str(_depth(d))] = depth_files.get(str(_depth(d)), 0) + len(v)
    return {"n_files": n_files, "n_cells": len(cells),
            "share_of_files_by_cell_size": classes,
            "cells_by_end_depth": dict(sorted(depth_cells.items())),
            "share_of_files_by_end_depth": {k: round(v / n_files, 6) for k, v in sorted(depth_files.items())},
            "null_is_size_only": all(d == "" for (_b, d) in cells),
            "note": "released copies are permuted within the LOC band only; depth 0 = the band alone"}


def scramble_outcome(file_table, positives, k=DEFAULT_K):
    """The released scramble for one outcome: band-only cells, k copies, rule 5. Returns
    (copies_or_None, report_part, measures). `measures` holds exact numbers and stays in memory (tests read
    it); `report_part` is what may be written: the release decision only."""
    cells = released_cells(file_table)
    copies = scramble(cells, positives, k)
    m = leak_measures(cells, positives, copies)
    released, written = release_decision(m, k)
    return (copies if released else None), dict(written), m
