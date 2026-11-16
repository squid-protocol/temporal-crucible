"""Would GitGalaxy have outlined the scope of a sweep?  Predict the set of swept functions from the snapshot BEFORE the sweep:
A = callers of the old name in the engine's call graph, B = functions containing the old name by text search (git grep), compared with the functions that were actually swept."""
import sys, re, json, pickle, bisect, collections, subprocess, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
from structural_fingerprint import ledger as LG
import sweeps as S, intent as I
B=S.B; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; SPD=S.SP
last=lambda n:n.split(".")[-1].split("::")[-1].rstrip("!")
def prf(pred,act):
    tp=len(pred&act); return (tp/len(pred) if pred else float("nan")), (tp/len(act) if act else float("nan"))
def run(name):
    if name=="impacket":
        picks,_=pickle.load(open(SPD+"/rn_truth_impacket.pkl","rb")); sn=[{"commit":p.commit,"db":f"{B}/scan_impacket/.work/snap_{i:03d}_galaxy_master.db"} for i,p in enumerate(picks)]
    else: sn=json.load(open(f"{B}/scan_{name}/snapshots.json"))
    snaps=[LG.Snapshot(Path(x["db"]),x["commit"],"") for x in sn]; repo=f"{POOL}/{name}"; led=LG.build_ledger(Path(repo),snaps); N=len(snaps)
    ev=pickle.load(open(f"{SPD}/{I.SRC[name]}","rb"))[name]["events"]; migr,_,_=S.detect(ev)
    pos={}
    def idx_of(e):
        s=e["s"]
        if "x" in e: return e["x"]
        if s not in pos: pos[s]={int(v):i for i,v in enumerate(led.ids[s])}
        return pos[s].get(e["id"])
    swept=collections.defaultdict(set)                      # (s,old,new) -> set of function indices at s
    for e in ev:
        if not e["code"]: continue
        for m_key in (): pass
    bym=collections.defaultdict(list)
    for m in migr: bym[m["s"]].append(m)
    for e in ev:
        if not e["code"] or e["s"] not in bym: continue
        for m in bym[e["s"]]:
            if m["old"] in e["rem"] and m["new"] in e["add"]:
                i=idx_of(e)
                if i is not None: swept[(m["s"],m["old"],m["new"])].add(i)
    cache={}
    def snapdata(s):
        if s in cache: return cache[s]
        edges=led._snaps[s].view.edges; call=collections.defaultdict(set); indeg=collections.Counter()
        for u,v in edges.tolist(): call[led.keys[s][v][1]].add(u); indeg[v]+=1
        rng=collections.defaultdict(list)
        for i,(k,mt) in enumerate(zip(led.keys[s],led._snaps[s].meta)):
            if mt and mt[0]>=1: rng[k[0]].append((mt[0],mt[0]+max(mt[1],1)-1,i))
        for p in rng: rng[p].sort()
        cache[s]=(call,indeg,rng); return cache[s]
    out=[]
    for m in migr:
        s=m["s"]; act=swept.get((s,m["old"],m["new"]),set()); o=last(m["old"])
        if len(act)<5: continue
        call,indeg,rng=snapdata(s); resolvable=o in call or o in {k[1] for k in led.keys[s]}
        A=set(call.get(o,set())) if resolvable else None
        Bset=None
        if re.fullmatch(r"[A-Za-z_]\w*",o):
            try:
                r=subprocess.run(["git","-C",repo,"grep","-n","-w","-F","-e",o,sn[s]["commit"]],capture_output=True,text=True,errors="replace",timeout=60).stdout
            except Exception: r=""
            Bset=set(); pre=sn[s]["commit"]+":"
            for ln in r.splitlines():
                parts=ln.split(":",3)
                if len(parts)<3 or not parts[2].isdigit(): continue
                p=parts[1]; line=int(parts[2]); L=rng.get(p)
                if not L: continue
                j=bisect.bisect_right([a for a,_,_ in L],line)-1
                if j>=0 and L[j][0]<=line<=L[j][1]: Bset.add(L[j][2])
        files=lambda X:{led.keys[s][i][0] for i in X}
        rec=dict(name=name,s=s,old=m["old"],new=m["new"],n=len(act),resolvable=resolvable,files=len(files(act)))
        if A is not None: rec["A"]=prf(A,act)+(len(A),); rec["Afiles"]=(len(files(A)&files(act))/max(len(files(A)|files(act)),1))
        if Bset is not None: rec["B"]=prf(Bset,act)+(len(Bset),)
        if A is not None and Bset is not None: rec["AB"]=prf(A|Bset,act)+(len(A|Bset),)
        top=sorted(collections.Counter(led.keys[s][i][0] for i in act).values(),reverse=True); rec["top3share"]=sum(top[:3])/len(act)
        deg=np.array([indeg[i] for i in act]); allv=np.array([indeg[i] for i in range(len(led.keys[s]))]); rec["hub_share"]=float(np.mean(deg>=np.percentile(allv,90)))
        out.append(rec)
    return out
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",len(out[n]),flush=True)
