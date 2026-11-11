#!/usr/bin/env python3
"""KWMAT (exploratory): if a function is born with its final shape, what changes afterwards?

    python tools/kwmature_eval.py freeze --repo curl    # presence vs counts: what the binary measure hides
    python tools/kwmature_eval.py drift  --repo curl    # does the keyword MIX drift, or only the mass?
    python tools/kwmature_eval.py direction --repo curl # which families gain and lose share over a life

**Exploratory. No registration, no hypothesis fixed in advance, no p-value claimed.**

The program's standing finding is that about 71% of functions never change *shape*, where a shape is the
**set** of keyword families present (`tools/lat_eval.py`: `P: bool (N x len(cols)) presence`). A set cannot
see maturation: {branch, call, alloc} is the same set whether a function holds one branch or nine, in any
order, at any nesting depth. So "born in final form" may be a statement about the resolution of the measure
rather than about code.

The engine already records **raw counts** per family, not flags (`struct_branch` runs 0..1631 in the curl
walk). This tool uses the counts that the presence measure throws away, on the same functions, and asks
three questions that presence cannot answer:

1. **freeze** -- among functions whose presence SET never changes, how many have changing COUNTS?
2. **drift** -- when a function grows, does it keep its proportions (isotropic growth: the same creature,
   larger) or does the mix move (anisotropic: it matures into something else)? Composition is compared as
   normalised count vectors, so pure scaling registers as no drift by construction.
3. **direction** -- which families gain and which lose share across a life, averaged over functions.

**Identity** is `(file_path, func_name)` within one repo walk. A rename or a move therefore reads as a death
and a birth, which undercounts long lives; it never invents one. Functions seen in only one snapshot are
excluded from every life measure.

**Not measured here, and the obvious next step:** the *order* of keywords and their *nesting depth*. Both
need the source, not the database. This tool deliberately stops at multiplicity and composition.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

WT = Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
       "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db",
       "openssl": WT / "frec/dbs/openssl_out/openssl_galaxy_master.db",
       "harfbuzz": WT / "sc-class/dbs/harfbuzz_out/harfbuzz_galaxy_master.db",
       "libarchive": WT / "sc-class/dbs/libarchive_out/libarchive_galaxy_master.db"}

# C-relevant keyword families. Naming and whitespace columns (struct_camel_case, struct_tabs...), the
# language-irrelevant ones (llm_*, dl_frameworks, struct_comprehensions...), and the threat/literature
# scanners are left out: they are not what a C function is built from.
FAMILIES = [
    "struct_branch", "struct_linear", "struct_args", "struct_func_start", "struct_macros",
    "struct_closures", "struct_var_decl",
    "state_pointers", "state_memory_alloc", "state_flux", "state_danger", "state_safety_neg",
    "state_cast_hits", "state_bailout_hits", "state_halt_hits", "state_print_hits",
    "state_heat_triggers", "state_graveyard", "state_planned_debt", "state_fragile_debt",
    "def_safety", "def_cleanup", "def_ownership", "def_sync_locks", "def_encapsulation",
    "def_doc", "def_telemetry", "def_freeze_hits", "def_spec_exposure", "def_auth",
    "arch_io", "arch_api", "arch_globals", "arch_import", "arch_concurrency", "arch_crypto",
    "arch_time", "arch_serialization", "arch_ipc", "arch_hardware", "arch_inline_asm",
    "arch_events", "arch_regex", "arch_sys_config", "bitwise_ops",
]


def lives(repo: str, min_snaps: int = 2):
    """Yield (key, [(date, loc, counts[]), ...]) per function, in snapshot order."""
    db = DBS[repo]
    if not db.exists():
        sys.exit(f"no walk database for {repo}: {db}")
    cols = ", ".join(f"fn.{c}" for c in FAMILIES)
    q = (f"SELECT f.commit_date, f.file_path, fn.func_name, fn.loc, {cols} "
         f"FROM function_data fn JOIN file_data f ON fn.file_id = f.id "
         f"ORDER BY f.file_path, fn.func_name, f.commit_date")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur, key, acc = con.execute(q), None, []
    for row in cur:
        date, path, name, loc = row[0], row[1], row[2], row[3] or 0
        counts = [int(x or 0) for x in row[4:]]
        k = (path, name)
        if k != key:
            if key and len(acc) >= min_snaps:
                yield key, acc
            key, acc = k, []
        if not acc or acc[-1][0] != date:      # one row per snapshot; duplicates (static funcs) take the first
            acc.append((date, loc, counts))
    if key and len(acc) >= min_snaps:
        yield key, acc
    con.close()


def presence(counts) -> tuple:
    return tuple(1 if c > 0 else 0 for c in counts)


def cosine(a, b) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    if not na or not nb:
        return float("nan")
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def normalise(counts):
    t = sum(counts)
    return [c / t for c in counts] if t else counts


def cmd_freeze(a) -> int:
    n = pres_frozen = count_frozen = both = loc_frozen = 0
    pres_frozen_count_moved = 0
    for _k, life in lives(a.repo):
        n += 1
        ps = {presence(c) for _d, _l, c in life}
        cs = {tuple(c) for _d, _l, c in life}
        ls = {l for _d, l, _c in life}
        pf, cf = len(ps) == 1, len(cs) == 1
        pres_frozen += pf
        count_frozen += cf
        both += pf and cf
        loc_frozen += len(ls) == 1
        if pf and not cf:
            pres_frozen_count_moved += 1
    print(f"{a.repo}: {n:,} functions seen in >= 2 snapshots of the walk\n")
    print(f"  presence SET never changes   {pres_frozen:7,}  {pres_frozen / n:6.1%}   <- the existing measure")
    print(f"  COUNT vector never changes   {count_frozen:7,}  {count_frozen / n:6.1%}")
    print(f"  line count never changes     {loc_frozen:7,}  {loc_frozen / n:6.1%}")
    print(f"\n  of the {pres_frozen:,} shape-frozen functions, {pres_frozen_count_moved:,} "
          f"({pres_frozen_count_moved / pres_frozen:.1%}) change their COUNTS")
    print(f"  so the binary measure calls them unchanged while the engine's own numbers move.")
    return 0


def cmd_drift(a) -> int:
    rows, raw = [], []
    for _k, life in lives(a.repo):
        first, last = life[0], life[-1]
        m0, m1 = sum(first[2]), sum(last[2])
        if m0 < a.min_mass or m1 < a.min_mass:
            continue
        rows.append((cosine(normalise(first[2]), normalise(last[2])), m0, m1, first[1], last[1],
                     presence(first[2]) == presence(last[2])))
        raw.append((rows[-1][0], m0, m1, first[1], last[1], first[2], last[2]))
    if not rows:
        return 1

    # NULL: pair each function's birth vector with ANOTHER function's last vector, inside the same
    # mass band. Without it a high cosine is unreadable -- it could just mean every C function has a
    # similar keyword mix. The real drift must beat this to mean anything.
    import random
    rng = random.Random(2982)
    bands = defaultdict(list)
    for i, r in enumerate(raw):
        bands[int(math.log2(max(1, r[1])))].append(i)
    null = []
    for i, r in enumerate(raw):
        pool = bands[int(math.log2(max(1, r[1])))]
        if len(pool) < 2:
            continue
        j = i
        for _ in range(8):
            j = rng.choice(pool)
            if j != i:
                break
        if j != i:
            null.append(cosine(normalise(r[5]), normalise(raw[j][6])))
    null.sort()

    rows.sort()
    def pct(p):
        return rows[min(len(rows) - 1, int(p * len(rows)))][0]
    grew = [r for r in rows if r[2] > r[1]]
    same_shape = [r for r in rows if r[5]]
    print(f"{a.repo}: {len(rows):,} functions with >= {a.min_mass} keyword hits at both ends of their life\n")
    print("  composition drift, first snapshot vs last (cosine of normalised count vectors;")
    print("  1.000 = identical mix, so pure growth with a fixed mix scores 1.000 by construction)")
    print(f"    median {pct(0.5):.3f}   p25 {pct(0.25):.3f}   p10 {pct(0.10):.3f}   p05 {pct(0.05):.3f}")
    print(f"    identical mix (cos > 0.999): {sum(1 for r in rows if r[0] > 0.999) / len(rows):6.1%}")
    print(f"    mix clearly moved (cos < 0.95): {sum(1 for r in rows if r[0] < 0.95) / len(rows):6.1%}")
    if same_shape:
        ss = sorted(r[0] for r in same_shape)
        print(f"\n  restricted to functions whose presence SET never changed ({len(same_shape):,}):")
        print(f"    median drift {ss[len(ss) // 2]:.3f}; mix moved (cos < 0.95) in "
              f"{sum(1 for c in ss if c < 0.95) / len(ss):.1%}")
    if null:
        def npct(p):
            return null[min(len(null) - 1, int(p * len(null)))]
        print(f"\n  NULL -- birth vector vs an UNRELATED function's last vector, same mass band "
              f"({len(null):,} pairs):")
        print(f"    median {npct(0.5):.3f}   p25 {npct(0.25):.3f}   p10 {npct(0.10):.3f}")
        print(f"    mix 'moved' (cos < 0.95): {sum(1 for c in null if c < 0.95) / len(null):6.1%}")
        print(f"    => a function's own life is {'MORE' if pct(0.5) > npct(0.5) else 'LESS'} conserved than "
              f"a random same-size pairing (median {pct(0.5):.3f} vs {npct(0.5):.3f})")

    if grew:
        g = sorted(r[0] for r in grew)
        print(f"\n  restricted to functions whose keyword mass GREW ({len(grew):,}):")
        print(f"    median drift {g[len(g) // 2]:.3f}; mix moved in {sum(1 for c in g if c < 0.95) / len(g):.1%}")
        ratios = sorted(r[2] / r[1] for r in grew)
        print(f"    median growth x{ratios[len(ratios) // 2]:.2f}")
    return 0


def cmd_direction(a) -> int:
    delta = defaultdict(float)
    n = 0
    for _k, life in lives(a.repo):
        f, l = normalise(life[0][2]), normalise(life[-1][2])
        if not sum(life[0][2]) or not sum(life[-1][2]):
            continue
        n += 1
        for i, fam in enumerate(FAMILIES):
            delta[fam] += l[i] - f[i]
    if not n:
        return 1
    out = sorted(((v / n, k) for k, v in delta.items()), reverse=True)
    print(f"{a.repo}: mean change in each family's SHARE of a function's keyword mass, birth -> last seen "
          f"({n:,} functions)\n")
    print(f"  {'family':24} {'mean share change':>18}")
    for v, k in out[:8]:
        print(f"  {k:24} {v:+18.4f}")
    print("  ...")
    for v, k in out[-8:]:
        print(f"  {k:24} {v:+18.4f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("freeze", "drift", "direction"))
    ap.add_argument("--repo", default="curl", choices=sorted(DBS))
    ap.add_argument("--min-mass", type=int, default=5,
                    help="drift: minimum keyword hits at both ends (tiny functions make cosine noisy)")
    a = ap.parse_args()
    return {"freeze": cmd_freeze, "drift": cmd_drift, "direction": cmd_direction}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
