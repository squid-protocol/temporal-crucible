#!/usr/bin/env python3
"""EXPLORATORY: the agent-habits programs (squid-protocol/agent-habits: 60 programs by Claude Code + Sonnet 5.5,
Claude Code + Haiku 5.5 and Codex, chess + SAT x C/Java/Python/Rust/COBOL) placed on the population fingerprint
lattice and keyword grammar. Scanned with the population engine (b64f42bf) so every comparison is like for like.

    python tools/exploratory/agents_lattice.py --scans <agent_habits_scans/out> --pop <master_db_v2.12.0-b64f42bf.db>
"""
from __future__ import annotations

import argparse
import hashlib
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
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from gr_eval import crucible_grammar  # noqa: E402

SEED, POP_PER_LANG, PERM = 2982, 150_000, 2000
LANGS = ("c", "java", "python", "rust", "cobol")
HOLES = [("arch_api", "def_encapsulation"), ("def_test", "def_encapsulation"), ("def_test", "def_telemetry"),
         ("def_test", "state_bailout_hits")]
ATTRACT = [("arch_events", "def_listeners"), ("state_memory_alloc", "def_cleanup"), ("arch_concurrency", "def_sync_locks"),
           ("state_danger", "state_bailout_hits")]


def model_of(run):
    m = re.match(r"(chess|sat)-([a-z]+)-(claude|sonnet-b|haiku-b|haiku|codex)-r(\d)", run)
    task, lang, who, rep = m.groups()
    model = {"claude": "sonnet", "sonnet-b": "sonnet", "haiku": "haiku", "haiku-b": "haiku", "codex": "codex"}[who]
    rnd = 2 if who.endswith("-b") else 1
    return task, lang, model, rnd, int(rep)


def lattice():
    raw = (DOCS_DIR / "fingerprint_trees_exploratory.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest().startswith("a27d2c93f817")
    D = json.loads(raw)
    sets = [frozenset(s["signals"]) for s in D["shapes"]]
    nn = np.array([s["n"] for s in D["shapes"]], float)
    n = len(sets)
    J = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            u = len(sets[i] | sets[j])
            J[i, j] = J[j, i] = 1 - (len(sets[i] & sets[j]) / u if u else 1)
    fam = fcluster(linkage(squareform(J, checks=False), method="average"), 14, criterion="maxclust")
    U = sorted(set().union(*sets))
    S = np.array([[c in s for c in U] for s in sets], np.int32)
    order = np.argsort(-nn, kind="stable")

    def assign(P, cols):
        X = P[:, [cols.index(c) for c in U]].astype(np.int32)
        inter = X @ S.T
        union = X.sum(1)[:, None] + S.sum(1)[None, :] - inter
        jac = np.where(union > 0, inter / np.maximum(union, 1), 1.0)
        pick = order[np.argmax(jac[:, order], axis=1)]
        return np.where(jac.max(1) > 0, fam[pick], 0), X.sum(1)
    return assign


def gfit(P, cols, w):
    g = np.zeros(len(P))
    for (a, b), v in w.items():
        if a in cols and b in cols:
            xa, xb = P[:, cols.index(a)], P[:, cols.index(b)]
            g += v * (xa & xb)
            if v > 0:
                g -= v * (xa ^ xb)
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scans", required=True)
    ap.add_argument("--pop", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    con = sqlite3.connect(f"file:{a.pop}?mode=ro", uri=True)
    cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
    sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
    q = (f"SELECT f.loc, {', '.join('(COALESCE(f.' + c + ',0) > 0)' for c in sig)} FROM function_data f JOIN file_data fd "
         "ON f.file_id = fd.id WHERE fd.language = ? AND f.loc >= 3")
    pop = {}
    for lg in LANGS:
        rows = con.execute(q, (lg,)).fetchall()
        if len(rows) > POP_PER_LANG:
            rows = [rows[i] for i in rng.choice(len(rows), POP_PER_LANG, replace=False)]
        pop[lg] = (np.array([r[0] for r in rows], float), np.array([r[1:] for r in rows], bool))
        print(f"  population {lg}: {len(rows):,}", flush=True)
    con.close()
    assign = lattice()
    w = crucible_grammar(POOL_DIR / "kw_scan" / "data_galaxy_master.db")
    # agent functions
    A = []
    for d in sorted(pathlib.Path(a.scans).iterdir()):
        dbs = list(d.rglob("*.db"))
        if not dbs:
            continue
        task, lang, model, rnd, rep = model_of(d.name)
        c2 = sqlite3.connect(f"file:{dbs[0]}?mode=ro", uri=True)
        have = {c[1] for c in c2.execute("PRAGMA table_info(function_data)")}
        rows = c2.execute(f"SELECT f.loc, {', '.join(('(COALESCE(f.' + c + ',0) > 0)') if c in have else '0' for c in sig)} "
                          "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE f.loc >= 3 AND fd.language = ?",
                          (lang,)).fetchall()
        c2.close()
        for r in rows:
            A.append((d.name, task, lang, model, rnd, float(r[0]), np.array(r[1:], bool)))
    runs = sorted({x[0] for x in A})
    print(f"  agent functions {len(A):,} in {len(runs)} programs", flush=True)
    P = np.array([x[6] for x in A])
    loc = np.array([x[5] for x in A])
    M = np.array([x[3] for x in A])
    LG = np.array([x[2] for x in A])
    RUN = np.array([x[0] for x in A])
    fam, k = assign(P, sig)
    G = gfit(P, sig, w)
    # grammar-fit percentile vs population, same language x size bin x signals-present (capped 8)
    pct = np.full(len(A), np.nan)
    hole_rate, pop_rates = defaultdict(dict), {}
    pfam = {}
    for lg in LANGS:
        pl, pp = pop[lg]
        pf, pk = assign(pp, sig)
        pfam[lg] = (pf, pk)
        pg = gfit(pp, sig, w)
        pst = np.array([f"{int(np.floor(np.log10(x) / 0.2))}|{min(n, 8)}" for x, n in zip(pl, pp.sum(1))])
        by = defaultdict(list)
        for s, g in zip(pst, pg):
            by[s].append(g)
        by = {s: np.sort(v) for s, v in by.items() if len(v) >= 200}
        for i in np.flatnonzero(LG == lg):
            s = f"{int(np.floor(np.log10(loc[i]) / 0.2))}|{min(int(P[i].sum()), 8)}"
            if s in by:
                v = by[s]
                pct[i] = (np.searchsorted(v, G[i], "left") + np.searchsorted(v, G[i], "right")) / 2 / len(v)
        for x, y in HOLES + ATTRACT:
            pop_rates[(lg, x, y)] = float((pp[:, sig.index(x)] & pp[:, sig.index(y)]).mean())
    models = ("sonnet", "haiku", "codex")
    L = ["# EXPLORATORY — agent-written code on the fingerprint lattice and keyword grammar", "",
         "Programs: [squid-protocol/agent-habits](https://github.com/squid-protocol/agent-habits) (60 autonomous runs; "
         "Claude Code + Sonnet 5.5 ×2 rounds, Claude Code + Haiku 5.5 ×2 rounds, Codex gpt-6-luna; chess engine + SAT "
         "solver × C, Java, Python, Rust, COBOL). Rescanned with the population engine `b64f42bf` (git history off); "
         "compared with a 150k-function sample per language of the v2.12.0 population (mostly human-written open source). "
         "Exploratory: these 60 programs already produced the agent-habits findings.", "",
         f"- programs read: {len(runs)} of 60; functions (loc ≥ 3): {len(A):,} — " + ", ".join(f"{m} {int((M == m).sum()):,}" for m in models), ""]
    # 1. lattice placement
    L += ["## 1. Where agent functions sit on the lattice (share of functions; population = same languages, weighted to each model's language mix)", "",
          "| | rung k ≤ 3 | k 4–5 | k ≥ 6 | median k | F7 public/general | F8 private-C | F6 bare one-step | other / unassigned |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]

    def row(name, f_, k_):
        return (f"| {name} | {np.mean(k_ <= 3):.0%} | {np.mean((k_ >= 4) & (k_ <= 5)):.0%} | {np.mean(k_ >= 6):.0%} | {np.median(k_):.0f} | "
                f"{np.mean(f_ == 7):.0%} | {np.mean(f_ == 8):.0%} | {np.mean(f_ == 6):.0%} | {np.mean(~np.isin(f_, [6, 7, 8])):.0%} |")
    for m in models:
        mm = M == m
        L.append(row(m, fam[mm], k[mm]))
        # population matched to this model's language mix
        pf_, pk_ = [], []
        for lg, cnt in Counter(LG[mm]).items():
            f0, k0 = pfam[lg]
            pick = rng.choice(len(f0), cnt, replace=True)
            pf_.append(f0[pick]); pk_.append(k0[pick])
        L.append(row(f"population, {m}'s language mix", np.concatenate(pf_), np.concatenate(pk_)))
    # 2. grammar
    L += ["", "## 2. Do agents follow the human keyword grammar? (fit percentile among population functions of the same language, size and signal count; 50% = typical)", "",
          "| | functions compared | median percentile | in the bottom 10% (grammar-breaking) | in the top 10% |", "|---|---:|---:|---:|---:|"]
    for m in models:
        v = pct[(M == m) & np.isfinite(pct)]
        L.append(f"| {m} | {len(v):,} | {np.median(v):.0%} | {np.mean(v <= 0.10):.1%} | {np.mean(v >= 0.90):.1%} |")
    L.append("| population (by construction) | — | 50% | 10% | 10% |")
    # 3. holes and attractions
    L += ["", "## 3. Combinations human code avoids (holes) and favours (attractions): rate per model vs population, same language mix", "",
          "| pair | kind | " + " | ".join(f"{m} (pop)" for m in models) + " |", "|---|---|" + "---:|" * len(models)]
    for (x, y), kind in [(p, "hole") for p in HOLES] + [(p, "attraction") for p in ATTRACT]:
        cells = []
        for m in models:
            mm = M == m
            obs = float((P[mm][:, sig.index(x)] & P[mm][:, sig.index(y)]).mean())
            exp = float(np.mean([pop_rates[(lg, x, y)] for lg in LG[mm]]))
            cells.append(f"{obs:.1%} ({exp:.1%})")
        L.append(f"| {x} + {y} | {kind} | " + " | ".join(cells) + " |")
    # 4. identification by family mix
    bands = lambda kk: np.where(kk <= 3, 0, np.where(kk <= 5, 1, 2))  # noqa: E731
    cats = sorted({(int(f), int(b)) for f, b in zip(fam, bands(k))})
    prog = {}
    for r in runs:
        mm = RUN == r
        v = np.array([np.mean((fam[mm] == f) & (bands(k[mm]) == b)) for f, b in cats])
        task, lang, model, rnd, rep = model_of(r)
        prog[r] = (task, lang, model, v)

    def ident(labels):
        hits = tot = 0
        chance = []
        for r, (t, lg, m, v) in prog.items():
            cand = [q for q, (t2, l2, _, _) in prog.items() if q != r and t2 == t and l2 == lg]
            if not any(labels[q] == labels[r] for q in cand):
                continue
            best = min(cand, key=lambda q: np.abs(prog[q][3] - v).sum())
            hits += labels[best] == labels[r]
            tot += 1
            chance.append(np.mean([labels[q] == labels[r] for q in cand]))
        return hits, tot, float(np.mean(chance)) if chance else float("nan")
    lab = {r: p[2] for r, p in prog.items()}
    h, t, ch = ident(lab)
    cells = defaultdict(list)
    for r, p in prog.items():
        cells[(p[0], p[1])].append(r)
    ge = 0
    for _ in range(PERM):
        lp = dict(lab)
        for rs in cells.values():
            vals = [lab[r] for r in rs]
            for r, v in zip(rs, rng.permutation(vals)):
                lp[r] = v
        ge += ident(lp)[0] >= h
    L += ["", "## 4. Does the family mix identify the model? (nearest program in the same task × language by lattice family × rung mix)", "",
          f"- same-model nearest neighbour **{h} of {t} ({h / max(t, 1):.0%})**; chance {ch:.0%}; label permutation within cells p = {(1 + ge) / (1 + PERM):.4f} ({PERM} draws)",
          "- for comparison, agent-habits' sfs structure lens: 43 of 52 (83%), chance 27% (exploratory there too)", "",
          "Caveats: exploratory and post hoc on programs that already informed agent-habits; 10 cells; Codex has one round. "
          "Population comparisons use mostly human-written open source of every size and purpose, so differences mix "
          "authorship with task (chess/SAT solvers are algorithmic code)."]
    (DOCS_DIR / "agents_lattice_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
