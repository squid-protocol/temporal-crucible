#!/usr/bin/env python3
"""What kinds of changes? Fix mechanism (from the fix commit's text) and causing-change type (from the verb in its subject, plus size) for the kernel named-cause pairs,
crossed with the blast-radius measurements from blast_radius.py. Hypotheses Q1-Q6: docs/sensor-overhaul/sensors/ripple_radius.md ("What kinds of changes?"), fixed before this ran.

    python tools/sensor/change_kinds.py --measure /tmp/.../blast/linux [--spot 12]

Rule-based on purpose (interpretable, checkable by reading): ordered keyword rules on the subject first, then the first 600 characters of the body; every class is spot-checked."""
import argparse
import collections
import pickle
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

import os  # noqa: E402

REPO = os.environ.get("BLAST_REPO_PATH", "/srv/storage_16tb/projects/temporal-crucible-pool/linux")

FIX_RULES = [
    ("lifetime", r"use[- ]after[- ]free|double[- ]free|\buaf\b|memory leak|\bleaks?\b|\bleaked\b|ref(erence)? ?count|\brefcnt|\bkref|dangling|\bfree(s|d)?\b.*\b(twice|again|early|too early|before)|\bput\b.*\b(missing|extra|unbalanced)|unbalanced|\bptr_err\b.*leak"),
    ("concurrency", r"\brace(s|d)?\b|\bracy\b|data[- ]race|deadlock|\block(s|ed|ing)?\b|\bunlock|\bmutex|\bspinlock|\brcu\b|\batomic|\bbarrier|\bread_once|\bwrite_once|\bconcurren|synchroni[sz]|\bsleeping\b|\bpreempt|lockdep|\bireq\b"),
    ("null deref", r"null[- ]?(pointer|ptr)?[- ]?(deref|dereference)|\bnpd\b|\boops\b|\bnull\b.*\b(check|crash|pointer)|missing null|check for null|\bnull check|null return|returns? null|\berr_ptr\b|\bis_err\b"),
    ("bounds/overflow", r"out[- ]of[- ]bounds|\boob\b|overflow|underflow|buffer overrun|\boverrun|off[- ]by[- ]one|bounds? check|array index|index out|slab[- ]out|stack[- ]out|truncat|wrap(s|around)?\b|integer overflow|\bsize check|too (large|small|long)"),
    ("uninitialized", r"uninit|not initiali[sz]ed|\bkmsan\b|\binitiali[sz]e\b.*\b(variable|field|memory|struct)|zero[- ]?(init|out)|\bmemset\b"),
    ("error handling", r"error (path|handling|code|return|pointer)|\bunwind|\bgoto\b|failure path|on failure|on error|\bcleanup\b|return value|propagate|\berr(or)? check|unchecked|ignored error|not checked|missing (error|return)|\bret\b"),
    ("build/compile", r"build (error|failure|break|fix|warning)|compil(e|ation|er) (error|warning|fix|failure)|\bwarning\b|undefined (reference|symbol|behaviou?r)|\bw=1\b|\bsparse\b|kernel-doc|kconfig|link(ing)? (error|failure)|unused (variable|function|parameter)|\bnot used\b|-wunused|missing (prototype|declaration|include|header|export)|\bbuild\b"),
]
FIX_C = [(n, re.compile(p)) for n, p in FIX_RULES]
CAUSE_VERBS = {
    "feature": {"add", "introduce", "implement", "support", "enable", "allow", "new", "create", "expose", "provide", "extend", "export", "register", "enhance", "initial"},
    "restructure": {"convert", "move", "rename", "split", "merge", "refactor", "simplify", "cleanup", "clean", "consolidate", "rework", "reorganize", "reorganise", "unify", "replace", "switch", "use", "make", "factor", "separate", "change", "update", "rewrite", "migrate", "constify", "reorder", "abstract", "drop", "remove", "delete", "kill", "get", "deprecate", "fold", "pass", "let", "stop", "disable", "set"},
    "optimization": {"optimize", "optimise", "speed", "improve", "reduce", "avoid", "skip", "cache", "batch", "prefetch", "defer", "shrink", "inline", "streamline", "limit", "tune", "increase", "decrease", "bump"},
    "fix": {"fix", "fixes", "correct", "handle", "prevent", "check", "validate", "ensure", "protect", "harden", "don't", "do", "never", "properly", "revert", "restore", "sanitize", "sanitise", "verify", "guard", "wait", "clear", "reset", "zero", "initialize", "init"},
}


def fix_class(subject, body):
    s = subject.lower()
    for n, rx in FIX_C:
        if rx.search(s):
            return n, "subject"
    b = re.split(r"\n\s*\n", body.strip(), 1)[0][:600].lower() if body else ""
    for n, rx in FIX_C:
        if rx.search(b):
            return n, "body"
    return "other", "none"


def cause_type(subject):
    seg = subject.split(": ")[-1].strip().lower()
    word = re.split(r"[\s,/(]", seg, 1)[0]
    for n, vs in CAUSE_VERBS.items():
        if word in vs:
            return n, word
    return "other", word


def messages(shas, cache_file):
    cache = pickle.load(open(cache_file, "rb")) if Path(cache_file).exists() else {}
    need = [s for s in dict.fromkeys(shas) if s not in cache]
    if need:
        res = subprocess.run(["git", "-C", REPO, "log", "--no-walk=unsorted", "--stdin", "--format=%H%x1f%s%x1f%b%x1e"], input="\n".join(need) + "\n", capture_output=True, text=True, errors="replace").stdout
        for rec in res.split("\x1e"):
            p = rec.strip("\n").split("\x1f")
            if len(p) >= 2:
                cache[p[0]] = (p[1], p[2] if len(p) > 2 else "")
        pickle.dump(cache, open(cache_file, "wb"))
    return cache


def numstat(shas, cache_file):
    """sha -> (lines changed in .c/.h, files, subsystems crossed)."""
    cache = pickle.load(open(cache_file, "rb")) if Path(cache_file).exists() else {}
    need = [s for s in dict.fromkeys(shas) if s not in cache]
    if need:
        res = subprocess.run(["git", "-C", REPO, "log", "--no-walk=unsorted", "--stdin", "--numstat", "--format=@@C %H"], input="\n".join(need) + "\n", capture_output=True, text=True, errors="replace").stdout
        cur = None
        acc = {}
        for line in res.splitlines():
            if line.startswith("@@C "):
                cur = line[4:].strip()
                acc[cur] = [0, 0, set()]
            elif cur and "\t" in line:
                a, d, path = line.split("\t", 2)
                if path.endswith((".c", ".h")) and a.isdigit() and d.isdigit():
                    acc[cur][0] += int(a) + int(d)
                    acc[cur][1] += 1
                    acc[cur][2].add(BR.sub(path))
        for k, v in acc.items():
            cache[k] = (v[0], v[1], len(v[2]))
        pickle.dump(cache, open(cache_file, "wb"))
    return cache


def stat_row(d, label, rng):
    out = d[d.nFo > 0]
    r2 = BR.ratio(out, "either2", "eB", rng)
    c1 = BR.ratio(out, "callers1", "eB", rng)
    e1 = BR.ratio(out, "callees1", "eB", rng)
    f = lambda r: "   n/a      " if r is None else f"{r[0]:4.2f} [{r[1]:4.2f},{r[2]:4.2f}]"  # noqa: E731
    return (
        f"  {label:18s} {len(d):6d} {100 * len(d) / args_total:5.1f}%  lag {np.median(d.lag):5.0f} d   same function {100 * d.same_func.mean():3.0f}%   cross-file {100 * (~d.same_file.astype(bool)).mean():3.0f}%   "
        f"2 calls {f(r2)}{'' if r2 is None else f' ({100 * r2[4]:.0f}% vs {100 * r2[5]:.0f}%)'}   callers1 {f(c1)}   callees1 {f(e1)}"
    )


def main():
    global args_total
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", required=True)
    ap.add_argument("--spot", type=int, default=12)
    ap.add_argument("--with-body", action="store_true", help="also use the body-based calls (low precision)")
    a = ap.parse_args()
    a.with_body = bool(a.with_body)
    rng = np.random.default_rng(2982)
    df = pd.read_pickle(Path(a.measure) / "measure.pkl")
    df = df[df.status == "ok"].copy()
    args_total = len(df)
    shas = list(df.fix) + list(df.ind)
    msg = messages(shas, Path(a.measure) / "messages.pkl")
    ns = numstat(list(df.ind), Path(a.measure) / "numstat.pkl")
    fx = [fix_class(*msg.get(s, ("", ""))) for s in df.fix]
    df["fix_src"] = [x[1] for x in fx]
    # spot checks showed the body-based calls are right about a third of the time and the subject-based ones about 85 to 90%: the classes use the subject only
    df["fix_kind"] = [x[0] if x[1] == "subject" else ("other" if a.with_body is False else x[0]) for x in fx]
    cz = [cause_type(msg.get(s, ("", ""))[0]) for s in df.ind]
    df["cause_kind"] = [x[0] for x in cz]
    df["cause_verb"] = [x[1] for x in cz]
    df["ind_lines"] = [ns.get(s, (0, 0, 0))[0] for s in df.ind]
    df["ind_files"] = [ns.get(s, (0, 0, 0))[1] for s in df.ind]
    df["ind_subsys"] = [ns.get(s, (0, 0, 0))[2] for s in df.ind]
    df["cross"] = ~df.same_file.astype(bool)

    print(f"{len(df)} measured pairs")
    print("\n=== FIX MECHANISM (from the fix commit's subject, then the first 600 characters of its body) ===")
    print("  class                 pairs  share   lag (median)   same function   cross-file   radius within 2 calls, callers and callees within 1 call (against same-file functions)")
    for k in ["lifetime", "concurrency", "null deref", "bounds/overflow", "uninitialized", "error handling", "build/compile", "other"]:
        d = df[df.fix_kind == k]
        if len(d):
            print(stat_row(d, k, rng))
    print(f"  classified from the subject: {100 * (df.fix_src == 'subject').mean():.0f}%, from the body: {100 * (df.fix_src == 'body').mean():.0f}%, unclassified (other): {100 * (df.fix_src == 'none').mean():.0f}%")
    cl = df[df.fix_kind != "other"]
    top3 = cl[cl.fix_kind.isin(["lifetime", "null deref", "error handling"])]
    print(f"  lifetime + NULL/missing check + error handling: {100 * len(top3) / len(cl):.0f}% of classified fixes (Q1)")

    print("\n=== CAUSING-CHANGE TYPE (verb after the subsystem prefix of the causing commit's subject) ===")
    for k in ["feature", "restructure", "optimization", "fix", "other"]:
        d = df[df.cause_kind == k]
        if len(d):
            print(stat_row(d, k, rng))
    print("  most common verbs: " + ", ".join(f"{v} {n}" for v, n in collections.Counter(df.cause_verb).most_common(18)))

    print("\n=== SIZE OF THE CAUSING CHANGE ===")
    for lab, col, bins in (("lines changed in .c/.h", "ind_lines", [-1, 9, 49, 199, 1e9]), ("functions touched", "nI", [0, 1, 3, 9, 1e9]), ("subsystems crossed", "ind_subsys", [-1, 1, 2, 1e9])):
        df["_b"] = pd.cut(df[col], bins)
        print(f"  by {lab}:")
        for k, d in df.groupby("_b", observed=True):
            print(stat_row(d, str(k), rng))

    print("\n=== CAUSING TYPE x FIX MECHANISM: lift (observed / expected if independent), pairs with 80 or more ===")
    ct = pd.crosstab(df.cause_kind, df.fix_kind)
    tot = ct.values.sum()
    rows = []
    for c in ct.index:
        for f in ct.columns:
            n = ct.loc[c, f]
            exp = ct.loc[c].sum() * ct[f].sum() / tot
            if n >= 80 and exp > 0:
                rows.append((n / exp, c, f, n))
    for lift, c, f, n in sorted(rows, reverse=True)[:8] + sorted(rows)[:5]:
        print(f"  {c:13s} -> {f:16s} lift {lift:4.2f} (n {n})")

    print("\n=== CROSS-FILE SHARE BY FIX MECHANISM (Q4) against the overall share ===")
    base = df.cross.mean()
    for k in ["lifetime", "concurrency", "null deref", "bounds/overflow", "uninitialized", "error handling", "build/compile", "other"]:
        d = df[df.fix_kind == k]
        if len(d):
            print(f"  {k:16s} {100 * d.cross.mean():5.1f}% ({d.cross.mean() / base:4.2f} x the overall {100 * base:.1f}%)")

    print("\n=== SPOT CHECKS (random examples per class; the rule's call in brackets) ===")
    rr = np.random.default_rng(7)
    for k in ["lifetime", "concurrency", "null deref", "bounds/overflow", "uninitialized", "error handling", "build/compile"]:
        d = df[df.fix_kind == k]
        pick = d.iloc[rr.choice(len(d), min(a.spot, len(d)), replace=False)]
        print(f"  -- {k} ({len(d)} pairs)")
        for s, src in zip(pick.fix, pick.fix_src):
            print(f"     [{src[:4]}] {msg[s][0][:105]}")
    df.drop(columns=["fix_files", "ind_files"], errors="ignore").to_pickle(Path(a.measure) / "kinds.pkl")


if __name__ == "__main__":
    main()
