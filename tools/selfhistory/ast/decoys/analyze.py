#!/usr/bin/env python3
import collections, glob, json, os, sqlite3, sys
sys.path.insert(0, "/srv/storage_16tb/projects/gitgalaxy-worktrees/engine-main")
from gitgalaxy.recorders.record_keeper import RecordKeeper
colmap = RecordKeeper().SHORT_KEY_MAP
man = json.load(open("root/manifest.json"))
db = glob.glob("scan/*master.db")[0]
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
have = {r[1] for r in c.execute("PRAGMA table_info(file_data)")}
vals = {}
fams_needed = sorted({f for m in man.values() for f in m["families"]})
cols = {f: colmap.get(f, f) for f in fams_needed}
missing = [f for f, col in cols.items() if col not in have]
sel = [col for col in set(cols.values()) if col in have]
for fp, *row in c.execute(f"SELECT file_path, {','.join(sel)} FROM file_data"):
    parts = fp.replace("\\", "/").split("/")
    folder = next((p for p in parts if "__" in p), None)
    if folder is None:
        continue
    vals[(folder, parts[-1])] = dict(zip(sel, row))
res = {}
for lang, m in man.items():
    base = vals.get((f"{lang}__base", m["main"]))
    if base is None:
        continue
    for fam in m["families"]:
        col = cols[fam]
        code = vals.get((f"{lang}__{fam}__code", m["main"])); com = vals.get((f"{lang}__{fam}__comment", m["main"]))
        if code is None or com is None or col not in base:
            continue
        dc, dm = (code[col] or 0) - (base[col] or 0), (com[col] or 0) - (base[col] or 0)
        sf = m.get("string_file")
        strv = vals.get((f"{lang}__{fam}__string", sf)) if sf else None
        sbase = vals.get((f"{lang}__base", sf)) if sf else None
        ds = None if strv is None or sbase is None else (strv[col] or 0) - (sbase[col] or 0)
        state = "pass" if dc > 0 and dm == 0 else "leak" if dc > 0 and dm > 0 else "leak-uncontrolled" if dm > 0 else "no-control"
        res.setdefault(lang, {})[fam] = {"state": state, "code_delta": dc, "comment_delta": dm, "keyword": m["families"][fam], "string_delta": ds}
json.dump(res, open("decoy_results.json", "w"), indent=1)
cnt = collections.Counter(v["state"] for l in res.values() for v in l.values())
print("columns missing from file_data:", missing)
print("cells:", sum(cnt.values()), dict(cnt), "languages:", len(res))
leaks = collections.defaultdict(list)
for l, fs in res.items():
    for f, v in fs.items():
        if v["state"].startswith("leak"):
            leaks[f].append(f"{l}({v['keyword']})")
print("\ncomment leaks by family:")
for f, ls in sorted(leaks.items(), key=lambda kv: -len(kv[1])):
    print(f"  {f:26s} {len(ls):3d}  {', '.join(ls[:8])}{' ...' if len(ls) > 8 else ''}")
nc = collections.Counter(f for l in res.values() for f, v in l.items() if v["state"] == "no-control")
print("\nno positive control (keyword did not fire as bare code), by family:", dict(nc.most_common(8)))

sc = [v for l in res.values() for v in l.values() if v["string_delta"] is not None and v["state"] == "pass"]
print("\nstring layer (only cells with a positive control):", len(sc), "| keyword in a string literal counts:", sum(1 for v in sc if v["string_delta"] > 0), "| does not:", sum(1 for v in sc if v["string_delta"] == 0))
byfam = collections.defaultdict(lambda: [0, 0])
for l in res.values():
    for f, v in l.items():
        if v["string_delta"] is not None and v["state"] == "pass":
            byfam[f][0] += v["string_delta"] > 0; byfam[f][1] += 1
print("share of languages where the family counts a keyword inside a string literal:")
for f, (n, t) in sorted(byfam.items(), key=lambda kv: -kv[1][0] / kv[1][1]):
    print(f"  {f:26s} {n:3d}/{t:<3d} {100*n//t:3d}%")
