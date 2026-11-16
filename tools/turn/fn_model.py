import pickle, glob, numpy as np, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import roc_auc_score
F={}
for f in glob.glob("fn_*.pkl"): F.update(pickle.load(open(f,"rb")))
TAGS=("raw","v3c","reg"); L=lambda x:np.log1p(x)
def X(R,g,spec):
    b=11+6*TAGS.index(g); c=[L(R[:,3]),L(R[:,10])]
    if spec in("file","fn+file","naive+file","kinds"): c.append(L(R[:,b]))
    if spec in("fn","fn+file","kinds"): c+= [L(R[:,b+1]),L(R[:,b+2])]
    if spec=="naive+file": c+= [L(R[:,b+3]),L(R[:,b+4])]
    if spec=="kinds": c+=[L(R[:,4+k]) for k in range(6)]
    return np.column_stack(c)
def fit(tr,te,g,spec):
    oc=11+6*TAGS.index(g)+5; m=PoissonRegressor(alpha=1e-3,max_iter=400).fit(X(tr,g,spec),tr[:,oc]/tr[:,2],sample_weight=tr[:,2]); return m.predict(X(te,g,spec))*te[:,2],m
def met(R,mu,g):
    y=R[:,11+6*TAGS.index(g)+5]
    if not((y>0).any() and (y==0).any()): return np.nan,np.nan
    o=np.argsort(-(mu/R[:,2])); cs=np.cumsum(R[o,2]); k=cs<=0.2*cs[-1]; return roc_auc_score(y>0,mu),y[o][k].sum()/y.sum()
rng=np.random.default_rng(2982); SP=["churn","file","fn","fn+file","naive+file","kinds"]
for g in TAGS:
    print(f"\n=== label: {g}   (AUC | recall at a 20%-of-lines budget; later half of each repo; function-quarters)")
    print(f"  {'repo':8s} {'later fixes':>11s} {'churn+age':>12s} {'+file':>12s} {'+function':>12s} {'+fn+file':>12s} {'+fn naive id':>13s} {'+edit kinds':>12s}")
    D=collections.defaultdict(list) if False else {}
    allD={"fn_over_file":[],"identity":[],"kinds":[]}
    for n,R in F.items():
        cut=np.median(R[:,1]); tr=R[R[:,1]<=cut]; te=R[R[:,1]>cut]; res={}
        for s in SP: mu,_=fit(tr,te,g,s); res[s]=(mu,)+met(te,mu,g)
        ids=np.unique(te[:,0]); byf={f:np.flatnonzero(te[:,0]==f) for f in ids}
        def d(a,b):
            v=[]
            for _ in range(100):
                idx=np.concatenate([byf[f] for f in rng.choice(ids,len(ids))]); v.append(met(te[idx],res[a][0][idx],g)[0]-met(te[idx],res[b][0][idx],g)[0])
            return np.nanpercentile(v,2.5),np.nanpercentile(v,97.5)
        c1=d("fn+file","file"); c2=d("fn+file","naive+file"); c3=d("kinds","fn+file")
        nf=int(te[:,11+6*TAGS.index(g)+5].sum())
        print(f"  {n:8s} {nf:11d} "+" ".join(f"{res[s][1]:.3f}|{res[s][2]:.2f}".rjust(12 if s!='naive+file' else 13) for s in ["churn","file","fn","fn+file","naive+file","kinds"]))
        print(f"  {'':8s} {'':11s} AUC gain: function over file {res['fn+file'][1]-res['file'][1]:+.3f} [{c1[0]:+.3f},{c1[1]:+.3f}]   lineage over naive identity {res['fn+file'][1]-res['naive+file'][1]:+.3f} [{c2[0]:+.3f},{c2[1]:+.3f}]   edit kinds {res['kinds'][1]-res['fn+file'][1]:+.3f} [{c3[0]:+.3f},{c3[1]:+.3f}]")
        allD["fn_over_file"].append(res['fn+file'][1]-res['file'][1]); allD["identity"].append(res['fn+file'][1]-res['naive+file'][1]); allD["kinds"].append(res['kinds'][1]-res['fn+file'][1])
    print("  mean AUC gain over repos: "+", ".join(f"{k} {np.mean(v):+.3f}" for k,v in allD.items()))
print("\nFUNCTION PRIOR-FIX TERMS (rate ratio per log unit, model +function, all function-quarters; v3c)")
import collections
for n,R in F.items():
    _,m=fit(R,R,"v3c","fn"); c=np.exp(m.coef_); print(f"  {n:8s} churn {c[0]:.2f} age {c[1]:.2f} | fixes last 4 quarters {c[2]:.2f}, fixes ever {c[3]:.2f}")
