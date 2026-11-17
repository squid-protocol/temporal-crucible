"""Branch logic (complexity) against size and parameter count in the v2.12.0 population DB, and the functions that break the pattern.
Per language: log(1 + complexity) ~ log(lines) + log(1 + args); residual outliers; what they are (names, repos, error-handling signals, call-graph role).
Signal comparisons are standardized by size decile (outliers are compared with other functions of the same size)."""
import collections, pickle, re
import numpy as np
import pandas as pd

df, SIG, TOP = pickle.load(open("/tmp/gitgalaxy-scratch/claude/pop2_fn.pkl", "rb"))
OUT = open("/tmp/gitgalaxy-scratch/claude/pop_outliers_report.txt", "w")
def say(*a):
    print(*a); print(*a, file=OUT, flush=True)

NOT = ("plaintext", "json", "markdown", "yaml", "xml", "html", "css", "csv")
langs = [l for l, n in df.language.value_counts().items() if n >= 100_000 and l not in NOT]
df = df[(df["loc"] >= 5) & (df.language.isin(langs)) & (df.def_test == 0)].copy()
say(f"functions of 5+ lines, non-test, {len(langs)} languages: {len(df):,}")
df["y"] = np.log1p(df.complexity.values); df["x1"] = np.log(df["loc"].values); df["x2"] = np.log1p(df.args.values)

say("\n== 1. HOW MUCH DOES THE PARAMETER COUNT ADD TO BRANCH LOGIC, ONCE SIZE IS KNOWN? ==")
say(f"{'language':11s} {'n':>9s} {'R2 size only':>12s} {'R2 size+args':>12s} {'args coef':>9s} {'size coef':>9s}")
coef = {}; res = []
for l in langs:
    d = df[df.language == l]
    X0 = np.c_[np.ones(len(d)), d.x1]; X1 = np.c_[np.ones(len(d)), d.x1, d.x2]
    b0 = np.linalg.lstsq(X0, d.y.values, rcond=None)[0]; b1 = np.linalg.lstsq(X1, d.y.values, rcond=None)[0]
    r0 = d.y.values - X0 @ b0; r1 = d.y.values - X1 @ b1; tot = ((d.y - d.y.mean()) ** 2).sum()
    coef[l] = b1; say(f"{l:11s} {len(d):9,d} {1 - (r0**2).sum() / tot:12.3f} {1 - (r1**2).sum() / tot:12.3f} {b1[2]:+9.3f} {b1[1]:+9.3f}")
    z = pd.Series(r1 / r1.std(), index=d.index); res.append(z)
df["z"] = pd.concat(res)
# is the args effect curved? mean residual (size only) by args bucket pooled
say("\n  average branch logic at the same size, by parameter count (size-only model residual, pooled, in log units; positive = branchier than size predicts)")
r0 = []
for l in langs:
    d = df[df.language == l]; X0 = np.c_[np.ones(len(d)), d.x1]; b0 = np.linalg.lstsq(X0, d.y.values, rcond=None)[0]; r0.append(pd.Series(d.y.values - X0 @ b0, index=d.index))
df["r0"] = pd.concat(r0)
b = pd.cut(df.args, [-1, 0, 1, 2, 3, 4, 6, 9, 1000], labels=["0", "1", "2", "3", "4", "5-6", "7-9", "10+"])
t = df.groupby(b, observed=True).r0.agg(["mean", "size"])
say("  " + "   ".join(f"{k}: {v['mean']:+.2f} (n {int(v['size']):,})" for k, v in t.iterrows()))
for l in ("c", "python", "java", "go"):
    if l in langs:
        d = df[df.language == l]; bb = pd.cut(d.args, [-1, 0, 1, 2, 3, 4, 6, 9, 1000], labels=["0", "1", "2", "3", "4", "5-6", "7-9", "10+"]); tt = d.groupby(bb, observed=True).r0.mean()
        say(f"  {l:8s} " + "   ".join(f"{k}: {v:+.2f}" for k, v in tt.items()))

df["h"] = (df.func_fan_in > 0).astype(float)
df["dec"] = pd.qcut(df["loc"], 10, labels=False, duplicates="drop")
say("\n== 2. OUTLIERS: functions the size-and-parameters model gets most wrong (residual beyond 3.5 standard deviations) ==")
hi, lo = df[df.z > 3.5], df[df.z < -3.5]
say(f"  branchier than expected: {len(hi):,} ({100 * len(hi) / len(df):.2f}%); flatter than expected: {len(lo):,} ({100 * len(lo) / len(df):.2f}%)")
wf = df[(df.args >= 6) & (df.complexity <= 1) & (df["loc"] >= 10)]
nk = df[(df.args <= 1) & (df.complexity >= 40)]
say(f"  wide and flat (6+ parameters, no branching, 10+ lines): {len(wf):,};   narrow and knotty (0-1 parameters, complexity 40+): {len(nk):,}")

def std_rate(group, col, positive=True):
    base = df.groupby("dec")[col].apply(lambda s: (s > 0).mean() if positive else s.mean())
    mix = group.dec.value_counts(normalize=True)
    expected = float((base * mix).sum())
    obs = float((group[col] > 0).mean() if positive else group[col].mean())
    return obs, expected
say("\n  What they look like, against other functions of the same size (observed vs size-matched expected):")
say(f"  {'group':26s} {'n':>8s} {'guards(def_safety)':>20s} {'early exits':>14s} {'public':>12s} {'has callers':>13s} {'median loc':>10s} {'median args':>11s}")
for nm, g in (("branchier than expected", hi), ("flatter than expected", lo), ("wide and flat", wf), ("narrow and knotty", nk)):
    row = [nm.ljust(26), f"{len(g):8,d}"]
    for col in ("def_safety", "state_bailout_hits", "is_public"):
        o, e = std_rate(g, col); row.append(f"{100*o:5.1f}% vs {100*e:4.1f}%")
    o, e = std_rate(g, "h"); row.append(f"{100*o:4.0f}% vs {100*e:3.0f}%")
    row += [f"{g['loc'].median():10.0f}", f"{g.args.median():11.0f}"]
    say("  " + "  ".join(row))

def tokens(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(s)); return [t.lower() for t in re.split(r"[^A-Za-z0-9]+", s) if len(t) >= 3]
base_tok = collections.Counter(); samp = df.sample(600_000, random_state=1)
for n in samp.func_name.values: base_tok.update(set(tokens(n)))
def lift(group, k=14, minc=300):
    c = collections.Counter(); g = group.sample(min(len(group), 100_000), random_state=2)
    for n in g.func_name.values: c.update(set(tokens(n)))
    rows = []
    for t, n in c.items():
        if n >= minc * len(g) / 100_000 and base_tok.get(t, 0) >= 30:
            rows.append((t, n / len(g) / (base_tok[t] / len(samp)), n))
    rows.sort(key=lambda r: -r[1]); return rows[:k]
say("\n  Name words that are over-represented (share in the group / share in all functions):")
for nm, g in (("branchier than expected", hi), ("flatter than expected", lo), ("wide and flat", wf), ("narrow and knotty", nk)):
    say(f"  {nm:24s} " + ", ".join(f"{t} x{x:.0f}" for t, x, n in lift(g)))
say("\n  Where they sit (repositories holding the most of each group, and their share):")
for nm, g in (("branchier than expected", hi), ("flatter than expected", lo), ("wide and flat", wf), ("narrow and knotty", nk)):
    c = g.repo_name.value_counts(); say(f"  {nm:24s} {len(c)} repos; top: " + ", ".join(f"{r} {100 * n / len(g):.0f}%" for r, n in c.head(5).items()))
say("\n  Concentration: share of each group in its top 10 repositories: " + ", ".join(f"{nm} {100 * g.repo_name.value_counts().head(10).sum() / len(g):.0f}%" for nm, g in (("branchier", hi), ("flatter", lo), ("wide+flat", wf), ("narrow+knotty", nk))))

say("\n== 3. ERROR-HANDLING SIGNALS AGAINST PARAMETERS AND BRANCHES (same size; rate of functions with the signal) ==")
for col, nm in (("def_safety", "guards"), ("state_bailout_hits", "early exits / bail-outs")):
    d = df.copy(); d["has"] = (d[col] > 0).astype(float)
    t = d.groupby([pd.cut(d.args, [-1, 0, 1, 2, 4, 1000], labels=["0", "1", "2", "3-4", "5+"]), pd.cut(d.z, [-99, -1, 1, 99], labels=["flat", "as expected", "branchy"])], observed=True).has.mean().unstack()
    say(f"  {nm}: share of functions with the signal, by parameters (rows) and branch logic against size (columns)"); say("  " + t.round(3).to_string().replace("\n", "\n  "))
pickle.dump({"hi": hi.index.values[:200000], "lo": lo.index.values[:200000]}, open("/tmp/gitgalaxy-scratch/claude/pop_outlier_idx.pkl", "wb"))
