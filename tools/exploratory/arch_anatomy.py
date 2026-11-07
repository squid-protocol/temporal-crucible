#!/usr/bin/env python3
"""EXPLORATORY (not registered): keyword anatomy of function archetypes, and the distribution of function
fingerprints, on the population DB. Circularity caveat: archetypes were clustered on these signal densities, so
per-archetype presence rates are partly by construction; the within-archetype PAIR grammar is the less circular part.

    python tools/exploratory/arch_anatomy.py --pop <db> --crucible <kw_scan db>
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402
from gr_eval import crucible_grammar, oe  # noqa: E402

SEED, PER_ARCH = 2982, 150_000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", required=True)
    ap.add_argument("--crucible", required=True)
    a = ap.parse_args()
    w = crucible_grammar(a.crucible)
    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    cur = con.execute(f"SELECT f.func_archetype, fd.language, f.loc, {', '.join('COALESCE(f.' + c + ',0)' for c in sig)} "
                      "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3")
    rng = np.random.default_rng(SEED)
    res = defaultdict(list)  # reservoir per archetype
    seen = Counter()
    sigcount = Counter()
    n_all = 0
    pres_all = np.zeros(len(sig))
    while True:
        rows = cur.fetchmany(250_000)
        if not rows:
            break
        C = np.array([r[3:] for r in rows], dtype=float)
        P = C > 0
        pres_all += P.sum(0)
        n_all += len(rows)
        keys = np.packbits(P, axis=1)
        sigcount.update(bytes(k) for k in keys)
        for r, c in zip(rows, C):
            ar = r[0] or "Unassigned"
            seen[ar] += 1
            if len(res[ar]) < PER_ARCH:
                res[ar].append((r[1], float(r[2]), c))
            else:
                j = rng.integers(0, seen[ar])
                if j < PER_ARCH:
                    res[ar][j] = (r[1], float(r[2]), c)
        print(f"  {n_all:,}", flush=True)
    con.close()
    overall = pres_all / n_all
    common = [i for i in range(len(sig)) if overall[i] >= 0.05]
    L = ["# EXPLORATORY — keyword anatomy of function archetypes, and fingerprint distribution (population DB v2.12.0-b64f42bf)", "",
         "**Circularity:** archetypes are clustered on these signal densities, so presence rates partly follow by construction. "
         "Structural absences and within-archetype pair grammar are the informative parts.", "",
         f"- functions (loc ≥ 3): {n_all:,}; signals {len(sig)}; signals present in ≥ 5% overall: {len(common)}", "",
         "## Structural absences and near-universals per archetype (signals with ≥ 5% overall prevalence)", "",
         "| archetype | n | never (< 0.1%) | almost always (≥ 90%) |", "|---|---:|---|---|"]
    arch_rows = {}
    for ar, lst in sorted(res.items(), key=lambda t: -seen[t[0]]):
        C = np.array([x[2] for x in lst])
        P = (C > 0).mean(0)
        never = [sig[i] for i in common if P[i] < 0.001]
        always = [sig[i] for i in common if P[i] >= 0.90]
        arch_rows[ar] = (lst, P)
        L.append(f"| {ar} | {seen[ar]:,} | {', '.join(never) or '—'} | {', '.join(always) or '—'} |")
    L += ["", "## Does the confirmed pair grammar hold within each archetype? (sign agreement with crucible consensus)", "",
          "| archetype | pairs testable | agreement |", "|---|---:|---:|"]
    for ar, (lst, P) in arch_rows.items():
        C = np.array([x[2] for x in lst])
        Pm = C > 0
        lc = np.array([x[1] for x in lst])
        used = [i for i in range(len(sig)) if 0.02 <= Pm[:, i].mean() <= 0.98]
        if len(used) < 3:
            L.append(f"| {ar} | 0 | — |")
            continue
        s = [sig[i] for i in used]
        M = oe(Pm[:, used], lc)
        hits = [np.sign(M[s.index(x), s.index(y)]) == np.sign(v) for (x, y), v in w.items() if x in s and y in s and M[s.index(x), s.index(y)] != 0]
        L.append(f"| {ar} | {len(hits)} | {np.mean(hits):.0%} |" if hits else f"| {ar} | 0 | — |")
    # fingerprint distribution: exact signal-presence signatures
    counts = np.array(sorted(sigcount.values(), reverse=True), dtype=float)
    tot = counts.sum()
    cum = np.cumsum(counts) / tot
    k50 = int(np.searchsorted(cum, 0.5)) + 1
    k90 = int(np.searchsorted(cum, 0.9)) + 1
    ranks = np.arange(1, len(counts) + 1)
    sel = (ranks >= 10) & (ranks <= min(len(counts), 100_000))
    slope = float(np.polyfit(np.log(ranks[sel]), np.log(counts[sel]), 1)[0]) if sel.sum() > 10 else float("nan")
    H = float(-(counts / tot * np.log2(counts / tot)).sum())
    L += ["", "## Fingerprint distribution: exact signal-presence signatures (which of the signals are present)", "",
          f"- distinct signatures: **{len(counts):,}** across {int(tot):,} functions; singletons {int((counts == 1).sum()):,} ({(counts == 1).sum() / len(counts):.0%} of signatures, {(counts == 1).sum() / tot:.1%} of functions)",
          f"- the top 10 signatures cover {cum[min(9, len(cum) - 1)]:.0%} of functions; **{k50:,}** signatures cover 50%, **{k90:,}** cover 90%",
          f"- rank–frequency slope (ranks 10 to 100k, log–log): **{slope:.2f}** (Zipf ≈ −1)",
          f"- signature entropy {H:.1f} bits"]
    # effective dimensionality of per-line densities
    S = np.vstack([np.array([x[2] for x in lst]) / np.array([x[1] for x in lst])[:, None] for lst, _ in arch_rows.values()])
    S = S[:, common]
    S = np.log1p(S * 100)
    S = (S - S.mean(0)) / (S.std(0) + 1e-9)
    ev = np.linalg.eigvalsh(np.cov(S.T))[::-1]
    ev = ev / ev.sum()
    pr = 1 / np.sum(ev ** 2)
    L += [f"- per-line density profile ({len(common)} common signals, {len(S):,}-function archetype-balanced sample): first 3 components explain "
          f"{ev[:3].sum():.0%}; 90% needs {int(np.searchsorted(np.cumsum(ev), 0.9)) + 1} components; participation ratio (effective dimensions) **{pr:.1f}**"]
    (DOCS_DIR / "arch_anatomy_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
