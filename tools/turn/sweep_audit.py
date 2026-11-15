"""Label audit: how many labelled fix commits are really sweeps (mass API migrations)?"""
import sys, re, json, pickle, subprocess, collections, numpy as np
sys.path.insert(0,"/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad")
import sweeps as S
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; EV="/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"; SP="/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad"
PKL={"libgit2":"ts_edits_c2.pkl","redis":"ts_edits_c2.pkl","curl":"ts_edits_c2.pkl","libxml2":"ts_edits_ho_c.pkl","prometheus":"ts_edits_ho_jg.pkl","ripgrep":"ts_edits_lang.pkl","sphinx":"ts_edits_ho_py.pkl"}
CALL=re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\("); KW={"if","while","for","switch","sizeof","return","defined","elif","assert","def","class","lambda","print","catch","fn","match","func","range","len"}
def norm(n): n=n.rstrip("!"); return re.split(r"\.|::|->",n)[-1]
def run(name):
    repo=f"{POOL}/{name}"; sn=json.load(open(f"{B}/scan_{name}/snapshots.json"))
    ct=[int(subprocess.run(["git","-C",repo,"show","-s","--format=%ct",x["commit"]],capture_output=True,text=True).stdout.strip()) for x in sn]
    ev=pickle.load(open(f"{SP}/{PKL[name]}","rb"))[name]["events"]; migr,one,_=S.detect(ev)
    names=collections.defaultdict(set); pairs=collections.defaultdict(set)
    for m in migr: names[m["s"]]|={norm(m["old"]),norm(m["new"])}; pairs[m["s"]].add((norm(m["old"]),norm(m["new"])))
    for o in one: names[o["s"]].add(norm(o["name"]))
    fx=json.load(open(f"{EV}/{name}_xc2.json"))["events"]; out=[]
    for e in fx:
        t=e["ct"]; s=next((i for i in range(len(ct)-1) if ct[i]<t<=ct[i+1]),None)
        if s is None or not e.get("c_files") or len(e["c_files"])>200: continue
        d=subprocess.run(["git","-C",repo,"show","-U0","--format=","--no-color",e["sha"],"--"]+list(e["c_files"]),capture_output=True,text=True,errors="replace").stdout
        R=collections.Counter(); A=collections.Counter()
        for ln in d.splitlines():
            if ln.startswith("---") or ln.startswith("+++") or not ln or ln[0] not in "+-": continue
            tgt=R if ln[0]=="-" else A
            for m in CALL.findall(ln[1:]):
                if m not in KW: tgt[norm(m)]+=1
        N=set(R)|set(A); sw=N&names.get(s,set()); mig=any(o in R and nw in A for o,nw in pairs.get(s,()))
        out.append(dict(sha=e["sha"],cls=e.get("class"),s=s,n=len(N),sw=len(sw),mig=mig,nfiles=len(e["c_files"]),subject=e.get("subject","")[:90],swnames=sorted(sw)[:6]))
    return dict(name=name,events=out,total=len(fx))
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",len(out[n]["events"]),flush=True)
