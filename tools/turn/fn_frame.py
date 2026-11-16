"""Function-quarter frame: prior fixes of the function itself (lineage vs naive identity), of its file, edit kinds, and later fixes, under three labels."""
import sys, json, pickle, collections, subprocess, numpy as np
exec(open("/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad/arch_frame.py").read().split("def frame(name):")[0])
SPD="/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"
TAGS=("raw","v3c","reg")
def build(name):
    sn=json.load(open(f"{AU.B}/scan_{name}/snapshots.json")); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]; repo=Path(f"{AU.POOL}/{name}")
    ct=[int(subprocess.run(["git","-C",str(repo),"show","-s","--format=%ct",x["commit"]],capture_output=True,text=True).stdout.strip()) for x in sn]
    led=LG.build_ledger(repo,snaps); N=len(snaps); A=[W.arrays(x.scan) for x in snaps]; ev=R[name]["events"]
    hits=pickle.load(open(f"{SPD}/ff_{name}.pkl","rb"))[name]["hits"]
    x2={e["sha"]:e.get("class") for e in json.load(open(f"{EV}/{name}_xc2.json"))["events"]}
    fl={t:[] for t in TAGS}
    for suf,cls_ok in (("_xc",lambda c:True),("_xc2",lambda c:True)):
        for e in json.load(open(f"{EV}/{name}{suf}.json"))["events"]:
            for f in e.get("c_files",[]):
                if suf=="_xc": fl["raw"].append((e["ct"],f))
                else:
                    fl["v3c"].append((e["ct"],f))
                    if e.get("class")=="regression": fl["reg"].append((e["ct"],f))
    first={}
    for s in range(N):
        for x in led.ids[s].tolist(): first.setdefault(x,s)
    keyidx=[{} for _ in range(N)]
    for s in range(N):
        for i,k in enumerate(led.keys[s]): keyidx[s].setdefault(k,i)
    flin={t:collections.Counter() for t in TAGS}; fkey={t:collections.Counter() for t in TAGS}
    for sha,h in hits.items():
        s=next((i for i in range(N-1) if ct[i]<h["ct"]<=ct[i+1]),None)
        if s is None: continue
        tags=["raw"]+(["v3c"] if sha in x2 else [])+(["reg"] if x2.get(sha)=="regression" else [])
        for (p,nm) in h["funcs"]:
            i=keyidx[s].get((p,nm))
            if i is None: continue
            lid=int(led.ids[s][i])
            for t in tags: flin[t][(lid,s)]+=1; fkey[t][((p,nm),s)]+=1
    code=[i for i,e in enumerate(ev) if e["code"]]; kinds=km.predict(Z(name)); cnt=collections.defaultdict(lambda:np.zeros(6))
    for i,k in zip(code,kinds): e=ev[i]; cnt[(int(led.ids[e["s"]][e["x"]]),e["s"])][COL[k]]+=1
    rows=[]
    for t in range(4,N-4,4):
        pri={g:collections.Counter(f for c,f in fl[g] if ct[t-4]<c<=ct[t]) for g in TAGS}
        for i,key in enumerate(led.keys[t]):
            lid=int(led.ids[t][i]); loc=A[t][1][i]; kd=sum((cnt.get((lid,s),np.zeros(6)) for s in range(t-4,t)),np.zeros(6)); r=[lid,t,loc,kd.sum(),*kd,t-first[lid]]
            for g in TAGS:
                r+=[pri[g].get(key[0],0), sum(flin[g].get((lid,s),0) for s in range(t-4,t)), sum(flin[g].get((lid,s),0) for s in range(0,t)),
                    sum(fkey[g].get((key,s),0) for s in range(t-4,t)), sum(fkey[g].get((key,s),0) for s in range(0,t)), sum(flin[g].get((lid,s),0) for s in range(t,t+4))]
            rows.append(r)
    return np.array(rows,float)
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=build(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",out[n].shape,flush=True)
