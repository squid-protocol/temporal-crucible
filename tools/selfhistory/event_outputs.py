#!/usr/bin/env python3
"""Q2 (docs/self_quality_structure_plan.md): re-time the parent and the found commit of every localised speed event, recording output counts."""
import json, subprocess, os
import speed_probe as sp
M = str(sp.MIRROR); TIP = "7203d2555753ca2b29e180de3cb8d7845aca6a06"
head = subprocess.run(["git", "--git-dir", M, "rev-list", "--first-parent", "--reverse", TIP], capture_output=True, text=True).stdout.split()
ev = json.load(open(sp.HERE / "final" / "out" / "steps_table.json"))["events"]
log = sp.HERE / "speed" / "event_outputs.jsonl"
done = {(r["sha"], r["target"]) for r in map(json.loads, log.open())} if log.exists() else set()
for e in sorted(ev, key=lambda e: e["index"]):
    i = e["index"]
    for role, idx in (("parent", i - 1), ("commit", i)):
        sha = head[idx]
        s = {"slot": f"q{idx:05d}", "date": e["date"][:10], "sha": sha}
        for t in ("language-crucible", "keyword-rosetta"):
            if (sha, t) in done: continue
            try: r = sp.one_run(s, t, 900, True)
            except Exception as ex: r = {"slot": s["slot"], "sha": sha, "target": t, "exit": 98, "tail": str(ex)[:200]}
            r.update(event_sha=e["sha"], event_index=i, role=role, direction=e["direction"])
            with log.open("a") as f: f.write(json.dumps(r) + "\n")
            print(i, role, t, "exit", r.get("exit"), "cpu", r.get("cpu_s"), "funcs", r.get("out_funcs"), "files", r.get("files_mapped"), flush=True)
        subprocess.run(["git", "--git-dir", M, "worktree", "remove", "--force", str(sp.ENG / s["slot"])], capture_output=True)
print("DONE")
