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
rows=[]
for k,evs in F.items():
    c=C[k]
    if not c["agent"] or k not in L["A"]: continue
    size=dict(n_old=sum(e["n_old"] for e in evs),n_new=sum(e["n_new"] for e in evs))
    size["dn"]=size["n_new"]-size["n_old"]; size["adn"]=sum(abs(e["n_new"]-e["n_old"]) for e in evs); size["nev"]=len(evs); size["nfile"]=len({e["file"] for e in evs})
    mod=collections.Counter(re.sub(r"^(gitgalaxy|backend)/","",e["file"]).split("/")[0] for e in evs).most_common(1)[0][0]
    rows.append(dict(k=k,date=c["date"],month=c["date"][:7],mod=mod,size=size,ast=vec(evs),A=L["A"][k]["primary"],B=L["B"].get(k,{}).get("primary"),
                     issues=[i["n"] for i in c["issues"]]))
print("agent-era eligible commits with features:",len(rows))
def groups(rows):
    p={}
    def f(x):
        while p.setdefault(x,x)!=x: p[x]=p[p[x]]; x=p[x]
        return x
    for r in rows:
        f(("c",r["k"]))
        for i in r["issues"]: p[f(("c",r["k"]))]=f(("i",i))
    return np.array([hash(f(("c",r["k"]))) for r in rows])
def X(rows,use_ast,months,mods):
    s=[]
    for r in rows:
        v=[r["size"][a] for a in("n_old","n_new","dn","adn","nev","nfile")]+[float(r["month"]==m) for m in months]+[float(r["mod"]==m) for m in mods]
        if use_ast: v+=[r["ast"][a] for a in AST+["type_l1","consts_added"]]
        s.append(v)
    return np.array(s,float)
def cv_auc(rows,y,g,use_ast,classes,seed=0):
    months=sorted({r["month"] for r in rows}); mods=sorted({r["mod"] for r in rows})
    Xm=X(rows,use_ast,months,mods); P=np.zeros((len(y),len(classes)))
    for tr,te in GroupKFold(5).split(Xm,y,g):
        m=make_pipeline(StandardScaler(),LogisticRegression(C=0.1,max_iter=2000)); m.fit(Xm[tr],y[tr])
        pr=m.predict_proba(Xm[te]); 
        for j,c in enumerate(classes):
            if c in m.classes_: P[te,j]=pr[:,list(m.classes_).index(c)]
    return np.array([roc_auc_score(y==c,P[:,j]) for j,c in enumerate(classes)])
def run(label_key,rows):
    R=[r for r in rows if r[label_key] and r[label_key] not in("unclear",)]
    y=np.array([r[label_key] for r in R]); g=groups(R)
    cnt=collections.Counter(y); classes=[c for c,n in cnt.items() if n>=20]
    base=cv_auc(R,y,g,False,classes); full=cv_auc(R,y,g,True,classes)
    print(f"\n[{label_key}] n={len(R)} classes={dict(cnt)} groups={len(set(g))}")
    for c,b,f in zip(classes,base,full): print(f"  {c:9s} baseline AUC {b:.3f}  +ast {f:.3f}  delta {f-b:+.3f}")
    d=(full-base).mean(); print(f"  macro delta (ast - locked baseline): {d:+.3f}")
    # permutation: shuffle labels within module
    rng=random.Random(1); mods=collections.defaultdict(list)
    for i,r in enumerate(R): mods[r["mod"]].append(i)
    ge=0; N=100
    for _ in range(N):
        yp=y.copy()
        for idx in mods.values():
            sh=list(yp[idx]); rng.shuffle(sh); yp[idx]=sh
        db=(cv_auc(R,yp,g,True,classes)-cv_auc(R,yp,g,False,classes)).mean()
        ge+= db>=d
    print(f"  permutation p (within module, {N} perms): {(ge+1)/(N+1):.3f}")
    # time-blocked: train Sep-Oct, test Nov
    tr=[i for i,r in enumerate(R) if r["month"]<"2026-11"]; te=[i for i,r in enumerate(R) if r["month"]>="2026-11"]
    months=sorted({r["month"] for r in R}); mods_=sorted({r["mod"] for r in R})
    out=[]
    for use in(False,True):
        Xm=X(R,use,months,mods_); m=make_pipeline(StandardScaler(),LogisticRegression(C=0.1,max_iter=2000)).fit(Xm[tr],y[tr]); pr=m.predict_proba(Xm[te])
        out.append([roc_auc_score(y[te]==c,pr[:,list(m.classes_).index(c)]) if c in m.classes_ and 0<(y[te]==c).sum()<len(te) else float("nan") for c in classes])
    print("  time-blocked (train <Nov, test Nov) baseline",np.round(out[0],3),"+ast",np.round(out[1],3),"classes",classes)
run("B",rows); run("A",rows)
