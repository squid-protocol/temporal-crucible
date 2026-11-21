#!/usr/bin/env python3
"""POST HOC (exploratory, added after seeing the permutation result): null C = hot-spot-preserving null. Appends to results.md."""
import bisect, collections, datetime as dt, json
import numpy as np
import radius as R

SEED = R.SEED; M = R.M; K = R.KEYS
order = R.order; dates = [R.cdate[s] for s in order]
alltouch = collections.Counter()
for s in order:
    for f in R.inc[s]: alltouch[f] += 1
poolcache = {}
def pool_counts(b):
    if b in poolcache: return poolcache[b]
    t = R.cdate[b]
    lo = bisect.bisect_left(dates, t - dt.timedelta(days=30)); hi = bisect.bisect_left(dates, t)
    c = collections.Counter()
    for s in order[lo:hi]:
        for f in R.inc[s]: c[f] += 1
    poolcache[b] = c
    return c

def evaluate_c(pairlist):
    rng = np.random.default_rng(SEED)
    byscan = collections.defaultdict(list)
    for a, b, lag in pairlist: byscan[R.scan_for(R.cdate[a])].append((a, b, lag))
    rows = []; fb = 0; prior = 0
    for sd in sorted(x for x in byscan if x):
        g = R.graph(sd); nid = g["nid"]
        for a, b, lag in byscan[sd]:
            Araw = R.inc[a]; Ain = {nid[f] for f in Araw if f in nid}
            if not Ain: continue
            outn = [(f, nid[f]) for f in R.inc[b] if f not in Araw and f in nid]
            if not outn: continue
            S = R.stack(R.make_masks(g, Ain))
            def build(counts):
                ids = [(nid[f], c) for f, c in counts.items() if f in nid and nid[f] not in Ain]
                return ids
            ids = build(pool_counts(b))
            fell = False
            if len(ids) < 20:
                ids = build(alltouch); fell = True
            w = np.array([c for _, c in ids], float); nodes = np.array([i for i, _ in ids])
            w /= w.sum()
            tA = R.cdate[a]
            for f, gn in outn:
                nC = S[nodes[rng.choice(len(nodes), size=M, p=w)]].mean(0)
                was = any(R.cdate[s] < tA and f in R.inc[s] for s in order)  # touched by an earlier fix commit before A
                rows.append(dict(a=a, b=b, lag=lag, obs=S[gn].astype(float), nC=nC, fb=fell, prior=was))
    return rows

rows = evaluate_c(R.pairs)
strata = {"all": None, "lag<=2d": lambda r: r["lag"] <= 2, "lag>2d": lambda r: r["lag"] > 2}
res = {sn: R.boot_ratio(rows, "nC", sel) for sn, sel in strata.items()}
bins = lambda lag: 0 if lag <= 2 else (1 if lag <= 7 else 2)
perm = []
for rep in range(3):
    rg = np.random.default_rng(SEED + 1 + rep); newp = []
    for bn in range(3):
        sub = [p for p in R.pairs if bins(p[2]) == bn]; Bs = [p[1] for p in sub]
        for p, j in zip(sub, rg.permutation(len(Bs))):
            if Bs[j] != p[0]: newp.append((p[0], Bs[j], p[2]))
    perm.append(R.boot_ratio(evaluate_c(newp), "nC"))
cnt = np.array(sorted(alltouch.values(), reverse=True)); tot = cnt.sum()
conc = {"distinct functions touched": len(cnt), "total touches": int(tot),
        "share on top 5%": float(cnt[:max(1, int(.05 * len(cnt)))].sum() / tot),
        "share on top 20%": float(cnt[:max(1, int(.20 * len(cnt)))].sum() / tot),
        "share of outside B functions touched by an earlier fix before A": float(np.mean([r["prior"] for r in rows])),
        "rows using the all-time fallback pool": float(np.mean([r["fb"] for r in rows])), "rows": len(rows)}
json.dump(dict(nullC=res, perm=perm, conc=conc), open("results_posthoc.json", "w"), indent=1)
L = ["", "## POST HOC (exploratory; added after seeing the permutation result; not pre-declared; nothing above altered)", "",
     "Null C: 200 draws per observed outside B function from functions touched by any fix commit in the 30 days before B (fallback: all fix commits, if <20 distinct nodes in A's scan), weighted by touch count, in A's scan, excluding the A set.", "",
     f"Concentration: {conc}", ""]
for sn in strata:
    t = res[sn]
    L += [f"### null C, stratum {sn} ({t['n_funcs']} functions, {t['n_Bcommits']} B commits)", "", "| relation | observed | null C | ratio | 95% |", "|---|---|---|---|---|"]
    for k in K:
        v = t[k]; L.append(f"| {k} | {100*v['obs']:.1f}% | {100*v['null']:.1f}% | {R.fmt(v['ratio'])} | [{R.fmt(v['lo'])}, {R.fmt(v['hi'])}] |")
    L.append("")
L.append("### permutation vs null C (B shuffled within lag bins)")
for i, t in enumerate(perm):
    L.append(f"- rep {i}: " + ", ".join(f"{k} {R.fmt(t[k]['ratio'])} [{R.fmt(t[k]['lo'])},{R.fmt(t[k]['hi'])}]" for k in ("same_file", "either1", "either2", "either3", "callers2", "callees2")))
open("results.md", "a").write("\n".join(L) + "\n")
print("\n".join(L))
