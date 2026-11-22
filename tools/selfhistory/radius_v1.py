#!/usr/bin/env python3
"""V1 / V2 repair-radius analysis (Amendment 2 of self_lattice_and_radius_plan.md). Read-only on all inputs.
Run: OMP_NUM_THREADS=1 nice -n 19 python3 radius.py"""
import collections, datetime as dt, gzip, json, re, sqlite3, subprocess
import numpy as np

H = "/srv/storage_16tb/projects/gitgalaxy-history"
OUT = H + "/radius"
MIRROR = H + "/mirror.git"
CACHE = H + "/evolution_real/cache/diff_gitgalaxy-engine_de3c170c426c97d9.json.gz"
K = (1, 2, 3)
M = 200
SEED = 2982
NBOOT = 2000
FIXRE = re.compile(r"(?i)^\s*(bugfix|fix)(es|ed)?\b")


def norm(p):
    return "gitgalaxy/" + p[len("backend/"):] if p.startswith("backend/") else p


def engine(p):
    p = norm(p)
    return (p.startswith("gitgalaxy/") and p.endswith(".py") and "/tests/" not in p and "/standards/" not in p
            and "gitgalaxy_standards" not in p and not p.endswith("__init__.py"))


items = [json.loads(l) for l in open(H + "/gh/items.jsonl")]
prs = {i["n"]: i for i in items if i["pr"] and i["merged"]}
pr_commit = {}
for l in open(H + "/gh/commit_files.txt"):
    if l.startswith("@@"):
        sha, subj = l[2:].rstrip("\n").split("\t", 1)
        m = re.search(r"\(#(\d+)\)\s*$", subj)
        if m:
            pr_commit[int(m.group(1))] = sha
cdate = {}
for l in subprocess.run(["git", "--git-dir=" + MIRROR, "log", "--first-parent", "--format=%H\t%cI"], capture_output=True, text=True).stdout.splitlines():
    s, d = l.split("\t")
    cdate[s] = dt.datetime.fromisoformat(d)
cache = json.load(gzip.open(CACHE))
funcs_raw = {s: {(norm(p), n) for p, n in v["funcs"]} for s, v in cache.items()}
funcs_eng = {s: {(p, n) for p, n in f if engine(p)} for s, f in funcs_raw.items()}

picks = [l.split("\t") for l in open(H + "/picks.tsv").read().split("\n") if l.strip()]
scan_path = {d: f"{H}/dbs/{d}_{s[:10]}.db" for d, s in picks}
scan_dates = sorted(scan_path)


def scan_for(t):
    d = t.date().isoformat()
    for sd in scan_dates:
        if sd >= d:
            return sd
    return None


_gcache = {}


def graph(sd):
    if sd in _gcache:
        return _gcache[sd]
    _gcache.clear()
    con = sqlite3.connect(f"file:{scan_path[sd]}?mode=ro&immutable=1", uri=True)
    files = {r[0]: norm(r[1]) for r in con.execute("SELECT id, file_path FROM file_data")}
    nid, nodes, loc, fkey = {}, [], [], {}
    for fid, ffile, name, lo in con.execute("SELECT id, file_id, func_name, loc FROM function_data"):
        p = files.get(ffile)
        if p is None or not engine(p):
            continue
        k = (p, name)
        if k not in nid:
            nid[k] = len(nodes); nodes.append(k); loc.append(0)
        loc[nid[k]] = max(loc[nid[k]], int(lo or 0))
        fkey[fid] = nid[k]
    fwd, rev = collections.defaultdict(set), collections.defaultdict(set)
    ne = 0
    for s, d in con.execute("SELECT src_func_id, dst_func_id FROM fcall_data WHERE kind='call' AND dst_func_id IS NOT NULL AND COALESCE(candidates,1)=1"):
        if s in fkey and d in fkey and fkey[s] != fkey[d]:
            fwd[fkey[s]].add(fkey[d]); rev[fkey[d]].add(fkey[s]); ne += 1
    con.close()
    n = len(nodes)
    loc = np.array(loc)
    cuts = np.percentile(loc, np.arange(10, 100, 10))
    dec = np.searchsorted(cuts, loc)
    by_dec = [np.where(dec == i)[0] for i in range(10)]
    by_file = collections.defaultdict(list)
    for i, (p, _) in enumerate(nodes):
        by_file[p].append(i)
    by_file = {p: np.array(v) for p, v in by_file.items()}
    isolated = sum(1 for i in range(n) if i not in fwd and i not in rev)
    g = dict(nodes=nodes, nid=nid, loc=loc, dec=dec, by_dec=by_dec, by_file=by_file, fwd=fwd, rev=rev, n=n, ne=ne, isolated=isolated)
    _gcache[sd] = g
    return g


def bfs(start, adj, kmax):
    seen = set(start); frontier = set(start); out = []; acc = set()
    for _ in range(kmax):
        nxt = set()
        for x in frontier:
            nxt |= adj.get(x, set())
        nxt -= seen; seen |= nxt; acc |= nxt; out.append(set(acc)); frontier = nxt
    return out


KEYS = ["same_file"] + [f"{d}{k}" for k in K for d in ("callers", "callees", "either")]


def make_masks(g, I):
    n = g["n"]
    mk = {}
    sf = np.zeros(n, bool)
    for p in {g["nodes"][i][0] for i in I}:
        sf[g["by_file"][p]] = True
    mk["same_file"] = sf
    cl = bfs(I, g["rev"], 3)   # callers of I (they call into I) within k hops
    ce = bfs(I, g["fwd"], 3)   # callees of I within k hops
    for k in K:
        a = np.zeros(n, bool); b = np.zeros(n, bool)
        if cl[k - 1]: a[list(cl[k - 1])] = True
        if ce[k - 1]: b[list(ce[k - 1])] = True
        mk[f"callers{k}"] = a; mk[f"callees{k}"] = b; mk[f"either{k}"] = a | b
    return mk


def stack(mk):
    return np.stack([mk[k] for k in KEYS], 1)


fix_prs = [n for n, i in prs.items() if (FIXRE.match(i["title"]) or "bug" in [l.lower() for l in i["labels"]])]
fix_by_title = [n for n in fix_prs if FIXRE.match(prs[n]["title"])]
fix_by_label = [n for n in fix_prs if "bug" in [l.lower() for l in prs[n]["labels"]]]
fix_commits = {}
for n in fix_prs:
    s = pr_commit.get(n)
    if s and s in cdate:
        fix_commits[s] = n
stats = collections.OrderedDict()
stats["merged PRs"] = len(prs)
stats["fix PRs (title prefix fix/bugfix/fixes/fixed, or label bug)"] = len(fix_prs)
stats["  by title"] = len(fix_by_title); stats["  by bug label"] = len(fix_by_label)
stats["fix PRs mapped to a first-parent commit"] = len(fix_commits)
inc = {s: funcs_eng.get(s, set()) for s in fix_commits}
stats["fix commits present in the diff cache"] = sum(1 for s in fix_commits if s in cache)
stats["fix commits with >=1 Python engine function"] = sum(1 for s in fix_commits if inc[s])
order = sorted((s for s in fix_commits if inc[s]), key=lambda s: cdate[s])
stats["  engine function touches summed over those commits"] = sum(len(inc[s]) for s in order)

pairs = []
for i, a in enumerate(order):
    for b in order[i + 1:]:
        lag = (cdate[b] - cdate[a]).total_seconds() / 86400
        if lag > 30:
            break
        pairs.append((a, b, lag))
stats["pairs (A, later fix B within 30 d), both with engine functions"] = len(pairs)


def evaluate(pairlist):
    rng = np.random.default_rng(SEED)
    byscan = collections.defaultdict(list)
    for a, b, lag in pairlist:
        byscan[scan_for(cdate[a])].append((a, b, lag))
    rows = []
    c = collections.Counter()
    for sd in sorted(byscan, key=lambda x: (x is None, x)):
        if sd is None:
            c["pairs: no scan at/after A"] += len(byscan[sd]); continue
        g = graph(sd)
        nid = g["nid"]
        cm = {}
        for a, b, lag in byscan[sd]:
            Araw = inc[a]
            Ain = {nid[f] for f in Araw if f in nid}
            if not Ain:
                c["pairs dropped: A has no function in scan"] += 1; continue
            outside = [f for f in inc[b] if f not in Araw]
            outn = []
            for f in outside:
                if f in nid:
                    outn.append(nid[f])
                else:
                    c["outside B functions dropped (not in scan graph)"] += 1
                    if f[0] not in g["by_file"]:
                        c["  ...file absent from scan (new/renamed/deleted file)"] += 1
                    else:
                        c["  ...file present, function absent (new/renamed/deleted function)"] += 1
            c["B functions touched by A as well (not outside)"] += len(inc[b]) - len(outside)
            c["A functions touched (summed over used+dropped pairs)"] += len(Araw)
            c["A functions dropped (not in scan graph)"] += len(Araw) - len(Ain)
            if not outn:
                c["pairs dropped: no outside B function in scan"] += 1; continue
            c["pairs used"] += 1; c["outside functions used"] += len(outn)
            if a not in cm:
                cm[a] = stack(make_masks(g, Ain))
            S = cm[a]
            Al = list(Ain)
            for gnode in outn:
                pool = g["by_dec"][g["dec"][gnode]]
                pool = pool[~np.isin(pool, Al)]
                if len(pool) == 0:
                    c["no null-A pool"] += 1; continue
                nA = S[pool[rng.integers(len(pool), size=M)]].mean(0)
                allm = g["by_file"][g["nodes"][gnode][0]]
                mates = allm[(allm != gnode) & ~np.isin(allm, Al)]
                nB = S[mates[rng.integers(len(mates), size=M)]].mean(0) if len(mates) else None
                if nB is None:
                    c["outside functions with no file-mate (excluded from null-B rows)"] += 1
                rows.append(dict(a=a, b=b, lag=lag, obs=S[gnode].astype(float), nA=nA, nB=nB, nfile=len(allm)))
    return rows, c


def boot_ratio(rows, key_null, sel=None):
    rs = [r for r in rows if r[key_null] is not None and (sel is None or sel(r))]
    if not rs:
        return None
    bs = sorted({r["b"] for r in rs}); bi = {b: i for i, b in enumerate(bs)}
    nb = len(bs)
    O = np.zeros((nb, len(KEYS))); N = np.zeros((nb, len(KEYS)))
    for r in rs:
        i = bi[r["b"]]; O[i] += r["obs"]; N[i] += r[key_null]
    o, n = O.sum(0), N.sum(0)
    out = {"n_funcs": len(rs), "n_Bcommits": nb}
    with np.errstate(all="ignore"):
        r0 = np.where(n > 0, o / n, np.nan)
        draws = np.random.default_rng(SEED).integers(0, nb, size=(NBOOT, nb))
        Ob = O[draws].sum(1); Nb = N[draws].sum(1)
        R = np.where(Nb > 0, Ob / Nb, np.nan)
        lo, hi = np.nanpercentile(R, 2.5, 0), np.nanpercentile(R, 97.5, 0)
    for j, k in enumerate(KEYS):
        out[k] = dict(obs=float(o[j] / len(rs)), null=float(n[j] / len(rs)), ratio=float(r0[j]), lo=float(lo[j]), hi=float(hi[j]))
    return out


def tables(rows):
    strata = {"all": None, "lag<=2d": lambda r: r["lag"] <= 2, "lag>2d": lambda r: r["lag"] > 2}
    return {sn: {"nullA": boot_ratio(rows, "nA", sel), "nullB": boot_ratio(rows, "nB", sel)} for sn, sel in strata.items()}


def r3_boot(rows, k, sel=None):
    """callers_k vs callees_k: raw observed-rate ratio, and excess-over-null-B ratio; bootstrap over B commits."""
    rs = [r for r in rows if r["nB"] is not None and (sel is None or sel(r))]
    jc, je = KEYS.index(f"callers{k}"), KEYS.index(f"callees{k}")
    bs = sorted({r["b"] for r in rs}); bi = {b: i for i, b in enumerate(bs)}
    O = np.zeros((len(bs), 2)); N = np.zeros((len(bs), 2))
    for r in rs:
        i = bi[r["b"]]; O[i] += [r["obs"][jc], r["obs"][je]]; N[i] += [r["nB"][jc], r["nB"][je]]
    def stat(O, N):
        o, n = O.sum(0), N.sum(0)
        return o[0] / o[1], (o[0] / n[0]) / (o[1] / n[1])
    d = np.random.default_rng(SEED).integers(0, len(bs), size=(NBOOT, len(bs)))
    bt = np.array([stat(O[x], N[x]) for x in d])
    p = stat(O, N)
    return {"raw_callers_over_callees": [float(p[0]), *map(float, np.percentile(bt[:, 0], [2.5, 97.5]))],
            "excess_ratio_nullB_callers_over_callees": [float(p[1]), *map(float, np.percentile(bt[:, 1], [2.5, 97.5]))]}


def v2():
    ap = json.load(open(H + "/gh/pilot_out/agreed_pairs.json"))
    res = []
    for p in ap:
        cs = pr_commit.get(p["cause_pr"])
        for fp in p["fix_prs"]:
            fs = pr_commit.get(fp)
            r = dict(issue=p["issue"], cause_pr=p["cause_pr"], fix_pr=fp, cause_commit=cs, fix_commit=fs)
            if not cs or not fs:
                r["note"] = "PR has no first-parent commit"; res.append(r); continue
            sd = scan_for(cdate[cs])
            r["lag_days"] = round((cdate[fs] - cdate[cs]).total_seconds() / 86400, 2)
            r["scan"] = sd
            C, F = funcs_eng.get(cs, set()), funcs_eng.get(fs, set())
            r["cause_in_cache"] = cs in cache; r["fix_in_cache"] = fs in cache
            r["cause_funcs_engine"] = sorted(f"{a}::{b}" for a, b in C)
            r["fix_funcs_engine"] = sorted(f"{a}::{b}" for a, b in F)
            r["cause_funcs_non_engine"] = len(funcs_raw.get(cs, set())) - len(C)
            r["fix_funcs_non_engine"] = len(funcs_raw.get(fs, set())) - len(F)
            r["same_function_overlap"] = sorted(f"{a}::{b}" for a, b in C & F)
            r["same_file_overlap"] = sorted({a for a, _ in C} & {a for a, _ in F})
            if sd is None:
                r["note"] = "no scan at/after cause"; res.append(r); continue
            g = graph(sd); nid = g["nid"]
            Ci = {nid[f] for f in C if f in nid}
            r["cause_funcs_in_scan"] = len(Ci)
            outside = sorted(f for f in F if f not in C)
            r["outside_fix_funcs"] = len(outside)
            r["outside_fix_funcs_in_scan"] = sum(f in nid for f in outside)
            if Ci:
                mk = make_masks(g, Ci)
                rel = []
                for f in outside:
                    if f not in nid:
                        rel.append(dict(func=f"{f[0]}::{f[1]}", status="not in scan")); continue
                    i = nid[f]
                    d = dict(func=f"{f[0]}::{f[1]}", same_file=bool(mk["same_file"][i]))
                    for k in K:
                        d[f"callers{k}"] = bool(mk[f"callers{k}"][i]); d[f"callees{k}"] = bool(mk[f"callees{k}"][i])
                    rel.append(d)
                r["outside_relations"] = rel
            res.append(r)
    return res


def fmt(x):
    return f"{x:.2f}" if x == x else "n/a"


def write_md(o):
    L = ["# V1/V2 repair radius results (Amendment 2)", "", "## Counts", ""]
    L += [f"- {k}: {v}" for k, v in o["counts"].items()]
    L += ["", "### Pair-level accounting (V1)", ""] + [f"- {k}: {v}" for k, v in o["counts_pairs"].items()]
    L += [f"- share of pairs with lag <= 2 d: {o['lag_share_le2d']:.2f}", f"- graphs used: {o['graphs_used']}"]
    for sn in ("all", "lag<=2d", "lag>2d"):
        for nl, nm in (("nullA", "repo-wide, same size decile"), ("nullB", "file-mates")):
            t = o["V1"][sn][nl]
            L += ["", f"### V1 stratum {sn}, null {nl[-1]} ({nm})", ""]
            if not t:
                L.append("no data"); continue
            L += [f"outside B functions: {t['n_funcs']} (in {t['n_Bcommits']} B commits)", "",
                  "| relation | observed | null | ratio | 95% interval |", "|---|---|---|---|---|"]
            for k in KEYS:
                v = t[k]
                L.append(f"| {k} | {100*v['obs']:.1f}% | {100*v['null']:.1f}% | {fmt(v['ratio'])} | [{fmt(v['lo'])}, {fmt(v['hi'])}] |")
    L += ["", "## V1-R3 callers vs callees ([point, lo, hi])", ""] + [f"- {sn} {k}: {v}" for sn, d in o["R3"].items() for k, v in d.items()]
    L += ["", "## Sanity 1: permutation (B shuffled across A within lag bins)", ""]
    for p in o["perm_check"]:
        L.append(f"- rep {p['rep']}: outside functions {p['nfuncs']}")
        for nl in ("nullA", "nullB"):
            t = p[nl]
            if t:
                L.append(f"  - {nl}: " + ", ".join(f"{k} {fmt(t[k]['ratio'])} [{fmt(t[k]['lo'])},{fmt(t[k]['hi'])}]" for k in ("same_file", "either1", "either2", "either3", "callers2", "callees2")))
    L += ["", "## Sanity 2: file size", "", f"- B outside functions: {o['size_check']}", f"- A functions: {o['size_check_A']}"]
    L += ["", "## V2 (descriptive, n=10 pairs)", ""]
    for r in o["V2"]:
        L.append(f"### issue {r['issue']}: cause PR {r['cause_pr']} -> fix PR {r['fix_pr']}")
        L.append("```\n" + json.dumps({k: v for k, v in r.items() if k not in ("issue", "cause_pr", "fix_pr")}, indent=1) + "\n```")
    open(OUT + "/results.md", "w").write("\n".join(L) + "\n")


def main():
    out = {"counts": dict(stats)}
    rows, c = evaluate(pairs)
    out["counts_pairs"] = dict(c)
    out["V1"] = tables(rows)
    out["R3"] = {sn: {f"k{k}": r3_boot(rows, k, sel) for k in K} for sn, sel in (("all", None), ("lag<=2d", lambda r: r["lag"] <= 2), ("lag>2d", lambda r: r["lag"] > 2))}
    bins = lambda lag: 0 if lag <= 2 else (1 if lag <= 7 else 2)
    perm = []
    for rep in range(3):
        rg = np.random.default_rng(SEED + 1 + rep)
        newp = []
        for bn in range(3):
            sub = [p for p in pairs if bins(p[2]) == bn]
            Bs = [p[1] for p in sub]
            for p, j in zip(sub, rg.permutation(len(Bs))):
                if Bs[j] != p[0] and cdate[Bs[j]] > cdate[p[0]] - dt.timedelta(days=0) and False:
                    pass
                if Bs[j] != p[0]:
                    newp.append((p[0], Bs[j], p[2]))
        prow, pc = evaluate(newp)
        perm.append({"rep": rep, "nfuncs": len(prow), "nullA": boot_ratio(prow, "nA"), "nullB": boot_ratio(prow, "nB")})
    out["perm_check"] = perm
    nfile = np.array([r["nfile"] for r in rows])
    out["size_check"] = {"share in file with >=50 functions": float((nfile >= 50).mean()),
                         ">=100": float((nfile >= 100).mean()), ">=200": float((nfile >= 200).mean()),
                         "median functions in file": float(np.median(nfile)),
                         "share with <=5 file-mates": float((nfile <= 6).mean())}
    big = collections.Counter()
    gf = {}
    asd = collections.defaultdict(set)
    for a, b, l in pairs:
        sd = scan_for(cdate[a])
        if sd:
            asd[sd].add(a)
    for sd in sorted(asd):
        g = graph(sd)
        gf[sd] = dict(nodes=g["n"], edges=g["ne"], isolated=g["isolated"])
        for a in asd[sd]:
            for f in inc[a]:
                if f in g["nid"]:
                    n = len(g["by_file"][f[0]])
                    big["A_total_distinct_A_commits_funcs"] += 1; big["in file >=50"] += n >= 50; big["in file >=100"] += n >= 100; big["in file >=200"] += n >= 200
    out["size_check_A"] = dict(big)
    out["graphs_used"] = {"n_scans": len(gf), "median_nodes": float(np.median([v["nodes"] for v in gf.values()])),
                          "median_edges": float(np.median([v["edges"] for v in gf.values()])),
                          "median_isolated_share": float(np.median([v["isolated"] / v["nodes"] for v in gf.values()]))}
    out["lag_share_le2d"] = float(np.mean([p[2] <= 2 for p in pairs]))
    out["V2"] = v2()
    json.dump(out, open(OUT + "/results.json", "w"), indent=1)
    write_md(out)


if __name__ == "__main__":
    main()
