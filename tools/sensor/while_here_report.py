import pickle, pathlib, numpy as np
HERE=pathlib.Path(__file__).resolve().parent; res=pickle.load(open(HERE/"while_here.pkl","rb"))
R={n:np.array([r[:5] for r in rows],float) for n,rows,_ in res if rows}; C={n:np.array([hash(r[5]) for r in rows]) for n,rows,_ in res if rows}
RULES=[("every open marker in a touched file",lambda a:np.ones(len(a),bool)),("change in the file >= 20 lines",lambda a:a[:,0]>=20),("change >= 50 lines",lambda a:a[:,0]>=50),("change >= 100 lines",lambda a:a[:,0]>=100),("change >= 200 lines",lambda a:a[:,0]>=200),
 ("change >= 50 lines, fossil markers only",lambda a:(a[:,0]>=50)&(a[:,1]==1)),("change >= 100 lines, fossil markers only",lambda a:(a[:,0]>=100)&(a[:,1]==1)),("change >= 50 lines, the editor wrote the marker",lambda a:(a[:,0]>=50)&(a[:,2]==1)),("change >= 50 lines, file holds 3+ open markers",lambda a:(a[:,0]>=50)&(a[:,4]>=3))]
print(f"{sum(len(v) for v in R.values()):,} (commit, file, open marker) observations in {len(R)} repos: "+", ".join(f"{n} {len(v):,}" for n,v in R.items()))
tot=np.vstack(list(R.values())); allrep=tot[:,3].sum(); print(f"markers repaid in the commit that touched their file: {int(allrep):,} of {len(tot):,} observations = {100*allrep/len(tot):.2f}%\n")
print("A. HOW OFTEN IS A MARKER REPAID, BY SIZE OF THE CHANGE TO ITS FILE (per marker per commit)")
for lo,hi in ((0,5),(5,20),(20,50),(50,100),(100,300),(300,10**9)):
    m=(tot[:,0]>=lo)&(tot[:,0]<hi); print(f"  {lo:4d}-{hi if hi<10**9 else 'inf':>4}: {int(m.sum()):9,d} observations   repaid {100*tot[m,3].mean():6.2f}%")
print("\nB. TRIGGER RULES REPLAYED OVER HISTORY (pooled): precision = surfaced markers that were actually repaid in that commit; recall = share of all repaid markers that the rule had surfaced")
print(f"  {'rule':50s} {'surfaced':>10s} {'per fired commit':>16s} {'precision':>9s} {'lift':>6s} {'recall':>7s}")
base=allrep/len(tot)
for lab,f in RULES:
    m=np.concatenate([f(a) for a in R.values()]); s=int(m.sum()); rep=tot[m,3].sum(); fired=sum(len(set(C[n][f(a)])) for n,a in R.items())
    print(f"  {lab:50s} {s:10,d} {s/max(fired,1):16.1f} {100*rep/s:8.2f}% {rep/s/base:5.1f}x {100*rep/allrep:6.1f}%")
print("\nC. THE SAME RULES, REPO BY REPO (precision of 'change >= 50 lines' vs 'every marker')")
for n,a in R.items():
    m=a[:,0]>=50; print(f"  {n:10s} every marker {100*a[:,3].mean():5.2f}%   change >= 50 lines {100*a[m,3].mean():5.2f}%   + fossil only {100*a[m&(a[:,1]==1),3].mean() if (m&(a[:,1]==1)).sum() else float('nan'):5.2f}%   markers surfaced per fired commit (>=50 lines) {m.sum()/max(len(set(C[n][m])),1):.1f}")
