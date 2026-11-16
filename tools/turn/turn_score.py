"""Per-repo scorer for the TURN identity / growth / settling-in / derived-function / print hypotheses, with bootstrap intervals (over snapshot pairs or lineages; seed 2982)."""
import sys, json, pickle, collections, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
from structural_fingerprint import ledger as LG
import what_changes as W
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; BOOT=1000
def snaplist(name):
    f=Path(f"{B}/scan_{name}/snapshots.json")
    if f.exists(): return json.load(open(f))
    picks,_o=pickle.load(open("/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad/rn_truth_impacket.pkl","rb"))
    return [{"label":p.label,"date":p.date,"commit":p.commit,"db":f"{B}/scan_impacket/.work/snap_{i:03d}_galaxy_master.db"} for i,p in enumerate(picks)]
def ids_from(led,keep):
    ids=[np.arange(len(led.keys[0]),dtype=np.int64)]; nxt=len(ids[0])
    for s,link in enumerate(led.links):
        cur=np.full(len(led.keys[s+1]),-1,dtype=np.int64)
        for x,l in link.items():
            if keep(l): cur[l.new]=ids[s][x]
        for y in np.flatnonzero(cur<0): cur[y]=nxt; nxt+=1
        ids.append(cur)
    return ids
def spans(ids):
    f={}; l={}
    for s,a in enumerate(ids):
        for x in a.tolist(): f.setdefault(x,s); l[x]=s
    return f,l
def ci(vals,stat,rng,n):
    """percentile interval of stat over resamples of an index set of size n."""
    out=[]
    for _ in range(BOOT):
        i=rng.integers(0,n,n); out.append(stat(i))
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
def score(name,lang):
    rng=np.random.default_rng(2982); sn=snaplist(name); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); N=len(snaps); R=dict(name=name,lang=lang,N=N)
    yrs=[int(str(x["date"])[:4]) for x in sn]; R["years"]=yrs[-1]-yrs[0]
    ids=led.ids; nids=ids_from(led,lambda l:l.stage=="identity"); P=N-1
    pop=np.array([len(led.keys[s]) for s in range(P)],float); ok=pop>=50
    dl=np.array([len(led.deaths(s)) for s in range(P)],float); dn=np.array([len(set(nids[s].tolist())-set(nids[s+1].tolist())) for s in range(P)],float)
    mv=np.array([sum(1 for l in led.links[s].values() if l.stage!="identity") for s in range(P)],float)
    # ID-1
    r1=lambda i: dn[i].sum()/max(dl[i].sum(),1)-1; R["ID1_overcount"]=(r1(np.arange(P)),)+ci(None,r1,rng,P)
    f,l=spans(ids); fn,ln=spans(nids)
    life=np.array([l[x]-f[x] for x in f if f[x]>0]); lifen=np.array([ln[x]-fn[x] for x in fn if fn[x]>0])
    R["ID1_life_ratio"]=(float(np.median(life)/max(np.median(lifen),1e-9)) if len(life) and len(lifen) else None,)
    # ID-2: top 10% of pairs hold what share of moves+renames
    k=max(1,round(0.1*P)); t10=lambda i: (np.sort(mv[i])[::-1][:k].sum()/max(mv[i].sum(),1)); R["ID2_top10_share"]=(t10(np.arange(P)),)+ci(None,t10,rng,P)
    # births / deaths by cause
    bc=collections.Counter(); dc=collections.Counter(); per_b=[]; per_d=[]
    for s in range(P):
        d_,b_=LG.classify_unlinked(led,s); cb=collections.Counter(b_.values()); cd=collections.Counter(d_.values()); per_b.append(cb); per_d.append(cd)
    def share(cs,keys,i): 
        a=sum(sum(cs[j][k] for k in keys) for j in i); t=sum(sum(cs[j].values()) for j in i); return a/max(t,1)
    ix=np.arange(P)
    R["GRO1_births_new_file"]=(share(per_b,["new_file"],ix),)+ci(None,lambda i:share(per_b,["new_file"],i),rng,P)
    R["GRO2_deaths_file_removed"]=(share(per_d,["file_removed"],ix),)+ci(None,lambda i:share(per_d,["file_removed"],i),rng,P)
    R["DER1_births_derived"]=(share(per_b,["split_or_extracted","merge_result"],ix),)+ci(None,lambda i:share(per_b,["split_or_extracted","merge_result"],i),rng,P)
    R["DER1_deaths_derived"]=(share(per_d,["split","merged"],ix),)+ci(None,lambda i:share(per_d,["split","merged"],i),rng,P)
    # GRO-3
    rate=lambda i: float(np.median((dl[ok]/pop[ok])[i])) if ok.sum() else float("nan")
    okn=int(ok.sum()); R["GRO3_median_death_rate"]=(rate(np.arange(okn)),)+ci(None,rate,rng,okn) if okn>=8 else (float("nan"),)
    t10d=lambda i:(np.sort(dl[i])[::-1][:k].sum()/max(dl[i].sum(),1)); R["GRO3_top10_death_share"]=(t10d(ix),)+ci(None,t10d,rng,P)
    # SET-1, SET-3 on lineages
    A=[W.arrays(x.scan) for x in snaps]
    pos=[{int(x):i for i,x in enumerate(a)} for a in ids]
    def tup(s,i): return (A[s][1][i],A[s][2][i],A[s][3][i],A[s][0][i].tobytes())
    cand=[x for x in f if f[x]>0 and l[x]>=f[x]+4]
    same=np.array([tup(f[x]+4,pos[f[x]+4][x])==tup(f[x],pos[f[x]][x]) for x in cand]) if cand else np.array([])
    R["SET1_unchanged_4q"]=(float(same.mean()),)+ci(None,lambda i:same[i].mean(),rng,len(same)) if len(same)>=30 else (float("nan"),)
    indeg=[]
    for s in range(N):
        e=led._snaps[s].view.edges; c=np.zeros(len(led.keys[s]))
        if len(e): np.add.at(c,e[:,1],1)
        indeg.append(c)
    orph=[x for x in cand if indeg[f[x]][pos[f[x]][x]]==0]
    still=np.array([indeg[f[x]+4][pos[f[x]+4][x]]==0 for x in orph]) if orph else np.array([])
    R["SET3_orphans_stay_uncalled"]=(float(still.mean()),)+ci(None,lambda i:still[i].mean(),rng,len(still)) if len(still)>=30 else (float("nan"),)
    # SET-4
    def persist(idl,s):
        n_=len(idl[s]); top=set(idl[s][np.argsort(-indeg[s])[:max(5,n_//100)]].tolist()); big=set(idl[s+4][np.argsort(-indeg[s+4])[:max(5,len(idl[s+4])//20)]].tolist()); return len(top&big),len(top)
    pr=[(persist(ids,s),persist(nids,s)) for s in range(0,N-4,2)]
    if pr:
        L=np.array([[a[0],a[1],b[0],b[1]] for a,b in pr],float); st=lambda i:(L[i,0].sum()/max(L[i,1].sum(),1),L[i,2].sum()/max(L[i,3].sum(),1))
        R["SET4_hub_persist_lineage"]=(st(np.arange(len(pr)))[0],)+ci(None,lambda i:st(i)[0],rng,len(pr)); R["SET4_hub_persist_naive"]=(st(np.arange(len(pr)))[1],)
        R["SET4_gap"]=(st(np.arange(len(pr)))[0]-st(np.arange(len(pr)))[1],)+ci(None,lambda i:st(i)[0]-st(i)[1],rng,len(pr))
    # KW-1: print density slope per year (yearly curves)
    FAM=W.FAM; ip=FAM.index("state_print_hits"); by=collections.defaultdict(list)
    for s in range(N):
        kl=A[s][1].sum()/1000.0
        if kl>0 and len(A[s][1])>=30: by[yrs[s]].append(A[s][0][:,ip].sum()/kl)
    ys=sorted(by); 
    if len(ys)>=6:
        yv=np.array([np.mean(by[y]) for y in ys]); sl=lambda i:np.polyfit(np.array(ys)[i],yv[i],1)[0] if len(set(np.array(ys)[i]))>=3 else np.nan
        R["KW1_print_slope_per_year"]=(float(np.polyfit(ys,yv,1)[0]),)+ci(None,sl,rng,len(ys))
    return R
if __name__=="__main__":
    out={}; LANGS=json.loads(sys.argv[2])
    for n in sys.argv[3:]:
        out[n]=score(n,LANGS[n]); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
