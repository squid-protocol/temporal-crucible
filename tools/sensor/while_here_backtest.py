#!/usr/bin/env python3
"""'While you are here' prompt: replay it over a repo's whole history. For every commit that touches a file with open debt markers, which markers would a given
trigger rule have surfaced, and how many were actually repaid in that commit?    python tools/sensor/while_here_backtest.py [repos...]"""
import sys, pathlib, bisect, collections, subprocess, pickle, warnings, multiprocessing
import numpy as np
warnings.filterwarnings("ignore")
HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parent))
import debt_trial as DT, debt_lifecycle as DL
YEAR=DL.YEAR
def run(name):
    repo=DL.POOL_DIR/name; _,items,head_ct,_,_,_=DT.track2(name); au,ev,ph=DT.hist(repo)
    for it in items: it["fid"]=DT.pid(ph,it["path"],it["start"])
    items=[i for i in items if i["fid"] is not None]; by=collections.defaultdict(list)
    for it in items: by[it["fid"]].append(it)
    closed=sorted((i["end"],(i["end"]-i["start"])/YEAR) for i in items if i["end"] is not None and not i.get("file_deleted"))
    ends=[c[0] for c in closed]; grid=[]; t=closed[0][0] if closed else 0
    while t<=head_ct: k=bisect.bisect_right(ends,t); grid.append((t,float(np.percentile([c[1] for c in closed[:k]],90)) if k>=20 else np.nan)); t+=0.5*YEAR
    gt=[g[0] for g in grid]
    log=DL.git(repo,"log","--no-merges","--no-renames","--numstat","--format=@@%H\t%ct\t%ae"); rows=[]; cur=None; nrep_all=sum(1 for i in items if i.get("end_sha") and not i.get("file_deleted"))
    for ln in log.splitlines():
        if ln.startswith("@@"): h,ct,ae=ln[2:].split("\t"); cur=(h,int(ct),ae.lower()); continue
        parts=ln.split("\t")
        if cur is None or len(parts)!=3 or not parts[0].isdigit() or not parts[1].isdigit(): continue
        path=parts[2]
        if not DL.keep(path): continue
        fid=DT.pid(ph,path,cur[1]); lst=by.get(fid)
        if not lst: continue
        n=int(parts[0])+int(parts[1]); g=bisect.bisect_right(gt,cur[1])-1; p90=grid[g][1] if g>=0 else np.nan
        for it in lst:
            if it["start"]<cur[1] and (it["end"] is None or it["end"]>=cur[1]):
                age=(cur[1]-it["start"])/YEAR
                rows.append((n,int(age>p90) if p90==p90 else 0,int(it["author"]==cur[2]),int(it.get("end_sha")==cur[0]),len(lst),cur[0]))
    return name,rows,nrep_all
if __name__=="__main__":
    names=sys.argv[1:] or ["libgit2","libxml2","redis","curl","harfbuzz","openssl"]
    with multiprocessing.Pool(3) as pool: res=pool.map(run,names)
    pickle.dump(res,open(HERE/"while_here.pkl","wb")); print({r[0]:len(r[1]) for r in res})
