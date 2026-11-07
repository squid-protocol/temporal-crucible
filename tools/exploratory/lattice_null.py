#!/usr/bin/env python3
"""EXPLORATORY: is the fingerprint lattice sparser than chance?

Null model: each signal present independently, with a per-signal probability that depends on the function's size
(logistic on log10 loc and its square, per language -- the same size-only placebo the KW studies use). One simulated
population of the same functions is drawn. Compared, observed vs null:
  - distinct signatures, overall and per number-of-signals k; singletons; coverage of the top 200
  - signal PAIRS: observed co-occurrence vs expected under the null (structural holes = expected many, seen ~none;
    attractions = seen far more than expected)
  - the "one-step neighbourhood" of the top-200 shapes: of all shapes one signal away, how many exist at all

    python tools/exploratory/lattice_null.py --pop <db> [--sample 2000000]
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sqlite3
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import kw_eval as K  # noqa: E402
from _engine import DOCS_DIR  # noqa: E402
from gr_eval import fit_p  # noqa: E402

SEED = 2982


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pop", required=True)
    ap.add_argument("--sample", type=int, default=2_000_000)
    ap.add_argument("--engine", default="/srv/storage_16tb/projects/gitgalaxy/gitgalaxy-worktrees/signal-names")
    a = ap.parse_args()
    sys.path.insert(0, a.engine)
    from gitgalaxy.standards.analysis_lens import signal_display_name as dn  # noqa: E402
    import re
    short = lambda c: re.sub(r"\s*\(.*\)$", "", dn(c))  # noqa: E731
    rng = np.random.default_rng(SEED)
    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    total = con.execute("SELECT COUNT(*) FROM function_data WHERE loc >= 3").fetchone()[0]
    keep = min(1.0, a.sample / total)
    cur = con.execute(f"SELECT fd.language, f.loc, {', '.join('(COALESCE(f.' + c + ',0) > 0)' for c in sig)} "
                      "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3")
    langs, locs, X = [], [], []
    while True:
        b = cur.fetchmany(250_000)
        if not b:
            break
        m = rng.random(len(b)) < keep
        for r, k in zip(b, m):
            if k:
                langs.append(r[0])
                locs.append(float(r[1]))
                X.append(r[2:])
        print(f"  read; kept {len(X):,}", flush=True)
    con.close()
    X = np.array(X, dtype=bool)
    lang = np.array(langs)
    loc = np.array(locs)
    live = np.flatnonzero(X.mean(0) > 0)  # signals ever present at function level
    X = X[:, live]
    S = [sig[i] for i in live]
    # null: per language, per signal, logistic in size
    Y = np.zeros_like(X)
    for l in np.unique(lang):
        ix = np.flatnonzero(lang == l)
        z = np.log10(loc[ix])
        z = (z - z.mean()) / (z.std() + 1e-9)
        for j in range(X.shape[1]):
            xj = X[ix, j]
            if xj.mean() in (0.0, 1.0) or len(ix) < 200:
                p = np.full(len(ix), xj.mean())
            else:
                p = fit_p(xj.astype(float), z)
            Y[ix, j] = rng.random(len(ix)) < p
        print(f"  null {l}: {len(ix):,}", flush=True)

    def profile(M):
        keys = [bytes(k) for k in np.packbits(M, axis=1)]
        c = Counter(keys)
        ks = M.sum(1)
        byk = defaultdict(set)
        for kk, kv in zip(ks, keys):
            byk[int(kk)].add(kv)
        cnts = np.array(sorted(c.values(), reverse=True))
        return {"distinct": len(c), "singletons": int((cnts == 1).sum()), "top200": float(cnts[:200].sum() / len(M)),
                "byk": {k: len(v) for k, v in byk.items()}, "fn_byk": Counter(int(x) for x in ks), "counter": c}
    O, Nl = profile(X), profile(Y)
    from math import comb
    m = X.shape[1]
    L = ["# EXPLORATORY — is the fingerprint lattice sparser than chance? (population DB v2.12.0-b64f42bf)", "",
         f"- random sample of {len(X):,} functions (loc ≥ 3); {m} signals ever present per function "
         f"({len(sig) - m} never are: see gitgalaxy#8012)",
         "- null = every signal independent, with a per-language probability that depends on function size "
         "(the KW size placebo), one simulated draw for the same functions", "",
         "| | observed | independent-signals null | ratio |", "|---|---:|---:|---:|",
         f"| distinct shapes | {O['distinct']:,} | {Nl['distinct']:,} | {O['distinct'] / Nl['distinct']:.2f} |",
         f"| shapes seen once | {O['singletons']:,} | {Nl['singletons']:,} | {O['singletons'] / max(Nl['singletons'], 1):.2f} |",
         f"| share covered by the 200 commonest | {O['top200']:.1%} | {Nl['top200']:.1%} | |", "",
         "## By number of signals present (k)", "",
         "| k | possible combinations C(m,k) | functions | distinct shapes observed | null | observed / null |",
         "|---:|---:|---:|---:|---:|---:|"]
    for k in range(0, max(max(O["byk"]), max(Nl["byk"])) + 1):
        o, nn = O["byk"].get(k, 0), Nl["byk"].get(k, 0)
        if o or nn:
            L.append(f"| {k} | {comb(m, k):,} | {O['fn_byk'].get(k, 0):,} | {o:,} | {nn:,} | {o / nn if nn else float('nan'):.2f} |")
    # pairs
    po = X.mean(0)
    co = (X.T.astype(np.float32) @ X.astype(np.float32)) / len(X)
    ce = (Y.T.astype(np.float32) @ Y.astype(np.float32)) / len(Y)
    rows = []
    for i, j in itertools.combinations(range(m), 2):
        if po[i] >= 0.005 and po[j] >= 0.005:
            exp_n = ce[i, j] * len(X)
            obs_n = co[i, j] * len(X)
            rows.append((S[i], S[j], obs_n, exp_n, np.log((obs_n + 0.5) / (exp_n + 0.5))))
    holes = sorted([r for r in rows if r[3] >= 200], key=lambda r: r[4])[:20]
    attract = sorted(rows, key=lambda r: -r[4])[:15]
    L += ["", f"## Signal pairs (both ≥ 0.5% prevalent: {len(rows)} pairs)", "",
          f"- pairs seen less than 1/10 as often as the null predicts (expected ≥ 200): "
          f"{sum(1 for r in rows if r[3] >= 200 and r[4] < np.log(0.1))}; more than 10×: {sum(1 for r in rows if r[4] > np.log(10))}", "",
          "**Holes** — combinations chance predicts often but code (almost) never builds:", "",
          "| pair | observed | null expects | obs/exp |", "|---|---:|---:|---:|"]
    L += [f"| {short(a_)} + {short(b_)} | {o:,.0f} | {e:,.0f} | {np.exp(v):.3f} |" for a_, b_, o, e, v in holes]
    L += ["", "**Attractions** — combinations built far more often than chance:", "",
          "| pair | observed | null expects | obs/exp |", "|---|---:|---:|---:|"]
    L += [f"| {short(a_)} + {short(b_)} | {o:,.0f} | {e:,.0f} | {np.exp(v):.1f} |" for a_, b_, o, e, v in attract]
    # one-step neighbourhood of the top 200 observed shapes
    top = [k for k, _ in O["counter"].most_common(200)]
    seen = set(O["counter"])
    seen_null = set(Nl["counter"])
    tot_nb = ex_nb = ex_nb_null = 0
    for k in top:
        bits = np.unpackbits(np.frombuffer(k, dtype=np.uint8))[:m].astype(bool)
        for j in range(m):
            nb = bits.copy()
            nb[j] = not nb[j]
            kk = bytes(np.packbits(nb))
            tot_nb += 1
            ex_nb += kk in seen
            ex_nb_null += kk in seen_null
    L += ["", "## One-step neighbourhood of the 200 commonest shapes", "",
          f"- each shape has {m} neighbours (add or drop one signal): {tot_nb:,} neighbour slots. "
          f"**{ex_nb / tot_nb:.0%}** of them exist in real code; {ex_nb_null / tot_nb:.0%} exist in the null population.",
          "", "Caveats: one null draw (no CI); presence only; function-weighted; rules as of b64f42bf (before "
          "#8010/#8011/#8016); a size-only null ignores language idiom beyond per-language rates."]
    (DOCS_DIR / "lattice_null_exploratory.md").write_text("\n".join(L) + "\n")
    (DOCS_DIR / "lattice_null_exploratory.json").write_text(json.dumps({
        "observed": {k: v for k, v in O.items() if k != "counter"}, "null": {k: v for k, v in Nl.items() if k != "counter"},
        "holes": holes, "attract": attract}, default=lambda o: o if not isinstance(o, Counter) else dict(o), indent=1))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
