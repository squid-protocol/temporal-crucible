"""Mock-up of the activity sensor on one repo (default curl): compute the panel, back-test its worklists and axes against what happened next,
and compare with the engine's churn and stability.   python tools/sensor/activity_mockup.py [repo]"""
from bisect import bisect_right
import sys, json, glob, sqlite3, subprocess, pickle, warnings, collections, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings("ignore")
ROOT="/srv/storage_16tb/projects"; B=f"{ROOT}/curl_call_graph_evolution/turn_v2"; SA=f"{B}/surface_area"; POOL=f"{ROOT}/temporal-crucible-pool"; DAY=86400
EV=f"{ROOT}/temporal-crucible/.claude/worktrees/turn/events"
sys.path.insert(0,f"{ROOT}/structural-fingerprint-scanner/src"); sys.path.insert(0,f"{ROOT}/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/turn"); sys.path.insert(0,f"{ROOT}/historical-call-graph-gif")
from structural_fingerprint import ledger as LG
import sweeps as S
name=sys.argv[1] if len(sys.argv)>1 else "curl"
def auc(y,s):
    y=np.asarray(y,bool)
    if y.sum()<10 or (~y).sum()<10: return np.nan
    r=rankdata(s); n1=y.sum(); return (r[y].sum()-n1*(n1+1)/2)/(n1*(~y).sum())
sn=json.load(open(f"{B}/scan_{name}/snapshots.json")); files=sorted(glob.glob(f"{SA}/hist/{name}/h*_galaxy_master.db")); idx=[int(f.split("/h")[-1][:3]) for f in files]
git=lambda *a: subprocess.run(["git","-C",f"{POOL}/{name}",*a],capture_output=True,text=True,errors="replace").stdout
ct={i:int(git("show","-s","--format=%ct",sn[i]["commit"]).strip()) for i in range(len(sn))}
log=git("log","--no-merges","--reverse","-M","--name-status","--format=@@%ct\t%ae",sn[idx[-1]]["commit"])
fid={}; nid=0; evid=collections.defaultdict(list); pidh=collections.defaultdict(list); au=collections.defaultdict(list); cur=None
for ln in log.splitlines():
    if ln.startswith("@@"): t,a=ln[2:].split("\t"); cur=(int(t),a.lower()); au[cur[1]].append(cur[0])
    elif ln and cur:
        parts=ln.split("\t"); st=parts[0][0]
        if st in "RC" and len(parts)==3:
            old,new=parts[1],parts[2]; i=fid.get(old)
            if i is None: i=nid; nid+=1
            if st=="R": fid.pop(old,None)
            fid[new]=i; pidh[new].append((cur[0],i)); evid[i].append(cur)
        elif st=="A" and len(parts)>=2:
            i=nid; nid+=1; fid[parts[1]]=i; pidh[parts[1]].append((cur[0],i)); evid[i].append(cur)
        elif st=="M" and len(parts)>=2:
            i=fid.get(parts[1])
            if i is None: i=nid; nid+=1; fid[parts[1]]=i; pidh[parts[1]].append((cur[0],i))
            evid[i].append(cur)
        elif st=="D" and len(parts)>=2: fid.pop(parts[1],None)
au={a:np.array(sorted(v)) for a,v in au.items()}
for i in evid: evid[i].sort()
times={i:np.array([x[0] for x in v]) for i,v in evid.items()}
def pid(path,T):
    h=pidh.get(path)
    if not h: return None
    k=bisect_right([x[0] for x in h],T)-1
    return h[k][1] if k>=0 else None
# mechanical share from the sweep detector, per (pair, file)
snaps=[LG.Snapshot(Path(x["db"]),x["commit"],"") for x in sn]; led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps)
EVF={"curl":"ts_edits_c2.pkl","libgit2":"ts_edits_c2.pkl","redis":"ts_edits_c2.pkl","libxml2":"ts_edits_ho_c.pkl"}[name]; evs=pickle.load(open(f"{B}/analysis/{EVF}","rb"))[name]["events"]; _,_,ins=S.detect(evs); fe=collections.defaultdict(lambda:[0,0])
for i,e in enumerate(evs):
    if e["code"]: fe[(e["s"],led.keys[e["s"]][e["x"]][0])][1 if i in ins else 0]+=1
fx={}
for tag,suf in (("raw","_xc"),("v3c","_xc2")):
    e_=json.load(open(f"{EV}/{name}{suf}.json"))["events"]; fx[tag]=[(e["ct"],pid(f,e["ct"])) for e in e_ for f in e.get("c_files",[]) if pid(f,e["ct"]) is not None]
rows=[]; dbs={}
for f,i in zip(files,idx):
    con=sqlite3.connect(f"file:{f}?mode=ro",uri=True); dbs[i]=pd.read_sql_query("SELECT file_path,coding_loc,risk_churn,risk_stability,pagerank_score,normalized_blast_radius FROM file_data WHERE function_count>=1",con); con.close()
for k in range(1,len(idx)-1):
    t=idx[k]; tn=idx[k+1]; tp=idx[k-1]; T=ct[t]; a=dbs[t].copy(); nxt=dbs[tn].set_index("file_path")
    out=[]; ids=[]
    for p in a.file_path:
        fi=pid(p,T); ids.append(fi); arr=times.get(fi) if fi is not None else None
        if arr is None or not len(arr) or arr[0]>T: out.append((0,0,0,0.0,np.nan,0,0.0,False,0)); continue
        n=int(np.searchsorted(arr,T,side="right")); lo=lambda d: int(n-np.searchsorted(arr[:n],T-d*DAY,side="right"))
        recent=[x[1] for x in evid[fi][:n] if x[0]>T-365*DAY]; c=collections.Counter(recent); top=c.most_common(1)[0][0] if c else None
        topa=evid[fi][n-1][1] if top is None else top
        oa=bool(len(au.get(topa,[])) and (au[topa]<=T).any() and au[topa][au[topa]<=T][-1]>T-2*365.25*DAY)
        nn=int(np.searchsorted(arr,ct[tn],side="right"))-n
        out.append((lo(90),lo(365),n,(T-arr[0])/(365.25*DAY),(T-arr[n-1])/DAY,len(c),(max(c.values())/len(recent)) if recent else 0.0,oa,nn))
    F=pd.DataFrame(out,columns=["c90","c365","clife","age_y","since_last_d","auth365","top_share","owner_active","commits_next"],index=a.index); a=pd.concat([a,F],axis=1)
    mech=[]
    for p in a.file_path:
        o=sw=0
        for s in range(max(t-4,0),t): z=fe.get((s,p)); o+=z[0] if z else 0; sw+=z[1] if z else 0
        mech.append(sw/(o+sw) if o+sw>0 else np.nan)
    a["mech_share"]=mech
    a["fid"]=ids
    for tag,v in fx.items(): a["prior_"+tag]=a.fid.map(collections.Counter(f for c_,f in v if ct[tp]<c_<=T)).fillna(0); a["out_"+tag]=a.fid.map(collections.Counter(f for c_,f in v if T<c_<=ct[tn])).fillna(0)
    a["next_loc"]=a.file_path.map(nxt.coding_loc); a["changed"]=(a.next_loc.fillna(0)-a.coding_loc).abs()/a.coding_loc.clip(lower=1); a["any_next"]=a.commits_next>0; a["t"]=t; rows.append(a)
D=pd.concat(rows,ignore_index=True); D["lsize"]=np.log1p(D.coding_loc)
import re
def role(p):
    pl=p.lower()
    if pl.startswith(".github/") or pl.endswith((".yml",".yaml")): return "ci/config"
    if re.search(r"(^|/)(tests?|testing|fuzz\w*|examples?|docs?)(/|$)|(^|/)test_",pl): return "tests/docs"
    if re.search(r"(makefile|cmake|\.am$|\.in$|\.sh$|\.pl$|\.pm$|\.py$)",pl) and not pl.endswith(".py"): return "build/scripts"
    return "source"
D["role"]=D.file_path.map(role)
for c in ["c365","c90","since_last_d","age_y","top_share","risk_churn","risk_stability","pagerank_score","mech_share"]: D[c+"_r"]=D.groupby("t")[c].rank(pct=True)
D["mech_share_f"]=D.mech_share.fillna(0)
print(f"{name}: share of files by role: "+", ".join(f"{k} {100*v:.0f}%" for k,v in D.role.value_counts(normalize=True).items()))
print(f"{name}: {len(D):,} file-intervals over {D.t.nunique()} history-aware snapshots; {D.file_path.nunique():,} files\n")
print("A. ARE THE AXES INDEPENDENT?  rank correlations (pooled within snapshot)")
cols=["c365","since_last_d","age_y","top_share","mech_share","pagerank_score","coding_loc","risk_churn","risk_stability"]; print(D.groupby("t")[cols].rank(pct=True).corr(method="spearman").round(2).to_string())
print("\nB. PREDICTION (this repo only, fit on earlier half of snapshots, test on later half): AUC")
cut=D.t.median(); tr=D[D.t<=cut]; te=D[D.t>cut]
sets={"size":["lsize"],"size+engine churn/stab":["lsize","risk_churn_r","risk_stability_r"],"size+new panel (activity, age, ownership, mechanical share, reach)":["lsize","c365_r","age_y_r","top_share_r","mech_share_f","pagerank_score_r"],"size+recent activity only":["lsize","c365_r"]}
for lab,y,yt,prior in (("later fix (v3c)","out_v3c",None,"prior_v3c"),("later fix (raw)","out_raw",None,"prior_raw"),("any later commit","any_next",None,None)):
    ytr=(tr[y]>0) if y!="any_next" else tr[y]; yte=(te[y]>0) if y!="any_next" else te[y]; line=[]
    for sl,cols_ in sets.items():
        m=LogisticRegression(max_iter=600).fit(tr[cols_],ytr); line.append(f"{sl[:30]} {auc(yte,m.predict_proba(te[cols_])[:,1]):.3f}")
    if prior:
        for sl,cols_ in (("size+prior",["lsize","lp"]),("size+prior+panel",["lsize","lp","c365_r","age_y_r","top_share_r","mech_share_f","pagerank_score_r"])):
            tr2=tr.assign(lp=np.log1p(tr[prior])); te2=te.assign(lp=np.log1p(te[prior])); m=LogisticRegression(max_iter=600).fit(tr2[cols_],ytr); line.append(f"{sl} {auc(yte,m.predict_proba(te2[cols_])[:,1]):.3f}")
    print(f"  {lab:18s} "+"  |  ".join(line))
print("\nB2. WHICH AXIS EARNS IT? AUC for later fix (v3c) adding one thing at a time to size (fit earlier half, test later half)")
for lab,cols_ in (("size only",["lsize"]),("+ recent activity (365-day commits)",["lsize","c365_r"]),("+ dormancy (days since last change)",["lsize","since_last_d_r"]),("+ age",["lsize","age_y_r"]),("+ ownership concentration",["lsize","top_share_r"]),("+ mechanical share",["lsize","mech_share_f"]),("+ reach (PageRank)",["lsize","pagerank_score_r"]),("+ engine churn and stability",["lsize","risk_churn_r","risk_stability_r"]),("+ all five panel axes",["lsize","c365_r","age_y_r","top_share_r","mech_share_f","pagerank_score_r"])):
    m=LogisticRegression(max_iter=600).fit(tr[cols_],tr["out_v3c"]>0); print(f"  {lab:42s} {auc(te['out_v3c']>0,m.predict_proba(te[cols_])[:,1]):.3f}")
print("\nC. WORKLISTS: how often do listed files get a fix / any change next interval, compared with all files that were active that year (c365>0)? pooled over snapshots; 95% interval resampling snapshots")
act=D[D.c365>0]; rng=np.random.default_rng(2982); snaps_=D.t.unique()
def rate(df,col): return float(((df[col]>0) if col.startswith("out_") else df[col]).mean()) if len(df) else np.nan
LISTS={"L1 hot now: top decile of 365-day activity":lambda d:d[d.c365_r>=0.9],
 "L2 hot and concentrated: active, top author >= 60% of commits and (owner inactive or share >= 90%)":lambda d:d[(d.c365>=3)&(d.top_share>=0.6)&((~d.owner_active)|(d.top_share>=0.9))],
 "L3 dormant but depended on: no commit for 2+ years, reach in top decile":lambda d:d[(d.since_last_d>=730)&(d.pagerank_score_r>=0.9)],
 "L4a hot files, mostly organic edits (mechanical share < 25%)":lambda d:d[(d.c365_r>=0.75)&(d.mech_share<0.25)],
 "L4b hot files, mostly mechanical edits (mechanical share >= 50%)":lambda d:d[(d.c365_r>=0.75)&(d.mech_share>=0.5)]}
base_pool={"L3 dormant but depended on: no commit for 2+ years, reach in top decile":D[D.since_last_d>=730]}
for lab,f in LISTS.items():
    L=f(D); base=base_pool.get(lab,act); res=[]
    for col in ("out_v3c","any_next"):
        pt=rate(L,col); b=rate(base,col); bs=[]
        for _ in range(300):
            pick=rng.choice(snaps_,len(snaps_)); Ls=pd.concat([L[L.t==s] for s in pick]); Bs=pd.concat([base[base.t==s] for s in pick]); bs.append(rate(Ls,col)/max(rate(Bs,col),1e-9))
        res.append(f"{'later fix' if col=='out_v3c' else 'any change'} {100*pt:4.1f}% vs {100*b:4.1f}% base (x{pt/max(b,1e-9):.2f} [{np.nanpercentile(bs,2.5):.2f},{np.nanpercentile(bs,97.5):.2f}])")
    print(f"  {lab}\n      n = {len(L):,} file-intervals ({L.t.nunique()} snapshots, median {int(L.groupby('t').size().median())} per snapshot); "+"; ".join(res))
# source-only versions
for lab,f in (("L1s hot now, SOURCE files only (top decile of source files)",lambda d:d[(d.role=="source")&(d.groupby("t").c365.rank(pct=True)>=0.9)]),):
    L=f(D); base=D[(D.role=="source")&(D.c365>0)]; pt=rate(L,"out_v3c"); b=rate(base,"out_v3c"); print(f"  {lab}: later fix {100*pt:.1f}% vs {100*b:.1f}% base (x{pt/max(b,1e-9):.2f}); n={len(L):,}")
# the panel at HEAD
pickle.dump(D,open(f"{SA}/mockup_{name}.pkl","wb")); t=idx[-2]; H=D[D.t==t].copy()
print(f"\nD. THE PANEL AT SNAPSHOT {t} ({pd.to_datetime(ct[t],unit='s').date()}), {len(H)} code files")
print(f"  files active in the last year: {int((H.c365>0).sum())}; dormant 2+ years: {int((H.since_last_d>=730).sum())}; median age {H.age_y.median():.1f} y; median commits last 365 d among active {H[H.c365>0].c365.median():.0f}")
q=lambda d:f"{len(d)}"
print(f"  age x activity map:  old (10y+) & active {q(H[(H.age_y>=10)&(H.c365>0)])} | old & dormant {q(H[(H.age_y>=10)&(H.c365==0)])} | young (<5y) & active {q(H[(H.age_y<5)&(H.c365>0)])} | young & dormant {q(H[(H.age_y<5)&(H.c365==0)])}")
def show(title,d,sort,n=6):
    print(f"  {title}")
    for _,r in d.sort_values(sort,ascending=False).head(n).iterrows(): print(f"    {r.file_path:44s} commits365 {int(r.c365):3d} (90d {int(r.c90):2d})  age {r.age_y:4.1f}y  dormant {int(r.since_last_d):5d}d  top-author {100*r.top_share:3.0f}% {'active' if r.owner_active else 'INACTIVE'}  mechanical {('%3.0f%%'%(100*r.mech_share)) if r.mech_share==r.mech_share else '  - '}  reach pct {100*r.pagerank_score_r:3.0f}")
show("hot files, all roles (top by 365-day commits):",H,"c365")
show("hot SOURCE files:",H[H.role=="source"],"c365")
show("hot and concentrated, source files (knowledge-loss read):",LISTS["L2 hot and concentrated: active, top author >= 60% of commits and (owner inactive or share >= 90%)"](H[H.role=="source"]),"c365")
show("dormant but depended on (source):",LISTS["L3 dormant but depended on: no commit for 2+ years, reach in top decile"](H[H.role=="source"]),"pagerank_score")
show("hot files that are mostly mechanical edits:",LISTS["L4b hot files, mostly mechanical edits (mechanical share >= 50%)"](H),"c365")
