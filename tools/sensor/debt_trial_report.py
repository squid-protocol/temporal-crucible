"""Report for the debt sensor v2 trial: validates the sensor's flags against actual repayment and builds the ranked worklist."""
import sys, pickle, re, subprocess, pathlib, warnings, collections, numpy as np, pandas as pd
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings("ignore"); HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE.parent)); import debt_lifecycle as DL
R=pickle.load(open(HERE/"debt_trial.pkl","rb")); YEAR=DL.YEAR; rng=np.random.default_rng(2982)
D=pd.concat([v["df"].assign(repo=n) for n,v in R.items() if len(v["df"])],ignore_index=True)
def auc(y,s):
    y=np.asarray(y,bool)
    if y.sum()<10 or (~y).sum()<10: return np.nan
    r=rankdata(s); n1=y.sum(); return (r[y].sum()-n1*(n1+1)/2)/(n1*(~y).sum())
print(f"item-observations {len(D):,} (open debt items at half-year dates) from {D.repo.nunique()} C projects; repaid within 2 years: {100*D.repaid2y.mean():.1f}%")
print("\nA. DOES THE SENSOR'S 'FOSSIL' FLAG MEAN ANYTHING?  share repaid within 2 years (yardstick = repaid-debt ages known at that date only; no leakage)")
print(f"  {'repo':10s} {'obs':>6s} {'fossil share':>12s} {'repaid: fossils':>16s} {'repaid: not fossils':>20s}")
for n,g in D.groupby("repo"):
    f=g[g.fossil==1]; nf=g[g.fossil==0]; print(f"  {n:10s} {len(g):6d} {100*g.fossil.mean():11.0f}% {100*f.repaid2y.mean() if len(f) else float('nan'):15.1f}% {100*nf.repaid2y.mean() if len(nf) else float('nan'):19.1f}%")
f=D[D.fossil==1]; nf=D[D.fossil==0]; print(f"  {'ALL':10s} {len(D):6d} {100*D.fossil.mean():11.0f}% {100*f.repaid2y.mean():15.1f}% {100*nf.repaid2y.mean():19.1f}%")
print("\nB. REPO-RELATIVE vs GLOBAL AGE: AUC for telling which items will NOT be repaid within 2 years (higher = better), per repo then mean")
res=collections.defaultdict(list)
for n,g in D.groupby("repo"):
    y=1-g.repaid2y
    for lab,s in (("raw age (years)",g.age),("age percentile within the repo",g.age_pct),("fossil flag",g.fossil),("age > 5 years (global threshold)",(g.age>5).astype(int))): res[lab].append(auc(y,s))
for k,v in res.items(): print(f"  {k:36s} mean {np.nanmean(v):.3f}   per repo: "+" ".join(f"{x:.2f}" for x in v))
print("\nC. WHAT ELSE PREDICTS STUCK DEBT?  logistic model for 'repaid within 2 years' (standardized; fit on the earlier half of dates in each repo, scored on the later half)")
D["xxx"]=(D.marker=="XXX").astype(int); D["fixme"]=D.marker.isin(["FIXME","HACK"]).astype(int); D["lc365"]=np.log1p(D.c365); D["lage"]=np.log1p(D.age); D["ltlen"]=np.log1p(D.tlen)
feat={"age only":["lage"],"+ repo yardstick (age percentile)":["lage","age_pct"],"+ marker class and bare":["lage","age_pct","xxx","fixme","bare"],"+ file activity and owner":["lage","age_pct","xxx","fixme","bare","lc365","owner_active"],"+ text length":["lage","age_pct","xxx","fixme","bare","lc365","owner_active","ltlen"]}
out=collections.defaultdict(list)
for n,g in D.groupby("repo"):
    cut=g["T"].quantile(0.5); tr=g[g["T"]<=cut]; te=g[g["T"]>cut]
    if te.repaid2y.sum()<10 or (1-te.repaid2y).sum()<10 or tr.repaid2y.nunique()<2: continue
    for lab,cols in feat.items():
        mu,sd=tr[cols].mean(),tr[cols].std().replace(0,1); m=LogisticRegression(max_iter=600).fit((tr[cols]-mu)/sd,tr.repaid2y); out[lab].append(auc(te.repaid2y,m.predict_proba((te[cols]-mu)/sd)[:,1]))
for k,v in out.items(): print(f"  {k:36s} AUC mean {np.nanmean(v):.3f} over {len(v)} repos")
cols=feat["+ text length"]; mu,sd=D[cols].mean(),D[cols].std(); m=LogisticRegression(max_iter=800).fit((D[cols]-mu)/sd,D.repaid2y); print("  odds ratios per 1 sd (all data): "+", ".join(f"{c} {np.exp(b):.2f}" for c,b in zip(cols,m.coef_[0])))
print("\nD. IS THE 'CHEAP MOMENT' REAL?  repaid within 2 years among FOSSILS, by file activity and by owner")
fo=D[D.fossil==1]
for lab,msk in (("file quiet (0 commits in last year)",fo.c365==0),("file moderately active (1-9 commits)",(fo.c365>=1)&(fo.c365<10)),("file hot (10+ commits)",fo.c365>=10),("owner still active",fo.owner_active==1),("owner inactive",fo.owner_active==0)):
    g=fo[msk]; 
    if len(g)>30: print(f"  {lab:40s} n {len(g):5d}  repaid {100*g.repaid2y.mean():5.1f}%")
print("  all items, same split:  "+"  ".join(f"{lab} {100*D[m].repaid2y.mean():.1f}%" for lab,m in (("class TODO",D.marker=="TODO"),("FIXME/HACK",D.marker.isin(["FIXME","HACK"])),("XXX",D.marker=="XXX"),("bare",D.bare==1),("explained",D.bare==0))))
# ranked worklist at HEAD
print("\nE. RANKED WORKLIST AT HEAD (original ages; stuck probability from the model above; ranked by stuck probability x file activity; fossils flagged)")
_lc={}
def lines_for(repo,path,text,k=0):
    key=(repo,path)
    if key not in _lc:
        _lc[key]=collections.defaultdict(list)
        for i,ln in enumerate(DL.git(DL.POOL_DIR/repo,"show",f"HEAD:{path}").splitlines(),1):
            d=DL.debt_line(ln)
            if d: _lc[key][d[1]].append(i)
    L=_lc[key].get(text,[]); return L[k] if k<len(L) else None
for n in ("curl","libgit2","libxml2","redis"):
    H=pd.DataFrame(R[n]["head"]); hc=R[n]["head_ct"]; ndup=len(H)
    if not len(H): continue
    # features at HEAD
    sub=D[D.repo==n]; 
    closed=np.sort([(i["end"]-i["start"])/YEAR for i in []]) if False else None
    items_age=(hc-H.start)/YEAR; p90=sub.p90.iloc[-1] if len(sub) else np.nan; apct=np.interp(items_age,np.sort(sub.age.values),np.linspace(0,1,len(sub))) if len(sub) else 0
    import subprocess
    act=collections.Counter(p for p in DL.git(DL.POOL_DIR/n,"log","--no-merges",f"--since=@{int(hc-YEAR)}","--name-only","--format=").splitlines() if p)
    H["age"]=items_age; H["fossil"]=H.age>p90; H["c365"]=H.path.map(lambda p:act.get(p,0)); H["xxx"]=(H.marker=="XXX").astype(int); H["fixme"]=H.marker.isin(["FIXME","HACK"]).astype(int)
    Xh=pd.DataFrame({"lage":np.log1p(H.age),"age_pct":sub.age_pct.rank(pct=True).reindex(range(len(H))).fillna(0.9).values if False else np.clip(np.interp(H.age,np.sort(sub.age.values),np.sort(sub.age_pct.values)),0,1),"xxx":H.xxx,"fixme":H.fixme,"bare":H.bare.astype(int),"lc365":np.log1p(H.c365),"owner_active":H.author.isin(set(DL.git(DL.POOL_DIR/n,"log","--no-merges",f"--since=@{int(hc-2*YEAR)}","--format=%ae").lower().split())).astype(int),"ltlen":np.log1p(H.text.str.len())})
    pr=m.predict_proba(((Xh[cols]-mu)/sd))[:,1]; H["stuck"]=1-pr; H["rank"]=H.stuck*(1+np.log1p(H.c365)); seen=collections.Counter(); ln_=[]
    for p,t in zip(H.path,H.text): ln_.append(lines_for(n,p,t,seen[(p,t)])); seen[(p,t)]+=1
    H["line"]=ln_; resolved=H.line.notna().mean()
    print(f"\n  === {n}: {len(H)} open markers; fossils (older than the repo's own 90th-percentile repayment age, {p90:.1f} y): {100*H.fossil.mean():.0f}%; median original age {H.age.median():.1f} y; line resolved for {100*resolved:.0f}% of markers" )
    for _,r in H.sort_values("rank",ascending=False).head(6).iterrows(): print(f"    {r.path}:{int(r.line) if r.line==r.line and r.line is not None else '?'}  {r.marker:5s} age {r.age:5.1f} y  stuck {100*r.stuck:3.0f}%  file commits last year {int(r.c365):3d}  {'FOSSIL' if r.fossil else '      '} | {r.text[:62]}")
