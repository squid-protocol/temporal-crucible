import sys, bisect, random, multiprocessing
from collections import Counter
sys.path.insert(0,'tools'); import chg_eval as C
random.seed(1)
out=Counter(); per=Counter(); ex=[]
for r in C.REPOS:
    ev,_=C.fix_events(r); ev=random.sample(ev,min(600,len(ev)))
    with multiprocessing.get_context("fork").Pool(8) as p: hits=[h for hs in p.imap_unordered(C.map_fix,ev,chunksize=8) for h in hs]
    snaps,perS,_T=C.transitions(r); cts=[s["ct"] for s in snaps]; names=[set(d) for d in perS]
    files=[{k[0] for k in d} for d in perS]
    for (_,path,nm,ct,k) in hits:
        j=bisect.bisect_right(cts,ct)-1
        if j<0: continue
        def has(i): return (path,nm) in names[i] or (path,nm.split('::')[-1]) in names[i]
        if has(j): c="match"
        elif j+1<len(names) and has(j+1): c="born after snapshot (in next)"
        elif path not in files[j]: c="file not in snapshot"
        else:
            c="name not in engine file"
            if len(ex)<12 and random.random()<.2: ex.append((r,path,nm))
        out[c]+=1; per[(r,c)]+=1
tot=sum(out.values()); print({k:f"{v/tot:.1%}" for k,v in out.items()}, tot)
for r in C.REPOS:
    t=sum(v for (rr,_),v in per.items() if rr==r); print(r,{c:f"{v/t:.0%}" for (rr,c),v in per.items() if rr==r})
print(ex)
