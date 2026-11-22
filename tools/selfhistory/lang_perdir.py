import os, subprocess, shutil, sqlite3, json, time, speed_probe as sp
from pathlib import Path
S={s["slot"]:s for s in sp.slots(12)}; wt=sp.ensure_engine(S["s11"]); cmdp,paths,mod=sp.engine_entry(wt)
assert sp.provenance(wt,mod,paths)[0]
T=Path("targets/language-crucible/data"); out={}
env=dict(os.environ,GITGALAXY_DISABLE_GIT_HISTORY="1",PYTHONPATH=os.pathsep.join(paths))
for d in sorted(p for p in T.iterdir() if p.is_dir()):
    w=Path("speed/lang/perdir")/d.name; shutil.rmtree(w,ignore_errors=True); w.mkdir(parents=True)
    n=sum(1 for p in d.rglob("*") if p.is_file()); t0=time.time()
    subprocess.run(cmdp+[str(d.resolve()),"--db-only"],cwd=w,env=env,capture_output=True,text=True,errors="replace")
    db=next(w.glob("*_galaxy_master.db"),None)
    if not db: out[d.name]={"disk":n,"error":"no db"}; continue
    c=sqlite3.connect(f"file:{db}?mode=ro&immutable=1",uri=True)
    rows=c.execute("select language,count(*),sum(coding_loc),sum(function_count) from file_data group by 1").fetchall()
    ex=c.execute("select count(*) from excluded_artifacts").fetchone()[0]
    out[d.name]={"disk":n,"mapped":sum(r[1] for r in rows),"functions":int(sum(r[3] or 0 for r in rows)),"loc":int(sum(r[2] or 0 for r in rows)),
                 "excluded":ex,"by_detected":{r[0]:[r[1],int(r[3] or 0)] for r in rows},"secs":round(time.time()-t0,1)}
    c.close(); shutil.rmtree(w,ignore_errors=True)
    print(d.name,out[d.name]["disk"],out[d.name]["mapped"],out[d.name]["functions"],out[d.name]["secs"],flush=True)
json.dump(out,open("join/language_crucible_perdir.json","w"),indent=1)
print("DONE")
