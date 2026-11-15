import pickle, glob, collections, numpy as np, random
R={}
for f in glob.glob("audit_*.pkl"): R.update(pickle.load(open(f,"rb")))
dom=lambda e: e["sw"]>=2 and e["sw"]/max(e["n"],1)>=0.5
print("SHARE OF LABELLED FIX COMMITS THAT ARE SWEEPS (>= 2 of the commit's changed call names are the names swept that quarter and they are >= half of all its changed names)")
print(f"  {'repo':11s} {'fix commits':>11s} {'all classes':>12s}  other-fix  regression  extrinsic  latent    touches any sweep name")
tot=collections.Counter(); totd=collections.Counter()
for n,r in R.items():
    ev=r["events"]; by=collections.defaultdict(list)
    for e in ev: by[e["cls"]].append(e)
    cell=lambda c: f"{100*np.mean([dom(e) for e in by[c]]):5.1f}% ({len(by[c])})" if by.get(c) else "     -"
    print(f"  {n:11s} {len(ev):11d} {100*np.mean([dom(e) for e in ev]):11.1f}%  {cell('other-fix'):>14s} {cell('regression'):>14s} {cell('extrinsic'):>14s} {cell('latent'):>12s}   {100*np.mean([e['sw']>=1 for e in ev]):.0f}%")
    for e in ev: tot[e["cls"]]+=1; totd[e["cls"]]+=dom(e)
print("  ALL        "+"  ".join(f"{c}: {totd[c]}/{tot[c]} = {100*totd[c]/tot[c]:.1f}%" for c in tot))
print("\nMASS: share of the fix-file outcome (commit x files touched) that comes from sweep commits")
for n,r in R.items():
    ev=r["events"]; w=sum(e["nfiles"] for e in ev); wd=sum(e["nfiles"] for e in ev if dom(e)); print(f"  {n:11s} {100*wd/w:5.1f}% of {w:,} commit-file pairs")
random.seed(2982); allev=[(n,e) for n,r in R.items() for e in r["events"] if dom(e)]
print("\nSAMPLES of labelled fixes that are sweeps:")
for n,e in random.sample(allev,min(16,len(allev))): print(f"  {n:10s} [{e['cls']}] {e['subject']}  <- {','.join(e['swnames'][:4])}")
