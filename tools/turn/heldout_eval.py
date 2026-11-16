import sys, json, pickle, collections, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from pathlib import Path
from structural_fingerprint import ledger as LG
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; SP="/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"
def evaluate(name):
    sn=json.load(open(f"{B}/scan_{name}/snapshots.json")); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); N=len(snaps); res=dict(name=name,N=N,n_end=len(led.keys[-1]))
    commits,labels,truth=pickle.load(open(f"{SP}/truth_{name}.pkl","rb"))
    T=collections.Counter(); ok=collections.Counter(); wrong=collections.Counter(); unl=collections.Counter()
    for s,link in enumerate(led.links):
        if s not in truth or not truth[s]["truth"]: continue
        claims=collections.Counter(b for d,b,j in truth[s]["truth"] if j>=0.85); strong={d:b for d,b,j in truth[s]["truth"] if j>=0.85 and claims[b]==1}
        kA,kB=led.keys[s],led.keys[s+1]; pos=collections.defaultdict(list)
        for i,k in enumerate(kA): pos[k].append(i)
        got={kA[a]:kB[l.new] for a,l in link.items()}
        for d,b in strong.items():
            if len(pos.get(d,[]))!=1: continue
            kind="move" if d[1]==b[1] else "rename"; T[kind]+=1
            if d not in got: unl[kind]+=1
            elif got[d]==b: ok[kind]+=1
            else: wrong[kind]+=1
    res.update(T=dict(T),ok=dict(ok),wrong=dict(wrong),unl=dict(unl))
    # witnesses for accepted verified links
    w=collections.Counter(); samples=[]; conflict=0; both=0
    for s,link in enumerate(led.links):
        for a,l in link.items():
            if l.stage not in LG.VERIFIED_STAGES: continue
            b_ok=l.body is not None and l.body>=0.5; d_ok=l.doc is not None and l.doc>=0.5
            w["both"if b_ok and d_ok else "body only" if b_ok else "comments only"]+=1
            if l.body is not None and l.doc is not None:
                both+=1; conflict+= (b_ok!=d_ok)
            if d_ok and not b_ok and len(samples)<400: samples.append((led.keys[s][a],led.keys[s+1][l.new],l.stage,l.doc,l.body))
    res.update(witness=dict(w),conflict=(conflict,both),samples=samples[:12])
    # chain vs direct over windows
    g=led._snaps[0].git; rows={}
    for win in (4,8,16):
        agree=collections.Counter(); starts=list(range(0,N-win,max(1,(N-win)//4)))[:4]
        for s0 in starts:
            ids0=led.ids[s0]; idsN=led.ids[s0+win]; where={int(x):j for j,x in enumerate(idsN)}
            link=LG.match_pair(led._snaps[s0],led._snaps[s0+win],g)
            for i,x in enumerate(ids0):
                c=where.get(int(x)); d=link[i].new if i in link else None
                agree["same" if c==d and c is not None else "both gone" if c is None and d is None else "chain only" if d is None else "direct only" if c is None else "disagree"]+=1
        rows[win]=dict(agree); 
    res["chain"]=rows
    return res
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=evaluate(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
