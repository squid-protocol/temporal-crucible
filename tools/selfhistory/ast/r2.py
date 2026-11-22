import json,re,collections,sys,random
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
C={r["sha"][:10]:r for r in json.load(open("commits.json")) if not r["tangled"]}
L=json.load(open("coding/labels.json"))
F=collections.defaultdict(list)
for l in open("features2.jsonl"):
    r=json.loads(l)
    if r["sha"][:10] in C: F[r["sha"][:10]].append(r)
AST=["nodes","loops","max_loop_depth","comps","try","handlers","guards","ifs","in_tests","in_set_lit","in_list_lit","augadd_in_loop","calls","distinct_callees",
     "re_calls","re_compile","rx_nested","rx_alt","rx_len","sorts","env_reads","returns","raises","annotated","args"]
def vec(evs):
    d={a:0.0 for a in AST}; l1=0; newc=0
    for e in evs:
        o,n=e["old"]["f"],e["new"]["f"]
        for a in AST: d[a]+=n.get(a,0)-o.get(a,0)
        t=collections.Counter(e["new"]["types"]); t.subtract(e["old"]["types"]); l1+=sum(abs(v) for v in t.values())
        newc+=len(set(e["new"]["consts"])-set(e["old"]["consts"]))
    d["type_l1"]=l1; d["consts_added"]=newc
    return d
S=json.load(open("structure_rows.json")); SC=S["cols"]; SR=S["rows"]
def svec(k,evs):
    d=[0.0]*len(SC); m=0
    for e in evs:
        fn=e["fn"].split(".")[-1]
        o=SR.get(f"old|{k}|{e.get('old_file') or e['file']}|{fn}"); n=SR.get(f"new|{k}|{e['file']}|{fn}")
        if o and n: m+=1; d=[a+(b-c) for a,b,c in zip(d,n,o)]
    return d,m
rows=[]
for k,evs in F.items():
    c=C[k]
    if not c["agent"] or k not in L["A"]: continue
    size=dict(n_old=sum(e["n_old"] for e in evs),n_new=sum(e["n_new"] for e in evs))
    size["dn"]=size["n_new"]-size["n_old"]; size["adn"]=sum(abs(e["n_new"]-e["n_old"]) for e in evs); size["nev"]=len(evs); size["nfile"]=len({e["file"] for e in evs})
    mod=collections.Counter(re.sub(r"^(gitgalaxy|backend)/","",e["file"]).split("/")[0] for e in evs).most_common(1)[0][0]
    sv,sm=svec(k,evs); rows.append(dict(sv=sv,sm=sm,nev_=len(evs),k=k,date=c["date"],month=c["date"][:7],mod=mod,size=size,ast=vec(evs),A=L["A"][k]["primary"],B=L["B"].get(k,{}).get("primary"),
                     issues=[i["n"] for i in c["issues"]]))

def groups(rows):
    p={}
    def f(x):
        while p.setdefault(x,x)!=x: p[x]=p[p[x]]; x=p[x]
        return x
    for r in rows:
        f(("c",r["k"]))
        for i in r["issues"]: p[f(("c",r["k"]))]=f(("i",i))
    return np.array([hash(f(("c",r["k"]))) for r in rows])

print("commits",len(rows),"with >=1 matched event (both views):",sum(r["sm"]>0 for r in rows),"| events matched share:",round(sum(r["sm"] for r in rows)/sum(r["nev_"] for r in rows),3))
rows=[r for r in rows if r["sm"]>0]
def X2(R,mode,months,mods):
    out=[]
    for r in R:
        v=[r["size"][a] for a in("n_old","n_new","dn","adn","nev","nfile")]+[float(r["month"]==m) for m in months]+[float(r["mod"]==m) for m in mods]
        if mode in("ast","both"): v+=[r["ast"][a] for a in AST+["type_l1","consts_added"]]
        if mode in("struct","both"): v+=r["sv"]
        out.append(v)
    return np.array(out,float)
def cv2(R,y,g,mode,classes):
    months=sorted({r["month"] for r in R}); mods=sorted({r["mod"] for r in R}); Xm=X2(R,mode,months,mods); P=np.zeros((len(y),len(classes)))
    for tr,te in GroupKFold(5).split(Xm,y,g):
        m=make_pipeline(StandardScaler(),LogisticRegression(C=0.1,max_iter=2000)).fit(Xm[tr],y[tr]); pr=m.predict_proba(Xm[te])
        for j,c in enumerate(classes):
            if c in m.classes_: P[te,j]=pr[:,list(m.classes_).index(c)]
    return np.array([roc_auc_score(y==c,P[:,j]) for j,c in enumerate(classes)])
for key in("B","A"):
    R=[r for r in rows if r[key] and r[key]!="unclear"]; y=np.array([r[key] for r in R]); g=groups(R)
    cnt=collections.Counter(y); classes=[c for c,n in cnt.items() if n>=20]
    res={m:cv2(R,y,g,m,classes) for m in("base","ast","struct","both")}
    print(f"\n[{key}] n={len(R)} classes={classes}")
    for m,a in res.items(): print(f"  {m:6s} per-class AUC {np.round(a,3)} macro {a.mean():.3f}  vs base {a.mean()-res['base'].mean():+.3f}")
    print(f"  R2 (ast minus structure, same folds): {res['ast'].mean()-res['struct'].mean():+.3f}")
