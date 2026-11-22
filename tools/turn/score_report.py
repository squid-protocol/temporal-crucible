import pickle, glob, numpy as np
R={}
for f in glob.glob("score_*.pkl"): R.update(pickle.load(open(f,"rb")))
DISC=["curl","redis","libgit2","impacket","sqlmap","ripgrep","tigerbeetle"]; HELD=["expat","libxml2","scapy","sphinx","commons-io","prometheus"]
# (key, label, direction, bound, formatter, c_only)
H=[("ID1_overcount","ID-1 path-name identity overcounts deaths",">",0.40,"{:.0%}",False),
   ("ID1_life_ratio","ID-1 median lifetime longer under lineage (x)",">",1.30,"{:.2f}",False),
   ("ID2_top10_share","ID-2 top 10% of quarters hold moves/renames",">",0.60,"{:.0%}",False),
   ("GRO1_births_new_file","GRO-1 births in new files",">",0.60,"{:.0%}",False),
   ("GRO2_deaths_file_removed","GRO-2 deaths = whole file removed",">",0.45,"{:.0%}",False),
   ("GRO3_median_death_rate","GRO-3 median quarterly death rate",  "<",0.005,"{:.2%}",False),
   ("GRO3_top10_death_share","GRO-3 top 10% of quarters hold deaths",">",0.60,"{:.0%}",False),
   ("SET1_unchanged_4q","SET-1 unchanged after 4 quarters",">",0.80,"{:.0%}",False),
   ("SET3_orphans_stay_uncalled","SET-3 uncalled newborns still uncalled",">",0.95,"{:.0%}",False),
   ("SET4_hub_persist_lineage","SET-4 hubs persist (lineage)",">",0.90,"{:.0%}",False),
   ("SET4_gap","SET-4 lineage minus naive persistence",">",0.03,"{:.1%}",False),
   ("DER1_births_derived","DER-1 births from split/merge/extract",  "<",0.02,"{:.1%}",False),
   ("DER1_deaths_derived","DER-1 deaths by split/merge/inline",  "<",0.05,"{:.1%}",False),
   ("KW1_print_slope_per_year","KW-1 print density slope per year (C)","<",0.0,"{:+.2f}",True)]
def verdict(v,dirn,b):
    p=v[0]
    if p is None or (isinstance(p,float) and np.isnan(p)): return "-"
    if len(v)<3 or np.isnan(v[1]): return "?"
    lo,hi=v[1],v[2]
    if dirn==">": return "S" if lo>b else ("C" if hi<b else "n")
    return "S" if hi<b else ("C" if lo>b else "n")
def fmt(v,f):
    if v is None or np.isnan(v[0]): return "n/a"
    s=f.format(v[0]); 
    if len(v)==3 and not np.isnan(v[1]): s+=f" [{f.format(v[1])},{f.format(v[2])}]"
    return s
for grp,label in ((DISC,"DISCOVERY repos (bounds were set from these)"),(HELD,"HELD-OUT repos (never used to set a bound)")):
    print(f"\n=== {label}: S = interval wholly on the predicted side of the bound, n = not detected, C = interval wholly on the other side, ? = no interval, - = not applicable")
    for key,lab,d,b,f,conly in H:
        cells=[]; tally={"S":0,"n":0,"C":0,"?":0,"-":0}
        for n in grp:
            r=R.get(n)
            if r is None or key not in r or (conly and r["lang"]!="c"): continue
            v=verdict(r[key],d,b); tally[v]+=1; cells.append(f"{n} {v}")
        t=" ".join(f"{k}{c}" for k,c in tally.items() if c and k!="-")
        print(f"  {lab:50s} bound {d}{('{:g}'.format(b)):>6s}   {t:14s}  "+"; ".join(f"{n}:{fmt(R[n][key],f)}" for n in grp if n in R and key in R[n] and not (conly and R[n]['lang']!='c'))[:260])
