#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""FORTV-H1 and FIXK-H1..H3 (docs/fort_hypotheses.md § FORT-V and FIXK). Engine venv (tree-sitter + gitgalaxy rules).

    <engine venv>/bin/python tools/fortv_fixk_eval.py
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
from scipy.stats import chi2

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, FILE_HDR, HUNK, REPOS, _fname, _git, _parser, fix_events  # noqa: E402
from fort_eval import EXITS, mh, mh_ci  # noqa: E402
from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS  # noqa: E402
from hunk_grammar import parse_diff_sections  # noqa: E402

SEED = 2982
CLASSES = ("latent", "regression", "other-fix", "extrinsic")
C_RULES = LANGUAGE_DEFINITIONS["c"]["rules"]
CPP_RULES = LANGUAGE_DEFINITIONS.get("cpp", {}).get("rules", C_RULES)
RULES = sorted(k for k in C_RULES if not k.startswith("_") and hasattr(C_RULES[k], "findall"))
EXCL = ("tests/", "docs/", ".github/", "scripts/")
CAPS = re.compile(r"^[A-Z_][A-Z0-9_]*$")


# ---------------------------------------------------------------- FORT-V
def guard_list(node):
    out, stack = [], [node]
    while stack:
        n = stack.pop()
        if n.type == "if_statement" and n.child_by_field_name("alternative") is None:
            c = n.child_by_field_name("consequence")
            ok = c is not None and (c.type in EXITS or (c.type == "compound_statement" and 1 <= len(
                [x for x in c.named_children if x.type != "comment"]) <= 3 and [x for x in c.named_children if x.type != "comment"][-1].type in EXITS))
            if ok:
                cond = n.child_by_field_name("condition")
                txt = " ".join(cond.text.decode("utf-8", "replace").split()) if cond is not None else ""
                ids, st2 = set(), [cond] if cond is not None else []
                while st2:
                    m = st2.pop()
                    if m.type in ("identifier", "field_identifier"):
                        t = m.text.decode("utf-8", "replace")
                        if not CAPS.match(t) and t != "NULL":
                            ids.add(t)
                    st2.extend(m.children)
                out.append((txt, ids))
        stack.extend(n.children)
    return out


def funcs_guards(src: bytes, lang):
    out, stack = {}, [_parser(lang).parse(src).root_node]
    spans = []
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm:
                spans.append((n.start_point[0] + 1, n.end_point[0] + 1, nm, guard_list(n)))
            continue
        stack.extend(n.children)
    return spans


def v_task(t):
    r, sha, ct, klass = t
    repo = POOL_DIR / r
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return []
    lines, cur = defaultdict(set), None
    for ln in _git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        m = FILE_HDR.match(ln)
        if m:
            cur = m.group(1) if m.group(1) and m.group(1).endswith(CEXT + CPPEXT) else None
            continue
        if cur:
            h = HUNK.match(ln)
            if h:
                s, n = int(h.group(1)), int(h.group(2) or 1)
                lines[cur].update(range(s, s + n) if n > 0 else [max(s, 1)])
    out = []
    for path, ls in lines.items():
        lang = "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"
        a = _git(repo, "show", f"{parent}:{path}", text=False)
        b = _git(repo, "show", f"{sha}:{path}", text=False)
        if not a or not b:
            continue
        post = {}
        for s_, e_, nm, gl in funcs_guards(b, lang):
            post.setdefault(nm, gl)
        for s_, e_, nm, gl in funcs_guards(a, lang):
            if not any(s_ <= l <= e_ for l in ls) or nm not in post or not gl:
                continue
            pre_txt = {x[0] for x in gl}
            new = [g for g in post[nm] if g[0] not in pre_txt]
            if not new:
                continue
            pre_ids = set().union(*[x[1] for x in gl])
            ext = any(g[1] & pre_ids for g in new)
            out.append((r, sha, klass, e_ - s_ + 1, ext))
    return out


# ---------------------------------------------------------------- FIXK
def k_task(t):
    r, sha, ct, klass = t
    repo = POOL_DIR / r
    d = subprocess.run(["git", "-C", str(repo), "diff", "-U0", f"{sha}^", sha], capture_output=True)
    if d.returncode != 0:
        return None
    secs = [s for s in parse_diff_sections(d.stdout.decode("utf-8", "replace"))
            if s["path"].endswith(CEXT + CPPEXT) and not s["path"].startswith(EXCL)]
    if not secs:
        return None
    add, rem = Counter(), Counter()
    nlines = 0
    for s in secs:
        rules = C_RULES if s["path"].endswith(CEXT) and r != "harfbuzz" else CPP_RULES
        nlines += s["n_added"] + s["n_removed"]
        for k in RULES:
            rk = rules.get(k, C_RULES[k])
            if not hasattr(rk, "findall"):
                continue
            add[k] += len(rk.findall(s["added_text"]))
            rem[k] += len(rk.findall(s["removed_text"]))
    return (r, sha, klass, nlines, {k: add[k] - rem[k] for k in RULES})


def cmh(e, y, st):
    _, si = np.unique(st, return_inverse=True)
    num = var = 0.0
    for s in range(si.max() + 1):
        m = si == s
        N = m.sum()
        n1 = e[m].sum()
        m1 = y[m].sum()
        if N < 2 or n1 in (0, N) or m1 in (0, N):
            continue
        a = (e[m] * y[m]).sum()
        num += a - n1 * m1 / N
        var += n1 * (N - n1) * m1 * (N - m1) / (N * N * (N - 1))
    if var <= 0:
        return 1.0
    return float(chi2.sf(num * num / var, 1))


def bh(p):
    p = np.asarray(p)
    o = np.argsort(p)
    q = np.empty_like(p)
    m = len(p)
    prev = 1.0
    for rank, i in reversed(list(enumerate(o, 1))):
        prev = min(prev, p[i] * m / rank)
        q[i] = prev
    return q


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    ev = []
    for r in REPOS:
        e, _ = fix_events(r)
        ev += [x for x in e if x[3] in CLASSES]
    with multiprocessing.get_context("fork").Pool(8) as p:
        V = [u for us in p.imap_unordered(v_task, ev, chunksize=8) for u in us]
        Kr = [x for x in p.imap_unordered(k_task, ev, chunksize=8) if x]
    print(f"FORT-V touches {len(V):,}; FIXK commits {len(Kr):,} ({time.time() - t0:.0f}s)", flush=True)
    L = ["# FORT-V and FIXK (SCORED)", ""]
    # FORT-V
    C = np.array([u[2] for u in V])
    ext = np.array([1.0 if u[4] else 0.0 for u in V])
    st = np.array([f"{u[0]}|{int(np.floor(np.log10(max(u[3], 1)) / 0.2))}" for u in V])
    cl = np.array([u[1] for u in V])
    m = (C == "latent") | (C == "other-fix")
    rr, lo, hi = mh_ci((C[m] == "latent").astype(float), ext[m], st[m], cl[m], rng)
    nl = int((C == "latent").sum())
    v = ("not evaluable" if nl < 30 else "SUPPORTED: incompleteness (extends existing defences)" if lo > 1
         else "SUPPORTED: exposure (new defences)" if hi < 1 else "inconclusive")
    L += [f"- touches: already-guarded functions where the fix adds a new guard: {len(V):,} — " + ", ".join(f"{k} {int((C == k).sum())}" for k in CLASSES),
          "", "| claim | result | verdict |", "|---|---|---|",
          f"| **FORTV-H1** new guard checks an already-guarded variable: latent vs other-fix | P(extends): latent {ext[C == 'latent'].mean():.1%}, other-fix {ext[C == 'other-fix'].mean():.1%}; MH RR **{rr:.2f}** [{lo:.2f}, {hi:.2f}] | **{v}** |"]
    mr = (C == "regression") | (C == "other-fix")
    if (C == "regression").sum():
        L.append(f"- regression (descriptive): P(extends) {ext[C == 'regression'].mean():.1%}; MH RR vs other-fix {mh((C[mr] == 'regression').astype(float), ext[mr], st[mr]):.2f}")
    # FIXK
    KC = np.array([x[2] for x in Kr])
    kst = np.array([f"{x[0]}|{int(np.floor(np.log10(max(x[3], 1)) / 0.25))}" for x in Kr])
    sig = {}
    rows = {}
    for klass in ("latent", "regression", "extrinsic"):
        mm = (KC == klass) | (KC == "other-fix")
        e = (KC[mm] == klass).astype(float)
        res = []
        for k in RULES:
            for dirn in ("gain", "loss"):
                y = np.array([1.0 if ((x[4][k] >= 1) if dirn == "gain" else (x[4][k] <= -1)) else 0.0 for x, keep in zip(Kr, mm) if keep])
                if y.sum() < 10:
                    continue
                res.append((k, dirn, mh(e, y, kst[mm]), cmh(e, y, kst[mm]), y[e == 1].mean(), y[e == 0].mean()))
        q = bh([r_[3] for r_ in res]) if res else []
        rows[klass] = [(*r_, qq) for r_, qq in zip(res, q)]
        sig[klass] = {(r_[0], r_[1]) for r_, qq in zip(res, q) if qq < 0.01 and (r_[2] >= 1.25 or r_[2] <= 0.80)}
    known = {"branch", "safety", "panics_and_aborts", "cleanup"}
    beyond = {s for s in sig["latent"] if s[0] not in known}
    j = len(sig["latent"] & sig["regression"]) / max(len(sig["latent"] | sig["regression"]), 1)
    L += ["", f"- FIXK commits with kept C/C++ files: {len(Kr):,} — " + ", ".join(f"{k} {int((KC == k).sum()):,}" for k in CLASSES), "",
          "| claim | result | verdict |", "|---|---|---|",
          f"| **FIXK-H1** CVE signature beyond known defensive rules | {len(sig['latent'])} signature rules; beyond {sorted(known)}: {sorted(beyond)} | **{'SUPPORTED' if beyond else 'not supported'}** |",
          f"| **FIXK-H2** regression signature exists | {sorted(sig['regression'])} | **{'SUPPORTED' if sig['regression'] else 'not supported'}** |",
          f"| **FIXK-H3** CVE and regression signatures differ | Jaccard {j:.2f} | **{'SUPPORTED' if sig['latent'] and sig['regression'] and j < 0.5 else 'not supported'}** |"]
    for klass in ("latent", "regression", "extrinsic"):
        L += ["", f"### {klass} vs other-fix (signature rules first; then the rest sorted by RR)", "", "| rule | change | class rate | other-fix rate | MH RR | BH q |", "|---|---|---:|---:|---:|---:|"]
        rs = sorted(rows[klass], key=lambda r_: (not ((r_[0], r_[1]) in sig[klass]), -abs(np.log(max(r_[2], 1e-9)))))
        for r_ in rs[:24]:
            L.append(f"| {r_[0]} | {r_[1]} | {r_[4]:.1%} | {r_[5]:.1%} | {r_[2]:.2f} | {r_[6]:.2g} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "fortv_fixk.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
