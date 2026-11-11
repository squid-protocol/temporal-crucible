#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Structural footprint of declared-AI vs other commits (EXPLORATORY, outcome-blind).

For every non-merge commit since 2024-01-01 in the C/C++ adopter and control repos, every function the commit touches
is read before (parent) and after (commit) with tree-sitter and the engine's C/C++ rules, as LAT-F does
(lat_eval._worker: rule presence on the Prism code stream). Per touched function:
- modified / born / deleted;
- signal set before and after, with LAT's frozen lattice (family, rung k) on both sides: did the shape move, did the
  family change, how did the rung change;
- counts of defensive and risk signals before and after;
- callee names (tree-sitter call expressions) before and after: callees added; whether an added callee is defined
  in the same file;
- lines changed inside the function.
Declared AI = an AI tool named in a Co-authored-by / Assisted-by / Generated-by line (tools/ai_comments.tool_of).
Undeclared AI use is in the "other" group and dilutes contrasts.

    GITGALAXY_PATH=$E PYTHONPATH=$E SFS_SRC=<sfs src> <venv>/bin/python tools/ai_structure.py
    -> docs/ai_structure_exploratory.md
"""
from __future__ import annotations

import multiprocessing
import pathlib
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from ai_comments import EXCL, tool_of  # noqa: E402
from chg2_eval import SIG  # noqa: E402
from chg_eval import CEXT, CPPEXT, _fname, _parser  # noqa: E402
from lat_eval import TREES_SHA, Lattice, _worker  # noqa: E402

ADOPTERS = ("harfbuzz", "openssl", "redis", "ndpi")
CONTROLS = ("postgres", "libxml2", "curl", "libgit2")
SINCE = "2024-01-01"
COUNTED = ("def_safety", "state_safety_neg", "state_bailout_hits", "state_pointers", "state_memory_alloc",
           "struct_branch", "state_cast_hits", "def_cleanup")
DEFENSIVE = ("def_safety", "state_safety_neg", "state_bailout_hits", "def_cleanup")
SIZE_EDGES = (2, 8, 32, 128)
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def git(repo, *a, text=True):
    p = subprocess.run(["git", "-C", str(repo), *a], capture_output=True)
    return p.stdout.decode("utf-8", "replace") if text else p.stdout


def lang(r, path):
    return "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"


def callee(node):
    f = node.child_by_field_name("function")
    while f is not None and f.type in ("field_expression", "qualified_identifier", "template_function",
                                       "parenthesized_expression", "pointer_expression"):
        nxt = (f.child_by_field_name("field") or f.child_by_field_name("name")
               or f.child_by_field_name("argument") or (f.children[-1] if f.children else None))
        if nxt is None or nxt is f:
            break
        f = nxt
    return f.text.decode("utf-8", "replace") if f is not None and f.type in ("identifier", "field_identifier") else None


def functions(raw, lg):
    """name -> (start_line0, end_line0, callees) for the first definition of each name."""
    out = {}
    stack = [_parser(lg).parse(raw).root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm and nm not in out:
                calls, st = set(), [n]
                while st:
                    x = st.pop()
                    if x.type == "call_expression":
                        c = callee(x)
                        if c:
                            calls.add(c)
                    st.extend(x.children)
                out[nm] = (n.start_point[0], n.end_point[0], calls)
            continue
        stack.extend(n.children)
    return out


def signals(W, text_lines, a, b, lg):
    body = "\n".join(text_lines[a:b + 1])
    try:
        code = W["prism"].split_streams(body, lg)["code_stream"]
    except Exception:
        code = body
    pres, cnt = set(), {}
    for k, rx in W["rules"][lg].items():
        col = W["col"](k)
        if col in COUNTED:
            n = len(rx.findall(code))
            cnt[col] = cnt.get(col, 0) + n
            if n:
                pres.add(col)
        elif rx.search(code):
            pres.add(col)
    return frozenset(pres), cnt


def commit_task(t):
    r, sha = t
    W = _worker()
    repo = POOL_DIR / r
    parent = git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return r, sha, None
    old_l, new_l, old, new = defaultdict(set), defaultdict(set), None, None
    pair = {}
    for ln in git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        if ln.startswith("--- "):
            old = None if ln[4:] == "/dev/null" else ln[6:]
        elif ln.startswith("+++ "):
            new = None if ln[4:] == "/dev/null" else ln[6:]
            key = new or old
            if key and key.endswith(CEXT + CPPEXT) and not EXCL.search(key):
                pair[key] = (old, new)
        elif ln.startswith("@@"):
            m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", ln)
            key = new or old
            if not m or key not in pair:
                continue
            s, n = int(m.group(1)), int(m.group(2) or 1)
            s2, n2 = int(m.group(3)), int(m.group(4) or 1)
            old_l[key].update(range(s, s + n) if n > 0 else [max(s, 1)])
            if n2 > 0:
                new_l[key].update(range(s2, s2 + n2))
    rows, files = [], 0
    for key, (o, nw) in pair.items():
        lg = lang(r, key)
        rb = git(repo, "show", f"{parent}:{o}", text=False) if o else b""
        ra = git(repo, "show", f"{sha}:{nw}", text=False) if nw else b""
        if len(rb) > 2_000_000 or len(ra) > 2_000_000:
            continue
        fb = functions(rb, lg) if rb else {}
        fa = functions(ra, lg) if ra else {}
        lb = rb.decode("utf-8", "replace").split("\n")
        la = ra.decode("utf-8", "replace").split("\n")
        files += 1
        local_after = set(fa)
        for nm in set(fb) | set(fa):
            bsp, asp = fb.get(nm), fa.get(nm)
            ch_old = sum(1 for x in old_l[key] if bsp and bsp[0] + 1 <= x <= bsp[1] + 1) if o else 0
            ch_new = sum(1 for x in new_l[key] if asp and asp[0] + 1 <= x <= asp[1] + 1)
            if bsp and asp and not (ch_old or ch_new):
                continue
            if bsp and not asp:
                rows.append({"kind": "deleted", "loc_b": bsp[1] - bsp[0] + 1})
                continue
            sa, ca = signals(W, la, asp[0], asp[1], lg)
            rec = {"kind": "modified" if bsp else "born", "changed": ch_old + ch_new, "loc_a": asp[1] - asp[0] + 1,
                   "sig_a": sa, "cnt_a": ca, "n_callees_a": len(asp[2])}
            if bsp:
                sb, cb = signals(W, lb, bsp[0], bsp[1], lg)
                added = asp[2] - bsp[2]
                rec.update(sig_b=sb, cnt_b=cb, loc_b=bsp[1] - bsp[0] + 1, callees_added=len(added),
                           callees_removed=len(bsp[2] - asp[2]), callees_added_local=len(added & local_after))
            rows.append(rec)
    return r, sha, {"files": files, "fns": rows}


def sbin(n):
    return sum(n > c for c in SIZE_EDGES)


def std_mean(target, ref, val, size):
    """Mean of val over ref re-weighted to target's size-bin mix."""
    w = Counter(sbin(size(x)) for x in target)
    acc = tot = 0.0
    for b, k in w.items():
        xs = [val(x) for x in ref if sbin(size(x)) == b]
        if xs:
            acc += k * float(np.mean(xs))
            tot += k
    return acc / tot if tot else np.nan


def main() -> int:
    L_ = Lattice()
    cols = sorted(set(SIG))
    repos = ADOPTERS + CONTROLS
    meta = []
    for r in repos:
        txt = git(POOL_DIR / r, "log", "--no-merges", f"--since={SINCE}", "--format=%x1e%H%x1f%ct%x1f%ae%x1f%B")
        for rec in txt.split("\x1e")[1:]:
            h, ct, ae, msg = rec.split("\x1f", 3)
            meta.append({"r": r, "sha": h, "ct": int(ct), "author": ae.strip().lower(), "tool": tool_of(msg)})
    log(f"commits {len(meta):,}; declared AI {sum(1 for m in meta if m['tool']):,}")
    with multiprocessing.get_context("fork").Pool(8) as p:
        res = {(r, s): v for r, s, v in p.imap_unordered(commit_task, [(m["r"], m["sha"]) for m in meta], chunksize=8)}
    F, CM = [], []
    for m in meta:
        v = res.get((m["r"], m["sha"]))
        if not v or not v["fns"]:
            continue
        CM.append(dict(m, files=v["files"], n_mod=sum(f["kind"] == "modified" for f in v["fns"]),
                       n_born=sum(f["kind"] == "born" for f in v["fns"]),
                       n_del=sum(f["kind"] == "deleted" for f in v["fns"]),
                       changed=sum(f.get("changed", 0) for f in v["fns"])))
        for f in v["fns"]:
            if f["kind"] != "deleted":
                F.append(dict(f, r=m["r"], sha=m["sha"], ct=m["ct"], author=m["author"], tool=m["tool"]))
    log(f"commits with touched functions {len(CM):,}; function changes {len(F):,}")
    # lattice on both sides
    def lat(sets):
        P = np.array([[c in s for c in cols] for s in sets], bool).reshape(len(sets), len(cols))
        fam, k, _ = L_.assign(P, cols)
        return fam, k
    mod = [f for f in F if f["kind"] == "modified"]
    fb, kb = lat([f["sig_b"] for f in mod])
    fa, ka = lat([f["sig_a"] for f in mod])
    for f, a, b, c, d in zip(mod, fb, fa, kb, ka):
        f.update(moved=f["sig_a"] != f["sig_b"], fam_change=int(a) != int(b), dk=int(d) - int(c),
                 gained=len(f["sig_a"] - f["sig_b"]), lost=len(f["sig_b"] - f["sig_a"]),
                 d_def=sum(f["cnt_a"].get(s, 0) - f["cnt_b"].get(s, 0) for s in DEFENSIVE),
                 d_branch=f["cnt_a"].get("struct_branch", 0) - f["cnt_b"].get("struct_branch", 0))
    born = [f for f in F if f["kind"] == "born"]
    fborn, kborn = lat([f["sig_a"] for f in born])
    for f, a, k in zip(born, fborn, kborn):
        f.update(fam=int(a), k=int(k), def_dens=100 * sum(f["cnt_a"].get(s, 0) for s in DEFENSIVE) / max(f["loc_a"], 1))
    first_ai = {r: min((c["ct"] for c in CM if c["r"] == r and c["tool"]), default=None) for r in repos}

    def window(xs, r):
        return [x for x in xs if x["r"] == r and first_ai[r] is not None and x["ct"] >= first_ai[r]]
    size = lambda x: x["changed"]  # noqa: E731
    L = ["# Structural footprint of declared-AI vs other commits (EXPLORATORY, outcome-blind)", "",
         "**Status: exploratory.** No fix or defect data is read. Script: `tools/ai_structure.py`. Functions touched by "
         "each commit are read before and after with tree-sitter and the engine's C/C++ rules, as in LAT-F; shapes are "
         f"placed on LAT's frozen lattice (`{TREES_SHA}`). Declared AI = an AI tool named in a commit trailer (as in "
         "`docs/ai_comments_exploratory.md`). Undeclared AI use is in the 'other' group.", "",
         f"- commits since {SINCE} with touched C/C++ functions: {len(CM):,} (declared AI {sum(1 for c in CM if c['tool']):,}); "
         f"function changes {len(F):,} (modified {len(mod):,}, born {len(born):,})",
         "- Comparisons are within repo, after the repo's first declared-AI commit. The 'other' side is re-weighted to "
         "the AI side's mix of lines changed per function (1–2, 3–8, 9–32, 33–128, > 128).", "",
         "## 1. Modified functions: does the shape move?", "",
         "| repo | modified fns AI / other | median lines changed AI / other | shape moved AI | other (size-matched) | "
         "family changed AI / other | signals gained per fn AI / other | defensive signals added per 100 changed lines "
         "AI / other | branches added per 100 changed lines AI / other |",
         "|---|---|---|---:|---:|---|---|---|---|"]
    for r in ADOPTERS:
        w = window(mod, r)
        ai, ot = [x for x in w if x["tool"]], [x for x in w if not x["tool"]]
        if len(ai) < 30 or len(ot) < 30:
            L.append(f"| {r} | {len(ai)} / {len(ot)} | too few | | | | | | |")
            continue
        per100 = lambda xs, k: 100 * sum(x[k] for x in xs) / max(sum(x["changed"] for x in xs), 1)  # noqa: E731
        L.append(
            f"| {r} | {len(ai):,} / {len(ot):,} | {np.median([x['changed'] for x in ai]):.0f} / "
            f"{np.median([x['changed'] for x in ot]):.0f} | **{np.mean([x['moved'] for x in ai]):.0%}** | "
            f"{std_mean(ai, ot, lambda x: x['moved'], size):.0%} | {np.mean([x['fam_change'] for x in ai]):.0%} / "
            f"{std_mean(ai, ot, lambda x: x['fam_change'], size):.0%} | {np.mean([x['gained'] for x in ai]):.2f} / "
            f"{std_mean(ai, ot, lambda x: x['gained'], size):.2f} | {per100(ai, 'd_def'):+.2f} / {per100(ot, 'd_def'):+.2f} | "
            f"{per100(ai, 'd_branch'):+.2f} / {per100(ot, 'd_branch'):+.2f} |")
    L += ["", "## 2. Calls: do AI commits add new dependencies?", "",
          "| repo | modified fns adding ≥ 1 new callee AI | other (size-matched) | new callees per modified fn AI / other "
          "(size-matched) | share of added callees defined in the same file AI / other |", "|---|---:|---:|---|---|"]
    for r in ADOPTERS:
        w = window(mod, r)
        ai, ot = [x for x in w if x["tool"]], [x for x in w if not x["tool"]]
        if len(ai) < 30 or len(ot) < 30:
            continue
        loc_share = lambda xs: sum(x["callees_added_local"] for x in xs) / max(sum(x["callees_added"] for x in xs), 1)  # noqa: E731
        L.append(f"| {r} | {np.mean([x['callees_added'] > 0 for x in ai]):.0%} | "
                 f"{std_mean(ai, ot, lambda x: x['callees_added'] > 0, size):.0%} | "
                 f"{np.mean([x['callees_added'] for x in ai]):.2f} / {std_mean(ai, ot, lambda x: x['callees_added'], size):.2f} | "
                 f"{loc_share(ai):.0%} / {loc_share(ot):.0%} |")
    L += ["", "## 3. Footprint per commit", "",
          "| repo | commits AI / other | files touched per commit AI / other | functions touched | share of touched "
          "functions that are new | functions deleted per commit |", "|---|---|---|---|---|---|"]
    for r in ADOPTERS:
        w = window(CM, r)
        ai, ot = [x for x in w if x["tool"]], [x for x in w if not x["tool"]]
        if len(ai) < 10:
            continue
        tf = lambda xs: np.mean([x["n_mod"] + x["n_born"] for x in xs])  # noqa: E731
        nb = lambda xs: sum(x["n_born"] for x in xs) / max(sum(x["n_mod"] + x["n_born"] for x in xs), 1)  # noqa: E731
        L.append(f"| {r} | {len(ai):,} / {len(ot):,} | {np.mean([x['files'] for x in ai]):.1f} / "
                 f"{np.mean([x['files'] for x in ot]):.1f} | {tf(ai):.1f} / {tf(ot):.1f} | {nb(ai):.0%} / {nb(ot):.0%} | "
                 f"{np.mean([x['n_del'] for x in ai]):.2f} / {np.mean([x['n_del'] for x in ot]):.2f} |")
    L += ["", "Footprint rows are not size-matched: a bigger change touches more, by construction.", "",
          "## 4. Functions born in AI vs other commits", "",
          "| repo | born AI / other | median loc AI / other | median rung k AI / other | defensive signals per 100 loc "
          "AI / other | callees per fn AI / other | top lattice family AI / other |", "|---|---|---|---|---|---|---|"]
    for r in ADOPTERS:
        w = window(born, r)
        ai, ot = [x for x in w if x["tool"]], [x for x in w if not x["tool"]]
        if len(ai) < 20 or len(ot) < 20:
            L.append(f"| {r} | {len(ai)} / {len(ot)} | too few | | | | |")
            continue
        top = lambda xs: "F{} ({:.0%})".format(*[(f, n / len(xs)) for f, n in [Counter(x['fam'] for x in xs).most_common(1)[0]]][0])  # noqa: E731
        L.append(f"| {r} | {len(ai):,} / {len(ot):,} | {np.median([x['loc_a'] for x in ai]):.0f} / "
                 f"{np.median([x['loc_a'] for x in ot]):.0f} | {np.median([x['k'] for x in ai]):.0f} / "
                 f"{np.median([x['k'] for x in ot]):.0f} | {np.mean([x['def_dens'] for x in ai]):.2f} / "
                 f"{np.mean([x['def_dens'] for x in ot]):.2f} | {np.mean([x['n_callees_a'] for x in ai]):.1f} / "
                 f"{np.mean([x['n_callees_a'] for x in ot]):.1f} | {top(ai)} / {top(ot)} |")
    # within author and by tool
    L += ["", "## 5. The same people, and the tools", ""]
    dm, dc = [], []
    for (r, a) in {(x["r"], x["author"]) for x in mod if x["tool"] and x["r"] in ADOPTERS}:
        w = [x for x in window(mod, r) if x["author"] == a]
        ai, ot = [x for x in w if x["tool"]], [x for x in w if not x["tool"]]
        if len(ai) < 10 or len(ot) < 10:
            continue
        d1 = np.mean([x["moved"] for x in ai]) - std_mean(ai, ot, lambda x: x["moved"], size)
        d2 = np.mean([x["callees_added"] for x in ai]) - std_mean(ai, ot, lambda x: x["callees_added"], size)
        if np.isfinite(d1):
            dm.append(d1)
        if np.isfinite(d2):
            dc.append(d2)
    if dm:
        L += [f"- authors with ≥ 10 AI and ≥ 10 other modified functions: **{len(dm)}**",
              f"- shape moved, AI minus own other (size-matched): median **{np.median(dm):+.0%}**; higher with AI for "
              f"{sum(1 for d in dm if d > 0)} of {len(dm)}",
              f"- new callees per modified function, AI minus own other: median {np.median(dc):+.2f}; higher with AI for "
              f"{sum(1 for d in dc if d > 0)} of {len(dc)}"]
    L += ["", "| repo | tool | modified fns | shape moved | other commits, size-matched | new callees per fn |",
          "|---|---|---:|---:|---:|---:|"]
    for r in ADOPTERS:
        w = window(mod, r)
        ot = [x for x in w if not x["tool"]]
        for t, n in Counter(x["tool"] for x in w if x["tool"]).most_common():
            if n < 50:
                continue
            xs = [x for x in w if x["tool"] == t]
            L.append(f"| {r} | {t} | {n:,} | {np.mean([x['moved'] for x in xs]):.0%} | "
                     f"{std_mean(xs, ot, lambda x: x['moved'], size):.0%} | {np.mean([x['callees_added'] for x in xs]):.2f} |")
    # era check in controls
    L += ["", "## 6. Era check: control repos (no declared AI), 2026 vs 2024–25, same measures", "",
          "| repo | modified fns 2024–25 / 2026 | shape moved 2024–25 | 2026 (size-matched to 2024–25) | new callees "
          "per fn 2024–25 / 2026 |", "|---|---|---:|---:|---|"]
    cut = 1767225600  # 2026-01-01 UTC
    for r in CONTROLS:
        xs = [x for x in mod if x["r"] == r]
        e, l2 = [x for x in xs if x["ct"] < cut], [x for x in xs if x["ct"] >= cut]
        if len(e) < 30 or len(l2) < 30:
            continue
        L.append(f"| {r} | {len(e):,} / {len(l2):,} | {np.mean([x['moved'] for x in e]):.0%} | "
                 f"{std_mean(e, l2, lambda x: x['moved'], size):.0%} | {np.mean([x['callees_added'] for x in e]):.2f} / "
                 f"{std_mean(e, l2, lambda x: x['callees_added'], size):.2f} |")
    L += ["", f"Runtime {time.time() - T0:.0f}s."]
    (DOCS_DIR / "ai_structure_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
