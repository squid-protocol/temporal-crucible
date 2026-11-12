#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ECOND (EXPLORATORY): what does a new or changed condition TEST, and is the new branch a guard?

    python tools/cond_content.py walk   --repo curl --out /scratch/econd_curl.jsonl   # outcome-blind
    python tools/cond_content.py report --repo curl --in  /scratch/econd_curl.jsonl   # outcome-blind
    python tools/cond_content.py join   --repo curl --in  /scratch/econd_curl.jsonl --json docs/econd_curl.json

**Exploratory. No registration, no p-value. `walk` and `report` read no fix label, event file or commit
message. `join` does, and is offered for the burned repos only (curl, libarchive).**

Why. `docs/etyp_label.md`: the TYPE of an edit ("a branch was added") does not separate a fix from a
feature, AUC 0.57-0.59 out of repo. ETYP abstracts away what the branch tests on purpose. This puts it
back, as a second closed taxonomy, for exactly the two places a condition can appear in an edit:

  - a NEW condition: an if / while / for / do / switch whose condition text is not in the old function;
  - for a new `if`, its SHAPE: a GUARD (the consequence leaves: return, goto, break or continue, alone
    or as the last statement of the block) or an ACTION (anything else).

A condition is split at && and || into leaf predicates, parentheses and a leading ! are peeled, and
each leaf gets ONE kind, purely from syntax:

    NULL_CMP    == or != against NULL                       if (p == NULL)
    ZERO_CMP    == or != against the literal 0              if (n != 0)
    CONST_CMP   == or != against another literal, an ALL_CAPS name or sizeof   if (rc == CURLE_OK)
    VAR_CMP     == or != between two non-constants          if (a == b)
    REL_CONST   < > <= >= with a literal / ALL_CAPS / sizeof on one side       if (len > MAX)
    REL_VAR     < > <= >= between two non-constants         if (i < n)
    BITTEST     a bitwise & test                            if (flags & F_X)
    NEGATED     !x, x not a comparison                      if (!p)
    TRUTHY      x, x not a comparison                       if (p)
    OTHER       anything else

plus one independent flag, CALL: the leaf contains a function call (`if (!strcmp(a, b))`, `if (f(x) < 0)`).

Per edit the tool records the kinds among its new conditions, the kinds among its new GUARD conditions
(prefixed G:), GUARD_ADD / ACTION_IF_ADD, and whether a new condition is an old one with a conjunct
added (COND_NARROW: the old text survives as one side of a new && or ||).

No type information is used: `if (p)` is TRUTHY whether p is a pointer or a flag, and `x == 0` is
ZERO_CMP whether x is a pointer or a count. That is a limit of an unpreprocessed parse, stated here
rather than papered over with name heuristics.

Needs tree-sitter-language-pack; `join` also needs numpy.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edit_types as et          # noqa: E402

KINDS = ("NULL_CMP", "ZERO_CMP", "CONST_CMP", "VAR_CMP", "REL_CONST", "REL_VAR", "BITTEST",
         "NEGATED", "TRUTHY", "OTHER", "CALL")
SHAPES = ("GUARD_ADD", "ACTION_IF_ADD", "COND_NARROW")
COLS = list(SHAPES) + list(KINDS) + ["G:" + k for k in KINDS]
EXITS = {"return_statement", "goto_statement", "break_statement", "continue_statement"}


def _peel(n):
    while n is not None and n.type == "parenthesized_expression" and n.named_child_count == 1:
        n = n.named_children[0]
    return n


def _op(n) -> str:
    o = n.child_by_field_name("operator")
    return o.type if o is not None else ""


def _is_const(n) -> bool:
    n = _peel(n)
    if n.type in ("number_literal", "char_literal", "sizeof_expression", "true", "false"):
        return True
    if n.type == "identifier":
        t = et._txt(n)
        return len(t) > 1 and t.upper() == t and any(c.isalpha() for c in t)
    return False


def _is_null(n) -> bool:
    n = _peel(n)
    return n.type == "null" or (n.type == "identifier" and et._txt(n) == "NULL")


def _is_zero(n) -> bool:
    n = _peel(n)
    return n.type == "number_literal" and et._txt(n).rstrip("uUlL") in ("0", "0x0", "0.0")


def _has_call(n) -> bool:
    stack = [n]
    while stack:
        x = stack.pop()
        if x.type == "call_expression":
            return True
        stack.extend(x.children)
    return False


def leaf_kind(n) -> str:
    """One kind for one leaf predicate (already split at && / ||)."""
    n = _peel(n)
    negated = False
    while n.type == "unary_expression" and _op(n) == "!":
        negated = not negated
        n = _peel(n.child_by_field_name("argument"))
    if n.type == "binary_expression":
        op = _op(n)
        left, right = n.child_by_field_name("left"), n.child_by_field_name("right")
        if op in ("==", "!="):
            if _is_null(left) or _is_null(right):
                return "NULL_CMP"
            if _is_zero(left) or _is_zero(right):
                return "ZERO_CMP"
            return "CONST_CMP" if (_is_const(left) or _is_const(right)) else "VAR_CMP"
        if op in ("<", ">", "<=", ">="):
            return "REL_CONST" if (_is_const(left) or _is_const(right)) else "REL_VAR"
        if op == "&":
            return "BITTEST"
        return "OTHER"
    if n.type in ("identifier", "field_expression", "subscript_expression", "pointer_expression",
                  "call_expression"):
        return "NEGATED" if negated else "TRUTHY"
    return "OTHER"


def leaves(cond) -> list:
    """Leaf predicate nodes of a condition, split at && and ||."""
    out, stack = [], [_peel(cond)]
    while stack:
        n = _peel(stack.pop())
        if n is None:
            continue
        if n.type == "binary_expression" and _op(n) in ("&&", "||"):
            stack.append(n.child_by_field_name("right"))
            stack.append(n.child_by_field_name("left"))
        else:
            out.append(n)
    return out


def kinds_of(cond) -> set[str]:
    out = set()
    for lf in leaves(cond):
        out.add(leaf_kind(lf))
        if _has_call(lf):
            out.add("CALL")
    return out


def _exits(node) -> bool:
    """Does this consequence leave: an exit statement, alone or last in its block?"""
    if node is None:
        return False
    if node.type in EXITS:
        return True
    if node.type == "compound_statement":
        named = [c for c in node.named_children if c.type != "comment"]
        return bool(named) and named[-1].type in EXITS
    return False


def conditions(fn) -> list[dict]:
    """Every condition in a function, in source order: text, kinds, parts, and for an `if` whether it exits."""
    out, stack = [], [fn]
    while stack:
        n = stack.pop()
        if n.type in et.COND_OWNERS:
            c = n.child_by_field_name("condition")
            if c is not None:
                out.append({"text": et._squash(et._txt(c)), "kinds": kinds_of(c),
                            "parts": [et._squash(et._txt(lf)) for lf in leaves(c)],
                            "is_if": n.type == "if_statement",
                            "guard": n.type == "if_statement" and _exits(n.child_by_field_name("consequence"))})
        stack.extend(reversed(n.children))
    return out


def cond_features(fa, fb) -> list[str]:
    """ECOND columns for one edit, from the function node before (fa) and after (fb)."""
    old = conditions(fa)
    left = Counter(c["text"] for c in old)
    old_texts = set(left)
    cols: set[str] = set()
    for c in conditions(fb):
        if left[c["text"]] > 0:
            left[c["text"]] -= 1
            continue                                   # this condition existed before: not new
        cols.update(c["kinds"])
        if len(c["parts"]) > 1 and any(p in old_texts or "(" + p + ")" in old_texts for p in c["parts"]):
            cols.add("COND_NARROW")
        if c["is_if"]:
            if c["guard"]:
                cols.add("GUARD_ADD")
                cols.update("G:" + k for k in c["kinds"])
            else:
                cols.add("ACTION_IF_ADD")
    # GUARD_ADD / ACTION_IF_ADD mean a NEW branch, not an edited one: require the if count to have grown.
    n_if = lambda cs: sum(1 for c in cs if c["is_if"])
    if n_if(conditions(fb)) <= n_if(old):
        cols -= {"GUARD_ADD", "ACTION_IF_ADD"} | {"G:" + k for k in KINDS}
    return sorted(cols)


# ---------------------------------------------------------------------------------------------- walk

def _work(args):
    repo, chunk = args
    lang = et.REPOS[repo]["lang"]
    blobs = et.Blobs(et.POOL / repo)
    cache: OrderedDict = OrderedDict()

    def parsed(oid):
        if oid in cache:
            cache.move_to_end(oid)
            return cache[oid]
        src = blobs.get(oid)
        val = et.functions_in(src, lang) if src is not None else ({}, set())
        cache[oid] = val
        if len(cache) > 48:
            cache.popitem(last=False)
        return val

    rows = []
    for sha, ct, path, old, new in chunk:
        fa, _da = parsed(old)
        fb, _db = parsed(new)
        for name in sorted(fa.keys() & fb.keys()):
            na, nb = fa[name], fb[name]
            if na.text == nb.text:
                continue
            A, B = et.features(na), et.features(nb)
            labs = et.classify(A, B)
            ta, tb = Counter(A["tokens"]), Counter(B["tokens"])
            rows.append({"sha": sha, "ct": ct, "path": path, "func": name, "labels": sorted(labs),
                         "primary": et.primary(labs), "ntok": len(B["tokens"]),
                         "tadd": sum((tb - ta).values()), "tdel": sum((ta - tb).values()),
                         "err": bool(A["has_error"] or B["has_error"]), "cond": cond_features(na, nb)})
    return rows


def cmd_walk(a) -> int:
    import multiprocessing as mp
    js = et.jobs(a.repo)
    if a.limit:
        js = js[: a.limit]
    step = max(1, math.ceil(len(js) / (a.workers * 8)))
    chunks = [(a.repo, js[i: i + step]) for i in range(0, len(js), step)]
    n = 0
    with mp.get_context("fork").Pool(a.workers) as pool, open(a.out, "w") as fh:
        for rows in pool.imap(_work, chunks):
            for r in rows:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
            n += len(rows)
    print(f"{a.repo}: {n:,} function edits -> {a.out}")
    return 0


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    with_new = [r for r in rows if set(r["cond"]) & set(KINDS)]
    guards = [r for r in rows if "GUARD_ADD" in r["cond"]]
    c_all = Counter(k for r in with_new for k in r["cond"] if k in KINDS)
    c_g = Counter(k[2:] for r in guards for k in r["cond"] if k.startswith("G:"))
    return {"edits": n, "edits_with_new_condition": len(with_new),
            "share_with_new_condition": len(with_new) / n,
            "shape_share": {s: sum(s in r["cond"] for r in rows) / n for s in SHAPES},
            "kind_share_of_new_condition_edits": {k: c_all[k] / len(with_new) for k in KINDS},
            "kind_share_of_guard_edits": {k: c_g[k] / len(guards) for k in KINDS} if guards else {},
            "other_only_share": sum(1 for r in with_new if set(r["cond"]) & set(KINDS) == {"OTHER"}) / len(with_new)}


def cmd_report(a) -> int:
    s = summarise(et.load(a.inp))
    if a.json:
        Path(a.json).write_text(json.dumps({"repo": a.repo, **s}, indent=1, sort_keys=True) + "\n")
    print(f"{a.repo}: {s['edits']:,} function edits; {s['edits_with_new_condition']:,} "
          f"({s['share_with_new_condition']:.1%}) carry a new condition (EXPLORATORY, outcome-blind)\n")
    for k in SHAPES:
        print(f"  {k:14} {s['shape_share'][k]:6.1%} of all edits")
    print(f"  only OTHER     {s['other_only_share']:6.1%} of edits with a new condition (the residual)\n")
    print(f"  {'kind':10} {'new-condition edits':>20} {'new-guard edits':>17}")
    for k in KINDS:
        print(f"  {k:10} {s['kind_share_of_new_condition_edits'][k]:20.1%} "
              f"{s['kind_share_of_guard_edits'].get(k, 0):17.1%}")
    return 0


# ---------------------------------------------------------------------------------------------- join

def cmd_join(a) -> int:
    import numpy as np
    import etyp_fix as ef
    import etyp_label as el
    rng = np.random.default_rng(ef.SEED)
    rows = et.load(a.inp)
    evs = ef.load_events(a.repo)
    by: dict = {}
    for r in rows:
        by.setdefault(r["sha"], []).append(r)
    shas = [s for s, rs in by.items() if len(rs) <= 50]
    idx = {c: i for i, c in enumerate(COLS)}
    X = np.zeros((len(shas), len(COLS)))
    n = np.zeros(len(shas), dtype=int)
    mag = np.zeros(len(shas), dtype=int)
    ct = np.zeros(len(shas), dtype=np.int64)
    for i, s in enumerate(shas):
        rs = by[s]
        n[i], ct[i], mag[i] = len(rs), rs[0]["ct"], sum(r["tadd"] + r["tdel"] for r in rs)
        for r in rs:
            for c in r["cond"]:
                X[i, idx[c]] += 1
        X[i] /= len(rs)
    bins = np.array([ef.size_bin(k) * 4 + ef.mag_bin(m) for k, m in zip(n, mag)])
    window = (ct >= evs["since"]) & (ct <= evs["head_ct"])
    cls = np.array([evs["class"].get(s, "") for s in shas])
    anyfix = (cls != "") & window
    amb = np.array([s in evs["dropped"] for s in shas])
    nonfix = window & ~anyfix & ~amb
    groups = {"all fixes": anyfix}
    for c in ef.FIX_CLASSES:
        groups[c] = (cls == c) & window
    groups["CVE (all)"] = np.array([s in evs["sev"] for s in shas])
    groups["CVE control"] = np.array([s in evs["control"] for s in shas])
    groups["CVE-introducing"] = np.array([s in evs["cve_intro"] for s in shas])
    groups["regr-inducing"] = np.array([s in evs["reg_inducing"] for s in shas]) & ~anyfix
    res = {g: {"commits": int(m.sum()), "by": ef.std_lift(X, bins, m, nonfix & ~m, rng, COLS)}
           for g, m in groups.items() if m.sum() >= 20}
    fu = ef.follow_up(rows, evs, set(evs["class"]), rng, COLS, lambda r: r["cond"])

    print(f"{a.repo}: {int(anyfix.sum()):,} fix, {int(nonfix.sum()):,} non-fix commits "
          f"(EXPLORATORY; lift over non-fix commits of the same size and magnitude; "
          f"* = 95% interval excludes 1; no multiplicity correction)")
    order = [g for g in ("all fixes", "other-fix", "regression", "extrinsic", "latent", "CVE (all)",
                         "CVE control", "CVE-introducing", "regr-inducing") if g in res]
    print("  commits: " + ", ".join(f"{g} {res[g]['commits']:,}" for g in order))
    ef.table("Shape and kind of new conditions", res, order[:5], list(SHAPES) + list(KINDS))
    ef.table("Kind of the condition on a NEW GUARD", res, order[:5], ["G:" + k for k in KINDS])
    if len(order) > 5:
        ef.table("CVE and defect-introducing commits", res, order[5:], list(SHAPES) + list(KINDS))
        ef.table("Same: kind on a new guard", res, order[5:], ["G:" + k for k in KINDS])
    print(f"\n  After a NON-fix edit, is the function fixed within 365 days?  "
          f"{fu['eligible_edits']:,} eligible edits, base rate {fu['base_rate']:.1%}")
    for c in COLS:
        v = fu["by"][c]
        if v["n"] >= 100 and v["rel"] is not None:
            star = "*" if (v["lo"] > 1 or v["hi"] < 1) else " "
            print(f"    {c:14} {v['n']:7,} {v['rate']:7.1%} {v['expected']:9.1%} {v['rel']:8.2f}{star}   "
                  f"[{v['lo']:.2f}, {v['hi']:.2f}]")

    # Does condition content make a single fix more recognisable than the edit types alone (etyp_label.md)?
    _s, base = el.design(rows)
    assert _s == shas
    cols = dict(base)
    for c in COLS:
        cols["E:" + c] = X[:, idx[c]]
    out = {"repo": a.repo, "type": "exploratory", "groups": res, "follow_up": fu,
           "design": {"shas": len(shas)}}
    if a.model_out or a.model_in:
        y = (cls != "").astype(float)
        keep = ~amb
        variants = {"size": el.SIZE, "type+size": el.ATOMS + el.SIZE,
                    "type+cond+size": el.ATOMS + ["E:" + c for c in COLS] + el.SIZE}
        if a.model_out:
            model = {"trained_on": a.repo, "variants": {}}
            for name, feats in variants.items():
                Z, mu, sd = el.matrix({k: v[keep] for k, v in cols.items()}, feats)
                w = el.fit_logit(Z, y[keep])
                model["variants"][name] = {"features": feats, "mu": mu.tolist(), "sd": sd.tolist(),
                                           "intercept": float(w[0]), "weights": w[1:].tolist()}
            Path(a.model_out).write_text(json.dumps(model, sort_keys=True) + "\n")
        if a.model_in:
            model = json.loads(Path(a.model_in).read_text())
            keep_i = np.flatnonzero(keep)
            draws = [rng.choice(keep_i, len(keep_i)) for _ in range(200)]
            print(f"\n  Fix vs not a fix, model fitted on {model['trained_on']}, scored here (AUC):")
            out["label_auc"] = {"trained_on": model["trained_on"]}
            sc = {}
            for name, m in model["variants"].items():
                Z, _mu, _sd = el.matrix(cols, m["features"], np.array(m["mu"]), np.array(m["sd"]))
                sc[name] = Z @ np.array(m["weights"])
                b = [el.auc(sc[name][d], y[d]) for d in draws]
                out["label_auc"][name] = {"auc": el.auc(sc[name][keep], y[keep]),
                                          "lo": float(np.percentile(b, 2.5)), "hi": float(np.percentile(b, 97.5))}
                print(f"    {name:15} {out['label_auc'][name]['auc']:.3f}  "
                      f"[{out['label_auc'][name]['lo']:.3f}, {out['label_auc'][name]['hi']:.3f}]")
            d = [el.auc(sc["type+cond+size"][x], y[x]) - el.auc(sc["type+size"][x], y[x]) for x in draws]
            out["label_auc"]["cond_gain"] = {
                "diff": out["label_auc"]["type+cond+size"]["auc"] - out["label_auc"]["type+size"]["auc"],
                "lo": float(np.percentile(d, 2.5)), "hi": float(np.percentile(d, 97.5))}
            g = out["label_auc"]["cond_gain"]
            print(f"    gain from condition content  {g['diff']:+.3f}  [{g['lo']:+.3f}, {g['hi']:+.3f}]")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("walk", "report", "join"))
    ap.add_argument("--repo", default="curl", choices=sorted(et.REPOS))
    ap.add_argument("--out")
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--json")
    ap.add_argument("--model-out")
    ap.add_argument("--model-in")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.step == "join" and a.repo not in ("curl", "libarchive"):
        ap.error("join reads outcomes and is offered for the burned repos only: curl, libarchive")
    return {"walk": cmd_walk, "report": cmd_report, "join": cmd_join}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
