"""Source-file generation with planted structure, for Python and C.

A source file is held as a small model -- functions whose bodies are trees of simple statements and control
nodes -- and rendered to text deterministically. Every planted property in the manifest is computed from the
model (`measure`), and the model is what the history edits, so the text and the manifest cannot drift apart.

Conventions the rendered code obeys, so that independent counts of the text agree with the model:

* Every simple statement renders as exactly one line (an allocation pair, C only, as exactly two).
* The only branch keywords in the text are the control nodes' own: Python `if`, `elif`, `for`, `while`;
  C `if` (an `else if` link carries one), `for`, `while`, `switch`. No comprehensions, no conditional
  expressions, no `do`, and no branch word inside a comment, docstring or string.
* `branches` = the number of those keyword tokens (see DECISIONS.md).
* `max_nesting` follows `tools/sa3_nesting.py`: a control node (Python: if/for/while/try; C:
  if/for/while/switch) sits at 1 + the number of control nodes above it, and an else-if chain link sits at its
  head's depth. Python `elif` arms and C `else if` arms are arms of one node here, which is exactly that rule.
  An `if` placed in an `else` arm is a child of the node, one level deeper (Python block / C braces).
* `calls_out` = call sites in a unit file whose callee is a function defined in another unit file;
  `calls_in` = call sites in other unit files whose callee is defined in this file. Only unit files make
  cross-file calls, and only to unit files.
* `state_writes_in_branches` = assignments to module/file state (`_STATE[...] = ...` in Python,
  `g_state[...] = ...;` in C) lexically inside an arm of an `if` (any arm, including `elif`/`else`) or of a C
  `switch`, at any depth. State writes outside every conditional also exist and are not counted.
* C only: `pointer_ops` = dereference-writes `*cursor = ...;`; `alloc_ops` = calls to `malloc` and `free`.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------------------------- vocabulary
# No word below is, or contains as a separate word, a branch keyword (if, elif, for, while, switch).
# r4: no directory word may be a name GitHub Linguist's vendor.yml / documentation.yml matches (LINGUIST_AVOID);
# "cache" was one ((^|/)cache/) and is replaced by "memo".
DIR_WORDS = ["core", "net", "io", "storage", "parser", "render", "auth", "memo", "codec", "sched", "metrics",
             "config", "plugins", "query", "index", "proto", "events", "model", "sync", "util", "store", "media",
             "crypto", "graph", "shell", "admin", "audit", "batch", "queue", "stream"]
FILE_NOUNS = ["frame", "record", "buffer", "token", "packet", "session", "table", "cursor", "node", "header",
              "socket", "page", "block", "entry", "column", "schema", "matrix", "vector", "ledger", "chunk",
              "window", "signal", "filter", "route", "bucket", "channel", "digest", "segment", "layer", "slot",
              "report", "field", "handle", "lookup", "timer", "worker", "batch", "range", "symbol", "image"]
FILE_ROLES = ["codec", "store", "reader", "writer", "pool", "map", "util", "core", "parser", "builder",
              "manager", "client", "server", "cache", "index", "queue", "view", "model", "tools", "ops"]
VERBS = ["parse", "build", "load", "store", "merge", "split", "scan", "pack", "unpack", "encode", "decode",
         "count", "reset", "flush", "fetch", "apply", "check", "update", "compute", "emit", "collect", "drain",
         "resolve", "select", "insert", "remove", "copy", "trim", "sort", "hash"]
DOC_NOUNS = ["state", "entries", "buffers", "records", "frames", "requests", "offsets", "counters", "tables",
             "results", "segments", "headers"]
DOC_VERBS = ["Helpers that manage", "Routines that track", "Utilities that shape", "Code that moves",
             "Logic that groups", "Functions that read"]

# r4: directory and file names that GitHub Linguist (v9.7.0, commit e0c78d62c42a) treats as vendored or as
# documentation by name alone, with the pattern each matches. The base repository uses none of them except the
# planted non-unit places (vendor/thirdparty/, docs/, LICENSE, README.md, .gitattributes); `check_linguist_names`
# enforces it at generation time. The lists themselves are never read at run time.
LINGUIST_AVOID = {
    "cache/": r"(^|/)cache/", "dist/": r"(^|/)dist/", "env/": r"(^|/)env/", "testdata/": r"(^|/)testdata/",
    "extern/, external/, externals/": r"(^|/)[Ee]xtern(als?)?/", "vendor/, vendors/": r"(^|/)vendors?/",
    "third_party/, thirdparty/, 3rdparty/": r"(3rd|[Tt]hird)[-_]?[Pp]arty/", "node_modules/": r"(^|/)node_modules/",
    "bower_components/": r"(^|/)bower_components/", "tests/fixtures/": r"(^|/)[Tt]ests?/fixtures/",
    "specs/fixtures/": r"(^|/)[Ss]pecs?/fixtures/", "dependencies/ (top)": r"^[Dd]ependencies/",
    "deps/ (top)": r"^deps/", "debian/ (top)": r"^debian/", "docs/, doc/ (top)": r"^[Dd]ocs?/",
    "documentation/": r"(^|/)[Dd]ocumentation/", "javadoc/": r"(^|/)[Jj]avadoc/", "groovydoc/": r"(^|/)[Gg]roovydoc/",
    "man/ (top)": r"^[Mm]an/", "examples/ (top)": r"^[Ee]xamples/", "demo/, demos/ (top)": r"^[Dd]emos?/",
    "samples/, sample/ (top)": r"^[Ss]amples?/", "inst/doc/": r"(^|/)inst/doc/",
    "README, CHANGELOG, CONTRIBUTING, COPYING, INSTALL, LICENSE, CITATION files":
        r"(^|/)(README|[Rr]eadme|CHANGE(S|LOG)?|CONTRIBUTING|COPYING|INSTALL|LICEN[CS]E|[Ll]icen[cs]e|CITATION)(\.|$)",
    "cpplint.py, configure, config.guess, config.sub": r"(^|/)(cpplint\.py|configure$|config\.guess$|config\.sub$)",
    ".gitattributes, .gitignore, .gitmodules": r"(^|/)\.git(attributes|ignore|modules)$",
}
_AVOID_RX = [(name, re.compile(rx)) for name, rx in LINGUIST_AVOID.items()]


def linguist_clash(path: str):
    """The LINGUIST_AVOID entry `path` matches, or None."""
    return next((name for name, rx in _AVOID_RX if rx.search(path)), None)


PY_BRANCH_WORDS = ("if", "elif", "for", "while")
C_BRANCH_WORDS = ("if", "for", "while", "switch")

FILLER_KINDS = ("assign", "local_call")
LICENCE_LINES = {
    "python": ["# SPDX-License-Identifier: MIT", "# Copyright (c) The Example Project Authors"],
    "c": ["/* SPDX-License-Identifier: MIT */", "/* Copyright (c) The Example Project Authors */"],
}


# ---------------------------------------------------------------------------------------------- the model
@dataclass
class Simple:
    """One simple statement. `lit` is the integer literal in it, the thing tweaks and fixes change."""
    sid: int
    kind: str                 # assign | local_call | ext_call | state | ptr | alloc
    lit: int
    form: int = 0             # which spelling of the statement
    ref: tuple | None = None  # ext_call: (file id, function name); local_call: function name
    key: int = 0              # state: slot index


@dataclass
class Arm:
    tag: str                  # if | elif | else | for | while | try | except | case | default
    lit: int
    body: list = field(default_factory=list)


@dataclass
class Control:
    kind: str                 # if | for | while | try | switch
    arms: list
    form: int = 0


@dataclass
class Function:
    name: str
    body: list
    doc: str = ""


@dataclass
class CodeFile:
    """A generated source file. `role` is the file kind (unit, test, vendor, ...); only units make
    cross-file calls."""
    fid: str
    lang: str
    role: str
    stem: str
    doc: str
    functions: list
    header: bool = False      # licence header present
    style: int = 0            # toggled by a reformat sweep; changes spelling, never lines or structure
    next_sid: int = 0
    refs_cache: list | None = None

    def new_sid(self) -> int:
        self.next_sid += 1
        return self.next_sid


# ------------------------------------------------------------------------------------------ tree helpers
def iter_nodes(body, depth=0, cond=False, parents=()):
    """Yield (node, depth_of_enclosing_control, inside_conditional, containing_body, parents) for every node.
    `depth` is the number of control nodes above the node."""
    for node in body:
        yield node, depth, cond, body, parents
        if isinstance(node, Control):
            for arm in node.arms:
                arm_cond = cond or arm.tag in ("if", "elif", "else", "case", "default")
                yield from iter_nodes(arm.body, depth + 1, arm_cond, parents + ((node, arm),))


def all_nodes(cf: CodeFile):
    for fn in cf.functions:
        yield from ((fn,) + t for t in iter_nodes(fn.body))


def node_branches(node: Control) -> int:
    if node.kind == "if":
        return sum(1 for a in node.arms if a.tag in ("if", "elif"))
    if node.kind in ("for", "while", "switch"):
        return 1
    return 0                  # try


def find_simple(cf: CodeFile, sid: int):
    for fn, node, _d, _c, body, _p in all_nodes(cf):
        if isinstance(node, Simple) and node.sid == sid:
            return node
    return None


# ------------------------------------------------------------------------------------------- measurement
def measure(cf: CodeFile, text: str | None = None) -> dict:
    """Planted properties of one file, from the model. `calls_in` is filled by the caller (it depends on
    every other file). `loc` is the rendered line count, passed in as text or computed by the caller."""
    branches = 0
    max_nesting = 0
    calls_out = 0
    state_in = 0
    state_all = 0
    ptr = 0
    alloc = 0
    control_nodes = 0
    for _fn, node, depth, cond, _b, _p in all_nodes(cf):
        if isinstance(node, Control):
            control_nodes += 1
            branches += node_branches(node)
            max_nesting = max(max_nesting, depth + 1)
        else:
            if node.kind == "ext_call":
                calls_out += 1
            elif node.kind == "state":
                state_all += 1
                state_in += cond
            elif node.kind == "ptr":
                ptr += 1
            elif node.kind == "alloc":
                alloc += 2
    out = {"branches": branches, "max_nesting": max_nesting, "calls_out": calls_out,
           "state_writes_in_branches": state_in, "state_writes_total": state_all, "control_nodes": control_nodes}
    if cf.lang == "c":
        out["pointer_ops"] = ptr
        out["alloc_ops"] = alloc
        out["pointer_declarations"] = pointer_declarations(cf)
    if text is not None:
        out["loc"] = text.count("\n")
    return out


def pointer_declarations(cf: CodeFile) -> int:
    """C only: declarations of a pointer in the text (`long *name`): the `long *data` parameter of every function
    definition, prototype and extern declaration, plus the locals `long *cursor` / `long *buf` of a function that
    writes through a pointer / allocates. None of these is a pointer operation in the sense of `pointer_ops`."""
    n = 2 * len(cf.functions) + len({name for _fid, name in ext_refs(cf)})
    for fn in cf.functions:
        kinds = {x.kind for x, *_ in iter_nodes(fn.body) if isinstance(x, Simple)}
        n += ("ptr" in kinds) + ("alloc" in kinds)
    return n


def ext_refs(cf: CodeFile):
    """(file id, function name) of every cross-file call site, sorted. Cached on the file: call sites are only
    ever created by `fill_code_file` and removed by `drop_calls_to`, which both clear the cache (tweaks and
    structure steps touch literals and filler statements only)."""
    if cf.refs_cache is None:
        cf.refs_cache = sorted(n.ref for _f, n, *_ in all_nodes(cf) if isinstance(n, Simple) and n.kind == "ext_call")
    return cf.refs_cache


# ---------------------------------------------------------------------------------------------- rendering
def module_of(path: str) -> str:
    """Python module path of a file path: src/a/b.py -> src.a.b"""
    return path[:-3].replace("/", ".")


def render(cf: CodeFile, path_of) -> str:
    """Text of a file. `path_of(fid)` gives the current path of another file (for Python imports)."""
    return _render_py(cf, path_of) if cf.lang == "python" else _render_c(cf)


def _cond_py(form: int, lit: int, tag: str) -> str:
    opts = (f"n > {lit}", f"total % {lit} == 0", f"n == {lit}", f"total < {lit}", f"len(data) > {lit}")
    return opts[(form + (tag == "elif")) % len(opts)]


def _cond_c(form: int, lit: int, tag: str) -> str:
    opts = (f"n > {lit}", f"total % {lit} == 0", f"n == {lit}", f"total < {lit}", f"data != 0 && n > {lit}")
    return opts[(form + (tag == "elif")) % len(opts)]


def _simple_py(s: Simple, cf: CodeFile) -> list:
    q = '"' if cf.style % 2 == 0 else "'"
    if s.kind == "assign":
        opts = (f"total = total + {s.lit}", f"total += n * {s.lit}", f"total -= {s.lit}",
                f"total = (total * {s.lit}) % 1000003", f"total = total ^ {s.lit}")
        return [opts[s.form % len(opts)]]
    if s.kind == "init":
        return [f"total = n + {s.lit}"]
    if s.kind == "local_call":
        return [f"total += {s.ref}(data, {s.lit})"]
    if s.kind == "ext_call":
        return [f"total += {s.ref[1]}(data, {s.lit})"]
    if s.kind == "state":
        return [f"_STATE[{q}{cf.stem}_{s.key}{q}] = total + {s.lit}"]
    raise ValueError(s.kind)


def _simple_c(s: Simple, cf: CodeFile) -> list:
    if s.kind == "assign":
        opts = (f"total = total + {s.lit};", f"total += n * {s.lit};", f"total -= {s.lit};",
                f"total = (total * {s.lit}) % 1000003;", f"total = total ^ {s.lit};")
        return [opts[s.form % len(opts)]]
    if s.kind == "init":
        return [f"long total = n + {s.lit};"]
    if s.kind == "local_call":
        return [f"total += {s.ref}(data, {s.lit});"]
    if s.kind == "ext_call":
        return [f"total += {s.ref[1]}(data, {s.lit});"]
    if s.kind == "state":
        return [f"g_state[{s.key}] = total + {s.lit};"]
    if s.kind == "ptr":
        return [f"*cursor = total + {s.lit};"]
    if s.kind == "alloc":
        return [f"buf = malloc(sizeof(long) * {s.lit});", "free(buf);"]
    raise ValueError(s.kind)


def _body_py(body, cf, ind, depth, out):
    pad = "    " * ind
    for node in body:
        if isinstance(node, Simple):
            out.extend(pad + line for line in _simple_py(node, cf))
            continue
        if node.kind == "if":
            for arm in node.arms:
                if arm.tag == "else":
                    out.append(pad + "else:")
                else:
                    out.append(f"{pad}{arm.tag} {_cond_py(node.form, arm.lit, arm.tag)}:")
                _body_py(arm.body, cf, ind + 1, depth + 1, out)
        elif node.kind == "for":
            var = "item" if depth == 0 else f"item{depth}"
            out.append(f"{pad}for {var} in data:")
            _body_py(node.arms[0].body, cf, ind + 1, depth + 1, out)
        elif node.kind == "while":
            out.append(f"{pad}while n > {node.arms[0].lit}:")
            _body_py(node.arms[0].body, cf, ind + 1, depth + 1, out)
            out.append(pad + "    n -= 1")
        elif node.kind == "try":
            out.append(pad + "try:")
            _body_py(node.arms[0].body, cf, ind + 1, depth + 1, out)
            out.append(pad + "except (KeyError, ValueError):")
            _body_py(node.arms[1].body, cf, ind + 1, depth + 1, out)
        else:
            raise ValueError(f"python has no {node.kind}")


def _body_c(body, cf, ind, depth, out):
    pad = "    " * ind
    for node in body:
        if isinstance(node, Simple):
            out.extend(pad + line for line in _simple_c(node, cf))
            continue
        if node.kind == "if":
            for i, arm in enumerate(node.arms):
                if arm.tag == "if":
                    out.append(f"{pad}if ({_cond_c(node.form, arm.lit, arm.tag)}) {{")
                elif arm.tag == "elif":
                    out.append(f"{pad}}} else if ({_cond_c(node.form, arm.lit, arm.tag)}) {{")
                else:
                    out.append(pad + "} else {")
                _body_c(arm.body, cf, ind + 1, depth + 1, out)
            out.append(pad + "}")
        elif node.kind == "for":
            v = f"i{depth + 1}"
            out.append(f"{pad}for (long {v} = 0; {v} < n; {v}++) {{")
            _body_c(node.arms[0].body, cf, ind + 1, depth + 1, out)
            out.append(pad + "}")
        elif node.kind == "while":
            out.append(f"{pad}while (n > {node.arms[0].lit}) {{")
            _body_c(node.arms[0].body, cf, ind + 1, depth + 1, out)
            out.append(pad + "    n--;")
            out.append(pad + "}")
        elif node.kind == "switch":
            cases = [a for a in node.arms if a.tag == "case"]
            out.append(f"{pad}switch (n % {len(cases) + 1}) {{")
            for j, arm in enumerate(cases):            # no declaration is ever generated, so no braces
                out.append(f"{pad}case {j}:")
                _body_c(arm.body, cf, ind + 1, depth + 1, out)
                out.append(pad + "    break;")
            out.append(pad + "default: break;")
            out.append(pad + "}")
        else:
            raise ValueError(f"c has no {node.kind}")


def _render_py(cf: CodeFile, path_of) -> str:
    out = []
    if cf.header:
        out.extend(LICENCE_LINES["python"])
    q3 = '"""' if cf.style % 2 == 0 else "'''"
    out.append(f"{q3}{cf.doc}{q3}")
    out.append("")
    imports = sorted({(module_of(path_of(fid)), name) for fid, name in ext_refs(cf)})
    for mod, name in imports:
        out.append(f"from {mod} import {name}")
    if imports:
        out.append("")
    out.append("_STATE = {}")
    for fn in cf.functions:
        out.extend(["", "", f"def {fn.name}(data, n):", f"    {q3}{fn.doc}{q3}"])
        _body_py(fn.body, cf, 1, 0, out)
        out.append("    return total")
    return "\n".join(out) + "\n"


def _render_c(cf: CodeFile) -> str:
    out = []
    if cf.header:
        out.extend(LICENCE_LINES["c"])
    out.append(f"/* {cf.doc} */" if cf.style % 2 == 0 else f"// {cf.doc}")
    if any(isinstance(n, Simple) and n.kind == "alloc" for _f, n, *_ in all_nodes(cf)):
        out.append("#include <stdlib.h>")
    out.append("")
    externs = sorted({name for _fid, name in ext_refs(cf)})
    for name in externs:
        out.append(f"extern long {name}(long *data, long n);")
    if externs:
        out.append("")
    out.append("static long g_state[64];")
    for fn in cf.functions:                          # prototypes: a function may call one defined below it
        out.append(f"long {fn.name}(long *data, long n);")
    for fn in cf.functions:
        out.extend(["", f"long {fn.name}(long *data, long n) {{"])
        uses_cursor = any(isinstance(n, Simple) and n.kind == "ptr" for n, *_ in iter_nodes(fn.body))
        uses_buf = any(isinstance(n, Simple) and n.kind == "alloc" for n, *_ in iter_nodes(fn.body))
        body = list(fn.body)
        init, rest = body[0], body[1:]
        _body_c([init], cf, 1, 0, out)
        if uses_cursor:
            out.append("    long *cursor = data;")
        if uses_buf:
            out.append("    long *buf = 0;")
        _body_c(rest, cf, 1, 0, out)
        out.append("    return total;")
        out.append("}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------- planted targets
def lognormal_trunc(rng: random.Random, median: float, sigma: float, lo: float, hi: float) -> float:
    """A lognormal draw, truncated to [lo, hi] by rejection (no pile-up at the bounds)."""
    for _ in range(1000):
        x = median * math.exp(rng.gauss(0.0, sigma))
        if lo <= x <= hi:
            return x
    return min(max(median, lo), hi)


def draw_targets(rng: random.Random, lang: str, loc: int) -> dict:
    """Per-file planted densities, each drawn independently of size and of each other."""
    t = {
        "loc": loc,
        "branches": (lognormal_trunc(rng, 0.075, 0.5, 0.01, 0.20) if lang == "python" else
                     lognormal_trunc(rng, 0.06, 0.5, 0.01, 0.12)),    # C spends more lines per branch
        "max_nesting": min(7, 1 + int(rng.expovariate(0.65))),
        "calls_out": lognormal_trunc(rng, 0.025, 0.6, 0.002, 0.10),
        "calls_in_attract": math.exp(rng.gauss(0.0, 0.7)),
        "state_writes_in_branches": lognormal_trunc(rng, 0.02, 0.7, 0.002, 0.08),
    }
    if lang == "c":
        t["pointer_ops"] = lognormal_trunc(rng, 0.02, 0.6, 0.002, 0.08)
        t["alloc_ops"] = lognormal_trunc(rng, 0.012, 0.6, 0.002, 0.06)
    return t


# -------------------------------------------------------------------------------------------- generation
class _Builder:
    """Builds one file's model from its targets. All randomness comes from the file's own stream."""

    def __init__(self, rng, cf: CodeFile, lit_lo=2, lit_hi=97):
        self.rng = rng
        self.cf = cf
        self.lit_lo, self.lit_hi = lit_lo, lit_hi

    def lit(self):
        return self.rng.randint(self.lit_lo, self.lit_hi)

    def filler(self, fn_name):
        cf, rng = self.cf, self.rng
        others = [f.name for f in cf.functions if f.name != fn_name]
        if others and rng.random() < 0.25:
            return Simple(cf.new_sid(), "local_call", self.lit(), ref=rng.choice(others))
        return Simple(cf.new_sid(), "assign", self.lit(), form=rng.randrange(5))

    def control(self, kind):
        rng = self.rng
        if kind == "if":
            arms = [Arm("if", self.lit())]
        elif kind == "try":
            arms = [Arm("try", 0), Arm("except", 0)]
        elif kind == "switch":
            arms = [Arm("case", 0) for _ in range(rng.randint(2, 3))] + [Arm("default", 0)]
        else:
            arms = [Arm(kind, self.lit())]
        return Control(kind, arms, form=rng.randrange(5))


def _slots(fn: Function, max_depth: int):
    """Places a new control node can go, with the depth it would get: (body list, new node depth)."""
    out = [(fn.body, 1)]
    for node, depth, _c, _b, _p in iter_nodes(fn.body):
        if isinstance(node, Control) and depth + 2 <= max_depth:
            for arm in node.arms:
                if arm.tag != "default":
                    out.append((arm.body, depth + 2))
    return out


def _insert(rng, body, node):
    """Insert after the function's init statement when the body is a function body."""
    lo = 1 if body and isinstance(body[0], Simple) and body[0].kind == "init" else 0
    body.insert(rng.randint(lo, len(body)), node)


def build_code_file(rng: random.Random, fid: str, lang: str, role: str, stem: str, targets: dict,
                    pick_call_target=None) -> CodeFile:
    """Generate a file meeting `targets` in one go (see `start_code_file` and `fill_code_file`)."""
    cf = start_code_file(rng, fid, lang, role, stem, targets)
    fill_code_file(rng, cf, targets, pick_call_target)
    return cf


def start_code_file(rng: random.Random, fid: str, lang: str, role: str, stem: str, targets: dict) -> CodeFile:
    """First phase: the file's functions and their names (so other files can call them before the bodies
    exist). Function names carry the file's stem, which is unique in the repo, so they are unique too."""
    L = int(targets["loc"])
    n_fn = max(1, min(L // 12, int(round(L / rng.uniform(18, 40)))))
    doc = f"{rng.choice(DOC_VERBS)} {stem.replace('_', ' ')} {rng.choice(DOC_NOUNS)}."
    cf = CodeFile(fid, lang, role, stem, doc, [])
    names = set()
    for _ in range(n_fn):
        for _try in range(50):
            name = f"{stem}_{rng.choice(VERBS)}"
            if _try > 10:
                name += f"_{rng.choice(FILE_NOUNS)}"
            if name not in names:
                break
        names.add(name)
        cf.functions.append(Function(name, [], doc=f"{rng.choice(VERBS).capitalize()} the {rng.choice(DOC_NOUNS)}."))
    return cf


def fill_code_file(rng: random.Random, cf: CodeFile, targets: dict, pick_call_target=None) -> CodeFile:
    """Second phase: bodies meeting `targets` (loc, densities). `pick_call_target(rng)` returns a (file id,
    function name) in another unit file, or None; only units are given one. The realised loc equals the
    target unless the planted structure cannot fit in it, in which case it is the smallest that fits."""
    lang = cf.lang
    L = int(targets["loc"])
    B = int(round(L * targets["branches"]))
    D = min(int(targets["max_nesting"]), B)
    bld = _Builder(rng, cf)
    for fn in cf.functions:
        fn.body.append(Simple(cf.new_sid(), "init", bld.lit()))

    kinds = ["if", "if", "if", "for", "while"] + (["switch"] if lang == "c" else [])
    # 1. the spine: D nested nodes in one function, so the file's max nesting is exactly D
    if D > 0:
        fn = rng.choice(cf.functions)
        body = fn.body
        for level in range(D):
            node = bld.control(rng.choice(kinds) if level < D - 1 else rng.choice(kinds))
            _insert(rng, body, node)
            if level == D - 1:
                break
            if node.kind == "if" and rng.random() < 0.35:
                node.arms.append(Arm("else", 0))      # exercise "an if inside a braced/indented else"
                body = node.arms[-1].body
            else:
                body = rng.choice([a for a in node.arms if a.tag != "default"]).body
    # 2. the remaining branches: elif links (flat) or new nodes no deeper than D
    remaining = B - D
    while remaining > 0:
        ifs = [n for f in cf.functions for n, *_ in iter_nodes(f.body) if isinstance(n, Control) and n.kind == "if"]
        if ifs and rng.random() < 0.3:
            node = rng.choice(ifs)
            pos = len(node.arms) - (1 if node.arms[-1].tag == "else" else 0)
            node.arms.insert(pos, Arm("elif", bld.lit()))
        else:
            fn = rng.choice(cf.functions)
            body, depth = rng.choice(_slots(fn, D))
            node = bld.control(rng.choice(kinds))
            if node.kind == "if" and rng.random() < 0.2:
                node.arms.append(Arm("else", 0))
            _insert(rng, body, node)
        remaining -= 1
    # 3. Python try blocks: no branch keyword, but a control node for nesting
    if lang == "python" and D >= 1:
        for fn in cf.functions:
            if rng.random() < 0.15:
                body, depth = rng.choice(_slots(fn, D))
                _insert(rng, body, bld.control("try"))
    # 4. every arm gets at least one statement
    for fn in cf.functions:
        for node, *_ in list(iter_nodes(fn.body)):
            if isinstance(node, Control):
                for arm in node.arms:
                    if arm.tag != "default" and not arm.body:
                        arm.body.append(bld.filler(fn.name))
    # 5. required statements
    cond_arms, free_bodies = [], []
    for fn in cf.functions:
        free_bodies.append(fn.body)
        for node, depth, cond, body, parents in iter_nodes(fn.body):
            if isinstance(node, Control):
                for arm in node.arms:
                    if arm.tag in ("if", "elif", "else", "case"):
                        cond_arms.append(arm.body)
                    elif not cond and arm.tag in ("for", "while"):
                        free_bodies.append(arm.body)

    def place(bodies, stmt):
        _insert(rng, rng.choice(bodies), stmt)

    if pick_call_target is not None:
        for _ in range(int(round(L * targets["calls_out"]))):
            ref = pick_call_target(rng)
            if ref is not None:
                place(free_bodies + cond_arms, Simple(cf.new_sid(), "ext_call", bld.lit(), ref=ref))
    if cond_arms:
        for _ in range(int(round(L * targets["state_writes_in_branches"]))):
            place(cond_arms, Simple(cf.new_sid(), "state", bld.lit(), key=rng.randrange(64)))
    for _ in range(int(round(L * 0.006))):      # state writes outside every conditional: not counted
        place(free_bodies, Simple(cf.new_sid(), "state", bld.lit(), key=rng.randrange(64)))
    if lang == "c":
        for _ in range(int(round(L * targets.get("pointer_ops", 0)))):
            place(free_bodies + cond_arms, Simple(cf.new_sid(), "ptr", bld.lit()))
        for _ in range(int(round(L * targets.get("alloc_ops", 0) / 2))):
            place(free_bodies + cond_arms, Simple(cf.new_sid(), "alloc", bld.lit()))
    cf.refs_cache = None
    # 6. fill to the target line count with one-line fillers
    all_bodies = []
    for fn in cf.functions:
        all_bodies.append((fn, fn.body))
        for node, *_ in iter_nodes(fn.body):
            if isinstance(node, Control):
                all_bodies.extend((fn, a.body) for a in node.arms if a.tag != "default")
    # Python imports are one line per distinct callee; callee names are unique, so any path will do here
    have = render(cf, lambda fid: "src/placeholder.py").count("\n")
    for _ in range(max(0, L - have)):
        fn, body = rng.choice(all_bodies)
        _insert(rng, body, bld.filler(fn.name))
    return cf


# ---------------------------------------------------------------------------------------- history edits
def tweak(rng: random.Random, cf: CodeFile, new_lit: int, prefer_cond=False):
    """Change one statement's literal (no change to lines or structure). Returns (sid, old, new)."""
    cands = []
    for _f, node, _d, cond, _b, _p in all_nodes(cf):
        if isinstance(node, Simple) and (cond or not prefer_cond):
            cands.append(node)
    if not cands:
        cands = [n for _f, n, *_ in all_nodes(cf) if isinstance(n, Simple)]
    s = cands[rng.randrange(len(cands))]
    old = s.lit
    s.lit = new_lit
    return (s.sid, old, new_lit)


def _max_depth_nodes(cf):
    return [(n, d) for _f, n, d, *_ in all_nodes(cf) if isinstance(n, Control)]


def removable_units(cf: CodeFile):
    """Branch units that can be removed without changing max nesting, calls, state writes in branches or any
    other planted count except branches (and loc). Returns a list of handles:

    ("elif", node, arm)   an `elif` / `else if` arm whose body holds only filler statements (dropped with it);
    ("flatten", node, body)  a leaf `for` / `while` / `if` / `switch` (no control node inside), replaced in its
                          parent `body` by its own statements (so calls, pointer and allocation operations stay); allowed
                          only, for an `if` / `switch`, when its statements hold no state write or it sits inside a
                          conditional (so every state write stays inside one), and only when it is not the
                          file's only deepest control node."""
    nodes = _max_depth_nodes(cf)
    if not nodes:
        return []
    top = max(d for _n, d in nodes)
    at_top = sum(1 for _n, d in nodes if d == top)
    out = []
    for _fn, node, depth, cond, body, _p in all_nodes(cf):
        if not isinstance(node, Control) or node.kind == "try":
            continue
        stmts = [x for a in node.arms for x in a.body]
        leaf = all(isinstance(x, Simple) for x in stmts)
        conditional = node.kind in ("if", "switch")  # its arms are conditionals; a loop body is not
        if leaf and (depth < top or at_top > 1) \
                and (not conditional or cond or not any(x.kind == "state" for x in stmts)):
            out.append(("flatten", node, body))
        if node.kind == "if":
            for arm in node.arms:
                if arm.tag == "elif" and all(isinstance(x, Simple) and x.kind in FILLER_KINDS for x in arm.body):
                    out.append(("elif", node, arm))
    return out


def structure_step(rng: random.Random, cf: CodeFile, direction: int, lit: int) -> bool:
    """Add (direction=+1) or remove (-1) one branch, keeping max nesting, calls and state writes unchanged.
    Returns False when no such step exists."""
    if direction < 0:
        cands = removable_units(cf)
        if not cands:
            return False
        kind = "elif" if any(c[0] == "elif" for c in cands) and rng.random() < 0.5 else "flatten"
        pool = [c for c in cands if c[0] == kind] or cands
        c = pool[rng.randrange(len(pool))]
        if c[0] == "elif":
            c[1].arms.remove(c[2])
        else:
            i = next(j for j, x in enumerate(c[2]) if x is c[1])
            c[2][i:i + 1] = [x for a in c[1].arms for x in a.body]
        return True
    nodes = _max_depth_nodes(cf)
    if not nodes:
        return False
    top = max(d for _n, d in nodes) + 1                # current max nesting
    bld = _Builder(rng, cf)
    ifs = [n for n, _d in nodes if n.kind == "if"]
    fn = cf.functions[rng.randrange(len(cf.functions))]
    if ifs and rng.random() < 0.5:
        node = ifs[rng.randrange(len(ifs))]
        pos = len(node.arms) - (1 if node.arms[-1].tag == "else" else 0)
        owner = next(f for f in cf.functions if any(n is node for n, *_ in iter_nodes(f.body)))
        node.arms.insert(pos, Arm("elif", lit, [bld.filler(owner.name)]))
        return True
    body, _depth = _slots(fn, top)[rng.randrange(len(_slots(fn, top)))]
    node = Control("if", [Arm("if", lit, [bld.filler(fn.name)])], form=rng.randrange(5))
    _insert(rng, body, node)
    return True


def drop_calls_to(cf: CodeFile, dead_fid: str) -> int:
    """Replace call sites into a deleted file with a local statement. Returns the number replaced."""
    n = 0
    for _f, node, *_ in all_nodes(cf):
        if isinstance(node, Simple) and node.kind == "ext_call" and node.ref[0] == dead_fid:
            node.kind, node.ref, node.form = "assign", None, node.lit % 5
            n += 1
    cf.refs_cache = None
    return n


# ------------------------------------------------------------------------------------- other file kinds
def generated_table(lang: str, rows: int, rng: random.Random) -> str:
    """The one generated file: a header saying so and a large constant table."""
    vals = [rng.randint(0, 65535) for _ in range(rows * 8)]
    if lang == "python":
        out = ["# Code generated by tablegen 1.4 from tables.yaml. DO NOT EDIT.", "", "TABLE = ["]
        for r in range(rows):
            out.append("    " + ", ".join(str(v) for v in vals[r * 8:(r + 1) * 8]) + ",")
        out.append("]")
    else:
        out = ["/* Code generated by tablegen 1.4 from tables.yaml. DO NOT EDIT. */", "",
               "const long gen_table[] = {"]
        for r in range(rows):
            out.append("    " + ", ".join(str(v) for v in vals[r * 8:(r + 1) * 8]) + ",")
        out.append("};")
    return "\n".join(out) + "\n"


LICENCE_TEXT = """MIT License

Copyright (c) The Example Project Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

DOC_SENTENCES = ["The {w} module keeps its {n} in one place.", "Each {w} call returns a total.",
                 "Run the {w} tools from the project root.", "The {w} layer reads {n} from the store.",
                 "See the {w} notes on {n} sizing.", "Values in {w} are stored as plain integers."]


def doc_lines(rng: random.Random, k: int) -> list:
    return [rng.choice(DOC_SENTENCES).format(w=rng.choice(DIR_WORDS), n=rng.choice(DOC_NOUNS)) for _ in range(k)]
