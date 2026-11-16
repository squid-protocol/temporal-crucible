"""Combined worklists from the saved mock-up frames: activity x reach, among source files. python tools/sensor/activity_combined.py curl libxml2 libgit2"""
import sys, pickle, numpy as np, pandas as pd
SA="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/surface_area"; rng=np.random.default_rng(2982)
for n in sys.argv[1:]:
    D=pickle.load(open(f"{SA}/mockup_{n}.pkl","rb")); S=D[(D.role=="source")&(D.c365>0)].copy(); S["act"]=S.groupby("t").c365.rank(pct=True); S["reach"]=S.groupby("t").pagerank_score.rank(pct=True)
    base=(S.out_v3c>0).mean(); snaps=S.t.unique(); print(f"\n{n}: {len(S):,} active source file-intervals, base later-fix rate {100*base:.1f}%")
    for lab,m in (("hot only (top decile of activity)",S.act>=0.9),("reach only (top decile of reach)",S.reach>=0.9),("hot AND high reach (activity top decile, reach top quartile)",(S.act>=0.9)&(S.reach>=0.75)),("hot but low reach (activity top decile, reach bottom half)",(S.act>=0.9)&(S.reach<0.5)),("high reach but quiet (reach top decile, activity bottom half)",(S.reach>=0.9)&(S.act<0.5))):
        L=S[m]; 
        if len(L)<30: print(f"  {lab:62s} n={len(L)} (too few)"); continue
        r=(L.out_v3c>0).mean(); bs=[]
        for _ in range(300):
            pick=rng.choice(snaps,len(snaps)); Ls=pd.concat([L[L.t==s] for s in pick]); Bs=pd.concat([S[S.t==s] for s in pick]); bs.append((Ls.out_v3c>0).mean()/max((Bs.out_v3c>0).mean(),1e-9))
        print(f"  {lab:62s} n={len(L):5d}  later fix {100*r:4.1f}%  x{r/base:.2f} [{np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}]")
