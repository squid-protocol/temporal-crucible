#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""COM-H3 instrument check (EXPLORATORY): the engine's C-family `dead_code` rule (state_graveyard) over the whole
fix-event panel, before and after gitgalaxy#8255. Wave A's audit (docs/comment_wave_a.md, COM-E3) covered one curl
snapshot; this one covers every C/C++ file in every fix event's parent commit (chg_eval.fix_events, 5 repos).

No fix class is read: events only supply which file versions to scan, and nothing is broken down by class, so
COM-H3 stays unscored. Three steps (engine on PYTHONPATH):

    python tools/dead_code_panel.py matches --tag fixed --out <scratch>/fixed.json      # engine with #8255
    python tools/dead_code_panel.py matches --tag old   --out <scratch>/old.json        # engine before #8255
    python tools/dead_code_panel.py sample  --matches <scratch>/fixed.json --out docs/dead_code_panel_sheet.tsv
    # judge every row by hand (label column), then:
    python tools/dead_code_panel.py report  --sheet docs/dead_code_panel_sheet.tsv --matches <scratch>/fixed.json \\
        --old <scratch>/old.json                                                        # -> docs/dead_code_panel.md

Labels: `code` (a commented-out statement, declaration or control line), `proto` (a commented-out prototype or
declaration note; counts as dead code by Wave A's definition), `annotation` (code text used as a label: an
end-of-block `} /* if(x) */` or an `else /* if(x) */`), `example` (code shown on purpose inside a doc or usage
comment), `prose` (natural language that only looks like code).
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import multiprocessing
import pathlib
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, REPOS, _git, fix_events  # noqa: E402

SEED = 2982
EXCL = ("tests/", "test/", "docs/", ".github/", "scripts/", "fuzz/")
LABELS = ("code", "proto", "annotation", "example", "prose")
_W = {}


def _rules():
    if not _W:
        from gitgalaxy.core.prism import Prism
        from gitgalaxy.standards.gitgalaxy_config import LEXICAL_FAMILY_HEURISTICS
        from gitgalaxy.standards.language_standards import LANGUAGE_DEFINITIONS as LD
        _W["prism"] = Prism(LEXICAL_FAMILY_HEURISTICS, LD)
        _W["dead"] = {lg: LD[lg]["rules"]["dead_code"] for lg in ("c", "cpp")}
    return _W


def lang(r, path):
    return "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"


def blobs_task(t):
    """Blob ids of the C/C++ files an event touched, at its parent commit."""
    r, sha = t
    repo = POOL_DIR / r
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return []
    paths = [p for p in _git(repo, "diff", "--name-only", "--no-renames", parent, sha).splitlines()
             if p.endswith(CEXT + CPPEXT) and not p.startswith(EXCL)]
    if not paths:
        return []
    out = []
    for ln in _git(repo, "ls-tree", parent, "--", *paths).splitlines():
        meta, path = ln.split("\t", 1)
        out.append((r, path, meta.split()[2]))
    return out


def scan_task(t):
    r, path, blob = t
    W = _rules()
    raw = _git(POOL_DIR / r, "cat-file", "-p", blob, text=False)
    if not raw:
        return r, path, blob, None
    text = raw.decode("utf-8", "replace")
    lg = lang(r, path)
    try:
        pos = W["prism"].split_positional_comment_stream(text, lg)
    except Exception:
        return r, path, blob, None
    nl = [m.start() for m in re.finditer("\n", pos)]
    lines = text.split("\n")
    hits = []
    for m in W["dead"][lg].finditer(pos):
        i = bisect.bisect_left(nl, m.start())  # 0-based line
        seg = pos[m.start():].split("\n", 1)[0].strip()
        ctx = "\n".join(lines[max(i - 2, 0):i + 3])
        hits.append((i + 1, seg[:160], ctx[:600]))
    return r, path, blob, hits


def cmd_matches(a):
    t0 = time.time()
    ev = []
    for r in REPOS:
        e, _ = fix_events(r)
        ev += [(r, x[1]) for x in e]
    with multiprocessing.get_context("fork").Pool(8) as p:
        files = {x for xs in p.imap_unordered(blobs_task, ev, chunksize=16) for x in xs}
    by_blob = {}
    for r, path, blob in sorted(files):
        by_blob.setdefault((r, blob), (r, path, blob))  # identical content is scanned once
    print(f"events {len(ev):,}; file versions {len(files):,}; distinct blobs {len(by_blob):,} "
          f"({time.time() - t0:.0f}s)", flush=True)
    res, failed = [], 0
    with multiprocessing.get_context("fork").Pool(8) as p:
        for r, path, blob, hits in p.imap_unordered(scan_task, list(by_blob.values()), chunksize=8):
            if hits is None:
                failed += 1
                continue
            for line, seg, ctx in hits:
                res.append({"repo": r, "path": path, "blob": blob, "line": line, "text": seg, "ctx": ctx})
    blobs_per_repo = Counter(r for r, _ in by_blob)
    out = {"tag": a.tag, "events": len(ev), "blobs": dict(blobs_per_repo), "failed": failed, "matches": res}
    pathlib.Path(a.out).write_text(json.dumps(out))
    print(f"{a.tag}: matches {len(res):,} in {len({(m['repo'], m['blob']) for m in res}):,} blobs; "
          f"distinct comments {len(distinct(res)):,}; failed {failed} ({time.time() - t0:.0f}s)")
    return 0


def distinct(ms):
    """One row per distinct (repo, path, comment text): the same comment in many versions of a file counts once."""
    d = {}
    for m in sorted(ms, key=lambda m: (m["repo"], m["path"], m["text"], m["blob"])):
        d.setdefault((m["repo"], m["path"], m["text"]), m)
    return d


def cmd_sample(a):
    D = distinct(json.loads(pathlib.Path(a.matches).read_text())["matches"])
    rng = np.random.default_rng(SEED)
    rows = []
    for r in REPOS:
        keys = sorted(k for k in D if k[0] == r)
        pick = sorted(rng.choice(len(keys), size=min(a.n_per_repo, len(keys)), replace=False)) if keys else []
        for j in pick:
            m = D[keys[j]]
            rows.append([f"{r}-{len(rows):03d}", r, m["path"], m["line"], m["text"], m["ctx"].replace("\t", " "), ""])
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["id", "repo", "path", "line", "match", "context", "label"])
        w.writerows(rows)
    print(f"sample: {len(rows)} rows -> {a.out}")
    return 0


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def cmd_report(a):
    rows = list(csv.DictReader(open(a.sheet), delimiter="\t"))
    bad = [r["id"] for r in rows if r["label"] not in LABELS]
    if bad:
        raise SystemExit(f"unlabelled or bad labels: {bad[:10]}")
    new = json.loads(pathlib.Path(a.matches).read_text())
    old = json.loads(pathlib.Path(a.old).read_text())
    Dn, Do = distinct(new["matches"]), distinct(old["matches"])
    L = ["# COM-H3 instrument check: `dead_code` over the fix-event panel (EXPLORATORY)", "",
         "**Status: exploratory, instrument check, no hypothesis.** Wave A (`docs/comment_wave_a.md`, COM-E3) found the "
         "C-family `dead_code` rule (`state_graveyard`) about 4% precise on one curl snapshot; gitgalaxy#8255 gave its "
         "keyword arm a code shape. This re-measures it over every C/C++ file version touched by a fix event "
         "(`chg_eval.fix_events`, parent commit; tests/docs/fuzz/scripts excluded) in "
         + ", ".join(REPOS) + ". No fix class is read or reported. Script: `tools/dead_code_panel.py`.", "",
         f"- events {new['events']:,}; distinct file blobs scanned {sum(new['blobs'].values()):,}; "
         f"scan failures {new['failed']}", "",
         "## Matches before and after #8255", "",
         "| repo | blobs | matches (old rule) | matches (fixed rule) | distinct comments (old) | distinct (fixed) |",
         "|---|---:|---:|---:|---:|---:|"]
    for r in REPOS:
        L.append(f"| {r} | {new['blobs'].get(r, 0):,} | {sum(1 for m in old['matches'] if m['repo'] == r):,} | "
                 f"{sum(1 for m in new['matches'] if m['repo'] == r):,} | {sum(1 for k in Do if k[0] == r):,} | "
                 f"{sum(1 for k in Dn if k[0] == r):,} |")
    L += [f"| all | {sum(new['blobs'].values()):,} | {len(old['matches']):,} | {len(new['matches']):,} | "
          f"{len(Do):,} | {len(Dn):,} |", "",
          "A distinct comment is one (repo, file path, comment text); the same comment in many versions of a file "
          "counts once. Precision is estimated over distinct comments.", "",
          f"## Precision of the fixed rule (hand-judged random sample, seed {SEED})", "",
          "| repo | judged | code | proto | annotation | example | prose | dead-code precision (code + proto) [95% Wilson] | "
          "strict (code only) |", "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    tot, wsum, wstrict, W = Counter(), 0.0, 0.0, 0
    for r in REPOS:
        rr = [x for x in rows if x["repo"] == r]
        c = Counter(x["label"] for x in rr)
        n = len(rr)
        tot.update(c)
        if not n:
            L.append(f"| {r} | 0 | | | | | | n/a | n/a |")
            continue
        k, ks = c["code"] + c["proto"], c["code"]
        lo, hi = wilson(k, n)
        L.append(f"| {r} | {n} | {c['code']} | {c['proto']} | {c['annotation']} | {c['example']} | {c['prose']} | "
                 f"**{k / n:.0%}** [{lo:.0%}, {hi:.0%}] | {ks / n:.0%} |")
        nd = sum(1 for key in Dn if key[0] == r)
        wsum += nd * k / n
        wstrict += nd * ks / n
        W += nd
    n = sum(tot.values())
    k = tot["code"] + tot["proto"]
    lo, hi = wilson(k, n)
    L += [f"| pooled sample | {n} | {tot['code']} | {tot['proto']} | {tot['annotation']} | {tot['example']} | {tot['prose']} | "
          f"**{k / n:.0%}** [{lo:.0%}, {hi:.0%}] | {tot['code'] / n:.0%} |", "",
          f"- Panel-wide estimate (each repo's precision weighted by its distinct fixed-rule comments): "
          f"**{wsum / W:.0%}** dead-code, {wstrict / W:.0%} strict.",
          "- Labels: `code` commented-out statement / declaration / control line; `proto` commented-out prototype or "
          "declaration note (dead code by Wave A's definition); `annotation` code text used as an end-of-block or "
          "else-branch label; `example` code shown on purpose in a doc or usage comment; `prose` natural language. The labelled sheet is `docs/dead_code_panel_sheet.tsv`.", "",
          "## Fixed-rule matches judged not dead code", ""]
    for x in [x for x in rows if x["label"] in ("annotation", "prose", "example")][:20]:
        L.append(f"- {x['repo']} `{x['path']}`:{x['line']} ({x['label']}): `{x['match'][:90]}`")
    if a.notes:
        L += ["", "## Reading", "", pathlib.Path(a.notes).read_text().strip()]
    (DOCS_DIR / "dead_code_panel.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("matches")
    m.add_argument("--tag", required=True)
    m.add_argument("--out", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--matches", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--n-per-repo", type=int, default=40)
    r = sub.add_parser("report")
    r.add_argument("--sheet", required=True)
    r.add_argument("--matches", required=True)
    r.add_argument("--old", required=True)
    r.add_argument("--notes")
    a = ap.parse_args()
    return {"matches": cmd_matches, "sample": cmd_sample, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
