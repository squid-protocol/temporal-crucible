"""What changes inside surviving functions: tree-sitter diff of each ledger-linked function between consecutive snapshots (C family)."""
import sys, re, json, pickle, collections, numpy as np
sys.path.insert(0,"/srv/storage_16tb/projects/structural-fingerprint-scanner/src")
from pathlib import Path
from structural_fingerprint import ledger as LG
from tree_sitter_language_pack import get_parser
B="/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2"; POOL="/srv/storage_16tb/projects/temporal-crucible-pool"
PARSER=get_parser("c")
NODES=["if_statement","for_statement","while_statement","switch_statement","goto_statement","return_statement","cast_expression","pointer_expression","pointer_declarator","subscript_expression","field_expression","call_expression","conditional_expression","sizeof_expression","preproc_if","preproc_ifdef","preproc_def","preproc_call","comment","declaration","assignment_expression"]
PRINT={"printf","fprintf","vfprintf","puts","perror","fputs","putchar","vprintf"}
ALLOC={"malloc","calloc","realloc","strdup","free","Curl_safefree","Curl_cfree","zmalloc","zfree","zcalloc","zrealloc","sdsfree","git__malloc","git__free","git__calloc","git__strdup","git__realloc","git__reallocarray","curlx_free","Curl_ccalloc","Curl_cmalloc","Curl_cstrdup","curl_free"}
ASSERT={"assert","DEBUGASSERT","git_assert","GIT_ASSERT","GIT_ASSERT_ARG","serverAssert","serverAssertWithInfo","redisAssert","DEBUGF","infof","failf"}
def feats(src: bytes):
    t=PARSER.parse(src); cnt=collections.Counter(); calls=collections.Counter(); sig=None
    def walk(n):
        nonlocal sig
        cnt[n.type]+=1
        if n.type=="call_expression":
            f=n.child_by_field_name("function")
            if f is not None:
                if f.type=="field_expression": f=f.child_by_field_name("field") or f
                calls[src[f.start_byte:f.end_byte].decode("utf8","replace")]+=1
        if n.type=="function_definition" and sig is None:
            body=n.child_by_field_name("body"); end=body.start_byte if body is not None else n.end_byte
            sig=re.sub(r"\s+"," ",src[n.start_byte:end].decode("utf8","replace")).strip()
        if n.type=="identifier" and src[n.start_byte:n.end_byte]==b"NULL": cnt["NULL"]+=1
        for c in n.children: walk(c)
    walk(t.root_node); return cnt,calls,sig
def analyse(name):
    f=Path(f"{B}/scan_{name}/snapshots.json"); sn=json.load(open(f)); yrs=[int(str(x["date"])[:4]) for x in sn]
    snaps=[LG.Snapshot(Path(x["db"]),x["commit"],x["label"]) for x in sn]
    led=LG.build_ledger(Path(f"{POOL}/{name}"),snaps); ev=[]; skipped=0; total=0
    for s,link in enumerate(led.links):
        a,b=led._snaps[s],led._snaps[s+1]
        for x,lk in link.items():
            path_a,nm_a=a.keys[x]; path_b,nm_b=b.keys[lk.new]
            if not path_a.lower().endswith((".c",".h")) or not path_b.lower().endswith((".c",".h")): continue
            ma,mb=a.meta[x],b.meta[lk.new]
            if not ma or not mb or ma[0]<1 or mb[0]<1: skipped+=1; continue
            la,lb=a.git.lines(a.snap.commit,path_a),b.git.lines(b.snap.commit,path_b)
            if la is None or lb is None: skipped+=1; continue
            total+=1
            ra="\n".join(la[ma[0]-1:ma[0]-1+ma[1]]); rb="\n".join(lb[mb[0]-1:mb[0]-1+mb[1]])
            if ra==rb: continue
            ta=LG.body_tokens(la,path_a,nm_a,ma[0],ma[1]); tb=LG.body_tokens(lb,path_b,nm_b,mb[0],mb[1])
            e=dict(s=s,year=yrs[s+1],stage=lk.stage,code=(ta!=tb),dloc=mb[1]-ma[1])
            if e["code"]:
                ca,ka,sa=feats(ra.encode()); cb,kb,sb=feats(rb.encode())
                e["d"]={k:cb[k]-ca[k] for k in NODES+["NULL"] if cb[k]!=ca[k]}
                e["sig"]=bool(sa and sb and sa.replace(nm_a,"@")!=sb.replace(nm_b,"@"))
                add=kb-ka; rem=ka-kb
                e["add"]=dict(add); e["rem"]=dict(rem)
            ev.append(e)
    return dict(name=name,events=ev,total=total,skipped=skipped)
if __name__=="__main__":
    out={}
    for n in sys.argv[2:]:
        out[n]=analyse(n); pickle.dump(out,open(sys.argv[1],"wb")); print(n,"done",len(out[n]["events"]),"changed of",out[n]["total"],flush=True)
