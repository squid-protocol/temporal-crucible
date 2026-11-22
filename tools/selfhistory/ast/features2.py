#!/usr/bin/env python3
"""ast feature extractor for body rewrites. Output features2.jsonl: old/new feature dicts + node-type multiset for each event."""
import ast, json, subprocess, sys, collections, re
from multiprocessing import Pool
GD=["git","--git-dir","/srv/storage_16tb/projects/gitgalaxy-history/mirror.git"]
LOOP=(ast.For,ast.While,ast.AsyncFor); RE_FN={"compile","search","match","sub","subn","findall","finditer","fullmatch","split"}
def show(rev,f):
    return subprocess.run(GD+["show",f"{rev}:{f}"],capture_output=True,text=True,errors="replace").stdout
def find(tree,qn):
    parts=qn.split("."); 
    def rec(n,ps):
        for c in ast.iter_child_nodes(n):
            if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and c.name==ps[0]:
                return c if len(ps)==1 else rec(c,ps[1:])
        # descend through non-def blocks (if/try at module level)
        for c in ast.iter_child_nodes(n):
            if not isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                r=rec(c,ps)
                if r: return r
    return rec(tree,parts)
def rx_risk(p):
    try:
        import re._parser as sp
        t=sp.parse(p)
    except Exception: return (0,0)
    nested=alt=0
    def walk(items,inrep):
        nonlocal nested,alt
        for op,av in items:
            name=str(op)
            if name in("MAX_REPEAT","MIN_REPEAT") :
                if inrep: nested+=1
                walk(av[2],True)
            elif name=="BRANCH":
                alt+=len(av[1])
                for b in av[1]: walk(b,inrep)
            elif name in("SUBPATTERN",): walk(av[-1],inrep)
            elif name in("ASSERT","ASSERT_NOT"): walk(av[1],inrep)
    walk(t,False); return nested,alt
def feats(fn):
    F=collections.Counter(); types=collections.Counter(); consts=set(); strs=set(); calls=set()
    def visit(n,depth):
        types[type(n).__name__]+=1
        if isinstance(n,LOOP):
            F["loops"]+=1; depth+=1; F["max_loop_depth"]=max(F["max_loop_depth"],depth)
        if isinstance(n,(ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)):
            F["comps"]+=1; F["max_loop_depth"]=max(F["max_loop_depth"],depth+len(n.generators))
        if isinstance(n,ast.Try): F["try"]+=1; F["handlers"]+=len(n.handlers)
        if isinstance(n,ast.If) and n.body and all(isinstance(s,(ast.Return,ast.Raise,ast.Continue,ast.Break)) for s in n.body): F["guards"]+=1
        if isinstance(n,ast.If): F["ifs"]+=1
        if isinstance(n,ast.Compare):
            for op,r in zip(n.ops,n.comparators):
                if isinstance(op,(ast.In,ast.NotIn)):
                    F["in_tests"]+=1
                    if isinstance(r,(ast.List,ast.Tuple)): F["in_list_lit"]+=1
                    if isinstance(r,ast.Set): F["in_set_lit"]+=1
                    if depth>0: F["in_tests_in_loop"]+=1
        if isinstance(n,ast.AugAssign) and isinstance(n.op,ast.Add) and depth>0: F["augadd_in_loop"]+=1
        if isinstance(n,ast.Call):
            F["calls"]+=1
            nm=n.func.attr if isinstance(n.func,ast.Attribute) else getattr(n.func,"id",None)
            if nm: calls.add(nm)
            base=getattr(n.func,"value",None)
            if nm in RE_FN and isinstance(base,ast.Name) and base.id=="re":
                F["re_calls"]+=1
                if depth>0: F["re_calls_in_loop"]+=1
                if nm=="compile": F["re_compile"]+=1; 
                if n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):
                    nes,al=rx_risk(n.args[0].value); F["rx_nested"]+=nes; F["rx_alt"]+=al; F["rx_len"]+=len(n.args[0].value)
            if nm in("sorted","sort"): F["sorts"]+=1
            if nm in("getenv",) or (isinstance(n.func,ast.Attribute) and n.func.attr=="get" and "environ" in ast.dump(n.func)): F["env_reads"]+=1
        if isinstance(n,ast.Constant):
            if isinstance(n.value,(int,float)) and not isinstance(n.value,bool): consts.add(n.value)
            elif isinstance(n.value,str): strs.add(n.value)
        if isinstance(n,(ast.Return,)): F["returns"]+=1
        if isinstance(n,ast.Raise): F["raises"]+=1
        for c in ast.iter_child_nodes(n): visit(c,depth)
    for s in fn.body: visit(s,0)
    a=fn.args; allargs=a.posonlyargs+a.args+a.kwonlyargs
    F["args"]=len(allargs); F["annotated"]=sum(1 for x in allargs if x.annotation is not None)+(1 if fn.returns else 0)
    F["has_doc"]=1 if ast.get_docstring(fn) else 0
    F["nodes"]=sum(types.values()); F["lines"]=(getattr(fn,"end_lineno",fn.lineno)-fn.lineno+1)
    F["distinct_callees"]=len(calls)
    return dict(F),dict(types),sorted(map(str,consts)),len(strs),sorted(calls)
def work(e):
    f=e["file"]; out=dict(e)
    for side,rev in (("old",e["sha"]+"^"),("new",e["sha"])):
        ff=(e.get("old_file") or f) if side=="old" else f
        try: t=ast.parse(show(rev,ff)); n=find(t,e["fn"])
        except Exception: n=None
        if n is None: return None
        F,T,C,S,CL=feats(n); out[side]={"f":F,"types":T,"consts":C,"nstr":S,"callees":CL}
    return out
if __name__=="__main__":
    ev=[json.loads(l) for l in open("fn_events2.jsonl")]; ev=[e for e in ev if e["kind"] in ("body","signature")]
    with Pool(3) as p, open("features2.jsonl","w") as o:
        for r in p.imap(work,ev,chunksize=20):
            if r: o.write(json.dumps(r)+"\n")
