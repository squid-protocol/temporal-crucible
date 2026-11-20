"""Pure analysis functions (no file IO) so they can be unit-tested on synthetic data. See tests/."""
import math, re, statistics as st
from collections import defaultdict

# --- file kind rule: copied from tools/selfhistory/join_steps.py ---
def kind(p):
    if p.startswith(("tests/", "test/")): return "tests"
    if p.startswith(("docs/", "site/", "templates/", ".github/", ".claude/")) or p.endswith((".md", ".txt")): return "docs"
    if "/standards/" in p or "gitgalaxy_standards" in p: return "standards"
    if p.startswith("gitgalaxy/tools/"): return "translator_tools"
    if p.startswith(("gitgalaxy/", "backend/")): return "core"
    return "other"


KINDS = ["core", "standards", "translator_tools", "tests", "docs", "other"]

# join_steps.py PERF verbatim (lacks a closing word boundary; trailing space in 'index(ed) '): kept only to report how many hits it gives
PERF_OLD = re.compile(r"\b(perf|performance|speed|fast(er)?|optimi[sz]\w*|O\(N|O\(n|quadratic|linear|cache[sd]?|caching|precompute\w*|memoi[sz]\w*|"
                      r"backtrack\w*|redos|slow\w*|timeout|hot ?path|bottleneck|throughput|latency|vectori[sz]\w*|batch\w*|prefetch\w*|"
                      r"hash ?map|lookup|index(ed)? )", re.I)
# DEVIATION (owner-supplied correction, fix list item 7): closing boundary added, 'batch' dropped, 'index' without trailing space
PERF = re.compile(r"(?<![A-Za-z0-9_])(perf(?:ormance)?|speed(?:ing|ed)?(?:\s?up)?|fast(?:er|est)?|optimi[sz]\w*|O\(\s*[Nn]\s*\^?\s*\d?\s*\)?|quadratic|linear(?:ity)?|"
                  r"cach(?:e|es|ed|ing)|precompute\w*|memoi[sz]\w*|backtrack\w*|redos|slow(?:er|est|ly|down)?|time-?outs?|hot[- ]?path|bottleneck|throughput|latency|"
                  r"vectori[sz]\w*|prefetch\w*|hash[- ]?map|lookups?|index(?:ed|ing)?)(?![A-Za-z0-9_])", re.I)

PR_RE = re.compile(r"\(#(\d+)\)")


def pr_number(subject, pr_items=None):
    """PR number: the LAST '(#N)' anywhere in the subject (so `Revert "... (#992)"` and a non-trailing (#N) are found). If pr_items
    (n -> item) is given, the last (#N) that is a known PR wins, else the last (#N)."""
    ns = [int(n) for n in PR_RE.findall(subject)]
    if not ns: return None
    if pr_items:
        known = [n for n in ns if n in pr_items and pr_items[n].get("pr")]
        if known: return known[-1]
    return ns[-1]


def n_core_funcs(cache, sha):
    c = cache.get(sha)
    if not c: return 0
    return len({(p, f) for p, f in c["funcs"] if kind(p) == "core"})


def bucket(files, nfuncs, cutoff=3, gap=False):
    """Amendment 1 buckets. gap = cache-absent core commit (function count unknown) -> 'gap'. (e) = no file changed at all."""
    if not files: return "e"
    ks = {kind(p) for p in files}
    if "core" in ks:
        if gap: return "gap"
        return "b" if nfuncs <= cutoff else "c"
    if "standards" in ks: return "a"
    return "d"


def pure_a(files):
    return bool(files) and all(kind(p) == "standards" for p in files)


# ---- refinement passes ----
def rkey(r): return (r["corpus"], r["from_sha"], r["to_sha"])


def merge_passes(p1, p2):
    """Dedupe by (corpus, from_sha, to_sha); pass 2 supersedes pass 1 (later line wins within a pass). Returns (rows, info);
    every row gets '_pass' (1/2) and '_pass1_class' (class in pass 1 or None)."""
    d, c1 = {}, {}
    for r in p1:
        d[rkey(r)] = {**r, "_pass": 1, "_pass1_class": None}; c1[rkey(r)] = r["class"]
    n_sup = 0
    for r in p2:
        k = rkey(r); old = c1.get(k)
        d[k] = {**r, "_pass": 2, "_pass1_class": r.get("pass1_class", old)}
        n_sup += 1
    rows = list(d.values())
    changed = [r for r in rows if r["_pass"] == 2 and r["_pass1_class"] is not None and r["_pass1_class"] != r["class"]]
    info = {"n_pass1_lines": len(p1), "n_pass1_distinct": len({rkey(r) for r in p1}), "n_pass2_lines": len(p2), "n_pass2_distinct": len({rkey(r) for r in p2}),
            "n_distinct": len(rows), "n_changed_class": len(changed),
            "changes": sorted({f"{r['_pass1_class']} -> {r['class']}" for r in changed}),
            "change_counts": {t: sum(1 for r in changed if f"{r['_pass1_class']} -> {r['class']}" == t) for t in {f"{r['_pass1_class']} -> {r['class']}" for r in changed}}}
    return rows, info


# ---- events ----
def make_events(refined, pmap):
    """Events = LOCALISED refinements deduped by found commit; within a commit, per-corpus entries deduped by (corpus, found):
    the cpu_s record is primary (larger |boundary_rel| if several); files_mapped facts are kept separately (size_files, files_rel)."""
    by = defaultdict(lambda: defaultdict(lambda: {"cpu_s": [], "files_mapped": []}))
    for r in refined:
        if r["class"] != "LOCALISED" or not r.get("found"): continue
        by[r["found"]][r["corpus"]][r.get("metric", "cpu_s")].append(r)
    evs = []
    for sha, cs in by.items():
        e = {"sha": sha, "index": pmap.get(sha), "corpora": {}}
        for corpus, m in cs.items():
            cpu = max(m["cpu_s"], key=lambda r: abs(r["boundary_rel"]), default=None)
            fil = max(m["files_mapped"], key=lambda r: abs(r["boundary_rel"]), default=None)
            p = cpu or fil
            ent = {"metric": "cpu_s" if cpu else "files_mapped", "down": p["down"], "boundary_rel": p["boundary_rel"], "boundary": p["boundary"], "dcpu_pair": p["dcpu"], "dfiles": p["dfiles"],
                   "from_date": p["from_date"], "to_date": p["to_date"], "files_rel": fil["boundary_rel"] if fil else None, "files_boundary": fil["boundary"] if fil else None}
            e["corpora"][corpus] = ent
        cpu_ents = [c for c in e["corpora"].values() if c["metric"] == "cpu_s"]
        e["size_cpu"] = max((abs(c["boundary_rel"]) for c in cpu_ents), default=None)
        fs = [abs(c["files_rel"]) for c in e["corpora"].values() if c["files_rel"] is not None] + [abs(c["boundary_rel"]) for c in e["corpora"].values() if c["metric"] == "files_mapped"]
        e["size_files"] = max(fs, default=None)
        basis = cpu_ents or list(e["corpora"].values())
        dirs = {c["down"] for c in basis}
        e["direction"] = "down" if dirs == {True} else "up" if dirs == {False} else "mixed"
        evs.append(e)
    return sorted(evs, key=lambda e: (e["index"] is None, e["index"]))


def cpu_steps(events):
    """(corpus, commit) steps judged on CPU, one per (corpus, found)."""
    out = []
    for e in events:
        for c, ent in e["corpora"].items():
            if ent["metric"] == "cpu_s":
                out.append({"corpus": c, "sha": e["sha"], "index": e["index"], "down": ent["down"], "boundary_rel": ent["boundary_rel"], "boundary": ent["boundary"]})
    return out


# ---- series ----
def build_series(rows, date_map=None):
    """Same logic as detect_steps.py. date_map: sha -> 'YYYY-MM-DD' (Eastern) overrides the run's date."""
    series = defaultdict(dict)
    for r in rows:
        if r.get("anchor_n") is not None: continue
        t, i = r["target"], r["fp_index"]
        d = (date_map or {}).get(r["sha"], r["date"])
        if (not r.get("exit")) and r.get("cpu_s") is not None:
            series[t][i] = {"cpu": r["cpu_s"], "files": r.get("files_mapped"), "sha": r["sha"], "date": d}
        else:
            series[t].setdefault(i, {"failed": True, "sha": r["sha"], "date": d})
    return series


def timed(series, t):
    return [(i, series[t][i]) for i in sorted(series.get(t, {})) if not series[t][i].get("failed")]


def crash_gap_pairs(series, t):
    """Every consecutive timed pair with a failed run between them (UNRESOLVED), with its size."""
    idx = sorted(series.get(t, {})); out = []; prev = None; failed = []
    for i in idx:
        s = series[t][i]
        if s.get("failed"): failed.append(i); continue
        if prev is not None and failed:
            a, b = series[t][prev], s
            out.append({"corpus": t, "from": prev, "to": i, "failed_indices": failed, "from_sha": a["sha"], "to_sha": b["sha"], "from_date": a["date"], "to_date": b["date"],
                        "cpu": [a["cpu"], b["cpu"]], "dcpu": b["cpu"] / a["cpu"] - 1,
                        "dfiles": ((b["files"] - a["files"]) / a["files"]) if a.get("files") and b.get("files") else None})
        prev = i; failed = []
    return out


# ---- exact statistics (stdlib, log space) ----
def _lc(n, k): return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _pmf(n, k, p):
    if p <= 0: return 1.0 if k == 0 else 0.0
    if p >= 1: return 1.0 if k == n else 0.0
    return math.exp(_lc(n, k) + k * math.log(p) + (n - k) * math.log1p(-p))


def binom_cdf(k, n, p):
    if k < 0: return 0.0
    return min(1.0, sum(_pmf(n, i, p) for i in range(0, min(k, n) + 1)))


def clopper_pearson(k, n, alpha=0.05):
    if n == 0: return (float("nan"), float("nan"))
    def solve(f, lo=0.0, hi=1.0):
        for _ in range(100):
            m = (lo + hi) / 2
            if f(m): lo = m
            else: hi = m
        return (lo + hi) / 2
    lo = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) < alpha / 2)
    hi = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) > alpha / 2)
    return (lo, hi)


def fisher_exact(a, b, c, d):
    """two-sided Fisher exact for [[a,b],[c,d]] -> (odds ratio, p). OR is nan for 0/0, inf for x/0 with x>0."""
    n1, n2, k = a + b, c + d, a + c
    tot = n1 + n2
    if tot == 0: return float("nan"), float("nan")
    lt = _lc(tot, k)
    def pr(x): return math.exp(_lc(n1, x) + _lc(n2, k - x) - lt)
    lo, hi = max(0, k - n2), min(k, n1)
    p0 = pr(a)
    p = sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p0 * (1 + 1e-9))
    num, den = a * d, b * c
    orr = float("nan") if num == 0 and den == 0 else float("inf") if den == 0 else num / den
    return orr, min(1.0, p)


def mantel_haenszel(strata):
    """strata: list of (a, b, c, d) = (event quiet, event not, other quiet, other not) per stratum. Returns common OR and the
    Mantel-Haenszel chi-square test (1 df, continuity corrected) p; strata with n<2 or no variance are skipped."""
    num = den = sa = se = sv = 0.0; used = 0
    for a, b, c, d in strata:
        n = a + b + c + d
        if n < 2: continue
        n1, n2, m1 = a + b, c + d, a + c
        num += a * d / n; den += b * c / n
        e = n1 * m1 / n; v = n1 * n2 * m1 * (n - m1) / (n * n * (n - 1))
        if v > 0: sa += a; se += e; sv += v; used += 1
    orr = float("nan") if num == 0 and den == 0 else float("inf") if den == 0 else num / den
    if sv <= 0: return orr, float("nan"), used
    chi = (max(0.0, abs(sa - se) - 0.5)) ** 2 / sv
    return orr, math.erfc(math.sqrt(chi / 2)), used


def raw_dcpu(c):
    """Unrounded CPU change of a detector candidate (the stored dcpu is rounded to 3 places and must not be tested against T)."""
    return c["cpu"][1] / c["cpu"][0] - 1


def pct(x, d=0): return "n/a" if x is None or x != x else f"{100 * x:.{d}f}%"
def num(x, d=3): return "n/a" if x is None or x != x else ("inf" if x == float("inf") else f"{x:.{d}f}")


# ---- eras (by commit date, US Eastern) ----
ERAS = ["gemini", "transition", "claude", "fleet"]
def era_of_date(d):
    d = d[:10]
    if d < "2026-07-06": return "gemini"
    if d <= "2026-07-21": return "transition"
    if d <= "2026-09-26": return "claude"
    return "fleet"


def quiet_test(group, others, quiet_key, era_key="era"):
    """group / others: lists of info dicts. quiet_key: field holding the quiet boolean. Returns share (+CP interval), pooled Fisher and
    era-stratified Mantel-Haenszel, all on the SAME populations (group vs others)."""
    k = sum(1 for v in group if v[quiet_key]); n = len(group)
    ko = sum(1 for v in others if v[quiet_key]); no = len(others)
    lo, hi = clopper_pearson(k, n)
    orr, p = fisher_exact(k, n - k, ko, no - ko) if n and no else (float("nan"), float("nan"))
    strata, per = [], {}
    for era in ERAS:
        g = [v for v in group if v[era_key] == era]; o = [v for v in others if v[era_key] == era]
        a = sum(1 for v in g if v[quiet_key]); c = sum(1 for v in o if v[quiet_key])
        strata.append((a, len(g) - a, c, len(o) - c)); per[era] = {"events": len(g), "events_quiet": a, "others": len(o), "others_quiet": c}
    mh_or, mh_p, used = mantel_haenszel(strata)
    return {"n_events": n, "quiet_events": k, "share": k / n if n else None, "ci95": [lo, hi], "n_others": no, "quiet_others": ko, "share_others": ko / no if no else None,
            "fisher_odds_ratio": orr, "fisher_p": p, "mh_odds_ratio": mh_or, "mh_p": mh_p, "mh_strata_used": used, "strata": per}


# ---- persistence ----
def km_reversed(times, events_flags):
    """Kaplan-Meier on time (commits) to reversal; non-reversed are right-censored at their follow-up. Returns (share reversed by the end, median time or None)."""
    data = sorted(zip(times, events_flags))
    n = len(data); S = 1.0; med = None; i = 0
    while i < n:
        t = data[i][0]; d = c = 0
        while i < n and data[i][0] == t:
            d += 1 if data[i][1] else 0; c += 0 if data[i][1] else 1; i += 1
        at_risk = n - (i - d - c)
        if d: S *= 1 - d / at_risk
        if med is None and S <= 0.5 and d: med = t
    return 1 - S, med


def persistence_analyze(steps, tm, T, step_dates, min_after=6):
    """steps: cpu_steps() records ({corpus, sha, index, down, boundary_rel, boundary}).
    tm: corpus -> list of (index, cpu, 'YYYY-MM-DD' Eastern) for timed commits, ascending index.
    T: corpus -> threshold. step_dates: sha -> Eastern date string.
    Amendment 2 rule: pre = median of 3 timed before; post = median of first 3 at/after the step commit; evaluated only if post > pre(1+T)
    and >= min_after timed commits at/after; REVERSED = a later run of 3 consecutive timed commits (starting after the post window) whose
    median is <= pre(1+T) (within T or beyond, overshoot included); ELEVATED AT TIP = median of last 3 > pre(1+T), independent of REVERSED;
    removed-by-named-DOWN if a localised DOWN step on the same corpus lies in the gap between the last non-reversed commit and the end of the reversal window;
    OVERLAPPING = another localised CPU step on the same corpus lies inside [first pre commit, last post commit]. DOWN steps are listed with
    boundary_rel (never median levels)."""
    from datetime import date as D
    up, down, skipped = [], [], []
    for s in sorted(steps, key=lambda s: (s["corpus"], s["index"])):
        t, k = s["corpus"], s["index"]; rows = tm.get(t, [])
        idxs = [r[0] for r in rows]; cpu = [r[1] for r in rows]; dts = [r[2] for r in rows]
        sd = step_dates[s["sha"]]
        before = [j for j, i in enumerate(idxs) if i < k]; after = [j for j, i in enumerate(idxs) if i >= k]
        base = {"corpus": t, "commit": s["sha"][:10], "sha": s["sha"], "index": k, "date": sd, "T": T[t], "n_after": len(after), "n_before": len(before)}
        if s["down"]:
            down.append({**base, "boundary": s["boundary"], "boundary_rel": s["boundary_rel"]}); continue
        if len(before) < 3 or len(after) < 3:
            skipped.append({**base, "reason": "fewer than 3 timed commits before or after"}); continue
        pre = st.median(cpu[j] for j in before[-3:]); post = st.median(cpu[j] for j in after[:3])
        rec = {**base, "pre": pre, "post": post, "size": post / pre - 1, "boundary_rel": s["boundary_rel"]}
        if not post > pre * (1 + T[t]):
            skipped.append({**rec, "reason": "post-level median within T of the pre level (step not visible at 3-commit medians)"}); continue
        if len(after) < min_after:
            skipped.append({**rec, "reason": f"fewer than {min_after} timed commits after the step (right-censored)"}); continue
        lo_i, hi_i = idxs[before[-3]], idxs[after[2]]
        rec["overlapping"] = [o["sha"][:10] + ("(down)" if o["down"] else "(up)") for o in steps if o["corpus"] == t and o["sha"] != s["sha"] and lo_i <= o["index"] <= hi_i]
        rec["overlap"] = bool(rec["overlapping"])
        thr = pre * (1 + T[t]); rev = None
        for j in range(after[0] + 3, len(cpu) - 2):
            if st.median(cpu[j:j + 3]) <= thr: rev = j; break
        rec["reversed"] = rev is not None
        if rev is not None:
            rec.update(reversal_index=idxs[rev], reversal_date=dts[rev], days_to_reversal=(D.fromisoformat(dts[rev]) - D.fromisoformat(sd)).days, commits_to_reversal=idxs[rev] - k,
                       overshoot=st.median(cpu[rev:rev + 3]) < pre * (1 - T[t]))
            named = [d for d in steps if d["corpus"] == t and d["down"] and idxs[rev - 1] < d["index"] <= idxs[rev + 2]]
            rec["removed_by_named_down"] = named[0]["sha"][:10] if named else None
        tip = st.median(cpu[-3:]); rec["tip_level"] = tip; rec["tip_vs_pre"] = tip / pre - 1; rec["elevated_at_tip"] = tip > thr
        rec["follow_up_commits"] = idxs[-1] - k
        rec["follow_up_days"] = (D.fromisoformat(dts[-1]) - D.fromisoformat(sd)).days
        up.append(rec)
    return up, down, skipped


def persistence_summary(up, T=None):
    pool = [x for x in up if not x["overlap"]]
    def block(xs):
        if not xs: return {"n": 0}
        rv = [x for x in xs if x["reversed"]]
        km, med = km_reversed([x["commits_to_reversal"] if x["reversed"] else x["follow_up_commits"] for x in xs], [x["reversed"] for x in xs])
        return {"n": len(xs), "n_reversed": len(rv), "share_reversed": len(rv) / len(xs), "ci95_reversed": list(clopper_pearson(len(rv), len(xs))),
                "n_reversed_by_named_down": sum(1 for x in rv if x["removed_by_named_down"]), "n_reversed_overshoot": sum(1 for x in rv if x["overshoot"]),
                "median_days_to_reversal": st.median(x["days_to_reversal"] for x in rv) if rv else None, "median_commits_to_reversal": st.median(x["commits_to_reversal"] for x in rv) if rv else None,
                "km_share_reversed_by_end": km, "km_median_commits_to_reversal": med,
                "n_not_reversed": len(xs) - len(rv), "median_follow_up_commits_not_reversed": st.median(x["follow_up_commits"] for x in xs if not x["reversed"]) if len(rv) < len(xs) else None,
                "n_elevated_at_tip": sum(1 for x in xs if x["elevated_at_tip"]), "share_elevated_at_tip": sum(1 for x in xs if x["elevated_at_tip"]) / len(xs)}
    S = {"per_corpus": {}}
    for t in sorted({x["corpus"] for x in up}): S["per_corpus"][t] = block([x for x in pool if x["corpus"] == t])
    S["pooled_corpus_commit_pairs"] = block(pool)
    bysha = defaultdict(list)
    for x in pool: bysha[x["sha"]].append(x)
    cm = {"n_commits": len(bysha), "all_corpora_reversed": 0, "none_reversed": 0, "mixed": 0, "elevated_at_tip_in_all": 0}
    for sha, xs in bysha.items():
        r = [x["reversed"] for x in xs]
        cm["all_corpora_reversed" if all(r) else "none_reversed" if not any(r) else "mixed"] += 1
        cm["elevated_at_tip_in_all"] += all(x["elevated_at_tip"] for x in xs)
    S["pooled_per_commit"] = cm; S["n_overlapping_excluded"] = len(up) - len(pool)
    return S
