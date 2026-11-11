#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""How do declared-AI commits comment? (EXPLORATORY, outcome-blind)

A commit is **declared AI** when its message names an AI tool in a Co-authored-by / Assisted-by / Generated-by /
"Generated with" line (Claude, Codex / OpenAI / ChatGPT / GPT, Copilot, Cursor, Gemini, Aider, Windsurf, Devin, ...).
A bare `Assisted-by: <person>` is not AI: curl uses it for human help.

For every non-merge commit since 2024-01-01 the lines it adds (and removes) in in-scope source files are read with the
engine's positional comment stream on the new (old) file version. Per commit:
- added non-blank lines and added comment lines;
- comment length; **prose** share (comment lines with >= 4 alphabetic words);
- danger wording (DC lexicon); debt markers (TODO / FIXME / XXX / HACK);
- removed comment lines.
Python docstrings are strings, not comments, in the engine's stream, so only `#` comments count for Python.
Undeclared AI use lands in the "other" group and dilutes every contrast toward zero.

    GITGALAXY_PATH=$E PYTHONPATH=$E <venv>/bin/python tools/ai_comments.py      # -> docs/ai_comments_exploratory.md
"""
from __future__ import annotations

import datetime as dt
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
from dc_eval import DANGER  # noqa: E402

ADOPTERS = ("harfbuzz", "openssl", "redis", "ndpi", "prometheus")
CONTROLS = ("postgres", "libxml2", "curl", "libgit2")
# owner (2026-11-11): every gitgalaxy commit is written with Gemini or Claude, so its undeclared commits are not
# human. It is an all-AI reference, never part of the AI-vs-other contrast.
REFERENCE = ("gitgalaxy",)
SINCE = "2024-01-01"
EXT = {".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hh": "cpp", ".hpp": "cpp", ".hxx": "cpp",
       ".py": "python", ".go": "go"}
EXCL = re.compile(r"(^|/)(tests?|testdata|docs?|fuzz|fuzzing|scripts|examples?|vendor|third_party|\.github)/")
TOOLS = (r"claude|anthropic|codex|openai|chatgpt|gpt-?\d|copilot|cursor|gemini|aider|windsurf|codeium|devin|"
         r"tabnine|codewhisperer|amazon q|jules")
TRAILER = re.compile(rf"^\s*(co-authored-by|assisted-by|generated-by|generated (with|by)|written (with|by))\b.*({TOOLS})",
                     re.I | re.M)
CC_BADGE = re.compile(r"generated with \[?claude code", re.I)
DEBT = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
WORD = re.compile(r"[A-Za-z]{2,}")
MARKS = re.compile(r"^\s*(/\*+|\*+/?|//+|#+)\s*|\s*\*+/\s*$")
SIZE_EDGES = (8, 32, 128, 512)
T0 = time.time()
_W = {}


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def git(repo, *a, text=True):
    p = subprocess.run(["git", "-C", str(repo), *a], capture_output=True)
    return p.stdout.decode("utf-8", "replace") if text else p.stdout


def prism():
    if not _W:
        from gitgalaxy.core.prism import Prism
        from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
        from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS
        _W["p"] = Prism(LEXICAL_FAMILY_HEURISTICS, LANGUAGE_DEFINITIONS)
    return _W["p"]


def tool_of(msg):
    m = TRAILER.search(msg)
    if m:
        t = m.group(0).lower()
    elif CC_BADGE.search(msg):
        t = "claude"
    else:
        return None
    for name, rx in (("claude", "claude|anthropic"), ("codex/openai", "codex|openai|chatgpt|gpt"),
                     ("copilot", "copilot"), ("cursor", "cursor")):
        if re.search(rx, t):
            return name
    return "other-ai"


def lang_of(r, path):
    ext = pathlib.PurePosixPath(path).suffix.lower()
    lg = EXT.get(ext)
    if lg == "c" and r == "harfbuzz":
        lg = "cpp"
    return lg


def comment_lines(r, rev, path, lg):
    raw = git(POOL_DIR / r, "show", f"{rev}:{path}", text=False)
    if not raw or len(raw) > 2_000_000:
        return None
    txt = raw.decode("utf-8", "replace")
    try:
        pos = prism().split_positional_comment_stream(txt, lg).split("\n")
    except Exception:
        return None
    return txt.split("\n"), pos


def commit_task(t):
    r, sha = t
    repo = POOL_DIR / r
    out = Counter()
    parent = git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return r, sha, out
    add, rem, old, new = defaultdict(list), defaultdict(list), None, None
    for ln in git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        if ln.startswith("--- "):
            old = None if ln[4:] == "/dev/null" else ln[6:]
        elif ln.startswith("+++ "):
            new = None if ln[4:] == "/dev/null" else ln[6:]
        elif ln.startswith("@@"):
            m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", ln)
            if not m:
                continue
            s, n = int(m.group(1)), int(m.group(2) or 1)
            s2, n2 = int(m.group(3)), int(m.group(4) or 1)
            if old and n > 0:
                rem[old].extend(range(s, s + n))
            if new and n2 > 0:
                add[new].extend(range(s2, s2 + n2))
    for path, ls in add.items():
        lg = lang_of(r, path)
        if not lg or EXCL.search(path):
            continue
        v = comment_lines(r, sha, path, lg)
        if v is None:
            continue
        lines, pos = v
        out["files"] += 1
        for i in ls:
            if i - 1 >= len(lines) or not lines[i - 1].strip():
                continue
            out["added"] += 1
            c = pos[i - 1].strip() if i - 1 < len(pos) else ""
            if not c:
                continue
            body = MARKS.sub("", c)
            out["c"] += 1
            out["c_chars"] += len(body)
            out["c_prose"] += len(WORD.findall(body)) >= 4
            out["c_danger"] += bool(DANGER.search(c))
            out["c_debt"] += bool(DEBT.search(c))
    for path, ls in rem.items():
        lg = lang_of(r, path)
        if not lg or EXCL.search(path):
            continue
        v = comment_lines(r, parent, path, lg)
        if v is None:
            continue
        lines, pos = v
        for i in ls:
            if i - 1 < len(lines) and lines[i - 1].strip():
                out["removed"] += 1
                if i - 1 < len(pos) and pos[i - 1].strip():
                    out["removed_c"] += 1
    return r, sha, out


def size_bin(n):
    return sum(n > c for c in SIZE_EDGES)


def rate(xs, num, den):
    d = sum(x[den] for x in xs)
    return sum(x[num] for x in xs) / d if d else np.nan


def std_share(ai, other, num="c", den="added"):
    """Comment share of the 'other' commits re-weighted to the AI commits' size distribution."""
    w = Counter(size_bin(x["added"]) for x in ai)
    tot, acc = 0, 0.0
    for b, k in w.items():
        ob = [x for x in other if size_bin(x["added"]) == b]
        r_ = rate(ob, num, den)
        if np.isfinite(r_):
            acc += k * r_
            tot += k
    return acc / tot if tot else np.nan


def main() -> int:
    repos = ADOPTERS + CONTROLS + REFERENCE
    meta = []
    for r in repos:
        txt = git(POOL_DIR / r, "log", "--no-merges", f"--since={SINCE}", "--format=%x1e%H%x1f%ct%x1f%ae%x1f%B")
        for rec in txt.split("\x1e")[1:]:
            h, ct, ae, msg = rec.split("\x1f", 3)
            meta.append({"r": r, "sha": h, "ct": int(ct), "author": ae.strip().lower(), "tool": tool_of(msg)})
    log(f"commits since {SINCE}: {len(meta):,}; declared AI {sum(1 for m in meta if m['tool']):,}")
    with multiprocessing.get_context("fork").Pool(8) as p:
        res = {(r, s): c for r, s, c in p.imap_unordered(commit_task, [(m["r"], m["sha"]) for m in meta], chunksize=8)}
    C = [dict(m, **res.get((m["r"], m["sha"]), Counter())) for m in meta]
    C = [c for c in C if c.get("added", 0) > 0]
    for c in C:
        for k in ("c", "c_chars", "c_prose", "c_danger", "c_debt", "removed", "removed_c", "added"):
            c.setdefault(k, 0)
    log(f"commits adding in-scope source lines: {len(C):,}")
    first_ai = {r: min((c["ct"] for c in C if c["r"] == r and c["tool"]), default=None) for r in repos}

    L = ["# How do declared-AI commits comment? (EXPLORATORY, outcome-blind)", "",
         "**Status: exploratory.** No fix or defect data is read. Script: `tools/ai_comments.py`. A commit is "
         "*declared AI* when its message names an AI tool in a Co-authored-by / Assisted-by / Generated-by / "
         "\"Generated with\" line. A bare `Assisted-by: <person>` is human help (curl's usage) and does not count. "
         "**Undeclared AI use is in the 'other' group**, which dilutes every contrast toward zero.", "",
         f"- commits since {SINCE} that add in-scope source lines (C/C++, Python, Go; tests, docs, vendor, examples "
         f"excluded): {len(C):,}; declared AI: {sum(1 for c in C if c['tool']):,}",
         "- **comment share** = added comment lines ÷ added non-blank lines; **prose** = comment lines with ≥ 4 words; "
         "Python counts `#` comments only (docstrings are strings).", "",
         "## 1. Declared-AI vs other commits, same repo, since the repo's first declared-AI commit", "",
         "| repo | AI commits (main tool) | other commits | median added lines AI / other | comment share AI | "
         "other | other, at AI's size mix | chars per comment AI / other | prose AI / other | danger AI / other | "
         "comments deleted per removed line AI / other |",
         "|---|---|---:|---|---:|---:|---:|---|---|---|---|"]
    for r in ADOPTERS:
        if first_ai[r] is None:
            continue
        w = [c for c in C if c["r"] == r and c["ct"] >= first_ai[r]]
        ai = [c for c in w if c["tool"]]
        ot = [c for c in w if not c["tool"]]
        if len(ai) < 10 or len(ot) < 10:
            L.append(f"| {r} | {len(ai)} | {len(ot)} | too few | | | | | | | |")
            continue
        tool = Counter(c["tool"] for c in ai).most_common(1)[0][0]
        L.append(
            f"| {r} | {len(ai):,} ({tool}) | {len(ot):,} | {np.median([c['added'] for c in ai]):.0f} / "
            f"{np.median([c['added'] for c in ot]):.0f} | **{rate(ai, 'c', 'added'):.1%}** | {rate(ot, 'c', 'added'):.1%} | "
            f"{std_share(ai, ot):.1%} | {rate(ai, 'c_chars', 'c'):.0f} / {rate(ot, 'c_chars', 'c'):.0f} | "
            f"{rate(ai, 'c_prose', 'c'):.0%} / {rate(ot, 'c_prose', 'c'):.0%} | "
            f"{rate(ai, 'c_danger', 'c'):.1%} / {rate(ot, 'c_danger', 'c'):.1%} | "
            f"{rate(ai, 'removed_c', 'removed'):.1%} / {rate(ot, 'removed_c', 'removed'):.1%} |")

    # within author
    L += ["", "## 2. The same people with and without declared AI", "",
          "Authors with ≥ 5 declared-AI and ≥ 5 other commits after their repo's first AI commit. Per author: comment "
          "share of their AI commits minus that of their other commits, the other side re-weighted to the AI side's "
          "size mix.", ""]
    diffs, prose_d, by_repo = [], [], Counter()
    for (r, a) in {(c["r"], c["author"]) for c in C if c["tool"] and c["r"] in ADOPTERS}:
        w = [c for c in C if c["r"] == r and c["author"] == a and c["ct"] >= first_ai[r]]
        ai = [c for c in w if c["tool"]]
        ot = [c for c in w if not c["tool"]]
        if len(ai) < 5 or len(ot) < 5:
            continue
        d = rate(ai, "c", "added") - std_share(ai, ot)
        if np.isfinite(d):
            diffs.append(d)
            by_repo[r] += 1
            pa, po = rate(ai, "c_prose", "c"), rate(ot, "c_prose", "c")
            if np.isfinite(pa) and np.isfinite(po):
                prose_d.append(pa - po)
    if diffs:
        d = np.array(diffs)
        rng = np.random.default_rng(2982)
        bm = [np.median(rng.choice(d, len(d))) for _ in range(2000)]
        L += [f"- authors: **{len(d)}** ({', '.join(f'{r} {n}' for r, n in by_repo.most_common())})",
              f"- comment share, AI minus own other commits: median **{np.median(d):+.1%}** "
              f"(bootstrap 95% [{np.quantile(bm, 0.025):+.1%}, {np.quantile(bm, 0.975):+.1%}]); authors who comment "
              f"more with AI: {int((d > 0).sum())} of {len(d)}",
              f"- prose share of their comments, AI minus other: median {np.median(prose_d):+.0%} "
              f"({sum(1 for x in prose_d if x > 0)} of {len(prose_d)} higher with AI)" if prose_d else "- prose: n/a"]
    else:
        L.append("- no author meets the threshold")

    # by tool
    L += ["", "## 3. By tool (adopters pooled, declared-AI commits; gitgalaxy excluded)", "",
          "| tool | commits | comment share | chars per comment | prose |", "|---|---:|---:|---:|---:|"]
    for t, n in Counter(c["tool"] for c in C if c["tool"] and c["r"] in ADOPTERS).most_common():
        xs = [c for c in C if c["tool"] == t and c["r"] in ADOPTERS]
        L.append(f"| {t} | {n:,} | {rate(xs, 'c', 'added'):.1%} | {rate(xs, 'c_chars', 'c'):.0f} | "
                 f"{rate(xs, 'c_prose', 'c'):.0%} |")
    L += ["", "Within one repo, so the tool is not confounded with the project (tools with ≥ 30 commits there):", "",
          "| repo | tool | commits | comment share | at the repo's other-commit size mix | chars per comment | prose |",
          "|---|---|---:|---:|---:|---:|---:|"]
    for r in ADOPTERS:
        w = [c for c in C if c["r"] == r and first_ai[r] is not None and c["ct"] >= first_ai[r]]
        ot = [c for c in w if not c["tool"]]
        for t, n in Counter(c["tool"] for c in w if c["tool"]).most_common():
            if n < 30:
                continue
            xs = [c for c in w if c["tool"] == t]
            L.append(f"| {r} | {t} | {n:,} | {rate(xs, 'c', 'added'):.1%} | {std_share(ot, xs):.1%} | "
                     f"{rate(xs, 'c_chars', 'c'):.0f} | {rate(xs, 'c_prose', 'c'):.0%} |")

    # culture over time
    def q(ct):
        d = dt.datetime.fromtimestamp(ct, dt.timezone.utc)
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"
    qs = sorted({q(c["ct"]) for c in C})
    L += ["", "## 4. Commenting culture over time (all commits; comment share of added lines; AI share of commits in "
          "brackets)", "", "| repo | " + " | ".join(qs) + " |", "|---|" + "---:|" * len(qs)]
    for r in repos:
        cells = []
        for qq in qs:
            xs = [c for c in C if c["r"] == r and q(c["ct"]) == qq]
            if len(xs) < 20:
                cells.append("·")
                continue
            ai_share = np.mean([bool(c["tool"]) for c in xs])
            cells.append(f"{rate(xs, 'c', 'added'):.0%}" + (f" [{ai_share:.0%}]" if ai_share >= 0.05 else ""))
        L.append(f"| {r}{' (control)' if r in CONTROLS else ''} | " + " | ".join(cells) + " |")
    # all-AI reference
    for r in REFERENCE:
        xs = [c for c in C if c["r"] == r]
        if not xs:
            continue
        cl = [c for c in xs if c["tool"] == "claude"]
        un = [c for c in xs if not c["tool"]]
        L += ["", f"## 5. All-AI reference: {r} (every commit written with Gemini or Claude, per the owner)", "",
              "Undeclared commits here are not human; the owner reports them as Gemini. Python, so not directly "
              "comparable with the C repos.", "",
              "| group | commits | median added lines | comment share | at Claude's size mix | chars per comment | "
              "prose | danger | debt |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for lab, g in (("declared Claude", cl), ("undeclared (Gemini, per owner)", un)):
            if not g:
                continue
            L.append(f"| {lab} | {len(g):,} | {np.median([c['added'] for c in g]):.0f} | {rate(g, 'c', 'added'):.1%} | "
                     f"{std_share(cl, g) if g is un else rate(g, 'c', 'added'):.1%} | {rate(g, 'c_chars', 'c'):.0f} | "
                     f"{rate(g, 'c_prose', 'c'):.0%} | {rate(g, 'c_danger', 'c'):.1%} | {rate(g, 'c_debt', 'c'):.1%} |")
        hum = [c for c in C if c["r"] in CONTROLS]
        L.append(f"| *human-written controls, pooled (C)* | {len(hum):,} | {np.median([c['added'] for c in hum]):.0f} | "
                 f"{rate(hum, 'c', 'added'):.1%} | | {rate(hum, 'c_chars', 'c'):.0f} | {rate(hum, 'c_prose', 'c'):.0%} | "
                 f"{rate(hum, 'c_danger', 'c'):.1%} | {rate(hum, 'c_debt', 'c'):.1%} |")
    L += ["", "· = fewer than 20 commits in the quarter. Comment share is computed over all commits in the quarter, "
          "AI and other.", "", f"Runtime {time.time() - T0:.0f}s."]
    (DOCS_DIR / "ai_comments_exploratory.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
