#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ETYP (exploratory, OUTCOME-BLIND): reduce every function edit to a discrete type.

    python tools/edit_types.py walk   --repo curl --out /scratch/etyp_curl.jsonl   # classify every edit
    python tools/edit_types.py report --repo curl --in  /scratch/etyp_curl.jsonl   # coverage and stability
    python tools/edit_types.py show   --repo curl --in  /scratch/etyp_curl.jsonl --label UNCLASSIFIED --n 5

**Exploratory. No registration, no hypothesis, no p-value. This tool never reads a fix label, an event
file or a commit message: it cannot compute anything about defects.** That is deliberate. The taxonomy
has to be frozen before any outcome is joined to it, or the types would be tuned to the answer.

Why. KWMAT / KWNEST (`docs/kwmature.md`, `docs/kwnest.md`) found a function's control skeleton is laid
down at birth and almost never rearranged, and CEIL (`docs/ceil.md`) found ~22 points of review-budget
performance sit in rate heterogeneity we do not measure. If structure is static, what varies between
functions must be the KIND of edit they receive. KWNEST compared first vs last snapshot and counted
differing tokens; this drops to the unit that actually happens -- one commit changing one function --
and gives each such edit a closed set of atomic labels.

Unit: (commit, file, function) where the function exists by the same name on both sides of a
non-merge commit and its source text differs. Births, deaths and renamed functions are not edits here.

Each edit gets a SET of atomic labels (below), a FAMILY set, and one PRIMARY family by a fixed priority
order, so "the type of this edit" has a single deterministic answer as well as a full one.

    family     atomic labels
    ---------  ------------------------------------------------------------------------------
    STRUCTURE  BRANCH_ADD BRANCH_DEL LOOP_CHANGE EXIT_CHANGE SKELETON_MOVE
    WIRING     CALL_ADD CALL_DEL CALL_RETARGET ARG_ARITY SIGNATURE
    LOGIC      COND_EDIT OPERATOR RETURN_VALUE ARG_VALUE
    DATA       NUM_LITERAL STRING_LITERAL TYPE FIELD LOCAL_DECL REF_SWAP STMT_ADD STMT_DEL
    BUILD      PREPROC
    NAMING     RENAME_LOCAL
    COSMETIC   COMMENT FORMAT
    RESIDUAL   EXPR_EDIT (an expression changed and nothing above names how) UNCLASSIFIED

Two instruments, as in KWNEST: git supplies the population (every modified file of every non-merge
commit, with blob ids), tree-sitter supplies the parse. No scan database is needed.

Limits, stated up front: tree-sitter parses unpreprocessed C, so macro-heavy functions parse with
ERROR nodes (flagged per edit, reported, not dropped); identity is (path-with-renames, function name),
so a renamed function is a death and a birth; a name defined more than once in a file (#ifdef variants)
is ambiguous and skipped, with a count.

Needs tree-sitter-language-pack.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

POOL = Path(os.environ.get("TC_POOL", "/srv/storage_16tb/projects/temporal-crucible-pool"))
SEED = 2982

# Source roots per repo: implementation only. Tests, docs and examples are bystanders (hunk_grammar.py).
REPOS = {
    "curl": {"lang": "c", "exts": (".c",), "roots": ("lib/", "src/")},
    "libarchive": {"lang": "c", "exts": (".c",), "roots": ("libarchive/", "tar/", "cpio/", "cat/")},
    "ndpi": {"lang": "c", "exts": (".c",), "roots": ("src/",)},
    "openssl": {"lang": "c", "exts": (".c",), "roots": ("crypto/", "ssl/", "apps/", "providers/")},
}

FAMILIES = OrderedDict([
    ("STRUCTURE", ("BRANCH_ADD", "BRANCH_DEL", "LOOP_CHANGE", "EXIT_CHANGE", "SKELETON_MOVE")),
    ("WIRING", ("CALL_ADD", "CALL_DEL", "CALL_RETARGET", "ARG_ARITY", "SIGNATURE")),
    ("LOGIC", ("COND_EDIT", "OPERATOR", "RETURN_VALUE", "ARG_VALUE")),
    ("DATA", ("NUM_LITERAL", "STRING_LITERAL", "TYPE", "FIELD", "LOCAL_DECL", "REF_SWAP",
              "STMT_ADD", "STMT_DEL")),
    ("BUILD", ("PREPROC",)),
    ("NAMING", ("RENAME_LOCAL",)),
    ("COSMETIC", ("COMMENT", "FORMAT")),
    ("RESIDUAL", ("EXPR_EDIT", "UNCLASSIFIED")),
])
LABELS = tuple(lab for labs in FAMILIES.values() for lab in labs)
FAMILY_OF = {lab: fam for fam, labs in FAMILIES.items() for lab in labs}
# The PRIMARY family of an edit is the first of these it carries. Fixed here, before any outcome.
PRIORITY = tuple(FAMILIES)

BRANCH = {"if", "else", "switch", "case", "default"}
LOOP = {"for", "while", "do"}
EXIT = {"return", "goto", "break", "continue"}
CONTROL = BRANCH | LOOP | EXIT
OPERATORS = {"+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!", "&", "|",
             "^", "~", "<<", ">>", "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=",
             "++", "--", "?"}
TYPE_NODES = {"primitive_type", "type_identifier", "sized_type_specifier", "type_qualifier",
              "storage_class_specifier"}
IDENT_KINDS = {"identifier", "field_identifier", "type_identifier", "statement_identifier"}
COND_OWNERS = {"if_statement", "while_statement", "do_statement", "for_statement", "switch_statement"}

_PARSERS: dict = {}


def parser(lang: str = "c"):
    if lang not in _PARSERS:
        try:
            import tree_sitter_language_pack as tslp
        except ImportError:
            sys.exit("tree-sitter is not available: pip install tree-sitter-language-pack")
        _PARSERS[lang] = tslp.get_parser(lang)
    return _PARSERS[lang]


def _txt(node) -> str:
    return node.text.decode("utf-8", "replace")


def _squash(s: str) -> str:
    return " ".join(s.split())


def func_name(node) -> str | None:
    d = node.child_by_field_name("declarator")
    while d is not None:
        if d.type == "identifier":
            return _txt(d)
        nxt = d.child_by_field_name("declarator")
        if nxt is None:
            for c in d.children:
                if c.type == "identifier":
                    return _txt(c)
            return None
        d = nxt
    return None


def functions_in(src: bytes, lang: str = "c") -> tuple[dict, set]:
    """({name: node} for names defined exactly once, {names defined more than once})."""
    tree = parser(lang).parse(src)
    found: dict = {}
    dup: set = set()
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = func_name(n)
            if nm:
                if nm in found:
                    dup.add(nm)
                found[nm] = n
            continue                      # C has no nested function definitions worth chasing
        stack.extend(n.children)
    for nm in dup:
        found.pop(nm, None)
    return found, dup


def _declared_names(node) -> list[str]:
    """Names a `declaration` / `parameter_declaration` node introduces."""
    out = []
    for i, c in enumerate(node.children):
        if node.field_name_for_child(i) != "declarator":
            continue
        d = c
        while d is not None and d.type != "identifier":
            d = d.child_by_field_name("declarator")
        if d is not None:
            out.append(_txt(d))
    return out


def features(fn) -> dict:
    """Everything the classifier compares, from one function node. Pure: same node, same answer."""
    body = fn.child_by_field_name("body")
    f = {
        "tokens": [], "comments": [], "skeleton": [], "calls": Counter(), "args": defaultdict(list),
        "arity": defaultdict(list), "conds": Counter(), "nums": Counter(), "strs": Counter(),
        "types": Counter(), "fields": Counter(), "ops": Counter(), "ndecl": 0, "locals": set(),
        "returns": Counter(), "preproc": Counter(), "stmts": Counter(), "nstmt": 0,
        "has_error": fn.has_error,
        "signature": _squash(fn.text[: (body.start_byte - fn.start_byte) if body else None]
                             .decode("utf-8", "replace")),
    }
    # Iterative, children pushed reversed so pops come in source order (openssl nests deep enough to
    # exhaust the recursion limit -- the KWNEST lesson).
    stack = [(fn, 0)]
    while stack:
        n, depth = stack.pop()
        t = n.type
        if t == "comment":
            f["comments"].append(_txt(n))
            continue
        if t in ("string_literal", "concatenated_string"):
            f["strs"][_txt(n)] += 1
            f["tokens"].append(("string_literal", _txt(n)))
            continue                      # one token: its pieces are not separate edits
        if t in ("number_literal", "char_literal"):
            f["nums"][_txt(n)] += 1
        elif t in TYPE_NODES:
            f["types"][_txt(n)] += 1
        elif t == "field_identifier":
            f["fields"][_txt(n)] += 1
        elif t == "call_expression":
            callee = n.child_by_field_name("function")
            arglist = n.child_by_field_name("arguments")
            name = _squash(_txt(callee)) if callee is not None else "?"
            f["calls"][name] += 1
            if arglist is not None:
                f["args"][name].append(_squash(_txt(arglist)))
                f["arity"][name].append(arglist.named_child_count)
        elif t in COND_OWNERS:
            c = n.child_by_field_name("condition")
            if c is not None:
                f["conds"][_squash(_txt(c))] += 1
        elif t == "return_statement":
            f["returns"][_squash(_txt(n))] += 1
        elif t == "expression_statement":
            f["nstmt"] += 1
            f["stmts"][_squash(_txt(n))] += 1
        elif t == "declaration":
            f["ndecl"] += 1
            f["locals"].update(_declared_names(n))
        elif t == "parameter_declaration":
            f["locals"].update(_declared_names(n))
        elif t.startswith("preproc_"):
            f["preproc"][t + " " + _txt(n).split("\n", 1)[0].strip()] += 1
        if not n.children:
            f["tokens"].append((t, _txt(n)))
            if not n.is_named:
                if t in CONTROL:
                    f["skeleton"].append((t, depth))
                elif t in OPERATORS:
                    f["ops"][t] += 1
            continue
        for c in reversed(n.children):
            stack.append((c, depth + 1 if c.type == "compound_statement" else depth))
    return f


def _kw(skel, group) -> int:
    return sum(1 for k, _d in skel if k in group)


def classify(a: dict, b: dict) -> set[str]:
    """Atomic labels for one edit, from the features of the function before (a) and after (b)."""
    if a["tokens"] == b["tokens"]:
        return {"COMMENT"} if a["comments"] != b["comments"] else {"FORMAT"}

    labels: set[str] = set()
    if a["comments"] != b["comments"]:
        labels.add("COMMENT")

    # Shape-preserving edit: the token-kind sequence is identical and only identifier tokens differ.
    swapped_nonlocal = False
    ta, tb = a["tokens"], b["tokens"]
    if len(ta) == len(tb) and all(x[0] == y[0] for x, y in zip(ta, tb)):
        diff = [(x, y) for x, y in zip(ta, tb) if x != y]
        if diff and all(x[0] in IDENT_KINDS for x, _y in diff):
            fwd, back, consistent = {}, {}, True
            for (_k, old), (_k2, new) in diff:
                if fwd.setdefault(old, new) != new or back.setdefault(new, old) != old:
                    consistent = False
            # Every occurrence of a renamed name must be renamed, or it is a swap, not a rename.
            untouched = {x[1] for x, y in zip(ta, tb) if x == y and x[0] in IDENT_KINDS}
            if consistent and not (set(fwd) & untouched) and set(fwd) <= a["locals"]:
                return labels | {"RENAME_LOCAL"}
            swapped_nonlocal = True

    sa, sb = a["skeleton"], b["skeleton"]
    d_branch = _kw(sb, BRANCH) - _kw(sa, BRANCH)
    if d_branch > 0:
        labels.add("BRANCH_ADD")
    elif d_branch < 0:
        labels.add("BRANCH_DEL")
    if _kw(sb, LOOP) != _kw(sa, LOOP):
        labels.add("LOOP_CHANGE")
    if _kw(sb, EXIT) != _kw(sa, EXIT):
        labels.add("EXIT_CHANGE")
    if sa != sb and Counter(k for k, _ in sa) == Counter(k for k, _ in sb):
        labels.add("SKELETON_MOVE")            # same keywords, different order or depth

    if a["signature"] != b["signature"]:
        labels.add("SIGNATURE")
    added, removed = b["calls"] - a["calls"], a["calls"] - b["calls"]
    if added and removed and sum(added.values()) == sum(removed.values()):
        labels.add("CALL_RETARGET")
    else:
        if added:
            labels.add("CALL_ADD")
        if removed:
            labels.add("CALL_DEL")
    for name in a["calls"].keys() & b["calls"].keys():
        if a["calls"][name] != b["calls"][name]:
            continue                            # the count moved: already CALL_ADD / CALL_DEL
        if sorted(a["arity"][name]) != sorted(b["arity"][name]):
            labels.add("ARG_ARITY")
        elif sorted(a["args"][name]) != sorted(b["args"][name]):
            labels.add("ARG_VALUE")

    if d_branch == 0 and _kw(sb, LOOP) == _kw(sa, LOOP) and a["conds"] != b["conds"]:
        labels.add("COND_EDIT")
    if sum(a["returns"].values()) == sum(b["returns"].values()) and a["returns"] != b["returns"]:
        labels.add("RETURN_VALUE")

    # Token-kind labels describe IN-PLACE edits only. When a unit (statement, declaration, branch,
    # loop, exit, call) is added or removed, its tokens come and go with it, so OPERATOR / FIELD /
    # TYPE / literal labels would fire as by-products on nearly every such edit (v0 measured 4.40
    # labels per edit, OPERATOR on 51%). A growing or shrinking edit is described by its units.
    in_place = (a["nstmt"] == b["nstmt"] and a["ndecl"] == b["ndecl"]
                and Counter(k for k, _ in sa) == Counter(k for k, _ in sb)
                and sum(a["calls"].values()) == sum(b["calls"].values()))
    if in_place:
        if a["ops"] != b["ops"]:
            labels.add("OPERATOR")
        if a["nums"] != b["nums"]:
            labels.add("NUM_LITERAL")
        if a["strs"] != b["strs"]:
            labels.add("STRING_LITERAL")
        if a["types"] != b["types"]:
            labels.add("TYPE")
        if a["fields"] != b["fields"]:
            labels.add("FIELD")
    if a["ndecl"] != b["ndecl"]:
        labels.add("LOCAL_DECL")
    if b["nstmt"] > a["nstmt"]:
        labels.add("STMT_ADD")
    elif b["nstmt"] < a["nstmt"]:
        labels.add("STMT_DEL")
    if a["preproc"] != b["preproc"]:
        labels.add("PREPROC")
    if swapped_nonlocal and not (labels & {"CALL_RETARGET", "FIELD", "TYPE"}):
        labels.add("REF_SWAP")

    if not (labels - {"COMMENT"}):
        labels.add("EXPR_EDIT" if a["stmts"] != b["stmts"] else "UNCLASSIFIED")
    return labels


def families(labels) -> list[str]:
    fams = {FAMILY_OF[lab] for lab in labels}
    return [f for f in PRIORITY if f in fams]


def primary(labels) -> str:
    return families(labels)[0]


# ---------------------------------------------------------------------------------------------- walk

class Blobs:
    """One `git cat-file --batch`, strictly request-then-read, so the pipe can never fill (the REW lesson)."""

    def __init__(self, repo_dir: Path):
        self.p = subprocess.Popen(["git", "-C", str(repo_dir), "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, oid: str) -> bytes | None:
        self.p.stdin.write(oid.encode() + b"\n")
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if len(head) < 3:
            return None
        data = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        return data


def jobs(repo: str) -> list[tuple]:
    """(sha, commit_time, canonical_path, old_blob, new_blob), oldest first, renames followed."""
    cfg = REPOS[repo]
    out = subprocess.run(
        ["git", "-C", str(POOL / repo), "log", "--no-merges", "--reverse", "--raw", "--no-abbrev",
         "-M", "--format=C %H %ct"], capture_output=True, text=True, check=True).stdout
    alias: dict[str, str] = {}
    res, sha, ct = [], None, 0
    for line in out.splitlines():
        if line.startswith("C "):
            _c, sha, ct = line.split()
            continue
        if not line.startswith(":"):
            continue
        meta, _tab, paths = line.partition("\t")
        _m1, _m2, old, new, status = meta.split()
        parts = paths.split("\t")
        path = parts[-1]
        if status[0] == "R":
            alias[path] = alias.get(parts[0], parts[0])
        if status[0] not in "MR" or old == new:
            continue
        if not path.endswith(cfg["exts"]) or not path.startswith(cfg["roots"]):
            continue
        res.append((sha, int(ct), alias.get(path, path), old, new))
    return res


def _work(args) -> tuple[list, Counter]:
    repo, chunk = args
    lang = REPOS[repo]["lang"]
    blobs = Blobs(POOL / repo)
    cache: OrderedDict = OrderedDict()

    def parsed(oid):
        if oid in cache:
            cache.move_to_end(oid)
            return cache[oid]
        src = blobs.get(oid)
        val = functions_in(src, lang) if src is not None else ({}, set())
        cache[oid] = val
        if len(cache) > 48:
            cache.popitem(last=False)
        return val

    rows, stats = [], Counter()
    for sha, ct, path, old, new in chunk:
        fa, da = parsed(old)
        fb, db = parsed(new)
        stats["files"] += 1
        stats["ambiguous_names"] += len(da | db)
        for name in sorted(fa.keys() & fb.keys()):      # sorted: row order feeds the seeded null
            na, nb = fa[name], fb[name]
            if na.text == nb.text:
                continue
            A, B = features(na), features(nb)
            labs = classify(A, B)
            ta, tb = Counter(A["tokens"]), Counter(B["tokens"])
            rows.append({"sha": sha, "ct": ct, "path": path, "func": name,
                         "labels": sorted(labs), "primary": primary(labs),
                         "ntok": len(B["tokens"]),
                         "tadd": sum((tb - ta).values()), "tdel": sum((ta - tb).values()), "err": bool(A["has_error"] or B["has_error"])})
    return rows, stats


def cmd_walk(a) -> int:
    import multiprocessing as mp
    js = jobs(a.repo)
    if a.limit:
        js = js[: a.limit]
    step = max(1, math.ceil(len(js) / (a.workers * 8)))
    chunks = [(a.repo, js[i: i + step]) for i in range(0, len(js), step)]
    stats: Counter = Counter()
    n = 0
    with mp.get_context("fork").Pool(a.workers) as pool, open(a.out, "w") as fh:
        for rows, st in pool.imap(_work, chunks):      # ordered: output stays chronological
            stats.update(st)
            for r in rows:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
            n += len(rows)
    print(f"{a.repo}: {len(js):,} modified files over non-merge commits -> {n:,} function edits "
          f"({stats['ambiguous_names']:,} ambiguous same-name definitions skipped) -> {a.out}")
    return 0


# -------------------------------------------------------------------------------------------- report

def load(path: str) -> list[dict]:
    with open(path) as fh:
        return [json.loads(line) for line in fh]


def _cover(counter: Counter, share: float) -> int:
    tot, acc = sum(counter.values()), 0
    for i, (_k, c) in enumerate(counter.most_common(), 1):
        acc += c
        if acc >= share * tot:
            return i
    return len(counter)


def _jacc(x: frozenset, y: frozenset) -> float:
    return len(x & y) / len(x | y) if (x | y) else 1.0


def summarise(rows: list[dict], draws: int = 20) -> dict:
    n = len(rows)
    lab = Counter(l for r in rows for l in r["labels"])
    prim = Counter(r["primary"] for r in rows)
    sig = Counter(tuple(r["labels"]) for r in rows)
    fsig = Counter(tuple(families(r["labels"])) for r in rows)
    resid = sum(1 for r in rows if {"EXPR_EDIT", "UNCLASSIFIED"} & set(r["labels"]))
    hard = sum(1 for r in rows if "UNCLASSIFIED" in r["labels"])

    # Stability: is a function's NEXT edit more like its LAST than like a size-matched stranger's?
    by_fn: dict = defaultdict(list)
    for r in rows:
        by_fn[(r["path"], r["func"])].append(r)
    pairs = [(e[i], e[i + 1]) for e in by_fn.values() for i in range(len(e) - 1)]
    bins: dict = defaultdict(list)
    for r in rows:
        bins[int(math.log2(max(r["ntok"], 1)))].append(r)
    rng = random.Random(SEED)
    stab = {}
    for key, name in ((lambda r: frozenset(r["labels"]), "atomic"),
                      (lambda r: frozenset(families(r["labels"])), "family")):
        obs = sum(_jacc(key(p), key(q)) for p, q in pairs) / len(pairs) if pairs else 0.0
        same = sum(1 for p, q in pairs if p["primary"] == q["primary"]) / len(pairs) if pairs else 0.0
        nulls, nsame = [], []
        for _ in range(draws):
            tot = hit = 0.0
            for p, q in pairs:
                pool = bins[int(math.log2(max(q["ntok"], 1)))]
                s = pool[rng.randrange(len(pool))]
                tot += _jacc(key(p), key(s))
                hit += p["primary"] == s["primary"]
            nulls.append(tot / len(pairs))
            nsame.append(hit / len(pairs))
        stab[name] = {"observed_jaccard": obs, "null_mean": sum(nulls) / draws,
                      "null_min": min(nulls), "null_max": max(nulls),
                      "ratio": obs / (sum(nulls) / draws) if sum(nulls) else None}
        stab["primary_repeat"] = {"observed": same, "null_mean": sum(nsame) / draws,
                                  "ratio": same / (sum(nsame) / draws) if sum(nsame) else None}
    sticky = {}
    for l in LABELS:
        prev = [q for p, q in pairs if l in p["labels"]]
        if len(prev) >= 50 and lab[l]:
            base = sum(1 for _p, q in pairs if l in q["labels"]) / len(pairs)
            sticky[l] = {"n_prev": len(prev), "p_next_given_prev": sum(l in q["labels"] for q in prev) / len(prev),
                         "base": base}
            sticky[l]["lift"] = sticky[l]["p_next_given_prev"] / base if base else None
    return {
        "edits": n, "functions": len(by_fn), "consecutive_pairs": len(pairs),
        "parse_error_share": sum(r["err"] for r in rows) / n,
        "atomic_share": {l: lab[l] / n for l in LABELS},
        "primary_share": {f: prim[f] / n for f in PRIORITY},
        "single_label_share": sum(1 for r in rows if len(r["labels"]) == 1) / n,
        "mean_labels_per_edit": sum(len(r["labels"]) for r in rows) / n,
        "residual_share": resid / n, "unclassified_share": hard / n,
        "distinct_atomic_signatures": len(sig), "atomic_signatures_for_80pct": _cover(sig, 0.8),
        "distinct_family_signatures": len(fsig), "family_signatures_for_80pct": _cover(fsig, 0.8),
        "family_signatures_for_95pct": _cover(fsig, 0.95),
        "top_family_signatures": [["+".join(k), c / n] for k, c in fsig.most_common(10)],
        "stability": stab, "sticky": sticky,
    }


def cmd_report(a) -> int:
    rows = load(a.inp)
    s = summarise(rows)
    if a.json:
        Path(a.json).write_text(json.dumps({"repo": a.repo, **s}, indent=1, sort_keys=True) + "\n")
    print(f"{a.repo}: {s['edits']:,} function edits over {s['functions']:,} functions "
          f"(EXPLORATORY, outcome-blind)\n")
    print(f"  parsed with an ERROR node on either side   {s['parse_error_share']:6.1%}")
    print(f"  no named type (EXPR_EDIT or UNCLASSIFIED)  {s['residual_share']:6.1%}"
          f"   of which UNCLASSIFIED {s['unclassified_share']:.1%}")
    print(f"  exactly one atomic label                   {s['single_label_share']:6.1%}"
          f"   mean labels per edit {s['mean_labels_per_edit']:.2f}")
    print(f"  atomic signatures: {s['distinct_atomic_signatures']:,} distinct, "
          f"{s['atomic_signatures_for_80pct']:,} cover 80%")
    print(f"  family signatures: {s['distinct_family_signatures']:,} distinct, "
          f"{s['family_signatures_for_80pct']} cover 80%, {s['family_signatures_for_95pct']} cover 95%\n")
    print(f"  {'primary family':12} {'share':>7}      {'atomic label':14} {'share of edits':>14}")
    lab_rows = sorted(s["atomic_share"].items(), key=lambda kv: -kv[1])
    for i in range(max(len(PRIORITY), len(lab_rows))):
        left = f"{PRIORITY[i]:12} {s['primary_share'][PRIORITY[i]]:7.1%}" if i < len(PRIORITY) else " " * 20
        right = f"{lab_rows[i][0]:14} {lab_rows[i][1]:14.1%}" if i < len(lab_rows) else ""
        print(f"  {left}      {right}")
    print("\n  Does a function's next edit resemble its last? "
          f"({s['consecutive_pairs']:,} consecutive pairs; null = a size-matched stranger's edit)")
    for name in ("atomic", "family"):
        st = s["stability"][name]
        print(f"    {name:7} label-set Jaccard  observed {st['observed_jaccard']:.3f}  "
              f"null {st['null_mean']:.3f} [{st['null_min']:.3f}, {st['null_max']:.3f}]  "
              f"ratio {st['ratio']:.2f}x")
    pr = s["stability"]["primary_repeat"]
    print(f"    same PRIMARY family          observed {pr['observed']:.3f}  null {pr['null_mean']:.3f}"
          f"                  ratio {pr['ratio']:.2f}x")
    print("\n  Stickiest atomic labels: P(next edit has it | last edit had it) over its base rate")
    for l, v in sorted(s["sticky"].items(), key=lambda kv: -(kv[1]["lift"] or 0))[:10]:
        print(f"    {l:14} {v['p_next_given_prev']:6.1%} vs {v['base']:6.1%}   lift {v['lift']:.2f}x"
              f"   (n={v['n_prev']:,})")
    return 0


def cmd_show(a) -> int:
    rows = [r for r in load(a.inp) if a.label in r["labels"]]
    random.Random(SEED).shuffle(rows)
    for r in rows[: a.n]:
        print(f"{r['sha'][:10]} {r['path']}::{r['func']}  {'+'.join(r['labels'])}")
        subprocess.run(["git", "-C", str(POOL / a.repo), "--no-pager", "show", "--format=", "-U1",
                        "--function-context" if a.context else "-U1", r["sha"], "--", r["path"]])
    print(f"{len(rows):,} edits carry {a.label}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("walk", "report", "show"))
    ap.add_argument("--repo", default="curl", choices=sorted(REPOS))
    ap.add_argument("--out")
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--label", default="UNCLASSIFIED")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--context", action="store_true")
    a = ap.parse_args()
    return {"walk": cmd_walk, "report": cmd_report, "show": cmd_show}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
