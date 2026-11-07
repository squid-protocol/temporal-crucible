#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""OUT-H1..H2 (docs/out_hypotheses.md): grammar outliers in the population.

    python tools/out_eval.py prepare --pop <db> --crucible <kw_scan db>   # H2 + audit packets (code only)
    python tools/out_eval.py score   --pop <db> --crucible <kw_scan db>   # after blind labels are hash-locked
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.stats import fisher_exact

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from gr_eval import crucible_grammar  # noqa: E402

PRIV = POOL_DIR / "vz_private"
CORPUS = pathlib.Path("/nvme-data/gitgalaxy-data")
SEED, ALPHA, N_AUDIT = 2982, 0.01 / 2, 40
FLAG_VG = re.compile(r"(^|/)(vendor|vendored|third_party|thirdparty|3rdparty|external|deps|node_modules|dist|build|generated|gen|autogen)(/|$)|\.min\.|_pb2\.py$|\.pb\.(go|cc|h)$", re.I)
FLAG_T = re.compile(r"(^|/)(test|tests|testing|spec|fixture|fixtures)(/|$)", re.I)
CATS = ("ordinary hand-written", "generated", "minified or bundled", "vendored third-party", "test or fixture",
        "obfuscated or suspicious", "data table or declarative", "unclear")


def load(pop, w):
    sigs = sorted({s for p in w for s in p})
    con = sqlite3.connect(f"file:{pop}?mode=ro", uri=True)
    cols = {c[1] for c in con.execute("PRAGMA table_info(function_data)")}
    threat = [c for c in cols if c.startswith("threat_")]
    q = (f"SELECT fd.language, fd.repo_name, fd.file_path, f.func_name, f.start_line, f.loc, "
         f"{', '.join('(f.' + s + ' > 0)' for s in sigs)}, ({' + '.join('COALESCE(f.' + c + ',0)' for c in threat) or '0'}) > 0 "
         "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3")
    cur = con.execute(q)
    pairs = [(sigs.index(a), sigs.index(b), v) for (a, b), v in w.items()]
    meta, G, NP, TH = [], [], [], []
    while True:
        rows = cur.fetchmany(250_000)
        if not rows:
            break
        X = np.array([r[6:6 + len(sigs)] for r in rows], dtype=bool)
        g = np.zeros(len(rows))
        for a, b, v in pairs:
            both = X[:, a] & X[:, b]
            g += v * both
            if v > 0:
                g -= v * (X[:, a] ^ X[:, b])
        G.append(g)
        NP.append(np.minimum(X.sum(1), 8))
        TH.append(np.array([bool(r[-1]) for r in rows]))
        meta += [r[:6] for r in rows]
        print(f"  {len(meta):,} ({time.time() - T0:.0f}s)", flush=True)
    con.close()
    return sigs, pairs, meta, np.concatenate(G), np.concatenate(NP), np.concatenate(TH)


def repo_dir(repo, path, cache={}):
    if repo not in cache:
        cands = [CORPUS / repo] + sorted(CORPUS.glob(f"*/{repo}")) + sorted(CORPUS.glob(f"*/*/{repo}"))
        cache[repo] = [c for c in cands if c.is_dir()]
    for c in cache[repo]:
        if (c / path).is_file():
            return c / path
    return None


def code(repo, path, start, loc):
    f = repo_dir(repo, path)
    if not f:
        return None
    lines = f.read_text(errors="replace").split("\n")
    return "\n".join(lines[max(start - 1, 0): max(start - 1, 0) + min(max(loc, 5) + 2, 150)])


T0 = time.time()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("prepare", "score"))
    ap.add_argument("--pop", required=True)
    ap.add_argument("--crucible", required=True)
    a = ap.parse_args()
    w = crucible_grammar(a.crucible)
    sigs, pairs, meta, G, NP, TH = load(a.pop, w)
    lang = np.array([m[0] for m in meta])
    loc = np.array([float(m[5]) for m in meta])
    st = np.array([f"{l}|{int(np.floor(np.log10(x) / 0.2))}|{n}" for l, x, n in zip(lang, loc, NP)])
    from scipy.stats import rankdata
    pct = np.full(len(meta), np.nan)
    order = np.argsort(st, kind="stable")
    sst = st[order]
    bounds = np.flatnonzero(np.r_[True, sst[1:] != sst[:-1], True])
    for i in range(len(bounds) - 1):
        ii = order[bounds[i]:bounds[i + 1]]
        if len(ii) >= 1000:
            pct[ii] = (rankdata(G[ii]) - 0.5) / len(ii)
    out = pct <= 0.001
    ctl = (pct >= 0.4) & (pct <= 0.6)
    valid = np.isfinite(pct)
    paths = [m[2] for m in meta]
    fvg = np.array([bool(FLAG_VG.search(p or "")) for p in paths])
    ft = np.array([bool(FLAG_T.search(p or "")) for p in paths])
    flag = fvg | ft
    # H2: indirect standardisation (expected flag rate of each outlier's stratum, over all valid functions there)
    rate = defaultdict(lambda: [0, 0])
    for s, f_, v in zip(st, flag, valid):
        if v:
            r_ = rate[s]
            r_[0] += f_
            r_[1] += 1
    oi = np.flatnonzero(out)
    exp = np.array([rate[st[i]][0] / rate[st[i]][1] for i in oi])
    obs = flag[oi].astype(float)
    ratio = obs.sum() / exp.sum()
    rng = np.random.default_rng(SEED)
    bs = []
    for _ in range(2000):
        k = rng.integers(0, len(oi), len(oi))
        bs.append(obs[k].sum() / exp[k].sum())
    lo2 = float(np.quantile(bs, ALPHA))
    v2 = "SUPPORTED" if ratio >= 1.5 and lo2 > 1 else "not supported"
    # descriptive: most violated pairs among outliers
    viol = Counter()
    L = ["# OUT-H1..H2 — grammar outliers in the population (SCORED; aggregates only)", "",
         f"- functions {len(meta):,}; in strata ≥ 1,000: {int(valid.sum()):,}; outliers (bottom 0.1%) {int(out.sum()):,}", "",
         "| claim | result | verdict |", "|---|---|---|",
         f"| **OUT-H2** outliers concentrate in vendored/generated/test paths | flagged {obs.mean():.1%} vs stratum-expected {exp.mean():.1%}: **{ratio:.2f}×** (lo {lo2:.2f}); "
         f"vendored/generated {fvg[oi].mean():.1%}, test {ft[oi].mean():.1%} | **{v2}** |"]
    keys = PRIV / "out_audit_keys.json"
    if a.mode == "prepare":
        rnd = random.Random(SEED)
        cand = list(oi)
        rnd.shuffle(cand)
        by_st = defaultdict(list)
        for i in np.flatnonzero(ctl):
            by_st[st[i]].append(i)
        units = []
        for i in cand:
            if len(units) >= 2 * N_AUDIT:
                break
            c_pool = by_st.get(st[i], [])
            if not c_pool:
                continue
            j = rnd.choice(c_pool)
            ci, cj = code(meta[i][1], meta[i][2], meta[i][4], meta[i][5]), code(meta[j][1], meta[j][2], meta[j][4], meta[j][5])
            if ci and cj:
                units += [(int(i), "outlier", ci), (int(j), "control", cj)]
        rnd.shuffle(units)
        packets = [{"id": k, "language": meta[u[0]][0], "code": u[2]} for k, u in enumerate(units)]
        (PRIV / "out_audit_packets.json").write_text(json.dumps(packets, indent=1))
        keys.write_text(json.dumps([{"id": k, "kind": u[1], "repo": meta[u[0]][1], "path": meta[u[0]][2], "func": meta[u[0]][3]} for k, u in enumerate(units)], indent=1))
        L.append(f"- audit packets {len(packets)} (code only; private)")
    else:
        K = {k["id"]: k for k in json.loads(keys.read_text())}
        lab = {l["id"]: l["label"] for l in json.loads((PRIV / "out_audit_labels.json").read_text())}
        tab = defaultdict(Counter)
        for i, k in K.items():
            if lab.get(i) and lab[i] != "unclear":
                tab[k["kind"]][lab[i]] += 1
        no, nc = sum(tab["outlier"].values()), sum(tab["control"].values())
        oo, oc = tab["outlier"]["ordinary hand-written"], tab["control"]["ordinary hand-written"]
        p = fisher_exact([[oo, no - oo], [oc, nc - oc]], alternative="less")[1]
        gap = oc / max(nc, 1) - oo / max(no, 1)
        v1 = "SUPPORTED" if gap >= 0.20 and p < ALPHA else "not supported"
        L.append(f"| **OUT-H1** outliers rarely ordinary hand-written (blind audit) | ordinary: outliers {oo}/{no} = {oo / max(no, 1):.0%} vs controls {oc}/{nc} = {oc / max(nc, 1):.0%}; gap {gap:+.0%}; p = {p:.2g} | **{v1}** |")
        L += ["", "Audit categories — outliers: " + ", ".join(f"{c} {n}" for c, n in tab["outlier"].most_common()),
              "Audit categories — controls: " + ", ".join(f"{c} {n}" for c, n in tab["control"].most_common())]
    by_lang = Counter(lang[oi])
    L += ["", "## Descriptive", "", f"- outliers with engine threat signals: {TH[oi].mean():.1%} vs all valid {TH[valid].mean():.1%}",
          "- outliers by language (top): " + ", ".join(f"{l} {n}" for l, n in by_lang.most_common(8)),
          "- repos with most outliers: " + ", ".join(f"{r} {n}" for r, n in Counter(meta[i][1] for i in oi).most_common(8)),
          "", f"Runtime {time.time() - T0:.0f}s · seed {SEED}."]
    (DOCS_DIR / ("out.md" if a.mode == "score" else "out_prepare.md")).write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
