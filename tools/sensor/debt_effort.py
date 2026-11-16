#!/usr/bin/env python3
"""Effort proxy for a debt marker: what predicts the SIZE of the change that repaid it?  (target = lines added + deleted in that file by the repaying commit)
    python tools/sensor/debt_effort.py [repos...]"""
import sys, re, pathlib, pickle, collections, subprocess, warnings, multiprocessing
import numpy as np
warnings.filterwarnings("ignore")
HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parent))
import debt_trial as DT, debt_lifecycle as DL
src2=DT.src.replace('file_deleted=p in e["deleted"])','file_deleted=p in e["deleted"], end_path=p)')
ns=dict(DL.__dict__); exec(src2,ns); track3=ns["track"]
HINT=re.compile(r"\b(rewrite|refactor|redesign|rework|support|implement|handle|all|every|proper(ly)?|better|generic|api|portable|abstract)\b",re.I)
def one(name):
    repo=DL.POOL_DIR/name; _,items,head_ct,_,_,_=track3(name); au,ev,ph=DT.hist(repo); rows=[]
    rep=[i for i in items if i["end"] is not None and not i.get("file_deleted") and i.get("end_sha") and i.get("end_path")]
    bycommit=collections.Counter((i["end_sha"],i["end_path"]) for i in rep)
    for it in rep:
        ns_=DL.git(repo,"show","--numstat","--format=","--no-color",it["end_sha"],"--",it["end_path"]).strip().split("\n")[0].split("\t")
        if len(ns_)<3 or not ns_[0].isdigit() or not ns_[1].isdigit(): continue
        churn=int(ns_[0])+int(ns_[1])
        fs=len(DL.git(repo,"show",f"{it['end_sha']}^:{it['end_path']}").splitlines())
        fi=DT.pid(ph,it["end_path"],it["end"]); arr=ev.get(fi); c365=int(((arr>it["end"]-365*86400)&(arr<=it["end"])).sum()) if arr is not None else 0
        rows.append((name,churn,fs,c365,len(it["text"]),int(bool(HINT.search(it["text"]))),bycommit[(it["end_sha"],it["end_path"])],(it["end"]-it["start"])/DL.YEAR,it["marker"].upper()))
    return rows
if __name__=="__main__":
    names=sys.argv[1:] or ["curl","libgit2","libxml2","redis","openssl","harfbuzz"]
    with multiprocessing.Pool(3) as pool: res=pool.map(one,names)
    pickle.dump(res,open(HERE/"debt_effort.pkl","wb")); print({n:len(r) for n,r in zip(names,res)})
