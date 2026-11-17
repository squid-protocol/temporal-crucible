"""Call-graph position again without the obvious artifacts: no test functions (as callers or callees), no callee names that are language keywords or
that are among the 300 most common callee names of their language, and only names of 5+ characters."""
import collections, pickle
import numpy as np
from scipy.stats import rankdata
df, SIG = pickle.load(open("/tmp/gitgalaxy-scratch/claude/pop_fn.pkl", "rb"))
OUT = open("/tmp/gitgalaxy-scratch/claude/pop_robust_report.txt", "w")
def say(*a):
    print(*a); print(*a, file=OUT, flush=True)
def partial(x, y, z):
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    A = np.vstack([rz, np.ones_like(rz)]).T
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]; ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    d = ex.std() * ey.std(); return float((ex * ey).mean() / d) if d > 0 else float("nan")
lang = df.language.values; calls = df.calls.values; names = df.func_name.values
is_test = (df.def_test.values > 0)
# the 300 most common callee names per language
common = {}
for l in df.language.value_counts().index[:20]:
    c = collections.Counter()
    for t in calls[lang == l][:500000]: c.update(set(t))
    common[l] = {k for k, _ in c.most_common(300)}
fan = np.full(len(df), -1.0, dtype=np.float32)
for repo, idx in df.groupby("repo_name").indices.items():
    keep = [i for i in idx if not is_test[i]]
    cnt = collections.Counter(names[i] for i in keep)
    uniq = {names[i]: i for i in keep if cnt[names[i]] == 1 and len(names[i]) >= 5 and names[i] not in common.get(lang[i], ())}
    fi = collections.Counter()
    for i in keep:
        for c in set(calls[i]):
            if c in uniq and c != names[i]: fi[c] += 1
    for n, i in uniq.items(): fan[i] = fi.get(n, 0)
df["fan_in"] = fan
r = df[df.fan_in >= 0]
say(f"measurable functions (non-test, unique name of 5+ chars, not a common name): {len(r):,}")
tot = r.fan_in.sum()
for q in (0.01, 0.05, 0.10):
    cut = max(r.fan_in.quantile(1 - q), 1); top = r[r.fan_in >= cut]
    say(f"  top {int(q*100)}% by fan-in hold {100*top.fan_in.sum()/tot:.0f}% of the name-resolved calls (cut {cut:.0f}+)")
say(f"  never called: {100*(r.fan_in==0).mean():.0f}%; 1 caller: {100*(r.fan_in==1).mean():.0f}%; 10+: {100*(r.fan_in>=10).mean():.1f}%")
say("\nfan-in vs args / callees (partial, size controlled), robust version:")
big = [l for l in ("c","cpp","python","java","csharp","typescript","rust","javascript","kotlin","php","dart","go","ruby")]
res = {}
for l in big:
    d = r[(r.language == l) & (r["loc"] >= 5)]
    if len(d) < 20000: continue
    s = d.sample(min(len(d), 250000), random_state=6)
    res[l] = (partial(s.fan_in, s.args, s["loc"]), partial(s.fan_in, s.n_callees, s["loc"]), len(d))
    say(f"  {l:11s} ~args {res[l][0]:+.2f}  ~callees {res[l][1]:+.2f}   (n {len(d):,})")
say("\nkeyword signals vs fan-in, robust version (median partial over languages):")
hub = {}
for l in res:
    d = r[(r.language == l) & (r["loc"] >= 5)]; s = d.sample(min(len(d), 200000), random_state=7)
    for c in SIG:
        fr = (s[c] > 0).mean()
        if 0.02 <= fr <= 0.98: hub.setdefault(c, {})[l] = partial(s[c], s.fan_in, s["loc"])
rows = []
for c, v in hub.items():
    vals = [x for x in v.values() if x == x]
    if len(vals) >= 3:
        m = float(np.median(vals)); rows.append((c, m, sum(1 for x in vals if np.sign(x) == np.sign(m)), len(vals)))
rows.sort(key=lambda x: -abs(x[1]))
for c, m, a, n in rows[:12]: say(f"  {c:26s} {m:+.2f} ({a}/{n} languages agree)")
say("\nhub (10+ callers) vs leaf (0) medians, robust version:")
for l in res:
    d = r[(r.language == l) & (r["loc"] >= 5)]; h, z = d[d.fan_in >= 10], d[d.fan_in == 0]
    if len(h) >= 500: say(f"  {l:11s} args {h.args.median():.0f} vs {z.args.median():.0f}; loc {h['loc'].median():.0f} vs {z['loc'].median():.0f}; callees {h.n_callees.median():.0f} vs {z.n_callees.median():.0f}; public {100*h.is_public.mean():.0f}% vs {100*z.is_public.mean():.0f}% (hubs {len(h):,})")
