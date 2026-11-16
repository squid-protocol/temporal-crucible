"""Do the surface-area metrics add anything to predicting later fixes, or later change, beyond size and prior fixes?"""
import sys, json, subprocess, warnings, collections, numpy as np, pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings("ignore")
sys.path.insert(0,".")
import sa_load as L
EV="/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"
REPOS=["curl","libgit2","redis","libxml2","prometheus","sphinx","ripgrep"]; RISK=[c for c in L.RISK if c not in("risk_spec_match","risk_stability","risk_churn")]
def auc(y,s):
    y=np.asarray(y,bool)
    if y.sum()<10 or (~y).sum()<10: return np.nan
    r=rankdata(s); n1=y.sum(); return (r[y].sum()-n1*(n1+1)/2)/(n1*(~y).sum())
def frame(name):
    df,sig=L.load(name,every=4); sn=json.load(open(f"{L.B}/scan_{name}/snapshots.json")); ctc={}
    def ct(i):
        if i not in ctc: ctc[i]=int(subprocess.run(["git","-C",f"{POOL}/{name}","show","-s","--format=%ct",sn[i]["commit"]],capture_output=True,text=True).stdout.strip())
        return ctc[i]
    fx={}
    for tag,suf in (("raw","_xc"),("v3c","_xc2")):
        ev=json.load(open(f"{EV}/{name}{suf}.json"))["events"]; fx[tag]=[(e["ct"],f) for e in ev for f in e.get("c_files",[])]
        if tag=="v3c": fx["reg"]=[(e["ct"],f) for e in ev if e.get("class")=="regression" for f in e.get("c_files",[])]
    snaps=sorted(df.snap.unique()); rows=[]
    for t in snaps:
        t4=t+4
        if t4>=df.nsnap.iloc[0] or t-4<0 or t4 not in snaps: continue
        a=df[df.snap==t].copy(); b=df[df.snap==t4].set_index("file_path")
        pri={k:collections.Counter(f for c,f in v if ct(t-4)<c<=ct(t)) for k,v in fx.items()}; out={k:collections.Counter(f for c,f in v if ct(t)<c<=ct(t4)) for k,v in fx.items()}
        for k in fx: a["prior_"+k]=a.file_path.map(pri[k]).fillna(0); a["out_"+k]=a.file_path.map(out[k]).fillna(0)
        a["next_loc"]=a.file_path.map(b.coding_loc); a["changed"]=(a.next_loc.fillna(0)-a.coding_loc).abs()/a.coding_loc.clip(lower=1)
        a["t"]=t; rows.append(a)
    return pd.concat(rows,ignore_index=True)
def run():
    F=pd.concat([frame(n) for n in REPOS],ignore_index=True)
    for c in RISK: F[c+"_r"]=F.groupby(["repo","t"])[c].rank(pct=True)
    F["lsize"]=np.log1p(F.coding_loc); F["lsize_r"]=F.groupby(["repo","t"]).lsize.rank(pct=True)
    print(f"{len(F):,} file-years, {F.file_path.nunique():,} files, {F.repo.nunique()} repos")
    R_=[c+"_r" for c in RISK]
    print("\nA. LATER FIXES: AUC for 'any fix next year', later half of each repo (fit on the earlier half); mean over repos and range")
    for tag in ("raw","v3c","reg"):
        res=collections.defaultdict(list)
        for n,g in F.groupby("repo"):
            cut=g.t.median(); tr=g[g.t<=cut]; te=g[g.t>cut]; y=te["out_"+tag]>0
            if y.sum()<20: continue
            for lab,cols in (("size",["lsize"]),("size+prior",["lsize",np.log1p(g["prior_"+tag]).name]),("size+metrics",["lsize"]+R_),("size+prior+metrics",["lsize","lp"]+R_)):
                pass
            tr=tr.assign(lp=np.log1p(tr["prior_"+tag])); te=te.assign(lp=np.log1p(te["prior_"+tag]))
            for lab,cols in (("size",["lsize"]),("size+prior",["lsize","lp"]),("size+metrics",["lsize"]+R_),("size+prior+metrics",["lsize","lp"]+R_)):
                m=LogisticRegression(max_iter=500,C=1.0).fit(tr[cols],tr["out_"+tag]>0); res[lab].append(auc(y,m.predict_proba(te[cols])[:,1]))
        print(f"  label {tag:4s}: "+"   ".join(f"{k} {np.nanmean(v):.3f}" for k,v in res.items())+f"   gain from metrics: over size {np.nanmean(np.array(res['size+metrics'])-np.array(res['size'])):+.3f}, over size+prior {np.nanmean(np.array(res['size+prior+metrics'])-np.array(res['size+prior'])):+.3f}")
    print("\nB. SINGLE METRIC WITHIN SIZE: AUC for later fix (v3c) inside each size quartile, median over repo-quartiles (0.5 = nothing beyond size)")
    for c in RISK:
        v=[]
        for n,g in F.groupby("repo"):
            q=pd.qcut(g.lsize.rank(method="first"),4,labels=False)
            for k in range(4):
                s=g[q==k]; v.append(auc(s["out_v3c"]>0,s[c]))
        print(f"  {c[5:]:15s} {np.nanmedian(v):.3f}  [{np.nanmin(v):.2f},{np.nanmax(v):.2f}]")
    print("\nC. LATER CHANGE: Spearman between metric and relative change in the file's size over the next year, within size quartile (median over repo-quartiles)")
    for c in RISK:
        v=[]
        for n,g in F.groupby("repo"):
            q=pd.qcut(g.lsize.rank(method="first"),4,labels=False)
            for k in range(4):
                s=g[q==k].dropna(subset=["changed"]); 
                if len(s)>80: v.append(spearmanr(s[c],s.changed).statistic)
        print(f"  {c[5:]:15s} {np.nanmedian(v):+.2f}  [{np.nanmin(v):+.2f},{np.nanmax(v):+.2f}]")
run()
