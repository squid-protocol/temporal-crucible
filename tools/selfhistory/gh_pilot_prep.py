import json, re, random, collections, datetime as dt
rows = [json.loads(l) for l in open("items.jsonl")]; by = {r["n"]: r for r in rows}
prs = {r["n"]: r for r in rows if r["pr"]}; iss = [r for r in rows if not r["pr"]]
files = {}; cur = None
for line in open("commit_files.txt", errors="replace"):
    line = line.rstrip("\n")
    if line.startswith("@@"):
        sha, subj = line[2:].split("\t", 1); m = re.search(r"\(#(\d+)\)\s*$", subj); cur = int(m.group(1)) if m else None
        if cur: files[cur] = []
    elif line and cur: files[cur].append(line)
LINK = re.compile(r"\b(fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s*#(\d+)", re.I)
closing = collections.defaultdict(list)
for r in prs.values():
    for m in LINK.finditer(r["body"]):
        if int(m.group(2)) in by and not by[int(m.group(2))]["pr"] and r["merged"]: closing[int(m.group(2))].append(r["n"])
CAUSE = re.compile(r"(regress\w*|introduced (?:by|in|with)|broke(?:n)? (?:by|in|with)|caused by|since|after|due to|result of|side effect of|follow.?up (?:to|of)|as a result of)[^.\n]{0,60}?#(\d+)", re.I)
def iso(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
pop = [r for r in iss if "bug" in r["labels"] and closing.get(r["n"])]
gold = {}
for r in pop:
    for m in CAUSE.finditer(r["body"]):
        n = int(m.group(2))
        if n in prs and prs[n]["merged"] and iso(prs[n]["merged"]) < iso(r["created"]) and n not in closing[r["n"]]: gold.setdefault(r["n"], set()).add(n)
rng = random.Random(2982)
rest = sorted(r["n"] for r in pop if r["n"] not in gold); rng.shuffle(rest)
chosen = sorted(gold) + rest[: 100 - len(gold)]
print("population (bug, closed by merged PR):", len(pop), "| gold issues:", len(gold), "| random:", len(chosen) - len(gold))
def kind_bot(p):
    t = p["title"].lower()
    return p["utype"] == "Bot" or "auto-update" in t
def words(s): return set(re.findall(r"[a-z_]{4,}", s.lower()))
PATH = re.compile(r"[\w./-]+\.(?:py|java|md|yml|toml|json|cbl|cob|sh)\b")
items, key = [], {}
for n in chosen:
    r = by[n]; created = iso(r["created"]); named = set(PATH.findall(r["body"] + " " + r["title"]))
    iw = words(r["title"] + " " + r["body"][:1500]); cands = []
    for pn, p in prs.items():
        if not p["merged"] or kind_bot(p) or pn in closing[n]: continue
        mg = iso(p["merged"])
        if not (created - dt.timedelta(days=45) <= mg < created): continue
        fl = files.get(pn, [])
        fo = sum(1 for f in fl for nm in named if f.endswith(nm) or nm.endswith(f) or nm.split("/")[-1] == f.split("/")[-1])
        wo = len(iw & words(p["title"] + " " + p["body"][:300]))
        cands.append((fo, wo, mg, pn, p, fl))
    cands.sort(key=lambda c: (-c[0], -c[1], -c[2].timestamp()))
    top = cands[:25]
    items.append({"issue": n, "title": r["title"], "created": r["created"][:10], "body": r["body"][:3000],
                  "candidates": [{"pr": c[3], "title": c[4]["title"][:140], "merged": c[4]["merged"][:10], "files": c[5][:6], "body_start": " ".join(c[4]["body"][:200].split())} for c in top]})
    key[n] = {"closing_prs": closing[n], "gold_cause": sorted(gold.get(n, [])), "candidate_prs": [c[3] for c in top], "n_candidates_before_cut": len(cands)}
json.dump(key, open("pilot_key/key.json", "w"), indent=1)
for b in range(4):
    json.dump(items[b::4], open(f"pilot/batch_{b+1:02d}.json", "w"), indent=1)   # interleave so each batch mixes gold and random
print("batches:", [len(items[b::4]) for b in range(4)], "| issues with no candidates:", sum(1 for i in items if not i["candidates"]), "| median candidates:", sorted(len(i["candidates"]) for i in items)[50])
print("gold cause inside the candidate list:", sum(1 for n in gold if set(gold[n]) & set(key[n]["candidate_prs"])), "of", len(gold))
