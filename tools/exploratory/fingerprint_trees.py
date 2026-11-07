#!/usr/bin/env python3
"""EXPLORATORY: draft "family trees" of function fingerprints (exact signal-presence signatures) on the population DB.

Tree 1 (growth): each common signature hangs under its most common proper subset among the common signatures
(ideally one signal fewer); the edge is labelled with the signals added.
Tree 2 (similarity): average-linkage clustering of the common signatures on Jaccard distance, cut into families;
each family is labelled by its core signals, languages, repo spread and test share.

Counts are function-weighted (corpus composition shows through: OS-scale repos weigh heavily); repo counts are
printed beside every node so concentration stays visible. Labels use the engine's display names (gitgalaxy#8009).

    python tools/exploratory/fingerprint_trees.py --pop <db> [--top 200] [--families 14] [--engine <gitgalaxy checkout>]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import sys
from collections import Counter, defaultdict

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402
from out_eval import FLAG_T  # noqa: E402


def rows(pop, sig, extra):
    con = sqlite3.connect(f"file:{pop}?mode=ro", uri=True)
    cur = con.execute(f"SELECT {extra}, {', '.join('(COALESCE(f.' + c + ',0) > 0)' for c in sig)} "
                      "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3")
    while True:
        b = cur.fetchmany(250_000)
        if not b:
            break
        yield b
    con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", required=True)
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--families", type=int, default=14)
    ap.add_argument("--engine", default="/srv/storage_16tb/projects/gitgalaxy/gitgalaxy-worktrees/signal-names")
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from gitgalaxy.standards.analysis_lens import signal_display_name as dn  # noqa: E402

    def short(c):
        return re.sub(r"\s*\(.*\)$", "", dn(c))

    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    con.close()
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    cnt, total = Counter(), 0
    for b in rows(a.pop, sig, "1"):
        for r in b:
            cnt[r[1:]] += 1
        total += len(b)
        print(f"  pass 1: {total:,}", flush=True)
    top = [k for k, _ in cnt.most_common(a.top)]
    idx = {k: i for i, k in enumerate(top)}
    st = [defaultdict(Counter) for _ in top]
    loc_sum = np.zeros(len(top))
    n = 0
    for b in rows(a.pop, sig, "fd.language, fd.repo_name, fd.file_path, f.loc, f.func_archetype"):
        for r in b:
            i = idx.get(r[5:])
            if i is None:
                continue
            s = st[i]
            s["lang"][r[0]] += 1
            s["repo"][r[1]] += 1
            s["test"][bool(FLAG_T.search(r[2] or ""))] += 1
            s["arch"][r[4] or "?"] += 1
            loc_sum[i] += r[3]
        n += len(b)
        print(f"  pass 2: {n:,}", flush=True)
    sets = [frozenset(sig[j] for j, v in enumerate(k) if v) for k in top]
    N = np.array([cnt[k] for k in top], dtype=float)

    def node(i):
        s = st[i]
        langs = "/".join(l for l, _ in s["lang"].most_common(3))
        big = s["repo"].most_common(1)[0][1] / N[i]
        return (f"{N[i] / total:.2%} · {len(s['repo'])} repos (top {big:.0%}) · {langs} · "
                f"{loc_sum[i] / N[i]:.0f} lines · tests {s['test'][True] / N[i]:.0%}")

    # ---- Tree 1: growth (parent = most common proper subset, preferring the fewest added signals)
    parent = {}
    for i, S in enumerate(sets):
        cands = [j for j, T in enumerate(sets) if j != i and T < S]
        if cands:
            parent[i] = min(cands, key=lambda j: (len(S - sets[j]), -N[j]))
    kids = defaultdict(list)
    for i, p in parent.items():
        kids[p].append(i)
    roots = [i for i in range(len(top)) if i not in parent]
    T1 = []

    def walk(i, depth, added):
        lab = ("+ " + ", ".join(short(x) for x in sorted(added))) if added is not None else \
            "{" + ", ".join(short(x) for x in sorted(sets[i])) + "}"
        T1.append(f"{'    ' * depth}- **{lab}** — #{i + 1}: {node(i)}")
        for k in sorted(kids[i], key=lambda j: -N[j]):
            walk(k, depth + 1, sets[k] - sets[i])
    for r_ in sorted(roots, key=lambda j: -N[j]):
        walk(r_, 0, None)
    one_step = sum(1 for i, p in parent.items() if len(sets[i] - sets[p]) == 1)

    # ---- Tree 2: similarity families
    J = np.zeros((len(top), len(top)))
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            u = len(sets[i] | sets[j])
            J[i, j] = J[j, i] = 1 - (len(sets[i] & sets[j]) / u if u else 1)
    Z = linkage(squareform(J, checks=False), method="average")
    lab = fcluster(Z, a.families, criterion="maxclust")
    fams = []
    for f in sorted(set(lab)):
        m = np.flatnonzero(lab == f)
        w = N[m]
        sc = Counter()
        for i in m:
            for x in sets[i]:
                sc[x] += N[i]
        core = [x for x, v in sc.items() if v / w.sum() >= 0.9]
        often = [x for x, v in sc.items() if 0.4 <= v / w.sum() < 0.9]
        L_, R_, A_, Tt = Counter(), Counter(), Counter(), 0
        for i in m:
            L_.update(st[i]["lang"])
            R_.update(st[i]["repo"])
            A_.update(st[i]["arch"])
            Tt += st[i]["test"][True]
        fams.append({"family": int(f), "shapes": len(m), "share": float(w.sum() / total),
                     "core": sorted(core), "often": sorted(often),
                     "langs": [(l, c / w.sum()) for l, c in L_.most_common(4)],
                     "repos": len(R_), "top_repo": R_.most_common(1)[0], "top_repo_share": R_.most_common(1)[0][1] / w.sum(),
                     "arch": [(x, c / w.sum()) for x, c in A_.most_common(3)], "tests": Tt / w.sum(),
                     "members": [int(i) + 1 for i in m[np.argsort(-w)][:6]]})
    fams.sort(key=lambda d: -d["share"])
    cover = N.sum() / total
    L = ["# EXPLORATORY — draft family trees of function fingerprints (population DB v2.12.0-b64f42bf)", "",
         f"- top {len(top)} signatures cover **{cover:.1%}** of {total:,} functions (loc ≥ 3); function-weighted, so "
         "OS-scale repos weigh heavily — repo counts are shown beside every node.",
         "- labels are engine display names (gitgalaxy#8009); signals and rules as of engine `b64f42bf` (before the "
         "#8010/#8011/#8016 fixes).", "",
         "## Tree 2 — families (similarity clustering)", "",
         "| family | share | shapes | always (≥ 90%) | often (40–90%) | languages | repos (largest) | tests | archetypes |",
         "|---|---:|---:|---|---|---|---|---:|---|"]
    for d in fams:
        L.append(f"| F{d['family']} | {d['share']:.1%} | {d['shapes']} | {', '.join(short(x) for x in d['core']) or '—'} | "
                 f"{', '.join(short(x) for x in d['often']) or '—'} | {', '.join(f'{l} {p:.0%}' for l, p in d['langs'])} | "
                 f"{d['repos']} ({d['top_repo'][0]} {d['top_repo_share']:.0%}) | {d['tests']:.0%} | "
                 f"{', '.join(f'{x} {p:.0%}' for x, p in d['arch'])} |")
    L += ["", "## Tree 1 — growth (each shape under its most common sub-shape; edge = signals added)", "",
          f"- {len(roots)} root(s); {one_step} of {len(parent)} edges add exactly one signal "
          f"({one_step / max(len(parent), 1):.0%}).", ""] + T1
    (DOCS_DIR / "fingerprint_trees_exploratory.md").write_text("\n".join(L) + "\n")
    (DOCS_DIR / "fingerprint_trees_exploratory.json").write_text(json.dumps(
        {"total": total, "cover": cover, "families": fams,
         "shapes": [{"rank": i + 1, "signals": sorted(sets[i]), "n": int(N[i]), "parent": (parent[i] + 1) if i in parent else None,
                     "repos": len(st[i]["repo"]), "langs": st[i]["lang"].most_common(5)} for i in range(len(top))]}, indent=1))
    print("\n".join(L[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
