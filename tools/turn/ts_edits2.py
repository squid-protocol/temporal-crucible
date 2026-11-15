"""Tree-sitter edit classification for Python, Rust and Zig (same method as ts_edits.py for C)."""
import sys; sys.path.insert(0,"/srv/storage_16tb/projects/historical-call-graph-gif")
import sys, re, json, pickle, textwrap, collections
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from pathlib import Path
from structural_fingerprint import ledger as LG
from tree_sitter_language_pack import get_parser
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"
LANG={"python":dict(exts=(".py",),calls={"call":"function"},fn=("function_definition",),dedent=True),
      "rust":dict(exts=(".rs",),calls={"call_expression":"function","macro_invocation":"macro"},fn=("function_item",),dedent=False),
      "zig":dict(exts=(".zig",),calls={"call_expression":"function"},fn=("function_declaration",),dedent=False)}
REPO_LANG={"sqlmap":"python","impacket":"python","ripgrep":"rust","tigerbeetle":"zig","scapy":"python","sphinx":"python"}
_P={}
def feats(src:str,lang:str):
    L=LANG[lang]; P=_P.setdefault(lang,get_parser(lang)); b=(textwrap.dedent(src) if L["dedent"] else src).encode()
    t=P.parse(b); cnt=collections.Counter(); calls=collections.Counter(); sig=None
    def txt(n): return b[n.start_byte:n.end_byte].decode("utf8","replace")
    def walk(n):
        nonlocal sig
        if n.is_named: cnt[n.type]+=1
        fld=L["calls"].get(n.type)
        if fld:
            f=n.child_by_field_name(fld)
            if f is not None:
                name=re.sub(r"\s+","",txt(f))
                if lang!="python" and f.type=="field_expression": name=name.split(".")[-1]
                if n.type=="macro_invocation": name+="!"
                calls[name[:48]]+=1
        if sig is None and n.type in L["fn"]:
            body=n.child_by_field_name("body"); sig=re.sub(r"\s+"," ",b[n.start_byte:(body.start_byte if body is not None else n.end_byte)].decode("utf8","replace")).strip()
        for c in n.children: walk(c)
    walk(t.root_node); return cnt,calls,sig
def analyse(name):
    lang=REPO_LANG[name]; L=LANG[lang]; f=Path(f"{B}/scan_{name}/snapshots.json")
    if f.exists(): sn=json.load(open(f))
    else:
        picks,_o=pickle.load(open("/tmp/claude-1000/-srv-storage-16tb-projects/1f3079c5-1f64-4125-9ec0-de27472732ec/scratchpad/rn_truth_impacket.pkl","rb"))
        sn=[{"label":p.label,"date":p.date,"commit":p.commit,"db":f"{B}/scan_impacket/.work/snap_{i:03d}_galaxy_master.db"} for i,p in enumerate(picks)]
    yrs=[int(str(x["date"])[:4]) for x in sn]; snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); ev=[]; total=0
    for s,link in enumerate(led.links):
        a,b=led._snaps[s],led._snaps[s+1]
        for x,lk in link.items():
            pa,na=a.keys[x]; pb,nb=b.keys[lk.new]
            if not pa.lower().endswith(L["exts"]) or not pb.lower().endswith(L["exts"]): continue
            ma,mb=a.meta[x],b.meta[lk.new]
            if not ma or not mb or ma[0]<1 or mb[0]<1: continue
            la,lb=a.git.lines(a.snap.commit,pa),b.git.lines(b.snap.commit,pb)
            if la is None or lb is None: continue
            total+=1; ra="\n".join(la[ma[0]-1:ma[0]-1+ma[1]]); rb="\n".join(lb[mb[0]-1:mb[0]-1+mb[1]])
            if ra==rb: continue
            ta=LG.body_tokens(la,pa,na,ma[0],ma[1]); tb=LG.body_tokens(lb,pb,nb,mb[0],mb[1])
            e=dict(s=s,year=yrs[s+1],id=int(led.ids[s][x]),stage=lk.stage,code=(ta!=tb),dloc=mb[1]-ma[1])
            if e["code"]:
                ca,ka,sa=feats(ra,lang); cb,kb,sb=feats(rb,lang)
                e["d"]={k:cb[k]-ca[k] for k in set(ca)|set(cb) if cb[k]!=ca[k]}
                e["sig"]=bool(sa and sb and sa.replace(na,"@")!=sb.replace(nb,"@")); e["add"]=dict(kb-ka); e["rem"]=dict(ka-kb)
            ev.append(e)
    return dict(name=name,lang=lang,events=ev,total=total,labels=[x["label"] for x in sn])
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]:
        out[n]=analyse(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",len(out[n]["events"]),"changed of",out[n]["total"],flush=True)
