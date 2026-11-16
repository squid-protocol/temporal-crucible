"""Scan snapshots from a real git checkout (a detached worktree) so the engine can read git history; time it."""
import sys, os, json, time, shutil, subprocess
from pathlib import Path
sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; W=Path("/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area/hist")
name=sys.argv[1]; idxs=[int(x) for x in sys.argv[2:]]; sn=json.load(open(f"{B}/scan_{name}/snapshots.json")); ENG="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area/engine_main"; repo=f"{POOL}/{name}"
(W/name).mkdir(parents=True,exist_ok=True)
for i in idxs:
    tag=f"h{i:03d}"; wt=W/name/tag; db=W/name/f"{tag}_galaxy_master.db"
    if db.exists(): print(name,i,"exists",flush=True); continue
    subprocess.run(["git","-C",repo,"worktree","add","--detach","-f",str(wt),sn[i]["commit"]],capture_output=True,check=True)
    t=time.time(); env=dict(os.environ); env.pop("GITGALAXY_DISABLE_GIT_HISTORY",None); env["GITGALAXY_HISTORY_ASOF"]="1"
    env["PYTHONPATH"]=ENG; r=subprocess.run([sys.executable,"-c","import sys; sys.argv=['galaxyscope',sys.argv[1],'--db-only']; from gitgalaxy.galaxyscope import main; sys.exit(main())",str(wt)],cwd=W/name,env=env,capture_output=True,text=True,errors="replace")
    subprocess.run(["git","-C",repo,"worktree","remove","--force",str(wt)],capture_output=True)
    print(name,i,"done" if db.exists() else "FAILED",f"{time.time()-t:.0f}s",(r.stderr or r.stdout)[-200:].replace("\n"," ") if not db.exists() else "",flush=True)
