#!/usr/bin/env python3
"""Structure of the repairs by where they land relative to the cause (tree-sitter C). Hypotheses ST1-ST5: docs/sensor-overhaul/sensors/ripple_radius.md, fixed before running.

    python tools/sensor/repair_structure.py REPO TAG OUTDIR [--limit N]     (OUTDIR: blast_radius.py output; small causes = under 100 lines added plus removed)"""
import collections
import json
import pickle
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from tree_sitter_language_pack import get_parser

sys.path.insert(0, "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees/sensor-overhaul/tools/sensor")
import blast_radius as BR  # noqa: E402

RELS = ["same", "caller", "callee", "two calls away", "same file, farther", "elsewhere"]
LOCK = re.compile(r"lock|mutex|spin|rcu|sem_|_sem|down_|up_|irqsave|irqrestore|barrier", re.I)
CLEAN = re.compile(r"free|put|release|unlock|destroy|close|unmap|deinit|cleanup|unref|dec|remove|disable|stop|clear", re.I)
EXIT = {"return_statement", "goto_statement", "break_statement", "continue_statement"}
STMT = {"if_statement", "while_statement", "for_statement", "do_statement", "switch_statement", "return_statement", "goto_statement", "expression_statement", "declaration", "break_statement", "continue_statement"}
_P = None


KEYWORDS = set("auto break case char const continue default do double else enum extern float for goto if inline int long register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while bool true false uint8_t uint16_t uint32_t uint64_t int8_t int16_t int32_t int64_t size_t ssize_t u8 u16 u32 u64 s8 s16 s32 s64".split())
TOKEN = re.compile(r"(->|\.)?\s*([A-Za-z_]\w*)\s*(\()?")
STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
TYPE = re.compile(r"\b(?:struct|enum|union)\s+([A-Za-z_]\w*)")


def idents(texts):
    """{(name, class)} for the identifiers of statement texts: callee, field, macro, type, variable."""
    out = set()
    for t in texts:
        t = STRING.sub(" ", t)
        for m in TYPE.finditer(t):
            out.add((m.group(1), "type"))
        for m in TOKEN.finditer(t):
            name = m.group(2)
            if name in KEYWORDS or len(name) < 3:
                continue
            cls = "field" if m.group(1) else "callee" if m.group(3) else "macro" if name.upper() == name and any(c.isalpha() for c in name) else "variable"
            out.add((name, cls))
    return out


def norm(b):
    return re.sub(r"\s+", " ", b.decode("utf8", "replace")).strip()


def func_name(node, src):
    d = node.child_by_field_name("declarator")
    while d is not None and d.type != "identifier":
        nxt = d.child_by_field_name("declarator")
        if nxt is None:
            return None
        d = nxt
    return src[d.start_byte:d.end_byte].decode("utf8", "replace") if d is not None else None


def functions(src, wanted):
    """{name: function_definition node} for the wanted names (first definition wins)."""
    global _P
    if _P is None:
        _P = get_parser("c")
    tree = _P.parse(src)
    out = {}
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = func_name(n, src)
            if nm in wanted and nm not in out:
                out[nm] = n
            continue
        stack.extend(reversed(n.children))
    return out


def summarize(fn, src):
    """Statements (type, normalised text, flag), calls (callee, args), declaration texts of a function."""
    stmts, calls = collections.Counter(), collections.Counter()
    body = fn.child_by_field_name("body")
    extra = {"header": norm(src[fn.start_byte:body.start_byte]) if body is not None else "", "tokens": [], "preproc": collections.Counter(), "seq": [], "raw": src[fn.start_byte:fn.end_byte]}
    stack = [(body, 0)]
    while stack:
        n, depth = stack.pop()
        if n is None:
            continue
        if n.type.startswith("preproc_"):
            extra["preproc"][norm(src[n.start_byte:n.end_byte]).split(" ")[0:3].__str__()] += 1
        if n.child_count == 0 and n.type != "comment":
            extra["tokens"].append(src[n.start_byte:n.end_byte])
        if n.type in STMT:
            extra["seq"].append((n.type, depth))
        if n.type == "call_expression":
            f = n.child_by_field_name("function")
            a = n.child_by_field_name("arguments")
            calls[(norm(src[f.start_byte:f.end_byte]) if f is not None else "?", norm(src[a.start_byte:a.end_byte]) if a is not None else "")] += 1
        if n.type in STMT:
            if n.type in ("if_statement", "while_statement", "for_statement", "do_statement", "switch_statement"):
                c = n.child_by_field_name("condition")
                head = norm(src[c.start_byte:c.end_byte]) if c is not None else ""
                exits = False
                if n.type == "if_statement":
                    cons = n.child_by_field_name("consequence")
                    st = [cons]
                    while st:
                        x = st.pop()
                        if x is None:
                            continue
                        if x.type in EXIT:
                            exits = True
                            break
                        st.extend(x.children)
                stmts[(n.type, head, exits)] += 1
            else:
                stmts[(n.type, norm(src[n.start_byte:n.end_byte]), False)] += 1
        stack.extend((c, depth + (1 if n.type in STMT else 0)) for c in reversed(n.children))
    extra["tokens"] = b" ".join(extra["tokens"])
    return stmts, calls, extra


def classify(old, new, changed_names):
    so, co, eo = old
    sn, cn, en = new
    added, removed = sn - so, so - sn
    ac, rc = cn - co, co - cn
    na, nr = sum(added.values()), sum(removed.values())
    callee = lambda c: re.split(r"[.>-]+", c)[-1]  # noqa: E731
    added_callees = collections.Counter(callee(k[0]) for k in ac.elements())
    removed_callees = collections.Counter(callee(k[0]) for k in rc.elements())
    guard = any(k[0] == "if_statement" and k[2] for k in added)
    cond_removed = [k for k in removed if k[0] in ("if_statement", "while_statement", "for_statement")]
    cond_added = [k for k in added if k[0] in ("if_statement", "while_statement", "for_statement")]
    lock_added = any(LOCK.search(c) for c in added_callees)
    clean_added = any(CLEAN.search(c) for c in added_callees)
    arg_changed = any(c in removed_callees and ac[k] for k in ac for c in [callee(k[0])])
    repl = bool(set(added_callees) - set(removed_callees)) and bool(set(removed_callees) - set(added_callees)) and abs(len(added_callees) - len(removed_callees)) <= 1
    decl_changed = any(k[0] == "declaration" for k in added) and any(k[0] == "declaration" for k in removed)
    ret_changed = any(k[0] == "return_statement" for k in added) and any(k[0] == "return_statement" for k in removed)
    touches = any(callee(k[0]) in changed_names for k in list(ac) + list(rc))
    ret_handling = any(k[0] == "if_statement" and any(re.search(rf"\b{re.escape(n)}\b", k[1]) for n in changed_names) for k in added)
    if na == 0 and nr == 0 and not ac and not rc:
        if eo["raw"] == en["raw"]:
            label = "identical function (attribution)"
        elif eo["header"] != en["header"]:
            label = "changes signature or storage class"
        elif eo["tokens"] == en["tokens"]:
            label = "comments or whitespace only"
        elif eo["preproc"] != en["preproc"]:
            label = "changes preprocessor lines"
        elif eo["seq"] != en["seq"]:
            label = "moves or re-nests statements"
        else:
            label = "other (no statement change)"
    elif guard and nr <= 2 * na:
        label = "adds a guard"
    elif lock_added and nr <= na:
        label = "adds locking"
    elif clean_added and nr <= na:
        label = "adds cleanup"
    elif cond_removed and cond_added and not guard:
        label = "changes a condition"
    elif arg_changed:
        label = "changes a call's arguments"
    elif repl:
        label = "replaces a callee"
    elif decl_changed and na + nr <= 4:
        label = "changes a declared type"
    elif ret_changed and na + nr <= 4:
        label = "changes a return"
    elif nr == 0:
        label = "adds statements"
    elif na == 0:
        label = "removes statements"
    else:
        label = "rewrites"
    ids = idents([k[1] for k in list(added) + list(removed)] + [k[0] + "(" + k[1] for k in list(ac) + list(rc)])
    return label, touches, ret_handling, na, nr, ids


def blob(repo, rev, path, cache):
    k = (rev, path)
    if k not in cache:
        r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True)
        cache[k] = r.stdout if r.returncode == 0 else None
    return cache[k]


def edit_worker(job):
    repo, fix, recs = job
    cache, out = {}, []
    by_path = collections.defaultdict(list)
    for r in recs:
        by_path[r["path"]].append(r)
    for path, rs in by_path.items():
        src_new, src_old = blob(repo, fix, path, cache), blob(repo, fix + "^", path, cache)
        if src_new is None or src_old is None:
            out += [{**r, "status": "file missing"} for r in rs]
            continue
        names = {r["func"] for r in rs}
        fn_new, fn_old = functions(src_new, names), functions(src_old, names)
        for r in rs:
            if r["func"] not in fn_new or r["func"] not in fn_old:
                out.append({**r, "status": "function not found"})
                continue
            label, touches, rh, na, nr, ids = classify(summarize(fn_old[r["func"]], src_old), summarize(fn_new[r["func"]], src_new), set(r["changed_names"]))
            out.append({**r, "status": "ok", "label": label, "touches": touches, "ret_handling": rh, "na": na, "nr": nr, "idents": sorted(ids)})
    return out


def rel_worker(args):
    db, items = args
    g = BR.Graph(db)
    keys = sorted(g.index, key=g.index.get)
    out = []
    for it in items:
        I = np.array(sorted({g.index[k] for k in it["I"] if k in g.index}), dtype=np.int64)
        if not len(I):
            continue
        near = g.near(I)
        Iset = set(I.tolist())
        ifiles = {int(g.fid[i]) for i in I}
        for k in it["F"]:
            if k not in g.index:
                continue
            f = g.index[k]
            if f in Iset:
                rel = "same"
            elif near["callers1"][f] and not near["callees1"][f]:
                rel = "caller"
            elif near["callees1"][f]:
                rel = "callee"
            elif near["either2"][f]:
                rel = "two calls away"
            elif int(g.fid[f]) in ifiles:
                rel = "same file, farther"
            else:
                rel = "elsewhere"
            out.append({"pid": it["pid"], "path": k[0], "func": k[1], "rel": rel, "changed_names": sorted({x[1] for x in it["I"]})})
    return out


def cramers_v(tab):
    from scipy.stats import chi2_contingency
    tab = tab.loc[tab.sum(axis=1) > 0, tab.sum(axis=0) > 0]
    chi2 = chi2_contingency(tab.values)[0]
    return float(np.sqrt(chi2 / (tab.values.sum() * (min(tab.shape) - 1))))


def main():
    repo, tag, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    meas = pd.read_pickle(out / "measure.pkl")
    meas = meas[meas.status == "ok"]
    feats = pd.read_pickle(out / "diff_feats.pkl")
    meas = meas[[s in feats for s in meas.ind]].copy()
    meas["lines"] = [feats[s]["n_add"] + feats[s]["n_rem"] for s in meas.ind]
    small = meas[meas.lines < 100]
    if limit:
        small = small.head(limit)
    touched = {}
    for f in ("touched.pkl", "touched_all.pkl"):
        if (out / f).exists():
            touched.update(pickle.load(open(out / f, "rb")))
    sn = json.load(open(f"{BR.B}/scan_{tag}/snapshots.json"))
    by_snap = collections.defaultdict(list)
    for r in small.itertuples():
        by_snap[int(r.snapshot)].append({"pid": r.pid, "I": [tuple(k) for k in touched[r.ind]], "F": [tuple(k) for k in touched[r.fix]]})
    print(f"{repo}: {len(small)} measured pairs with a cause under 100 lines (of {len(meas)})", flush=True)
    recs = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for r in ex.map(rel_worker, [(sn[s]["db"], items) for s, items in sorted(by_snap.items())]):
            recs += r
    fixof = dict(zip(small.pid, small.fix))
    for r in recs:
        r["fix"] = fixof[r["pid"]]
    print(f"{len(recs)} (pair, fixed function) records; parsing the edits", flush=True)
    jobs = collections.defaultdict(list)
    for r in recs:
        jobs[r["fix"]].append(r)
    res = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for i, r in enumerate(ex.map(edit_worker, [(f"{BR.POOL}/{repo}", f, rs) for f, rs in jobs.items()], chunksize=20)):
            res += r
            if (i + 1) % 2000 == 0:
                print(f"  {i + 1}/{len(jobs)} fix commits", flush=True)
    df = pd.DataFrame(res)
    df.to_pickle(out / "repair_structure.pkl")
    report(df, repo)


def report(df, repo):
    ok = df[df.status == "ok"].copy()
    print(f"\n########## {repo}: {len(df)} records; parsed {len(ok)} ({100 * len(ok) / len(df):.0f}%); not parsed: " + ", ".join(f"{k} {v}" for k, v in df.status.value_counts().items() if k != "ok") + " ##########")
    print("  relation to the cause:", ", ".join(f"{r} {int((ok.rel == r).sum())} ({100 * (ok.rel == r).mean():.0f}%)" for r in RELS))
    tab = pd.crosstab(ok.rel, ok.label)
    shares = tab.div(tab.sum(axis=1), axis=0)
    cols = list(tab.sum().sort_values(ascending=False).index)
    print("\n  edit type (row shares) by relation:")
    print("  " + " " * 20 + " ".join(f"{c[:11]:>11s}" for c in cols))
    for r in RELS:
        if r in shares.index:
            print(f"  {r:20s}" + " ".join(f"{100 * shares.loc[r, c]:10.1f}%" for c in cols) + f"   n {int(tab.loc[r].sum())}")
    print("  " + f"{'ALL':20s}" + " ".join(f"{100 * (ok.label == c).mean():10.1f}%" for c in cols))
    cal, cae, same = ok[ok.rel == "caller"], ok[ok.rel == "callee"], ok[ok.rel == "same"]
    st1c, st1e = 100 * cal.touches.mean(), 100 * cae.touches.mean()
    g = lambda d: (d.label.isin(["adds a guard", "changes a condition"])).mean()  # noqa: E731
    st2 = g(cae) / g(cal) if g(cal) > 0 else float("nan")
    v = cramers_v(tab.loc[[r for r in RELS if r in tab.index]])
    named = ok[~ok.label.isin(["rewrites", "other (no statement change)", "identical function (attribution)"])]
    bucket_labels = ["identical function (attribution)", "changes signature or storage class", "comments or whitespace only", "changes preprocessor lines", "moves or re-nests statements", "other (no statement change)"]
    bk = ok[ok.label.isin(bucket_labels)]
    print(f"\n  THE FORMER 'NO STATEMENT CHANGE' BUCKET: {len(bk)} edits ({100 * len(bk) / len(ok):.1f}% of parsed)")
    for b in bucket_labels:
        print(f"    {b:38s} {int((bk.label == b).sum()):5d}  {100 * (bk.label == b).mean():5.1f}% of the bucket  {100 * (ok.label == b).mean():4.1f}% of all parsed edits")
    sizes = bk.label.value_counts()
    top2 = set(sizes.drop("other (no statement change)", errors="ignore").index[:2])
    sp1 = 1 - (bk.label == "other (no statement change)").mean()
    sp2 = (ok.label == "identical function (attribution)").mean()
    print(f"  SP1 share of the bucket in a named piece {100 * sp1:.0f}% (needs 75%): {'supported' if sp1 >= 0.75 else 'not supported'}")
    print(f"  SP2 identical function (attribution) {100 * sp2:.1f}% of parsed edits (needs 10% or less): {'supported' if sp2 <= 0.10 else 'not supported'}")
    print(f"  SP3 two largest named pieces: {sorted(top2)} (needs signature and moves): {'supported' if top2 == {'changes signature or storage class', 'moves or re-nests statements'} else 'not supported'}")
    cb = bk[bk.rel == "callee"]
    print("  SP4 pieces among callee repairs (share of callee 'bucket' edits): " + ", ".join(f"{b.split(' (')[0]} {100 * (cb.label == b).mean():.0f}%" for b in bucket_labels))
    print("      share of all edits by relation, bucket as a whole: " + ", ".join(f"{r} {100 * bk[bk.rel == r].shape[0] / max(ok[ok.rel == r].shape[0], 1):.1f}%" for r in RELS))
    for lab in ("changes signature or storage class", "changes preprocessor lines", "moves or re-nests statements"):
        print(f"      {lab:38s} by relation: " + ", ".join(f"{r} {100 * (ok[ok.rel == r].label == lab).mean():.1f}%" for r in RELS))
    st5 = cal.ret_handling.mean() / same.ret_handling.mean() if same.ret_handling.mean() > 0 else float("nan")
    print(f"\n  ST1 edits that call a changed function: callers {st1c:.0f}% (needs 40%), callees {st1e:.0f}% (needs 15% or less): {'supported' if st1c >= 40 and st1e <= 15 else 'not supported'}")
    print(f"  ST2 guard-or-condition share, callees / callers = {st2:.2f} (needs 1.3): {'supported' if st2 >= 1.3 else 'not supported'}")
    print(f"  ST3 Cramer's V of edit type by relation = {v:.3f} (needs 0.10): {'supported' if v >= 0.10 else 'not supported'}")
    print(f"  ST4 (re-scored post hoc, with the split pieces counted as typed; rewrites, other and identical functions untyped): {100 * len(named) / len(ok):.0f}% of parsed edits typed (needs 85%): {'supported' if len(named) / len(ok) >= 0.85 else 'not supported'}")
    print(f"  ST5 'an added if tests a changed function', callers {100 * cal.ret_handling.mean():.1f}% vs same function {100 * same.ret_handling.mean():.1f}% = {st5:.2f} (needs 1.5): {'supported' if st5 >= 1.5 else 'not supported'}")


if __name__ == "__main__":
    main()
