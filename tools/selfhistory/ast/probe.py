#!/usr/bin/env python3
"""Feasibility probe: per first-parent commit, per engine .py file, match functions old vs new by qualname and
classify born / deleted / body_changed / signature_changed / unchanged using ast.dump (no positions)."""
import ast, json, subprocess, sys, re
G=["git","--git-dir","/srv/storage_16tb/projects/gitgalaxy-history/mirror.git"]
def sh(*a):
    return subprocess.run(G+list(a),capture_output=True,text=True,errors="replace").stdout
def funcs(src):
    try: t=ast.parse(src)
    except Exception: return None
    out={}
    def walk(n,pre):
        for c in ast.iter_child_nodes(n):
            if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef)):
                q=pre+c.name
                sig=ast.dump(c.args)+ast.dump(c.returns) if c.returns else ast.dump(c.args)
                body=ast.dump(ast.Module(body=c.body,type_ignores=[]))
                out[q]=(sig,body,sum(1 for _ in ast.walk(c)))
                walk(c,q+".")
            elif isinstance(c,ast.ClassDef): walk(c,pre+c.name+".")
            else: walk(c,pre)
    walk(t,"")
    return out
def eng(p): return p.endswith(".py") and (p.startswith("gitgalaxy/") or p.startswith("backend/")) and "/tests/" not in p and "standards/" not in p and not p.endswith("__init__.py")
tip=sys.argv[1]
log=sh("log","--first-parent","-m","--name-status","--format=@@%H\t%cs\t%s",tip)
cur=None; rows=[]
for l in log.splitlines():
    if l.startswith("@@"):
        h,d,s=l[2:].split("\t",2); cur={"sha":h,"date":d,"subj":s,"files":[]}; rows.append(cur)
    elif l and cur is not None:
        p=l.split("\t")
        if p[0][0] in "AMD" and eng(p[-1]): cur["files"].append((p[0][0],p[-1]))
out=open("fn_events.jsonl","w")
for r in rows:
    for st,f in r["files"]:
        old=funcs(sh("show",r["sha"]+"^:"+f)) if st!="A" else {}
        new=funcs(sh("show",r["sha"]+":"+f)) if st!="D" else {}
        if old is None or new is None: continue
        for q in set(old)|set(new):
            if q not in old: k="born"
            elif q not in new: k="deleted"
            elif old[q][0]!=new[q][0]: k="signature"
            elif old[q][1]!=new[q][1]: k="body"
            else: continue
            out.write(json.dumps({"sha":r["sha"],"date":r["date"],"subj":r["subj"][:100],"file":f,"fn":q,"kind":k,
              "n_old":old.get(q,(0,0,0))[2],"n_new":new.get(q,(0,0,0))[2]})+"\n")
out.close()
print("commits",len(rows))
