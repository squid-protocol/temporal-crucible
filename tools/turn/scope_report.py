import pickle, glob, numpy as np, collections
R=[]
for f in glob.glob("sc_*.pkl"):
    for n,v in pickle.load(open(f,"rb")).items(): R+=v
print(f"{len(R)} sweeps with >= 5 functions swept; resolvable by the engine (old name is a function defined in the repo): {sum(r['resolvable'] for r in R)}")
def agg(key,rs):
    v=[r[key] for r in rs if key in r and not np.isnan(r[key][0]) and not np.isnan(r[key][1])]
    if not v: return None
    P=np.array([x[0] for x in v]); Rc=np.array([x[1] for x in v]); sz=np.array([x[2] for x in v])
    return len(v),np.median(P),np.median(Rc),np.mean(Rc>=0.8),np.mean(P>=0.8),np.median(sz)
print("\nPREDICTING THE SET OF SWEPT FUNCTIONS FROM THE SNAPSHOT BEFORE THE SWEEP (median over sweeps)")
print(f"  {'method':58s} {'sweeps':>6s} {'precision':>9s} {'recall':>7s} {'recall>=0.8':>11s} {'precision>=0.8':>14s} {'median set size':>15s}")
res=[r for r in R if r["resolvable"]]
for lab,key,rs in (("GitGalaxy call graph: callers of the old name   (resolvable)","A",res),("text search: functions that contain the old name   (same sweeps)","B",[r for r in res if "A" in r]),("union of both                                          (same sweeps)","AB",res),("text search on ALL sweeps (incl. names the engine cannot resolve)","B",R)):
    a=agg(key,rs)
    if a: print(f"  {lab:58s} {a[0]:6d} {a[1]:9.2f} {a[2]:7.2f} {100*a[3]:10.0f}% {100*a[4]:13.0f}% {a[5]:15.0f}")
print("\nGitGalaxy callers vs actual swept set, by how big the sweep was")
for lo,hi in ((5,20),(20,60),(60,200),(200,10**6)):
    rs=[r for r in res if lo<=r["n"]<hi and "A" in r]
    if len(rs)>=5: a=agg("A",rs); print(f"  {lo:4d}-{hi if hi<10**6 else 'inf':>4} functions: {a[0]:3d} sweeps, precision {a[1]:.2f}, recall {a[2]:.2f}")
print("\nSCOPE FEATURES OF THE SWEPT SET")
print(f"  files touched: median {np.median([r['files'] for r in R]):.0f} (interquartile {np.percentile([r['files'] for r in R],25):.0f}-{np.percentile([r['files'] for r in R],75):.0f}); the 3 biggest files hold a median {100*np.median([r['top3share'] for r in R]):.0f}% of the swept functions")
print(f"  overlap of predicted and actual file sets (Jaccard, callers of the old name): median {np.median([r['Afiles'] for r in res if 'Afiles' in r]):.2f}")
print(f"  share of swept functions in the top decile by in-degree (hubs): median {100*np.median([r['hub_share'] for r in R]):.0f}% (10% would be chance)")
