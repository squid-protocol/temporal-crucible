#!/usr/bin/env python3
"""Refinement rule of docs/self_sensitivity_plan.md: bisect every candidate pair from steps_detected.json to one first-parent commit,
re-time the boundary pair with 2 repeats, classify LOCALISED / UNCONFIRMED. Resumable: speed/refined.jsonl. Run after detect_steps.py."""
import json, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "speed" / "steps_detected.json")); T = d["T"]
log = HERE / "speed" / "refined.jsonl"
done = {(r["corpus"], r["from_sha"], r["to_sha"]) for r in map(json.loads, log.open())} if log.exists() else set()
for c in d["candidates"]:
    key = (c["corpus"], c["from_sha"], c["to_sha"])
    if key in done: continue
    metric = "cpu_s" if abs(c["dcpu"]) > T[c["corpus"]] else "files_mapped"
    a, b = (c["cpu"] if metric == "cpu_s" else c["files"])
    thresh = (a + b) / 2; down = b < a
    cmd = [sys.executable, str(HERE / "bisect_cost.py"), c["from_sha"], c["to_sha"], c["corpus"], str(thresh), "--metric", metric] + (["--down"] if down else [])
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    txt = p.stdout
    m = re.search(r"FIRST COMMIT PAST THRESHOLD: ([0-9a-f]{40})", txt)
    tail = txt.split("boundary check")[-1] if "boundary check" in txt else ""
    vals = [float(x) for x in re.findall(rf"{metric}=([0-9.]+)", tail)]
    rec = {**{k: c[k] for k in ("corpus", "from_sha", "to_sha", "from_date", "to_date", "dcpu", "dfiles")}, "metric": metric, "thresh": thresh, "down": down,
           "found": m.group(1) if m else None, "boundary": vals[:2]}
    if len(vals) >= 2 and vals[0] > 0:
        rel = (vals[1] - vals[0]) / vals[0]; thr = T[c["corpus"]] if metric == "cpu_s" else 0.03
        rec["boundary_rel"] = round(rel, 3); rec["class"] = "LOCALISED" if (abs(rel) > thr and (rel < 0) == down) else "UNCONFIRMED"
    else: rec["class"] = "UNEVALUABLE"
    with log.open("a") as f: f.write(json.dumps(rec) + "\n")
    print(rec["class"], c["corpus"], c["from_date"], c["to_date"], (rec["found"] or "")[:9], rec.get("boundary"), flush=True)
