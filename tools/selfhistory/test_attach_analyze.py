import pickle, json, math, datetime as dt, collections
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy import stats
D = pickle.load(open("/srv/storage_16tb/projects/gitgalaxy-history/tests_attach/derived.pkl", "rb"))
weeks, snap, touch, birth, size = D["weeks"], D["snap"], D["touch"], D["birth"], D["size"]
log = D["log"]; R = collections.OrderedDict()
def group(p):
    s = p.split("/")
    return s[1] if len(s) > 2 and s[1] in ("core", "tools", "recorders") else "other"
NW = len(weeks)
def era(i):
    d = weeks[i]
    if d < dt.date(2026, 7, 6): return "gemini"
    if d < dt.date(2026, 7, 22): return "transition"
    if d < dt.date(2026, 9, 27): return "claude"
    return "fleet"
def att(i, f): return snap[i]["att"].get(f, 0) if 0 <= i < NW and f in snap[i]["files"] else None
tw = collections.defaultdict(lambda: np.zeros(NW))  # file -> touches by week
for (p, i), (y, n) in touch.items(): tw[p][i] += n
rows = []; drops = collections.Counter()
for (p, i), (y, n) in touch.items():
    if i < 1: drops["week 0 (no previous week-end commit)"] += 1; continue
    if p not in snap[i - 1]["files"]: drops["file not in tree at previous week-end (new that week or moved)"] += 1; continue
    loc = size.get((p, i - 1))
    if loc is None: drops["no size in daily scan at previous week-end"] += 1; continue
    a1 = att(i - 1, p); a2 = att(i - 2, p) if i >= 2 else None; lead = att(i + 1, p)
    bd = birth.get(p)
    bw = max(0, (min(bd.date() - dt.timedelta(days=bd.weekday()), weeks[i - 1]) if bd else weeks[i - 1]) and 0)
    age = (weeks[i - 1] - (bd.date() - dt.timedelta(days=bd.weekday()))).days / 7 if bd else np.nan
    rows.append(dict(file=p, week=i, y=int(y), n=int(n), a1=a1, a2=a2, lead=lead, loc=loc, lloc=math.log(max(loc, 1)),
                     age=max(age, 0), rec=math.log1p(tw[p][max(0, i - 4):i].sum()), era=era(i), grp=group(p), wstart=str(weeks[i])))
df = pd.DataFrame(rows)
R["steps"] = dict(weeks=NW, engine_files_ever=len({f for s in snap for f in s["files"]}),
                  engine_files_at_tip=len(snap[-1]["files"]), file_weeks_with_touches=len(touch),
                  touches=int(sum(n for y, n in touch.values())), fix_touches=int(sum(y for y, n in touch.values())),
                  rows_dropped=dict(drops), rows_in_lag1_model=len(df))
# ---- descriptive
months = collections.OrderedDict()
for i in range(NW):
    m = str(weeks[i] + dt.timedelta(days=6))[:7]
    fs = snap[i]["files"]
    months.setdefault(m, []).append((len(fs), sum(1 for f in fs if snap[i]["att"].get(f, 0) >= 1)))
R["attached_share_by_month"] = {m: dict(weekly_snapshots=len(v), mean_engine_files=round(np.mean([a for a, b in v]), 1),
                                        share_attached_mean_of_weeks=round(float(np.mean([b / a for a, b in v if a])), 3),
                                        share_attached_last_week=round(v[-1][1] / v[-1][0], 3)) for m, v in months.items()}
def desc(d):
    return dict(file_weeks=len(d), files=int(d.file.nunique()), touches=int(d.n.sum()), fix_touches=int(d.y.sum()),
                pooled_fix_share=round(float(d.y.sum() / d.n.sum()), 3), mean_row_fix_share=round(float((d.y / d.n).mean()), 3),
                loc_q10_50_90=[float(x) for x in d["loc"].quantile([.1, .5, .9])])
df["att1"] = (df.a1 >= 1).astype(int)
R["descriptive_lag1"] = {"attached": desc(df[df.att1 == 1]), "unattached": desc(df[df.att1 == 0])}
R["attachment_variation_lag1"] = dict(share_rows_attached=round(float(df.att1.mean()), 3), rows=len(df),
    unattached_rows=int((df.att1 == 0).sum()), unattached_files=int(df[df.att1 == 0].file.nunique()),
    files_ever_in_rows=int(df.file.nunique()),
    files_with_both_states_in_rows=int((df.groupby("file").att1.nunique() == 2).sum()),
    count_attached_quantiles_10_50_90=[float(x) for x in df[df.att1 == 1].a1.quantile([.1, .5, .9])],
    unattached_rows_by_era=df[df.att1 == 0].era.value_counts().to_dict(), rows_by_era=df.era.value_counts().to_dict())
# ---- models
def fit(d, expo, label):
    d = d.dropna(subset=[expo, "age"]).copy()
    X = pd.DataFrame({"exposure": d[expo].astype(float), "lloc": d.lloc, "age": d.age, "rec": d.rec})
    for e in ("transition", "claude", "fleet"): X["era_" + e] = (d.era == e).astype(float)
    for g in ("tools", "recorders", "other"): X["grp_" + g] = (d.grp == g).astype(float)
    X = sm.add_constant(X)
    # drop all-zero columns (unseen levels)
    drop = [c for c in X.columns if c != "const" and X[c].std() == 0]
    X = X.drop(columns=drop)
    codes = pd.factorize(d.file)[0]
    r = sm.GLM(np.column_stack([d.y, d.n - d.y]), X, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": codes})
    b, ci = r.params["exposure"], r.conf_int().loc["exposure"]
    out = dict(label=label, rows=len(d), files=int(d.file.nunique()), coef=float(b), se=float(r.bse["exposure"]), p=float(r.pvalues["exposure"]),
               coef_ci95=[float(ci[0]), float(ci[1])], OR=float(math.exp(b)), OR_ci95=[float(math.exp(ci[0])), float(math.exp(ci[1]))],
               dropped_constant_columns=drop, other_coefs={k: round(float(v), 3) for k, v in r.params.items() if k not in ("exposure",)})
    return out
def verdict(m):
    lo, hi = m["coef_ci95"]
    if m["coef"] >= 0: return "REFUTED (coefficient >= 0)"
    return "SUPPORTED (interval wholly below 0)" if hi < 0 else "NOT SUPPORTED (interval includes 0)"
df["logn1"] = np.log1p(df.a1)
m1 = fit(df, "att1", "T1 lag1 attached(>=1)"); m1["verdict"] = verdict(m1)
m2 = fit(df, "logn1", "T2 lag1 log(1+n attached tests)"); m2["verdict"] = verdict(m2)
R["T1"] = m1; R["T2"] = m2
# T3a lead
dl = df.dropna(subset=["lead"]).copy(); dl["leadatt"] = (dl.lead >= 1).astype(int); dl["a1b"] = dl.att1
R["T3a_lead_attached"] = fit(dl, "leadatt", "lead (end of following week) attached")
R["T3a_lag_on_lead_subset"] = fit(dl, "a1b", "lagged attached on the same rows as the lead model")
dl["leadlog"] = np.log1p(dl.lead); dl["laglog"] = dl.logn1
R["T3a_lead_log"] = fit(dl, "leadlog", "lead log(1+n)"); R["T3a_lag_log_on_lead_subset"] = fit(dl, "laglog", "lag log(1+n), lead subset")
# T3b
rec = []
for i in range(NW - 1):
    fixed = {p for (p, w), (y, n) in touch.items() if w == i and y > 0}
    for f in snap[i]["files"]:
        if f in snap[i + 1]["files"]:
            a0, a1 = snap[i]["att"].get(f, 0), snap[i + 1]["att"].get(f, 0)
            touched = (f, i) in touch
            rec.append(dict(file=f, week=i, fixw=int(f in fixed), touched=int(touched), rise=int(a1 > a0), unatt0=int(a0 == 0)))
t3 = pd.DataFrame(rec)
def t3tab(d):
    g = d.groupby("fixw").rise.agg(["sum", "count"]); 
    return {int(k): dict(rises=int(v["sum"]), file_weeks=int(v["count"]), share=round(float(v["sum"] / v["count"]), 4)) for k, v in g.iterrows()}
R["T3b_all_files_existing_both_weeks"] = t3tab(t3)
R["T3b_only_unattached_at_start_POSTHOC"] = t3tab(t3[t3.unatt0 == 1])
R["T3b_touched_files_only_POSTHOC"] = t3tab(t3[t3.touched == 1])
rr = sm.GLM(t3.rise, sm.add_constant(t3.fixw.astype(float)), family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(t3.file)[0]})
ci = rr.conf_int().loc["fixw"]
R["T3b_OR_fix_vs_nofix_cluster_robust"] = dict(OR=float(math.exp(rr.params["fixw"])), ci95=[float(math.exp(ci[0])), float(math.exp(ci[1]))])
# ---- robustness 1: 2-week lag
d2 = df.dropna(subset=["a2"]).copy(); d2["att2"] = (d2.a2 >= 1).astype(int); d2["logn2"] = np.log1p(d2.a2)
R["ROB_lag2_attached"] = fit(d2, "att2", "attachment at end of week t-2"); R["ROB_lag2_attached"]["verdict"] = verdict(R["ROB_lag2_attached"])
R["ROB_lag2_log"] = fit(d2, "logn2", "log(1+n) at end of week t-2"); R["ROB_lag2_log"]["verdict"] = verdict(R["ROB_lag2_log"])
# ---- robustness 2: file level
root = D["root_day"]
fl = []
fl_drop = collections.Counter()
allfiles = {f for s in snap for f in s["files"]}
for f in allfiles:
    bd = birth.get(f)
    if bd is None or (bd - root).days < 2: fl_drop["existed at start of data (birth unknown)"] += 1; continue
    bw = (bd.date() - dt.timedelta(days=bd.weekday())); bi = (bw - weeks[0]).days // 7
    k = bi + 3
    if k >= NW: fl_drop["born < 4 weeks before the end"] += 1; continue
    if f not in snap[k]["files"]: fl_drop["not in tree at end of its first 4 weeks"] += 1; continue
    s = size.get((f, k))
    if s is None: fl_drop["no size"] += 1; continue
    y = sum(v[0] for (p, w), v in touch.items() if p == f); n = sum(v[1] for (p, w), v in touch.items() if p == f)
    if n == 0: fl_drop["no touches in window"] += 1; continue
    fl.append(dict(file=f, y=y, n=n, att=int(snap[k]["att"].get(f, 0) >= 1), lloc=math.log(max(s, 1))))
fd = pd.DataFrame(fl)
R["ROB_file_level"] = dict(files=len(fd), dropped=dict(fl_drop))
if len(fd) > 10:
    fd["dec"] = pd.qcut(fd.lloc, 10, labels=False, duplicates="drop")
    R["ROB_file_level"]["attached_files"] = int(fd.att.sum())
    R["ROB_file_level"]["pooled_fix_share"] = {k: round(float(g.y.sum() / g.n.sum()), 3) for k, g in fd.groupby("att")}
    R["ROB_file_level"]["files_by_att"] = {int(k): int(len(g)) for k, g in fd.groupby("att")}
    X = pd.get_dummies(fd.dec, prefix="dec", drop_first=True).astype(float); X["att"] = fd.att.astype(float); X = sm.add_constant(X)
    X = X.loc[:, (X.std() > 0) | (X.columns == "const")]
    if fd.att.nunique() == 2:
        r = sm.GLM(np.column_stack([fd.y, fd.n - fd.y]), X, family=sm.families.Binomial()).fit(cov_type="HC1")
        ci = r.conf_int().loc["att"]
        R["ROB_file_level"]["decile_matched_OR"] = dict(OR=float(math.exp(r.params["att"])), ci95=[float(math.exp(ci[0])), float(math.exp(ci[1]))])
        R["ROB_file_level"]["within_decile_diff_in_pooled_share"] = [
            dict(dec=int(k), n_unatt=int((g.att == 0).sum()), n_att=int((g.att == 1).sum()),
                 share_unatt=round(float(g[g.att == 0].y.sum() / max(g[g.att == 0].n.sum(), 1)), 3) if (g.att == 0).any() else None,
                 share_att=round(float(g[g.att == 1].y.sum() / max(g[g.att == 1].n.sum(), 1)), 3) if (g.att == 1).any() else None) for k, g in fd.groupby("dec")]
json.dump(R, open("/srv/storage_16tb/projects/gitgalaxy-history/tests_attach/results.json", "w"), indent=1, default=str)
print(json.dumps(R, indent=1, default=str))
