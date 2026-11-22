#!/usr/bin/env python3
"""EXPLORATORY: mass-migration (sweep) analysis of GitGalaxy's engine code, TURN method (tools: curl_call_graph_evolution/turn_v2/analysis/ts_edits2.py + sweeps.py).
Each linked function pair across consecutive daily snapshots whose text changed is parsed with tree-sitter (Python); edits are classified by call/node deltas.
Sweep window = ISO week (daily pairs are too short; TURN used quarters). A sweep = the same call changed in >= max(10, 1%) of a week's code-edited functions.
Units = the same engine units as evo/analyze.py (gitgalaxy/ or backend/, no tests, no standards/, no __init__), .py only, both ends."""
import sys, pickle, json, datetime as dt, collections
sys.path.insert(0, "/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/analysis")
sys.path.insert(0, "/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from pathlib import Path
import numpy as np
from structural_fingerprint import ledger as LG
import ts_edits2 as T2, sweeps as SW
H = Path("/srv/storage_16tb/projects/gitgalaxy-history")
led = pickle.load(open(H / "evo" / "ledger_all.pkl", "rb"))
def unit(p):
    q = p.replace("backend/", "gitgalaxy/", 1) if p.startswith("backend/") else p
    return q.startswith("gitgalaxy/") and q.endswith(".py") and "/tests/" not in q and "/standards/" not in q and "gitgalaxy_standards" not in q and not q.endswith("__init__.py")
date = [dt.date.fromisoformat(s.label) for s in led.snapshots]
def week(d): y, w, _ = d.isocalendar(); return (y, w)
weeks = sorted({week(d) for d in date}); widx = {w: i for i, w in enumerate(weeks)}
labels = [f"{y}-W{w:02d}" for y, w in weeks]
ev = []; total = 0
for s, link in enumerate(led.links):
    a, b = led._snaps[s], led._snaps[s + 1]
    for x, lk in link.items():
        pa, na = a.keys[x]; pb, nb = b.keys[lk.new]
        if not (unit(pa) and unit(pb)): continue
        ma, mb = a.meta[x], b.meta[lk.new]
        if not ma or not mb or ma[0] < 1 or mb[0] < 1: continue
        la, lb = a.git.lines(a.snap.commit, pa), b.git.lines(b.snap.commit, pb)
        if la is None or lb is None: continue
        total += 1
        ra = "\n".join(la[ma[0] - 1:ma[0] - 1 + ma[1]]); rb = "\n".join(lb[mb[0] - 1:mb[0] - 1 + mb[1]])
        if ra == rb: continue
        ta = LG.body_tokens(la, pa, na, ma[0], ma[1]); tb = LG.body_tokens(lb, pb, nb, mb[0], mb[1])
        e = dict(s=widx[week(date[s + 1])], year=2026, date=str(date[s + 1]), id=int(led.ids[s][x]), stage=lk.stage, code=(ta != tb), dloc=mb[1] - ma[1], path=pb)
        if e["code"]:
            ca, ka, sa = T2.feats(ra, "python"); cb, kb, sb = T2.feats(rb, "python")
            e["d"] = {k: cb[k] - ca[k] for k in set(ca) | set(cb) if cb[k] != ca[k]}
            e["sig"] = bool(sa and sb and sa.replace(na, "@") != sb.replace(nb, "@")); e["add"] = dict(kb - ka); e["rem"] = dict(ka - kb)
        ev.append(e)
code = [e for e in ev if e["code"]]
print("linked pairs examined:", total, "| text changed:", len(ev), "| code edits (token change):", len(code), flush=True)
R = {"gitgalaxy": dict(name="gitgalaxy", lang="python", events=ev, total=total, labels=labels)}
pickle.dump(R, open(H / "evo" / "self_edits.pkl", "wb"))
SW.labels = lambda name: labels
SW.show(str(H / "evo" / "self_edits.pkl"))
# era split (Gemini < 07-06, Claude 07-22..09-26, fleet >= 09-27) of sweep share
migr, one, ins = SW.detect(ev)
def era(d): d = dt.date.fromisoformat(d); return "gemini" if d < dt.date(2026, 7, 6) else "transition" if d < dt.date(2026, 7, 22) else "claude" if d < dt.date(2026, 9, 27) else "fleet"
tot = collections.Counter(era(ev[i]["date"]) for i, e in enumerate(ev) if e["code"]); sw = collections.Counter(era(ev[i]["date"]) for i in ins)
print("share of code edits in sweeps by era:", {k: f"{sw[k]}/{tot[k]} = {sw[k]/max(tot[k],1):.0%}" for k in tot})
json.dump({"code_edits": len(code), "in_sweep": len(ins), "migrations": migr, "one_sided": one, "era": {k: [sw[k], tot[k]] for k in tot}, "weeks": labels}, open(H / "evo" / "self_sweeps.json", "w"), indent=1)
