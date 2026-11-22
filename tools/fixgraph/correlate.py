import re, sys, sqlite3, subprocess, random, math
from collections import defaultdict, Counter
import numpy as np
import networkx as nx

S = __import__("os").environ.get("FIXGRAPH_WORK", "/tmp/fixgraph-work")  # work dir: repos/<n>, src/<n>, scan/, scan2/
name = sys.argv[1]
rng = np.random.default_rng(7)
random.seed(7)

FIX = re.compile(r"\b(fix(es|ed)?|bug|cve-\d|crash|overflow|leak|use[- ]after|uaf|segfault|regression|out[- ]of[- ]bounds|oob|null[- ]?deref|double[- ]free|heap|stack)\b", re.I)

db = sqlite3.connect(f"{S}/scan/{name}/{name}_galaxy_master.db")
files = {}  # path -> dict
for fid, p, loc, bc, pr, br in db.execute("select id,file_path,coding_loc,betweenness_score,pagerank_score,normalized_blast_radius from file_data"):
    files[p] = dict(id=fid, loc=loc or 0, bc=bc, pr=pr, br=br)
fid2path = {v["id"]: k for k, v in files.items()}
funcs = {}  # id -> dict
byname = defaultdict(list)
for i, fi, n, cx, loc, fin, fout in db.execute("select id,file_id,func_name,complexity,loc,func_fan_in,func_fan_out from function_data"):
    p = fid2path.get(fi)
    if p is None:
        continue
    funcs[i] = dict(file=p, name=n, cx=cx or 0, loc=loc or 0, fin=fin or 0, fout=fout or 0)
    byname[(p, n)].append(i)

# ---- mine history
out = subprocess.run(["git", "-C", f"{S}/repos/{name}", "log", "--no-merges", "-U0", "--since=2021-01-01",
                      "--format=@@C\t%H\t%s", "-p", "--", "*.c", "*.h"], capture_output=True, text=True, errors="replace").stdout
commits = []  # dict(fix, files:set, funcs:set)
cur = None
curfile = None
hunk_re = re.compile(r"^@@ [^@]*@@\s*(.*)$")
fn_re = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
for line in out.splitlines():
    if line.startswith("@@C\t"):
        _, h, subj = line.split("\t", 2)
        cur = dict(fix=bool(FIX.search(subj)), files=set(), funcs=set())
        commits.append(cur)
        curfile = None
    elif line.startswith("+++ b/"):
        curfile = line[6:]
        if cur is not None and curfile in files:
            cur["files"].add(curfile)
    elif line.startswith("@@") and cur is not None and curfile in files:
        m = hunk_re.match(line)
        if m:
            f = fn_re.search(m.group(1))
            if f and (curfile, f.group(1)) in byname:
                for fi in byname[(curfile, f.group(1))]:
                    cur["funcs"].add(fi)
nfix = sum(c["fix"] for c in commits)
print(f"### {name}: {len(files)} files, {len(funcs)} funcs, {len(commits)} commits (touching .c/.h), {nfix} fix-like ({100*nfix/max(1,len(commits)):.0f}%)")

# ---- stats helpers
def rank(x):
    x = np.asarray(x, float)
    o = x.argsort(kind="mergesort")
    r = np.empty(len(x)); r[o] = np.arange(len(x))
    # average ties
    for v in np.unique(x):
        m = x == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r

def spearman(a, b):
    return float(np.corrcoef(rank(a), rank(b))[0, 1])

def partial(a, b, ctrl):
    ra, rb = rank(a), rank(b)
    X = np.column_stack([np.ones(len(ra))] + [rank(c) for c in ctrl])
    ea = ra - X @ np.linalg.lstsq(X, ra, rcond=None)[0]
    eb = rb - X @ np.linalg.lstsq(X, rb, rcond=None)[0]
    return float(np.corrcoef(ea, eb)[0, 1])

def perm_p(stat, a, b, ctrl, n=500):
    base = stat(a, b, ctrl)
    ge = 0
    for _ in range(n):
        if abs(stat(a, rng.permutation(b), ctrl)) >= abs(base):
            ge += 1
    return base, (ge + 1) / (n + 1)

# ---- FILE LEVEL
fc_fix = Counter(); fc_all = Counter()
for c in commits:
    for p in c["files"]:
        fc_all[p] += 1
        if c["fix"]:
            fc_fix[p] += 1
rows = [(p, v) for p, v in files.items() if v["bc"] is not None and fc_all[p] >= 3 and v["loc"] > 0]
print(f"\n[file-level] n={len(rows)} files with >=3 commits")
if len(rows) > 30:
    fix = np.array([fc_fix[p] for p, _ in rows]); allc = np.array([fc_all[p] for p, _ in rows])
    loc = np.array([v["loc"] for _, v in rows])
    for metric in ("bc", "pr", "br"):
        m = np.array([v[metric] or 0 for _, v in rows])
        raw = spearman(fix, m)
        # partial controlling for LOC only, and for LOC + total commits
        p1, pv1 = perm_p(lambda a, b, c: partial(a, b, c), fix, m, [loc], 300)
        # fix-share controlling LOC
        share = fix / allc
        p2, pv2 = perm_p(lambda a, b, c: partial(a, b, c), share, m, [loc, allc], 300)
        print(f"  {metric}: raw rho(fix_count, {metric})={raw:+.2f}   partial|LOC={p1:+.2f} (p={pv1:.3f})   rho(fix_share,{metric})|LOC,commits={p2:+.2f} (p={pv2:.3f})")
    print("  size baseline: rho(fix_count, LOC)=%+.2f, rho(fix_count, total commits)=%+.2f" % (spearman(fix, loc), spearman(fix, allc)))

# ---- FUNCTION GRAPH
G = nx.DiGraph()
for s, d in db.execute("select src_func_id,dst_func_id from fcall_data where dst_func_id is not null and src_func_id is not null"):
    if s in funcs and d in funcs and s != d:
        G.add_edge(s, d)
U = G.to_undirected()
k = min(800, G.number_of_nodes())
bcf = nx.betweenness_centrality(G, k=k, seed=3) if G.number_of_nodes() else {}
sccs = [c for c in nx.strongly_connected_components(G) if len(c) > 1]
in_cycle = set().union(*sccs) if sccs else set()
print(f"\n[function graph] {G.number_of_nodes()} nodes in graph, {G.number_of_edges()} edges, {len(sccs)} multi-function cycles ({len(in_cycle)} funcs)")

ft = Counter()
for c in commits:
    if c["fix"]:
        for f in c["funcs"]:
            ft[f] += 1
touched = sum(1 for f in funcs if ft[f] > 0)
print(f"  funcs touched by >=1 fix commit: {touched}/{len(funcs)}")

ids = [f for f in funcs if f in G]
if len(ids) > 50:
    y = np.array([ft[f] for f in ids]); loc = np.array([funcs[f]["loc"] for f in ids]); cx = np.array([funcs[f]["cx"] for f in ids])
    print("  size baseline: rho(fix_touches, LOC)=%+.2f, rho(fix_touches, complexity)=%+.2f" % (spearman(y, loc), spearman(y, cx)))
    for label, vec in (("betweenness", [bcf.get(f, 0) for f in ids]), ("fan_in", [funcs[f]["fin"] for f in ids]),
                       ("fan_out", [funcs[f]["fout"] for f in ids])):
        v = np.array(vec)
        raw = spearman(y, v)
        p, pv = perm_p(lambda a, b, c: partial(a, b, c), y, v, [loc, cx], 300)
        print(f"  {label}: raw rho={raw:+.2f}   partial|LOC,complexity={p:+.2f} (p={pv:.3f})")
    # enrichment of top-5% betweenness
    b = np.array([bcf.get(f, 0) for f in ids]); thr = np.quantile(b, 0.95); top = b >= thr
    print(f"  top-5% betweenness funcs: {top.sum()} funcs = {100*loc[top].sum()/loc.sum():.0f}% of LOC, receive {100*y[top].sum()/max(1,y.sum()):.0f}% of fix touches")
    for label, mask in (("in a cycle", np.array([f in in_cycle for f in ids])),):
        if mask.sum() >= 5:
            print(f"  cycle members: {mask.sum()} funcs = {100*loc[mask].sum()/loc.sum():.1f}% of LOC, receive {100*y[mask].sum()/max(1,y.sum()):.1f}% of fix touches; mean touches {y[mask].mean():.2f} vs {y[~mask].mean():.2f}")

# ---- CO-CHANGE LOCALITY
CUT = 4
pool = [f for f in ft if f in U]
pairs = []
for c in commits:
    if not c["fix"]:
        continue
    fs = [f for f in c["funcs"] if f in U]
    if 2 <= len(fs) <= 12:
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                pairs.append((fs[i], fs[j]))
def dist(a, b):
    try:
        return nx.shortest_path_length(U, a, b) if nx.has_path(U, a, b) else 99
    except Exception:
        return 99
def near(pr, cross_only=False):
    n = t = 0
    for a, b in pr:
        if cross_only and funcs[a]["file"] == funcs[b]["file"]:
            continue
        t += 1
        # bounded BFS
        d = nx.single_source_shortest_path_length(U, a, cutoff=CUT) if False else None
        n += 1 if _within(a, b) else 0
    return n, t
_cache = {}
def _within(a, b):
    if a not in _cache:
        _cache[a] = nx.single_source_shortest_path_length(U, a, cutoff=CUT)
    return b in _cache[a] and _cache[a][b] <= 2
print(f"\n[co-change locality] {len(pairs)} function pairs changed together in one fix commit (<=12 funcs per commit)")
if len(pairs) >= 30 and len(pool) >= 30:
    random.shuffle(pairs)
    pairs = pairs[:3000]
    for label, cross in (("all pairs", False), ("cross-file pairs only", True)):
        pp = [(a, b) for a, b in pairs if not cross or funcs[a]["file"] != funcs[b]["file"]]
        if len(pp) < 20:
            print(f"  {label}: too few ({len(pp)})")
            continue
        hit = sum(_within(a, b) for a, b in pp) / len(pp)
        nulls = []
        for _ in range(5):
            nn = []
            while len(nn) < len(pp):
                a, b = random.sample(pool, 2)
                if cross and funcs[a]["file"] == funcs[b]["file"]:
                    continue
                nn.append((a, b))
            nulls.append(sum(_within(a, b) for a, b in nn) / len(nn))
        print(f"  {label}: n={len(pp)}  within 2 call hops: {100*hit:.1f}%   null (random fix-touched pairs): {100*np.mean(nulls):.1f}% (range {100*min(nulls):.1f}-{100*max(nulls):.1f})   lift x{hit/max(1e-9,np.mean(nulls)):.1f}")
