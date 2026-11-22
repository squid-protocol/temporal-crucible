#!/usr/bin/env python3
"""Apply the pre-declared detection rule (docs/self_sensitivity_plan.md) to dense.jsonl + sens.jsonl. Writes speed/steps_detected.{json,md}."""
import json, statistics as st, subprocess, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows = []
for f in ("dense.jsonl", "sens.jsonl"):
    p = HERE / "speed" / f
    if p.exists(): rows += [json.loads(l) for l in p.open()]
anch = defaultdict(list); series = defaultdict(dict)
for r in rows:
    t = r["target"]
    if r.get("anchor_n") is not None:
        if not r.get("exit") and r.get("cpu_s"): anch[t].append(r["cpu_s"])
        continue
    i = r["fp_index"]
    if (not r.get("exit")) and r.get("cpu_s") is not None:
        series[t][i] = {"cpu": r["cpu_s"], "files": r.get("files_mapped"), "funcs": r.get("out_funcs"), "sha": r["sha"], "date": r["date"]}
    else:
        series[t].setdefault(i, {"failed": True, "sha": r["sha"], "date": r["date"]})
T = {}
for t in ["keyword-rosetta", "cics-crucible", "onepl", "language-crucible"]:
    a = anch.get(t, [])
    dev = max(abs(x - st.median(a)) / st.median(a) for x in a) if len(a) >= 2 else 0.0
    T[t] = max(0.10, 4 * dev)
cands, unresolved, ramps = [], [], []
for t, s in series.items():
    idx = sorted(s)
    prev = None
    for i in idx:
        cur = s[i]
        if cur.get("failed"):
            unresolved.append({"corpus": t, "index": i, "date": cur["date"], "sha": cur["sha"]}); continue
        if prev is not None:
            pc = s[prev]
            dc = (cur["cpu"] - pc["cpu"]) / pc["cpu"]
            df = ((cur["files"] - pc["files"]) / pc["files"]) if cur.get("files") and pc.get("files") else 0
            gap_fail = any(s[j].get("failed") for j in idx if prev < j < i)
            if abs(dc) > T[t] or abs(df) > 0.03:
                cands.append({"corpus": t, "from": prev, "to": i, "from_sha": pc["sha"], "to_sha": cur["sha"], "from_date": pc["date"], "to_date": cur["date"],
                              "dcpu": round(dc, 3), "dfiles": round(df, 3), "cpu": [pc["cpu"], cur["cpu"]], "files": [pc.get("files"), cur.get("files")], "gap_has_failed_commit": gap_fail})
        prev = i
    ok = [i for i in idx if not s[i].get("failed")]
    for k in range(0, max(len(ok) - 9, 0)):
        w = ok[k:k + 10]; steps = [(s[b]["cpu"] - s[a]["cpu"]) / s[a]["cpu"] for a, b in zip(w, w[1:])]
        cum = (s[w[-1]]["cpu"] - s[w[0]]["cpu"]) / s[w[0]]["cpu"]
        if abs(cum) > 2 * T[t] and max(abs(x) for x in steps) <= T[t]:
            ramps.append({"corpus": t, "from": w[0], "to": w[-1], "from_date": s[w[0]]["date"], "to_date": s[w[-1]]["date"], "cumulative": round(cum, 3)})
# merge overlapping ramp windows per corpus
merged = []
for r in sorted(ramps, key=lambda r: (r["corpus"], r["from"])):
    if merged and merged[-1]["corpus"] == r["corpus"] and r["from"] <= merged[-1]["to"] and (r["cumulative"] > 0) == (merged[-1]["cumulative"] > 0):
        merged[-1]["to"] = max(merged[-1]["to"], r["to"]); merged[-1]["to_date"] = r["to_date"]
    else: merged.append(dict(r))
KNOWN = {"E1 #3929": "6b604f91a", "E2 #5512": "14fc9c7a5", "E3 #1234": "89d86da58"}
head = subprocess.run(["git", "--git-dir", str(HERE / "mirror.git"), "rev-list", "--first-parent", "--reverse", "7203d2555753ca2b29e180de3cb8d7845aca6a06"], capture_output=True, text=True).stdout.split()
pos = {s[:9]: i for i, s in enumerate(head)}
recall = {}
for name, sha in KNOWN.items():
    k = pos[sha[:9]]
    hit = [c for c in cands if c["from"] < k <= c["to"]]
    recall[name] = {"index": k, "flagged_by": sorted({c["corpus"] for c in hit}), "sampled_commits_bracketing": [max((i for s in series.values() for i in s if i < k), default=None), min((i for s in series.values() for i in s if i >= k), default=None)]}
out = {"T": T, "anchor_runs": {t: len(v) for t, v in anch.items()}, "n_series_points": {t: len(s) for t, s in series.items()}, "candidates": cands, "unresolved_failed_commits": unresolved, "ramps": merged, "known_event_recall": recall}
(HERE / "speed" / "steps_detected.json").write_text(json.dumps(out, indent=1))
L = [f"# Detected steps (plan rule applied; EXPLORATORY)", "", f"Thresholds T per corpus (max(10%, 4 x A/A deviation)): " + ", ".join(f"{t} {v:.0%}" for t, v in T.items()),
     f"Points per corpus: {out['n_series_points']}; A/A anchor runs: {out['anchor_runs']}", f"Candidates: {len(cands)}; unresolved (engine failed): {len({(u['index']) for u in unresolved})} commits; ramps: {len(merged)}", "",
     "## Known events: flagged by the sample?"] + [f"- {n}: index {v['index']} bracketed by sampled {v['sampled_commits_bracketing']}; flagged by {v['flagged_by'] or 'NOBODY'}" for n, v in recall.items()] + \
    ["", "## Candidates (corpus, bracket, dCPU, dFiles)"] + [f"- {c['corpus']:17s} {c['from_date']}..{c['to_date']} idx {c['from']}-{c['to']} dCPU {c['dcpu']:+.0%} dFiles {c['dfiles']:+.1%}{' (a failed commit lies in the gap)' if c['gap_has_failed_commit'] else ''}" for c in cands]
(HERE / "speed" / "steps_detected.md").write_text("\n".join(L))
print("\n".join(L[:12])); print("...", len(cands), "candidates")
