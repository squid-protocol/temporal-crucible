"""Arguments, call-out, engine-resolved fan-in and keyword signals in the v2.12.0 population DB. Size (rank of lines) is controlled everywhere."""
import collections, json, pickle
import numpy as np
from scipy.stats import rankdata
df, SIG, TOP = pickle.load(open("/tmp/gitgalaxy-scratch/claude/pop2_fn.pkl", "rb"))
OUT = open("/tmp/gitgalaxy-scratch/claude/pop2_report.txt", "w")
def say(*a):
    print(*a); print(*a, file=OUT, flush=True)
def partial(x, y, z):
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    A = np.vstack([rz, np.ones_like(rz)]).T
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]; ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    d = ex.std() * ey.std(); return float((ex * ey).mean() / d) if d > 0 else float("nan")
def plain(x, y): return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])
langs = df.language.value_counts()
say(f"functions {len(df):,}; repos {df.repo_name.nunique():,}; languages {df.language.nunique()}")
NOT = ("plaintext", "json", "markdown", "yaml", "xml", "html", "css", "csv")
big = [l for l, n in langs.items() if n >= 100_000 and l not in NOT]
say("\n== A. ARGUMENTS AND CALL-OUT BY LANGUAGE (5+ lines) ==")
say(f"{'language':11s} {'functions':>10s} {'args med':>8s} {'mean':>5s} {'5+':>6s} {'8+':>6s} {'no callee':>9s} {'callees med':>11s} {'rho args~loc':>12s} {'rho callees~loc':>15s} {'rho fan_out~callees':>19s}")
use = []
for l in big:
    d = df[(df.language == l) & (df["loc"] >= 5)]
    if len(d) < 50_000: continue
    s = d.sample(min(len(d), 300_000), random_state=1); use.append(l)
    say(f"{l:11s} {len(d):10,d} {d.args.median():8.0f} {d.args.mean():5.2f} {100*(d.args>=5).mean():5.1f}% {100*(d.args>=8).mean():5.1f}% {100*(d.n_callees==0).mean():8.1f}% {d.n_callees.median():11.0f} {plain(s.args, s['loc']):12.2f} {plain(s.n_callees, s['loc']):15.2f} {plain(s.func_fan_out, s.n_callees):19.2f}")
say("\n== B. ARGS vs DISTINCT CALLS (partial, size controlled) ==")
for l in use:
    d = df[(df.language == l) & (df["loc"] >= 5)]; s = d.sample(min(len(d), 300_000), random_state=2)
    say(f"  {l:11s} raw {plain(s.args, s.n_callees):+.2f}  size-controlled {partial(s.args, s.n_callees, s['loc']):+.2f}")
def pooled(target, minfr=0.02, n=250_000, only=None, seed=3):
    out = {}
    for l in use:
        d = df[(df.language == l) & (df["loc"] >= 5)]
        if only is not None: d = d[only(d)]
        if len(d) < 30_000: continue
        s = d.sample(min(len(d), n), random_state=seed)
        for c in SIG:
            fr = (s[c] > 0).mean()
            if minfr <= fr <= 1 - minfr: out.setdefault(c, {})[l] = partial(s[c], s[target], s["loc"])
    rows = []
    for c, v in out.items():
        vals = [x for x in v.values() if x == x]
        if len(vals) >= 3:
            m = float(np.median(vals)); rows.append((c, m, sum(1 for x in vals if np.sign(x) == np.sign(m)), len(vals)))
    rows.sort(key=lambda r: -abs(r[1])); return rows
say("\n== C. KEYWORD SIGNALS (partial, size controlled; median over languages) ==")
for t, nm in (("args", "PARAMETERS"), ("n_callees", "DISTINCT CALLS")):
    say(f"\n  vs {nm}:")
    for c, m, a, n in pooled(t)[:12]: say(f"    {c:26s} {m:+.2f}  ({a}/{n} languages agree)")
say("\n== D. CALL GRAPH: ENGINE-RESOLVED FAN-IN ==")
f = df[df["loc"] >= 1]; tot = f.func_fan_in.sum()
say(f"  functions {len(f):,}; fan-in recorded >0 for {100*(f.func_fan_in>0).mean():.0f}%; 1 caller {100*(f.func_fan_in==1).mean():.0f}%; 10+ callers {100*(f.func_fan_in>=10).mean():.1f}%")
pos = f[f.func_fan_in > 0]
for q in (0.01, 0.05, 0.10):
    cut = max(f.func_fan_in.quantile(1 - q), 1); top = f[f.func_fan_in >= cut]
    say(f"  top {int(q*100)}% of all functions by fan-in hold {100*top.func_fan_in.sum()/tot:.0f}% of resolved calls (cut {cut:.0f}+ callers)")
say("\n  fan-in vs args / calls (partial, size controlled), non-test functions:")
for l in use:
    d = df[(df.language == l) & (df["loc"] >= 5) & (df.def_test == 0)]
    if len(d) < 30_000: continue
    s = d.sample(min(len(d), 300_000), random_state=4)
    say(f"  {l:11s} ~args {partial(s.func_fan_in, s.args, s['loc']):+.2f}  ~distinct calls {partial(s.func_fan_in, s.n_callees, s['loc']):+.2f}  ~loc(raw) {plain(s.func_fan_in, s['loc']):+.2f}  ~public {plain(s.func_fan_in, s.is_public):+.2f}")
say("\n  keyword signals vs fan-in, non-test functions:")
for c, m, a, n in pooled("func_fan_in", only=lambda d: d.def_test == 0, seed=5)[:12]: say(f"    {c:26s} {m:+.2f}  ({a}/{n} languages agree)")
say("\n== E. HUB (10+ callers) vs LEAF (none), non-test, 5+ lines ==")
for l in use:
    d = df[(df.language == l) & (df["loc"] >= 5) & (df.def_test == 0)]; h, z = d[d.func_fan_in >= 10], d[d.func_fan_in == 0]
    if len(h) >= 500: say(f"  {l:11s} args {h.args.median():.0f} vs {z.args.median():.0f}; loc {h['loc'].median():.0f} vs {z['loc'].median():.0f}; calls {h.n_callees.median():.0f} vs {z.n_callees.median():.0f}; public {100*h.is_public.mean():.0f}% vs {100*z.is_public.mean():.0f}% (hubs {len(h):,}, leaves {len(z):,})")
say("\n== F. MOST COMMON CALLEE NAMES PER LANGUAGE (is the call list clean?) ==")
for l in use:
    if l in TOP: say(f"  {l:11s} " + ", ".join(k for k, _ in TOP[l][:14]))
