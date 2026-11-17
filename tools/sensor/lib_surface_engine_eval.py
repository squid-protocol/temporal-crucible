#!/usr/bin/env python3
"""Does the ENGINE's `gitgalaxy libsurface` (glob table, gitgalaxy/tools/sensors/library_table.py) reproduce the validated C numbers?

    ENGINE=/path/to/gitgalaxy/checkout python tools/sensor/lib_surface_engine_eval.py curl libarchive harfbuzz

Same 19 units, snapshots, outcome and metric as lib_surface_eval.py (the prototype with regex profiles); the sensor score here is the engine
module's density for the library at each snapshot's scan database. Prints the engine module against the prototype and the registered regexes."""
import collections
import json
import multiprocessing
import os
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, os.environ["ENGINE"])
import lib_eval as LE  # noqa: E402
import lib_surface as LS  # noqa: E402
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402
from sc_discover import recall20  # noqa: E402

from gitgalaxy.tools.sensors import libsurface as ES  # noqa: E402

DB = pathlib.Path("/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/libsurface")
LIBS = ES.load_libraries([])


def regex_task(a):
    repo, sha = a
    exts = LE.EXTS[repo]
    return sha, LE.grep_counts(POOL_DIR / repo, sha, "", exts), {d: LE.grep_counts(POOL_DIR / repo, sha, p, exts) for d, _, p in LE.DEPS[repo]}


def run(repo):
    walk = json.loads((REPO_ROOT / "walks" / f"{repo}_quarterly.json").read_text())
    snaps = [s for s in walk["revisions"] if s.get("status", "ok") == "ok"]
    for s in snaps:
        s["ct"] = int(LE._git(POOL_DIR / repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    work = LE.work_commits(repo)
    deps = [d for d, _, _ in LE.DEPS[repo]]
    with multiprocessing.get_context("fork").Pool(6) as p:
        rx = {sha: (ln, cp) for sha, ln, cp in p.imap_unordered(regex_task, [(repo, s["sha"]) for s in snaps])}
    per = collections.defaultdict(list)
    for i, s in enumerate(snaps):
        dbs = list((DB / repo).glob(f"{i:03d}_*.db"))
        if not dbs:
            continue
        lines, rcoup = rx[s["sha"]]
        if not lines:
            continue
        surface = ES.build(dbs[0], LIBS)
        paths = sorted(lines)
        loc = np.array([float(max(lines[p], 1)) for p in paths])
        pr = np.argsort(np.argsort(np.array(paths)))
        for d in deps:
            if d not in LS.LIBS:
                continue
            touched = set()
            for c in work[d]:
                if s["ct"] < c["ct"] <= s["ct"] + LE.WINDOW * LE.DAY:
                    touched.update(c["files"])
            y = np.array([1.0 if p in touched else 0.0 for p in paths])
            if y.sum() == 0:
                continue
            files = surface.libraries.get(d, {})
            eng = np.array([files[p].density if p in files else 0.0 for p in paths])
            cs = LS.coupling(dbs[0], d, LE.EXTS[repo])
            proto = np.array([cs.get(p, {}).get("density", 0.0) for p in paths])
            reg = np.array([rcoup[d].get(p, 0) for p in paths], dtype=float) / loc
            base = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
            per[d].append({"eng": recall20(eng, loc, pr, y), "proto": recall20(proto, loc, pr, y), "regex": recall20(reg, loc, pr, y), "base": base})
    return per


def main():
    rng = np.random.default_rng(2982)
    units = []
    print(f"{'repo':10s} {'library':9s} {'snaps':>5s} {'engine':>7s} {'proto':>7s} {'regex':>7s} {'size':>7s} {'eng-proto':>9s}")
    for repo in sys.argv[1:]:
        for d, v in run(repo).items():
            if len(v) < LE.MIN_SNAPS:
                continue
            m = lambda k: float(np.mean([x[k] for x in v]))  # noqa: E731
            units.append((repo, d, [x["eng"] - x["base"] for x in v], [x["eng"] - x["regex"] for x in v], [x["eng"] - x["proto"] for x in v]))
            print(f"{repo:10s} {d:9s} {len(v):5d} {m('eng'):7.3f} {m('proto'):7.3f} {m('regex'):7.3f} {m('base'):7.3f} {m('eng') - m('proto'):+9.3f}")
    for name, idx in (("engine - size (want > 0)", 2), ("engine - regex (non-inferior if lower bound > -0.05)", 3), ("engine - prototype (want ~ 0)", 4)):
        arrs = [np.array(u[idx]) for u in units]
        mean = float(np.mean([a.mean() for a in arrs]))
        b = np.array([np.mean([a[rng.integers(0, len(a), len(a))].mean() for a in arrs]) for _ in range(2000)])
        print(f"{name}: units {len(arrs)}, mean {mean:+.3f}, 99.7% lower bound {np.quantile(b, 0.0033):+.3f}, 90% CI [{np.quantile(b, .05):+.3f}, {np.quantile(b, .95):+.3f}]")


if __name__ == "__main__":
    main()
