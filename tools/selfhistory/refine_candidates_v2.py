#!/usr/bin/env python3
"""PASS-2 version (review fixes: raw unrounded dcpu decides the metric; uses bisect_cost_v2.py; output refined_pass2.jsonl; re-runs candidates that pass 1 left UNCONFIRMED/UNEVALUABLE or that the rounding mis-routed, plus any not refined). Refinement rule of docs/self_sensitivity_plan.md: bisect every candidate pair from steps_detected.json to one first-parent commit,
re-time the boundary pair with 2 repeats, classify LOCALISED / UNCONFIRMED. Resumable: speed/refined.jsonl. Run after detect_steps.py."""
import json, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "speed" / "steps_detected.json")); T = d["T"]
pass1 = [json.loads(l) for l in (HERE / "speed" / "refined.jsonl").open()] if (HERE / "speed" / "refined.jsonl").exists() else []
P1 = {(x["corpus"], x["from_sha"], x["to_sha"]): x["class"] for x in pass1}
log = HERE / "speed" / "refined_pass2.jsonl"
done = {(r["corpus"], r["from_sha"], r["to_sha"]) for r in map(json.loads, log.open())} if log.exists() else set()
for c in d["candidates"]:
    key = (c["corpus"], c["from_sha"], c["to_sha"])
    if key in done: continue
    raw_dcpu = c["cpu"][1] / c["cpu"][0] - 1
    rounded_flip = (abs(raw_dcpu) > T[c["corpus"]]) != (abs(c["dcpu"]) > T[c["corpus"]])
    if P1.get(key) == "LOCALISED" and not rounded_flip: continue          # pass 1 stands
    metric = "cpu_s" if abs(raw_dcpu) > T[c["corpus"]] else "files_mapped"
    a, b = (c["cpu"] if metric == "cpu_s" else c["files"])
    thresh = (a + b) / 2; down = b < a
    cmd = [sys.executable, str(HERE / "bisect_cost_v2.py"), c["from_sha"], c["to_sha"], c["corpus"], str(thresh), "--metric", metric] + (["--down"] if down else [])
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    txt = p.stdout
    m = re.search(r"FIRST COMMIT PAST THRESHOLD: ([0-9a-f]{40})", txt)
    tail = txt.split("boundary check")[-1] if "boundary check" in txt else ""
    vals = [float(x) for x in re.findall(rf"{metric}=([0-9.]+)", tail)]
    rec = {**{k: c[k] for k in ("corpus", "from_sha", "to_sha", "from_date", "to_date", "dcpu", "dfiles")}, "dcpu_raw": raw_dcpu, "pass1_class": P1.get(key), "metric": metric, "thresh": thresh, "down": down,
           "found": m.group(1) if m else None, "boundary": vals[:2]}
    if len(vals) >= 2 and vals[0] > 0:
        rel = (vals[1] - vals[0]) / vals[0]; thr = T[c["corpus"]] if metric == "cpu_s" else 0.03
        rec["boundary_rel"] = round(rel, 3); rec["class"] = "LOCALISED" if (abs(rel) > thr and (rel < 0) == down) else "UNCONFIRMED"
    else: rec["class"] = "UNEVALUABLE"
    with log.open("a") as f: f.write(json.dumps(rec) + "\n")
    print(rec["class"], c["corpus"], c["from_date"], c["to_date"], (rec["found"] or "")[:9], rec.get("boundary"), flush=True)
