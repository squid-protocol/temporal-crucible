#!/usr/bin/env python3
"""Dense timing: every 25th first-parent commit (index % 25 == 0, root = 0) plus the last, each commit's own engine, 3 small corpora, 1 repeat.
Sampling rule fixed before the commit text is read (draft doc, decision 4). Resumable: dense.jsonl."""
import json, subprocess, sys
import speed_probe as sp
M = str(sp.MIRROR); LAST = "7203d2555753ca2b29e180de3cb8d7845aca6a06"
head = subprocess.run(["git", "--git-dir", M, "rev-list", "--first-parent", "--reverse", LAST], capture_output=True, text=True).stdout.split()
idx = sorted({i for i in range(0, len(head), 25)} | {len(head) - 1})
if len(sys.argv) > 1 and sys.argv[1] == "list":
    print(len(head), "first-parent commits;", len(idx), "sampled"); sys.exit()
TARGETS = ["keyword-rosetta", "cics-crucible", "onepl"]
log = sp.HERE / "speed" / "dense.jsonl"
done = {(r["sha"], r["target"]) for r in map(json.loads, log.open())} if log.exists() else set()
for n, i in enumerate(idx, 1):
    sha = head[i]
    date = subprocess.run(["git", "--git-dir", M, "log", "-1", "--format=%cd", "--date=short", sha], capture_output=True, text=True).stdout.strip()
    s = {"slot": f"d{i:05d}", "date": date, "sha": sha}
    for t in TARGETS:
        if (sha, t) in done: continue
        try:
            r = sp.one_run(s, t, 700, True)
        except Exception as e:
            r = {"slot": s["slot"], "date": date, "sha": sha, "target": t, "exit": 98, "tail": f"{type(e).__name__}: {e}"[:300]}
        r["fp_index"] = i
        with log.open("a") as f: f.write(json.dumps(r) + "\n")
        print(f"[{n}/{len(idx)}] {i:5d} {date} {t:16s} exit={r.get('exit')} cpu={r.get('cpu_s')} files={r.get('files_mapped')}", flush=True)
    subprocess.run(["git", "--git-dir", M, "worktree", "remove", "--force", str(sp.ENG / s["slot"])], capture_output=True)
