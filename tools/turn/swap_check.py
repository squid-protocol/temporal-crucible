"""For each kind of edit: does the ENGINE see it, as a keyword-family change or as a resolved call-graph change?"""
import sys, json, pickle, collections, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
exec(open("/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad/arch_frame.py").read().split("def frame(name):")[0])
def callee_sets(led,s):
    e=led._snaps[s].view.edges; out=collections.defaultdict(set)
    for u,v in e.tolist(): out[u].add(led.keys[s][v][1])
    return out
def run(name):
    sn=json.load(open(f"{AU.B}/scan_{name}/snapshots.json")); snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{AU.POOL}/{name}"),snaps); A=[W.arrays(x.scan) for x in snaps]; ev=R[name]["events"]
    code=[i for i,e in enumerate(ev) if e["code"]]; kinds=km.predict(Z(name)); cs={}
    res=collections.defaultdict(lambda:collections.Counter())
    for i,k in zip(code,kinds):
        e=ev[i]; s,x=e["s"],e["x"]; l=led.links[s].get(x)
        if l is None: continue
        if s not in cs: cs[s]=(callee_sets(led,s),callee_sets(led,s+1))
        kind=KIND[k]; c=res[kind]; c["n"]+=1
        c["keyword counts changed"]+= bool((A[s][0][x]!=A[s+1][0][l.new]).any()); c["call edges changed (resolved callees)"]+= cs[s][0].get(x,set())!=cs[s][1].get(l.new,set())
        c["complexity changed"]+= A[s][2][x]!=A[s+1][2][l.new]; c["neither keywords nor call edges"]+= (not (A[s][0][x]!=A[s+1][0][l.new]).any()) and cs[s][0].get(x,set())==cs[s][1].get(l.new,set())
    return {k:dict(v) for k,v in res.items()}
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",flush=True)
