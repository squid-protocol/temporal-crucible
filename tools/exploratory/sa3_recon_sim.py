"""Synthetic only. Compare the two proposed 'adds to size' statistics, and the three proposed negative controls."""
import sys, json, numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import sa3_review_sim as sim
from sa3_review_sim import bands_of, sauc, resid_within, make
rng = np.random.default_rng(7)
sim.rng = rng

def bauc(x, y, loc, b, k, cal=1.5):
    tot = {'gt': [0.0, 0], 'lt': [0.0, 0], 'eq': [0.0, 0]}
    for j in range(k):
        m = b == j
        xp, lp = x[m][y[m] == 1], loc[m][y[m] == 1]
        xn, ln = x[m][y[m] == 0], loc[m][y[m] == 0]
        if not len(xp) or not len(xn): continue
        ratio = lp[:, None] / ln[None, :]
        ok = (ratio <= cal) & (ratio >= 1 / cal)
        conc = (xp[:, None] > xn[None, :]) + 0.5 * (xp[:, None] == xn[None, :])
        for name, mask in (('gt', ok & (ratio > 1)), ('lt', ok & (ratio < 1)), ('eq', ok & (ratio == 1))):
            tot[name][0] += conc[mask].sum(); tot[name][1] += mask.sum()
    n = sum(v[1] for v in tot.values())
    if tot['gt'][1] < 25 or tot['lt'][1] < 25: return np.nan
    we = tot['eq'][1] / n
    ce = tot['eq'][0] / tot['eq'][1] if tot['eq'][1] else 0.5
    return (1 - we) * 0.5 * (tot['gt'][0] / tot['gt'][1] + tot['lt'][0] / tot['lt'][1]) + we * ce

def one(n, pos, kind, c):
    loc, lg, x, y = make(n, pos / n, 1.2, 0.9, kind, c)
    k = 10 if n >= 300 else 5
    b = bands_of(loc, k)
    return sauc(resid_within(x, lg, b, k), y, b, k) - 0.5, bauc(x, y, loc, b, k) - 0.5

def study(mix, kind, c, reps):
    out = {'resid': [], 'bauc': []}
    for _ in range(reps):
        per = np.array([one(n, p, kind, c) for n, p in mix])
        for i, s in enumerate(('resid', 'bauc')):
            v = per[:, i]; v = v[~np.isnan(v)]
            m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
            out[s].append((m, m - 2.24 * se > 0, m + 2.24 * se < 0))   # 97.5% interval (Holm-first)
    return {s: (np.mean([r[0] for r in v]), np.mean([r[1] for r in v]), np.mean([r[2] for r in v])) for s, v in out.items()}

mix = json.loads(sys.argv[1]); reps = int(sys.argv[2])
print(f"{'true effect':<12}{'predictor':<15}{'resid mean':>11}{'supp':>6}{'contra':>7}   {'bAUC mean':>10}{'supp':>6}{'contra':>7}")
for c in (0.0, 0.15, 0.3):
    for kind in ('noise', 'noisy_size_hi', 'count', 'sparse_count', 'score'):
        if c and kind in ('noise', 'noisy_size_hi'): continue
        r = study(mix, kind, c, reps)
        print(f"c={c:<10}{kind:<15}{r['resid'][0]:>+11.4f}{r['resid'][1]:>6.2f}{r['resid'][2]:>7.2f}   {r['bauc'][0]:>+10.4f}{r['bauc'][1]:>6.2f}{r['bauc'][2]:>7.2f}", flush=True)

# ---- negative controls: a predictor that tracks ACTIVITY only, never defects
print("\nCONTROL TEST: x tracks how busy a file is, fixes are a constant share of all commits (no defect content).")
print("share of simulated studies where effect(HP) - effect(control) reads 'defect-specific' (should be ~0.03):")
def ctl_study(mix, reps, pfix=0.12):
    res = {'CHURN_any': [], 'CHURN_exclusive': [], 'matched': []}
    for _ in range(reps):
        d = {k: [] for k in res}
        for n, pos in mix:
            lg = rng.normal(5, 1.2, n); loc = np.exp(lg)
            busy = rng.normal(0, 1, n)
            x = busy + rng.normal(0, 1, n)                    # noisy activity proxy, independent of LOC
            base = np.exp(0.9 * (lg - 5) + 0.8 * busy)
            scale = np.interp(pos / n, *zip(*[((1 - np.exp(-s * base * pfix)).mean(), s) for s in np.geomspace(1e-3, 50, 60)]))
            rate = scale * base
            hp = rng.poisson(rate * pfix) > 0
            other = rng.poisson(rate * (1 - pfix))
            anyc = other > 0
            matched = rng.binomial(other, pfix / (1 - pfix)) > 0   # as many control commits as fix commits
            k = 10 if n >= 300 else 5; b = bands_of(loc, k)
            r = resid_within(x, lg, b, k)
            e = lambda yy: sauc(r, yy.astype(int), b, k) - 0.5
            eh = e(hp)
            d['CHURN_any'].append(eh - e(anyc)); d['CHURN_exclusive'].append(eh - e(anyc & ~hp)); d['matched'].append(eh - e(matched))
        for kk, v in d.items():
            v = np.array(v); v = v[~np.isnan(v)]; m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
            res[kk].append((m, m - 1.96 * se > 0))
    for kk, v in res.items():
        print(f"  {kk:<17} mean difference {np.mean([a for a, _ in v]):+.4f}   reads defect-specific in {np.mean([b for _, b in v]):.0%} of studies")
ctl_study(mix, max(40, reps // 2))
