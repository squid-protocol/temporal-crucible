#!/usr/bin/env python3
"""probe v2 (after review_claude.md): renames followed (R/C), nested defs stripped from the parent's body hash,
docstring-only changes split out, decorators in the signature, signature+body kinds kept, full subject stored,
merge-of-branch commits flagged."""
import ast, copy, json, subprocess, sys
G=["git","--git-dir","/srv/storage_16tb/projects/gitgalaxy-history/mirror.git"]
def sh(*a): return subprocess.run(G+list(a),capture_output=True,text=True,errors="replace").stdout
class Strip(ast.NodeTransformer):
    def visit_FunctionDef(self,n): return ast.Name(id="<def "+n.name+">",ctx=ast.Load())
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_ClassDef(self,n): return ast.Name(id="<class "+n.name+">",ctx=ast.Load())
def funcs(src):
    try: t=ast.parse(src)
    except Exception: return None
    out={}
    def walk(n,pre):
        for c in ast.iter_child_nodes(n):
            if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef)):
                q=pre+c.name
                sig=ast.dump(c.args)+(ast.dump(c.returns) if c.returns else "")+"".join(ast.dump(d) for d in c.decorator_list)
                body=list(c.body); doc=None
                if body and isinstance(body[0],ast.Expr) and isinstance(getattr(body[0],"value",None),ast.Constant) and isinstance(body[0].value.value,str):
                    doc=body[0].value.value; body=body[1:]
                m=ast.Module(body=[Strip().visit(copy.deepcopy(s)) for s in body],type_ignores=[])
                out[q]=(sig,ast.dump(m),doc,sum(1 for _ in ast.walk(c)))
                walk(c,q+".")
            elif isinstance(c,ast.ClassDef): walk(c,pre+c.name+".")
            else: walk(c,pre)
    walk(t,""); return out
def eng(p): return p.endswith(".py") and (p.startswith("gitgalaxy/") or p.startswith("backend/")) and "/tests/" not in p and "standards/" not in p and not p.endswith("__init__.py")
tip=sys.argv[1]
log=sh("log","--first-parent","-m","-M","--name-status","--format=@@%H\t%cs\t%P\t%s",tip)
cur=None; rows=[]
for l in log.splitlines():
    if l.startswith("@@"):
        h,d,par,s=l[2:].split("\t",3); cur={"sha":h,"date":d,"subj":s,"merge":len(par.split())>1,"files":[]}; rows.append(cur)
    elif l and cur is not None:
        p=l.split("\t"); st=p[0][0]
        if st in "AMD" and eng(p[-1]): cur["files"].append((st,p[-1],p[-1]))
        elif st in "RC" and eng(p[-1]): cur["files"].append(("M" if st=="R" else "A",p[1] if eng(p[1]) else None,p[-1]))
out=open("fn_events2.jsonl","w")
for r in rows:
    for st,of,nf in r["files"]:
        old=funcs(sh("show",r["sha"]+"^:"+of)) if st!="A" and of else {}
        new=funcs(sh("show",r["sha"]+":"+nf)) if st!="D" else {}
        if old is None or new is None: continue
        for q in set(old)|set(new):
            if q not in old: k="born"
            elif q not in new: k="deleted"
            else:
                o,n=old[q],new[q]
                if o[0]!=n[0]: k="signature"
                elif o[1]!=n[1]: k="body"
                elif o[2]!=n[2]: k="doc_only"
                else: continue
            o=old.get(q,(0,0,0,0)); n=new.get(q,(0,0,0,0))
            out.write(json.dumps({"sha":r["sha"],"date":r["date"],"subj":r["subj"],"merge":r["merge"],"file":nf,"old_file":of,"fn":q,"kind":k,
               "body_changed":(o[1]!=n[1]) if q in old and q in new else None,"n_old":o[3],"n_new":n[3]})+"\n")
out.close(); print("commits",len(rows))
