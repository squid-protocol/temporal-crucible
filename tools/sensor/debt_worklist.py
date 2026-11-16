#!/usr/bin/env python3
"""Debt worklist v2: ranked, located, explained, with stable IDs, an empirical effort band, a cluster count and triage status.
    python tools/sensor/debt_worklist.py REPO [--top N] [--set ID STATUS [--note TEXT]]
States (our own vocabulary, mapped to SARIF 2.1.0 suppressions on export): open; watching (someone is on it; ranked last; SARIF underReview);
keep (kept on purpose; listed apart; SARIF accepted); not_debt (not a debt marker; hidden; SARIF rejected); done (claimed resolved; hidden; reopened if the marker is found again).
    --sarif OUT writes the open markers as SARIF with stable IDs as partialFingerprints and the sensor's fields as properties."""
import sys, argparse, hashlib, json, pathlib, collections, datetime, pickle, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
warnings.filterwarnings("ignore")
HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parent))
import debt_trial as DT, debt_lifecycle as DL
YEAR=DL.YEAR; DAY=86400; STATUS=("watching","keep","not_debt","done"); SARIF_STATE={"watching":"underReview","keep":"accepted","not_debt":"rejected"}
BAND=[(500,"S","usual repayment in files this size: ~24 lines changed (90th pct 137)"),(2000,"M","usual repayment: ~34 lines (90th pct 368)"),(10**9,"L","usual repayment: ~56 lines (90th pct 1,301)")]
def marker_id(path,marker,text,k): return hashlib.sha1(f"{path}|{marker}|{text}|{k}".encode()).hexdigest()[:10]
def fit_model():
    D=pickle.load(open(HERE/"debt_trial.pkl","rb")); D=pd.concat([v["df"] for v in D.values() if len(v["df"])],ignore_index=True)
    D["lage"]=np.log1p(D.age); D["lc365"]=np.log1p(D.c365); D["ltlen"]=np.log1p(D.tlen); D["xxx"]=(D.marker=="XXX").astype(int); D["fixme"]=D.marker.isin(["FIXME","HACK"]).astype(int)
    cols=["lage","age_pct","xxx","fixme","bare","lc365","owner_active","ltlen"]; mu,sd=D[cols].mean(),D[cols].std(); m=LogisticRegression(max_iter=800).fit((D[cols]-mu)/sd,D.repaid2y); return m,cols,mu,sd
def build(repo):
    r=DL.POOL_DIR/repo; _,items,head_ct,_,_,_=DT.track2(repo); au,ev,ph=DT.hist(r)
    closed=np.sort([(i["end"]-i["start"])/YEAR for i in items if i["end"] is not None and not i.get("file_deleted")]); p90=float(np.percentile(closed,90))
    occ=collections.Counter(); rows=[]
    for it in sorted(items,key=lambda i:i["start"]):
        k=occ[(it["path"],it["text"])]; occ[(it["path"],it["text"])]+=1
        if it["end"] is None and it.get("cur_path"): rows.append(dict(id=marker_id(it["path"],it["marker"].upper(),it["text"],k),path=it["cur_path"],marker=it["marker"].upper(),text=it["text"],start=it["start"],author=it["author"],bare=int(it["short"])))
    H=pd.DataFrame(rows); act=set(a for a,arr in au.items() if ((arr<=head_ct)&(arr>head_ct-2*YEAR)).any())
    H["age"]=(head_ct-H.start)/YEAR; H["age_pct"]=np.searchsorted(closed,H.age)/len(closed); H["fossil"]=H.age>p90
    c365={}; 
    for p in H.path.unique():
        fi=DT.pid(ph,p,head_ct); arr=ev.get(fi); c365[p]=int(((arr>head_ct-365*DAY)&(arr<=head_ct)).sum()) if arr is not None else 0
    H["c365"]=H.path.map(c365); H["owner_active"]=H.author.isin(act).astype(int)
    fl={p:len(DL.git(r,"show",f"HEAD:{p}").splitlines()) for p in H.path.unique()}; H["flines"]=H.path.map(fl); H["band"]=H.flines.map(lambda n:next(b for lim,b,_ in BAND if n<lim)); H["others"]=H.groupby("path").id.transform("count")-1
    m,cols,mu,sd=fit_model(); X=pd.DataFrame({"lage":np.log1p(H.age),"age_pct":H.age_pct,"xxx":(H.marker=="XXX").astype(int),"fixme":H.marker.isin(["FIXME","HACK"]).astype(int),"bare":H.bare,"lc365":np.log1p(H.c365),"owner_active":H.owner_active,"ltlen":np.log1p(H.text.str.len())})
    H["stuck"]=1-m.predict_proba(((X[cols]-mu)/sd))[:,1]; H["score"]=H.stuck*(1+np.log1p(H.c365))
    lc={}; 
    def line(p,t,k):
        if p not in lc:
            lc[p]=collections.defaultdict(list)
            for i,ln in enumerate(DL.git(r,"show",f"HEAD:{p}").splitlines(),1):
                d=DL.debt_line(ln)
                if d: lc[p][d[1]].append(i)
        L=lc[p].get(t,[]); return L[k] if k<len(L) else None
    seen=collections.Counter(); ls=[]
    for p,t in zip(H.path,H.text): ls.append(line(p,t,seen[(p,t)])); seen[(p,t)]+=1
    H["line"]=ls; return H,p90,head_ct
def triage_path(repo): return HERE/"triage"/f"{repo}.json"
def load_triage(repo):
    f=triage_path(repo); return json.loads(f.read_text()) if f.exists() else {}
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("repo"); ap.add_argument("--top",type=int,default=8); ap.add_argument("--set",nargs=2,metavar=("ID","STATUS")); ap.add_argument("--note",default=""); ap.add_argument("--sarif",metavar="OUT")
    a=ap.parse_args(); H,p90,head_ct=build(a.repo); T=load_triage(a.repo)
    if a.set:
        i,st=a.set
        if st not in STATUS: sys.exit(f"status must be one of {STATUS}")
        if i not in set(H.id) and st!="done": sys.exit(f"unknown id {i}")
        T[i]=dict(status=st,note=a.note,date=str(datetime.date.today()),text=(H[H.id==i].text.iloc[0] if i in set(H.id) else "")); triage_path(a.repo).write_text(json.dumps(T,indent=1)); print(f"{i} -> {st}")
    reopened=[i for i,v in T.items() if v["status"]=="done" and i in set(H.id)]
    for i in reopened: T[i]=dict(T[i],status="reopened",note=(T[i].get("note","")+" [re-detected]").strip()); triage_path(a.repo).write_text(json.dumps(T,indent=1))
    st=H.id.map(lambda i:T.get(i,{}).get("status","open")); H["status"]=st
    vis=H[~H.status.isin(["not_debt","done","keep"])].copy(); vis["rank"]=vis.score-(vis.status=="watching")*10
    print(f"{a.repo}: {len(H)} open markers; fossils (older than this repo's 90th-percentile repayment age, {p90:.1f} y): {100*H.fossil.mean():.0f}%; not debt: {int((H.status=='not_debt').sum())}; kept on purpose: {int((H.status=='keep').sum())}; reopened: {len(reopened)}")
    TR=pickle.load(open(HERE/"debt_trial.pkl","rb")).get(a.repo)
    if TR is not None and len(TR["df"])>200:
        g=TR["df"]; f=g[g.fossil==1]; nf=g[g.fossil==0]; hot=f[f.c365>=10]; q=f[f.c365==0]; oa=f[f.owner_active==1]; oi=f[f.owner_active==0]
        print(f"  track record in THIS repo (open debt at half-year dates, repaid within 2 years): fossils {100*f.repaid2y.mean():.1f}% vs other debt {100*nf.repaid2y.mean():.1f}%"+(f"; fossils in hot files (10+ commits a year) {100*hot.repaid2y.mean():.1f}% vs quiet files {100*q.repaid2y.mean():.1f}%" if len(hot)>30 and len(q)>30 else "")+(f"; owner active {100*oa.repaid2y.mean():.1f}% vs gone {100*oi.repaid2y.mean():.1f}%" if len(oa)>30 and len(oi)>30 else ""))
    print(f"  {'id':10s} {'where':44s} {'marker':6s} {'age':>6s} {'stuck':>5s} {'file commits':>12s} {'owner':>8s} {'usual size':>10s} {'+others':>7s}  status")
    for _,r in vis.sort_values("rank",ascending=False).head(a.top).iterrows():
        w=f"{r.path}:{int(r.line) if r.line==r.line and r.line is not None else '?'}"; print(f"  {r.id:10s} {w[:44]:44s} {r.marker:6s} {r.age:5.1f}y {100*r.stuck:4.0f}% {int(r.c365):12d} {'active' if r.owner_active else 'gone':>8s} {r.band:>10s} {int(r.others):7d}  {r.status}{' FOSSIL' if r.fossil else ''} | {r.text[:48]}")
    if (H.status=="keep").any():
        print("  kept on purpose:"); 
        for _,r in H[H.status=="keep"].iterrows(): print(f"    {r.id} {r.path} | {r.text[:60]} ({T[r.id].get('note','')})")
    if a.sarif:
        res=[]
        for _,r in H[~H.status.isin(["not_debt","done"])].iterrows():
            x={"ruleId":"debt/open-marker","level":"note","message":{"text":f"{r.marker} open for {r.age:.1f} years: {r.text[:120]}"},
               "locations":[{"physicalLocation":{"artifactLocation":{"uri":r.path},"region":{"startLine":int(r.line) if r.line==r.line and r.line is not None else 1}}}],
               "partialFingerprints":{"debtMarkerId/v1":r.id},
               "properties":{"age_years":round(float(r.age),2),"stuck_probability":round(float(r.stuck),3),"fossil":bool(r.fossil),"owner_active":bool(r.owner_active),"file_commits_365d":int(r.c365),"usual_repayment_size_band":r.band,"other_open_markers_in_file":int(r.others),"line_resolved":bool(r.line==r.line and r.line is not None)}}
            if r.status in SARIF_STATE or r.status=="keep": x["suppressions"]=[{"kind":"external","status":SARIF_STATE.get(r.status,"accepted"),"justification":T.get(r.id,{}).get("note","")}]
            res.append(x)
        doc={"$schema":"https://json.schemastore.org/sarif-2.1.0.json","version":"2.1.0","runs":[{"tool":{"driver":{"name":"debt-ledger (sensor-overhaul prototype)","rules":[{"id":"debt/open-marker","shortDescription":{"text":"Open self-admitted debt marker"}}]}},"results":res}]}
        pathlib.Path(a.sarif).write_text(json.dumps(doc,indent=1)); print(f"SARIF written: {len(res)} results -> {a.sarif}")
