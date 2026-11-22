#!/usr/bin/env python3
"""Q1 of docs/self_quality_structure_plan.md: does speed co-move with output volume? Reads speed/sens.jsonl (language-crucible runs with CPU, functions found, files mapped)."""
import json, math
from scipy.stats import spearmanr
r = [json.loads(l) for l in open("speed/sens.jsonl")]
lc = sorted([x for x in r if x["target"] == "language-crucible" and x.get("anchor_n") is None and not x.get("exit") and x.get("cpu_s") and x.get("out_funcs") and x.get("files_mapped")], key=lambda x: x["fp_index"])
P = [dict(dcpu=math.log(b["cpu_s"] / a["cpu_s"]), dfun=math.log(b["out_funcs"] / a["out_funcs"]), dfil=b["files_mapped"] / a["files_mapped"] - 1) for a, b in zip(lc, lc[1:])]
prim = [p for p in P if abs(p["dfil"]) <= 0.03]
print("pairs", len(P), "primary", len(prim), "rho", spearmanr([p["dcpu"] for p in prim], [p["dfun"] for p in prim]))
