import pickle, glob, collections, numpy as np
R={}
for f in glob.glob("cat_*.pkl"): R.update(pickle.load(open(f,"rb")))
ev=[dict(e,repo=n) for n,r in R.items() for e in r["events"]]
cl=["latent","regression","extrinsic","other-fix"]; by={c:[e for e in ev if e["cls"]==c] for c in cl}
print("FIX COMMITS ANALYSED (C repos: curl, libxml2, libgit2, redis):",{c:len(v) for c,v in by.items()})
rng=np.random.default_rng(2982)
def share(v,f): return np.mean([bool(f(e)) for e in v]) if v else float("nan")
def lift(c,f):
    a=by[c]; b=by["other-fix"]
    if len(a)<30: return None
    pa,pb=share(a,f),share(b,f); bs=[]
    for _ in range(400):
        sa=[a[i] for i in rng.integers(0,len(a),len(a))]; sb=[b[i] for i in rng.integers(0,len(b),len(b))]
        x,y=share(sa,f),share(sb,f); bs.append(x/y if y>0 else np.nan)
    return pa,pb,np.nanpercentile(bs,2.5),np.nanpercentile(bs,97.5)
T=[("adds a null check",lambda e:e["null_check"]>0),("adds a bounds/size/limit check",lambda e:e["bounds_check"]>0),("adds any new if-condition",lambda e:e["guard_added"]>0),
   ("removes an if-condition",lambda e:e["guard_removed"]>0),("adds a goto (cleanup path)",lambda e:e["goto_d"]>0),("adds a return",lambda e:e["ret_d"]>0),
   ("adds a cast",lambda e:e["cast_d"]>0),("changes pointer syntax",lambda e:e["ptr_d"]!=0),("replaces an unsafe call with a safer one",lambda e:e["unsafe_removed"]>0 and e["safer_added"]>0),
   ("adds a free / release call",lambda e:e["free_added"]>0),("removes a free / release call",lambda e:e["free_removed"]>0),("adds an allocation",lambda e:e["alloc_added"]>0)]
print(f"\nSHARE OF FIX COMMITS THAT DO X, by class   (lift = class share / other-fix share, 95% CI)")
print(f"  {'':44s}"+"".join(f"{c:>12s}" for c in cl)+"   lift of latent / regression / extrinsic")
for lab,f in T:
    row=f"  {lab:44s}"+"".join(f"{100*share(by[c],f):11.1f}%" for c in cl); L=[]
    for c in ("latent","regression","extrinsic"):
        l=lift(c,f); L.append(f"{l[0]/l[1]:.2f} [{l[2]:.2f},{l[3]:.2f}]" if l and l[1]>0 else "-")
    print(row+"   "+" / ".join(L))
print("\nSIZE OF THE WORK (median; lines added+deleted, files touched, new conditions)")
for c in cl:
    v=by[c]; print(f"  {c:10s} lines {np.median([e['lines'] for e in v]):5.0f} (90th pct {np.percentile([e['lines'] for e in v],90):.0f})   files {np.median([e['files'] for e in v]):.0f}   new if-conditions {np.mean([e['guard_added'] for e in v]):.2f} mean")
print("\nCALLS MOST OVER-REPRESENTED IN EACH CLASS vs other-fix (added | removed), commits with the call, min 8 commits")
for c in ("latent","regression","extrinsic"):
    for side in ("add","rem"):
        a=collections.Counter(); b=collections.Counter()
        for e in by[c]: a.update(set(e[side]))
        for e in by["other-fix"]: b.update(set(e[side]))
        sc=[(( (a[k]/len(by[c]))/((b[k]+1)/len(by["other-fix"])) ),k,a[k]) for k in a if a[k]>=8]; sc.sort(reverse=True)
        print(f"  {c:10s} {side}: "+", ".join(f"{k} (x{r:.0f}, {n})" for r,k,n in sc[:8]))
