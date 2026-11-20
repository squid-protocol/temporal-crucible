#!/usr/bin/env python3
"""Stage 2 of the sensitivity pass (rules: docs/self_sensitivity_plan.md). Resumable: speed/sens.jsonl."""
import json, os, subprocess, datetime as dt
import speed_probe as sp
M = str(sp.MIRROR); LAST = "7203d2555753ca2b29e180de3cb8d7845aca6a06"; ANCHOR = LAST
env = dict(os.environ, TZ="America/Detroit")
out = subprocess.run(["git", "--git-dir", M, "log", "--first-parent", "--reverse", "--format=%H %cd", "--date=format-local:%Y-%m-%d", LAST],
                     capture_output=True, text=True, env=env).stdout.splitlines()
head = [l.split()[0] for l in out]; date = {l.split()[0]: l.split()[1] for l in out}
grid = {i for i in range(0, len(head), 25)} | {len(head) - 1}
week = {}
for i, sha in enumerate(head):
    y, w, _ = dt.date.fromisoformat(date[sha]).isocalendar(); week[(y, w)] = i          # last commit of each ISO week
weekly = set(week.values())
S2 = sorted(grid | weekly)
pilot_done = {json.loads(l)["fp_index"] for l in open(sp.HERE / "speed" / "dense.jsonl")} if (sp.HERE / "speed" / "dense.jsonl").exists() else set()
ALL = ["keyword-rosetta", "cics-crucible", "onepl", "language-crucible"]
SMALL = ALL[:3]
log = sp.HERE / "speed" / "sens.jsonl"
done = {(r["sha"], r["target"], r.get("anchor_n")) for r in map(json.loads, log.open())} if log.exists() else set()
def run(sha, d, i, target, anchor_n=None):
    key = (sha, target, anchor_n)
    if key in done: return
    s = {"slot": f"p{i:05d}" if anchor_n is None else f"a{anchor_n:03d}", "date": d, "sha": sha}
    try: r = sp.one_run(s, target, 800 + (anchor_n or 0), True)
    except Exception as e: r = {"slot": s["slot"], "date": d, "sha": sha, "target": target, "exit": 98, "tail": f"{type(e).__name__}: {e}"[:300]}
    r.update(fp_index=i, anchor_n=anchor_n)
    with log.open("a") as f: f.write(json.dumps(r) + "\n")
    print(f"{'A' if anchor_n is not None else ' '} {i:5d} {d} {target:16s} exit={r.get('exit')} cpu={r.get('cpu_s')} files={r.get('files_mapped')} funcs={r.get('out_funcs')}", flush=True)
if __name__ == "__main__":
    print(len(head), "commits;", len(S2), "in S2 (", len(grid), "grid +", len(weekly), "weekly );", len(set(S2) - pilot_done), "not in pilot", flush=True)
    for n, i in enumerate(S2):
        sha = head[i]
        targets = ["language-crucible"] + ([t for t in SMALL if i not in pilot_done] if i not in grid else [])
        for t in targets: run(sha, date[sha], i, t)
        subprocess.run(["git", "--git-dir", M, "worktree", "remove", "--force", str(sp.ENG / f"p{i:05d}")], capture_output=True)
        if n % 20 == 19:                                              # A/A anchor, same session
            k = n // 20 + 1
            for t in ALL: run(ANCHOR, date[ANCHOR], len(head) - 1, t, anchor_n=k)
            subprocess.run(["git", "--git-dir", M, "worktree", "remove", "--force", str(sp.ENG / f"a{k:03d}")], capture_output=True)
