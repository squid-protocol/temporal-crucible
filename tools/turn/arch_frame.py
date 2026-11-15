"""File-year frame: edit-kind counts per file (prior 4 quarters) + fixes under three labels (next 4 quarters)."""
import sys, json, pickle, collections, subprocess, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
src=open("/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad/archetypes.py").read().split("print(\"\\nARCHETYPES")[0].split("best=None")[0]
exec(src)                                    # R, feats, squash, Z, train, idx, KMeans, disc ...
km=KMeans(6,n_init=5,random_state=2982).fit(train[idx])
raw=np.vstack([feats(R[n]["events"]) for n in disc]); labs=np.concatenate([km.predict(Z(n)) for n in disc]); cm=np.array([raw[labs==c].mean(0) for c in range(6)])
KIND={}
for c in range(6):
    m=cm[c]; KIND[c]=("swap" if m[11]>0.5 else "rewrite" if m[3]>1.0 else "signature" if m[1]>0.5 else "shrink" if m[0]<-1 else "grow" if m[0]>1 else "tweak")
ORDER=["tweak","swap","signature","grow","shrink","rewrite"]; COL={c:ORDER.index(k) for c,k in KIND.items()}
from structural_fingerprint import ledger as LG
import what_changes as W, sweep_audit as AU
EV=AU.EV
def frame(name):
    sn=json.load(open(f"{AU.B}/scan_{name}/snapshots.json")); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]; repo=Path(f"{AU.POOL}/{name}")
    ct=[int(subprocess.run(["git","-C",str(repo),"show","-s","--format=%ct",x["commit"]],capture_output=True,text=True).stdout.strip()) for x in sn]
    led=LG.build_ledger(repo,snaps); N=len(snaps); A=[W.arrays(x.scan) for x in snaps]; ev=R[name]["events"]
    code=[i for i,e in enumerate(ev) if e["code"]]; kinds=km.predict(Z(name)); assert len(kinds)==len(code)
    cnt=collections.defaultdict(lambda:np.zeros(6))
    for i,k in zip(code,kinds):
        e=ev[i]; cnt[(e["s"],led.keys[e["s"]][e["x"]][0])][COL[k]]+=1
    lab={}
    for tag,suf,cls in (("raw","_xc",None),("v3c","_xc2",None),("reg","_xc2","regression")):
        fx=json.load(open(f"{EV}/{name}{suf}.json"))["events"]; lab[tag]=[(e["ct"],f) for e in fx if (cls is None or e.get("class")==cls) for f in e.get("c_files",[])]
    rows=[]; fid={}
    for t in range(4,N-4,4):
        size=collections.Counter()
        for i,(p,_) in enumerate(led.keys[t]): size[p]+=A[t][1][i]
        pri={k:collections.Counter(f for c,f in v if ct[t-4]<c<=ct[t]) for k,v in lab.items()}; out={k:collections.Counter(f for c,f in v if ct[t]<c<=ct[t+4]) for k,v in lab.items()}
        for p,sz in size.items():
            if sz<5: continue
            a=sum((cnt.get((s,p),np.zeros(6)) for s in range(t-4,t)),np.zeros(6))
            rows.append([fid.setdefault(p,len(fid)),t,sz,a.sum(),*a,*(pri[k].get(p,0) for k in ("raw","v3c","reg")),*(out[k].get(p,0) for k in ("raw","v3c","reg"))])
    return np.array(rows,float)
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=frame(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",out[n].shape,flush=True)
