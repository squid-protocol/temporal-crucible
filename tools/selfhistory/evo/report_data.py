#!/usr/bin/env python3
"""EXPLORATORY: call-network density, documentation/comment trends and comment-only edits for GitGalaxy's engine code (same unit rule as evo/analyze.py)."""
import sys, pickle, json, glob, sqlite3, datetime as dt, collections, statistics as st
sys.path.insert(0, "/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from pathlib import Path
import numpy as np
H = Path("/srv/storage_16tb/projects/gitgalaxy-history")
def unit(p):
    q = p.replace("backend/", "gitgalaxy/", 1) if p.startswith("backend/") else p
    return q.startswith("gitgalaxy/") and "/tests/" not in q and "/standards/" not in q and "gitgalaxy_standards" not in q and not q.endswith("__init__.py")
def era(d):
    d = dt.date.fromisoformat(d)
    return "gemini" if d < dt.date(2026, 7, 6) else "transition" if d < dt.date(2026, 7, 22) else "claude" if d < dt.date(2026, 9, 27) else "fleet"
dbs = sorted(glob.glob(str(H / "dbs" / "*.db")))
series = []
for k in list(range(0, len(dbs), 6)) + [len(dbs) - 1]:
    f = dbs[k]; c = sqlite3.connect(f"file:{f}?mode=ro&immutable=1", uri=True)
    cols = {r[1] for r in c.execute("pragma table_info(function_data)")}
    sel = ["fn.loc", "f.file_path"] + [("fn." + x) if x in cols else "NULL" for x in ("func_fan_in", "func_fan_out", "is_documented", "has_header_comment", "docstring")]
    rows = c.execute(f"select {', '.join(sel)} from function_data fn join file_data f on fn.file_id=f.id").fetchall(); c.close()
    rows = [r for r in rows if unit(r[1]) and (r[0] or 0) >= 3]
    n = len(rows)
    if not n: continue
    fi = np.array([r[2] or 0 for r in rows], float); fo = np.array([r[3] or 0 for r in rows], float)
    doc = np.array([1 if (r[4] or 0) else 0 for r in rows]); hdr = np.array([1 if (r[5] or 0) else 0 for r in rows])
    dw = np.array([len((r[6] or "").split()) for r in rows]); has = dw > 0
    top = np.sort(fi)[::-1]; k1 = max(1, n // 100)
    series.append({"date": Path(f).name[:10], "n": n, "calls_per_func": round(float(fo.sum()) / n, 3), "mean_fan_in": round(float(fi.mean()), 3), "uncalled": round(float((fi == 0).mean()), 3),
                   "top1_fanin_share": round(float(top[:k1].sum() / max(fi.sum(), 1)), 3), "documented": round(float(doc.mean()), 3), "header_comment": round(float(hdr.mean()), 3),
                   "has_docstring": round(float(has.mean()), 3), "mean_doc_words": round(float(dw[has].mean()), 1) if has.any() else 0})
json.dump(series, open(H / "evo" / "report_series.json", "w"), indent=1)
by = collections.defaultdict(list)
for s in series: by[era(s["date"])].append(s)
print("ERA MEANS of per-snapshot values (every 6th daily snapshot)")
for e in ("gemini", "transition", "claude", "fleet"):
    v = by.get(e)
    if v: print(f" {e:10s} n_snap={len(v)} funcs {int(st.mean(x['n'] for x in v)):5d} | calls/func {st.mean(x['calls_per_func'] for x in v):.2f} mean fan-in {st.mean(x['mean_fan_in'] for x in v):.2f} uncalled {st.mean(x['uncalled'] for x in v):.0%} top1% fan-in share {st.mean(x['top1_fanin_share'] for x in v):.0%} | documented {st.mean(x['documented'] for x in v):.0%} header-comment {st.mean(x['header_comment'] for x in v):.0%} docstring {st.mean(x['has_docstring'] for x in v):.0%} ({st.mean(x['mean_doc_words'] for x in v):.0f} words)")
print("first:", series[0]); print("last:", series[-1])
# lineage cohorts from the ledger: documentation at birth and 30 days later; comment-only edits
led = pickle.load(open(H / "evo" / "ledger_all.pkl", "rb"))
S = len(led.ids); date = [dt.date.fromisoformat(s.label) for s in led.snapshots]
doc = [[(m[2] if m else "") for m in led._snaps[s].meta] for s in range(S)]
pos = [dict((int(l), i) for i, l in enumerate(led.ids[s])) for s in range(S)]
first = {}
for s in range(S):
    for i, l in enumerate(led.ids[s]):
        first.setdefault(int(l), (s, i))
res = collections.defaultdict(lambda: collections.Counter())
for l, (b, i) in first.items():
    if b == 0 or not unit(led.keys[b][i][0]): continue
    tgt = date[b] + dt.timedelta(days=30); s2 = next((s for s in range(b + 1, S) if date[s] >= tgt), None)
    if s2 is None: continue
    j = pos[s2].get(l)
    if j is None: continue
    d0, d1 = bool(doc[b][i]), bool(doc[s2][j]); e = era(str(date[b])); r = res[e]
    r["n"] += 1; r["doc_birth"] += d0; r["doc_30"] += d1; r["gained"] += (not d0 and d1); r["lost"] += (d0 and not d1); r["text_changed"] += (d0 and d1 and doc[b][i] != doc[s2][j])
print("\nDOCSTRING AT BIRTH vs 30 DAYS LATER (functions of 3+ lines, engine units, alive at +30d)")
for e in ("gemini", "claude", "fleet"):
    r = res[e]
    if r["n"]: print(f" {e:7s} n={r['n']:4d}: documented at birth {r['doc_birth']/r['n']:.0%}, at +30d {r['doc_30']/r['n']:.0%}; gained {r['gained']/r['n']:.0%}, lost {r['lost']/r['n']:.0%}; docstring text changed (of those documented at both) {r['text_changed']/max(r['doc_birth']-r['lost'],1):.0%}")
ev = pickle.load(open(H / "evo" / "self_edits.pkl", "rb"))["gitgalaxy"]["events"]
tot = collections.Counter(era(e["date"]) for e in ev); co = collections.Counter(era(e["date"]) for e in ev if not e["code"])
print("\nTEXT-CHANGED FUNCTION EDITS that touch only comments/whitespace (no token change):", sum(co.values()), "of", sum(tot.values()), f"= {sum(co.values())/sum(tot.values()):.1%}", {k: f"{co[k]}/{tot[k]}" for k in tot})
json.dump({"era_docs": {e: dict(r) for e, r in res.items()}, "comment_only": dict(co), "text_changed": dict(tot)}, open(H / "evo" / "report_cohorts.json", "w"), indent=1)
