#!/usr/bin/env python3
"""Evolution of a repository: a report from git history alone, richer with quarterly scans. Prototype for a GitGalaxy command.

    python tools/report/evolution_report.py --repo /path/to/clone --name curl --lang c --out OUT
        [--scans /path/to/scan_dir_with_snapshots.json]   (optional: adds size, births and deaths, age layers, heat, and the repair radius)
        [--blame 2500]                                     (optional: derive causes by blame for unnamed fix-like commits, sampled)
        [--cache DIR]                                      (cache of the one `git log -p` pass)

Definitions follow the research log (docs/sensor-overhaul/sensors/ripple_radius.md, "Accounting for all the work"); every figure carries a confidence label
and the report links to wiki pages that explain how it is computed."""
import argparse
import collections
import json
import os
import pickle
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sensor"))

EXTS = {"c": (".c", ".h", ".cc", ".cpp", ".hpp"), "go": (".go",), "python": (".py",), "rust": (".rs",)}
HUNK = re.compile(r"^@@ -\S+ \+\S+ @@ ?(.*)$")
IDENT = re.compile(r"([A-Za-z_]\w*)\s*$")
FIX = re.compile(r"\b(fix|fixes|fixed|bug|regression|crash|leak|overflow|race|deadlock|uaf|null)\b", re.I)
FMT = re.compile(r"\b(typo|typos|spelling|whitespace|style|checkpatch|indent(ation)?|licen[cs]e|docs?|documentation|comments?|copyright|spdx)\b", re.I)
FIXES_TRAILER = re.compile(r"^Fixes:\s*([0-9a-fA-F]{8,40})", re.M)
TESTPART = {"test", "tests", "testing", "__tests__", "spec", "specs", "testdata", "t"}
COMMENT = {"c": re.compile(r"^\s*(/\*|\*|//|$)"), "go": re.compile(r"^\s*(//|/\*|\*|$)"), "python": re.compile(r"^\s*(#|\"\"\"|'''|$)"), "rust": re.compile(r"^\s*(//|/\*|\*|$)")}
VERBS = {
    "feature": {"add", "introduce", "implement", "support", "enable", "allow", "new", "create", "expose", "provide", "extend", "export", "register", "enhance", "initial"},
    "restructure": {"convert", "move", "rename", "split", "merge", "refactor", "simplify", "cleanup", "clean", "consolidate", "rework", "reorganize", "reorganise", "unify", "replace", "switch", "use", "make", "factor", "separate", "change", "remove", "drop"},
    "optimization": {"optimize", "optimise", "speed", "improve", "reduce", "avoid", "skip", "cache", "batch", "prefetch", "defer", "shrink", "inline", "streamline", "limit", "tune", "increase", "decrease"},
    "fix": {"fix", "fixes", "correct", "handle", "prevent", "check", "validate", "ensure", "protect", "harden", "don't", "do", "never", "properly", "revert", "restore", "sanitize", "sanitise", "verify", "guard", "wait", "clear", "reset"},
}
GROUPS = ["organic", "sweeps", "fixes", "mechanical"]
CAT_GROUP = {"sweep": "sweeps", "revert": "mechanical", "tests only": "mechanical", "comment or whitespace only": "mechanical", "formatting, docs, licence (subject)": "mechanical"}


def func_name(ctx, lang):
    if lang == "c":
        i = ctx.find("(")
        m = IDENT.search(ctx[:i]) if i > 0 else None
        return m.group(1) if m else None
    if lang == "go":
        m = re.match(r"^func\s*(?:\([^)]*\)\s*)?(\w+)", ctx)
    elif lang == "python":
        m = re.search(r"\bdef\s+(\w+)", ctx)
    else:
        m = re.search(r"\bfn\s+(\w+)", ctx)
    return m.group(1) if m else None


def is_test(path):
    parts = path.lower().split("/")
    fn = parts[-1]
    return any(p in TESTPART for p in parts[:-1]) or fn.startswith("test_") or fn.endswith(("_test.go", "_test.py", "_test.c", "_test.rs", "test.c"))


def cause_verb(subject):
    seg = subject.split(": ")[-1].strip().lower()
    w = re.split(r"[\s,/(]", seg, 1)[0]
    for k, vs in VERBS.items():
        if w in vs:
            return k
    return "other"


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, errors="replace").stdout


def load_commits(repo):
    out = git(repo, "log", "--no-merges", "--format=%x1d%H%x1f%ct%x1f%ae%x1f%s%x1f%B%x1e")
    commits = {}
    for blk in out.split("\x1d")[1:]:
        head, _, rest = blk.partition("\x1e")
        p = head.split("\x1f", 4)
        if len(p) >= 5:
            commits[p[0]] = {"ct": int(p[1]), "author": p[2].lower(), "subject": p[3], "body": p[4]}
    return commits


def diff_pass(repo, lang, cache_file):
    """sha -> {funcs: [(path, function)], add, rem, comment_only, files: [path]} for code files, one streaming `git log -p -U0` pass, cached."""
    head = git(repo, "rev-parse", "HEAD").strip()
    if cache_file.exists():
        c = pickle.load(open(cache_file, "rb"))
        if c.get("head") == head:
            return c["data"]
    exts = EXTS[lang]
    cm = COMMENT[lang]
    proc = subprocess.Popen(["git", "-C", repo, "log", "--no-merges", "-p", "-U0", "--no-color", "-M", "--format=\x1dC %H"], stdout=subprocess.PIPE, text=True, errors="replace")
    data, sha, cur = {}, None, None

    def new(s):
        data[s] = {"funcs": set(), "add": 0, "rem": 0, "nc": 0, "files": set()}

    for line in proc.stdout:
        if line.startswith("\x1dC "):
            sha, cur = line[3:].strip(), None
            new(sha)
        elif sha:
            if line.startswith("+++ b/"):
                cur = line[6:].rstrip("\n")
                if cur.endswith(exts):
                    data[sha]["files"].add(cur)
                else:
                    cur = None
            elif cur and line.startswith("@@"):
                m = HUNK.match(line.rstrip("\n"))
                n = func_name(m.group(1), lang) if m else None
                if n:
                    data[sha]["funcs"].add((cur, n))
            elif cur and line[:1] in "+-" and not line.startswith(("+++", "---")):
                d = data[sha]
                if line[0] == "+":
                    d["add"] += 1
                else:
                    d["rem"] += 1
                if not cm.match(line[1:]):
                    d["nc"] += 1
    proc.wait()
    for d in data.values():
        d["funcs"] = sorted(d["funcs"])
        d["files"] = sorted(d["files"])
    pickle.dump({"head": head, "data": data}, open(cache_file, "wb"))
    return data


def resolve_pairs(commits):
    by12 = collections.defaultdict(list)
    for s in commits:
        by12[s[:8]].append(s)
    pairs = []
    for s, c in commits.items():
        for m in FIXES_TRAILER.finditer(c["body"]):
            h = m.group(1).lower()
            cand = [x for x in by12.get(h[:8], []) if x.startswith(h)]
            if len(cand) == 1 and cand[0] != s and commits[cand[0]]["ct"] < c["ct"]:
                pairs.append((s, cand[0]))
    return list(dict.fromkeys(pairs))


def blame_pairs(repo, lang, fixes, commits, n):
    import random
    import lang_validation as LV
    fixes = [(s, commits[s]["ct"]) for s in fixes]
    random.Random(7).shuffle(fixes)
    fixes = fixes[:n]
    from concurrent.futures import ProcessPoolExecutor
    pairs = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(LV.szz_worker, [(repo, lang if lang != "c" else "c", fixes[i : i + 15]) for i in range(0, len(fixes), 15)]):
            for fix, ind, _n, _t in res:
                if ind != fix and ind in commits and commits[ind]["ct"] < commits[fix]["ct"]:
                    pairs.append((fix, ind))
    return pairs, len(fixes)


def qlabel(ts):
    d = datetime.fromtimestamp(ts, timezone.utc)
    return f"{d.year} Q{(d.month - 1) // 3 + 1}"


def build(args):
    repo = args.repo
    lang = args.lang
    cache = Path(args.cache or Path(args.out) / "cache")
    cache.mkdir(parents=True, exist_ok=True)
    commits = load_commits(repo)
    diff = diff_pass(repo, lang, cache / f"diff_{args.name}.pkl")
    nf = {s: len(diff.get(s, {}).get("funcs", [])) for s in commits}
    named = resolve_pairs(commits)
    named_fix = {f for f, _ in named}
    trailer_fix = {s for s, c in commits.items() if FIXES_TRAILER.search(c["body"])}
    pairs = list(named)
    blame_info = None
    unnamed = [s for s, c in commits.items() if 1 <= nf[s] <= 60 and not c["subject"].lower().startswith("revert") and s not in trailer_fix and FIX.search(c["subject"])]
    blamed = {}
    if args.blame:
        bp, nb = blame_pairs(repo, lang, unnamed, commits, args.blame)
        blamed = {f: i for f, i in bp}
        blame_info = {"sampled": nb, "found": len(bp), "unnamed_fix_like": len(unnamed)}
        pairs += [p for p in bp]
    cited = {i for _, i in pairs}
    cat = {}
    for s, c in commits.items():
        d = diff.get(s)
        n = nf[s]
        subj = c["subject"]
        if n == 0:
            cat[s] = "none"
        elif n > 60:
            cat[s] = "sweep"
        elif subj.lower().startswith("revert"):
            cat[s] = "revert"
        elif s in trailer_fix:
            cat[s] = "fix, named cause"
        elif FIX.search(subj):
            cat[s] = "fix, cause by blame" if s in blamed else ("fix, no cause found" if args.blame else "fix, cause not searched")
        elif d["files"] and all(is_test(f) for f in d["files"]):
            cat[s] = "tests only"
        elif FMT.search(subj):
            cat[s] = "formatting, docs, licence (subject)"
        elif d["nc"] == 0 and (d["add"] + d["rem"]) > 0:
            cat[s] = "comment or whitespace only"
        elif d["add"] >= 3 * max(d["rem"], 1):
            cat[s] = "adds code"
        elif d["rem"] >= 3 * max(d["add"], 1):
            cat[s] = "removes code"
        else:
            cat[s] = "modifies"
    grp = {s: CAT_GROUP.get(k, "fixes" if k.startswith("fix") else ("organic" if k != "none" else None)) for s, k in cat.items()}
    total_edits = sum(nf.values())
    out = {"name": args.name, "lang": lang, "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "mode": "scans" if args.scans else "git-only"}
    out["span"] = [qlabel(min(c["ct"] for c in commits.values())), qlabel(max(c["ct"] for c in commits.values()))]
    out["commits"] = len(commits)
    out["commits_with_functions"] = sum(1 for s in commits if nf[s] > 0)
    out["function_edits"] = total_edits
    comp_e, comp_c = collections.Counter(), collections.Counter()
    for s, g in grp.items():
        if g:
            comp_e[g] += nf[s]
            comp_c[g] += 1
    out["composition_edits"] = {g: comp_e[g] / max(total_edits, 1) for g in GROUPS}
    out["composition_commits"] = {g: comp_c[g] / max(sum(comp_c.values()), 1) for g in GROUPS}
    out["categories"] = {k: {"commits": sum(1 for v in cat.values() if v == k), "edits": sum(nf[s] for s, v in cat.items() if v == k)} for k in sorted(set(cat.values()))}
    # label quality
    since = commits and sorted(c["ct"] for c in commits.values())[len(commits) // 2]
    out["label_quality"] = {
        "fixes_trailer_share_of_function_commits": len([s for s in trailer_fix if nf[s] > 0]) / max(out["commits_with_functions"], 1),
        "fixes_trailer_share_of_all": len(trailer_fix) / max(len(commits), 1),
        "cc_stable_share": float(np.mean(["cc: stable" in c["body"].lower() or "cc: <stable" in c["body"].lower() for c in commits.values()])),
        "reported_by_share": float(np.mean(["reported-by:" in c["body"].lower() for c in commits.values()])),
        "named_pairs": len(named),
        "unnamed_fix_like": len(unnamed),
        "blame": blame_info,
        "fix_like_subject_share": float(np.mean([bool(FIX.search(c["subject"])) for c in commits.values()])),
    }
    # sweeps
    sw = sorted(((nf[s], s) for s, k in cat.items() if k == "sweep"), reverse=True)[:12]
    out["largest_sweeps"] = [{"date": datetime.fromtimestamp(commits[s]["ct"], timezone.utc).strftime("%Y-%m-%d"), "functions": n, "subject": commits[s]["subject"][:96], "cited_as_cause": s in cited} for n, s in sw]
    out["sweep_count"] = sum(1 for v in cat.values() if v == "sweep")
    # lag, cause types
    pm = [(f, i) for f, i in pairs if nf[f] > 0 and nf[i] > 0]  # both commits change functions, as in the measured pairs of the research log
    lags = [(commits[f]["ct"] - commits[i]["ct"]) / 86400 for f, i in pm]
    bins = [(0, 7, "under a week"), (7, 30, "1-4 weeks"), (30, 90, "1-3 months"), (90, 180, "3-6 months"), (180, 365, "6-12 months"), (365, 730, "1-2 years"), (730, 1e9, "over 2 years")]
    out["lag_hist"] = [{"bin": lab, "pairs": int(sum(1 for x in lags if a <= x < b))} for a, b, lab in bins]
    out["lag_median_days"] = float(np.median(lags)) if lags else None
    out["pairs"] = len(pm)
    out["pairs_all"] = len(pairs)
    ct_rows = collections.defaultdict(list)
    for (f, i), lg in zip(pm, lags):
        ff, fi = set(diff.get(f, {}).get("funcs", [])), set(diff.get(i, {}).get("funcs", []))
        ct_rows[cause_verb(commits[i]["subject"])].append((bool(ff & fi) if ff and fi else None, lg))
    out["cause_types"] = [{"cause": k, "pairs": len(v), "same_function": float(np.mean([x[0] for x in v if x[0] is not None])) if any(x[0] is not None for x in v) else None, "median_lag": float(np.median([x[1] for x in v]))} for k, v in sorted(ct_rows.items(), key=lambda kv: -len(kv[1]))]
    # cc stable lag
    stab = [lg for (f, i), lg in zip(pm, lags) if "cc: stable" in commits[f]["body"].lower() or "cc: <stable" in commits[f]["body"].lower()]
    non = [lg for (f, i), lg in zip(pm, lags) if not ("cc: stable" in commits[f]["body"].lower() or "cc: <stable" in commits[f]["body"].lower())]
    out["stable_lag"] = {"with": float(np.median(stab)) if len(stab) >= 30 else None, "without": float(np.median(non)) if len(non) >= 30 else None, "n_with": len(stab)}
    # repeat spots
    fc = collections.Counter()
    for s, k in cat.items():
        if k.startswith("fix"):
            for f in diff.get(s, {}).get("funcs", []):
                fc[tuple(f)] += 1
    tot = sum(fc.values())
    out["repeat_spots"] = {"fix_edits": tot, "functions_fixed": len(fc), "share_in_fixed_2plus": sum(v for v in fc.values() if v >= 2) / tot if tot else None, "share_in_fixed_5plus": sum(v for v in fc.values() if v >= 5) / tot if tot else None}
    out["most_fixed"] = [{"function": k[1], "file": k[0], "fixes": v} for k, v in fc.most_common(10)]
    # size bands: organic commits at least 3 years old
    end = max(c["ct"] for c in commits.values())
    rows = [(nf[s], s in cited) for s, k in cat.items() if k in ("adds code", "removes code", "modifies") and commits[s]["ct"] <= end - 3 * 365 * 86400]
    bands = [(1, 1, "1 function"), (2, 3, "2-3"), (4, 10, "4-10"), (11, 30, "11-30"), (31, 60, "31-60")]
    out["size_bands"] = [{"band": lab, "commits": sum(1 for n, c in rows if a <= n <= b), "later_repaired": (float(np.mean([c for n, c in rows if a <= n <= b])) if any(a <= n <= b for n, c in rows) else None)} for a, b, lab in bands]
    out["size_bands_basis"] = "named" if not args.blame else "named + blame sample (understates)"
    # calendar-quarter series (git only)
    qs = collections.OrderedDict()
    for s, c in sorted(commits.items(), key=lambda kv: kv[1]["ct"]):
        q = qs.setdefault(qlabel(c["ct"]), {"commits": 0, "edits": collections.Counter(), "authors": collections.Counter(), "fix_commits": 0, "fix_with_test": 0})
        q["commits"] += 1
        q["authors"][c["author"]] += 1
        g = grp[s]
        if g:
            q["edits"][g] += nf[s]
        if cat[s].startswith("fix"):
            q["fix_commits"] += 1
            if any(is_test(f) for f in diff.get(s, {}).get("files", [])):
                q["fix_with_test"] += 1
    out["git_quarters"] = [{"label": k, "commits": v["commits"], **{f"edits_{g}": v["edits"][g] for g in GROUPS}, "authors": len(v["authors"]), "top_author_share": max(v["authors"].values()) / v["commits"], "fix_commits": v["fix_commits"], "fix_with_test": v["fix_with_test"]} for k, v in qs.items()]
    out["_internal"] = {"cat": cat, "nf": nf, "commits": commits, "diff": diff, "pairs": pairs, "cited": cited}
    return out


def scan_series(out, scans):
    sn = json.load(open(scans))
    internal = out["_internal"]
    commits, diff, cat, nf = internal["commits"], internal["diff"], internal["cat"], internal["nf"]
    cts = []
    keys_by_q = []
    for s in sn:
        con = sqlite3.connect(f"file:{s['db']}?mode=ro", uri=True)
        files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
        keys = {(files[f], n) for f, n in con.execute("SELECT file_id, func_name FROM function_data") if f in files}
        con.close()
        keys_by_q.append(keys)
        cts.append(int(subprocess.run(["git", "-C", out["_repo"], "show", "-s", "--format=%ct", s["commit"]], capture_output=True, text=True).stdout.strip()))
    first = {}
    for i, keys in enumerate(keys_by_q):
        for k in keys:
            first.setdefault(k, i)
    years = sorted({sn[i]["date"][:4] for i in set(first.values())})
    ct_sorted = sorted((c["ct"], s) for s, c in commits.items())
    quarters, edited_by_q, prev = [], [], None
    for i, s in enumerate(sn):
        keys = keys_by_q[i]
        q = {"label": s["label"], "date": s["date"], "functions": len(keys)}
        cnt = collections.Counter(sn[first[k]]["date"][:4] for k in keys)
        q["cohorts"] = {y: cnt.get(y, 0) for y in years}
        if prev is not None:
            lo, hi = cts[i - 1], cts[i]
            names_prev = collections.Counter(k[1] for k in prev)
            names_now = collections.Counter(k[1] for k in keys)
            q["births_new_code"] = sum(1 for k in keys - prev if k[1] not in names_prev)
            q["births_moved"] = sum(1 for k in keys - prev if k[1] in names_prev)
            q["deaths_removed"] = sum(1 for k in prev - keys if k[1] not in names_now)
            q["deaths_moved"] = sum(1 for k in prev - keys if k[1] in names_now)
            edited = set()
            e = collections.Counter()
            for t, c in ct_sorted:
                if lo < t <= hi:
                    g = CAT_GROUP.get(cat[c], "fixes" if cat[c].startswith("fix") else ("organic" if cat[c] != "none" else None))
                    if g:
                        e[g] += nf[c]
                        edited.update(tuple(f) for f in diff.get(c, {}).get("funcs", []))
            for g in GROUPS:
                q["edits_" + g] = e[g]
            edited_by_q.append(edited)
            q["edited_functions"] = len(edited & keys)
            recent = set().union(*edited_by_q[-4:]) if len(edited_by_q) >= 4 else None
            q["untouched_4q_share"] = (1 - len(recent & keys) / max(len(keys), 1)) if recent is not None else None
        prev = keys
        quarters.append(q)
    out["quarters"] = quarters
    out["cohort_years"] = years
    return out


def radius(out, scans):
    """Repair radius within 1 and 2 calls (optional): needs tools/sensor/blast_radius.py and a clone under its pool."""
    import blast_radius as BR
    import pandas as pd
    repo = out["_repo"]
    pool = Path(BR.POOL)
    if Path(repo).resolve().parent != pool.resolve():
        out["radius"] = None
        out["radius_note"] = "The repair radius needs the research pool layout; it is not computed for this repository."
        return out
    internal = out["_internal"]
    named = [p for p in internal["pairs"]]
    commits = internal["commits"]
    work = Path(out["_out"]) / "radius"
    work.mkdir(parents=True, exist_ok=True)
    pj = work / "pairs.json"
    json.dump([{"fix": f, "ind": i, "fix_ct": commits[f]["ct"], "ind_ct": commits[i]["ct"], "lag": (commits[f]["ct"] - commits[i]["ct"]) / 86400} for f, i in named], open(pj, "w"))
    snap_src = Path(scans).parent
    r = subprocess.run([sys.executable, str(HERE.parent / "sensor" / "blast_radius.py"), "run", "--repo", out["name"], "--tag", out["name"], "--pairs", str(pj), "--out", str(work), "--lang", out["lang"]], capture_output=True, text=True, env={**os.environ, "BLAST_SCANS": str(snap_src)})
    mp = work / "measure.pkl"
    if r.returncode or not mp.exists():
        out["radius"] = None
        out["radius_note"] = "The radius measurement did not run: " + (r.stderr or r.stdout)[-200:]
        return out
    m = pd.read_pickle(mp)
    m = m[m.status == "ok"].copy()
    rng = np.random.default_rng(2982)
    o = m[m.nFo > 0]
    res = {"measured": int(len(m)), "outside_set": int(len(o)), "same_function_share": float(m.same_func.mean())}
    for rel, lab in (("either1", "Within 1 call, any direction"), ("either2", "Within 2 calls"), ("callers1", "Callers, 1 call"), ("callees1", "Callees, 1 call")):
        rr = BR.ratio(o, rel, "eB", rng)
        res[rel] = None if rr is None else {"label": lab, "ratio": rr[0], "lo": rr[1], "hi": rr[2]}
    out["radius"] = res
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--lang", default="c", choices=list(EXTS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--scans")
    ap.add_argument("--blame", type=int, default=0)
    ap.add_argument("--cache")
    ap.add_argument("--link-base", default="https://github.com/squid-protocol/gitgalaxy/blob/main/docs/wiki")
    ap.add_argument("--radius", action="store_true")
    args = ap.parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    out = build(args)
    out["_repo"] = args.repo
    out["_out"] = args.out
    if args.scans:
        out = scan_series(out, args.scans)
        if args.radius:
            out = radius(out, args.scans)
    out["link_base"] = args.link_base
    out.pop("_internal_dump", None)
    internal = out.pop("_internal")
    out.pop("_repo")
    out.pop("_out")
    json.dump(out, open(Path(args.out) / f"{args.name}_evolution.json", "w"), indent=1, default=float)
    tpl = (HERE / "template.html").read_text()
    html = tpl.replace("__DATA__", json.dumps(out, separators=(",", ":"), default=float)).replace("__TITLE__", f"Evolution of {args.name}")
    (Path(args.out) / f"{args.name}_evolution.html").write_text(html)
    c = out["composition_edits"]
    print(f"{args.name}: {out['commits']:,} commits, {out['function_edits']:,} function edits, mode {out['mode']}; edits: " + ", ".join(f"{g} {100 * c[g]:.1f}%" for g in GROUPS) + f"; named pairs {out['pairs']:,}; median lag {out['lag_median_days'] and round(out['lag_median_days'])} d")


if __name__ == "__main__":
    main()
