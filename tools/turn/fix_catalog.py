"""What do labelled fix commits do? tree-sitter diff of each changed C file before/after the fix."""
import sys, re, json, pickle, subprocess, collections
from tree_sitter_language_pack import get_parser
POOL="/srv/storage_16tb/projects/temporal-crucible-pool"; EV="/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"
P=get_parser("c")
UNSAFE={"strcpy","strcat","sprintf","vsprintf","gets","strncpy","strncat","atoi","atol","alloca","scanf","sscanf","strtok","memcpy","strdup"}
SAFER={"snprintf","vsnprintf","strlcpy","strlcat","strncpy","strncat","strtol","strtoul","strtoll","memmove","memcpy","calloc","fgets","curlx_strtoofft","strtok_r","msnprintf","curl_msnprintf"}
FREEISH={"free","Curl_safefree","curlx_free","git__free","xmlFree","zfree","sdsfree","Curl_cfree"}; ALLOC={"malloc","calloc","realloc","strdup","git__malloc","git__calloc","xmlMalloc","zmalloc","zcalloc","Curl_cmalloc"}
def parse(src):
    b=src.encode("utf8","replace"); t=P.parse(b); conds=collections.Counter(); calls=collections.Counter(); cnt=collections.Counter()
    def walk(n):
        cnt[n.type]+=1
        if n.type=="if_statement":
            c=n.child_by_field_name("condition")
            if c is not None: conds[re.sub(r"\s+","",b[c.start_byte:c.end_byte].decode("utf8","replace"))]+=1
        if n.type=="call_expression":
            f=n.child_by_field_name("function")
            if f is not None:
                if f.type=="field_expression": f=f.child_by_field_name("field") or f
                calls[b[f.start_byte:f.end_byte].decode("utf8","replace")]+=1
        for c in n.children: walk(c)
    walk(t.root_node); return cnt,calls,conds
def blob(repo,ref,path):
    r=subprocess.run(["git","-C",repo,"show",f"{ref}:{path}"],capture_output=True); 
    return r.stdout.decode("utf8","replace") if r.returncode==0 and len(r.stdout)<400_000 else None
NULLC=re.compile(r"NULL|^\(?!\(?\w+(->\w+|\.\w+|\[\w+\])*\)?\)?$|==0|!=0|==\(?void\*\)?0")
BNDC=re.compile(r"[<>]|len|size|count|max|min|SIZE_MAX|INT_MAX|overflow|bound|limit|remain",re.I)
def run(name):
    repo=f"{POOL}/{name}"; fx=json.load(open(f"{EV}/{name}_xc2.json"))["events"]; out=[]
    for k,e in enumerate(fx):
        files=[f for f in e.get("c_files",[]) if f.lower().endswith((".c",".h"))][:12]
        if not files: continue
        ns=subprocess.run(["git","-C",repo,"show","--numstat","--format=","--no-color",e["sha"],"--"]+list(e["c_files"][:60]),capture_output=True,text=True,errors="replace").stdout
        add=dele=0
        for ln in ns.splitlines():
            p=ln.split("\t")
            if len(p)==3 and p[0].isdigit() and p[1].isdigit(): add+=int(p[0]); dele+=int(p[1])
        cb=collections.Counter(); ca=collections.Counter(); kb=collections.Counter(); ka=collections.Counter(); db=collections.Counter(); da=collections.Counter(); ok=0
        for f in files:
            b=blob(repo,e["sha"]+"^",f); a=blob(repo,e["sha"],f)
            if a is None or b is None: continue
            ok+=1; x,y,z=parse(b); cb.update(x); kb.update(y); db.update(z); x,y,z=parse(a); ca.update(x); ka.update(y); da.update(z)
        if not ok: continue
        newc=da-db; gone=db-da; addc=ka-kb; remc=kb-ka
        out.append(dict(sha=e["sha"],cls=e.get("class"),lines=add+dele,files=len(e["c_files"]),
            guard_added=sum(newc.values()),guard_removed=sum(gone.values()),
            null_check=sum(v for c,v in newc.items() if NULLC.search(c)),bounds_check=sum(v for c,v in newc.items() if BNDC.search(c)),
            goto_d=ca["goto_statement"]-cb["goto_statement"],cast_d=ca["cast_expression"]-cb["cast_expression"],ret_d=ca["return_statement"]-cb["return_statement"],
            ptr_d=(ca["pointer_expression"]+ca["pointer_declarator"])-(cb["pointer_expression"]+cb["pointer_declarator"]),
            unsafe_removed=sum(v for c,v in remc.items() if c in UNSAFE),safer_added=sum(v for c,v in addc.items() if c in SAFER),
            free_added=sum(v for c,v in addc.items() if c in FREEISH),free_removed=sum(v for c,v in remc.items() if c in FREEISH),
            alloc_added=sum(v for c,v in addc.items() if c in ALLOC),alloc_removed=sum(v for c,v in remc.items() if c in ALLOC),
            add=dict(addc),rem=dict(remc)))
        if k%500==0: print(name,k,len(fx),flush=True)
    return dict(name=name,events=out)
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]: out[n]=run(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",len(out[n]["events"]),flush=True)
