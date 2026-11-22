import re, sys, sqlite3, subprocess, pickle, os, math, random
from collections import defaultdict, Counter
import numpy as np
import networkx as nx

S = __import__("os").environ.get("FIXGRAPH_WORK", "/tmp/fixgraph-work")  # work dir: repos/<n>, src/<n>, scan/, scan2/
rng = np.random.default_rng(23); random.seed(23)
GEN = re.compile(r"\b(fix(es|ed)?|bug|regression)\b", re.I)
MEM = re.compile(r"(leak|free[sd]?\b|freeing|uaf|use[- ]after|overflow|heap|stack|oob|out[- ]of[- ]bounds|null[- ]?(ptr|pointer|deref)|double|memory|alloc|dangling|refcount|ref[- ]count)", re.I)
DEFS = {"B": lambda s: bool(GEN.search(s)) and not MEM.search(s), "D": lambda s: True}
KW = {"if", "for", "while", "switch", "catch", "synchronized", "new", "return", "func", "sizeof", "defined", "else", "do"}
LANGPATH = {"C": ["*.c", "*.h"], "Go": ["*.go"], "Java": ["*.java"]}
ATTR = f"{S}/gitattrs"
open(ATTR, "w").write("*.go diff=golang\n*.java diff=java\n")
ID = re.compile(r"([A-Za-z_$][A-Za-z0-9_$]*)\s*\(")
GORECV = re.compile(r"^\s*func\s*(\([^)]*\)\s*)?")


def funcname(lang, hdr):
    if lang == "Go":
        hdr = GORECV.sub("", hdr, count=1)
    for m in ID.finditer(hdr):
        if m.group(1) not in KW:
            return m.group(1)
    return None


def mine(name, lang):
    cp = f"{S}/cache2_{name}.pkl"
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    db = sqlite3.connect(f"{S}/scan2/{name}/{name}_galaxy_master.db")
    fid2path = {i: p for i, p in db.execute("select id,file_path from file_data")}
    byname = defaultdict(list)
    for i, fi, n in db.execute("select id,file_id,func_name from function_data"):
        if fi in fid2path:
            byname[(fid2path[fi], n)].append(i)
    paths = set(fid2path.values())
    out = subprocess.run(["git", "-c", f"core.attributesFile={ATTR}", "-C", f"{S}/repos/{name}", "log", "--no-merges", "-U0",
                          "--since=2021-01-01", "--format=@@C\t%H\t%s", "-p", "--"] + LANGPATH[lang],
                         capture_output=True, text=True, errors="replace").stdout
    commits = []; cur = None; curfile = None
    hunk = re.compile(r"^@@ [^@]*@@\s*(.*)$")
    for line in out.splitlines():
        if line.startswith("@@C\t"):
            _, h, subj = line.split("\t", 2)
            cur = dict(subj=subj, files=set(), funcs=set()); commits.append(cur); curfile = None
        elif line.startswith("+++ b/"):
            curfile = line[6:]
            if cur is not None and curfile in paths:
                cur["files"].add(curfile)
        elif line.startswith("@@") and cur is not None and curfile in paths:
            m = hunk.match(line)
            if m:
                f = funcname(lang, m.group(1))
                if f and (curfile, f) in byname:
                    cur["funcs"].update(byname[(curfile, f)])
    pickle.dump(commits, open(cp, "wb"))
    return commits


def load(name):
    db = sqlite3.connect(f"{S}/scan2/{name}/{name}_galaxy_master.db")
    fid2path = {i: p for i, p in db.execute("select id,file_path from file_data")}
    funcs = {}
    for i, fi, n, cx, loc in db.execute("select id,file_id,func_name,complexity,loc from function_data"):
        if fi in fid2path:
            funcs[i] = dict(file=fid2path[fi], name=n, cx=cx or 0, loc=loc or 0)
    G = nx.DiGraph()
    for s, d in db.execute("select src_func_id,dst_func_id from fcall_data where dst_func_id is not null and src_func_id is not null"):
        if s in funcs and d in funcs and s != d:
            G.add_edge(s, d)
    return funcs, G


def rank(x):
    x = np.asarray(x, float); o = x.argsort(kind="mergesort"); r = np.empty(len(x)); r[o] = np.arange(len(x))
    for v in np.unique(x):
        m = x == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r


def partial(a, b, ctrl):
    ra, rb = rank(a), rank(b)
    X = np.column_stack([np.ones(len(ra))] + [rank(c) for c in ctrl])
    ea = ra - X @ np.linalg.lstsq(X, ra, rcond=None)[0]; eb = rb - X @ np.linalg.lstsq(X, rb, rcond=None)[0]
    return float(np.corrcoef(ea, eb)[0, 1])


def poisson_mu(y, X):
    beta = np.zeros(X.shape[1]); beta[0] = math.log(max(y.mean(), 1e-6))
    for _ in range(30):
        mu = np.exp(X @ beta); z = X @ beta + (y - mu) / np.maximum(mu, 1e-9)
        beta = np.linalg.solve(X.T @ (X * mu[:, None]) + 1e-6 * np.eye(X.shape[1]), X.T @ (mu * z))
    return np.exp(X @ beta)


H = 8


def analyse(name, lang, defname):
    commits = mine(name, lang); funcs, G = load(name)
    isfix = DEFS[defname]
    ids = [f for f in funcs if f in G]
    ft = Counter(); nfix = 0; fixfuncs = []
    for c in commits:
        if isfix(c["subj"]):
            nfix += 1
            fs = [f for f in c["funcs"] if f in G]
            for f in fs:
                ft[f] += 1
            fixfuncs.append(fs)
    y = np.array([ft[f] for f in ids], float)
    r = dict(name=name, lang=lang, n_commits=len(commits), n_fix=nfix, n_funcs=len(ids), touches=int(y.sum()))
    if y.sum() < 30 or len(ids) < 100:
        r["skip"] = True; return r
    X = np.column_stack([np.ones(len(ids)), np.log1p([funcs[f]["loc"] for f in ids]), np.log1p([funcs[f]["cx"] for f in ids])])
    mu = poisson_mu(y, X)
    fin = np.array([G.in_degree(f) for f in ids]); fout = np.array([G.out_degree(f) for f in ids])
    tot = fin + fout; ratio = np.where(tot > 0, fin / np.maximum(tot, 1), 0.0)
    p90o = np.percentile(fout, 90); p90i = np.percentile(fin, 90)
    cls = {
        "orchestrator (8)": (fin < H) & (fout >= H),
        "orchestrator (pctile)": (fout >= max(p90o, 3)) & (fin < max(p90i, 1)),
        "utility": (fin >= H) & (fout < H),
        "hub": (fin >= H) & (fout >= H),
        "consumer-ish": (tot >= 3) & (ratio < 0.2),
        "intermediate": (tot >= 3) & (ratio >= 0.2) & (ratio <= 0.8),
        "producer-ish": (tot >= 3) & (ratio > 0.8),
    }
    r["cls"] = {}
    for k, m in cls.items():
        idx = np.where(m)[0]; O = float(y[m].sum()); E = float(mu[m].sum())
        if len(idx) < 8 or E < 3:
            r["cls"][k] = dict(n=int(len(idx)), skip=True); continue
        bs = []
        for _ in range(200):
            s = rng.choice(idx, len(idx)); bs.append(math.log((y[s].sum() + .5) / (mu[s].sum() + .5)))
        r["cls"][k] = dict(n=int(len(idx)), O=O, E=E, lift=O / E, L=math.log((O + .5) / (E + .5)), se=float(np.std(bs)))
    loc = X[:, 1]; cx = X[:, 2]
    r["fanout_partial"] = partial(y, fout, [loc, cx]); r["fanin_partial"] = partial(y, fin, [loc, cx])
    # ---- fix radius with directory-matched null
    pool = [f for f in ft if f in G]
    bydir = defaultdict(list); byfile = defaultdict(list)
    for f in pool:
        byfile[funcs[f]["file"]].append(f); bydir[os.path.dirname(funcs[f]["file"])].append(f)
    pairs = []
    for fs in fixfuncs:
        fs = list(dict.fromkeys(fs))
        if 2 <= len(fs) <= 12:
            for i in range(len(fs)):
                for j in range(i + 1, len(fs)):
                    pairs.append((fs[i], fs[j]))
    random.shuffle(pairs); pairs = pairs[:2500]
    U = G.to_undirected(); cache = {}
    def near(a, b):
        if a not in cache:
            cache[a] = nx.single_source_shortest_path_length(U, a, cutoff=2)
        return b in cache[a]
    obs = nul = 0; nn = 0
    for a, b in pairs:
        obs += near(a, b)
        same = funcs[a]["file"] == funcs[b]["file"]
        cand = byfile[funcs[b]["file"]] if same else bydir[os.path.dirname(funcs[b]["file"])]
        cand = [c for c in cand if c != a and c != b]
        if not cand:
            continue
        for _ in range(3):
            nul += near(a, random.choice(cand)); nn += 1
    r["radius"] = dict(pairs=len(pairs), obs=obs / max(1, len(pairs)), null=nul / max(1, nn)) if len(pairs) >= 100 and nn >= 100 else dict(pairs=len(pairs))
    return r


def re_pool(items):
    # DerSimonian-Laird random effects over (L, se)
    L = np.array([i[0] for i in items]); se = np.array([max(i[1], 0.02) for i in items]); w = 1 / se ** 2
    k = len(L)
    fe = (w * L).sum() / w.sum(); Q = (w * (L - fe) ** 2).sum()
    c = w.sum() - (w ** 2).sum() / w.sum(); tau2 = max(0.0, (Q - (k - 1)) / c) if k > 1 else 0.0
    ws = 1 / (se ** 2 + tau2); m = (ws * L).sum() / ws.sum(); s = 1 / math.sqrt(ws.sum())
    I2 = max(0.0, (Q - (k - 1)) / Q) if Q > 0 and k > 1 else 0.0
    return math.exp(m), math.exp(m - 1.96 * s), math.exp(m + 1.96 * s), I2, k


if __name__ == "__main__":
    defname = sys.argv[1]
    repos = [l.split() for l in open(f"{S}/ext_repos.txt")]
    res = []
    for lang, r in repos:
        n = r.split("/")[1]
        a = analyse(n, lang, defname); res.append(a)
        if a.get("skip"):
            print(f"{lang:4s} {n:17s} SKIPPED (touches={a['touches']} funcs={a['n_funcs']})"); continue
        rd = a["radius"]
        rr = f"radius {100*rd['obs']:.0f}% vs dir-null {100*rd['null']:.0f}% ({rd['obs']/max(rd['null'],1e-9):.1f}x, n={rd['pairs']})" if "obs" in rd else f"radius n={rd['pairs']} (too few)"
        o = a["cls"]["orchestrator (8)"]; c = a["cls"]["consumer-ish"]; p = a["cls"]["producer-ish"]
        f = lambda d: f"{d['lift']:.2f}x(n={d['n']})" if "lift" in d else f"-(n={d['n']})"
        print(f"{lang:4s} {n:17s} commits={a['n_commits']:5d} fix={a['n_fix']:5d} funcs={a['n_funcs']:5d} | orch {f(o)} cons {f(c)} prod {f(p)} | fanout_rho {a['fanout_partial']:+.2f} | {rr}")
    print(f"\n==== POOLED (def {defname}), random effects (DerSimonian-Laird); I2 = between-repo heterogeneity")
    for stratum in ("C", "Go", "Java", "ALL"):
        rs = [a for a in res if not a.get("skip") and (stratum == "ALL" or a["lang"] == stratum)]
        print(f"-- {stratum}: {len(rs)} repos")
        for k in ("orchestrator (8)", "orchestrator (pctile)", "utility", "hub", "consumer-ish", "intermediate", "producer-ish"):
            it = [(a["cls"][k]["L"], a["cls"][k]["se"]) for a in rs if "L" in a["cls"][k]]
            if len(it) < 2:
                print(f"   {k:24s} too few repos ({len(it)})"); continue
            m, lo, hi, I2, kk = re_pool(it)
            pos = sum(1 for a in rs if "lift" in a["cls"][k] and a["cls"][k]["lift"] > 1)
            print(f"   {k:24s} {m:4.2f}x ({lo:.2f}-{hi:.2f}){'*' if (lo>1 or hi<1) else ' '} I2={I2:.2f} repos={kk} lift>1 in {pos}/{kk}")
        fo = [a["fanout_partial"] for a in rs]
        fi = [a["fanin_partial"] for a in rs]
        print(f"   fan-out partial rho: median {np.median(fo):+.2f}, positive in {sum(1 for x in fo if x>0)}/{len(fo)};   fan-in partial rho: median {np.median(fi):+.2f}, positive in {sum(1 for x in fi if x>0)}/{len(fi)}")
        rd = [a["radius"] for a in rs if "obs" in a["radius"]]
        lifts = [d["obs"] / max(d["null"], 1e-9) for d in rd]
        if rd:
            print(f"   fix radius vs directory-matched null: median lift {np.median(lifts):.1f}x, >=1.5x in {sum(1 for x in lifts if x>=1.5)}/{len(lifts)} repos (min {min(lifts):.1f}x, max {max(lifts):.1f}x)")
