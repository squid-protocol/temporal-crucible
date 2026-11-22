import sys, json, pickle, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
from pathlib import Path
from structural_fingerprint import ledger as LG
import what_changes as W, sweeps as S
FAM=W.FAM; B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"
HIGH=["state_memory_alloc","def_cleanup","state_print_hits","state_safety_neg","arch_io"]; LOW=["struct_branch","state_pointers","struct_args","struct_macros","def_safety"]
ev=pickle.load(open(sys.argv[1],"rb")); rng=np.random.default_rng(2982)
for name,r in ev.items():
    sn=json.load(open(f"{B}/scan_{name}/snapshots.json")); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); A=[W.arrays(x.scan) for x in snaps]
    _,_,ins=S.detect(r["events"]); sweep={(r["events"][i]["s"],r["events"][i]["x"]) for i in ins}
    n=len(FAM); Bs=np.zeros(n); Ds=np.zeros(n); Dall=np.zeros(n); Dno=np.zeros(n); per=[]
    for s,link in enumerate(led.links):
        sa=A[s][0]; sb=A[s+1][0]; used={l.new for l in link.values()}
        born=[y for y in range(len(led.keys[s+1])) if y not in used]; dead=[x for x in range(len(led.keys[s])) if x not in link]
        Bs+=sb[born].sum(0); Ds+=sa[dead].sum(0); d=np.zeros(n); dn=np.zeros(n)
        for x,l in link.items():
            dd=sb[l.new]-sa[x]; d+=dd
            if (s,x) not in sweep: dn+=dd
        Dall+=d; Dno+=dn
    def R(dr): return np.abs(dr)/np.maximum(Bs+Ds+np.abs(dr),1e-9)
    Ra,Rn=R(Dall),R(Dno); hi=[FAM.index(f) for f in HIGH]; lo=[FAM.index(f) for f in LOW]
    gap_a=Ra[hi].mean()-Ra[lo].mean(); gap_n=Rn[hi].mean()-Rn[lo].mean()
    print(f"\n== {name}: sweep edits removed = {len(sweep):,} of {sum(e['code'] for e in r['events']):,} code edits")
    print(f"   H6 gap (retrofit share, predicted-high minus predicted-low): all edits {gap_a:+.3f}  | sweeps removed {gap_n:+.3f}  | shrinks by {100*(1-gap_n/gap_a):.0f}%" if gap_a else "   gap 0")
    print("   per family retrofit R, all -> sweeps removed:  "+"; ".join(f"{f.replace('state_','').replace('struct_','').replace('def_','')} {Ra[FAM.index(f)]:.2f}->{Rn[FAM.index(f)]:.2f}" for f in HIGH+LOW))
