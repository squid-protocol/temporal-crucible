import sys, pickle, numpy as np
sys.path.insert(0,".")
exec(open("archetypes.py").read().split("print(\"\\nARCHETYPES")[0].split("best=None")[0])   # reuse loader + features
km=KMeans(6,n_init=5,random_state=2982).fit(train[idx]); lab={n:km.predict(Z(n)) for n in R}
from scipy.stats import spearmanr
raw=np.vstack([feats(R[n]["events"]) for n in disc]); labs=np.concatenate([lab[n] for n in disc]); cm=np.array([raw[labs==c].mean(0) for c in range(6)])
nm={}
for c in range(6):
    m=cm[c]
    nm[c]="swap/rename" if m[11]>0.5 else "big rewrite" if m[3]>1.0 else "signature" if m[1]>0.5 else "shrink" if m[0]<-1 else "grow+logic" if m[0]>1 else "tweak"
assert sorted(nm.values())==sorted(["swap/rename","big rewrite","signature","shrink","grow+logic","tweak"]),nm
names=[nm[c] for c in range(6)]; order=[names.index(x) for x in ["tweak","swap/rename","signature","grow+logic","shrink","big rewrite"]]; print("cluster->kind",nm)
print("HOW PREDICTABLE IS THE QUARTERLY MIX AND VOLUME OF EDITS?  (5 C repos; quarters with >= 30 code edits)")
tv_last=[];tv_long=[];vol=[]
rows={}
for n in R:
    ev=R[n]["events"]; code=[i for i,e in enumerate(ev) if e["code"]]; s=np.array([ev[i]["s"] for i in code]); L=lab[n]
    P=max(s)+1; C=np.zeros((P,6))
    for si,l in zip(s,L): C[si,l]+=1
    tot=C.sum(1); ok=tot>=30; sh=np.where(tot[:,None]>0,C/np.maximum(tot[:,None],1),0)
    tl=[];tg=[];
    for q in range(8,P-1):
        if not (ok[q] and ok[q+1]): continue
        longrun=C[:q+1].sum(0)/C[:q+1].sum(); tl.append(0.5*np.abs(sh[q+1]-sh[q]).sum()); tg.append(0.5*np.abs(sh[q+1]-longrun).sum())
    # per-archetype volume predictability: Spearman of count at q vs q+1 and vs expanding mean
    ac=[spearmanr(C[:-1,k],C[1:,k]).statistic for k in range(6)]; rows[n]=(np.mean(tl),np.mean(tg),ac,np.corrcoef(np.log1p(tot[:-1]),np.log1p(tot[1:]))[0,1])
print(f"  {'repo':8s} {'mix error: last quarter':>24s} {'mix error: long-run mean':>26s}   lag-1 rank correlation of quarterly COUNT by kind: "+"  ".join(f"{names[k][:9]:>9s}" for k in order))
for n,(a,b,ac,tc) in rows.items(): print(f"  {n:8s} {a:24.3f} {b:26.3f}   {'':45s}"+"  ".join(f"{ac[k]:9.2f}" for k in order)+f"   total {tc:.2f}")
