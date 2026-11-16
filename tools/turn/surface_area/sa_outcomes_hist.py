"""History-aware test (main engine, as-of scans from real worktrees): do churn, stability and the other surface-area metrics add to size and prior fixes for predicting later fixes and later change?"""
import sys, json, glob, sqlite3, subprocess, warnings, collections, numpy as np, pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings("ignore"); sys.path.insert(0,".")
import sa_load as L
EV="/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; H="hist"
REPOS=["curl","libgit2","redis","libxml2","prometheus","sphinx","ripgrep"]
STRUCT=["risk_cognitive_load","risk_safety_score","risk_tech_debt","risk_verification","risk_api_exposure","risk_concurrency","risk_state_flux","risk_dead_code","risk_documentation"]
PROC=["risk_churn","risk_stability","raw_churn_freq","ownership_entropy","silo_risk"]
def auc(y,s):
    y=np.asarray(y,bool)
    if y.sum()<10 or (~y).sum()<10: return np.nan
    r=rankdata(s); n1=y.sum(); return (r[y].sum()-n1*(n1+1)/2)/(n1*(~y).sum())
def frame(name):
    sn=json.load(open(f"{L.B}/scan_{name}/snapshots.json")); files=sorted(glob.glob(f"{H}/{name}/h*_galaxy_master.db")); idx=[int(f.split("/h")[-1][:3]) for f in files]
    ctc={}
    def ct(i):
        if i not in ctc: ctc[i]=int(subprocess.run(["git","-C",f"{POOL}/{name}","show","-s","--format=%ct",sn[i]["commit"]],capture_output=True,text=True).stdout.strip())
        return ctc[i]
    fx={}
    for tag,suf in (("raw","_xc"),("v3c","_xc2")):
        ev=json.load(open(f"{EV}/{name}{suf}.json"))["events"]; fx[tag]=[(e["ct"],f) for e in ev for f in e.get("c_files",[])]
        if tag=="v3c": fx["reg"]=[(e["ct"],f) for e in ev if e.get("class")=="regression" for f in e.get("c_files",[])]
    dfs={}
    for f,i in zip(files,idx):
        con=sqlite3.connect(f"file:{f}?mode=ro",uri=True); cols=[r[1] for r in con.execute("PRAGMA table_info(file_data)")]
        want=[c for c in ["file_path","coding_loc","function_count"]+STRUCT+PROC if c in cols]; d=pd.read_sql_query(f"SELECT {','.join(want)} FROM file_data WHERE function_count>=1",con); con.close(); dfs[i]=d
    rows=[]
    for k in range(1,len(idx)-1):
        t=idx[k]; tp=idx[k-1]; tn=idx[k+1]; a=dfs[t].copy(); b=dfs[tn].set_index("file_path")
        for tag,v in fx.items():
            a["prior_"+tag]=a.file_path.map(collections.Counter(f for c,f in v if ct(tp)<c<=ct(t))).fillna(0); a["out_"+tag]=a.file_path.map(collections.Counter(f for c,f in v if ct(t)<c<=ct(tn))).fillna(0)
        a["next_loc"]=a.file_path.map(b.coding_loc); a["changed"]=(a.next_loc.fillna(0)-a.coding_loc).abs()/a.coding_loc.clip(lower=1); a["t"]=t; a["repo"]=name; rows.append(a)
    return pd.concat(rows,ignore_index=True)
F=pd.concat([frame(n) for n in REPOS],ignore_index=True)
for c in STRUCT+PROC: F[c+"_r"]=F.groupby(["repo","t"])[c].rank(pct=True)
F["lsize"]=np.log1p(F.coding_loc); print(f"{len(F):,} file-intervals, {F.file_path.nunique():,} files, {F.repo.nunique()} repos; churn nonzero {100*(F.risk_churn>0).mean():.0f}%, stability nonzero {100*(F.risk_stability>0).mean():.0f}%")
S_=[c+"_r" for c in STRUCT]; P_=[c+"_r" for c in PROC]
print("\nA. LATER FIXES: AUC for 'any fix in the next interval', later half of each repo (mean over repos)")
for tag in ("raw","v3c","reg"):
    res=collections.defaultdict(list)
    for n,g in F.groupby("repo"):
        cut=g.t.median(); tr=g[g.t<=cut].assign(lp=lambda d:np.log1p(d["prior_"+tag])); te=g[g.t>cut].assign(lp=lambda d:np.log1p(d["prior_"+tag])); y=te["out_"+tag]>0
        if y.sum()<20: continue
        for lab,cols in (("size",["lsize"]),("size+prior",["lsize","lp"]),("size+churn/stability",["lsize"]+P_),("size+prior+churn/stab",["lsize","lp"]+P_),("size+structural 9",["lsize"]+S_),("size+prior+structural 9",["lsize","lp"]+S_),("size+prior+all",["lsize","lp"]+S_+P_)):
            m=LogisticRegression(max_iter=600).fit(tr[cols],tr["out_"+tag]>0); res[lab].append(auc(y,m.predict_proba(te[cols])[:,1]))
    print(f"  label {tag:4s}: "+"  ".join(f"{k} {np.nanmean(v):.3f}" for k,v in res.items()))
print("\nB. SINGLE PROCESS METRICS: AUC for later fix (v3c) within size quartile, median over repo-quartiles (0.5 = nothing beyond size)")
for c in PROC+["risk_state_flux","risk_tech_debt","risk_verification","risk_cognitive_load"]:
    v=[]
    for n,g in F.groupby("repo"):
        q=pd.qcut(g.lsize.rank(method="first"),4,labels=False)
        for k in range(4): s=g[q==k]; v.append(auc(s["out_v3c"]>0,s[c]))
    print(f"  {c:20s} {np.nanmedian(v):.3f}  [{np.nanmin(v):.2f},{np.nanmax(v):.2f}]")
print("\nC. LATER CHANGE: Spearman with relative size change over the next interval, within size quartile (median over repo-quartiles)")
for c in PROC+["risk_state_flux","risk_tech_debt"]:
    v=[]
    for n,g in F.groupby("repo"):
        q=pd.qcut(g.lsize.rank(method="first"),4,labels=False)
        for k in range(4):
            s=g[q==k].dropna(subset=["changed"]); 
            if len(s)>80: v.append(spearmanr(s[c],s.changed).statistic)
    print(f"  {c:20s} {np.nanmedian(v):+.2f}  [{np.nanmin(v):+.2f},{np.nanmax(v):+.2f}]")
