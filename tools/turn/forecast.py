"""Forecast ladder: will a surviving function change or die within h quarters?  Climatology -> + persistence -> + structure -> + git process.  Forward-in-time split, per repo."""
import sys, subprocess, pickle, collections, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss
from structural_fingerprint import ledger as LG
import what_changes as W, turn_score as T
def git_activity(repo,c0,c1):
    r=subprocess.run(["git","-C",str(repo),"log","--no-merges","--name-only","--format=@@%an",f"{c0}..{c1}"],capture_output=True,text=True,errors="replace",check=False).stdout
    nc=collections.Counter(); au=collections.defaultdict(set); a=None; ncommits=0; authors=set()
    for ln in r.splitlines():
        if ln.startswith("@@"): a=ln[2:]; ncommits+=1; authors.add(a)
        elif ln.strip() and a is not None: nc[ln.strip()]+=1; au[ln.strip()].add(a)
    return nc,au,ncommits,len(authors)
def dataset(name,hs=(1,4)):
    sn=T.snaplist(name); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]; repo=Path(f"{T.POOL}/{name}")
    led=LG.build_ledger(repo,snaps); N=len(snaps); A=[W.arrays(x.scan) for x in snaps]
    H=[np.array([hash((int(A[s][1][i]),int(A[s][2][i]),int(A[s][3][i]),A[s][0][i].tobytes())) for i in range(len(led.ids[s]))]) for s in range(N)]
    pos=[{int(x):i for i,x in enumerate(a)} for a in led.ids]
    act=[None]+[git_activity(repo,snaps[s-1].commit,snaps[s].commit) for s in range(1,N)]
    last={}; first={}; rows=[]; tg={h:[] for h in hs}; meta=[]; rate_hist=[]
    for s in range(N):
        n=len(led.ids[s]); ch=np.zeros(n,bool); born=np.zeros(n,bool)
        for i,x in enumerate(led.ids[s].tolist()):
            if x not in first: first[x]=s; last[x]=s; born[i]= s>0
            elif s>0 and x in pos[s-1] and H[s][i]!=H[s-1][pos[s-1][x]]: last[x]=s; ch[i]=True
        dprev=(len(led.deaths(s-1))/max(len(led.ids[s-1]),1)) if s>=1 else 0.0
        rate_hist.append(float(ch.mean())+dprev if s>0 else 0.0)
        if s==0 or s>=N-1: continue
        r1=rate_hist[-1]; r4=1-np.prod([1-x for x in rate_hist[-4:]])
        e=led._snaps[s].view.edges; indeg=np.zeros(n); outdeg=np.zeros(n)
        if len(e): np.add.at(indeg,e[:,1],1); np.add.at(outdeg,e[:,0],1)
        nc,au,ncm,nau=act[s]; paths=[k[0] for k in led.keys[s]]; byfile=collections.defaultdict(list)
        for i,p in enumerate(paths): byfile[p].append(i)
        ffrac=np.zeros(n); fcount=np.zeros(n)
        for p,idx in byfile.items(): ffrac[idx]=ch[idx].mean(); fcount[idx]=len(idx)
        loc=A[s][1]; sig=A[s][0]; dens=sig/np.maximum(loc,1)[:,None]
        for i,x in enumerate(led.ids[s].tolist()):
            p=paths[i]; age=s-first[x]
            rows.append([age,1.0 if first[x]==0 else 0.0,loc[i],                                  # R0
                         1.0 if ch[i] else 0.0,s-last[x],1.0 if born[i] else 0.0,                  # R1
                         A[s][2][i],A[s][3][i],indeg[i],outdeg[i],*dens[i],                       # R2
                         nc.get(p,0),len(au.get(p,())),ffrac[i],fcount[i],ncm,nau,r1,r4])               # R3
            meta.append(s)
            for h in hs:
                j=s+h
                if j<N: tg[h].append(1.0 if (x not in pos[j] or H[j][pos[j][x]]!=H[s][i]) else 0.0)
                else: tg[h].append(np.nan)
    X=np.array(rows,float); return X,{h:np.array(v) for h,v in tg.items()},np.array(meta),N,len(W.FAM)
def run(name):
    X,Y,S,N,nf=dataset(name); R=dict(name=name,N=N,rows=len(X)); split=int(0.6*N)
    c0,c1,c2,c3=3,6,10+nf,X.shape[1]-2; sets={"R0 age+size":list(range(0,3)),"R1 +persistence":list(range(0,6))+[X.shape[1]-2,X.shape[1]-1],"R2 +structure":list(range(0,c2))+[X.shape[1]-2,X.shape[1]-1],"R3 +git process":list(range(0,c3+2))}
    rng=np.random.default_rng(2982)
    for h,y in Y.items():
        tr=np.flatnonzero((S<=split-h)&~np.isnan(y)); te=np.flatnonzero((S>split)&~np.isnan(y))
        if len(tr)<500 or len(te)<500: continue
        if len(tr)>150000: tr=rng.choice(tr,150000,replace=False)
        base=y[tr].mean(); b0=np.mean((y[te]-base)**2); ref=X[te][:,-2] if h==1 else X[te][:,-1]; b_ref=np.mean((y[te]-ref)**2); out={"bss_recent_baseline":float(1-b_ref/b0),"base_train":float(base),"base_test":float(y[te].mean()),"n_test":int(len(te))}
        for lab,cols in sets.items():
            m=HistGradientBoostingClassifier(max_iter=100,max_depth=3,learning_rate=0.06,min_samples_leaf=300,l2_regularization=5.0,random_state=2982).fit(X[tr][:,cols],y[tr]); p=m.predict_proba(X[te][:,cols])[:,1]
            out[lab]=dict(bss=float(1-np.mean((y[te]-p)**2)/b0),bss_recent=float(1-np.mean((y[te]-p)**2)/b_ref),auc=float(roc_auc_score(y[te],p)))
        R[h]=out
    return R
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
