#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""ENV-H1..H3: platform-conditional density vs extrinsic fixes on unseen repos (docs/env_hypotheses.md).
Git only, no engine scan.

    python tools/env_eval.py walk  --repo harfbuzz --branch main --exts .c,.h,.cc,.hh,.cpp,.hpp
    python tools/xc_harvest.py     --repo harfbuzz --exts .c,.h,.cc,.hh,.cpp,.hpp
    python tools/env_eval.py score --repo harfbuzz --exts .c,.h,.cc,.hh,.cpp,.hpp
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent / "exploratory"))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from ea_eval import recall_at  # noqa: E402
from xc_envcond import PATTERNS  # noqa: E402  (registered: PATTERNS["P"] at 8a793c9, verbatim)

SEED, ITERS, DAY, WINDOW = 2982, 5000, 86400, 180
ALPHA, MIN_UNITS, EQUIV = 0.01 / 3, 20, 0.02


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def grep_counts(repo, sha, pat, exts):
    out = {}
    globs = [f"*{e}" for e in exts]
    for line in _git(repo, "-c", "core.quotepath=off", "grep", "-c", "-P", pat, sha, "--", *globs).splitlines():
        _, _, rest = line.partition(":")
        path, _, n = rest.rpartition(":")
        if n.isdigit():
            out[path] = int(n)
    return out


def walk(a):
    repo = POOL_DIR / a.repo
    head = _git(repo, "rev-parse", f"origin/{a.branch}").strip()
    head_ct = int(_git(repo, "show", "-s", "--format=%ct", head).strip())
    fp = [line.split() for line in _git(repo, "log", "--first-parent", "--format=%H %ct", head).splitlines()]
    fp = [(h, int(c)) for h, c in fp][::-1]  # oldest first
    first = dt.datetime.fromtimestamp(fp[0][1], dt.timezone.utc)
    q = dt.datetime(first.year, 3 * ((first.month - 1) // 3) + 1, 1, tzinfo=dt.timezone.utc)
    revs, i, started = [], 0, False
    while True:
        m = q.month + 3
        q = dt.datetime(q.year + (m - 1) // 12, (m - 1) % 12 + 1, 1, tzinfo=dt.timezone.utc)
        b = int(q.timestamp())
        if b + WINDOW * DAY >= head_ct:
            break
        while i + 1 < len(fp) and fp[i + 1][1] < b:
            i += 1
        sha = fp[i][0]
        if not started:
            n = sum(1 for p in _git(repo, "ls-tree", "-r", "--name-only", sha).splitlines() if p.endswith(tuple(a.exts.split(","))))
            if n < 50:
                continue
            started = True
        revs.append({"ref": f"pre-{q.date()}", "sha": sha, "boundary": q.isoformat(), "status": "ok"})
    out = {"repo": a.repo, "mode": "quarterly", "branch": f"origin/{a.branch}", "events_head": head,
           "outcome_days": WINDOW, "min_c_files": 50, "exts": a.exts, "revisions": revs}
    (REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").write_text(json.dumps(out, indent=1))
    print(a.repo, len(revs), "snapshots", revs[0]["ref"], "..", revs[-1]["ref"])


def score(a):
    t0 = time.time()
    repo = POOL_DIR / a.repo
    exts = tuple(a.exts.split(","))
    snaps = json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())["revisions"]
    for s in snaps:
        s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
    xc = json.loads((REPO_ROOT / "events" / f"{a.repo}_xc.json").read_text())
    events = xc["events"]
    classes = ("extrinsic", "regression", "other-fix")
    per = []
    for s in snaps:
        lines = grep_counts(repo, s["sha"], "", exts)
        if not lines:
            continue
        paths = sorted(lines)
        loc = np.array([float(lines[p]) for p in paths])
        pc = grep_counts(repo, s["sha"], PATTERNS["P"], exts)
        p_line = np.array([pc.get(p, 0) for p in paths], dtype=float) / np.maximum(loc, 1.0)
        pos = {k: set() for k in classes}
        for e in events:
            if e["class"] in pos and s["ct"] < e["ct"] <= s["ct"] + WINDOW * DAY:
                pos[e["class"]].update(e["c_files"])
        lift = {}
        for k in classes:
            y = np.array([1.0 if p in pos[k] else 0.0 for p in paths])
            if y.sum() == 0:
                continue
            base = max(recall_at(loc, loc, paths, y, 0.2), recall_at(-loc, loc, paths, y, 0.2))
            lift[k] = recall_at(p_line, loc, paths, y, 0.2) - base
        per.append({"ref": s["ref"], "lift": lift, "share_p": float(np.mean(p_line > 0))})

    def vec(f, *ks):
        return np.array([f(p) for p in per if all(k in p["lift"] for k in ks)])

    claims = {"ENV-H1": vec(lambda p: p["lift"]["extrinsic"], "extrinsic"),
              "ENV-H2": vec(lambda p: p["lift"]["extrinsic"] - p["lift"]["regression"], "extrinsic", "regression"),
              "ENV-H3": vec(lambda p: p["lift"]["extrinsic"] - p["lift"]["other-fix"], "extrinsic", "other-fix")}
    spawn = iter(np.random.SeedSequence(SEED).spawn(4))
    L = [f"# ENV-H1..H3 — platform-conditional density vs fix classes: {a.repo} (SCORED)", "",
         f"- labels `events/{a.repo}_xc.json` (rules v2, exts {a.exts}): " +
         ", ".join(f"{k} {xc['counts'].get(k, 0)}" for k in classes),
         f"- {len(per)} quarterly snapshots; files with any platform conditional: median "
         f"{np.median([p['share_p'] for p in per]):.1%}", "",
         "| claim | n | mean | lo (α=0.0033) | 90% CI | verdict |", "|---|---:|---:|---:|---|---|"]
    for c, x in claims.items():
        n = len(x)
        rng = np.random.default_rng(next(spawn))
        if n < MIN_UNITS:
            L.append(f"| **{c}** | {n} | {x.mean() if n else float('nan'):+.3f} | — | — | **not evaluable** |")
            continue
        b = np.array([x[rng.integers(0, n, n)].mean() for _ in range(ITERS)])
        lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
        v = ("SUPPORTED" if x.mean() > 0 and lo > 0 else
             "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        L.append(f"| **{c}** | {n} | {x.mean():+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | **{v}** |")
    L += ["", "Mean lift by class: " + ", ".join(
        f"{k} {np.mean([p['lift'][k] for p in per if k in p['lift']]):+.3f}" for k in classes),
          "", f"Runtime {time.time() - t0:.0f}s · bootstrap {ITERS} rounds over snapshots, seed {SEED}."]
    (DOCS_DIR / f"env_{a.repo}.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["walk", "score"])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", default="master")
    ap.add_argument("--exts", default=".c,.h")
    a = ap.parse_args()
    (walk if a.cmd == "walk" else score)(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
