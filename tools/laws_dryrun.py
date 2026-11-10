#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS Amendment 2 item 5: the development-set dry run of the three ACC-H3 statistics with the panel engine.

    python tools/laws_dryrun.py --study ACC_STUDY_DIR --engine-dir engine-<sha> --engine <sha> > laws_dryrun_result.json

A pre-draw check, not a gate: it reports, per ACC development repo, in-degree rho, top-1% hub Jaccard and
file-coupling kappa of the engine's resolved call graph against the ACC oracles, and changes no verdict.

It is ACC-2's scorer (tools/acc2_eval.py: same node set, matching, oracles and `compare`), ACC-3's Go oracle
(tools/acc3_eval.py), with two differences, both fixed by LAWS Amendment 1 item 1:
  - the scans are read from <study>/<engine-dir>/ (the panel engine), not <study>/engine/;
  - only CONFIDENT links are edges (the engine's own definition, CONFIDENT_STEPS below); ambiguous links are
    counted and reported, never used.
Not applied here: the LAWS M3 exclusions (tests, vendored, generated code). ACC-2's node set is used unchanged, so
these numbers are comparable with docs/acc2.md and docs/acc3_hypotheses.md, not with ACC-P.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import acc2_eval as B  # noqa: E402
import acc3_eval as C  # noqa: E402  (its import narrows B.REPOS to Go; REPOS below is this tool's own list)
import acc_eval as A  # noqa: E402

REPOS = {"libgit2": "c", "redis": "c", "commons-lang": "java", "commons-io": "java", "prometheus": "go", "sphinx": "python"}
# gitgalaxy core/call_resolver.py at the panel engine: RESOLUTION_OF_STEP values in CONFIDENT_RESOLUTIONS
CONFIDENT_STEPS = ("class", "qualified", "typed", "file", "import", "unique", "proximate")
BARS = {"indegree_spearman": 0.80, "hub_jaccard": 0.50, "coupling_kappa": 0.60}


def resolved(study: Path, engine_dir: str, repo: str, lang: str):
    """acc2_eval.resolved over <study>/<engine_dir>/<repo>, confident links only; also the link counts by step."""
    db = sorted((study / engine_dir / repo).glob("*_galaxy_master.db"))[0]
    root = str(study / "repos" / repo)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cls = dict(con.execute("SELECT id, class_name FROM class_data"))
    rows = {}
    for fid, path, name, start, loc, args, pc in con.execute(
            "SELECT f.id, fd.file_path, f.func_name, f.start_line, f.loc, f.args, f.parent_class_id FROM function_data f "
            "JOIN file_data fd ON f.file_id = fd.id"):
        p = str(path)
        if p.startswith(root):
            p = p[len(root):].lstrip("/")
        if not name or (loc or 0) < 3 or not p.endswith(A.EXT[lang]):
            continue
        argc = int(args) if args is not None and str(args).strip().lstrip("-").isdigit() else None
        rows[fid] = {"file": p, "name": str(name).split("::")[-1].split(".")[-1], "start": int(start or 0),
                     "cls": cls.get(pc), "argc": argc}
    edges, steps = set(), collections.Counter()
    for s, d, step in con.execute(
            "SELECT src_func_id, dst_func_id, step FROM fcall_data WHERE kind = 'call' AND dst_func_id IS NOT NULL"):
        if s in rows and d in rows and s != d:
            steps[step] += 1
            if step in CONFIDENT_STEPS:
                edges.add(((rows[s]["file"], s), (rows[d]["file"], d)))
    con.close()
    return rows, edges, steps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=Path, required=True)
    ap.add_argument("--engine-dir", required=True, help="scan directory under --study, e.g. engine-b873edc5b")
    ap.add_argument("--engine", required=True, help="the gitgalaxy commit of those scans (recorded in the output)")
    ap.add_argument("--repos", default=",".join(REPOS))
    a = ap.parse_args()
    s = a.study
    go_env = {**{k: v for k, v in os.environ.items() if k != "GOFLAGS"}, "GOPATH": str(s / "gopath"),
              "GOMODCACHE": str(s / "gopath/pkg/mod"), "GOTOOLCHAIN": "auto",
              "PATH": f"{s}/go/bin:{s}/gopath/bin:{os.environ['PATH']}"}
    oracles = {"c": A.oracle_c, "java": B.oracle_java, "python": B.oracle_python, "go": lambda st, r: C.go(st, r, go_env)}
    res = {"engine": a.engine, "engine_dir": a.engine_dir, "confident_steps": list(CONFIDENT_STEPS), "bars": BARS,
           "status": "descriptive pre-draw check (LAWS Amendment 2 item 5); not a gate", "repos": {}}
    for repo in a.repos.split(","):
        lang = REPOS[repo]
        rows, edges, steps = resolved(s, a.engine_dir, repo, lang)
        links = {"confident": sum(n for k, n in steps.items() if k in CONFIDENT_STEPS),
                 "ambiguous_not_used": sum(n for k, n in steps.items() if k not in CONFIDENT_STEPS),
                 "by_step": dict(steps.most_common())}
        try:
            orc = oracles[lang](s, repo)
        except Exception as e:  # an oracle that fails is "not evaluable", as in ACC-2
            res["repos"][repo] = {"language": lang, "evaluable": False, "links": links, "error": f"{type(e).__name__}: {e}"[:400]}
            print(f"{repo}: oracle failed: {e}", file=sys.stderr, flush=True)
            continue
        if not orc["direct"] and not orc["dynamic"]:
            res["repos"][repo] = {"language": lang, "evaluable": False, "links": links, "error": str(orc.get("err", ""))[:400]}
            continue
        m = B.matcher(rows, lang)
        mapped = {k: {(x, y) for x, y in ((m(p), m(q)) for p, q in orc[k]) if x and y} for k in ("direct", "dynamic")}
        nodes = {(r["file"], fid) for fid, r in rows.items()}
        cmp_ = A.compare(nodes, edges, {}, mapped, use_line=False)
        for verdict in ("H1", "H2", "H3"):  # ACC's verdict keys: this run registers none
            cmp_.pop(verdict, None)
        met = {k: (cmp_.get(k) is not None and cmp_[k] >= bar) for k, bar in BARS.items()}
        res["repos"][repo] = {"language": lang, "evaluable": True, "links": links, **cmp_, "bars_met": met,
                              "all_three_met": all(met.values())}
        print(f"{repo}: done", file=sys.stderr, flush=True)
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
