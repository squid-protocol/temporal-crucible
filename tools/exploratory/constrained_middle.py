#!/usr/bin/env python3
"""EXPLORATORY: the "constrained middle" -- three-signal combinations that chance predicts often but code (almost) never
builds, although each of their pairs is built normally. Candidate higher-order "building codes", checked per language and
per large repo.

Null: each signal independent, per-language probability depending on function size (logistic in standardised log10 loc
and its square: the KW size placebo). Expected counts are exact sums of per-function probability products.

    python tools/exploratory/constrained_middle.py --pop <master_db_v2.12.0-b64f42bf.db> [--sample 2000000]
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import re
import sqlite3
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402
from gr_eval import fit_p  # noqa: E402
from out_eval import FLAG_T, code  # noqa: E402

SEED, MIN_LANG, MIN_REPO, PAIR_OK = 2982, 30_000, 20_000, 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", required=True)
    ap.add_argument("--sample", type=int, default=2_000_000)
    ap.add_argument("--engine", default="/srv/storage_16tb/projects/gitgalaxy/gitgalaxy-worktrees/signal-names")
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from gitgalaxy.standards.analysis_lens import signal_display_name as dn  # noqa: E402
    short = lambda c: re.sub(r"\s*\(.*\)$", "", dn(c))  # noqa: E731
    rng = np.random.default_rng(SEED)
    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    total = con.execute("SELECT COUNT(*) FROM function_data WHERE loc >= 3").fetchone()[0]
    keep = min(1.0, a.sample / total)
    cur = con.execute(f"SELECT fd.language, fd.repo_name, fd.file_path, f.func_name, f.start_line, f.loc, "
                      f"{', '.join('(COALESCE(f.' + c + ',0) > 0)' for c in sig)} "
                      "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3")
    meta, X = [], []
    while True:
        b = cur.fetchmany(250_000)
        if not b:
            break
        for r, k in zip(b, rng.random(len(b)) < keep):
            if k:
                meta.append(r[:6])
                X.append(r[6:])
        print(f"  kept {len(X):,}", flush=True)
    con.close()
    X = np.array(X, dtype=bool)
    lang = np.array([m[0] for m in meta])
    repo = np.array([m[1] for m in meta])
    loc = np.array([float(m[5]) for m in meta])
    prev = X.mean(0)
    use = [j for j in range(len(sig)) if K.LO <= prev[j] <= K.HI]
    S = [sig[j] for j in use]
    X = X[:, use]
    m = len(S)
    # per-language size-dependent probabilities
    Pp = np.zeros(X.shape, np.float32)
    langs = [l for l in np.unique(lang) if (lang == l).sum() >= MIN_LANG]
    for l in np.unique(lang):
        ix = np.flatnonzero(lang == l)
        z = np.log10(loc[ix])
        z = (z - z.mean()) / (z.std() + 1e-9)
        for j in range(m):
            x = X[ix, j].astype(float)
            Pp[ix, j] = fit_p(x, z) if 0 < x.mean() < 1 and len(ix) >= 200 else x.mean()
    print(f"  null fitted; signals {m}; languages with >= {MIN_LANG}: {len(langs)}", flush=True)

    def counts(rows):
        Xi, Pi = X[rows].astype(np.float32), Pp[rows]
        O2, E2 = Xi.T @ Xi, Pi.T @ Pi
        O3, E3 = np.zeros((m, m, m), np.float32), np.zeros((m, m, m), np.float32)
        for i, j in itertools.combinations(range(m), 2):
            O3[i, j] = (Xi[:, i] * Xi[:, j]) @ Xi
            E3[i, j] = (Pi[:, i] * Pi[:, j]) @ Pi
        return O2, E2, O3, E3
    allr = np.arange(len(X))
    O2, E2, O3, E3 = counts(allr)
    r2 = (O2 + 0.5) / (E2 + 0.5)
    cand = []
    for i, j, k in itertools.combinations(range(m), 3):
        e = E3[i, j, k]
        if e < 200:
            continue
        ratio = (O3[i, j, k] + 0.5) / (e + 0.5)
        pairs_ok = min(r2[i, j], r2[i, k], r2[j, k]) >= PAIR_OK
        # also beyond what the pairs imply: compare with the expectation given the observed pair rates
        cond = O2[i, j] * O2[i, k] * O2[j, k] / max(len(X), 1) ** 3 * len(X)
        cand.append((ratio, i, j, k, int(O3[i, j, k]), float(e), pairs_ok))
    cand.sort()
    holes = [c for c in cand if c[6] and c[0] < 0.25]
    # universality per language and per large repo
    per_lang = {l: counts(np.flatnonzero(lang == l)) for l in langs}
    big = [r for r in np.unique(repo) if (repo == r).sum() >= MIN_REPO]
    per_repo = {r: counts(np.flatnonzero(repo == r)) for r in big}
    print(f"  per-language and per-repo counts done ({len(big)} large repos)", flush=True)

    def holds(tab, i, j, k):
        ok = tot = 0
        for O2_, E2_, O3_, E3_ in tab.values():
            e = E3_[i, j, k]
            if e < 20:
                continue
            tot += 1
            ok += (O3_[i, j, k] + 0.5) / (e + 0.5) < 0.25
        return ok, tot
    L = ["# EXPLORATORY — the constrained middle: three-signal combinations code avoids (population DB v2.12.0-b64f42bf)", "",
         f"- sample {len(X):,} functions (loc ≥ 3); signals with 2–98% presence: {m}; triples with null expectation ≥ 200: {len(cand):,}",
         "- null: independent signals, per-language size-dependent rates (the KW size placebo); ratio = (observed + 0.5) / (expected + 0.5)",
         f"- **higher-order holes** (triple ratio < 0.25 while every pair of it is built at ≥ {PAIR_OK} of chance): **{len(holes)}** of {len(cand):,} triples "
         f"({len(holes) / max(len(cand), 1):.1%}); all triples < 0.25 including pair-driven ones: {sum(1 for c in cand if c[0] < 0.25)}", "",
         "## The strongest higher-order holes, and how universal they are", "",
         "| combination (all three present) | observed | chance expects | ratio | languages where it holds | large repos where it holds |",
         "|---|---:|---:|---:|---:|---:|"]
    shown = []
    for ratio, i, j, k, o, e, _ in holes[:25]:
        hl, tl = holds(per_lang, i, j, k)
        hr, tr = holds(per_repo, i, j, k)
        shown.append((i, j, k, hl, tl, hr, tr))
        L.append(f"| {short(S[i])} + {short(S[j])} + {short(S[k])} | {o:,} | {e:,.0f} | {ratio:.3f} | {hl}/{tl} | {hr}/{tr} |")
    univ = [s for s in shown if s[4] >= 5 and s[3] / s[4] >= 0.8 and s[6] >= 5 and s[5] / s[6] >= 0.8]
    L += ["", f"- **universal** (holds in ≥ 80% of languages and of large repos where testable, ≥ 5 each): {len(univ)} of the {len(shown)} shown"]
    # attractions for contrast
    att = sorted([c for c in cand if c[6]], key=lambda c: -c[0])[:8]
    L += ["", "## For contrast: the strongest higher-order attractions", ""]
    L += [f"- {short(S[i])} + {short(S[j])} + {short(S[k])}: {o:,} vs {e:,.0f} expected ({r:.1f}×)" for r, i, j, k, o, e, _ in att]
    # who breaks the universal rules
    if univ:
        L += ["", "## Who breaks the universal rules", ""]
        for i, j, k, *_ in univ[:5]:
            br = np.flatnonzero(X[:, i] & X[:, j] & X[:, k])
            tshare = np.mean([bool(FLAG_T.search(meta[b][2] or "")) for b in br]) if len(br) else float("nan")
            base = np.mean([bool(FLAG_T.search(mm[2] or "")) for mm in meta[::50]])
            langs_b = defaultdict(int)
            for b in br:
                langs_b[lang[b]] += 1
            L.append(f"- **{short(S[i])} + {short(S[j])} + {short(S[k])}**: {len(br):,} breakers in the sample; "
                     f"in test paths {tshare:.0%} (all functions {base:.0%}); languages " + ", ".join(f"{l} {n}" for l, n in sorted(langs_b.items(), key=lambda t: -t[1])[:4]))
            for b in rng.permutation(br)[:2]:
                c = code(meta[b][1], meta[b][2], meta[b][4], meta[b][5])
                if c:
                    L += [f"  - {meta[b][0]} · {meta[b][1]} · `{meta[b][3]}`", "", "```", "\n".join(c.split("\n")[:12]), "```", ""]
    L += ["", "Caveats: exploratory; one null draw family (size-only); presence only; function-weighted (OS-scale repos weigh "
          "heavily, hence the per-repo check); rules as of b64f42bf (before gitgalaxy#8024 / #8016)."]
    (DOCS_DIR / "constrained_middle_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
