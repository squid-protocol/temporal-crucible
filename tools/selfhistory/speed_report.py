#!/usr/bin/env python3
"""Summarize speed/runs.jsonl: median over repeats per (slot, target), spread, stage table, and a
per-stage view. Prints markdown; also writes speed/summary.json."""
import json, statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "speed" / "runs.jsonl").open()]
ok = [r for r in rows if not r.get("exit")]
bad = [r for r in rows if r.get("exit")]
g = defaultdict(list)
for r in ok:
    g[(r["slot"], r["target"])].append(r)
slots = sorted({r["slot"] for r in rows})
dates = {r["slot"]: r["date"] for r in rows}
targets = ["keyword-rosetta", "cics-crucible", "language-crucible"]


def med(rs, k):
    v = [r[k] for r in rs if r.get(k) is not None]
    return (st.median(v), (max(v) - min(v)) / st.median(v) * 100 if len(v) > 1 and st.median(v) else 0, len(v)) if v else None


summary = {}
print(f"{len(ok)} good runs, {len(bad)} failed\n")
for t in targets:
    print(f"### {t}: median of repeats (engine's own pipeline seconds; spread = (max-min)/median)\n")
    print("| slot | date | files mapped | pipeline s | spread % | wall s | LOC/s | stages timed |")
    print("|---|---|---|---|---|---|---|---|")
    for s in slots:
        rs = g.get((s, t), [])
        if not rs:
            print(f"| {s} | {dates[s]} | — | — | — | — | — | (no good run) |"); continue
        p, sp, n = med(rs, "pipeline_s") or (None, 0, 0)
        f = med(rs, "files_mapped"); w = med(rs, "wall_s"); l = med(rs, "loc_per_s")
        nph = len(rs[0].get("phases", {}))
        summary[f"{s}/{t}"] = {"date": dates[s], "files": f and f[0], "pipeline_s": p, "spread_pct": round(sp, 1), "wall_s": w and w[0], "loc_per_s": l and l[0], "n": n}
        print(f"| {s} | {dates[s]} | {int(f[0]) if f else '—'} | {p} | {sp:.0f} | {w[0] if w else '—'} | {int(l[0]) if l else '—'} | {nph or '—'} |")
    print()
print("### Per-stage cumulative seconds, language-crucible (median of repeats)\n")
stages = sorted({k for r in ok for k in r.get("phases", {})})
if stages:
    print("| slot | " + " | ".join(stages) + " |"); print("|---|" + "---|" * len(stages))
    for s in slots:
        rs = g.get((s, "language-crucible"), [])
        if not rs: continue
        cells = []
        for k in stages:
            v = [r["phases"][k]["total_s"] for r in rs if k in r.get("phases", {})]
            cells.append(f"{st.median(v):.2f}" if v else "—")
        print(f"| {s} {dates[s]} | " + " | ".join(cells) + " |")
if bad:
    print("\n### Failures\n")
    for r in bad: print(f"- {r['slot']} {r['target']} rep{r['rep']} exit={r['exit']} {r.get('tail','')[:160]!r}")
(HERE / "speed" / "summary.json").write_text(json.dumps(summary, indent=1))
