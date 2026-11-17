"""Patterns among arguments, call-out, call-graph position and keyword signals in the population DB (8.27M functions).
Every correlation is a Spearman rank correlation controlling for function size (log lines), computed within a language and then pooled across
languages, because size drives all of these and languages differ in style."""
import collections
import json
import pickle
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

df, SIG = pickle.load(open("/tmp/gitgalaxy-scratch/claude/pop_fn.pkl", "rb"))
OUT = open("/tmp/gitgalaxy-scratch/claude/pop_report.txt", "w")


def say(*a):
    print(*a)
    print(*a, file=OUT, flush=True)


def partial(x, y, z):
    """Spearman correlation of x and y after removing the linear effect of z's rank from both ranks."""
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    A = np.vstack([rz, np.ones_like(rz)]).T
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]
    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    d = ex.std() * ey.std()
    return float((ex * ey).mean() / d) if d > 0 else float("nan")


def plain(x, y):
    return float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


say(f"functions {len(df):,}; repos {df.repo_name.nunique():,}; languages {df.language.nunique()}")
langs = df.language.value_counts()
big = [l for l, n in langs.items() if n >= 100_000 and l not in ("plaintext", "json", "markdown", "yaml", "xml", "html", "css", "csv")]
say("languages with 100k+ functions:", ", ".join(f"{l} {langs[l]:,}" for l in big))
R = {}

# ---- A. arguments and call-out by language
say("\n== A. ARGUMENT COUNT AND CALL-OUT BY LANGUAGE (functions of 5+ lines) ==")
say(f"{'language':12s} {'functions':>10s} {'args median':>11s} {'mean':>6s} {'5+ args':>8s} {'8+ args':>8s} {'no callee':>9s} {'callees med':>11s} {'rho args~loc':>12s} {'rho callees~loc':>15s}")
rows = {}
for l in big:
    d = df[(df.language == l) & (df["loc"] >= 5)]
    if len(d) < 50_000:
        continue
    s = d.sample(min(len(d), 400_000), random_state=1)
    rows[l] = {"n": len(d), "args_med": float(d.args.median()), "args_mean": float(d.args.mean()), "a5": float((d.args >= 5).mean()), "a8": float((d.args >= 8).mean()), "no_callee": float((d.n_callees == 0).mean()), "callee_med": float(d.n_callees.median()), "rho_args_loc": plain(s.args, s["loc"]), "rho_call_loc": plain(s.n_callees, s["loc"])}
    r = rows[l]
    say(f"{l:12s} {r['n']:10,d} {r['args_med']:11.0f} {r['args_mean']:6.2f} {100 * r['a5']:7.1f}% {100 * r['a8']:7.1f}% {100 * r['no_callee']:8.1f}% {r['callee_med']:11.0f} {r['rho_args_loc']:12.2f} {r['rho_call_loc']:15.2f}")
R["A"] = rows
use = list(rows)

# ---- B. args vs call-out, controlling for size
say("\n== B. DO FUNCTIONS WITH MORE ARGUMENTS CALL MORE THINGS? (partial Spearman, size controlled) ==")
pb = {}
for l in use:
    d = df[(df.language == l) & (df["loc"] >= 5)]
    s = d.sample(min(len(d), 300_000), random_state=2)
    pb[l] = {"raw": plain(s.args, s.n_callees), "partial": partial(s.args, s.n_callees, s["loc"])}
    say(f"  {l:12s} raw {pb[l]['raw']:+.2f}   size-controlled {pb[l]['partial']:+.2f}")
R["B"] = pb

# ---- C. keyword signals against args and call-out
say("\n== C. KEYWORD SIGNALS AGAINST ARGUMENTS AND CALL-OUT (partial Spearman, size controlled; pooled over languages) ==")
res = {"args": collections.defaultdict(dict), "callees": collections.defaultdict(dict)}
for l in use:
    d = df[(df.language == l) & (df["loc"] >= 5)]
    s = d.sample(min(len(d), 250_000), random_state=3)
    for c in SIG:
        if (s[c] > 0).mean() < 0.02 or (s[c] > 0).mean() > 0.98:
            continue
        res["args"][c][l] = partial(s[c], s.args, s["loc"])
        res["callees"][c][l] = partial(s[c], s.n_callees, s["loc"])
summary = {}
for target in ("args", "callees"):
    rows_ = []
    for c, v in res[target].items():
        vals = [x for x in v.values() if x == x]
        if len(vals) < 3:
            continue
        med = float(np.median(vals))
        agree = sum(1 for x in vals if np.sign(x) == np.sign(med))
        rows_.append((c, med, agree, len(vals)))
    rows_.sort(key=lambda r: -abs(r[1]))
    summary[target] = rows_
    say(f"\n  signal vs {target.upper()} ({'parameters' if target == 'args' else 'distinct functions called'}): strongest, median over languages, signs agreeing")
    for c, med, agree, n in rows_[:14]:
        say(f"    {c:26s} {med:+.2f}  ({agree}/{n} languages agree)")
R["C"] = {t: [(c, m, a, n) for c, m, a, n in v] for t, v in summary.items()}

# ---- D. call graph: fan-in by unique name within a repo
say("\n== D. CALL-GRAPH POSITION: WHO GETS CALLED (names defined once in a repo; fan-in = distinct functions in the repo that call that name) ==")
fan = np.full(len(df), -1.0, dtype=np.float32)
calls = df.calls.values
names = df.func_name.values
by_repo = df.groupby("repo_name").indices
for repo, idx in by_repo.items():
    cnt = collections.Counter(names[idx])
    uniq = {names[i]: i for i in idx if cnt[names[i]] == 1}
    fi = collections.Counter()
    for i in idx:
        for c in set(calls[i]):
            if c in uniq and c != names[i]:
                fi[c] += 1
    for n, i in uniq.items():
        fan[i] = fi.get(n, 0)
df["fan_in"] = fan
res_d = df[df.fan_in >= 0]
say(f"  functions with a unique name in their repo (so fan-in is measurable): {len(res_d):,} of {len(df):,}")
tot = res_d.fan_in.sum()
for q in (0.01, 0.05, 0.10):
    cut = res_d.fan_in.quantile(1 - q)
    top = res_d[res_d.fan_in >= max(cut, 1)]
    say(f"  top {int(q * 100)}% of functions by fan-in hold {100 * top.fan_in.sum() / tot:.0f}% of all name-resolved calls (cut: {max(cut, 1):.0f}+ callers)")
say(f"  never called by name in their repo: {100 * (res_d.fan_in == 0).mean():.0f}%; called by 1 function: {100 * (res_d.fan_in == 1).mean():.0f}%; 10+ callers: {100 * (res_d.fan_in >= 10).mean():.1f}%")
rd = {}
say("\n  Fan-in against size, arguments and call-out (partial Spearman, size controlled, by language):")
say(f"  {'language':12s} {'~args':>6s} {'~callees':>9s} {'~loc (raw)':>11s}")
for l in use:
    d = res_d[(res_d.language == l) & (res_d["loc"] >= 5)]
    if len(d) < 30_000:
        continue
    s = d.sample(min(len(d), 300_000), random_state=4)
    rd[l] = {"args": partial(s.fan_in, s.args, s["loc"]), "callees": partial(s.fan_in, s.n_callees, s["loc"]), "loc": plain(s.fan_in, s["loc"])}
    say(f"  {l:12s} {rd[l]['args']:+6.2f} {rd[l]['callees']:+9.2f} {rd[l]['loc']:+11.2f}")
R["D"] = rd

say("\n  Keyword signals of hubs (partial Spearman of the signal with fan-in, size controlled; pooled over languages):")
hub = {}
for l in use:
    d = res_d[(res_d.language == l) & (res_d["loc"] >= 5)]
    if len(d) < 30_000:
        continue
    s = d.sample(min(len(d), 250_000), random_state=5)
    for c in SIG:
        fr = (s[c] > 0).mean()
        if fr < 0.02 or fr > 0.98:
            continue
        hub.setdefault(c, {})[l] = partial(s[c], s.fan_in, s["loc"])
rows_ = []
for c, v in hub.items():
    vals = [x for x in v.values() if x == x]
    if len(vals) >= 3:
        med = float(np.median(vals))
        rows_.append((c, med, sum(1 for x in vals if np.sign(x) == np.sign(med)), len(vals)))
rows_.sort(key=lambda r: -abs(r[1]))
for c, med, agree, n in rows_[:14]:
    say(f"    {c:26s} {med:+.2f}  ({agree}/{n} languages agree)")
R["D_signals"] = rows_

# ---- E. what hubs and leaves look like
say("\n== E. WHAT A HUB LOOKS LIKE (10+ callers) VERSUS A LEAF (called by nobody), same language, 5+ lines ==")
say(f"  {'language':12s} {'median args':>13s} {'median loc':>13s} {'median callees':>15s} {'public':>13s}")
for l in use:
    d = res_d[(res_d.language == l) & (res_d["loc"] >= 5)]
    h, z = d[d.fan_in >= 10], d[d.fan_in == 0]
    if len(h) < 2000:
        continue
    say(f"  {l:12s} {h.args.median():5.0f} vs {z.args.median():<4.0f}  {h['loc'].median():5.0f} vs {z['loc'].median():<4.0f}  {h.n_callees.median():6.0f} vs {z.n_callees.median():<4.0f}  {100 * h.is_public.mean():4.0f}% vs {100 * z.is_public.mean():<3.0f}%   (hubs {len(h):,}, leaves {len(z):,})")

# ---- F. names: what everyone calls
say("\n== F. WHAT EVERYONE CALLS: the 12 most common callee names per language, and the share of all call sites the top 20 names take ==")
for l in use[:12]:
    c = collections.Counter()
    for t in df.calls.values[df.language.values == l][:600_000]:
        c.update(set(t))
    tot_ = sum(c.values())
    top = c.most_common(12)
    say(f"  {l:12s} top20 share {100 * sum(v for _, v in c.most_common(20)) / tot_:4.1f}%  " + ", ".join(f"{k}" for k, _ in top))
json.dump(R, open("/tmp/gitgalaxy-scratch/claude/pop_results.json", "w"), default=float)
