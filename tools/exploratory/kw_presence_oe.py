"""Exploratory (after KW, KW-R): yes/no keyword presence; continuous size control via a per-signal logistic model
p_s(loc) on log loc (+ square); pair association = log((observed co-presence + .5) / (expected under size-conditional
independence + .5)). Cross-language agreement, shuffle null, size-only placebo, with/without struct_branch."""
import sys, pathlib, sqlite3, itertools
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import kw_eval as K
db = sys.argv[1]
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
cols = [c[1] for c in con.execute("PRAGMA table_info(function_data)")]
sig = [c for c in cols if c not in K.NON_SIGNAL and c not in K.STYLE]
rows = con.execute(f"SELECT fd.language, f.loc, {', '.join('f.' + c for c in sig)} FROM function_data f JOIN file_data fd ON f.file_id=fd.id WHERE f.loc>=3").fetchall()
lang = np.array([r[0] for r in rows]); loc = np.array([float(r[1] or 0) for r in rows])
X = np.array([[(v or 0) > 0 for v in r[2:]] for r in rows], dtype=bool)
langs = [l for l in sorted(set(lang)) if (lang == l).sum() >= K.MIN_FUNCS]
rng = np.random.default_rng(7)

def fit_p(x, z):
    Z = np.c_[np.ones_like(z), z, z * z]
    def f(b):
        t = np.clip(Z @ b, -30, 30); p = 1 / (1 + np.exp(-t))
        return -np.sum(x * np.log(p + 1e-12) + (1 - x) * np.log(1 - p + 1e-12)), Z.T @ (p - x)
    b = minimize(f, np.zeros(3), jac=True, method="L-BFGS-B").x
    return 1 / (1 + np.exp(-np.clip(Z @ b, -30, 30)))

def oe(Xl, P):
    O = Xl.T.astype(float) @ Xl; E = P.T @ P
    M = np.log((O + .5) / (E + .5)); np.fill_diagonal(M, 0); return M

D = {}
for l in langs:
    m = lang == l; Xl = X[m]; prev = Xl.mean(0); used = np.flatnonzero((prev >= K.LO) & (prev <= K.HI))
    z = np.log10(loc[m]); z = (z - z.mean()) / (z.std() + 1e-9)
    P = np.column_stack([fit_p(Xl[:, i].astype(float), z) for i in used])
    D[l] = {"sig": [sig[i] for i in used], "X": Xl[:, used], "P": P}

def cross(mats, drop=(), perm=False):
    rs = []
    for l1, l2 in itertools.combinations(langs, 2):
        s1, s2 = D[l1]["sig"], D[l2]["sig"]; sh = [s for s in s1 if s in s2 and s not in drop]
        tri = list(itertools.combinations(range(len(sh)), 2))
        if len(tri) < 10: continue
        M1, M2 = mats[l1], mats[l2]
        i1 = [s1.index(s) for s in sh]; i2 = [s2.index(s) for s in sh]
        if perm: i1 = list(rng.permutation(i1)); i2 = list(rng.permutation(i2))
        v1 = np.array([M1[i1[i], i1[j]] for i, j in tri]); v2 = np.array([M2[i2[i], i2[j]] for i, j in tri])
        if v1.std() > 0 and v2.std() > 0: rs.append(np.corrcoef(v1, v2)[0, 1])
    return float(np.mean(rs))

real = {l: oe(D[l]["X"], D[l]["P"]) for l in langs}
for drop in ((), ("struct_branch",)):
    tag = "without struct_branch" if drop else "all signals"
    obs = cross(real, drop)
    pl = np.mean([cross({l: oe(rng.random(D[l]["P"].shape) < D[l]["P"], D[l]["P"]) for l in langs}, drop) for _ in range(10)])
    nul = np.quantile([cross(real, drop, perm=True) for _ in range(500)], 0.995)
    print(f"[{tag}] cross-language r = {obs:.3f}; size-only placebo {pl:.3f}; shuffle null 99.5th {nul:.3f}")
agg = {}
for l in langs:
    s, M = D[l]["sig"], real[l]
    for i, j in itertools.combinations(range(len(s)), 2):
        agg.setdefault(tuple(sorted((s[i], s[j]))), []).append(M[i, j])
med = {k: (np.median(v), np.mean(np.sign(v) == np.sign(np.median(v))), len(v)) for k, v in agg.items() if len(v) >= len(langs) // 2}
print("together more than size predicts:"); [print(f"   {a} + {b}: x{np.exp(v[0]):.2f}  ({v[1]:.0%} of {v[2]} langs)") for (a, b), v in sorted(med.items(), key=lambda t: -t[1][0])[:14]]
print("together less than size predicts:"); [print(f"   {a} x {b}: x{np.exp(v[0]):.2f}  ({v[1]:.0%} of {v[2]} langs)") for (a, b), v in sorted(med.items(), key=lambda t: t[1][0])[:10]]
