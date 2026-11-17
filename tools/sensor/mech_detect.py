"""Mechanical-swap detector for one change (the part of change_report.py that finds repeated old-call -> new-call substitutions).

A swap is a line pair, in a hunk that removes and adds the same number of lines, where exactly one call name left the line and exactly one call name
arrived (`git_buf_free(x)` -> `git_buf_dispose(x)`). A swap seen `min_repeat` or more times in the one change is reported as mechanical; the share is
the lines that belong to such swaps over the lines the change touched. Language-agnostic: a call is `name(`."""
import collections
import re

CALL = re.compile(r"([A-Za-z_]\w*)\s*\(")
KW = {"if", "while", "for", "switch", "sizeof", "return", "defined"}
# a C type or storage keyword before a parenthesis is a declarator or a cast (`int (*cb)(...)`), not a call: `int -> GIT_CALLBACK` is not a swap of calls
KW |= {"int", "char", "void", "long", "short", "unsigned", "signed", "float", "double", "struct", "enum", "union", "const", "static", "extern", "volatile", "bool", "typeof"}
COMMENT = ("//", "*", "/*", "--")  # a comment line names functions in prose; a rename there is not a code edit
MIN_REPEAT = 5


def hunk_swaps(removed, added):
    """(old, new) call pairs from one hunk's removed and added lines; empty unless the hunk replaces line for line."""
    out = []
    if not removed or len(removed) != len(added):
        return out
    for x, y in zip(removed, added):
        if x.lstrip().startswith(COMMENT) or y.lstrip().startswith(COMMENT):
            continue
        cx = [c for c in CALL.findall(x) if c not in KW]
        cy = [c for c in CALL.findall(y) if c not in KW]
        sx, sy = set(cx) - set(cy), set(cy) - set(cx)
        if len(sx) == 1 and len(sy) == 1:
            out.append((next(iter(sx)), next(iter(sy)), x, y))
    return out


def hunk_swaps_loose(removed, added):
    """Hunk-level pairing: across the whole hunk exactly one call name left and exactly one arrived, whatever else the lines changed and whatever the sizes.
    One swap per hunk, weighted by how many removed lines held the old call; the lines returned are the first removed and added line that name each call."""
    rem = [x for x in removed if not x.lstrip().startswith(COMMENT)]
    add = [y for y in added if not y.lstrip().startswith(COMMENT)]
    if not rem or not add:
        return []
    cx = collections.Counter(c for x in rem for c in set(CALL.findall(x)) if c not in KW)
    cy = collections.Counter(c for y in add for c in set(CALL.findall(y)) if c not in KW)
    sx, sy = set(cx) - set(cy), set(cy) - set(cx)
    if len(sx) != 1 or len(sy) != 1:
        return []
    x, y = next(iter(sx)), next(iter(sy))
    lx = next(l for l in rem if x in CALL.findall(l))
    ly = next(l for l in add if y in CALL.findall(l))
    return [(x, y, lx, ly)] * cx[x]


def swaps_cooc(hunks, min_repeat=MIN_REPEAT, ratio=0.4):
    """The sweep study's own rule, at the scale of one change: an (old, new) pair counts when the old call leaves and the new call arrives in the same hunk
    at least `min_repeat` times and in at least `ratio` of the hunks that lose the old call or gain the new one (the smaller side); each call is used once,
    best pair first. Tolerates hunks that change several calls and lines that change more than the call. Returns (counts, big, lines) like swaps()."""
    co, rem_h, add_h, sample = collections.Counter(), collections.Counter(), collections.Counter(), {}
    for _path, removed, added in hunks:
        rem = [x for x in removed if not x.lstrip().startswith(COMMENT)]
        add = [y for y in added if not y.lstrip().startswith(COMMENT)]
        if not rem or not add:
            continue
        cr = {c for x in rem for c in CALL.findall(x) if c not in KW}
        ca = {c for y in add for c in CALL.findall(y) if c not in KW}
        gone, new = cr - ca, ca - cr
        for x in gone:
            rem_h[x] += 1
        for y in new:
            add_h[y] += 1
        for x in gone:
            for y in new:
                co[(x, y)] += 1
                sample.setdefault((x, y), (next(l for l in rem if x in CALL.findall(l)), next(l for l in add if y in CALL.findall(l))))
    big, used_x, used_y = {}, set(), set()
    for (x, y), c in co.most_common():
        if x in used_x or y in used_y:
            continue
        if c >= min_repeat and c >= ratio * min(rem_h[x], add_h[y]):
            big[(x, y)] = c
            used_x.add(x)
            used_y.add(y)
    return co, big, [((x, y), *sample[(x, y)]) for (x, y), c in big.items() for _ in range(c)]


def swaps(hunks, min_repeat=MIN_REPEAT, loose=False):
    """hunks: iterable of (path, removed_lines, added_lines). Returns (counts of every swap pair, the pairs seen min_repeat+ times, the lines that belong to them)."""
    counts = collections.Counter()
    seen = []
    for _path, removed, added in hunks:
        for x, y, lx, ly in (hunk_swaps_loose(removed, added) if loose else hunk_swaps(removed, added)):
            counts[(x, y)] += 1
            seen.append(((x, y), lx, ly))
    big = {k: v for k, v in counts.items() if v >= min_repeat}
    return counts, big, [s for s in seen if s[0] in big]


def is_pure(old_line, new_line, old, new):
    """True when substituting `old` with `new` in the removed line gives the added line exactly (ignoring spacing): the line changed in nothing else."""
    sub = re.sub(rf"\b{re.escape(old)}\b", new, old_line)
    return re.sub(r"\s+", "", sub) == re.sub(r"\s+", "", new_line)


def mechanical_lines(big):
    """Changed lines (removed plus added) that belong to the repeated swaps."""
    return sum(2 * n for n in big.values())
