#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The missing half of label validation: RECALL. Draw from what the label calls NOT a fix.

    python tools/recall_sample.py --repos curl --n 40 --seed 2986     # draw and print for judging
    python tools/recall_sample.py --score docs/recall_judgments.json  # turn judgments into recall

Every audit this programme has run measures PRECISION: of the commits we call fixes, how many are real. None
measures RECALL: of the real fixes, how many do we catch. The two are not interchangeable, and the cleaning
rule that lifted precision (v3c rule C: require a fix word in the subject) is exactly the kind that destroys
recall -- "Don't create an ack frame if one isn't wanted" is a real fix whose subject never says fix.

Estimator. With P commits labelled fix at measured precision p, and N labelled not-fix of which a sampled
fraction q are really fixes:

    true fixes  ~  P*p + N*q          recall  ~  P*p / (P*p + N*q)

q is what this samples. Because N is large, recall is very sensitive to q: at curl's numbers a q of 0.05
rather than 0.02 moves recall by about 15 points, so the sample has to be big enough to pin it and the
interval must be reported, never the point alone.

Judging uses the SUBJECT AND BODY (tools/hist_meta.py), unlike the precision audits, which saw one line.
That difference is itself worth reporting.
"""
from __future__ import annotations

import argparse, json, math, random, sqlite3
from pathlib import Path

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")


def draw(repo: str, n: int, seed: int):
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{repo}.db'}?mode=ro", uri=True)
    rows = [(s, sub or "") for s, sub in
            h.execute("select sha, subject from commit_ where fix=0 and merge=0 and bot=0")]
    npool = len(rows)
    h.close()
    bodies = {}
    mdb = STUDY / "meta" / f"{repo}.db"
    if mdb.exists():
        m = sqlite3.connect(f"file:{mdb}?mode=ro", uri=True)
        bodies = {s: b for s, b in m.execute("select sha, body from body")}
        m.close()
    rnd = random.Random(seed)
    pick = rnd.sample(rows, min(n, len(rows)))
    return npool, [(s, sub, (bodies.get(s) or "").strip()) for s, sub in pick]


def recall(P: int, p: float, N: int, k: int, n: int) -> dict:
    """k of n sampled not-fix commits were really fixes."""
    q = k / n
    lo_q = max(0.0, q - 1.96 * math.sqrt(q * (1 - q) / n))
    hi_q = min(1.0, q + 1.96 * math.sqrt(q * (1 - q) / n))
    f = lambda qq: (P * p) / (P * p + N * qq) if (P * p + N * qq) else None
    return {"q": round(q, 4), "q_ci95": [round(lo_q, 4), round(hi_q, 4)],
            "missed_est": round(N * q), "caught_est": round(P * p),
            "recall": round(f(q), 3), "recall_ci95": [round(f(hi_q), 3), round(f(lo_q), 3)]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default="curl")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=2986)
    ap.add_argument("--score", type=Path, help="JSON: {repo: {P,p,N,k,n}} -> recall")
    a = ap.parse_args()
    if a.score:
        d = json.loads(a.score.read_text())
        print(f"{'repo':14}{'q':>8}{'missed':>9}{'caught':>9}{'recall':>9}  95% CI")
        for r, x in d.items():
            o = recall(x["P"], x["p"], x["N"], x["k"], x["n"])
            print(f"{r:14}{o['q']:>8.3f}{o['missed_est']:>9,}{o['caught_est']:>9,}"
                  f"{o['recall']:>9.3f}  {o['recall_ci95']}")
        return 0
    for r in a.repos.split(","):
        npool, rows = draw(r, a.n, a.seed)
        print(f"\n## {r} — {len(rows)} of {npool:,} commits the label calls NOT a fix (seed {a.seed})\n")
        print("Judge each: does this commit repair behaviour that was wrong? Subject AND body shown.\n")
        for s, sub, body in rows:
            first = " / ".join(l.strip() for l in body.split("\n") if l.strip())[:220]
            print(f"- [ ] `{s[:10]}` {sub[:110]}")
            if first:
                print(f"       body: {first}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
