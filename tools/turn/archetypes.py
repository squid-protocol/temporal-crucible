"""Change archetypes: cluster in-place edits to surviving C functions; do clusters found on discovery repos reappear on held-out repos?"""
import sys, pickle, numpy as np
sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
import sweeps as S
from sklearn.cluster import KMeans
from scipy.optimize import linear_sum_assignment
NAMES=["length change","signature changed","if-conditions +/-","goto +/-","casts +/-","pointer syntax +/-","return +/-","calls +/-","#if +/-","names added","names removed","in a sweep"]
def feats(ev):
    _,_,ins=S.detect(ev); X=[]; keep=[]
    for i,e in enumerate(ev):
        if not e["code"]: continue
        d=e["d"]; g=lambda k:d.get(k,0)
        X.append([np.sign(e["dloc"])*np.log1p(abs(e["dloc"])),float(e["sig"]),g("if_statement"),g("goto_statement"),g("cast_expression"),g("pointer_expression")+g("pointer_declarator"),g("return_statement"),g("call_expression"),g("preproc_if")+g("preproc_ifdef"),np.log1p(sum(e["add"].values())),np.log1p(sum(e["rem"].values())),float(i in ins)]); keep.append(i)
    return np.array(X,float)
def squash(X): return np.sign(X)*np.log1p(np.abs(X))
R={}; 
for f in ("ts_edits_c2.pkl","ts_edits_ho_c.pkl"): R.update(pickle.load(open(f,"rb")))
disc=["curl","redis","libgit2"]; held=["expat","libxml2"]; F={n:squash(feats(R[n]["events"])) for n in R}
mu=np.vstack([F[n] for n in disc]).mean(0); sd=np.vstack([F[n] for n in disc]).std(0)+1e-9
Z=lambda n:(F[n]-mu)/sd; rng=np.random.default_rng(2982)
train=np.vstack([Z(n) for n in disc]); idx=rng.choice(len(train),min(60000,len(train)),replace=False)
best=None
for k in (4,5,6,7,8):
    km=KMeans(k,n_init=5,random_state=2982).fit(train[idx]); 
    # stability: fit on each held-out repo separately and match centroids
    ds=[]
    for n in held:
        kh=KMeans(k,n_init=5,random_state=2982).fit(Z(n)); D=((km.cluster_centers_[:,None,:]-kh.cluster_centers_[None,:,:])**2).sum(2)**0.5; r,c=linear_sum_assignment(D); ds.append(D[r,c].mean())
    print(f"k={k}: inertia/n {km.inertia_/len(idx):.2f}; mean distance of each cluster to its best match in an independently clustered held-out repo: "+", ".join(f"{n} {d:.2f}" for n,d in zip(held,ds)))
    if k==6: best=km
km=best; print("\nARCHETYPES (k=6 fitted on curl+redis+libgit2); means in raw units (before scaling), share of code edits per repo")
lab={n:km.predict(Z(n)) for n in R}
raw=np.vstack([feats(R[n]["events"]) for n in disc]); labs=np.concatenate([lab[n] for n in disc])
print(f"  {'':3s}"+"".join(f"{n[:11]:>12s}" for n in NAMES)+"   "+"  ".join(f"{n:>8s}" for n in list(R)))
for c in range(6):
    m=raw[labs==c].mean(0); print(f"  C{c} "+"".join(f"{v:12.2f}" for v in m)+"   "+"  ".join(f"{100*np.mean(lab[n]==c):7.1f}%" for n in R))
# anomaly: distance to nearest centroid, per repo, tail share
print("\nANOMALY: share of edits farther from every archetype than the 99th percentile of the discovery repos")
dist=lambda n:np.min(((Z(n)[:,None,:]-km.cluster_centers_[None,:,:])**2).sum(2),axis=1)**0.5
thr=np.percentile(np.concatenate([dist(n) for n in disc]),99)
print("  "+"  ".join(f"{n} {100*np.mean(dist(n)>thr):.1f}%" for n in R))
