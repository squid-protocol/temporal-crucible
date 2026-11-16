import sys, json, pickle, collections, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
from structural_fingerprint import ledger as LG
import what_changes as W, turn_score as T
def run(name):
    sn=T.snaplist(name); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{T.POOL}/{name}"),snaps); N=len(snaps); A=[W.arrays(x.scan) for x in snaps]
    pos=[{int(x):i for i,x in enumerate(a)} for a in led.ids]; f,l=T.spans(led.ids)
    def tup(s,i): return (A[s][1][i],A[s][2][i],A[s][3][i],A[s][0][i].tobytes())
    ages=(1,2,4,8,16); un={a:[] for a in ages}; first=collections.Counter(); at_risk=collections.Counter(); kinds=collections.Counter(); nline=0
    for x in f:
        if f[x]==0 or l[x]==f[x]: continue
        nline+=1; base=tup(f[x],pos[f[x]][x]); changed=None
        for a in range(1,l[x]-f[x]+1):
            t=tup(f[x]+a,pos[f[x]+a][x]); same=(t==base)
            if a in un: un[a].append(same)
            if changed is None:
                at_risk[a]+=1
                if not same:
                    changed=a; first[a]+=1
                    s=f[x]+a; b=pos[f[x]][x]; i=pos[s][x]
                    d_loc=A[s][1][i]!=A[f[x]][1][b]; d_sig=(A[s][0][i]!=A[f[x]][0][b]).any(); d_cx=A[s][2][i]!=A[f[x]][2][b]; d_ar=A[s][3][i]!=A[f[x]][3][b]
                    kinds["+".join(w for fl,w in ((d_loc,"length"),(d_sig,"keywords"),(d_cx,"complexity"),(d_ar,"args")) if fl) or "none"]+=1
    return dict(name=name,N=N,lineages=nline,unchanged={a:(float(np.mean(v)),len(v)) for a,v in un.items() if len(v)>=30},
                hazard={a:first[a]/at_risk[a] for a in range(1,9) if at_risk[a]>=30},kinds=dict(kinds.most_common(6)))
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
