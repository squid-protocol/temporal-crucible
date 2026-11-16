"""Construct validity of the engine's planned_debt / fragile_debt counts: per-file Spearman against a git-grep count of TODO/FIXME/XXX/HACK comment lines at the same commit."""
import sys, json, re, sqlite3, subprocess, collections, numpy as np
from scipy.stats import spearmanr
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"
CODE=re.compile(r"\.(c|h|cc|cpp|hpp|py|go|java|rs|zig)$")
for name in sys.argv[1:]:
    sn=json.load(open(f"{B}/scan_{name}/snapshots.json")); db=sn[-1]["db"]; commit=sn[-1]["commit"]
    con=sqlite3.connect(f"file:{db}?mode=ro",uri=True); eng={p:(a or 0,b or 0) for p,a,b in con.execute("select file_path,state_planned_debt,state_fragile_debt from file_data where function_count>=1")}; con.close()
    out=subprocess.run(["git","-C",f"{POOL}/{name}","grep","-c","-I","-i","-E",r"\b(TODO|FIXME|XXX|HACK|BUG|KLUDGE)\b",commit],capture_output=True,text=True,errors="replace").stdout.splitlines()
    g={}
    for ln in out:
        try: p,c=ln[len(commit)+1:].rsplit(":",1); g[p]=int(c)
        except ValueError: pass
    paths=[p for p in eng if CODE.search(p)]; x=np.array([sum(eng[p]) for p in paths]); y=np.array([g.get(p,0) for p in paths])
    both=(x>0)|(y>0)
    print(f"{name:10s} files {len(paths):5d} | files with a marker by engine {int((x>0).sum()):4d}, by text search {int((y>0).sum()):4d}, both {int(((x>0)&(y>0)).sum()):4d} | totals engine {x.sum()} vs text {y.sum()} | Spearman (all files) {spearmanr(x,y).statistic:+.2f}, (files with any) {spearmanr(x[both],y[both]).statistic:+.2f}")
