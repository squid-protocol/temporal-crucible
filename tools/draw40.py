#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Draw a 40-repo age x language panel from the corpus pool, to find the MODERATOR of the structural sign.

    python tools/draw40.py --out docs/draw40.json [--per-cell 10]

struct_null.py found call-graph centrality beating LOC in four repos and losing in four, all significant --
a pooled null that no repo exhibits. The obvious moderator candidates are AGE and LANGUAGE, and in those
eight they are perfectly confounded: all four anti-predictive repos are old C. This draws a balanced panel
so they can be separated.

Deterministic: same seed, same draw. Repos already assessed are excluded, so they stay an independent set.
"""
from __future__ import annotations

import argparse, collections, json, os, random, subprocess
from pathlib import Path

BASE = Path("/nvme-data/gitgalaxy-data")
DONE = {"commons-lang", "curl", "libgit2", "libxml2", "ndpi", "postgres",
        "prometheus", "redis", "ripgrep", "sphinx"}
EXT = {".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp", ".py": "python",
       ".java": "java", ".go": "go", ".rs": "rust", ".ts": "jsts", ".js": "jsts",
       ".cs": "csharp", ".php": "php", ".kt": "kotlin"}
OLD_BEFORE = 2006          # >= 20 years old at 2026
MIN_COMMITS = 2000


def probe(d: Path):
    g = ["git", "-C", str(d)]
    try:
        y = subprocess.run(g + ["log", "--reverse", "--format=%ad", "--date=format:%Y"],
                           capture_output=True, text=True, timeout=90).stdout.split("\n", 1)[0]
        n = subprocess.run(g + ["rev-list", "--count", "HEAD"], capture_output=True, text=True,
                           timeout=90).stdout.strip()
        if not (y.isdigit() and n.isdigit()) or int(n) < MIN_COMMITS:
            return None
        c = collections.Counter()
        for f in subprocess.run(g + ["ls-tree", "-r", "--name-only", "HEAD"], capture_output=True,
                                text=True, timeout=180).stdout.splitlines():
            e = os.path.splitext(f)[1]
            if e in EXT:
                c[EXT[e]] += 1
        if sum(c.values()) < 50:
            return None
        lang = c.most_common(1)[0][0]
        return {"repo": d.name, "year": int(y), "commits": int(n), "lang": lang,
                "age": "old" if int(y) < OLD_BEFORE else "young",
                "family": "C" if lang in ("c", "cpp") else "managed"}
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("docs/draw40.json"))
    ap.add_argument("--per-cell", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20261113)
    a = ap.parse_args()
    cand = []
    for d in sorted(BASE.iterdir()):
        if not (d / ".git").is_dir() or d.name in DONE:
            continue
        r = probe(d)
        if r:
            cand.append(r)
    cells = collections.defaultdict(list)
    for r in cand:
        cells[(r["age"], r["family"])].append(r)
    rnd = random.Random(a.seed)
    draw, short = [], []
    for k in (("old", "C"), ("young", "C"), ("old", "managed"), ("young", "managed")):
        pool = sorted(cells[k], key=lambda x: x["repo"])
        rnd.shuffle(pool)
        take = pool[:a.per_cell]
        draw += take
        print(f"  {k[0]:<6}{k[1]:<9} available {len(pool):>3}  drawn {len(take):>2}  "
              f"{', '.join(x['repo'] for x in take)}")
        if len(take) < a.per_cell:
            short.append(f"{k[0]}/{k[1]}: {len(take)} of {a.per_cell}")
    a.out.write_text(json.dumps({"seed": a.seed, "per_cell": a.per_cell, "old_before": OLD_BEFORE,
                                 "n": len(draw), "short": short, "draw": draw,
                                 "available": {f"{k[0]}/{k[1]}": len(v) for k, v in cells.items()}},
                                indent=1) + "\n")
    print(f"\n{len(draw)} repos -> {a.out}" + (f"   SHORT: {'; '.join(short)}" if short else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
