#!/usr/bin/env python3
"""Does the library-surface sensor rank where a library's work lands (LIB-H1 recipe) -- and is it as good as the registered regexes?
    python tools/sensor/lib_surface_eval.py REPO [REPO ...]       (scan DBs from libsurface_scan.sh; outcome and baselines from tools/lib_eval.py)
Per (repo, library) unit with >= 20 scanned snapshots that have library work: recall@20 of sensor coupling, of the regex coupling (git grep,
the registered measure) and of the stronger size order; paired differences, bootstrapped over snapshots. Exploratory."""
import sys, json, pathlib, multiprocessing, collections
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import lib_eval as LE, lib_surface as LS
from sc_discover import recall20
from _engine import REPO_ROOT, POOL_DIR
DB = pathlib.Path("/srv/storage_16tb/projects/curl_call_graph_evolution/turn_v2/libsurface")

def regex_task(a):
    repo, sha = a; exts = LE.EXTS[repo]; return sha, LE.grep_counts(POOL_DIR / repo, sha, "", exts), {d: LE.grep_counts(POOL_DIR / repo, sha, p, exts) for d, _, p in LE.DEPS[repo]}

def run(repo):
    walk = json.loads((REPO_ROOT / "walks" / f"{repo}_quarterly.json").read_text()); snaps = [s for s in walk["revisions"] if s.get("status", "ok") == "ok"]
    for s in snaps: s["ct"] = int(LE._git(POOL_DIR / repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    work = LE.work_commits(repo); deps = [d for d, _, _ in LE.DEPS[repo]]
    with multiprocessing.get_context("fork").Pool(6) as p: rx = {sha: (ln, cp) for sha, ln, cp in p.imap_unordered(regex_task, [(repo, s["sha"]) for s in snaps])}
    per = collections.defaultdict(list)
    for i, s in enumerate(snaps):
        dbs = list((DB / repo).glob(f"{i:03d}_*.db"))
        if not dbs: continue
        lines, rcoup = rx[s["sha"]]
        if not lines: continue
        paths = sorted(lines); loc = np.array([float(max(lines[p], 1)) for p in paths]); pr = np.argsort(np.argsort(np.array(paths)))
        for d in deps:
            if d not in LS.LIBS: continue
            touched = set()
            for c in work[d]:
                if s["ct"] < c["ct"] <= s["ct"] + LE.WINDOW * LE.DAY: touched.update(c["files"])
            y = np.array([1.0 if p in touched else 0.0 for p in paths])
            if y.sum() == 0: continue
            cs = LS.coupling(dbs[0], d, LE.EXTS[repo]); sens = np.array([cs.get(p, {}).get("density", 0.0) for p in paths])
            cl = LS.coupling_learned(dbs[0], d, LE.EXTS[repo]); learned = np.array([cl.get(p, {}).get("density", 0.0) for p in paths])
            inc = np.array([len(cs.get(p, {}).get("includes", ())) / loc[k] for k, p in enumerate(paths)])  # header includes only: no hand-written API-name list
            reg = np.array([rcoup[d].get(p, 0) for p in paths], dtype=float) / loc
            base = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
            per[d].append({"sensor": recall20(sens, loc, pr, y), "regex": recall20(reg, loc, pr, y), "inc": recall20(inc, loc, pr, y), "learned": recall20(learned, loc, pr, y), "base": base, "pos": int(y.sum()), "found": int((sens > 0).sum())})
    return per

def main():
    rng = np.random.default_rng(2982); allu = []
    print(f"{'repo':10s} {'library':9s} {'snaps':>5s} {'listed':>7s} {'inc-only':>8s} {'learned':>8s} {'regex':>7s} {'size':>7s} {'learn-size':>10s} {'learn-listed':>12s}")
    for repo in sys.argv[1:]:
        for d, v in run(repo).items():
            if len(v) < LE.MIN_SNAPS: continue
            m = lambda k: float(np.mean([x[k] for x in v])); allu.append((repo, d, [x["sensor"] - x["base"] for x in v], [x["sensor"] - x["regex"] for x in v], [x["inc"] - x["base"] for x in v], [x["inc"] - x["sensor"] for x in v], [x["learned"] - x["base"] for x in v], [x["learned"] - x["sensor"] for x in v]))
            print(f"{repo:10s} {d:9s} {len(v):5d} {m('sensor'):7.3f} {m('inc'):8.3f} {m('learned'):8.3f} {m('regex'):7.3f} {m('base'):7.3f} {m('learned')-m('base'):+10.3f} {m('learned')-m('sensor'):+12.3f}")
    for name, idx, margin in (("sensor - size (want > 0)", 2, 0.0), ("sensor - regex (non-inferior if lower CI > -0.05)", 3, -0.05), ("includes-only - size (want > 0)", 4, 0.0), ("includes-only - full sensor (non-inferior if lower CI > -0.05)", 5, -0.05), ("LEARNED names - size (want > 0)", 6, 0.0), ("LEARNED names - listed names (non-inferior if lower CI > -0.05)", 7, -0.05)):
        arrs = [np.array(u[idx]) for u in allu]
        if not arrs: continue
        mean = float(np.mean([a.mean() for a in arrs])); b = np.array([np.mean([a[rng.integers(0, len(a), len(a))].mean() for a in arrs]) for _ in range(2000)])
        print(f"{name}: units {len(arrs)}, mean {mean:+.3f}, 99.7% lower bound {np.quantile(b, 0.0033):+.3f}, 90% CI [{np.quantile(b, .05):+.3f}, {np.quantile(b, .95):+.3f}]")
if __name__ == "__main__": main()
