import json,re,random
C=json.load(open("commits.json")); el=[r for r in C if not r["tangled"]]
STOP=r"loops?|nested|set|dict|dictionary|guards?|regex(?:es)?|patterns?|compile[ds]?|cach(?:e|ed|ing)|hoist(?:ed|ing)?|early[- ]return|try/except|try|except|constants?|lookups?|precompute[ds]?|quadratic|linear|splice|split|O\(\w+(?:\^?\d)?\)|iterat\w+|list|tuple|memoi[sz]\w*|branch(?:es)?"
def mask(t):
    t=re.sub(r"```.*?```"," ",t,flags=re.S); t=re.sub(r"`[^`]*`"," ",t)
    t=re.sub(r"\b[\w./]+\.(?:py|md|json|yml|yaml|toml)\b"," ",t); t=re.sub(r"\b\w+_\w+(?:\(\))?"," ",t); t=re.sub(r"\b\w+\.\w+\(\)"," ",t)
    t=re.sub(r"\b(?:%s)\b"%STOP,"[M]",t,flags=re.I); t=re.sub(r"https?://\S+"," ",t); t=re.sub(r"\[c:[0-9a-f]+\]"," ",t)
    return re.sub(r"[ \t]+"," ",re.sub(r"\n{2,}","\n",t)).strip()
A=[{"id":r["sha"][:10],"text":mask(r["subject"]+"\n"+r["pr_body"])[:1500]} for r in el]
B=[{"id":r["sha"][:10],"text":mask("\n\n".join(i["title"]+"\n"+i["body"] for i in r["issues"] if i["early"]))[:1500]} for r in el if any(i["early"] for i in r["issues"])]
random.seed(7)
pil=random.sample(A,20); json.dump(pil,open("coding/pilot.json","w"),indent=0)
rest=[a for a in A if a["id"] not in {p["id"] for p in pil}]
def chunks(L,n): return [L[i:i+n] for i in range(0,len(L),n)]
for k,c in enumerate(chunks(rest,90)): json.dump(c,open(f"coding/A_{k:02d}.json","w"))
for k,c in enumerate(chunks(B,90)): json.dump(c,open(f"coding/B_{k:02d}.json","w"))
print(len(A),len(B),"A files",len(chunks(rest,90)),"B files",len(chunks(B,90)))
