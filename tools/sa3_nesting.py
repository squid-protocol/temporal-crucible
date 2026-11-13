#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Control-flow nesting depth of a source file, from tree-sitter (SA3 Amendment 2). No outcome is read here.

    python tools/sa3_nesting.py --selftest
    python tools/sa3_nesting.py FILE --lang c

The engine has no nesting measure: its `complexity` column equals the branch-keyword count. This goes back to
the source. A CONTROL NODE is a conditional, a loop, a multi-way branch (the statement, never its arms) or a
try block; the node kinds are listed per language below and are part of the registration. The depth of a
control node is 1 + the number of control nodes among its ancestors.

    nest_max   the deepest control node in the file (0 when it has none)
    nest_mean  the mean depth over the file's control nodes (0 when it has none)

Needs tree_sitter_language_pack (an engine venv has it; the LAWS scorer venv does not).
"""
from __future__ import annotations

import argparse, sys

PACK_VERSION = "1.20.0"   # tree_sitter_language_pack; node kinds are a property of the grammar version
CONTROL = {
    "c": "if_statement for_statement while_statement do_statement switch_statement",
    "cpp": "if_statement for_statement for_range_loop while_statement do_statement switch_statement try_statement",
    "python": "if_statement for_statement while_statement match_statement try_statement",
    "go": "if_statement for_statement expression_switch_statement type_switch_statement select_statement",
    "java": "if_statement for_statement enhanced_for_statement while_statement do_statement switch_expression "
            "try_statement try_with_resources_statement",
    "javascript": "if_statement for_statement for_in_statement while_statement do_statement switch_statement try_statement",
    "typescript": "if_statement for_statement for_in_statement while_statement do_statement switch_statement try_statement",
    "tsx": "if_statement for_statement for_in_statement while_statement do_statement switch_statement try_statement",
    "php": "if_statement for_statement foreach_statement while_statement do_statement switch_statement "
           "match_expression try_statement",
    "csharp": "if_statement for_statement foreach_statement while_statement do_statement switch_statement "
              "switch_expression try_statement",
    "rust": "if_expression for_expression while_expression loop_expression match_expression",
    "kotlin": "if_expression for_statement while_statement do_while_statement when_expression try_expression",
    "ruby": "if unless while until for case case_match begin",
    "zig": "IfStatement IfExpr ForStatement ForExpr WhileStatement WhileExpr SwitchExpr",
    "swift": "if_statement for_statement while_statement repeat_while_statement switch_statement do_statement",
    "perl": "conditional_statement for_statement cstyle_for_statement loop_statement try_statement",
    "fortran": "if_statement do_loop select_case_statement forall_statement",
    "matlab": "if_statement for_statement while_statement switch_statement try_statement",
}
CONTROL = {k: frozenset(v.split()) for k, v in CONTROL.items()}
# the unit language of laws_units -> the grammar(s) to parse with, by file suffix where one language has several
GRAMMAR = {"c": "c", "cpp": "cpp", "python": "python", "go": "go", "java": "java", "php": "php", "csharp": "csharp",
           "rust": "rust", "kotlin": "kotlin", "ruby": "ruby", "zig": "zig", "swift": "swift", "perl": "perl",
           "fortran": "fortran", "matlab": "matlab"}   # racket: S-expressions, no control node kinds -> not measured
JSTS = {".ts": "typescript", ".tsx": "tsx"}            # every other jsts suffix parses as javascript
_PARSERS: dict = {}


def grammar_for(unit_lang: str, path: str) -> str | None:
    if unit_lang == "jsts":
        return next((g for suf, g in JSTS.items() if path.endswith(suf)), "javascript")
    if unit_lang in ("c", "cpp"):                       # a C-family repo: C++ grammar for C++ suffixes and for .h
        return "c" if path.endswith(".c") else "cpp"
    return GRAMMAR.get(unit_lang)


def nesting(src: bytes, grammar: str) -> dict:
    import tree_sitter_language_pack as tslp
    if grammar not in _PARSERS:
        _PARSERS[grammar] = tslp.get_parser(grammar)
    tree = _PARSERS[grammar].parse(src)
    kinds = CONTROL[grammar]
    n = total = best = 0
    stack = [(tree.root_node, 0)]                      # iterative: real files nest deeper than Python's recursion
    while stack:
        node, d = stack.pop()
        if node.is_named and node.type in kinds:   # Ruby names its keyword tokens like its nodes
            d += 1
            n += 1; total += d
            best = max(best, d)
        stack.extend((c, d) for c in node.children)
    return {"nest_max": best, "nest_mean": round(total / n, 4) if n else 0.0, "control_nodes": n,
            "parse_error": bool(tree.root_node.has_error)}


SELFTEST = {  # grammar -> (source, expected nest_max)
    "c": (b"int f(int a){ if(a){ for(;;){ while(a){ switch(a){case 1: break;} } } } return a?1:0; }", 4),
    "cpp": (b"int f(int a){ if(a){ for(auto x: v){ try{ g(); } catch(...){} } } return 0; }", 3),
    "python": (b"def f(a):\n  if a:\n    for x in a:\n      while x:\n        try:\n          pass\n        except E:\n          pass\n", 4),
    "go": (b"package p\nfunc f(a int){ if a>0 { for i:=0;i<a;i++ { switch a { case 1: } } } }", 3),
    "java": (b"class A{ void f(int a){ if(a>0){ for(int i=0;i<a;i++){ while(a>0){ switch(a){ case 1: break; } } } } } }", 4),
    "javascript": (b"function f(a){ if(a){ for(const x of a){ while(x){ switch(x){ case 1: break } } } } }", 4),
    "typescript": (b"function f(a:number){ if(a){ for(const x of [a]){ switch(x){ case 1: break } } } }", 3),
    "php": (b"<?php function f($a){ if($a){ foreach($a as $x){ while($x){ switch($x){ case 1: break; } } } } }", 4),
    "csharp": (b"class A{ void f(int a){ if(a>0){ foreach(var x in y){ while(a>0){ switch(a){ case 1: break; } } } } } }", 4),
    "rust": (b"fn f(a:i32){ if a>0 { for x in 0..a { while a>0 { match a { _=>{} } } } } }", 4),
    "kotlin": (b"fun f(a:Int){ if(a>0){ for(x in 0..a){ while(a>0){ when(a){ else->{} } } } } }", 4),
    "ruby": (b"def f(a)\n if a\n  while a\n   unless a\n    case a\n    when 1 then 2\n    end\n   end\n  end\n end\nend", 4),
    "zig": (b"fn f(a: i32) void { if (a > 0) { while (a > 0) { for (xs) |x| { switch (x) { else => {} } } } } }", 4),
    "swift": (b"func f(a:Int){ if a>0 { for x in 0..<a { while a>0 { switch a { default: break } } } } }", 4),
    "perl": (b"sub f { my $a=shift; if($a){ foreach my $x (@a){ while($x){ unless($x){ } } } } }", 4),
    "fortran": (b"subroutine f(a)\n integer a\n if (a>0) then\n  do i=1,a\n   if (i>1) then\n   end if\n  end do\n end if\nend subroutine", 3),
    "matlab": (b"function f(a)\n if a\n  for i=1:a\n   while a\n    switch a\n     case 1\n    end\n   end\n  end\n end\nend", 4),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--lang")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        bad = 0
        for g, (src, want) in SELFTEST.items():
            got = nesting(src, g)
            ok = got["nest_max"] == want and not got["parse_error"]
            bad += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {g:<11} nest_max {got['nest_max']} (want {want})  nodes {got['control_nodes']}"
                  f"  mean {got['nest_mean']}  parse_error {got['parse_error']}")
        return 1 if bad else 0
    print(nesting(open(a.file, "rb").read(), a.lang))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
