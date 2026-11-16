"""Does measured reach (callers of the swept functions) predict where a sweep's ripple lands, better than the file-level api_exposure score?"""
import sys, json, pickle, sqlite3, collections, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src"); sys.path.insert(0,"/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn-forecast/tools/turn"); sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
from pathlib import Path
from scipy.stats import spearmanr, rankdata
from sklearn.linear_model import LogisticRegression
from structural_fingerprint import ledger as LG
import sweeps as S
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; A=f"{B}/analysis"
SRC={"libgit2":"ts_edits_c2.pkl","redis":"ts_edits_c2.pkl","curl":"ts_edits_c2.pkl","expat":"ts_edits_ho_c.pkl","libxml2":"ts_edits_ho_c.pkl","scapy":"ts_edits_ho_py.pkl","sphinx":"ts_edits_ho_py.pkl","commons-io":"ts_edits_ho_jg.pkl","prometheus":"ts_edits_ho_jg.pkl","sqlmap":"ts_edits_lang.pkl","ripgrep":"ts_edits_lang.pkl","tigerbeetle":"ts_edits_lang.pkl","impacket":"ts_edits_imp.pkl"}
def auc(y,s):
    y=np.asarray(y,bool)
    if y.sum()<10 or (~y).sum()<10: return np.nan
    r=rankdata(s); n1=y.sum(); return (r[y].sum()-n1*(n1+1)/2)/(n1*(~y).sum())
def run(name):
    f=Path(f"{B}/scan_{name}/snapshots.json")
    if f.exists(): sn=json.load(open(f))
    else:
        picks,_o=pickle.load(open("/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad/rn_truth_impacket.pkl","rb")); sn=[{"commit":p.commit,"db":f"{B}/scan_impacket/.work/snap_{i:03d}_galaxy_master.db"} for i,p in enumerate(picks)]
    snaps=[LG.Snapshot(Path(x["db"]),x["commit"],"") for x in sn]; led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); N=len(snaps)
    ev=pickle.load(open(f"{A}/{SRC[name]}","rb"))[name]["events"]; migr,_,ins=S.detect(ev)
    pos={}
    def idx_of(e):
        s=e["s"]
        if "x" in e: return e["x"]
        if s not in pos: pos[s]={int(v):i for i,v in enumerate(led.ids[s])}
        return pos[s].get(e["id"])
    byS=collections.defaultdict(set); edited=collections.defaultdict(set); sweepfn=collections.defaultdict(set); bym=collections.defaultdict(list)
    for m in migr: bym[m["s"]].append(m)
    for i,e in enumerate(ev):
        if not e["code"]: continue
        x=idx_of(e)
        if x is None: continue
        lid=int(led.ids[e["s"]][x])
        if i in ins: sweepfn[e["s"]].add(x)
        else: edited[e["s"]].add(lid)
        for m in bym.get(e["s"],()):
            if m["old"] in e["rem"] and m["new"] in e["add"]: byS[(m["s"],m["old"],m["new"])].add(x)
    rows=[]; sweeps=[]
    for (s,o,nw),Sset in byS.items():
        if len(Sset)<10 or s+2>=N: continue
        edges=led._snaps[s].view.edges; callers=collections.defaultdict(set)
        for u,v in edges.tolist(): callers[v].add(u)
        d1=set().union(*[callers[v] for v in Sset])-Sset; d2=set().union(*[callers[u] for u in d1])-Sset-d1 if d1 else set()
        n=len(led.keys[s]); keys=led.keys[s]; meta=led._snaps[s].meta; swfiles={keys[i][0] for i in Sset}
        fanin=np.zeros(n); 
        if len(edges): np.add.at(fanin,edges[:,1],1)
        E=edited[s]|edited[s+1]; allsw=sweepfn[s]|Sset
        try:
            con=sqlite3.connect(f"file:{sn[s]['db']}?mode=ro",uri=True); api=dict(con.execute("select file_path, risk_api_exposure from file_data")); con.close()
        except Exception: api={}
        rng=np.random.default_rng(2982+s); cand=[i for i in range(n) if i not in allsw]
        keep=set(d1)|set(d2)|{i for i in cand if keys[i][0] in swfiles}
        others=[i for i in cand if i not in keep]; keep|=set(rng.choice(others,min(len(others),3000),replace=False).tolist()) if others else set()
        apiv=np.array([api.get(keys[i][0],0.0) for i in range(n)]); apir=rankdata(apiv)/n
        for i in keep:
            if i in allsw: continue
            ln=meta[i][1] if meta[i] else 0
            rows.append((len(sweeps),int(i in d1),int(i in d2),int(keys[i][0] in swfiles),np.log1p(ln),np.log1p(fanin[i]),apir[i],int(int(led.ids[s][i]) in E)))
        edited_d1=sum(1 for i in d1 if int(led.ids[s][i]) in E)
        sweeps.append((name,s,len(Sset),len(d1),len(d2),len({keys[i][0] for i in d1}),edited_d1))
    return dict(name=name,rows=np.array(rows,float),sweeps=sweeps)
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",len(out[n]["sweeps"]),"sweeps",len(out[n]["rows"]),"rows",flush=True)
