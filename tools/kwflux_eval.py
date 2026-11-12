#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""KWFLUX (EXPLORATORY): which parts of a function are constant and which are in flux?

Direction-agnostic by design. KWMAT asked which way a family's share moves and got an answer that did not
replicate; this asks only **whether** it moves, which is the question that survives sign flips.

No registration, no hypothesis fixed in advance, no p-value claimed. Nulls are reported beside every
number that needs one.

    python tools/kwflux_eval.py [--repos curl openssl ...]      # -> docs/kwflux.md

Unit: a transition, i.e. one function between two consecutive snapshots of the quarterly walk. A transition
counts as an EDIT when any keyword-family count or the function's line count differs across it; everything
below is conditioned on edits, because an untouched function cannot move and would otherwise drown the rates.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR  # noqa: E402
from kwmature_eval import FAMILIES, lives  # noqa: E402

REPOS = ("curl", "openssl", "libarchive", "harfbuzz", "ndpi")
SEED = 2982
MIN_SCOPE = 100       # a family is "in scope" for a repo only if this many functions ever hold it
NSETS = 400_000       # cap on retained move-sets per repo (memory); reservoir-free, first N


def scan(repo):
    n = len(FAMILIES)
    moves, absd, mass = np.zeros(n), np.zeros(n), np.zeros(n)
    inscope, co = np.zeros(n), np.zeros((n, n))
    edited, funcs, own, pool = 0, 0, [], []
    for _key, life in lives(repo):
        arr = np.array([c for _, _, c in life], dtype=float)
        loc = np.array([l for _, l, _ in life], dtype=float)
        funcs += 1
        inscope += arr.max(axis=0) > 0
        mass += arr.mean(axis=0)
        d = np.diff(arr, axis=0)
        moved = d != 0
        ed = moved.any(axis=1) | (np.diff(loc) != 0)
        if not ed.any():
            continue
        M = moved[ed]
        edited += int(ed.sum())
        moves += M.sum(axis=0)
        absd += np.abs(d[ed]).sum(axis=0)
        co += M.T.astype(float) @ M.astype(float)
        sets = [frozenset(np.nonzero(m)[0].tolist()) for m in M if m.any()]
        own += [(sets[i], sets[i + 1]) for i in range(len(sets) - 1)]
        if len(pool) < NSETS:
            pool += sets[: NSETS - len(pool)]
    return {"repo": repo, "funcs": funcs, "edited": edited, "moves": moves, "absd": absd, "mass": mass,
            "inscope": inscope, "co": co, "own": own, "pool": pool}


def jac(a, b):
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def consistency(s, rng):
    """Do the same functions move the same families each time they are edited? Own successive pairs vs a
    size-matched null (pairs drawn from different functions with the same two set sizes)."""
    own = s["own"]
    if len(own) < 50:
        return None
    by_size = defaultdict(list)
    for x in s["pool"]:
        by_size[len(x)].append(x)
    obs, null = [], []
    for a, b in own:
        obs.append(jac(a, b))
        ca, cb = by_size.get(len(a)), by_size.get(len(b))
        if ca and cb:
            null.append(jac(ca[rng.integers(len(ca))], cb[rng.integers(len(cb))]))
    return float(np.mean(obs)), float(np.mean(null)), len(obs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repos", nargs="+", default=list(REPOS))
    a = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    S = {}
    for r in a.repos:
        S[r] = scan(r)
        print(f"{r}: {S[r]['funcs']:,} functions, {S[r]['edited']:,} edited transitions "
              f"({time.time() - t0:.0f}s)", flush=True)

    rate = {}   # repo -> per-family P(family moves | the function was edited), NaN when out of scope
    for r in a.repos:
        s = S[r]
        p = s["moves"] / max(s["edited"], 1)
        p[s["inscope"] < MIN_SCOPE] = np.nan
        rate[r] = p

    L = ["# What is constant and what is in flux (KWFLUX, EXPLORATORY)", "",
         "**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value claimed**. "
         f"Tool: `tools/kwflux_eval.py`. Repos: {', '.join(a.repos)}. Run 2026-11-11.", "",
         "## The question", "",
         "[`kwmature.md`](kwmature.md) ranked families by **which way** their share moves over a function's "
         "life. That direction did not replicate: `state_pointers` is the top gainer in curl and the top "
         "loser in nDPI. This note drops direction and asks only **what moves at all**, which is the part "
         "that can be compared across projects.", "",
         "Everything is conditioned on an **edit** — a transition where any family count or the line count "
         "changed. Unedited transitions are the large majority and would otherwise set every rate near zero.", "",
         "| repo | functions | edited transitions |", "|---|---:|---:|"]
    for r in a.repos:
        L.append(f"| {r} | {S[r]['funcs']:,} | {S[r]['edited']:,} |")

    # ---- the categorisation
    arr = np.array([rate[r] for r in a.repos])            # repos x families
    with np.errstate(invalid="ignore"):
        mean_p = np.nanmean(arr, axis=0)
    seen = (~np.isnan(arr)).sum(axis=0)
    order = np.argsort(-np.nan_to_num(mean_p, nan=-1))
    L += ["", "## Every family, by how often it moves when the function is edited", "",
          f"`P(moves | edited)`, per repo. A family is blank where fewer than {MIN_SCOPE} functions in that "
          "repo ever hold it — out of scope, not constant.", "",
          "| family | " + " | ".join(a.repos) + " | mean | spread |",
          "|---|" + "---:|" * (len(a.repos) + 2)]
    for i in order:
        if seen[i] == 0:
            continue
        cells = " | ".join("—" if np.isnan(rate[r][i]) else f"{rate[r][i]:.3f}" for r in a.repos)
        vals = arr[:, i][~np.isnan(arr[:, i])]
        L.append(f"| `{FAMILIES[i]}` | {cells} | {mean_p[i]:.3f} | {vals.max() - vals.min():.3f} |")

    # constant vs fluid, by agreement across repos rather than by the pooled mean
    ranks = np.full(arr.shape, np.nan)
    for j, r in enumerate(a.repos):
        v = arr[j]
        ok = ~np.isnan(v)
        rr = np.full(len(v), np.nan)
        rr[ok] = np.argsort(np.argsort(-v[ok])) / max(ok.sum() - 1, 1)
        ranks[j] = rr
    with np.errstate(invalid="ignore"):
        hi = np.nansum(ranks <= 1 / 3, axis=0)
        lo = np.nansum(ranks >= 2 / 3, axis=0)
    fluid = [i for i in order if seen[i] >= 3 and hi[i] == seen[i]]
    const = [i for i in order if seen[i] >= 3 and lo[i] == seen[i]]
    mixed = [i for i in order if seen[i] >= 3 and i not in fluid and i not in const]
    L += ["", "## The categorisation", "",
          "A family is **IN FLUX** only if it lands in the top third of the move-rate ranking in *every* repo "
          "where it is in scope, and **CONSTANT** only if it lands in the bottom third in every one. Anything "
          "that disagrees across projects is **MIXED**, which is a result about the family, not a failure.", "",
          "| verdict | families |", "|---|---|",
          "| **IN FLUX everywhere** | " + (", ".join(f"`{FAMILIES[i]}`" for i in fluid) or "—") + " |",
          "| **CONSTANT everywhere** | " + (", ".join(f"`{FAMILIES[i]}`" for i in const) or "—") + " |",
          "| MIXED | " + (", ".join(f"`{FAMILIES[i]}`" for i in mixed) or "—") + " |"]

    # ---- do the repos agree on the ordering at all?
    L += ["", "## Do projects agree about what moves?", "",
          "Spearman correlation between repos of the per-family move rate (families in scope in both).", "",
          "| | " + " | ".join(a.repos) + " |", "|---|" + "---:|" * len(a.repos)]
    for j, r in enumerate(a.repos):
        row = []
        for k, r2 in enumerate(a.repos):
            m = ~np.isnan(arr[j]) & ~np.isnan(arr[k])
            if m.sum() < 5:
                row.append("—")
                continue
            x, y = arr[j][m], arr[k][m]
            rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
            row.append(f"{np.corrcoef(rx, ry)[0, 1]:.2f}")
        L.append(f"| **{r}** | " + " | ".join(row) + " |")

    # ---- do the same functions move the same way?
    L += ["", "## Do the same functions change the same way each time?", "",
          "For every function edited at least twice: the Jaccard overlap between the set of families it moved "
          "in one edit and the set it moved in the next. The null pairs **different** functions' edits, matched "
          "on both set sizes, so a high overlap cannot come from most edits touching one or two families.", "",
          "| repo | successive edit pairs | own next edit | size-matched null | ratio |", "|---|---:|---:|---:|---:|"]
    for r in a.repos:
        c = consistency(S[r], rng)
        if c is None:
            L.append(f"| {r} | — | — | — | — |")
            continue
        obs, nul, n = c
        L.append(f"| {r} | {n:,} | **{obs:.3f}** | {nul:.3f} | {obs / nul:.2f}× |" if nul else
                 f"| {r} | {n:,} | **{obs:.3f}** | 0.000 | — |")

    # ---- co-change, first look
    L += ["", "## Co-change (a first look, not a result)", "",
          "Lift = P(A and B both move in one edit) / P(A)·P(B), over edited transitions. Lift 1.0 means the two "
          "move independently. Pairs are ranked by lift among families in scope with a move rate of at least "
          "2%, so the list is not dominated by rare families that co-occur once.", ""]
    r0 = a.repos[0]
    s = S[r0]
    p = rate[r0]
    cand = [i for i in range(len(FAMILIES)) if not np.isnan(p[i]) and p[i] >= 0.02]
    pairs = []
    for ii, i in enumerate(cand):
        for j in cand[ii + 1:]:
            both = s["co"][i, j] / max(s["edited"], 1)
            exp = p[i] * p[j]
            if exp > 0 and both > 0:
                pairs.append((both / exp, FAMILIES[i], FAMILIES[j], both))
    pairs.sort(reverse=True)
    L += [f"In **{r0}**, {len(cand)} families qualify.", "",
          "| pair | P(both move) | lift |", "|---|---:|---:|"]
    L += [f"| `{x[1]}` + `{x[2]}` | {x[3]:.3f} | {x[0]:.2f}× |" for x in pairs[:12]]

    L += ["", "## Limits", "",
          "- **An edit is a change in the engine's counts or the line count**, not a diff. A change that keeps "
          "every count identical is invisible here, and [`kwnest.md`](kwnest.md) shows those exist: of 375 "
          "curl functions edited while keeping an identical keyword multiset, naming and wiring still moved.",
          "- **The walk is quarterly**, so a move and its reversal inside one quarter is invisible. Every rate "
          "here is a floor.",
          "- **Identity is `(file_path, func_name)`**, so a rename reads as a death and a birth and the sample "
          "leans toward survivors.",
          "- **Move rates are not independent of family mass**: a family with many hits per function has more "
          "chances to differ. The mass column is not shown here; the cross-repo agreement, not the absolute "
          "rate, is what this note reads.",
          "- **Five C/C++ projects.** Nothing here speaks to other languages, and the keyword families are "
          "defined per language, so they are not comparable across them as implemented.",
          "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "kwflux.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
