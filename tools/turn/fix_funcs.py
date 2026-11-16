"""Which functions did each fix commit touch?  hunks (old-file line ranges) x function ranges of the pre-fix file (tree-sitter C)."""
import sys, re, json, pickle, subprocess, collections
from tree_sitter_language_pack import get_parser
POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; EV="/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"
P=get_parser("c")
def fname(n):
    d=n.child_by_field_name("declarator")
    while d is not None and d.type!="function_declarator": d=d.child_by_field_name("declarator")
    if d is None: return None
    i=d.child_by_field_name("declarator")
    while i is not None and i.type not in ("identifier",): 
        i=i.child_by_field_name("declarator") or (i.children[0] if i.children else None)
    return i
def funcs(src):
    b=src.encode("utf8","replace"); out=[]
    def walk(n):
        if n.type=="function_definition":
            i=fname(n)
            if i is not None: out.append((b[i.start_byte:i.end_byte].decode("utf8","replace"),n.start_point[0]+1,n.end_point[0]+1))
            return
        for c in n.children: walk(c)
    walk(P.parse(b).root_node); return out
HUNK=re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")
def run(name):
    repo=f"{POOL}/{name}"; ev={}
    for suf in ("_xc","_xc2"):
        for e in json.load(open(f"{EV}/{name}{suf}.json"))["events"]: ev.setdefault(e["sha"],e)
    hits={}
    for k,(sha,e) in enumerate(ev.items()):
        files=[f for f in e.get("c_files",[]) if f.lower().endswith((".c",".h"))][:8]
        if not files: continue
        d=subprocess.run(["git","-C",repo,"show","-U0","--format=","--no-color",sha,"--"]+files,capture_output=True,text=True,errors="replace").stdout
        cur=None; ranges=collections.defaultdict(list)
        for ln in d.splitlines():
            if ln.startswith("--- a/"): cur=ln[6:]
            elif ln.startswith("--- /dev/null"): cur=None
            else:
                m=HUNK.match(ln)
                if m and cur: a=int(m.group(1)); n=int(m.group(2)) if m.group(2) is not None else 1; ranges[cur].append((a,a+max(n,1)-1))
        res=[]
        for p,rs in ranges.items():
            r=subprocess.run(["git","-C",repo,"show",f"{sha}^:{p}"],capture_output=True)
            if r.returncode!=0 or len(r.stdout)>300_000: continue
            fs=funcs(r.stdout.decode("utf8","replace")); seen=set()
            for a,z in rs:
                for nm,s0,s1 in fs:
                    if s0<=z and a<=s1 and (nm,s0) not in seen: seen.add((nm,s0)); res.append((p,nm))
        hits[sha]=dict(ct=e["ct"],funcs=res,cls=e.get("class"))
        if k%1000==0: print(name,k,len(ev),flush=True)
    return dict(name=name,hits=hits)
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",len(out[n]["hits"]),flush=True)
