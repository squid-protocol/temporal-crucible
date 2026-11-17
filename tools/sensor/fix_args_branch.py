#!/usr/bin/env python3
"""Where do fixes land, by parameter count and branch logic, and which functions break the pattern? (exploratory; see docs/sensor-overhaul/sensors/args_branch_errors.md)

    python tools/sensor/fix_args_branch.py REPO [REPO ...]      (C repositories; needs pickles from args_life_build.py with the complexity column)

Fix attribution is by function name from each hunk's header context (`git log -p -U0`: the enclosing function line git reports), joined to the
quarterly snapshot before the fix by (path, name). Units: a function present in snapshot s (source file, 5+ lines); outcome: touched by a fix commit of the
crucible's v3c events (events/<repo>_xc2.json) between snapshot s and s+1. Expected rates come from size alone (repository x size decile), so a ratio
above 1 means more fixes than a function of that size gets on average. Intervals are resampled for the 95% intervals."""
import collections
import json
import pickle
import re
import subprocess
import sys

import numpy as np
import pandas as pd

SP = "/tmp/gitgalaxy-scratch/claude/argl"
EV = "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/turn/events"
POOL = "/srv/storage_16tb/projects/temporal-crucible-pool"
TESTP = re.compile(r"(^|/)(tests?|examples?|docs?|fuzz\w*|bench\w*|testdata|samples?)(/|$)")
HUNK = re.compile(r"^@@ -\S+ \+\S+ @@ ?(.*)$")
IDENT = re.compile(r"([A-Za-z_]\w*)\s*$")
rng = np.random.default_rng(2982)
CLASSES = ("regression", "other-fix", "extrinsic", "latent")


def func_name(ctx):
    i = ctx.find("(")
    if i <= 0:
        return None
    m = IDENT.search(ctx[:i])
    return m.group(1) if m else None


def fix_hunks(repo, shas):
    """sha -> set of (path, function name) for the C-like files each fix commit changed."""
    want = set(shas)
    out = {}
    proc = subprocess.Popen(["git", "-C", repo, "log", "--no-merges", "-p", "-U0", "--no-color", "-M", "--format=@@COMMIT %H"], stdout=subprocess.PIPE, text=True, errors="replace")
    sha = None
    cur = None
    for line in proc.stdout:
        if line.startswith("@@COMMIT "):
            sha = line[9:].strip()
            cur = None
            if sha in want:
                out[sha] = set()
        elif sha in out:
            if line.startswith("+++ b/"):
                cur = line[6:].rstrip("\n")
                if not cur.endswith((".c", ".h")):
                    cur = None
            elif cur and line.startswith("@@"):
                m = HUNK.match(line.rstrip("\n"))
                n = func_name(m.group(1)) if m else None
                if n:
                    out[sha].add((cur, n))
    return out


def build(name):
    d = pickle.load(open(f"{SP}/{name}.pkl", "rb"))
    df = pd.DataFrame(d["rows"], columns=["s", "lin", "args", "loc", "path", "fn", "cx"])
    df = df[(df["loc"] >= 5) & ~df.path.map(lambda p: bool(TESTP.search(p))) & df.path.str.endswith((".c", ".h"))].copy()
    ct = np.array(d["ct"])
    ev = [e for e in json.load(open(f"{EV}/{name}_xc2.json"))["events"] if e["class"] in CLASSES]
    hunks = fix_hunks(f"{POOL}/{name}", [e["sha"] for e in ev])
    touched = collections.defaultdict(set)  # (interval, class) -> {(path, name)}
    n_h = n_m = 0
    keys = collections.defaultdict(set)
    for s_, p_, f_ in zip(df.s, df.path, df.fn):
        keys[int(s_)].add((p_, f_))
    for e in ev:
        i = int(np.searchsorted(ct, e["ct"], side="left")) - 1
        if not (0 <= i < len(ct) - 1):
            continue
        for k in hunks.get(e["sha"], ()):
            n_h += 1
            if k in keys.get(i, ()):
                n_m += 1
                touched[(i, e["class"])].add(k)
                touched[(i, "any")].add(k)
    df = df[df.s < len(ct) - 1].copy()
    for cls in CLASSES + ("any",):
        df["y_" + cls] = [(p, f) in touched.get((int(s), cls), ()) for s, p, f in zip(df.s, df.path, df.fn)]
    df["repo"] = name
    return df, n_h, n_m


def main():
    names = sys.argv[1:]
    parts, info = [], {}
    for nm in names:
        d, n_h, n_m = build(nm)
        parts.append(d)
        info[nm] = (len(d), n_h, n_m, float(d.y_any.mean()))
        print(f"{nm}: {len(d):,} function-intervals (source, 5+ lines); fix hunks with a function name {n_h:,}, found among that snapshot's functions {n_m:,} ({100 * n_m / max(n_h, 1):.0f}%); a function is touched by a fix in {100 * d.y_any.mean():.2f}% of intervals", flush=True)
    D = pd.concat(parts, ignore_index=True)
    D["dec"] = D.groupby("repo")["loc"].transform(lambda x: pd.qcut(x, 100, labels=False, duplicates="drop"))
    D["cl"] = D.repo + "/" + D.s.astype(str)
    D["abk"] = pd.cut(D.args, [-1, 0, 1, 2, 4, 1000], labels=["0", "1", "2", "3-4", "5+"])
    # branch logic within the function's size decile: its rank quartile
    D["bq"] = D.groupby(["repo", "dec"])["cx"].transform(lambda x: pd.qcut(x.rank(method="first"), 4, labels=False))
    D["bk"] = D.bq.map({0: "Q1 flat", 1: "Q2", 2: "Q3", 3: "Q4 branchy"})
    out = {}
    for cls in ("any",) + CLASSES:
        y = D["y_" + cls].astype(float)
        base = y.groupby([D.repo, D.dec]).transform("mean")
        D["e_" + cls] = base
    print(f"\npooled {len(D):,} function-intervals; fix touches: " + ", ".join(f"{c} {int(D['y_' + c].sum()):,}" for c in ("any",) + CLASSES))

    def oe(sub, cls):
        return float(sub["y_" + cls].sum() / sub["e_" + cls].sum()) if sub["e_" + cls].sum() > 0 else float("nan")

    def boot_cells(keycols, cls, B=300):
        g = D.groupby(keycols + ["cl"], observed=True).agg(o=("y_" + cls, "sum"), e=("e_" + cls, "sum")).reset_index()
        cells = {(k[0] if len(keycols) == 1 and isinstance(k, tuple) else k): v for k, v in g.groupby(keycols, observed=True)}
        cl = D.cl.unique()
        idx = {c: i for i, c in enumerate(cl)}
        res = {}
        for k, v in cells.items():
            o = np.zeros(len(cl))
            e = np.zeros(len(cl))
            for c, a, b in zip(v.cl, v.o, v.e):
                o[idx[c]] += a
                e[idx[c]] += b
            ests = []
            for _ in range(B):
                w = np.bincount(rng.integers(0, len(cl), len(cl)), minlength=len(cl))
                ee = (e * w).sum()
                ests.append((o * w).sum() / ee if ee > 0 else np.nan)
            res[k] = (o.sum() / e.sum() if e.sum() > 0 else float("nan"), float(np.nanpercentile(ests, 2.5)), float(np.nanpercentile(ests, 97.5)), int(o.sum()), len(v))
        return res

    for cls in ("any", "regression", "other-fix"):
        print(f"\n=== {cls.upper()} FIXES: observed / expected-from-size, by parameter count (columns) and branch logic against size (rows) ===")
        grid = boot_cells(["bk", "abk"], cls, B=200)
        cols = ["0", "1", "2", "3-4", "5+"]
        print(f"{'':12s}" + "".join(f"{c:>20s}" for c in cols))
        for r in ("Q1 flat", "Q2", "Q3", "Q4 branchy"):
            line = f"{r:12s}"
            for c in cols:
                v = grid.get((r, c))
                line += f"{v[0]:7.2f} [{v[1]:4.2f},{v[2]:4.2f}]" if v else f"{'':20s}"
                line += " "
            print(line)
        m1 = boot_cells(["abk"], cls, B=200)
        m2 = boot_cells(["bk"], cls, B=200)
        print("  margins: parameters " + ", ".join(f"{k} {v[0]:.2f}" for k, v in sorted(m1.items(), key=lambda kv: cols.index(kv[0]))) + "; branch rank " + ", ".join(f"{k} {v[0]:.2f}" for k, v in sorted(m2.items())))
        # where the pattern breaks: cells far from the product of their margins
        brk = []
        for (r, c), v in grid.items():
            pred = m2[r][0] * m1[c][0]
            if v[3] >= 30:
                brk.append((v[0] / pred, r, c, v[0], pred, v[3]))
        brk.sort(reverse=True)
        print("  cells furthest above the additive (product of margins) expectation: " + "; ".join(f"{r} x {c} params: {o:.2f} vs {p:.2f} (x{x:.2f}, {n} fixes)" for x, r, c, o, p, n in brk[:3]))
        print("  cells furthest below it: " + "; ".join(f"{r} x {c} params: {o:.2f} vs {p:.2f} (x{x:.2f}, {n} fixes)" for x, r, c, o, p, n in brk[-3:]))

    print("\n=== OUTLIER FUNCTIONS: observed fix touches against expected over the function's life (functions present in 8+ intervals) ===")
    L = D.groupby(["repo", "lin"]).agg(o=("y_any", "sum"), e=("e_any", "sum"), n=("s", "size"), path=("path", "last"), fn=("fn", "last"), args=("args", "max"), cx=("cx", "max"), loc=("loc", "max")).reset_index()
    L = L[(L.n >= 8) & (L.e >= 1.0)].copy()
    L["z"] = (L.o - L.e) / np.sqrt(L.e)
    print(f"  {len(L):,} long-lived functions with expected touches of 1+; touched more than expected by 3+ standard errors: {int((L.z >= 3).sum())} ({100 * (L.z >= 3).mean():.1f}%); fewer by 3+: {int((L.z <= -3).sum())} ({100 * (L.z <= -3).mean():.1f}%)")
    print("  most over-fixed:")
    for r in L.sort_values("z", ascending=False).head(12).itertuples():
        print(f"    {r.repo:10s} {r.fn:36s} {r.path[:44]:44s} fixes {int(r.o):3d} vs {r.e:5.1f} expected; params {int(r.args)}, branches {int(r.cx)}, lines {int(r.loc)}")
    hi = L[(L.cx >= L.cx.quantile(0.9)) & (L["loc"] >= L["loc"].quantile(0.9))]
    print(f"  large and branchy (top tenth of both): {len(hi)}; of them never touched by a fix though {hi.e.sum() / len(hi):.1f} were expected on average: {int((hi.o == 0).sum())}")
    print("  most under-fixed among those (expected, observed): " + "; ".join(f"{r.repo}/{r.fn} {r.e:.1f} vs {int(r.o)}" for r in hi[hi.o == 0].sort_values("e", ascending=False).head(8).itertuples()))
    ab = L[(L.args >= 5) & (L.z >= 3)]
    print(f"  over-fixed (3+ SE) with 5+ parameters: {len(ab)} of {int((L.z >= 3).sum())} over-fixed ({100 * len(ab) / max(int((L.z >= 3).sum()), 1):.0f}%) against {100 * (L.args >= 5).mean():.0f}% of all long-lived functions")


if __name__ == "__main__":
    main()
