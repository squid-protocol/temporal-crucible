#!/usr/bin/env python3
"""Reach panel (prototype): per-file and per-function reach from the engine's call graph, include counts for headers, 'not measured' states, and worklists.
    python tools/sensor/reach_panel.py REPO SNAPSHOT_INDEX      (uses the history-aware scan in turn_v2/surface_area/hist and, if present, the activity mock-up frame)"""
import sys, re, json, sqlite3, subprocess, tarfile, io, pickle, pathlib, collections, numpy as np
SA="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area"; B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"
name,idx=sys.argv[1],int(sys.argv[2]); commit=json.load(open(f"{B}/scan_{name}/snapshots.json"))[idx]["commit"]
con=sqlite3.connect(f"file:{SA}/hist/{name}/h{idx:03d}_galaxy_master.db?mode=ro",uri=True)
files={r[0]:r for r in con.execute("select id,file_path,language,function_count from file_data")}
funcs={r[0]:r for r in con.execute("select id,file_id,func_name,is_public,loc from function_data")}
edges=con.execute("select src_func_id,src_file_id,dst_func_id,dst_file_id from fcall_data where dst_func_id is not null").fetchall()
tar=tarfile.open(fileobj=io.BytesIO(subprocess.run(["git","-C",f"{POOL}/{name}","archive",commit],capture_output=True).stdout)); INC=re.compile(r'#\s*include\s*[<"]([^>"]+)[>"]'); incl=collections.defaultdict(set)
for m in tar.getmembers():
    if m.isfile() and m.name.lower().endswith((".c",".h",".cc",".cpp",".hpp")):
        try: t=tar.extractfile(m).read().decode("utf8","replace")
        except Exception: continue
        for h in INC.findall(t): incl[pathlib.PurePosixPath(h).name].add(m.name)
callers_f=collections.defaultdict(set); callfiles=collections.defaultdict(set); fcallers=collections.defaultdict(set); fcfiles=collections.defaultdict(set)
for sf,sfile,df,dfile in edges:
    fcallers[df].add(sf); fcfiles[df].add(sfile)
    if sfile!=dfile: callers_f[dfile].add(sf); callfiles[dfile].add(sfile)
role=lambda p:"tests/docs" if re.search(r"(^|/)(tests?|examples?|fuzz\w*|docs?)(/|$)",p) else ("ci/config" if p.startswith(".github/") or p.endswith((".yml",".yaml")) else "source")
hdr=lambda p:p.endswith((".h",".hpp"))
meas=collections.Counter()
rows=[]
for fid,(i,p,lang,fc) in files.items():
    if hdr(p): meas["header (include count)"]+=1; rows.append((p,"header",len(incl.get(pathlib.PurePosixPath(p).name,())),0,0,role(p))); continue
    if fc and fc>=1:
        two=set()
        for fn in (k for k,v in funcs.items() if v[1]==fid):
            for c in fcallers.get(fn,()): two|=fcallers.get(c,set())
        meas["source (call-based reach)"]+=1; rows.append((p,"source",len(callfiles.get(fid,())),len(callers_f.get(fid,())),len(two),role(p)))
    else: meas["not measured (no functions, not a header)"]+=1
print(f"REACH PANEL  {name} snapshot {idx} ({commit[:8]}): {len(files)} files")
print("  coverage: "+"; ".join(f"{k} {v}" for k,v in meas.items()))
src=[r for r in rows if r[1]=="source" and r[5]=="source"]; src.sort(key=lambda r:-r[2])
act=None; fr=pathlib.Path(f"{SA}/mockup_{name}.pkl")
if fr.exists():
    D=pickle.load(open(fr,"rb")); D=D[D.t==idx]; act=dict(zip(D.file_path,D.c365))
print("  files that the most other files call into (source):")
for p,k,cf,cfn,two,ro in src[:8]: print(f"    {p:44s} {cf:4d} caller files, {cfn:5d} caller functions, {two:5d} more one hop out"+(f", {act.get(p,'-')} commits last year" if act is not None else ""))
pf=[(len(fcfiles[k]-{v[1]}),v[2],files[v[1]][1],v[3]) for k,v in funcs.items() if v[3] and len(fcfiles.get(k,set())-{v[1]})>0]; pf.sort(reverse=True)
print(f"  most-used public functions ({sum(1 for v in funcs.values() if v[3])} functions are marked public):")
for n,fn,p,pub in pf[:6]: print(f"    {fn:34s} {p:34s} called from {n} other files")
hd=sorted([r for r in rows if r[1]=="header"],key=lambda r:-r[2]); print("  headers by number of files that include them: "+", ".join(f"{pathlib.PurePosixPath(r[0]).name} ({r[2]})" for r in hd[:5]))
if act is not None and src:
    cfs=np.array([r[2] for r in src]); thr=np.percentile(cfs,90); fo=[(r[0],r[2],r[3]) for r in src if r[2]>=thr and act.get(r[0],0)==0]
    print(f"  stable foundations (reach in the top decile, no commit in the last year): {len(fo)}"+("".join(f"\n    {p:44s} {cf} caller files, {cfn} caller functions" for p,cf,cfn in sorted(fo,key=lambda x:-x[1])[:5])))
