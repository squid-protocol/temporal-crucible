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


# ---- QUADRANT GRID
ids = [f for f in funcs if f in G]
fin = {f: G.in_degree(f) for f in ids}; fout = {f: G.out_degree(f) for f in ids}
ftc = Counter(); callers_co = defaultdict(list)
for c in commits:
    if c["fix"]:
        for f in c["funcs"]:
            if f in G:
                ftc[f] += 1
y = np.array([ftc[f] for f in ids], float)
X = np.column_stack([np.ones(len(ids)), np.log1p([funcs[f]["loc"] for f in ids]), np.log1p([funcs[f]["cx"] for f in ids])])
# Poisson IRLS: expected fix touches from size+complexity only
beta = np.zeros(X.shape[1]); beta[0] = math.log(max(y.mean(), 1e-6))
for _ in range(30):
    mu = np.exp(X @ beta); W = mu
    z = X @ beta + (y - mu) / np.maximum(mu, 1e-9)
    A = X.T @ (X * W[:, None]) + 1e-6 * np.eye(X.shape[1])
    beta = np.linalg.solve(A, X.T @ (W * z))
mu = np.exp(X @ beta)
H = 8
q = {}
for k, f in enumerate(ids):
    q[f] = ("hiIN" if fin[f] >= H else "loIN") + "/" + ("hiOUT" if fout[f] >= H else "loOUT")
names = {"hiIN/loOUT": "utility (high in, low out)", "loIN/hiOUT": "orchestrator (low in, high out)",
         "hiIN/hiOUT": "hub (high in, high out)", "loIN/loOUT": "ordinary (low/low)"}
print(f"\n[grid, threshold={H}] {len(ids)} funcs; size-adjusted = observed fixes / fixes predicted from LOC+complexity")
print(f"  {'quadrant':36s} {'n':>6s} {'LOC':>6s} {'cx':>5s} {'fix/func':>8s} {'%touched':>8s} {'share_of_fixes':>14s} {'adj. lift (95% CI)':>22s}")
tot = y.sum()
for key in ("loIN/loOUT", "hiIN/loOUT", "loIN/hiOUT", "hiIN/hiOUT"):
    m = np.array([q[f] == key for f in ids])
    if m.sum() < 5:
        print(f"  {names[key]:36s} {m.sum():6d}  (too few)"); continue
    lift = y[m].sum() / mu[m].sum()
    bs = []
    idx = np.where(m)[0]
    for _ in range(300):
        s = rng.choice(idx, len(idx)); bs.append(y[s].sum() / mu[s].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"  {names[key]:36s} {m.sum():6d} {X[m,1].mean() and np.mean([funcs[f]['loc'] for f,mm in zip(ids,m) if mm]):6.0f} {np.mean([funcs[f]['cx'] for f,mm in zip(ids,m) if mm]):5.1f} {y[m].mean():8.2f} {100*(y[m]>0).mean():7.0f}% {100*y[m].sum()/tot:13.0f}% {lift:9.2f}x ({lo:.2f}-{hi:.2f})")
# top excess functions in the orchestrator and hub quadrants
for key in ("loIN/hiOUT", "hiIN/hiOUT"):
    cand = [(y[k] - mu[k], ids[k]) for k in range(len(ids)) if q[ids[k]] == key]
    cand.sort(reverse=True)
    print(f"\n  most fixes beyond size-expectation in {names[key]}: (excess | fixes | in | out | loc)")
    for ex, f in cand[:5]:
        print(f"    {ex:5.1f} | {ftc[f]:2d} | {fin[f]:3d} | {fout[f]:3d} | {funcs[f]['loc']:4d} | {funcs[f]['file']}::{funcs[f]['name']}")
