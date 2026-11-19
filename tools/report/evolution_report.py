#!/usr/bin/env python3
"""Evolution of a repository: a report from git history alone, richer with quarterly scans. Prototype for a GitGalaxy command.

    python tools/report/evolution_report.py --repo /path/to/clone --name curl --lang c --out OUT
        [--scans /path/to/scan_dir_with_snapshots.json]   (optional: adds size, births and deaths, age layers, heat, and the repair radius)
        [--blame 2500]                                     (optional: derive causes by blame for unnamed fix-like commits, sampled)
        [--cache DIR]                                      (cache of the one `git log -p` pass)

Definitions follow the research log (docs/sensor-overhaul/sensors/ripple_radius.md, "Accounting for all the work"); every figure carries a confidence label
and the report links to wiki pages that explain how it is computed."""
import argparse
import bisect
import collections
import gzip
import hashlib
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
COMMENT = {"c": re.compile(r"^\s*(/\*|\*(\s|/|$)|//|$)"), "go": re.compile(r"^\s*(//|/\*|\*|$)"), "python": re.compile(r"^\s*(#|\"\"\"|'''|$)"), "rust": re.compile(r"^\s*(//|/\*|\*|$)")}
VERBS = {
    "feature": {"add", "introduce", "implement", "support", "enable", "allow", "new", "create", "expose", "provide", "extend", "export", "register", "enhance", "initial"},
    "restructure": {"convert", "move", "rename", "split", "merge", "refactor", "simplify", "cleanup", "clean", "consolidate", "rework", "reorganize", "reorganise", "unify", "replace", "switch", "use", "make", "factor", "separate", "change", "remove", "drop"},
    "optimization": {"optimize", "optimise", "speed", "improve", "reduce", "avoid", "skip", "cache", "batch", "prefetch", "defer", "shrink", "inline", "streamline", "limit", "tune", "increase", "decrease"},
    "fix": {"correct", "handle", "prevent", "validate", "ensure", "protect", "harden", "restore", "sanitize", "sanitise", "verify", "guard", "reset"},
}
PARSER_VERSION = "2"  # bump when the diff parser or the rules change: part of the cache key
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
    return any(p in TESTPART for p in parts[:-1]) or fn.startswith("test_") or fn.endswith(("_test.go", "_test.py", "_test.c", "_test.cc", "_test.cpp", "_test.rs"))


def lemma(w):
    """Map a past-tense, -ing or plural verb to a listed bare verb ('added', 'adds', 'adding' -> 'add')."""
    known = set().union(*VERBS.values())
    for cand in (w, w[:-1], w[:-2], w[:-3], w[:-3] + "e", w[:-2] + "e", w[:-1] + "e"):
        if cand in known:
            return cand
    if len(w) > 3 and w[-1] == w[-2]:  # 'dropped' -> 'drop'
        for cand in (w[:-3], w[:-4]):
            if cand in known:
                return cand
    return w


def cause_verb(subject):
    """Type of a causing commit from its subject: a fix-like subject first, then the first verb (lemmatised); everything else is 'other'."""
    if FIX.search(subject):
        return "fix"
    seg = subject.split(": ")[-1].strip().lower()
    w = lemma(re.split(r"[\s,/(]", seg, 1)[0])
    for k, vs in VERBS.items():
        if w in vs:
            return k
    return "other"


def git(repo, *a):
    r = subprocess.run(["git", "-c", "core.quotepath=off", "-C", repo, *a], capture_output=True, text=True, errors="replace")
    if r.returncode:
        raise SystemExit(f"git {' '.join(a[:2])} failed in {repo}: {r.stderr.strip()[:200]}")
    return r.stdout


def load_commits(repo):
    out = git(repo, "log", "--no-merges", "--name-only", "--format=%x1d%H%x1f%ct%x1f%ae%x1f%s%x1f%B%x1e")
    commits = {}
    for blk in out.split("\x1d")[1:]:
        head, _, rest = blk.partition("\x1e")
        p = head.split("\x1f", 4)
        if len(p) >= 5:
            files = [f for f in rest.split("\n") if f.strip()]
            commits[p[0]] = {"ct": int(p[1]), "author": p[2].lower(), "subject": p[3], "body": p[4], "any_test": any(is_test(f) for f in files), "all_test": bool(files) and all(is_test(f) for f in files)}
    return commits


def diff_pass(repo, lang, cache_dir, name):
    """sha -> {funcs: [(path, function)], add, rem, nc, files: [path]} for code files, one streaming `git log -p -U0` pass over code paths, cached as gzip JSON.
    The cache key covers HEAD, the language, the parser version and the rule tables, so a stale cache is never reused."""
    head = git(repo, "rev-parse", "HEAD").strip()
    key = hashlib.sha1(json.dumps([head, lang, PARSER_VERSION, EXTS[lang], COMMENT[lang].pattern, HUNK.pattern], default=str).encode()).hexdigest()[:16]
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    cache_file = Path(cache_dir) / f"diff_{name}_{key}.json.gz"
    if cache_file.exists():
        try:
            with gzip.open(cache_file, "rt") as fh:
                data = json.load(fh)
            return {s: {**d, "funcs": [tuple(f) for f in d["funcs"]]} for s, d in data.items()}
        except (OSError, ValueError):
            pass
    exts = EXTS[lang]
    cm = COMMENT[lang]
    pathspec = ["--"] + [f"*{e}" for e in exts]
    proc = subprocess.Popen(["git", "-c", "core.quotepath=off", "-C", repo, "log", "--no-merges", "-p", "-U0", "--no-color", "-M", "--format=\x1dC %H", *pathspec], stdout=subprocess.PIPE, text=True, errors="replace")
    data, sha, cur = {}, None, None
    old = new = None
    in_header = False

    def clean(p):
        p = p.rstrip("\n").split("\t")[0]
        if p.startswith('"') and p.endswith('"'):
            p = p[1:-1]
        return p

    for line in proc.stdout:
        if line.startswith("\x1dC "):
            sha, cur, in_header = line[3:].strip(), None, False
            data[sha] = {"funcs": set(), "add": 0, "rem": 0, "nc": 0, "files": set()}
        elif sha is None:
            continue
        elif line.startswith("diff --git "):
            cur, old, new, in_header = None, None, None, True
        elif in_header and line.startswith("--- "):
            old = clean(line[4:])
            old = old[2:] if old.startswith("a/") else old
        elif in_header and line.startswith("+++ "):
            new = clean(line[4:])
            new = new[2:] if new.startswith("b/") else new
        elif line.startswith("@@"):
            if in_header:
                in_header = False
                path = new if new and new != "/dev/null" else old
                cur = path if path and path.endswith(exts) else None
                if cur:
                    data[sha]["files"].add(cur)
            if cur:
                m = HUNK.match(line.rstrip("\n"))
                n = func_name(m.group(1), lang) if m else None
                if n:
                    data[sha]["funcs"].add((cur, n))
        elif cur and not in_header and line[:1] in "+-":
            d = data[sha]
            if line[0] == "+":
                d["add"] += 1
            else:
                d["rem"] += 1
            if not cm.match(line[1:]):
                d["nc"] += 1
    proc.wait()
    if proc.returncode:
        raise SystemExit(f"git log -p failed in {repo}")
    for d in data.values():
        d["funcs"] = sorted(d["funcs"])
        d["files"] = sorted(d["files"])
    tmp = cache_file.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as f:
        json.dump(data, f)
    os.replace(tmp, cache_file)
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
            if len(cand) == 1 and cand[0] != s and commits[cand[0]]["ct"] <= c["ct"]:
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
    return pairs, fixes


def qlabel(ts):
    d = datetime.fromtimestamp(ts, timezone.utc)
    return f"{d.year} Q{(d.month - 1) // 3 + 1}"


def build(args):
    repo = args.repo
    lang = args.lang
    cache = Path(args.cache or Path(args.out) / "cache")
    cache.mkdir(parents=True, exist_ok=True)
    commits = load_commits(repo)
    diff = diff_pass(repo, lang, cache, args.name)
    EMPTY = {"funcs": [], "add": 0, "rem": 0, "nc": 0, "files": []}
    diff = collections.defaultdict(lambda: EMPTY, diff)
    if not commits:
        raise SystemExit(f"no commits found in {repo}")
    nf = {s: len(diff[s]["funcs"]) for s in commits}
    named = resolve_pairs(commits)
    named_fix = {f for f, _ in named}
    trailer_fix = {s for s, c in commits.items() if FIXES_TRAILER.search(c["body"])}
    pairs = list(named)
    blame_info = None
    unnamed = [s for s, c in commits.items() if 1 <= nf[s] <= 60 and not c["subject"].lower().startswith("revert") and s not in trailer_fix and FIX.search(c["subject"])]
    blamed = {}
    sampled_set = set()
    if args.blame:
        bp, sampled_fixes = blame_pairs(repo, lang, unnamed, commits, args.blame)
        blamed = {f: i for f, i in bp}
        sampled_set = {f for f, _ in sampled_fixes}
        blame_info = {"sampled": len(sampled_fixes), "found": len(bp), "unnamed_fix_like": len(unnamed), "coverage": len(sampled_fixes) / max(len(unnamed), 1)}
        pairs += [p for p in bp]
    cited = {i for _, i in pairs}
    cat = {}
    for s, c in commits.items():
        d = diff[s]
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
        elif FMT.search(subj):  # "fix typo", "fix whitespace": formatting, not a repair
            cat[s] = "formatting, docs, licence (subject)"
        elif FIX.search(subj):
            if s in blamed:
                cat[s] = "fix, cause by blame"
            elif s in sampled_set:
                cat[s] = "fix, no cause found"
            else:
                cat[s] = "fix, cause not searched"
        elif c["all_test"]:
            cat[s] = "tests only"
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
        ff, fi = set(diff[f]["funcs"]), set(diff[i]["funcs"])
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
            for f in diff[s]["funcs"]:
                fc[tuple(f)] += 1
    tot = sum(fc.values())
    out["repeat_spots"] = {"fix_edits": tot, "functions_fixed": len(fc), "share_in_fixed_2plus": sum(v for v in fc.values() if v >= 2) / tot if tot else None, "share_in_fixed_5plus": sum(v for v in fc.values() if v >= 5) / tot if tot else None}
    out["most_fixed"] = [{"function": k[1], "file": k[0], "fixes": v} for k, v in fc.most_common(10)]
    # size bands: organic commits at least 3 years old
    end = max(c["ct"] for c in commits.values())
    rows = [(nf[s], s in cited) for s, k in cat.items() if k in ("adds code", "removes code", "modifies") and commits[s]["ct"] <= end - 3 * 365 * 86400]
    bands = [(1, 1, "1 function"), (2, 3, "2-3"), (4, 10, "4-10"), (11, 30, "11-30"), (31, 60, "31-60")]
    out["size_bands"] = [{"band": lab, "commits": sum(1 for n, c in rows if a <= n <= b), "later_repaired": (float(np.mean([c for n, c in rows if a <= n <= b])) if any(a <= n <= b for n, c in rows) else None)} for a, b, lab in bands]
    out["pairs_dropped_no_function_share"] = 1 - (out["pairs"] / out["pairs_all"]) if out["pairs_all"] else None
    out["same_function_overall"] = (lambda v: float(np.mean(v)) if v else None)([bool(set(diff[f]["funcs"]) & set(diff[i]["funcs"])) for f, i in pm if diff[f]["funcs"] and diff[i]["funcs"]])
    citing = collections.Counter(i for f, i in pairs)
    for sw_row, (n_, s_) in zip(out["largest_sweeps"], sw):
        sw_row["fixes_citing"] = int(citing.get(s_, 0))
    fn_counts = collections.Counter(fc.values())
    out["repeat_spots"]["functions_fixed_2plus_share"] = (sum(v for k, v in fn_counts.items() if k >= 2) / len(fc)) if fc else None
    out["fix_definition"] = {"trailer_fixes": len(trailer_fix), "subject_only_fixes": len(unnamed), "trailer_habit": len(trailer_fix) >= 0.02 * len(commits)}
    out["blame_complete"] = (not args.blame and len(unnamed) == 0) or bool(blame_info and blame_info["coverage"] >= 0.999) or (not args.blame and len(named) > 0.5 * max(len(unnamed) + len(trailer_fix), 1))
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
            if commits[s]["any_test"]:
                q["fix_with_test"] += 1
    cur_q = qlabel(datetime.now(timezone.utc).timestamp())
    out["git_quarters"] = [{"label": k, "commits": v["commits"], **{f"edits_{g}": v["edits"][g] for g in GROUPS}, "authors": len(v["authors"]), "top_author_share": max(v["authors"].values()) / v["commits"], "fix_commits": v["fix_commits"], "fix_with_test": v["fix_with_test"], "partial": k == cur_q} for k, v in qs.items()]
    out["_internal"] = {"cat": cat, "nf": nf, "commits": commits, "diff": diff, "pairs": pairs, "cited": cited}
    return out


def scan_series(out, scans):
    sn = json.load(open(scans))
    def n_functions(snap):
        con = sqlite3.connect(f"file:{snap['db']}?mode=ro", uri=True)
        try:
            return con.execute("SELECT count(*) FROM function_data").fetchone()[0]
        finally:
            con.close()
    while len(sn) > 1 and n_functions(sn[0]) < 100:  # an almost empty first scan (the repository's first commits) would distort growth and age
        sn = sn[1:]
    internal = out["_internal"]
    commits, diff, cat, nf = internal["commits"], internal["diff"], internal["cat"], internal["nf"]
    cts = []
    keys_by_q = []
    com_stats = []
    fan = []
    arch_f = []
    arch_c = []
    last_extra = {}
    locs = {}
    for i, s in enumerate(sn):
        con = sqlite3.connect(f"file:{s['db']}?mode=ro", uri=True)
        files = {r[0]: r[1] for r in con.execute("SELECT id, file_path FROM file_data")}
        keys = {(files[f], n) for f, n in con.execute("SELECT file_id, func_name FROM function_data") if f in files}
        tl, cl, dl, pd_, fd_, hl = con.execute("SELECT sum(total_loc), sum(coding_loc), sum(doc_loc), sum(state_planned_debt), sum(state_fragile_debt), 0 FROM file_data").fetchone()
        nfun, hdr, docd = con.execute("SELECT count(*), sum(has_header_comment), sum(is_documented) FROM function_data").fetchone()
        com_stats.append({"code_lines": cl or 0, "comment_lines": dl or 0, "planned": pd_ or 0, "fragile": fd_ or 0, "functions": nfun or 0, "header": hdr or 0, "documented": docd or 0})
        fm = {}
        for f, nm, fi_, pr_ in con.execute("SELECT file_id, func_name, func_fan_in, func_pagerank FROM function_data"):
            if f in files:
                cur = fm.get(nm)
                if cur is None or (fi_ or 0) > cur[0]:
                    fm[nm] = (fi_ or 0, pr_ or 0.0, files[f])
        fan.append(fm)
        af = {}
        for f, nm, ar in con.execute("SELECT file_id, func_name, func_archetype FROM function_data"):
            if f in files and ar:
                af[(files[f], nm)] = ar
        arch_f.append(af)
        arch_c.append({files[fid]: ar for fid, ar in con.execute("SELECT id, composition_file_archetype FROM file_data") if ar and fid in files})
        if i == len(sn) - 1:
            locs = {(files[f], n): (l or 0) for f, n, l in con.execute("SELECT file_id, func_name, loc FROM function_data") if f in files}
            langs = collections.Counter(r[0] for r in con.execute("SELECT language FROM file_data") if r[0])
            last_extra = {"languages": dict(langs.most_common(6)), "files": sum(langs.values()), "public_share": (lambda r: (r[0] or 0) / max(r[1], 1))(con.execute("SELECT sum(is_public), count(*) FROM function_data").fetchone()), "unreferenced_share": (lambda r: (r[0] or 0) / max(r[1], 1))(con.execute("SELECT sum(func_fan_in = 0), count(*) FROM function_data").fetchone())}
        con.close()
        keys_by_q.append(keys)
        ctr = subprocess.run(["git", "-C", out["_repo"], "show", "-s", "--format=%ct", s["commit"]], capture_output=True, text=True).stdout.strip()
        if not ctr.isdigit():
            raise SystemExit(f"scan commit {s['commit'][:10]} ({s.get('label')}) is not in the repository")
        cts.append(int(ctr))
    first = {}
    for i, keys in enumerate(keys_by_q):
        for k in keys:
            first.setdefault(k, i)
    years = sorted({sn[i]["date"][:4] for i in set(first.values())})
    ct_sorted = sorted((c["ct"], s) for s, c in commits.items())
    ct_times = [t for t, _ in ct_sorted]
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
            for t, c in ct_sorted[bisect.bisect_right(ct_times, lo) : bisect.bisect_right(ct_times, hi)]:
                g = CAT_GROUP.get(cat[c], "fixes" if cat[c].startswith("fix") else ("organic" if cat[c] != "none" else None))
                if g:
                    e[g] += nf[c]
                    edited.update(tuple(f) for f in diff[c]["funcs"])
            for g in GROUPS:
                q["edits_" + g] = e[g]
            edited_by_q.append(edited)
            q["edited_functions"] = len(edited & keys)
            recent = set().union(*edited_by_q[-4:]) if len(edited_by_q) >= 4 else None
            old_keys = keys & keys_by_q[i - 4] if i >= 4 else None  # only functions that already existed four scans ago can be "untouched for four quarters"
            q["untouched_4q_share"] = (1 - len(recent & old_keys) / max(len(old_keys), 1)) if recent is not None and old_keys else None
            q["partial"] = (cts[i] - cts[i - 1]) < 60 * 86400
        prev = keys
        quarters.append(q)
    out["quarters"] = quarters
    out["cohort_years"] = years
    for q, cs in zip(quarters, com_stats):
        k = max(cs["code_lines"], 1) / 1000
        q["comments"] = {"density": cs["comment_lines"] / max(cs["code_lines"], 1), "planned_per_kloc": cs["planned"] / k, "fragile_per_kloc": cs["fragile"] / k, "header_share": (cs["header"] / cs["functions"]) if cs["functions"] else None, "documented_share": (cs["documented"] / cs["functions"]) if cs["functions"] else None}
    out["lifetimes"] = lifetimes(sn, keys_by_q, locs)
    out["hubs"] = hubs(sn, fan, first, keys_by_q, out["_repo"])
    out["archetypes"] = archetypes(sn, arch_f, arch_c, edited_by_q)
    out["current_extra"] = last_extra
    out["current_extra"]["top_dirs"] = [{"dir": d, "functions": c} for d, c in collections.Counter("/".join(k[0].split("/")[:2]) for k in keys_by_q[-1]).most_common(8)]
    out["current_extra"]["largest_functions"] = [{"function": k[1], "file": k[0], "lines": l} for l, k in sorted(((locs.get(k, 0), k) for k in keys_by_q[-1]), reverse=True)[:5]]
    return out


def km(durations, events, grid):
    """Kaplan-Meier survival at the grid points (years)."""
    d = np.array(durations, dtype=float)
    e = np.array(events, dtype=bool)
    order = np.argsort(d)
    d, e = d[order], e[order]
    n = len(d)
    surv, res, i = 1.0, [], 0
    uniq = np.unique(d[e])
    ptr = 0
    out = []
    for t in grid:
        while ptr < len(uniq) and uniq[ptr] <= t:
            at_risk = n - int(np.searchsorted(d, uniq[ptr], side="left"))
            deaths = int(((d == uniq[ptr]) & e).sum())
            surv *= 1 - deaths / max(at_risk, 1)
            ptr += 1
        out.append(surv)
    return out


def lifetimes(sn, keys_by_q, locs):
    """How long functions live, from their presence in the quarterly scans. Identity is (file, name): a function that moves or is renamed counts as a death and a birth."""
    sizes = [len(k) for k in keys_by_q]
    start = next((i for i, n in enumerate(sizes) if n >= 100), 0)
    from datetime import date as D
    dts = [D.fromisoformat(x["date"]) for x in sn]
    yrs = lambda a, b: (dts[b] - dts[a]).days / 365.25  # noqa: E731
    first, last = {}, {}
    for i in range(start, len(keys_by_q)):
        for k in keys_by_q[i]:
            first.setdefault(k, i)
            last[k] = i
    n = len(keys_by_q)
    groups = {"born": [], "initial": []}
    died = []
    for k, f in first.items():
        alive = last[k] == n - 1
        dur = yrs(f, n - 1) if alive else yrs(f, last[k] + 1)
        g = "initial" if f == start else "born"
        groups[g].append((dur, not alive))
        if not alive:
            died.append((dur, k, f, last[k] + 1, g))
    grid = [round(0.25 * j, 2) for j in range(0, int(yrs(start, n - 1) / 0.25) + 1)]
    out = {"since": sn[start]["label"], "years_observed": yrs(start, n - 1), "grid": grid, "curves": {}, "survive": {}, "counts": {}}
    for g, v in groups.items():
        if len(v) < 50:
            continue
        sv = km([d for d, _ in v], [e for _, e in v], grid)
        out["curves"][g] = sv
        out["counts"][g] = {"functions": len(v), "died": sum(1 for _, e in v if e), "alive": sum(1 for _, e in v if not e)}
        out["survive"][g] = {str(y): (sv[grid.index(y)] if y in grid else None) for y in (1, 2, 5, 10)}
        below = [t for t, sval in zip(grid, sv) if sval <= 0.5]
        out["counts"][g]["median_years"] = below[0] if below else None
    died.sort(reverse=True)
    out["longest_died"] = [{"function": k[1], "file": k[0], "years": round(d, 1), "born": sn[f]["label"] if g == "born" else "before " + sn[start]["label"], "died": sn[dq]["label"], "at_least": g == "initial"} for d, k, f, dq, g in died[:8]]
    old = sorted(((locs.get(k, 0), k) for k, f in first.items() if f == start and last[k] == n - 1), reverse=True)[:8]
    out["oldest_alive"] = [{"function": k[1], "file": k[0], "lines": l} for l, k in old]
    out["initial_still_alive"] = sum(1 for k, f in first.items() if f == start and last[k] == n - 1)
    out["alive_now"] = len(keys_by_q[-1])
    out["alive_now_older_than_observed"] = out["initial_still_alive"] / max(len(keys_by_q[-1]), 1)
    ages = [yrs(f, n - 1) for k, f in first.items() if last[k] == n - 1]
    out["median_age_alive_years"] = float(np.median(ages)) if ages else None
    return out


def archetypes(sn, arch_f, arch_c, edited_by_q):
    """Function types (the engine's function archetypes) now, over time, and how stable they are: share of functions (and of files, by composition label) that keep their label a year later, edited or not."""
    meta = json.load(open(HERE / "archetype_labels.json"))
    defs = {**meta["definitions"], **meta["older_set"]}
    n = len(arch_f)
    last = collections.Counter(arch_f[-1].values())
    total = sum(last.values()) or 1
    order = [k for k, _ in last.most_common()]
    keep = order[:8]
    series = {k: [sum(1 for v in arch_f[i].values() if v == k) for i in range(n)] for k in keep}
    series["Other types"] = [len(arch_f[i]) - sum(series[k][i] for k in keep) for i in range(n)]
    now = [{"label": k, "count": last[k], "share": last[k] / total, "meaning": defs.get(k, "no written definition for this label")} for k in order]
    L = 4

    def retention(maps, edited_of, min_n):
        ed_same = ed_tot = un_same = un_tot = 0
        trans = collections.Counter()
        for i in range(0, n - L):
            a, b = maps[i], maps[i + L]
            if len(a) < min_n:
                continue
            edited = set().union(*edited_by_q[i : i + L]) if i + L <= len(edited_by_q) else set()
            edp = {k[0] for k in edited}
            for k, v in a.items():
                w = b.get(k)
                if w is None:
                    continue
                if edited_of(k, edited, edp):
                    ed_tot += 1
                    ed_same += v == w
                    if v != w:
                        trans[(v, w)] += 1
                else:
                    un_tot += 1
                    un_same += v == w
        return {"edited_kept": ed_same / ed_tot if ed_tot else None, "edited_n": ed_tot, "unedited_kept": un_same / un_tot if un_tot else None, "unedited_n": un_tot, "transitions": [{"from": a, "to": b, "count": c} for (a, b), c in trans.most_common(6)]}
    ret_f = retention(arch_f, lambda k, ed, edp: k in ed, 1000)
    ret_c = retention(arch_c, lambda k, ed, edp: k in edp, 100)
    return {"definitions_source": meta["source"], "now": now, "mix": {"labels": list(series), "series": series}, "retention_function": ret_f, "retention_file": ret_c, "years": L / 4, "label_note": "Labels are the engine's; scans made by an older engine can carry older names (marked in the table)."}


def hubs(sn, fan, first, keys_by_q, repo=None):
    """Hubs by callers (fan-in) and by centrality (PageRank), tracked by function NAME so a file move does not look like a death: the lists now, how long hubs stay hubs, former hubs.
    `fan[i]` maps name -> (callers, pagerank, file) for the best-known definition of that name at scan i."""
    n = len(fan)
    from datetime import date as D
    d_last = D.fromisoformat(sn[-1]["date"])
    first_name = {}
    for (path, nm), f in first.items():
        first_name[nm] = min(f, first_name.get(nm, f))
    first_idx = min(first_name.values()) if first_name else 0
    top = lambda fm, which, m: [k for k, _ in sorted(fm.items(), key=lambda kv: -kv[1][which])[:m]]  # noqa: E731

    def row(nm, which):
        f = first_name.get(nm, n - 1)
        v = fan[-1][nm]
        return {"function": nm, "file": v[2], "callers": int(v[0]), "centrality": v[1], "age_years": round((d_last - D.fromisoformat(sn[f]["date"])).days / 365.25, 1), "since_first_scan": f == first_idx, "spark": [fan[i].get(nm, (0, 0, ""))[which] for i in range(n)], "spark_callers": [fan[i].get(nm, (0, 0, ""))[0] for i in range(n)]}
    now = {"callers": [row(k, 0) for k in top(fan[-1], 0, 10)], "centrality": [row(k, 1) for k in top(fan[-1], 1, 10)]}
    both = {r["function"] for r in now["callers"]} & {r["function"] for r in now["centrality"]}
    persist = {}
    for L, lab in ((4, "1 year"), (20, "5 years")):
        for which, name in ((0, "callers"), (1, "centrality")):
            inc, sur = [], []
            for i in range(0, n - L):
                if len(fan[i]) < 1000:
                    continue
                A = set(top(fan[i], which, max(int(len(fan[i]) * 0.01), 1)))
                B = set(top(fan[i + L], which, max(int(len(fan[i + L]) * 0.05), 1)))
                alive = A & set(fan[i + L])
                inc.append(len(A & B) / len(A))
                sur.append(len(A & B) / max(len(alive), 1))
            if inc:
                persist[f"{name}_{lab}"] = {"including_removed": float(np.mean(inc)), "among_survivors": float(np.mean(sur)), "n": len(inc)}
    now100 = set(top(fan[-1], 0, 100))
    peak = {}
    for i in range(n):
        for nm, v in fan[i].items():
            if v[0] > peak.get(nm, (0, 0, ""))[0]:
                peak[nm] = (v[0], i, v[2])
    former = []
    for nm, (fi, i, path) in sorted(peak.items(), key=lambda kv: -kv[1][0]):
        if nm in now100:
            continue
        former.append({"function": nm, "file": path, "peak_callers": int(fi), "peak_quarter": sn[i]["label"], "callers_now": int(fan[-1][nm][0]) if nm in fan[-1] else None, "gone": nm not in fan[-1]})
        if len(former) >= 5:
            break
    for fh in former:  # a function missing from the latest scan may still be in the code: the scanner skips some directories (for example any named log or logs)
        fh["still_defined_in"] = None
        if repo and fh["gone"]:
            r = subprocess.run(["git", "-C", repo, "grep", "-n", "-E", "-m1", f"^[A-Za-z_][A-Za-z0-9_ \\*]*\\b{re.escape(fh['function'])}\\(", "HEAD", "--", "*.c", "*.h", "*.cc", "*.cpp"], capture_output=True, text=True, errors="replace")
            if r.returncode == 0 and r.stdout.strip():
                fh["still_defined_in"] = r.stdout.split("\n")[0].split(":")[1] if r.stdout.count(":") >= 2 else None
    return {"now": now, "in_both_lists": len(both), "persistence": persist, "former": former, "labels": [x["label"] for x in sn], "identity": "function name"}


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


def build_facts(out, internal):
    """A deterministic fact sheet about the repository as it stands now: structured fields plus plain sentences, each derived from a stated field (no model, no guessing)."""
    commits, cat, nf = internal["commits"], internal["cat"], internal["nf"]
    cts = [c["ct"] for c in commits.values()]
    last_ct, first_ct = max(cts), min(cts)
    day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")  # noqa: E731
    y1, y2 = last_ct - 365 * 86400, last_ct - 730 * 86400
    cur = [s for s, c in commits.items() if c["ct"] > y1]
    prev = [s for s, c in commits.items() if y2 < c["ct"] <= y1]
    grp = {s: CAT_GROUP.get(k, "fixes" if k.startswith("fix") else ("organic" if k != "none" else None)) for s, k in cat.items()}
    edits = lambda ss: collections.Counter({g: sum(nf[s] for s in ss if grp[s] == g) for g in GROUPS})  # noqa: E731
    e_cur, e_prev = edits(cur), edits(prev)
    f = {"repository": out["name"], "language": out["lang"], "first_commit": day(first_ct), "latest_commit": day(last_ct), "age_years": round((last_ct - first_ct) / (365.25 * 86400), 1), "commits": out["commits"],
         "last_12_months": {"commits": len(cur), "authors": len({commits[s]["author"] for s in cur}), "function_edits": sum(e_cur.values()), "edits_by_kind": dict(e_cur), "sweeps": sum(1 for s in cur if cat[s] == "sweep"), "fix_commits": sum(1 for s in cur if cat[s].startswith("fix")),
                            "previous_12_months": {"commits": len(prev), "function_edits": sum(e_prev.values())}}}
    sent = []
    sent.append(f"{out['name']} has {out['commits']:,} commits over {f['age_years']} years (first {f['first_commit']}, latest {f['latest_commit']}).")
    l12 = f["last_12_months"]
    if l12["commits"]:
        trend = ""
        if l12["previous_12_months"]["function_edits"]:
            r = l12["function_edits"] / l12["previous_12_months"]["function_edits"]
            trend = f" (function edits {'up' if r > 1.1 else 'down' if r < 0.9 else 'about level'} {abs(r - 1) * 100:.0f}% on the year before)" if abs(r - 1) >= 0.1 else " (function edits about level with the year before)"
        sent.append(f"In the last 12 months: {l12['commits']:,} commits by {l12['authors']} authors, {l12['function_edits']:,} function edits, {l12['sweeps']} sweeps and {l12['fix_commits']:,} fix commits{trend}.")
    q = out.get("quarters")
    if q:
        ex = out["current_extra"]
        f["size"] = {"functions": q[-1]["functions"], "files": ex["files"], "languages": ex["languages"], "top_directories": ex["top_dirs"], "public_function_share": round(ex["public_share"], 3), "functions_never_called_share": round(ex["unreferenced_share"], 3)}
        langs = ", ".join(f"{k} ({v:,} files)" for k, v in list(ex["languages"].items())[:3])
        sent.append(f"Today the code base has {q[-1]['functions']:,} functions in {ex['files']:,} files; main languages: {langs}. The largest areas by functions are {', '.join(d['dir'] + ' (' + format(d['functions'], ',') + ')' for d in ex['top_dirs'][:3])}.")
        L = out.get("lifetimes", {})
        if L.get("median_age_alive_years") is not None:
            f["age_of_code"] = {"median_function_age_years": round(L["median_age_alive_years"], 1), "share_present_since_first_scan": round(L["alive_now_older_than_observed"], 3), "first_scan": L["since"]}
            sent.append(f"The median function is {L['median_age_alive_years']:.1f} years old (counted from the first scan {L['since']} or its birth); {L['alive_now_older_than_observed'] * 100:.0f}% of today's functions were already there at the first scan.")
        H = out["hubs"]
        a, c = H["now"]["callers"][0], H["now"]["centrality"][0]
        slim = lambda rows: [{k: v for k, v in h.items() if not k.startswith("spark")} for h in rows]  # noqa: E731  (copies: the page still needs the sparklines)
        f["hubs"] = {"most_called": slim(H["now"]["callers"][:5]), "most_central": slim(H["now"]["centrality"][:5]), "in_both_lists_of_ten": H["in_both_lists"], "persistence": H["persistence"], "former_hubs": H["former"][:3]}
        sent.append(f"The most-called function is {a['function']} ({a['callers']:,} callers, {a['file']}); the most central is {c['function']} ({c['file']}). {H['in_both_lists']} of the top ten appear in both lists.")
        pr = H["persistence"].get("callers_1 year")
        if pr:
            sent.append(f"Hubs are stable here: of the top 1% most-called functions, {pr['including_removed'] * 100:.0f}% were still in the top 5% a year later (a function that disappears counts as not persisting; moves between files do not).")
        if H["former"]:
            fh = H["former"][0]
            sent.append(f"{fh['function']} was once a hub (peak {fh['peak_callers']:,} callers in {fh['peak_quarter']}); " + (f"it is still defined in {fh['still_defined_in']} but that directory is not in the latest scan, so its callers are not counted now." if fh.get("still_defined_in") else ("it is no longer in the code." if fh["gone"] else f"it is down to {fh['callers_now']:,} callers now.")))
        A = out.get("archetypes")
        if A and A["now"]:
            top3 = A["now"][:3]
            f["function_types"] = {"most_common": [{"label": t["label"], "share": round(t["share"], 3)} for t in top3], "kept_type_after_a_year": {"edited": A["retention_function"]["edited_kept"], "unedited": A["retention_function"]["unedited_kept"]}}
            sent.append("The most common function types are " + ", ".join(f"{t['label']} ({t['share'] * 100:.0f}%)" for t in top3) + (f"; {A['retention_function']['unedited_kept'] * 100:.1f}% of untouched functions and {A['retention_function']['edited_kept'] * 100:.0f}% of edited ones kept their type a year later." if A["retention_function"]["edited_kept"] is not None and A["retention_function"]["unedited_kept"] is not None else "."))
        f["largest_functions"] = ex["largest_functions"]
        lf = ex["largest_functions"][0]
        sent.append(f"The largest function is {lf['function']} ({lf['lines']:,} lines, {lf['file']}).")
        cm = q[-1].get("comments")
        if cm:
            f["comments"] = {"comment_lines_per_code_line": round(cm["density"], 3), "functions_with_comment_above": round(cm["header_share"], 3) if cm["header_share"] is not None else None, "todo_markers_per_kloc": round(cm["planned_per_kloc"], 2), "fragile_markers_per_kloc": round(cm["fragile_per_kloc"], 2)}
    if out.get("most_fixed"):
        mf = out["most_fixed"][0]
        f["most_repaired_function"] = mf
        sent.append(f"The most repaired function is {mf['function']} ({mf['fixes']} fix commits, {mf['file']}).")
    ce = out["composition_edits"]
    f["work_mix"] = {k: round(v, 3) for k, v in ce.items()}
    if out.get("lag_median_days") is not None and out.get("pairs", 0) >= 30:
        f["median_days_from_change_to_fix"] = round(out["lag_median_days"])
        sent.append(f"Across its history {ce['organic'] * 100:.0f}% of function edits are organic change, {ce['sweeps'] * 100:.0f}% sweeps and {ce['fixes'] * 100:.0f}% fixes; a fix arrives a median {round(out['lag_median_days'])} days after the change that caused it.")
    f["stage"] = None
    f["stage_note"] = "A building / maturing / maintenance label needs thresholds calibrated on a reference set; not computed yet."
    f["sentences"] = sent
    f["reliability"] = {"call_graph": {"c": "checked against libclang: hubs, ranks and coupling agree", "java": "hubs sensitive to overloaded names; indicative", "go": "not yet evaluated", "python": "not yet evaluated", "rust": "records about a third of resolvable calls; indicative"}.get(out["lang"], "not evaluated")}
    return f


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
    ap.add_argument("--gif", help="optional GIF of the call graph over time (from tools/report/make_gif.py), embedded in the page if under 9 MB")
    args = ap.parse_args()
    if not re.fullmatch(r"[\w.-]+", args.name):
        ap.error("--name may contain only letters, digits, dot, underscore and hyphen")
    if not args.link_base.startswith("https://"):
        ap.error("--link-base must start with https://")
    Path(args.out).mkdir(parents=True, exist_ok=True)
    out = build(args)
    out["_repo"] = args.repo
    out["_out"] = args.out
    if args.scans:
        out = scan_series(out, args.scans)
        if args.radius:
            out = radius(out, args.scans)
    out["facts"] = build_facts(out, out["_internal"])
    out["link_base"] = args.link_base
    if args.gif and Path(args.gif).exists():
        import base64
        raw = Path(args.gif).read_bytes()
        if len(raw) <= 9_000_000:
            out["gif_data_uri"] = "data:image/gif;base64," + base64.b64encode(raw).decode()
            out["gif_bytes"] = len(raw)
    out.pop("_internal_dump", None)
    internal = out.pop("_internal")
    out.pop("_repo")
    out.pop("_out")
    uri = out.pop("gif_data_uri", None)
    json.dump(out, open(Path(args.out) / f"{args.name}_evolution.json", "w"), indent=1, default=float)
    if uri:
        out["gif_data_uri"] = uri
    tpl = (HERE / "template.html").read_text()
    payload = json.dumps(out, separators=(",", ":"), default=float).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = tpl.replace("__TITLE__", f"Evolution of {args.name}").replace("__DATA__", payload)  # title first: the payload may contain any text
    (Path(args.out) / f"{args.name}_evolution.html").write_text(html)
    c = out["composition_edits"]
    print(f"{args.name}: {out['commits']:,} commits, {out['function_edits']:,} function edits, mode {out['mode']}; edits: " + ", ".join(f"{g} {100 * c[g]:.1f}%" for g in GROUPS) + f"; named pairs {out['pairs']:,}; median lag {out['lag_median_days'] and round(out['lag_median_days'])} d")


if __name__ == "__main__":
    main()
