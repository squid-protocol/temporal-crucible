import sys, json, pickle, collections, datetime as dt, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
from pathlib import Path
from structural_fingerprint import ledger as LG
import what_changes as W
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; FAM=W.FAM
def run(name):
    f=Path(f"{B}/scan_{name}/snapshots.json")
    if f.exists(): sn=json.load(open(f))
    else:                                              # impacket: snapshot list was kept in a pickle
        picks,_o=pickle.load(open("/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad/rn_truth_impacket.pkl","rb"))
        sn=[{"label":p.label,"date":p.date,"commit":p.commit,"db":f"{B}/scan_impacket/.work/snap_{i:03d}_galaxy_master.db"} for i,p in enumerate(picks)]
    snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); A=[W.arrays(x.scan) for x in snaps]; N=len(snaps)
    yr=[int(str(x["date"])[:4]) for x in sn]
    Bs=np.zeros(len(FAM)); Ds=np.zeros(len(FAM)); Dr=np.zeros(len(FAM)); sizeB=sizeD=sizeDr=0.0; dd=np.zeros(len(FAM))
    for s,link in enumerate(led.links):
        sa,la,_,_,_=A[s]; sb,lb,_,_,_=A[s+1]; used={l.new for l in link.values()}
        born=[y for y in range(len(led.keys[s+1])) if y not in used]; dead=[x for x in range(len(led.keys[s])) if x not in link]
        Bs+=sb[born].sum(0); Ds+=sa[dead].sum(0)
        if link:
            a=np.fromiter(link.keys(),int); b=np.array([l.new for l in link.values()]); Dr+=(sb[b]-sa[a]).sum(0); sizeDr+=(lb[b]-la[a]).sum()
        if link and la[a].sum()>0 and lb[b].sum()>0: dd+=1000.0*(sb[b].sum(0)/lb[b].sum()-sa[a].sum(0)/la[a].sum())   # density change inside survivors (per kLOC)
        sizeB+=lb[born].sum(); sizeD+=la[dead].sum()
    # yearly density curves (whole population), mean over that year's snapshots
    dens=collections.defaultdict(list)
    for s in range(N):
        k=A[s][1].sum()/1000.0
        if k>0 and len(A[s][1])>=30: dens[yr[s]].append(A[s][0].sum(0)/k)
    years=sorted(dens); curve=np.array([np.mean(dens[y],0) for y in years])
    slope=np.array([np.polyfit(years,curve[:,i],1)[0] if len(years)>=4 else np.nan for i in range(len(FAM))])
    return dict(name=name,N=N,B=Bs,D=Ds,Dr=Dr,years=years,curve=curve,slope=slope,size=(sizeB,sizeD,sizeDr),n_end=len(led.keys[-1]),dd=dd,pop=(A[-1][0].sum(0)/(A[-1][1].sum()/1000.0))-(A[0][0].sum(0)/max(A[0][1].sum()/1000.0,1e-9)) if A[0][1].sum()>0 else None)
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
