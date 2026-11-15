"""Sweep exposure as a (quasi-)natural experiment on later fixes: file-years, Poisson with log-size exposure, clustered by file."""
import sys, json, pickle, collections, subprocess, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
import statsmodels.api as sm
from structural_fingerprint import ledger as LG
import what_changes as W, sweeps as S, sweep_audit as AU
EV=AU.EV
def frame(name):
    sn=json.load(open(f"{AU.B}/scan_{name}/snapshots.json")); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]; repo=Path(f"{AU.POOL}/{name}")
    ct=[int(subprocess.run(["git","-C",str(repo),"show","-s","--format=%ct",x["commit"]],capture_output=True,text=True).stdout.strip()) for x in sn]
    led=LG.build_ledger(repo,snaps); N=len(snaps); A=[W.arrays(x.scan) for x in snaps]
    ev=pickle.load(open(f"{AU.SP}/{AU.PKL[name]}","rb"))[name]["events"]; _,_,ins=S.detect(ev)
    pos={}
    def path_of(e):
        s=e["s"]
        if "x" in e: return led.keys[s][e["x"]][0]
        if s not in pos: pos[s]={int(v):i for i,v in enumerate(led.ids[s])}
        i=pos[s].get(e["id"]); return led.keys[s][i][0] if i is not None else None
    org=collections.defaultdict(int); swp=collections.defaultdict(int)
    for i,e in enumerate(ev):
        if not e["code"]: continue
        p=path_of(e)
        if p is None: continue
        (swp if i in ins else org)[(e["s"],p)]+=1
    fx=json.load(open(f"{EV}/{name}_xc2.json"))["events"]; fxl=[(e["ct"],f) for e in fx for f in e.get("c_files",[])]
    rows=[]; fid={}
    for t in range(4,N-4,4):
        size=collections.Counter()
        for i,(p,_) in enumerate(led.keys[t]): size[p]+=A[t][1][i]
        prior=collections.Counter(f for c,f in fxl if ct[t-4]<c<=ct[t]); out=collections.Counter(f for c,f in fxl if ct[t]<c<=ct[t+4])
        for p,sz in size.items():
            if sz<5: continue
            co=sum(org.get((s,p),0) for s in range(t-4,t)); cs=sum(swp.get((s,p),0) for s in range(t-4,t))
            rows.append((fid.setdefault(p,len(fid)),t,sz,co,cs,prior.get(p,0),out.get(p,0)))
    return np.array(rows,float)
def fit(R):
    y=R[:,6]; off=np.log(R[:,2]); X=np.column_stack([np.ones(len(R)),np.log1p(R[:,5]),np.log1p(R[:,3]),np.log1p(R[:,4])])
    m=sm.GLM(y,X,family=sm.families.Poisson(),offset=off).fit(cov_type="cluster",cov_kwds={"groups":R[:,0]})
    ci=m.conf_int(); return {k:(float(np.exp(m.params[i])),float(np.exp(ci[i,0])),float(np.exp(ci[i,1]))) for i,k in ((1,"prior_fix"),(2,"organic_edits"),(3,"sweep_edits"))}
def mh(R,rng,B=300):
    """Mantel-Haenszel rate ratio swept (any sweep edit) vs unswept inside strata of size quartile x prior fix x organic churn tercile."""
    sw=R[:,4]>0
    def est(idx):
        r=R[idx]; swi=sw[idx]; sz=np.digitize(r[:,2],np.quantile(r[:,2],[.25,.5,.75])); pf=(r[:,5]>0).astype(int); oc=np.digitize(r[:,3],np.quantile(r[:,3],[.34,.67]))
        key=sz*10+pf*3+oc; num=den=0.0
        for k in np.unique(key):
            m=key==k; a=m&swi; b=m&~swi
            if a.sum()<3 or b.sum()<3: continue
            E1=r[a,2].sum(); E0=r[b,2].sum(); y1=r[a,6].sum(); y0=r[b,6].sum(); T=E0+E1
            num+=y1*E0/T; den+=y0*E1/T
        return num/den if den>0 else np.nan
    pt=est(np.arange(len(R))); files=np.unique(R[:,0]); byf=collections.defaultdict(list)
    for i,f in enumerate(R[:,0]): byf[f].append(i)
    bs=[]
    for _ in range(B):
        pick=rng.choice(files,len(files)); idx=np.concatenate([byf[f] for f in pick]); bs.append(est(idx))
    return float(pt),float(np.nanpercentile(bs,2.5)),float(np.nanpercentile(bs,97.5))
if __name__=="__main__":
    out={}; rng=np.random.default_rng(2982)
    for n in sys.argv[2:]:
        R=frame(n); out[n]=dict(n=len(R),files=int(len(np.unique(R[:,0]))),events=float(R[:,6].sum()),swept_share=float((R[:,4]>0).mean()),glm=fit(R),mh=mh(R,rng)); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
