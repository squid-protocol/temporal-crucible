"""Step 1-4: build week-end snapshots, attachment, touches, rows. Writes rows.pkl (all derived data)."""
import subprocess, json, gzip, re, ast, os, sqlite3, pickle, datetime as dt, collections, bisect
H = "/srv/storage_16tb/projects/gitgalaxy-history"
M = H + "/mirror.git"
OUT = H + "/tests_attach"
TIP = "7203d2555753ca2b29e180de3cb8d7845aca6a06"

def git(*a):
    return subprocess.run(["git", "--git-dir=" + M, "-c", "core.quotepath=off", *a], capture_output=True, text=True, errors="replace", check=True).stdout

def canon(p):
    return "gitgalaxy/" + p[len("backend/"):] if p.startswith("backend/") else p

def is_engine(p):
    p = canon(p)
    return (p.startswith("gitgalaxy/") and p.endswith(".py") and not p.startswith("gitgalaxy/standards/")
            and not p.endswith("/__init__.py") and "/tests/" not in p)

def group(p):
    s = p.split("/")
    return s[1] if len(s) > 2 and s[1] in ("core", "tools", "recorders") else "other"

def utc(s):
    return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc).replace(tzinfo=None)

def wk(d):  # ISO week -> Monday date
    d = d.date() if isinstance(d, dt.datetime) else d
    return d - dt.timedelta(days=d.weekday())

# ---- commits
fp = []  # newest first
for l in git("log", "--first-parent", "--format=%H%x09%cI%x09%s", TIP).splitlines():
    h, c, s = l.split("\t", 2); fp.append((h, utc(c), s))
fpset = {h for h, _, _ in fp}
allc = {}
for l in git("log", "--no-merges", "--format=%H%x09%cI%x09%s", TIP).splitlines():
    h, c, s = l.split("\t", 2); allc[h] = (utc(c), s)
log = collections.OrderedDict()
log["first_parent_commits"] = len(fp); log["non_merge_commits"] = len(allc)
first_day = min(d for d, _ in allc.values())
w0 = wk(first_day); w1 = wk(max(d for h, d, s in fp))
weeks = []
w = w0
while w <= w1:
    weeks.append(w); w += dt.timedelta(days=7)
widx = {w: i for i, w in enumerate(weeks)}
def week_end_commit(w):
    end = dt.datetime.combine(w + dt.timedelta(days=6), dt.time(23, 59, 59))
    for h, d, s in fp:
        if d <= end:
            return h
endc = [week_end_commit(w) for w in weeks]
log["weeks"] = len(weeks); log["week_first"] = str(weeks[0]); log["week_last"] = str(weeks[-1])

# ---- fix rule
items = {}
for l in open(H + "/gh/items.jsonl"):
    x = json.loads(l)
    if x.get("pr"): items[x["n"]] = x
fixre = re.compile(r"^(fix|bugfix)\b", re.I)
prre = re.compile(r"\(#(\d+)\)\s*$")
def is_fix(h):
    s = allc[h][1]
    if fixre.match(s): return True
    if h in fpset:
        m = prre.search(s)
        if m and int(m.group(1)) in items and "bug" in items[int(m.group(1))]["labels"]: return True
    return False
fixflag = {h: is_fix(h) for h in allc}
log["fix_commits_all"] = sum(fixflag.values())
log["fix_commits_by_subject"] = sum(1 for h in allc if fixre.match(allc[h][1]))

# ---- touches: (canon path, week) -> [fix, all]
cache = json.load(gzip.open(H + "/evolution_real/cache/diff_gitgalaxy-engine_de3c170c426c97d9.json.gz"))
log["diff_cache_commits"] = len(cache)
log["diff_cache_commits_not_in_git_log"] = sum(1 for h in cache if h not in allc)
touch = collections.defaultdict(lambda: [0, 0])
ntouch_total = 0
for h, v in cache.items():
    if h not in allc: continue
    wi = widx.get(wk(allc[h][0]))
    if wi is None: continue
    seen = set()
    for p, f in v["funcs"]:
        p = canon(p)
        if not is_engine(p) or (p, f) in seen: continue
        seen.add((p, f))
        t = touch[(p, wi)]; t[1] += 1; t[0] += fixflag[h]; ntouch_total += 1
log["engine_function_touches"] = ntouch_total
log["engine_file_weeks_with_touches_any_file"] = len(touch)

# ---- tests & imports
proc = subprocess.Popen(["git", "--git-dir=" + M, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
def blob(b):
    proc.stdin.write((b + "\n").encode()); proc.stdin.flush()
    hdr = proc.stdout.readline().split()
    n = int(hdr[2]); d = proc.stdout.read(n); proc.stdout.read(1); return d
impcache = {}
def imports(b):
    if b in impcache: return impcache[b]
    recs = []
    try:
        tree = ast.parse(blob(b).decode("utf-8", "replace"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names: recs.append(("i", a.name, None))
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                recs.append(("f", n.module, [a.name for a in n.names]))
        ok = True
    except Exception:
        ok = False
    impcache[b] = (ok, recs)
    return impcache[b]
def cm(m):
    return "gitgalaxy." + m[len("backend."):] if m.startswith("backend.") else m

snap = []  # per week: dict(files=set(engine paths), att={path: set(tests)})
parse_fail = 0; tests_zero_resolved = []
for i, c in enumerate(endc):
    files = set(); tests = []
    for l in git("ls-tree", "-r", c).splitlines():
        meta, p = l.split("\t", 1)
        b = meta.split()[2]
        if p.endswith(".py"):
            if p.startswith("tests/"): tests.append((p, b))
            elif is_engine(p): files.add(canon(p))
    mods = {f[:-3].replace("/", "."): f for f in files}
    att = collections.defaultdict(set); nzero = 0; nfail = 0
    for p, b in tests:
        ok, recs = imports(b)
        if not ok: nfail += 1; continue
        hit = False
        for kind, m, names in recs:
            m = cm(m)
            if kind == "i":
                if m in mods: att[mods[m]].add(p); hit = True
            else:
                for x in names:
                    if x != "*" and (m + "." + x) in mods: att[mods[m + "." + x]].add(p); hit = True
                    elif m in mods: att[mods[m]].add(p); hit = True
        if not hit: nzero += 1
    snap.append(dict(files=files, att={k: len(v) for k, v in att.items()}, ntests=len(tests), nfail=nfail, nzero=nzero))
log["snapshots"] = [dict(week=str(weeks[i]), commit=endc[i][:10], engine_files=len(s["files"]), test_files=s["ntests"],
                         tests_unparsable=s["nfail"], tests_resolving_to_no_engine_file=s["nzero"],
                         files_attached=sum(1 for f in s["files"] if s["att"].get(f, 0) >= 1)) for i, s in enumerate(snap)]

# ---- birth dates
birth = {}
cur = None
for l in git("log", "--no-merges", "--no-renames", "--diff-filter=A", "--name-only", "--format=@@%cI", TIP).split("\n"):
    if l.startswith("@@"): cur = utc(l[2:])
    elif l.strip() and is_engine(l):
        p = canon(l.strip()); birth[p] = min(birth.get(p, cur), cur)
root_day = first_day

# ---- sizes from daily scans
picks = [l.split("\t") for l in open(H + "/picks.tsv").read().split("\n") if l.strip()]
scan = {}
for d, sha in picks:
    con = sqlite3.connect(f"file:{H}/dbs/{d}_{sha[:10]}.db?mode=ro&immutable=1", uri=True)
    scan[d] = {}
    for p, loc in con.execute("select file_path, coding_loc from file_data"):
        if is_engine(p): scan[d][canon(p)] = loc
    con.close()
scand = sorted(scan)
def size_at(path, i):
    day = str(weeks[i] + dt.timedelta(days=6))
    k = bisect.bisect_right(scand, day) - 1
    return scan[scand[k]].get(path) if k >= 0 else None
log["scan_days"] = len(scand)

pickle.dump(dict(weeks=weeks, endc=endc, snap=snap, touch=dict(touch), birth=birth, root_day=root_day,
                 size={(p, i): size_at(p, i) for i in range(len(weeks)) for p in snap[i]["files"]}, log=log), open(OUT + "/derived.pkl", "wb"))
json.dump(log, open(OUT + "/build_log.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in log.items() if k != "snapshots"}, indent=1, default=str))
