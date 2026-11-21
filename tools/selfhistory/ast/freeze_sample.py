import json,re,random,collections,subprocess
E=[json.loads(l) for l in open("fn_events.jsonl")]; b=[e for e in E if e["kind"]=="body"]
per=collections.Counter(e["sha"] for e in b)
mech=collections.Counter((e["sha"],e["fn"].split(".")[-1]) for e in b)   # same fn name in many files = sweep marker
tangled={s for s,v in per.items() if v>6}
nonT=[e for e in b if e["sha"] not in tangled]
rep=collections.Counter((e["file"],e["fn"]) for e in b)
A=[e for e in nonT if rep[(e["file"],e["fn"])]>=3]
rest=[e for e in nonT if rep[(e["file"],e["fn"])]<3]
random.seed(20261120); R=random.sample(rest,min(300,len(rest)))
S=A+R
print("rewrites",len(b),"tangled commits",len(tangled),"rewrites in them",sum(per[s] for s in tangled),"non-tangled",len(nonT),"A(>=3 reps)",len(A),"R random",len(R),"sample",len(S))
json.dump({"seed":20261120,"rule":"non-tangled (<=6 body rewrites/commit); all rewrites of functions rewritten>=3 times + random 300 of the rest","keys":[[e["sha"],e["file"],e["fn"]] for e in S],"tangled":sorted(tangled)},open("sample_frozen.json","w"))
# claim text for the sample commits (subject+body from git; PR body from items.jsonl)
GD=["git","--git-dir","/srv/storage_16tb/projects/gitgalaxy-history/mirror.git"]
I={i["n"]:i for i in map(json.loads,open("../gh/items.jsonl")) if i.get("pr")}
def clean(t): t=re.sub(r"- \[[ x]\].*","",t or ""); return re.sub(r"\r","",t).strip()
out=open("claims.jsonl","w")
for s in sorted({e["sha"] for e in S}):
    body=subprocess.run(GD+["show","-s","--format=%s%n%n%b",s],capture_output=True,text=True,errors="replace").stdout
    m=re.findall(r"\(#(\d+)\)",body.split("\n")[0]); pb=clean(I[int(m[-1])]["body"]) if m and int(m[-1]) in I else ""
    out.write(json.dumps({"sha":s,"commit":body.strip()[:3000],"pr":int(m[-1]) if m else None,"pr_body":pb[:4000]})+"\n")
