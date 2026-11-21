#!/usr/bin/env python3
"""Build the call-network evolution artifact (GIF/MP4/HTML) for GitGalaxy's own engine code from the 180 daily scans, using historical-call-graph-gif.
Engine units (same rule as evo/analyze.py): gitgalaxy/ or backend/, excluding tests, standards pattern tables, __init__.py. `backend/` is renamed `gitgalaxy/` so the
March files line up with later ones (files moved into gitgalaxy/core/ still show as a death plus a birth, a known limit of the tool)."""
import sys, sqlite3, shutil, os, datetime as dt
from pathlib import Path
sys.path.insert(0, "/srv/storage_16tb/projects/historical-call-graph-gif")
H = Path("/srv/storage_16tb/projects/gitgalaxy-history"); OUT = H / "evolution_artifact"; WORK = OUT / "work"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 48
picks = [l.split("\t") for l in (H / "picks.tsv").read_text().split("\n") if l]
days = [dt.date.fromisoformat(d) for d, _ in picks]
t0, t1 = days[0], days[-1]
chosen = []
for k in range(N):
    tgt = t0 + (t1 - t0) * k / (N - 1)
    i = min(range(len(days)), key=lambda j: abs((days[j] - tgt).days))
    if i not in chosen: chosen.append(i)
from historical_call_graph_gif import collect, cli
from historical_call_graph_gif.snapshots import Pick
ENG = ("file_path LIKE 'gitgalaxy/%' AND file_path NOT LIKE '%/tests/%' AND file_path NOT LIKE '%/standards/%' "
       "AND file_path NOT LIKE '%gitgalaxy_standards%' AND file_path NOT LIKE '%__init__.py'")
dbs, pk = [], []
for i in chosen:
    d, sha = picks[i]
    src = next((H / "dbs").glob(f"{d}_{sha[:10]}.db")); dst = WORK / src.name
    if not dst.exists():
        a = sqlite3.connect(f"file:{src}?mode=ro&immutable=1", uri=True); b = sqlite3.connect(dst); a.backup(b); a.close()
        b.execute("UPDATE file_data SET file_path = 'gitgalaxy/' || substr(file_path, 9) WHERE file_path LIKE 'backend/%'")
        b.execute(f"DELETE FROM function_data WHERE file_id NOT IN (SELECT id FROM file_data WHERE {ENG})")
        b.execute(f"DELETE FROM file_data WHERE NOT ({ENG})")
        b.commit(); b.execute("VACUUM"); b.close()
    dbs.append(dst); pk.append(Pick(sha, d, dt.date.fromisoformat(d).strftime("%b %d")))
print(len(dbs), "snapshots,", pk[0].label, "to", pk[-1].label, flush=True)
ds = collect.drop_leading_empty(collect.from_snapshot_dbs("gitgalaxy", pk, dbs))
print("functions ever seen:", len(ds.funcs), "| alive in last snapshot:", len(ds.alive[-1]), flush=True)
collect.master_db_commits = lambda *a, **k: []
collect.from_master_db = lambda *a, **k: ds
args = ["from-db", "unused.db", "--name", "gitgalaxy", "--title", "GitGalaxy's own call network (engine code, Mar-Nov 2026)",
        "-o", str(OUT), "--formats", "html,mp4,gif,png", "--quality", "standard", "--duration", "60", "--hold", "4", "--jobs", "2", "--frames-per-snapshot", "4"]
sys.exit(cli.main(args))
