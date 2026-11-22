import re, sys, sqlite3, subprocess, pickle, os, math, json
from collections import defaultdict, Counter
import numpy as np
import networkx as nx

S = __import__("os").environ.get("FIXGRAPH_WORK", "/tmp/fixgraph-work")  # work dir: repos/<n>, src/<n>, scan/, scan2/
SCAN = os.environ.get("SCAN", "scan")
rng = np.random.default_rng(11)

ORIG = re.compile(r"\b(fix(es|ed)?|bug|cve-\d|crash|overflow|leak|use[- ]after|uaf|segfault|regression|out[- ]of[- ]bounds|oob|null[- ]?deref|double[- ]free|heap|stack)\b", re.I)
GEN = re.compile(r"\b(fix(es|ed)?|bug|regression)\b", re.I)
MEM = re.compile(r"(leak|free[sd]?\b|freeing|uaf|use[- ]after|overflow|heap|stack|oob|out[- ]of[- ]bounds|null[- ]?(ptr|pointer|deref)|double|memory|alloc|dangling|refcount|ref[- ]count)", re.I)
DEFS = {
    "orig": lambda s: bool(ORIG.search(s)),
    "B(no-memory)": lambda s: bool(GEN.search(s)) and not MEM.search(s),
    "D(any commit)": lambda s: True,
}
LIFE = re.compile(r"(free|close|destroy|cleanup|clean_up|finali[sz]e|shutdown|teardown|release|done|disconnect|unlink|remove|del(ete)?)", re.I)


def mine(name):
    cp = f"{S}/cache_{name}.pkl" if SCAN == "scan" else f"{S}/cache_{SCAN}_{name}.pkl"
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    db = sqlite3.connect(f"{S}/{SCAN}/{name}/{name}_galaxy_master.db")
    fid2path = {i: p for i, p in db.execute("select id,file_path from file_data")}
    byname = defaultdict(list)
    for i, fi, n in db.execute("select id,file_id,func_name from function_data"):
        if fi in fid2path:
            byname[(fid2path[fi], n)].append(i)
    paths = set(fid2path.values())
    out = subprocess.run(["git", "-C", f"{S}/repos/{name}", "log", "--no-merges", "-U0", "--since=2021-01-01",
                          "--format=@@C\t%H\t%s", "-p", "--", "*.c", "*.h"],
                         capture_output=True, text=True, errors="replace").stdout
    commits = []; cur = None; curfile = None
    hunk = re.compile(r"^@@ [^@]*@@\s*(.*)$"); fn = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
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
                f = fn.search(m.group(1))
                if f and (curfile, f.group(1)) in byname:
                    cur["funcs"].update(byname[(curfile, f.group(1))])
    pickle.dump(commits, open(cp, "wb"))
    return commits


def load(name):
    db = sqlite3.connect(f"{S}/{SCAN}/{name}/{name}_galaxy_master.db")
    files = {p: dict(loc=l or 0, pr=r if r is not None else 0.0, role=ro) for p, l, r, ro in
             db.execute("select file_path,coding_loc,producer_ratio,ecosystem_role from file_data")}
    fid2path = {i: p for i, p in db.execute("select id,file_path from file_data")}
    funcs = {}
    for i, fi, n, cx, loc in db.execute("select id,file_id,func_name,complexity,loc from function_data"):
        if fi in fid2path:
            funcs[i] = dict(file=fid2path[fi], name=n, cx=cx or 0, loc=loc or 0)
    G = nx.DiGraph()
    for s, d in db.execute("select src_func_id,dst_func_id from fcall_data where dst_func_id is not null and src_func_id is not null"):
        if s in funcs and d in funcs and s != d:
            G.add_edge(s, d)
    return files, funcs, G


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


def classes(funcs, G, ids):
    fin = np.array([G.in_degree(f) for f in ids]); fout = np.array([G.out_degree(f) for f in ids])
    life = np.array([bool(LIFE.search(funcs[f]["name"])) for f in ids])
    tot = fin + fout; ratio = np.where(tot > 0, fin / np.maximum(tot, 1), 0.0)
    c = {
        "orchestrator (in<8,out>=8)": (fin < H) & (fout >= H),
        "utility (in>=8,out<8)": (fin >= H) & (fout < H),
        "hub (in>=8,out>=8)": (fin >= H) & (fout >= H),
        "lifecycle-named (all)": life,
        "lifecycle & in>=8": life & (fin >= H),
        "lifecycle & out>=5": life & (fout >= 5),
        "consumer-ish ratio<0.2 (tot>=3)": (tot >= 3) & (ratio < 0.2),
        "intermediate 0.2-0.8 (tot>=3)": (tot >= 3) & (ratio >= 0.2) & (ratio <= 0.8),
        "producer-ish ratio>0.8 (tot>=3)": (tot >= 3) & (ratio > 0.8),
    }
    return c, fin, fout


def analyse(name, defname, half, commits, files, funcs, G):
    n = len(commits); mid = n // 2
    cs = commits if half == "all" else (commits[:mid] if half == "new" else commits[mid:])
    isfix = DEFS[defname]
    ids = [f for f in funcs if f in G]
    ft = Counter(); ffile = Counter(); fall = Counter()
    nfix = 0
    for c in cs:
        fx = isfix(c["subj"])
        nfix += fx
        for p in c["files"]:
            fall[p] += 1
            if fx:
                ffile[p] += 1
        if fx:
            for f in c["funcs"]:
                if f in G:
                    ft[f] += 1
    y = np.array([ft[f] for f in ids], float)
    X = np.column_stack([np.ones(len(ids)), np.log1p([funcs[f]["loc"] for f in ids]), np.log1p([funcs[f]["cx"] for f in ids])])
    mu = poisson_mu(y, X)
    cl, fin, fout = classes(funcs, G, ids)
    res = {"n_commits": len(cs), "n_fix": int(nfix), "n_funcs": len(ids), "touches": int(y.sum()), "cls": {}}
    for k, m in cl.items():
        res["cls"][k] = (int(m.sum()), float(y[m].sum()), float(mu[m].sum()), np.where(m)[0].tolist())
    res["_y"] = y; res["_mu"] = mu
    loc = X[:, 1]; cx = X[:, 2]
    res["fanout_partial"] = partial(y, fout, [loc, cx]) if y.sum() > 20 else float("nan")
    res["fanin_partial"] = partial(y, fin, [loc, cx]) if y.sum() > 20 else float("nan")
    # file-level producer/consumer
    frows = [(p, v) for p, v in files.items() if v["loc"] > 0 and fall[p] > 0]
    if frows and defname != "D(any commit)":
        fy = np.array([ffile[p] for p, _ in frows], float)
        fX = np.column_stack([np.ones(len(frows)), np.log1p([v["loc"] for _, v in frows])])
        fmu = poisson_mu(fy, fX)
        pr = np.array([v["pr"] for _, v in frows]); role = [v["role"] for _, v in frows]
        fc = {}
        for label, m in (("file consumer (<0.2)", np.array([r == "Pure Consumer (Orchestrator)" for r in role])),
                         ("file transceiver", np.array([r == "Transceiver (Middle-Tier)" for r in role])),
                         ("file producer (>0.8)", np.array([r == "Pure Producer (Foundation)" for r in role]))):
            fc[label] = (int(m.sum()), float(fy[m].sum()), float(fmu[m].sum()))
        res["file"] = fc
    return res


def lift_ci(y, mu, idx, reps=200):
    idx = np.asarray(idx)
    if len(idx) == 0:
        return float("nan"), float("nan"), float("nan")
    base = y[idx].sum() / max(mu[idx].sum(), 1e-9)
    bs = []
    for _ in range(reps):
        s = rng.choice(idx, len(idx)); bs.append(y[s].sum() / max(mu[s].sum(), 1e-9))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return base, lo, hi


def fmt(res, key):
    n, o, e, idx = res["cls"][key]
    if n < 8 or e < 3:
        return f"n={n:5d} (too few)"
    b, lo, hi = lift_ci(res["_y"], res["_mu"], idx)
    flag = "*" if (lo > 1 or hi < 1) else " "
    return f"n={n:5d} {b:4.2f}x ({lo:.2f}-{hi:.2f}){flag}"


if __name__ == "__main__":
    mode = sys.argv[1]; repos = sys.argv[2].split(",")
    defnames = sys.argv[3].split(",") if len(sys.argv) > 3 else ["orig", "B(no-memory)", "D(any commit)"]
    halves = sys.argv[4].split(",") if len(sys.argv) > 4 else ["all"]
    allres = {}
    for name in repos:
        commits = mine(name); files, funcs, G = load(name)
        for h in halves:
            for d in defnames:
                r = analyse(name, d, h, commits, files, funcs, G)
                allres[(name, d, h)] = r
                print(f"\n### {name} | def={d} | half={h} | commits={r['n_commits']} fix-like={r['n_fix']} touches={r['touches']} funcs={r['n_funcs']} | fanout partial={r['fanout_partial']:+.2f} fanin partial={r['fanin_partial']:+.2f}")
                for k in r["cls"]:
                    print(f"   {k:36s} {fmt(r, k)}")
                if "file" in r:
                    for k, (n, o, e) in r["file"].items():
                        print(f"   {k:36s} n={n:5d} {o/max(e,1e-9):4.2f}x  (obs {o:.0f} / exp {e:.0f})")
    # pooled summary
    keys = sorted({(d, h) for (_, d, h) in allres})
    print("\n==== POOLED over repos [" + ",".join(repos) + "] (sum observed / sum expected; CI by within-repo bootstrap)")
    for d, h in keys:
        print(f"-- def={d} half={h}")
        rs = [allres[(n, d, h)] for n in repos]
        for k in rs[0]["cls"]:
            O = sum(r["cls"][k][1] for r in rs); E = sum(r["cls"][k][2] for r in rs); N = sum(r["cls"][k][0] for r in rs)
            if N < 8 or E < 3:
                print(f"   {k:36s} n={N} (too few)"); continue
            bs = []
            for _ in range(200):
                o = e = 0.0
                for r in rs:
                    idx = np.asarray(r["cls"][k][3])
                    if len(idx):
                        s = rng.choice(idx, len(idx)); o += r["_y"][s].sum(); e += r["_mu"][s].sum()
                bs.append(o / max(e, 1e-9))
            lo, hi = np.percentile(bs, [2.5, 97.5])
            per = " ".join(f"{(r['cls'][k][1]/max(r['cls'][k][2],1e-9)):.2f}" if r['cls'][k][2] >= 3 else "  - " for r in rs)
            print(f"   {k:36s} n={N:5d} pooled {O/max(E,1e-9):4.2f}x ({lo:.2f}-{hi:.2f}){'*' if (lo>1 or hi<1) else ' '}   per-repo: {per}")
        fp = [r.get("fanout_partial", float("nan")) for r in rs]
        print(f"   fan-out partial rho per repo: " + " ".join(f"{x:+.2f}" for x in fp) + "   (positive in %d/%d)" % (sum(1 for x in fp if x > 0), len(fp)))
