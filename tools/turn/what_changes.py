import sys, pickle, collections, numpy as np
sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
import cascade2 as C
from structural_fingerprint.scan_io import load_scan
SP=C.SP; refP=C.refP; FAM=list(refP.signal_columns)
def arrays(db):
    sc=load_scan(db,FAM); ft,v,nrm,nb,keys,vec,st=C.prep(db); m=sc.loc>=3
    names=np.array(sc.func_name)[m]; ok=len(names)==len(ft.name) and all(names[i]==ft.name[i] for i in range(min(50,len(names))))
    sig=sc.signals[m][v.rows]; loc=sc.loc[m][v.rows]; cx=sc.complexity[m][v.rows]; ar=sc.args[m][v.rows]
    return sig,loc,cx,ar,ok
def analyse(name):
    L=pickle.load(open(f"{SP}/ledger2_{name}.pkl","rb")); links=L["links"]; dbs=L["dbs"]; N=len(dbs); A=[arrays(d) for d in dbs]
    assert all(a[4] for a in A), "row alignment failed"
    up=collections.Counter(); down=collections.Counter(); n=0; tot=collections.Counter(); nchg=0
    for s,(link,kA,kB) in enumerate(links):
        sa,la,ca,ra,_=A[s]; sb,lb,cb,rb,_=A[s+1]
        for a,(b,*_r) in link.items():
            n+=1
            d=sb[b]-sa[a]; sizechg=(lb[b]!=la[a]); sigchg=bool(np.any(d!=0)); sc=(cb[b]!=ca[a]); ag=(rb[b]!=ra[a])
            if not (sizechg or sigchg or sc or ag): continue
            nchg+=1; tot["loc"]+=sizechg; tot["complexity"]+=sc; tot["args"]+=ag
            for i,f in enumerate(FAM):
                if d[i]>0: up[f]+=1
                elif d[i]<0: down[f]+=1
    return dict(n=n,nchg=nchg,up=dict(up),down=dict(down),tot=dict(tot))
if __name__=="__main__":
    R={}
    for name in sys.argv[2:]: R[name]=analyse(name); pickle.dump(R,open(sys.argv[1],"wb")); print(name,"done",flush=True)
    for name,r in R.items():
        print(f"\n== {name}: {r['nchg']} changes among {r['n']} function-quarters ({100*r['nchg']/r['n']:.1f}%) | size changed in {100*r['tot'].get('loc',0)/r['nchg']:.0f}% of changes, complexity {100*r['tot'].get('complexity',0)/r['nchg']:.0f}%, arguments {100*r['tot'].get('args',0)/r['nchg']:.0f}%")
        rows=sorted(((r['up'].get(f,0)+r['down'].get(f,0),f) for f in set(r['up'])|set(r['down'])),reverse=True)[:8]
        print("   keyword families that change most often (share of changes where the count moved; up/down):")
        for c,f in rows: print(f"     {f:26s} {100*c/r['nchg']:4.0f}%   up {r['up'].get(f,0):5d}  down {r['down'].get(f,0):5d}")
