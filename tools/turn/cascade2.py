import sys, pickle, json, time, collections, subprocess, sqlite3, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from structural_fingerprint import blind as BL
from structural_fingerprint import features as F
from structural_fingerprint.fingerprint import build, FunctionTable
from structural_fingerprint.reference import load_reference
from structural_fingerprint.scan_io import load_scan
from structural_fingerprint.twins import find_twins, TwinParams
POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; SP="/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"
refP=load_reference("portable")
def load_truth(name):
    if name=="impacket":
        picks,out=pickle.load(open(SP+"/rn_truth_impacket.pkl","rb"))
        commits=[p.commit for p in picks]; dbs=[f"{B}/scan_impacket/.work/snap_{i:03d}_galaxy_master.db" for i in range(len(picks))]
    else:
        commits,labels,out=pickle.load(open(f"{SP}/truth_{name}.pkl","rb"))
        snaps=json.load(open(f"{B}/scan_{name}/snapshots.json")); dbs=[x["db"] for x in snaps]
    return commits,dbs,out
def file_renames(repo,c1,c2):
    r=subprocess.run(["git","-C",repo,"diff","-M50%","--name-status",c1,c2],capture_output=True,text=True).stdout
    return {p[1]:p[2] for p in (l.split("\t") for l in r.splitlines()) if p[0].startswith("R") and len(p)==3}
def starts(db):
    con=sqlite3.connect(f"file:{db}?mode=ro",uri=True); files={r[0]:r[1] for r in con.execute("select id,file_path from file_data")}; d={}
    for fid,n,st in con.execute("select file_id,func_name,start_line from function_data"):
        if fid in files: d.setdefault((files[fid],n),st or 0)
    con.close(); return d
_c={}
def prep(db):
    if db in _c: return _c[db]
    sc=load_scan(db,refP.signal_columns); ft=build(sc,refP,min_loc=3,keyword_mode="composition").functions; v=BL.blind_view(ft)
    comp=F.raw_features(refP,sc.loc,sc.complexity,sc.args,sc.keyword_density,sc.signals,keyword_mode="composition")[v.rows]
    nrm=comp/np.maximum(np.linalg.norm(comp,axis=1,keepdims=True),1e-9)
    nb=collections.defaultdict(set)
    for a,b in v.edges.tolist(): nb[a].add(b); nb[b].add(a)
    keys=[(str(ft.path[r]),str(ft.name[r])) for r in v.rows]; vec=ft.vectors[v.rows]
    _c[db]=(ft,v,nrm,nb,keys,vec,starts(db)); return _c[db]
def sub(ft,v,idx):
    r=v.rows[np.asarray(idx,int)]
    return FunctionTable(repo=ft.repo,name=ft.name[r],path=ft.path[r],language=ft.language[r],loc=ft.loc[r],archetype=ft.archetype[r],key=ft.key[r],vectors=ft.vectors[r],edges=None)
def run_pair(name,s,commits,dbs,out):
    repo=f"{POOL}/{name}"; A=prep(dbs[s]); Bq=prep(dbs[s+1]); ftA,vA,nA,nbA,kA,vecA,stA=A; ftB,vB,nB,nbB,kB,vecB,stB=Bq
    cA=collections.Counter(kA); cB=collections.Counter(kB); idxB={k:i for i,k in enumerate(kB) if cB[k]==1}
    anchor={u:idxB[k] for u,k in enumerate(kA) if cA[k]==1 and k in idxB}        # unchanged functions map to themselves (certain)
    D=[u for u,k in enumerate(kA) if cA[k]==1 and k not in idxB and k not in cB]; Born=[i for i,k in enumerate(kB) if cB[k]==1 and k not in set(kA)]
    stages=collections.OrderedDict(); acc={}; used=set(anchor.values())
    fr=file_renames(repo,commits[s],commits[s+1])
    # stage 0 (name-AWARE; certain): same name in the file git says it moved to, or a name unique among the dead and among the born
    bykey={kB[i]:i for i in Born}; s0={}
    for u in D:
        k=(fr.get(kA[u][0],kA[u][0]),kA[u][1])
        if k in bykey and bykey[k] not in set(s0.values()): s0[u]=bykey[k]
    dn=collections.Counter(kA[u][1] for u in D if u not in s0); bn=collections.Counter(kB[i][1] for i in Born if i not in set(s0.values()))
    bname={kB[i][1]:i for i in Born if i not in set(s0.values())}
    for u in D:
        if u in s0: continue
        n=kA[u][1]
        if dn[n]==1 and bn.get(n)==1: s0[u]=bname[n]
    acc.update(s0); used|=set(s0.values()); stages["0 same name (file-mapped / unique)  [name-aware]"]=dict(acc)
    D=[u for u in D if u not in acc]; Born=[i for i in Born if i not in used]
    # stage 1: git file context + in-file structural match (structure + relative line order)
    pools=collections.defaultdict(lambda:([],[]))
    for u in D: pools[fr.get(kA[u][0],kA[u][0])][0].append(u)
    for i in Born: pools[kB[i][0]][1].append(i)
    s1={}
    for f,(ds,bs) in pools.items():
        if not ds or not bs: continue
        L=np.sqrt(((vecA[ds][:,None,:]-vecB[bs][None,:,:])**2).sum(2))
        p=np.array([stA.get(kA[u],0) for u in ds],float); q=np.array([stB.get(kB[i],0) for i in bs],float)
        rp=(np.argsort(np.argsort(p))+0.5)/len(p); rq=(np.argsort(np.argsort(q))+0.5)/len(q); T=L+0.5*np.abs(rp[:,None]-rq[None,:])
        bi=T.argmin(1); di=T.argmin(0)
        for a,u in enumerate(ds):
            j=bi[a]
            if di[j]==a: s1[u]=bs[j]
    acc.update(s1); used|=set(s1.values()); stages["1 + file context + in-file match"]=dict(acc)
    # stage 2: name-blind structural twins (reciprocal best hit + ratio test + decoy FDR) on what is left
    left=[u for u in D if u not in acc]; leftB=[i for i in Born if i not in used]; s2={}
    if len(left)>=3 and len(leftB)>=3:
        try:
            r=find_twins(sub(ftA,vA,left),sub(ftB,vB,leftB),TwinParams(min_loc=3,ratio=0.8,fdr=0.01))
            for qi,ti in zip(r.q_index,r.t_index): s2[left[int(qi)]]=leftB[int(ti)]
        except Exception: pass
    acc.update(s2); used|=set(s2.values()); stages["2 + structural twins"]=dict(acc)
    # stage 3: call-graph extension from every anchor and every match so far
    mapped=dict(acc)
    for _ in range(6):
        prop=[]
        for pu in D:
            if pu in mapped: continue
            votes=collections.Counter()
            for q in nbA.get(pu,()):
                t=anchor.get(q,mapped.get(q))
                if t is not None:
                    for rc in nbB.get(t,()):
                        if rc not in used and cB[kB[rc]]==1 and kB[rc] not in set(kA): votes[rc]+=1
            if not votes: continue
            c=np.array(list(votes)); w=np.array([votes[x] for x in c],float); cos=nB[c]@nA[pu]; sc=w*(1+np.maximum(cos,0)); k=int(np.argmax(sc))
            prop.append((float(sc[k]),pu,int(c[k]),float(cos[k])))
        if not prop: break
        prop.sort(reverse=True); add=0
        for _,pu,ru,cs in prop:
            if pu not in mapped and ru not in used and cs>=0.9: mapped[pu]=ru; used.add(ru); add+=1
        if not add: break
    stages["3 + call-graph extension"]=dict(mapped)
    truth={d:(b,j) for d,b,j in out[s]["truth"]}
    return kA,kB,D,stages,truth
def evaluate(name,pairs=None):
    commits,dbs,out=load_truth(name); R=collections.defaultdict(collections.Counter); T=collections.Counter(); t0=time.time()
    for s in sorted(out):
        if not out[s]["truth"] or (pairs and s not in pairs): continue
        kA,kB,D,stages,truth=run_pair(name,s,commits,dbs,out); inD={kA[u]:u for u in D}
        inD={kA[u]:u for u in range(len(kA))}
        for d,(b,j) in truth.items():
            if j>=0.85 and d in inD: T["move" if d[1]==b[1] else "rename"]+=1
        for sn,m in stages.items():
            for u,i in m.items():
                if u not in D and False: continue
                d=kA[u]; b=kB[i]
                if d in truth:
                    tb,j=truth[d]
                    if tb==b: R[sn]["hit_"+("move" if d[1]==b[1] else "rename")+("" if j>=0.85 else "_weak")]+=1
                    else: R[sn]["conflict"]+=1
                else: R[sn]["no-truth"]+=1
        print(name,s,f"{time.time()-t0:.0f}s",flush=True)
    return R,T
if __name__=="__main__":
    res={}
    for name in sys.argv[2:]:
        R,T=evaluate(name); res[name]=(dict((k,dict(v)) for k,v in R.items()),dict(T))
        pickle.dump(res,open(sys.argv[1],"wb"))
    print("\nstrong truth pairs present (loc>=3):")
    for name,(R,T) in res.items(): print(f"  {name:12s} moves {T.get('move',0)}  renames {T.get('rename',0)}")
    for name,(R,T) in res.items():
        print(f"\n{name}: cumulative stages  (precision lower/upper bound = hits / accepted, hits+unverified / accepted)")
        for sn,r in R.items():
            hm=r.get("hit_move",0); hr=r.get("hit_rename",0); acc=sum(r.values()); hw=r.get("hit_move_weak",0)+r.get("hit_rename_weak",0)
            print(f"  {sn:34s} moves {100*hm/max(1,T.get('move',0)):3.0f}%  renames {100*hr/max(1,T.get('rename',0)):3.0f}%  | accepted {acc:5d}: hits {hm+hr+hw}, conflict {r.get('conflict',0)}, unverified {r.get('no-truth',0)} | precision {100*(hm+hr+hw)/max(1,acc):3.0f}%..{100*(hm+hr+hw+r.get('no-truth',0))/max(1,acc):3.0f}%")
