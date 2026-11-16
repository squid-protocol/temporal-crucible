#!/usr/bin/env python3
"""Debt sensor v2 trial: longitudinal item table (original ages), repo yardstick with no leakage, and a back-test of what predicts repayment.
    python tools/sensor/debt_trial.py [repos...]   (default: the nine C projects of the lifecycle study)"""
import sys, re, inspect, subprocess, pathlib, pickle, collections, warnings, multiprocessing
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE.parent))
import debt_lifecycle as DL
YEAR=DL.YEAR; DAY=86400
src=inspect.getsource(DL.track)
src=src.replace('items.append({"r": r, "marker": mk, "start": ct, "author": author, "end": None, "short": len(t) <= 6})','items.append({"r": r, "marker": mk, "start": ct, "author": author, "end": None, "short": len(t) <= 6, "path": p, "text": t})')
src=src.replace("    head_ct = meta[order[-1]][0] if order else 0","    for (_p, _t), _q in alive.items():\n        for _i in _q: items[_i]['cur_path'] = _p\n    head_ct = meta[order[-1]][0] if order else 0")
ns=dict(DL.__dict__); exec(src,ns); track2=ns["track"]
def hist(repo):
    log=DL.git(repo,"log","--no-merges","--reverse","-M","--name-status","--format=@@%ct\t%ae"); fid={}; nid=0; ev=collections.defaultdict(list); ph=collections.defaultdict(list); au=collections.defaultdict(list); cur=None
    for ln in log.splitlines():
        if ln.startswith("@@"): t,a=ln[2:].split("\t"); cur=(int(t),a.lower()); au[cur[1]].append(cur[0])
        elif ln and cur:
            parts=ln.split("\t"); st=parts[0][:1]
            if st in "RC" and len(parts)==3:
                i=fid.get(parts[1]); 
                if i is None: i=nid; nid+=1
                if st=="R": fid.pop(parts[1],None)
                fid[parts[2]]=i; ph[parts[2]].append((cur[0],i)); ev[i].append(cur[0])
            elif st=="A" and len(parts)>=2: i=nid; nid+=1; fid[parts[1]]=i; ph[parts[1]].append((cur[0],i)); ev[i].append(cur[0])
            elif st=="M" and len(parts)>=2:
                i=fid.get(parts[1])
                if i is None: i=nid; nid+=1; fid[parts[1]]=i; ph[parts[1]].append((cur[0],i))
                ev[i].append(cur[0])
            elif st=="D" and len(parts)>=2: fid.pop(parts[1],None)
    return {a:np.array(sorted(v)) for a,v in au.items()}, {i:np.array(sorted(v)) for i,v in ev.items()}, ph
def pid(ph,path,T):
    h=ph.get(path)
    if not h: return None
    lo,hi=0,len(h)
    while lo<hi:
        m=(lo+hi)//2
        if h[m][0]<=T: lo=m+1
        else: hi=m
    return h[lo-1][1] if lo else None
def per_repo(name):
    repo=DL.POOL_DIR/name; _,items,head_ct,_,_,_=track2(name); au,ev,ph=hist(repo)
    for it in items: it["file_deleted"]=bool(it.get("file_deleted",False))
    first=min(i["start"] for i in items); rows=[]; T=first+3*YEAR
    while T<=head_ct-2*YEAR:
        closed=np.sort([(i["end"]-i["start"])/YEAR for i in items if i["end"] is not None and i["end"]<=T and not i["file_deleted"]])
        if len(closed)>=20:
            p90=np.percentile(closed,90); p50=np.percentile(closed,50); acts={}
            for it in items:
                if it["start"]>T or (it["end"] is not None and it["end"]<=T): continue
                end=it["end"]
                if end is not None and end<=T+2*YEAR and it["file_deleted"]: continue         # file deleted: neither repaid nor kept
                y=int(end is not None and end<=T+2*YEAR)
                age=(T-it["start"])/YEAR; fi=pid(ph,it["path"],T) or (pid(ph,it.get("cur_path",""),T) if it.get("cur_path") else None); arr=ev.get(fi)
                c365=int(((arr>T-365*DAY)&(arr<=T)).sum()) if arr is not None else 0
                a=au.get(it["author"]); oa=bool(a is not None and ((a<=T)&(a>T-2*YEAR*1.0)).any())
                rows.append((name,T,it["marker"].upper(),int(it["short"]),len(it["text"]),age,float(np.searchsorted(closed,age)/len(closed)),int(age>p90),p90,c365,int(oa),y))
        T+=0.5*YEAR
    cols=["repo","T","marker","bare","tlen","age","age_pct","fossil","p90","c365","owner_active","repaid2y"]
    # HEAD ledger: open items with original age and current line
    head=[]
    for it in items:
        if it["end"] is None and it.get("cur_path"):
            head.append(dict(repo=name,path=it["cur_path"],marker=it["marker"].upper(),text=it["text"],start=it["start"],author=it["author"],bare=it["short"]))
    return name,pd.DataFrame(rows,columns=cols),head,head_ct,len(items),au,ev,ph
if __name__=="__main__":
    names=sys.argv[1:] or list(DL.CORE+DL.UNSEEN)
    with multiprocessing.Pool(3) as pool: res=pool.map(per_repo,names)
    out={r[0]:dict(df=r[1],head=r[2],head_ct=r[3],items=r[4]) for r in res}; pickle.dump(out,open(HERE/"debt_trial.pkl","wb"))
    for n,v in out.items(): print(n,"items tracked",v["items"],"rows",len(v["df"]),"open at HEAD",len(v["head"]))
