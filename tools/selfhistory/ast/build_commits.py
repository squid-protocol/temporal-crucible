import json,re,collections,subprocess,datetime
GD=["git","--git-dir","/srv/storage_16tb/projects/gitgalaxy-history/mirror.git"]
E=[json.loads(l) for l in open("fn_events2.jsonl")]
items={i["n"]:i for i in map(json.loads,open("../gh/items.jsonl"))}
by=collections.defaultdict(list)
for e in E: by[e["sha"]].append(e)
MECH=re.compile(r"\b(ruff|lint|format|reformat|rename|typing|autofix|merge pull request|merge branch|bump|pyupgrade|isort)\b",re.I)
AG=re.compile(r"Claude|Co-Authored-By|🤖|Generated with|Codex|\bagy\b|Gemini|\[c:[0-9a-f]+\]",re.I)
def clean(t): t=re.sub(r"- \[[ xX]\].*","",t or ""); return re.sub(r"\r","",t).strip()
def pt(s):
    try: return datetime.datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception: return None
rows=[]; why=collections.Counter()
for sha,evs in by.items():
    if not any(e["kind"] in("body","signature") for e in evs): continue
    full=subprocess.run(GD+["show","-s","--format=%s%n%n%b",sha],capture_output=True,text=True,errors="replace").stdout.strip()
    subj=full.split("\n")[0]; m=re.findall(r"\(#(\d+)\)",subj); prn=int(m[-1]) if m else None
    pr=items.get(prn) if prn else None; prb=clean(pr["body"]) if pr and pr.get("pr") else ""
    reasons=[]
    if any(e["merge"] for e in evs): reasons.append("merge")
    if len(evs)>6: reasons.append(">6events")
    if MECH.search(subj): reasons.append("mechanical")
    sw=collections.Counter((e["n_new"]-e["n_old"]) for e in evs if e["kind"]=="body")
    if sw and max(sw.values())>=5 and max(sw)!=0: reasons.append("sweep")
    iss=[]
    for n in set(int(x) for x in re.findall(r"(?:part of|fixes|closes|resolves|refs?|towards)\s+#(\d+)",full+"\n"+prb,re.I)):
        it=items.get(n)
        if it and not it.get("pr"):
            early=bool(pr and pt(it["created"]) and pt(pr["created"]) and (pt(pr["created"])-pt(it["created"])).total_seconds()>86400)
            iss.append({"n":n,"title":it["title"],"body":clean(it["body"]),"early":early})
    rows.append({"sha":sha,"date":evs[0]["date"],"subject":subj,"commit":full,"pr":prn,"pr_body":prb,"issues":iss,"agent":bool(AG.search(full+prb)),
      "n_events":len(evs),"n_body":sum(e["kind"]=="body" for e in evs),"files":sorted({e["file"] for e in evs}),"tangled":reasons})
json.dump(rows,open("commits.json","w"))
el=[r for r in rows if not r["tangled"]]
print("commits with a body/signature rewrite",len(rows),"eligible (non-tangled)",len(el))
print("tangled reasons",collections.Counter(x for r in rows for x in r["tangled"]))
print("eligible agent-era",sum(r["agent"] for r in el),"with early issue",sum(any(i["early"] for i in r["issues"]) for r in el if r["agent"]),"with any issue",sum(bool(r["issues"]) for r in el if r["agent"]),"with PR body",sum(bool(r["pr_body"]) for r in el if r["agent"]))
print("eligible by month",dict(sorted(collections.Counter(r["date"][:7] for r in el).items())))
