import json,subprocess,os,sys,glob,sqlite3,collections
GD=["git","--git-dir","/srv/storage_16tb/projects/gitgalaxy-history/mirror.git"]
C=json.load(open("commits.json")); el={r["sha"] for r in C if not r["tangled"]}
E=[json.loads(l) for l in open("fn_events2.jsonl")]
files=collections.defaultdict(set)
for e in E:
    if e["sha"] in el and e["kind"] in("body","signature"): files[e["sha"]].add((e.get("old_file") or e["file"],e["file"]))
root="gscan/trees"; 
for side in("old","new"): os.makedirs(f"{root}/{side}",exist_ok=True)
n=0
for sha,fs in files.items():
    for of,nf in fs:
        for side,rev,f in(("old",sha+"^",of),("new",sha,nf)):
            p=f"{root}/{side}/{sha[:10]}/{f}"; os.makedirs(os.path.dirname(p),exist_ok=True)
            src=subprocess.run(GD+["show",f"{rev}:{f}"],capture_output=True,text=True,errors="replace").stdout
            open(p,"w").write(src); n+=1
print("files written",n,flush=True)
