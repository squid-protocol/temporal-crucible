#!/usr/bin/env python3
"""The repair radius in other languages, with causes from SZZ-style blame instead of trailers. Hypotheses LG1-LG5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/lang_validation.py REPO [REPO ...] [--max-fixes N]
    repos: sphinx scapy sqlmap (python), prometheus (go), commons-lang commons-io (java), ripgrep (rust), dpdk curl (c, calibration)"""
import collections
import json
import os
import pickle
import random
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from tree_sitter_language_pack import get_parser

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402
import repair_structure as RS  # noqa: E402
import verify_functions as VF  # noqa: E402

B = "/tmp/gitgalaxy-scratch/claude"
CFG = {"sphinx": "python", "scapy": "python", "sqlmap": "python", "prometheus": "go", "commons-lang": "java", "commons-io": "java", "ripgrep": "rust", "dpdk": "c", "curl": "c", "libgit2": "c", "redis": "c", "libxml2": "c", "crispy-doom": "c", "dsda-doom": "c", "nugget-doom": "c", "doomretro": "c", "fastdoom": "c", "inter-doom": "c", "chocolate-doom": "c"}
EXT = {"python": (".py",), "go": (".go",), "java": (".java",), "rust": (".rs",), "c": (".c", ".h")}
NODES = {"python": {"function_definition"}, "go": {"function_declaration", "method_declaration"}, "java": {"method_declaration", "constructor_declaration"}, "rust": {"function_item"}, "c": {"function_definition"}}
TESTPART = {"test", "tests", "testing", "__tests__", "spec", "specs", "testdata"}
FIXRE = re.compile(r"\b(fix|fixes|fixed|bug|regression)\b", re.I)
rng = np.random.default_rng(2982)
_PARSERS = {}


def is_test(path):
    parts = path.lower().split("/")
    fn = parts[-1]
    return any(p in TESTPART for p in parts[:-1]) or fn.startswith("test_") or fn.endswith(("_test.go", "test.java", "tests.java", "_test.py", "_test.rs", "_test.c"))


def src_file(lang, path):
    return path.endswith(EXT[lang]) and not is_test(path)


def func_texts(lang, src):
    """{name: sorted list of hashes of the function texts} for every function definition (nested functions skipped)."""
    if lang not in _PARSERS:
        _PARSERS[lang] = get_parser(lang)
    tree = _PARSERS[lang].parse(src)
    out = collections.defaultdict(list)
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type in NODES[lang]:
            if lang == "c":
                nm = RS.func_name(n, src)
            else:
                x = n.child_by_field_name("name")
                nm = src[x.start_byte:x.end_byte].decode("utf8", "replace") if x is not None else None
            if nm:
                out[nm].append(hash(src[n.start_byte:n.end_byte]))
            continue
        stack.extend(n.children)
    return {k: sorted(v) for k, v in out.items()}


def name_status(repo, sha, lang):
    out = subprocess.run(["git", "-C", repo, "diff-tree", "-r", "-M", "--no-commit-id", "--name-status", sha], capture_output=True, text=True, errors="replace").stdout.splitlines()
    res = []
    for l in out:
        p = l.split("\t")
        if len(p) >= 2 and src_file(lang, p[-1]):
            res.append((p[0][0], p[1], p[-1]))
    return res


def szz_worker(job):
    repo, lang, fixes = job
    out = []
    for sha, _ct in fixes:
        files = [f for f in name_status(repo, sha, lang) if f[0] in "MR"]
        if not files or len(files) > 40:
            continue
        patch = subprocess.run(["git", "-C", repo, "diff", "-U0", "--no-color", "-M", f"{sha}^", sha, "--"] + [f[2] for f in files] + [f[1] for f in files if f[1] != f[2]], capture_output=True, text=True, errors="replace").stdout
        counts, old, nh = collections.Counter(), None, 0
        for l in patch.splitlines():
            if l.startswith("--- a/"):
                old = l[6:]
            elif l.startswith("@@") and old:
                m = re.match(r"@@ -(\d+)(?:,(\d+))? ", l)
                if not m:
                    continue
                a, b = int(m.group(1)), int(m.group(2)) if m.group(2) is not None else 1
                if b == 0 or nh >= 12:
                    continue
                nh += 1
                b = min(b, 200)
                try:
                    bl = subprocess.run(["git", "-C", repo, "blame", "-w", "-M", "--line-porcelain", "-L", f"{a},{a + b - 1}", f"{sha}^", "--", old], capture_output=True, text=True, errors="replace", timeout=90).stdout
                except subprocess.TimeoutExpired:
                    continue
                for bl_line in bl.splitlines():
                    mm = re.match(r"^([0-9a-f]{40}) \d+ \d+", bl_line)
                    if mm:
                        counts[mm.group(1)] += 1
        if counts:
            ind, n = counts.most_common(1)[0]
            out.append((sha, ind, n, sum(counts.values())))
    return out


def commit_worker(job):
    repo, lang, shas = job
    out = {}
    for sha in shas:
        files = name_status(repo, sha, lang)
        if not files or len(files) > 80:
            out[sha] = ([], 0, len(files))
            continue
        keys = []
        for status, old, new in files:
            if status not in "MR":
                continue
            a, b = VF.get(repo, f"{sha}:{new}"), VF.get(repo, f"{sha}^:{old}")
            if a is None or b is None:
                continue
            try:
                fa, fb = func_texts(lang, a), func_texts(lang, b)
            except Exception:  # noqa: BLE001
                continue
            keys += [(new, n) for n in fa if n in fb and fa[n] != fb[n]]
        ns = subprocess.run(["git", "-C", repo, "diff-tree", "-r", "-M", "--no-commit-id", "--numstat", sha], capture_output=True, text=True, errors="replace").stdout.splitlines()
        lines = 0
        for l in ns:
            p = l.split("\t")
            if len(p) >= 3 and src_file(lang, p[-1]) and p[0].isdigit() and p[1].isdigit():
                lines += int(p[0]) + int(p[1])
        out[sha] = (keys, lines, len(files))
    return out


def build(repo, max_fixes):
    lang = CFG[repo]
    path = f"{BR.POOL}/{repo}"
    cache = f"{B}/blast/lang_{repo}.pkl"
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    log = subprocess.run(["git", "-C", path, "log", "--no-merges", "--format=%H%x1f%ct%x1f%s"], capture_output=True, text=True, errors="replace").stdout.splitlines()
    ct = {}
    fixes = []
    for l in log:
        p = l.split("\x1f", 2)
        if len(p) == 3:
            ct[p[0]] = int(p[1])
            if FIXRE.search(p[2]) and not p[2].lower().startswith("revert"):
                fixes.append((p[0], int(p[1])))
    random.Random(7).shuffle(fixes)
    n_fix_all = len(fixes)
    fixes = fixes[:max_fixes]
    print(f"{repo} ({lang}): {len(ct)} commits, {n_fix_all} fix-like subjects, blaming {len(fixes)}", flush=True)
    pairs = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(szz_worker, [(path, lang, fixes[i : i + 15]) for i in range(0, len(fixes), 15)]):
            for fix, ind, n, tot in res:
                if ind != fix and ind in ct and ct[ind] < ct[fix]:
                    pairs.append({"fix": fix, "ind": ind, "fix_ct": ct[fix], "ind_ct": ct[ind], "lag": (ct[fix] - ct[ind]) / 86400, "n": n, "tot": tot})
    print(f"  {len(pairs)} fix-cause pairs from blame", flush=True)
    shas = list(dict.fromkeys(x for p in pairs for x in (p["fix"], p["ind"])))
    info = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(commit_worker, [(path, lang, shas[i : i + 25]) for i in range(0, len(shas), 25)]):
            info.update(res)
    pickle.dump((pairs, info), open(cache, "wb"))
    return pairs, info


def measure(repo, pairs, info):
    sn = json.load(open(f"{BR.B}/scan_{repo}/snapshots.json"))
    cf = f"{B}/blast/lang_{repo}_snapcts.npy"
    if os.path.exists(cf):
        cts = np.load(cf)
    else:
        cts = np.array([int(subprocess.run(["git", "-C", f"{BR.POOL}/{repo}", "show", "-s", "--format=%ct", x["commit"]], capture_output=True, text=True).stdout.strip()) for x in sn])
        np.save(cf, cts)
    by, meta, drop = collections.defaultdict(list), {}, collections.Counter()
    for pid, p in enumerate(pairs):
        I, F = info[p["ind"]][0], info[p["fix"]][0]
        s = int(np.searchsorted(cts, p["ind_ct"], side="left"))
        if s >= len(sn):
            drop["no snapshot"] += 1
        elif not I or not F:
            drop["no function in a commit"] += 1
        elif len(I) > 60 or len(F) > 30:
            drop["sweep"] += 1
        else:
            by[s].append({"pid": pid, "I": I, "F": F})
            meta[pid] = {"lag": p["lag"], "lines": info[p["ind"]][1]}
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(BR.measure_snapshot, [(sn[s]["db"], None, it) for s, it in sorted(by.items())]):
            rows += r
    df = pd.DataFrame(rows)
    if len(df):
        df["lag"] = df.pid.map(lambda i: meta[i]["lag"])
        df["lines"] = df.pid.map(lambda i: meta[i]["lines"])
    return df, dict(drop)


def summarize(df):
    ok = df[df.status == "ok"]
    o = ok[ok.nFo > 0]
    rr = {k: BR.ratio(o, k, "eB", rng) for k in ("either1", "either2", "callers1", "callees1")}
    x = o[~o.same_file.astype(bool)]
    far = {k: BR.ratio(x, k, "eB", rng) for k in ("callers1", "callees1")}
    sm, lg = o[o.lines < 30], o[o.lines >= 100]
    return len(ok), len(o), ok.same_func.mean(), rr, far, (BR.ratio(sm, "either2", "eB", rng), BR.ratio(lg, "either2", "eB", rng)), len(x)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mf = int(sys.argv[sys.argv.index("--max-fixes") + 1]) if "--max-fixes" in sys.argv else 2500
    args = [a for a in args if not a.isdigit()]
    allres = {}
    for repo in args:
        pairs, info = build(repo, mf)
        df, drop = measure(repo, pairs, info)
        allres[repo] = df
        if not len(df):
            print(f"  {repo}: nothing measured (dropped {drop})")
            continue
        nm, no, sf, rr, far, (sm, lg), nx = summarize(df)
        f = lambda r: f"{r[0]:.2f} [{r[1]:.2f},{r[2]:.2f}] (n {r[3]})" if r else "n/a"  # noqa: E731
        print(f"\n########## {repo} ({CFG[repo]}): {len(pairs)} pairs; dropped {drop}; measured {nm}; with a repaired function outside the changed set {no}; same function {100 * sf:.0f}% ##########")
        print(f"  within 1 call {f(rr['either1'])}\n  within 2 calls {f(rr['either2'])}\n  callers1 {f(rr['callers1'])}   callees1 {f(rr['callees1'])}")
        print(f"  repairs in a different file (n {nx}): callers1 {f(far['callers1'])}  callees1 {f(far['callees1'])}")
        print(f"  by size of the cause, within 2 calls: under 30 lines {f(sm)}; 100 or more {f(lg)}")
    print("\n=== VERDICTS ===")
    ref = {"dpdk": 1.57, "curl": 1.65}
    cal = {}
    for r in ("dpdk", "curl"):
        if r in allres and len(allres[r]):
            v = summarize(allres[r])[3]["either2"]
            cal[r] = v
    if cal:
        ok1 = all(abs(v[0] / ref[r] - 1) <= 0.25 for r, v in cal.items() if v)
        print("  LG1 calibration: " + ", ".join(f"{r} SZZ {v[0]:.2f} against trailer {ref[r]:.2f} ({100 * (v[0] / ref[r] - 1):+.0f}%)" for r, v in cal.items() if v) + f" (needs within 25%): {'supported' if ok1 else 'not supported'}")
    nonc = [r for r in allres if CFG[r] != "c" and len(allres[r])]
    lg2 = {}
    for r in nonc:
        if CFG[r] in ("python", "go", "java"):
            s = summarize(allres[r])
            lg2[r] = (s[1], s[3]["either2"])
    if lg2:
        print("  LG2 per repository (python, go, java): " + "; ".join(f"{r} {v[0]:.2f} [{v[1]:.2f},{v[2]:.2f}] (n {n})" if v else f"{r} untestable (n {n})" for r, (n, v) in lg2.items()) + f" (needs 1.3 with lower bound 1.1, n at least 100): {'supported' if all(v and n >= 100 and v[0] >= 1.3 and v[1] > 1.1 for n, v in lg2.values()) else 'not supported'}")
    if nonc:
        pooled = pd.concat([allres[r] for r in nonc], ignore_index=True)
        nm, no, sf, rr, far, (sm, lg), nx = summarize(pooled)
        print(f"  pooled non-C ({', '.join(nonc)}): within 2 calls {rr['either2'][0]:.2f} [{rr['either2'][1]:.2f},{rr['either2'][2]:.2f}] (n {no}); same function {100 * sf:.0f}%")
        c, e = far["callers1"], far["callees1"]
        if c and e:
            print(f"  LG3 different-file repairs, callers1 {c[0]:.2f} against callees1 {e[0]:.2f} (n {nx}): {'supported' if c[0] > e[0] else 'not supported'}")
        print(f"  LG4 pooled non-C radius {rr['either2'][0]:.2f} (needs 1.2 to 2.5): {'supported' if 1.2 <= rr['either2'][0] <= 2.5 else 'not supported'}")
        if sm and lg:
            print(f"  LG5 under 30 lines {sm[0]:.2f} against 100 or more {lg[0]:.2f} = {sm[0] / lg[0]:.2f} (needs 1.2): {'supported' if sm[0] / lg[0] >= 1.2 else 'not supported'}")
        print(f"  surprise bar (pooled non-C radius at or below 1.1): {'MET' if rr['either2'][0] <= 1.1 else 'not met'}")


if __name__ == "__main__":
    main()
