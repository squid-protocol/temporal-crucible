#!/usr/bin/env python3
"""Construct validity of the engine's reach measures against an independent text measure (who mentions a function's name; who #includes a header).
    python tools/sensor/reach_validity.py curl 104   (repo, hist snapshot index)"""
import sys, re, json, sqlite3, subprocess, tarfile, io, collections, numpy as np, pathlib
from scipy.stats import spearmanr
SA="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area"; B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"
name,idx=sys.argv[1],int(sys.argv[2]); sn=json.load(open(f"{B}/scan_{name}/snapshots.json")); commit=sn[idx]["commit"]
con=sqlite3.connect(f"file:{SA}/hist/{name}/h{idx:03d}_galaxy_master.db?mode=ro",uri=True)
files={r[0]:r[1:] for r in con.execute("select id,file_path,language,function_count,pagerank_score,normalized_blast_radius,internal_dependency_links,import_count from file_data")}
funcs=list(con.execute("select id,file_id,func_name from function_data"))
edges=[r for r in con.execute("select src_file_id,dst_file_id,dst_func_id from fcall_data where dst_func_id is not null")]
tar=subprocess.run(["git","-C",f"{POOL}/{name}","archive",commit],capture_output=True).stdout; tf=tarfile.open(fileobj=io.BytesIO(tar))
CM=re.compile(r"/\*.*?\*/|//[^\n]*",re.S); ID=re.compile(r"[A-Za-z_]\w*"); INC=re.compile(r'#\s*include\s*[<"]([^>"]+)[>"]')
text={}; 
for m in tf.getmembers():
    if m.isfile() and m.name.lower().endswith((".c",".h",".cc",".cpp",".hpp",".py",".go",".java",".rs",".zig")):
        try: text[m.name]=tf.extractfile(m).read().decode("utf8","replace")
        except Exception: pass
ident=collections.defaultdict(set); incl=collections.defaultdict(set)
for p,t in text.items():
    for i in set(ID.findall(CM.sub(" ",t))): ident[i].add(p)
    for h in INC.findall(t): incl[pathlib.PurePosixPath(h).name].add(p)
path2id={v[0]:k for k,v in files.items()}
names=collections.Counter(n for _,_,n in funcs); eng=collections.defaultdict(set)
for sf,df,dfn in edges:
    if sf!=df: eng[dfn].add(files[sf][0])
rows=[]; rec=[]; prec=[]; miss=0; n_ok=0
for fid,file_id,n in funcs:
    if names[n]!=1 or file_id not in files or files[file_id][0] not in text: continue
    own=files[file_id][0]; t=ident.get(n,set())-{own}; e=eng.get(fid,set())
    rows.append((len(t),len(e))); n_ok+=1
    if t: rec.append(len(t&e)/len(t)); miss+= (len(e)==0)
    if e: prec.append(len(t&e)/len(e))
a=np.array(rows); print(f"{name} snapshot {idx} ({commit[:8]}): {n_ok} uniquely named functions compared")
print(f"FUNCTION LEVEL: cross-file caller files, engine vs text search: Spearman {spearmanr(a[:,0],a[:,1]).statistic:+.2f}; of functions the text says have outside users, the engine finds none for {100*miss/max(len(rec),1):.0f}%; per-function recall of text callers (median) {np.median(rec):.2f}; precision of engine callers (median) {np.median(prec):.2f}")
# file level
tx=[];E=collections.defaultdict(list); callerfiles=collections.defaultdict(set)
for sf,df,_ in edges:
    if sf!=df: callerfiles[df].add(sf)
fnames=collections.defaultdict(list)
for fid,file_id,n in funcs:
    if names[n]==1: fnames[file_id].append(n)
kind=[]
for file_id,(p,lang,fc,pr,br,idl,imp) in files.items():
    if p not in text or fc<1: continue
    dep=set()
    for n in fnames.get(file_id,[]): dep|=ident.get(n,set())-{p}
    base=pathlib.PurePosixPath(p).name
    tx.append(len(dep)); kind.append(p.endswith((".h",".hpp"))); 
    for k,v in (("pagerank_score",pr),("normalized_blast_radius",br),("internal_dependency_links",idl),("import_count",imp),("call-based caller files",len(callerfiles.get(file_id,())))): E[k].append(v)
    E.setdefault("#include count (headers)",[]).append(len(incl.get(base,())))
tx=np.array(tx); print(f"FILE LEVEL ({len(tx)} files): Spearman with 'files that mention any function the file defines' (text):")
for k,v in E.items():
    v=np.array(v,float)
    if k.startswith("#include"): m=np.array(kind); print(f"  {k:34s} {spearmanr(tx[m],v[m]).statistic:+.2f}  (headers only, n={int(m.sum())})")
    else: print(f"  {k:34s} {spearmanr(tx,v).statistic:+.2f}")
HM={k:[] for k in ("pagerank_score","normalized_blast_radius","internal_dependency_links","import_count","call-based caller files")}; HI=[]
for file_id,(p,lang,fc,pr,br,idl,imp) in files.items():
    if p.endswith((".h",".hpp")) and p in text:
        HI.append(len(incl.get(pathlib.PurePosixPath(p).name,()))); 
        for k,v in zip(HM,(pr,br,idl,imp,len(callerfiles.get(file_id,())))): HM[k].append(v)
HI=np.array(HI,float); print(f"HEADERS ({len(HI)} header files, {int((HI>0).sum())} included somewhere): Spearman with the number of files that #include them: "+", ".join(f"{k} {spearmanr(HI,np.array(v,float)).statistic:+.2f}" for k,v in HM.items()))
