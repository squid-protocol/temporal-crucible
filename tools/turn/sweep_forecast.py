"""Can sweeps be forecast?  size from caller counts, lead time from the new name's first appearance, deprecation precursors, chains, and a name-morphology alert."""
import sys, re, json, pickle, collections, subprocess, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
from scipy.stats import spearmanr
from structural_fingerprint import ledger as LG
import sweeps as S, intent as I
B=S.B; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; SPD=S.SP
def last(n): return n.split(".")[-1].split("::")[-1].rstrip("!")
def related(o,n):
    k=I.intent(o,n); return k!="other / needs context"
def run(name):
    sn=S.json.load(open(f"{B}/scan_{name}/snapshots.json")) if name!="impacket" else None
    if sn is None:
        picks,_=pickle.load(open(SPD+"/rn_truth_impacket.pkl","rb")); sn=[{"commit":p.commit,"db":f"{B}/scan_impacket/.work/snap_{i:03d}_galaxy_master.db"} for i,p in enumerate(picks)]
    snaps=[LG.Snapshot(Path(x["db"]),x["commit"],"") for x in sn]; led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); N=len(snaps)
    ev=pickle.load(open(f"{SPD}/{I.SRC[name]}","rb"))[name]["events"]; migr,_,_=S.detect(ev)
    defined=[collections.Counter(k[1] for k in led.keys[s]) for s in range(N)]
    callers=[]
    for s in range(N):
        e=led._snaps[s].view.edges; c=collections.defaultdict(set)
        for u,v in e.tolist(): c[led.keys[s][v][1]].add(u)
        callers.append({k:len(v) for k,v in c.items()})
    first={}
    for s in range(N):
        for nm in defined[s]: first.setdefault(nm,s)
    R=dict(name=name,migr=len(migr),resolv=0,size=[],lag=[],chain=0,dep=[0,0],cand=[0,0],recall=[0,0])
    pairs={(m["old"],m["new"]):m for m in migr}; newnames={last(m["new"]) for m in migr}; oldnames={last(m["old"]) for m in migr}
    for m in migr:
        o,nw,s=last(m["old"]),last(m["new"]),m["s"]
        if o in defined[s] and nw in first and nw in defined[min(s+1,N-1)]:
            R["resolv"]+=1; R["size"].append((m["n"],callers[s].get(o,0))); R["lag"].append(s+1-first[nw])
        if o in newnames or nw in oldnames: R["chain"]+=1
    # deprecation precursor for the 25 largest migrations
    for m in sorted(migr,key=lambda x:-x["n"])[:25]:
        s=m["s"]; a=sn[max(s-4,0)]["commit"]; b=sn[s+1]["commit"]
        try: r=subprocess.run(["git","-C",f"{POOL}/{name}","log","-i","--grep=deprecat","-S"+last(m["old"]),"--format=%s","-n","3",f"{a}..{b}"],capture_output=True,text=True,errors="replace",timeout=45).stdout.strip()
        except Exception: continue
        R["dep"][1]+=1; R["dep"][0]+=bool(r)
    # name-morphology alert: new function name introduced at q; old function existing at q-1 with >=10 callers and a morphological relation; migration within next 4 quarters?
    hits=set((last(m["old"]),last(m["new"])) for m in migr if m["n"]>=10); migq=collections.defaultdict(list)
    for m in migr: migq[(last(m["old"]),last(m["new"]))].append(m["s"])
    flagged=set()
    for q in range(1,N-1):
        newf=[nm for nm in defined[q] if first.get(nm)==q]
        if not newf: continue
        olds=[o for o,c in callers[q-1].items() if c>=10 and defined[q-1].get(o)]
        for nw in newf:
            for o in olds:
                if o!=nw and related(o,nw) and (o[:4]==nw[:4] or nw.endswith(o) or o in nw or I.norm(o)==I.norm(nw)):
                    R["cand"][1]+=1; ok=any(q-1<=s<=q+3 for s in migq.get((o,nw),())); R["cand"][0]+=ok; flagged.add((o,nw))
    for (o,nw) in hits:
        if any(o in defined[s] and first.get(nw,N)<=s+1 for s in migq[(o,nw)]): R["recall"][1]+=1; R["recall"][0]+= (o,nw) in flagged
    return R
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
