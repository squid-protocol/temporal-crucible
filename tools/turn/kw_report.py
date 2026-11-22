import sys, pickle, numpy as np
sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
import what_changes as W
FAM=W.FAM; SP="/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"
R={}
for f in sys.argv[1:]: R.update(pickle.load(open(f,"rb")))
names=list(R)
WATCH=["state_print_hits","def_safety","state_safety_neg","state_pointers","state_cast_hits","state_bailout_hits","struct_branch","state_flux","def_test","arch_io"]
print("TREND per year (density per kLOC; slope of the yearly curve; + rising / - falling) for the families you named")
print(f"  {'family':20s}"+"".join(f"{n:>22s}" for n in names))
for f in WATCH:
    i=FAM.index(f); row=[]
    for n in names:
        r=R[n]; c=r["curve"][:,i]; row.append(f"{c[0]:5.1f}->{c[-1]:5.1f} ({r['slope'][i]:+.2f}/yr)")
    print(f"  {f:20s}"+"".join(f"{x:>22s}" for x in row))
print("\nWHAT DRIVES EACH FAMILY'S NET CHANGE: share of total movement from births / deaths / survivors rewritten (retrofit)")
print("  retrofit R = |survivor drift| / (births + deaths + |drift|)   [R near 0: only turnover; R high: old code is being rewritten]")
print(f"  {'family':20s}"+"".join(f"{n:>22s}" for n in names))
for f in WATCH:
    i=FAM.index(f); row=[]
    for n in names:
        r=R[n]; b,d,dr=r["B"][i],r["D"][i],r["Dr"][i]; tot=b+d+abs(dr)
        row.append(f"R={abs(dr)/tot:.2f} drift{'+' if dr>=0 else '-'}" if tot>0 else "-")
    print(f"  {f:20s}"+"".join(f"{x:>22s}" for x in row))
print("\nFAMILIES MOST OFTEN REWRITTEN IN PLACE (highest retrofit, families with >= 200 total hits)")
for n in names:
    r=R[n]; rows=[]
    for i,f in enumerate(FAM):
        b,d,dr=r["B"][i],r["D"][i],r["Dr"][i]; tot=b+d+abs(dr)
        if tot>=200: rows.append((abs(dr)/tot,f,dr))
    rows.sort(reverse=True); print(f"  {n:12s} "+", ".join(f"{f} {x:.2f}{'+' if dr>=0 else '-'}" for x,f,dr in rows[:5]))
print("\nSIZE: net lines added through births / lost through deaths / net change inside survivors")
for n in names: b,d,dr=R[n]["size"]; print(f"  {n:12s} births +{b:,.0f}  deaths -{d:,.0f}  survivors {dr:+,.0f}  -> survivors are {100*abs(dr)/(b+d+abs(dr)):.0f}% of line movement")
print("\nDIRECTION CONSISTENCY across repos (how many of the repos have this family rising / falling)")
for f in WATCH:
    i=FAM.index(f); sl=[R[n]['slope'][i] for n in names]; print(f"  {f:20s} rising in {sum(s>0 for s in sl)}, falling in {sum(s<0 for s in sl)} of {len(sl)}")
print("\nTURNOVER OR REWRITING? Change of density (per kLOC) over the repo's life: whole repo vs inside the surviving code")
print("  'inside survivors' is the summed density change of functions that persisted pair to pair; if it matches the whole-repo change, old code was rewritten; if near zero, the shift came from births and deaths")
print(f"  {'family':20s}"+"".join(f"{n:>24s}" for n in names))
for f in WATCH:
    i=FAM.index(f); row=[]
    for n in names:
        r=R[n]; pop=r["pop"]; 
        row.append(f"repo {pop[i]:+6.1f} | surv {r['dd'][i]:+6.1f}" if pop is not None else "-")
    print(f"  {f:20s}"+"".join(f"{x:>24s}" for x in row))
