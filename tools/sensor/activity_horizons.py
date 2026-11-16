"""Activity sensor test: do separate time horizons (30/90/365 days, lifetime, dormancy, authors) carry non-redundant information, and
do they beat the engine's churn and stability? 7 repos, history-aware (as-of) scans, forward-in-time split."""
import sys, json, glob, sqlite3, subprocess, bisect, warnings, collections, numpy as np, pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA
warnings.filterwarnings("ignore")
SA="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area"; B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"
EV="/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; DAY=86400
REPOS=sys.argv[1:] or ["curl","libgit2","redis","libxml2","prometheus","sphinx","ripgrep"]
ENG=["risk_churn","risk_stability","raw_churn_freq","ownership_entropy","silo_risk"]
HOR=["c30","c90","c365","clife","age_y","since_last_d","auth365","top_share365"]
def auc(y,s):
    y=np.asarray(y,bool)
    if y.sum()<10 or (~y).sum()<10: return np.nan
    r=rankdata(s); n1=y.sum(); return (r[y].sum()-n1*(n1+1)/2)/(n1*(~y).sum())
def frame(name):
    sn=json.load(open(f"{B}/scan_{name}/snapshots.json")); files=sorted(glob.glob(f"{SA}/hist/{name}/h*_galaxy_master.db")); idx=[int(f.split("/h")[-1][:3]) for f in files]
    ct={}; 
    for i in idx+[idx[-1]]: ct[i]=int(subprocess.run(["git","-C",f"{POOL}/{name}","show","-s","--format=%ct",sn[i]["commit"]],capture_output=True,text=True).stdout.strip())
    log=subprocess.run(["git","-C",f"{POOL}/{name}","log","--no-merges","--name-only","--format=@@%ct\t%ae",sn[idx[-1]]["commit"]],capture_output=True,text=True,errors="replace").stdout
    tl=collections.defaultdict(list); cur=None
    for ln in log.splitlines():
        if ln.startswith("@@"): t,a=ln[2:].split("\t"); cur=(int(t),a.lower())
        elif ln and cur: tl[ln].append(cur)
    for p in tl: tl[p].sort()
    times={p:np.array([x[0] for x in v]) for p,v in tl.items()}
    fx={}
    for tag,suf in (("raw","_xc"),("v3c","_xc2")):
        ev=json.load(open(f"{EV}/{name}{suf}.json"))["events"]; fx[tag]=[(e["ct"],f) for e in ev for f in e.get("c_files",[])]
        if tag=="v3c": fx["reg"]=[(e["ct"],f) for e in ev if e.get("class")=="regression" for f in e.get("c_files",[])]
    dfs={}
    for f,i in zip(files,idx):
        con=sqlite3.connect(f"file:{f}?mode=ro",uri=True); cols=[r[1] for r in con.execute("PRAGMA table_info(file_data)")]
        want=[c for c in ["file_path","coding_loc","function_count"]+ENG if c in cols]; d=pd.read_sql_query(f"SELECT {','.join(want)} FROM file_data WHERE function_count>=1",con); con.close(); dfs[i]=d
    rows=[]
    for k in range(1,len(idx)-1):
        t=idx[k]; tp=idx[k-1]; tn=idx[k+1]; T=ct[t]; a=dfs[t].copy(); b=dfs[tn].set_index("file_path")
        feats=[]
        for p in a.file_path:
            arr=times.get(p)
            if arr is None: feats.append((0,0,0,0,0.0,np.nan,0,0.0)); continue
            n=int(np.searchsorted(arr,T,side="right")); 
            if n==0: feats.append((0,0,0,0,0.0,np.nan,0,0.0)); continue
            lo=lambda d_: int(n-np.searchsorted(arr[:n],T-d_*DAY,side="right"))
            recent=[x[1] for x in tl[p][:n] if x[0]>T-365*DAY]; cnt=collections.Counter(recent)
            feats.append((lo(30),lo(90),lo(365),n,(T-arr[0])/(365.25*DAY),(T-arr[n-1])/DAY,len(cnt),(max(cnt.values())/len(recent)) if recent else 0.0))
        F=pd.DataFrame(feats,columns=HOR,index=a.index); a=pd.concat([a,F],axis=1)
        for tag,v in fx.items():
            a["prior_"+tag]=a.file_path.map(collections.Counter(f for c,f in v if ct[tp]<c<=T)).fillna(0); a["out_"+tag]=a.file_path.map(collections.Counter(f for c,f in v if T<c<=ct[tn])).fillna(0)
        a["next_loc"]=a.file_path.map(b.coding_loc); a["changed"]=(a.next_loc.fillna(0)-a.coding_loc).abs()/a.coding_loc.clip(lower=1); a["t"]=t; a["repo"]=name; rows.append(a)
    return pd.concat(rows,ignore_index=True)
if __name__=="__main__":
    F=pd.concat([frame(n) for n in REPOS],ignore_index=True); F["since_last_d"]=F.since_last_d.fillna(F.since_last_d.max())
    print(f"{len(F):,} file-intervals, {F.repo.nunique()} repos; files with no git history up to the snapshot (renamed or new): {100*(F.clife==0).mean():.0f}%")
    for c in HOR+ENG: F[c+"_r"]=F.groupby(["repo","t"])[c].rank(pct=True)
    F["lsize"]=np.log1p(F.coding_loc)
    print("\nA. REDUNDANCY: within-repo rank correlations")
    cm=F[[c+"_r" for c in HOR+ENG]].corr(method="spearman"); cm.index=cm.columns=HOR+ENG
    print(cm.round(2).to_string())
    for lab,cols in (("engine churn+stability",["risk_churn","risk_stability"]),("engine 5 history columns",ENG),("proposed 8 horizon features",HOR),("recent (c30,c90,c365)",["c30","c90","c365"]),("long (clife,age,since_last)",["clife","age_y","since_last_d"])):
        ev=PCA().fit(F[[c+"_r" for c in cols]].values).explained_variance_ratio_; print(f"  {lab:32s} PC1 {100*ev[0]:.0f}%  participation ratio {1/np.sum(ev**2):.1f} of {len(cols)}")
    print("\nB. LATER FIXES: AUC, later half of each repo (mean over repos)")
    for tag in ("raw","v3c","reg"):
        res=collections.defaultdict(list)
        for n,g in F.groupby("repo"):
            cut=g.t.median(); tr=g[g.t<=cut].assign(lp=lambda d:np.log1p(d["prior_"+tag])); te=g[g.t>cut].assign(lp=lambda d:np.log1p(d["prior_"+tag])); y=te["out_"+tag]>0
            if y.sum()<20: continue
            E=["risk_churn_r","risk_stability_r"]; H=[c+"_r" for c in HOR]; R_=["c30_r","c90_r","c365_r"]; L_=["clife_r","age_y_r","since_last_d_r"]; O=["ownership_entropy_r","silo_risk_r","auth365_r","top_share365_r"]
            for lab,cols in (("size",["lsize"]),("size+prior",["lsize","lp"]),("+engine churn/stab",["lsize"]+E),("+recent horizons",["lsize"]+R_),("+long horizons",["lsize"]+L_),("+all 8 horizons",["lsize"]+H),("+owners only",["lsize"]+O),("prior+engine",["lsize","lp"]+E),("prior+8 horizons",["lsize","lp"]+H),("prior+horizons+engine",["lsize","lp"]+H+E)):
                m=LogisticRegression(max_iter=700).fit(tr[cols],tr["out_"+tag]>0); res[lab].append(auc(y,m.predict_proba(te[cols])[:,1]))
        print(f"  {tag:4s}: "+"  ".join(f"{k} {np.nanmean(v):.3f}" for k,v in res.items()))
    print("\nC. SINGLE FEATURES within size quartile: AUC for later fix (v3c) | Spearman with later size change (median over repo-quartiles)")
    for c in HOR+ENG:
        v=[];w=[]
        for n,g in F.groupby("repo"):
            q=pd.qcut(g.lsize.rank(method="first"),4,labels=False)
            for k in range(4):
                s=g[q==k]; v.append(auc(s["out_v3c"]>0,s[c])); s2=s.dropna(subset=["changed"]); w.append(spearmanr(s2[c],s2.changed).statistic if len(s2)>80 else np.nan)
        print(f"  {c:16s} AUC {np.nanmedian(v):.3f} [{np.nanmin(v):.2f},{np.nanmax(v):.2f}]   change rho {np.nanmedian(w):+.2f}")
