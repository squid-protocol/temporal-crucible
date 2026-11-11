#!/usr/bin/env python3
"""KWNEST (exploratory): does a function reorganise -- order and nesting -- when its keyword counts do not?

    python tools/kwnest_eval.py probe  --repo curl --n 3     # show one function's birth vs last, in detail
    python tools/kwnest_eval.py run    --repo curl --n 1200  # the measurement

**Exploratory. No registration, no hypothesis fixed in advance, no p-value claimed.**

KWMAT (`docs/kwmature.md`) found that a function's keyword *recipe* is conserved and its *scale* is not.
Two dimensions were left unmeasured because the scan database cannot hold them:

**The stored signals are scope-blind.** `function_data` has exactly one positional column, `start_line` --
where the function begins. Nothing records where inside a function a keyword falls: no depth, no block, no
section. (`complexity` is equal to `struct_branch` in all 809,654 rows of the curl walk: it is the branch
keyword count, not a control-flow measure.) So from the database one cannot say that a keyword moved, only
that there are more or fewer of them.

This tool goes back to the source. For a function at its first and last snapshot it parses the C with
tree-sitter and records, for every reserved keyword occurrence, **its position in the sequence and its
nesting depth**. Then it asks the decisive question:

    among functions whose keyword MULTISET is identical at both ends -- functions that every
    measure so far calls unchanged -- how many have a different ORDER, or a different DEPTH profile?

A function that keeps the same keywords in the same proportions but moves them deeper inside new
conditionals, or reorders them, has matured in a way nothing measured before this could see.

Needs tree-sitter: run with an engine venv, e.g.
  /srv/storage_16tb/projects/gitgalaxy-worktrees/tc-asof-55c471d10/.venv-tc/bin/python
"""

from __future__ import annotations

import argparse
import os
import random
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

WT = Path(os.environ.get("TC_WORKTREES", "/srv/storage_16tb/projects/temporal-crucible/.claude/worktrees"))
POOL = Path(os.environ.get("TC_POOL", "/srv/storage_16tb/projects/temporal-crucible-pool"))
DBS = {"curl": WT / "forward-asof/dbs/curl_out/curl_galaxy_master.db",
       "ndpi": WT / "forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db"}

# C reserved words. The control-flow subset is what carries structure; the rest are reported but do not
# drive the headline, because a `const` moving is not a reorganisation.
CONTROL = {"if", "else", "for", "while", "do", "switch", "case", "default", "break", "continue",
           "goto", "return"}
OTHER = {"auto", "char", "const", "double", "enum", "extern", "float", "inline", "int", "long",
         "register", "restrict", "short", "signed", "sizeof", "static", "struct", "typedef",
         "union", "unsigned", "void", "volatile"}
KEYWORDS = CONTROL | OTHER
SEED = 2982

_PARSER = None


def parser():
    global _PARSER
    if _PARSER is None:
        try:
            import tree_sitter_language_pack as tslp
        except ImportError:
            sys.exit("tree-sitter is not available: run with an engine venv (see the module docstring)")
        _PARSER = tslp.get_parser("c")
    return _PARSER


def blob(repo: str, sha: str, path: str) -> bytes | None:
    r = subprocess.run(["git", "-C", str(POOL / repo), "show", f"{sha}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def func_name(node) -> str | None:
    d = node.child_by_field_name("declarator")
    while d is not None:
        if d.type == "identifier":
            return d.text.decode("utf-8", "replace")
        nxt = d.child_by_field_name("declarator")
        if nxt is None:
            for c in d.children:
                if c.type == "identifier":
                    return c.text.decode("utf-8", "replace")
            return None
        d = nxt
    return None


def keyword_profile(fn_node) -> list[tuple[str, int]]:
    """[(keyword, nesting depth)] in source order, depth counted in enclosing blocks inside the function."""
    out = []

    def walk(n, depth):
        for c in n.children:
            if c.type in KEYWORDS and not c.is_named:      # tree-sitter keeps keywords as anonymous tokens
                out.append((c.type, depth))
            deeper = depth + 1 if c.type == "compound_statement" else depth
            walk(c, deeper)

    body = fn_node.child_by_field_name("body")
    if body is None:
        return out
    walk(body, 0)
    return out


def functions_in(src: bytes) -> dict[str, object]:
    tree = parser().parse(src)
    found = {}

    def walk(n):
        if n.type == "function_definition":
            nm = func_name(n)
            if nm and nm not in found:
                found[nm] = n
        for c in n.children:
            walk(c)

    walk(tree.root_node)
    return found


def candidates(repo: str, limit: int, rng: random.Random):
    """(path, name, first_sha, last_sha, counts_identical) for functions seen at >= 2 snapshots."""
    con = sqlite3.connect(f"file:{DBS[repo]}?mode=ro", uri=True)
    q = ("SELECT f.file_path, fn.func_name, f.commit_hash, f.commit_date, fn.loc, fn.complexity, "
         "fn.struct_linear, fn.state_pointers, fn.struct_args "
         "FROM function_data fn JOIN file_data f ON fn.file_id = f.id "
         "WHERE f.file_path LIKE '%.c' ORDER BY f.file_path, fn.func_name, f.commit_date")
    cur, key, acc, out = con.execute(q), None, [], []
    for path, name, sha, date, loc, cx, sl, sp, sa in cur:
        k = (path, name)
        if k != key:
            if key and len(acc) >= 2:
                sig_first, sig_last = acc[0][2], acc[-1][2]
                out.append((key[0], key[1], acc[0][1], acc[-1][1], sig_first == sig_last))
            key, acc = k, []
        if not acc or acc[-1][0] != date:
            acc.append((date, sha, (loc, cx, sl, sp, sa)))
    if key and len(acc) >= 2:
        out.append((key[0], key[1], acc[0][1], acc[-1][1], acc[0][2] == acc[-1][2]))
    con.close()
    rng.shuffle(out)
    return out[:limit] if limit else out


def compare(repo: str, path: str, name: str, sha_a: str, sha_b: str, cache: dict):
    prof = []
    for sha in (sha_a, sha_b):
        ck = (sha, path)
        if ck not in cache:
            src = blob(repo, sha, path)
            cache[ck] = functions_in(src) if src else {}
        node = cache[ck].get(name)
        if node is None:
            return None
        prof.append((keyword_profile(node), node.text))
    (a, txt_a), (b, txt_b) = prof
    ca, cb = Counter(k for k, _d in a), Counter(k for k, _d in b)
    seq_a, seq_b = [k for k, _d in a], [k for k, _d in b]
    ctl_a = [(k, d) for k, d in a if k in CONTROL]
    ctl_b = [(k, d) for k, d in b if k in CONTROL]
    depth = lambda xs: (max((d for _k, d in xs), default=0),
                        sum(d for _k, d in xs) / len(xs) if xs else 0.0)
    maxa, mna = depth(ctl_a)
    maxb, mnb = depth(ctl_b)
    return {"byte_same": txt_a == txt_b,
            "multiset_same": ca == cb,
            "order_same": seq_a == seq_b,
            "ctl_order_same": [k for k, _ in ctl_a] == [k for k, _ in ctl_b],
            "depth_same": [d for _k, d in ctl_a] == [d for _k, d in ctl_b],
            "max_depth_a": maxa, "max_depth_b": maxb,
            "mean_depth_a": mna, "mean_depth_b": mnb,
            "n_ctl_a": len(ctl_a), "n_ctl_b": len(ctl_b)}


def cmd_probe(a) -> int:
    rng = random.Random(SEED)
    cache: dict = {}
    shown = 0
    for path, name, sa, sb, same in candidates(a.repo, 4000, rng):
        if not same:
            continue
        r = compare(a.repo, path, name, sa, sb, cache)
        if not r or not r["multiset_same"]:
            continue
        print(f"{path}::{name}  {sa[:8]} -> {sb[:8]}")
        print(f"  same keyword multiset: {r['multiset_same']}   same order: {r['ctl_order_same']}   "
              f"same depths: {r['depth_same']}")
        print(f"  control keywords {r['n_ctl_a']} -> {r['n_ctl_b']}; "
              f"max depth {r['max_depth_a']} -> {r['max_depth_b']}; "
              f"mean depth {r['mean_depth_a']:.2f} -> {r['mean_depth_b']:.2f}\n")
        shown += 1
        if shown >= a.n:
            return 0
    return 0


def leaves(node):
    """(type, text) for every leaf token under a node -- the material an edit can touch."""
    out = []

    def walk(n):
        if not n.children:
            out.append((n.type, n.text.decode("utf-8", "replace")))
        for c in n.children:
            walk(c)

    walk(node)
    return out


def cmd_what(a) -> int:
    """For functions edited WITHOUT touching the keyword skeleton: what did change?"""
    rng = random.Random(SEED)
    cache: dict = {}
    kinds: Counter = Counter()
    n = 0
    for path, name, sa, sb, _flag in candidates(a.repo, a.n * 4, rng):
        if n >= a.n:
            break
        prof = []
        ok = True
        for sha in (sa, sb):
            ck = (sha, path)
            if ck not in cache:
                src = blob(a.repo, sha, path)
                cache[ck] = functions_in(src) if src else {}
            node = cache[ck].get(name)
            if node is None:
                ok = False
                break
            prof.append(node)
        if not ok:
            continue
        ta, tb = prof[0].text, prof[1].text
        if ta == tb:
            continue
        ka = Counter(k for k, _d in keyword_profile(prof[0]))
        kb = Counter(k for k, _d in keyword_profile(prof[1]))
        if ka != kb:
            continue                      # skeleton changed: not the population we are asking about
        n += 1
        la, lb = Counter(leaves(prof[0])), Counter(leaves(prof[1]))
        for (typ, _txt), c in ((la - lb) + (lb - la)).items():
            kinds[typ] += c
    if not n:
        return 1
    tot = sum(kinds.values())
    print(f"{a.repo}: {n:,} functions EDITED with an identical keyword skeleton.")
    print(f"  What changed instead -- differing leaf tokens by kind ({tot:,} token differences):\n")
    print(f"  {'token kind':24} {'count':>8} {'share':>8}")
    for typ, c in kinds.most_common(12):
        print(f"  {typ:24} {c:8,} {c / tot:8.1%}")
    return 0


def cmd_run(a) -> int:
    rng = random.Random(SEED)
    cache: dict = {}
    tot = ms_same = byte_same = edited = 0
    reorg = depth_moved = order_moved = both_same = 0
    deeper = shallower = 0
    for path, name, sa, sb, _flag in candidates(a.repo, a.n * 4, rng):
        if tot >= a.n:
            break
        r = compare(a.repo, path, name, sa, sb, cache)
        if r is None:
            continue
        tot += 1
        if not r["multiset_same"]:
            continue
        ms_same += 1
        if r["byte_same"]:
            byte_same += 1
            continue          # a function nobody touched cannot have reorganised: not evidence
        edited += 1
        o = not r["ctl_order_same"]
        d = not r["depth_same"]
        order_moved += o
        depth_moved += d
        reorg += (o or d)
        both_same += (not o and not d)
        if r["mean_depth_b"] > r["mean_depth_a"]:
            deeper += 1
        elif r["mean_depth_b"] < r["mean_depth_a"]:
            shallower += 1
    print(f"{a.repo}: {tot:,} functions compared at first vs last snapshot "
          f"(tree-sitter, C reserved keywords)\n")
    print(f"  identical keyword MULTISET at both ends: {ms_same:,} ({ms_same / tot:.1%})")
    if not ms_same:
        return 0
    print(f"    of those, byte-identical source   {byte_same:6,}  {byte_same / ms_same:6.1%}  "
          f"<- nobody touched them; they cannot reorganise")
    print(f"    EDITED but same multiset          {edited:6,}  {edited / ms_same:6.1%}  "
          f"<- the only functions that can answer the question")
    if not edited:
        return 0
    print(f"\n  of those {edited:,} EDITED functions, which every count-based measure calls unchanged:")
    print(f"    control-keyword ORDER changed      {order_moved:6,}  {order_moved / edited:6.1%}")
    print(f"    nesting DEPTH profile changed      {depth_moved:6,}  {depth_moved / edited:6.1%}")
    print(f"    either (reorganised)               {reorg:6,}  {reorg / edited:6.1%}")
    print(f"    neither (genuinely identical)      {both_same:6,}  {both_same / edited:6.1%}")
    print(f"\n    of those that moved depth: deeper {deeper:,}, shallower {shallower:,}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("probe", "run", "what"))
    ap.add_argument("--repo", default="curl", choices=sorted(DBS))
    ap.add_argument("--n", type=int, default=1200)
    a = ap.parse_args()
    return {"probe": cmd_probe, "run": cmd_run, "what": cmd_what}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
