"""Exploratory (after KW scoring): association beyond the size-only placebo (real log OR − mean placebo log OR),
and whether that residual is shared across languages."""
import sys, pathlib, sqlite3, itertools
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import kw_eval as K
db = sys.argv[1]
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
rows = con.execute(f"SELECT fd.language, f.loc, {', '.join('f.' + c for c in sig)} FROM function_data f JOIN file_data fd ON f.file_id=fd.id WHERE f.loc>=3").fetchall()
lang = np.array([r[0] for r in rows]); loc = np.array([float(r[1] or 0) for r in rows])
X = np.array([[(v or 0) > 0 for v in r[2:]] for r in rows], dtype=bool)
rng = np.random.default_rng(1)
langs = [l for l in sorted(set(lang)) if (lang == l).sum() >= K.MIN_FUNCS]
R = {}
for l in langs:
    m = lang == l; Xl = X[m]; prev = Xl.mean(0); used = np.flatnonzero((prev >= K.LO) & (prev <= K.HI))
    Xu = Xl[:, used]; q = np.quantile(loc[m], np.linspace(0, 1, 11)[1:-1]); st = np.searchsorted(q, loc[m], side="right")
    Mr = K.mh_logor(Xu, st)
    lb = np.searchsorted(np.quantile(loc[m], np.linspace(0, 1, 51)[1:-1]), loc[m], side="right")
    P = np.zeros(Xu.shape)
    for b in np.unique(lb): P[lb == b] = Xu[lb == b].mean(0)
    Mp = np.mean([K.mh_logor(rng.random(Xu.shape) < P, st) for _ in range(20)], axis=0)
    R[l] = ([sig[i] for i in used], Mr - Mp)
rs = []; med = {}
for l1, l2 in itertools.combinations(langs, 2):
    s1, M1 = R[l1]; s2, M2 = R[l2]; sh = [s for s in s1 if s in s2]
    tri = list(itertools.combinations(range(len(sh)), 2))
    if len(tri) < 10: continue
    v1 = np.array([M1[s1.index(sh[i]), s1.index(sh[j])] for i, j in tri]); v2 = np.array([M2[s2.index(sh[i]), s2.index(sh[j])] for i, j in tri])
    rs.append(np.corrcoef(v1, v2)[0, 1])
print("mean cross-language r of beyond-size residual association:", round(float(np.mean(rs)), 3), "over", len(rs), "pairs")
allp = {}
for l in langs:
    s, M = R[l]
    for i, j in itertools.combinations(range(len(s)), 2):
        allp.setdefault(tuple(sorted((s[i], s[j]))), []).append(M[i, j])
agg = {k: (np.median(v), np.mean(np.sign(v) == np.sign(np.median(v))), len(v)) for k, v in allp.items() if len(v) >= len(langs) // 2}
print("beyond-size, most positive:"); [print("  ", k, round(v[0], 2), f"{v[1]:.0%}", v[2]) for k, v in sorted(agg.items(), key=lambda t: -t[1][0])[:10]]
print("beyond-size, most negative:"); [print("  ", k, round(v[0], 2), f"{v[1]:.0%}", v[2]) for k, v in sorted(agg.items(), key=lambda t: t[1][0])[:8]]
