import pickle, re, warnings, numpy as np, pandas as pd
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import cross_val_predict
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_mutual_info_score
warnings.filterwarnings("ignore")
import sys
PK=sys.argv[1] if len(sys.argv)>1 else "sa_files.pkl"
D,SIG=pickle.load(open(PK,"rb")); RISK=[c for c in D.columns if c.startswith("risk_")]
NAME={c:c[5:] for c in RISK}
D["is_test"]=D.file_path.str.contains(r"(^|/)(tests?|testing|spec|specs|__tests__|unittests?|fuzz\w*|testdata)(/|$)|(^|/)test_|_test\.|tests?\.\w+$",case=False,regex=True)
D["is_docs"]=D.file_path.str.contains(r"(^|/)(docs?|examples?|samples?|demos?|contrib|scripts?|tools?)(/|$)",case=False,regex=True)
D["is_vendor"]=D.file_path.str.contains(r"(^|/)(vendor|third[_-]?party|external|deps|node_modules|lib/vtls)(/|$)",case=False,regex=True)
D["is_header"]=D.file_path.str.contains(r"\.(h|hpp|hh)$",case=False,regex=True)
last=D[D.snap==D.nsnap-1].copy(); last=last[last.groupby("repo").file_path.transform("count")>=1]; print(f"file-snapshots {len(D):,}; last snapshot of each repo {len(last):,} code files in {last.repo.nunique()} repos\n")
def auc(score,mask):
    m=np.asarray(mask,bool); s=np.asarray(score,float); 
    if m.sum()<20 or (~m).sum()<20: return np.nan
    r=rankdata(s); n1=m.sum(); n0=(~m).sum(); return (r[m].sum()-n1*(n1+1)/2)/(n1*n0)
def within(f,df=last):
    v=[f(g) for _,g in df.groupby("repo") if len(g)>=60]; v=[x for x in v if x==x]; return (np.median(v),min(v),max(v),len(v)) if v else (np.nan,)*4
act=[c for c in RISK if last[c].std()>0]; print("metrics with any variance:",[NAME[c] for c in act],"| constant:",[NAME[c] for c in RISK if c not in act],"\n")
print("A. DEGENERACY  (last snapshots, pooled; share of files at exactly 0, at 100, and median among non-zero)")
for c in act:
    x=last[c]; nz=x[x>0]; print(f"  {NAME[c]:15s} zero {100*(x==0).mean():5.1f}%   at 100: {100*(x>=99.99).mean():5.1f}%   median of non-zero {nz.median() if len(nz) else float('nan'):6.1f}")
print("\nB. SIZE  Spearman with coding_loc, per repo: median [min, max] over repos")
for c in act: r=within(lambda g:spearmanr(g[c],g.coding_loc).statistic); print(f"  {NAME[c]:15s} {r[0]:+.2f} [{r[1]:+.2f},{r[2]:+.2f}]")
dens=np.log1p(last[SIG].div(last.coding_loc.clip(lower=1),axis=0)*1000).fillna(0); keep=[c for c in dens.columns if dens[c].std()>0]; dens=dens[keep]
print("\nC. IS EACH METRIC JUST A SUMMARY OF KEYWORD-FAMILY DENSITIES?  best single family (Spearman, pooled) and 5-fold R2 from all densities + size")
Xd=np.column_stack([dens.values,np.log1p(last.coding_loc.values)])
for c in act:
    y=last[c].values; rho=[(abs(spearmanr(dens[k],y).statistic),k) for k in keep[:]]; rho=[r for r in rho if r[0]==r[0]]; rho.sort(reverse=True)
    try: p=cross_val_predict(RidgeCV(alphas=[0.1,1,10,100]),Xd,rankdata(y)/len(y),cv=5); r2=1-np.sum((rankdata(y)/len(y)-p)**2)/np.sum((rankdata(y)/len(y)-np.mean(rankdata(y)/len(y)))**2)
    except Exception: r2=np.nan
    print(f"  {NAME[c]:15s} R2 {r2:.2f}   top families: "+", ".join(f"{k} {r:.2f}" for r,k in rho[:3]))
print("\nD. DIMENSIONALITY  PCA on within-repo ranks of the active metrics (pooled last snapshots)")
R=last[act+["repo"]].copy()
for c in act: R[c]=R.groupby("repo")[c].rank(pct=True)
pca=PCA().fit(R[act].values); ev=pca.explained_variance_ratio_; print("  variance explained by component:",", ".join(f"{100*v:.0f}%" for v in ev[:6]),f"| components for 90%: {int(np.searchsorted(np.cumsum(ev),0.9)+1)} of {len(act)} | participation ratio {1/np.sum(ev**2):.1f}")
cm=R[act].corr(method="spearman"); iu=np.triu_indices(len(act),1); print(f"  pairwise rank correlations among the {len(act)} metrics: median {np.median(cm.values[iu]):+.2f}, share with |r|>0.5: {100*np.mean(np.abs(cm.values[iu])>0.5):.0f}%")
print("\nE. DOES EACH METRIC TRACK WHAT ITS NAME SAYS?  Spearman with an independent measure, median [min,max] over repos")
last["doc_ratio"]=last.doc_loc/last.coding_loc.clip(lower=1); last["debt"]=last.get("state_planned_debt",0)+last.get("state_fragile_debt",0); last["conc"]=last.get("arch_concurrency",0)+last.get("def_sync_locks",0)
checks=[("cognitive_load","max_func_complexity"),("cognitive_load","avg_func_complexity"),("api_exposure","normalized_blast_radius"),("api_exposure","internal_dependency_links"),("api_exposure","pagerank_score"),("api_exposure","is_header"),("documentation","doc_ratio"),("tech_debt","debt"),("concurrency","conc"),("state_flux","state_flux"),("dead_code","state_unreferenced"),("safety_score","def_safety"),("safety_score","state_danger"),("verification","is_test"),("verification","def_test")]
for m,ind in checks:
    c="risk_"+m
    if c not in last or ind not in last: continue
    r=within(lambda g:spearmanr(g[c],g[ind].astype(float)).statistic); print(f"  {m:15s} vs {ind:26s} {r[0]:+.2f} [{r[1]:+.2f},{r[2]:+.2f}]")
print("\nF. WHAT DO THEY SEPARATE?  AUC for telling a role from other files (within repo, median over repos) and share of variance that is between repos")
for role in ("is_test","is_header","is_docs","is_vendor"):
    print(f"  {role:10s} (share of files {100*last[role].mean():.0f}%): "+"  ".join(f"{NAME[c][:9]} {within(lambda g:auc(g[c],g[role]))[0]:.2f}" for c in act))
print("\nG. THE MIX: cluster files on the active metrics' within-repo ranks (k=6), pooled")
km=KMeans(6,n_init=10,random_state=2982).fit(R[act].values); last["cl"]=km.labels_
cen=pd.DataFrame(km.cluster_centers_,columns=[NAME[c] for c in act]).round(2); cen["files"]=np.bincount(km.labels_); cen["is_test"]=[last[last.cl==k].is_test.mean() for k in range(6)]; cen["header"]=[last[last.cl==k].is_header.mean() for k in range(6)]; cen["median_loc"]=[last[last.cl==k].coding_loc.median() for k in range(6)]
print(cen.to_string())
print("  agreement of clusters with: role (test/header/docs/vendor) AMI",round(adjusted_mutual_info_score(last.cl,(last.is_test*1+last.is_header*2+last.is_docs*4+last.is_vendor*8)),3),"| language AMI",round(adjusted_mutual_info_score(last.cl,last.language),3),"| repo AMI",round(adjusted_mutual_info_score(last.cl,last.repo),3),"| size quartile AMI",round(adjusted_mutual_info_score(last.cl,pd.qcut(last.coding_loc,4,labels=False,duplicates="drop")),3),"| archetype AMI",round(adjusted_mutual_info_score(last.cl,last.file_archetype.astype(str)),3))
print("\nH. STABILITY OVER TIME  Spearman of the same file's value two sampled snapshots apart (~2 years), median over repos")
res={}
for n,g in D.groupby("repo"):
    snaps=sorted(g.snap.unique())
    for c in act+["coding_loc"]:
        v=[]
        for a,b in zip(snaps[:-1],snaps[1:]):
            m=g[g.snap==a].merge(g[g.snap==b],on="file_path",suffixes=("_a","_b"))
            if len(m)>=60: v.append(spearmanr(m[c+"_a"],m[c+"_b"]).statistic)
        if v: res.setdefault(c,[]).append(np.nanmedian(v))
print("  "+"  ".join(f"{NAME.get(c,c)[:9]} {np.nanmedian(v):.2f}" for c,v in res.items()))

print("\nI. CHURN AND STABILITY (only populated where the scan could read git history)")
for c in ("risk_churn","risk_stability"):
    if c in last:
        x=last[c]; print(f"  {c[5:]:10s} nonzero {100*(x>0).mean():5.1f}% | at 100 {100*(x>=99.99).mean():5.1f}% | repos with any nonzero {last.loc[x>0,'repo'].nunique()} of {last.repo.nunique()}")
H=last[(last.get("risk_stability",0)>0)|(last.get("risk_churn",0)>0)]
if len(H)>200:
    print(f"  among {len(H):,} files with history ({H.repo.nunique()} repos): Spearman of churn with: "+", ".join(f"{k} {spearmanr(H['risk_churn'],H[k],nan_policy='omit').statistic:+.2f}" for k in ["coding_loc","risk_stability","raw_churn_freq","ownership_entropy","silo_risk","risk_cognitive_load","risk_tech_debt","risk_state_flux"] if k in H))
    print("  stability with: "+", ".join(f"{k} {spearmanr(H['risk_stability'],H[k],nan_policy='omit').statistic:+.2f}" for k in ["coding_loc","risk_churn","raw_churn_freq","ownership_entropy","risk_cognitive_load","risk_tech_debt"] if k in H))
