#!/usr/bin/env python3
"""Dense timing around the commits the bisections named. For each event: the parent, the commit, and a few after it
(first-parent offsets), each timed on all corpora + the one-file-per-language control, then structure-scanned.
  events_probe.py time [-r 2]   |   events_probe.py structure
Resumable (events.jsonl; dbs_events/)."""
import json, subprocess, sys, shutil
from pathlib import Path
import speed_probe as sp
import history_scan as hs
HERE = sp.HERE; M = str(sp.MIRROR)
EVENTS = {"E1_3929_precompile_threshold": "6b604f91a731a1c7a257db8ffb29f350f370fefb",
          "E2_5512_vendored_screen": "14fc9c7a55cd5d980e3008e586195046057b97c2",
          "E3_1234_prism_quotes": "89d86da58ad7e69bdc6827c6f8999985e8903185"}
OFFS = (-1, 0, 1, 3, 10)
TARGETS = ["keyword-rosetta", "cics-crucible", "onepl", "language-crucible"]
head = subprocess.run(["git", "--git-dir", M, "rev-list", "--first-parent", "--reverse", "7203d2555753ca2b29e180de3cb8d7845aca6a06"], capture_output=True, text=True).stdout.split()
pos = {s: i for i, s in enumerate(head)}
pts = []
for name, sha in EVENTS.items():
    i = pos[sha]
    for o in OFFS:
        c = head[i + o]
        date = subprocess.run(["git", "--git-dir", M, "log", "-1", "--format=%cd", "--date=short", c], capture_output=True, text=True).stdout.strip()
        pts.append({"slot": f"{name[:2]}_{'m' if o<0 else 'p'}{abs(o)}_{c[:8]}", "event": name, "offset": o, "sha": c, "date": date})
if sys.argv[1] == "time":
    reps = int(sys.argv[sys.argv.index("-r") + 1]) if "-r" in sys.argv else 2
    log = HERE / "speed" / "events.jsonl"
    done = {(r["slot"], r["target"], r["rep"]) for r in map(json.loads, log.open())} if log.exists() else set()
    for rep in range(1, reps + 1):
        for p in pts:
            for t in TARGETS:
                if (p["slot"], t, rep) in done: continue
                r = sp.one_run(p, t, 500 + rep, True)
                r.update(event=p["event"], offset=p["offset"], rep=rep)
                with log.open("a") as f: f.write(json.dumps(r) + "\n")
                print(f"{p['event'][:2]} off={p['offset']:+3d} {t:17s} rep{rep} cpu={r.get('cpu_s')} files={r.get('files_mapped')} exit={r['exit']}", flush=True)
            subprocess.run(["git", "--git-dir", M, "worktree", "remove", "--force", str(sp.ENG / p["slot"])], capture_output=True)
else:
    out = HERE / "dbs_events"; out.mkdir(exist_ok=True)
    for p in pts:
        final = out / f"{p['event'][:2]}_{p['offset']:+d}_{p['sha'][:10]}.db"
        if final.exists(): continue
        job = HERE / "work" / f"ev_{p['sha'][:10]}"; shutil.rmtree(job, ignore_errors=True); job.mkdir(parents=True)
        db = hs.checkout_scan(p["sha"], job)
        if db: shutil.move(str(db), final)
        shutil.rmtree(job, ignore_errors=True); print(p["slot"], "structure", "ok" if db else "FAILED", flush=True)
