#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Quantitative bias analysis for HR-1: how much lift can the LABELLING PROCESS manufacture by itself?

    python tools/hr1_bias.py --repo curl --reps 400

HR-1 measures whether prior fixes order later fixes better than size does. Both sides are read off the SAME
noisy label (sensitivity ~0.41, specificity ~0.83 measured externally), so their errors are correlated by
construction: a file that attracts announcement-style commits is counted on both sides of the comparison.

So the question is not "is the label noisy" -- we know it is -- but **how big a lift does that noise produce
when the true effect is ZERO?** This simulates exactly that null and reports the distribution.

The generative model, stated plainly so it can be argued with:

  * TRUE fixes land on files with probability proportional to LOC^alpha -- size and nothing else. By
    construction there is **no real recidivism effect**: prior fixes carry no information about later ones
    beyond what size already carries.
  * Each file has an ANNOUNCEMENT PROPENSITY a_i, lognormal with spread tau, constant over time. It is the
    whole mechanism: some files, authors and subsystems say "fix" and some do not, and that habit persists
    across the cut.
  * A true fix is OBSERVED with probability sensitivity * a_i (capped at 1).
  * A non-fix commit is observed as a fix with probability (1 - specificity) * a_i -- the cosmetic churn that
    the recall audit found: lint, javadoc, formatting, concentrated in the same files.

Then HR-1 runs unchanged on the simulated observations. Any lift it reports is pure artefact. tau = 0 is the
non-differential case, where theory says the effect should attenuate and NOT invent a lift; tau > 0 is the
case our audits actually found.
"""
from __future__ import annotations

import argparse, json, math, random, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hist_replicate import auc, CUT_Q, WINDOW_DAYS  # noqa: E402

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")


def repo_frame(repo: str):
    """files alive at the cut with their LOC, plus how many commits touched each before/after."""
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{repo}.db'}?mode=ro", uri=True)
    cts = [r[0] for r in h.execute("select ct from commit_ where merge=0 and bot=0 order by ct")]
    cut = cts[int(len(cts) * CUT_Q)]
    end = cut + WINDOW_DAYS * 86400
    before: dict[str, int] = {}
    after: dict[str, int] = {}
    for path, ct in h.execute("select t.path, c.ct from touch t join commit_ c on c.sha=t.sha "
                              "where c.merge=0 and c.bot=0"):
        if ct < cut:
            before[path] = before.get(path, 0) + 1
        elif ct <= end:
            after[path] = after.get(path, 0) + 1
    h.close()
    w = sqlite3.connect(f"file:{STUDY/'dbs'/f'{repo}.db'}?mode=ro", uri=True)
    import datetime as dt
    best, sha = None, None
    for c, d in w.execute("select commit_hash, date from snap where rc=0"):
        try:
            e = dt.datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if best is None or abs(e - cut) < best:
            best, sha = abs(e - cut), c
    loc = {p: l for p, l in w.execute(
        "select path, total_loc from file where commit_hash=? and generated=0", (sha,)) if l}
    w.close()
    files = [p for p in loc if p in before or p in after]
    return [(p, float(loc[p]), before.get(p, 0), after.get(p, 0)) for p in files]


def estimate_tau(repo: str, min_commits: int = 15) -> tuple[float, int]:
    """Between-file spread of the labelled-fix RATE, with the binomial sampling part removed (delta method).

    Circular in the obvious way -- it is estimated from the same label whose error is being modelled -- and it
    sees FILE-level heterogeneity only. Author- and era-level variation adds to it, and that is where Bird et
    al. locate the bias, so the true spread is ABOVE this. Treat it as a lower bound."""
    import statistics as st
    h = sqlite3.connect(f"file:{STUDY/'history'/f'{repo}.db'}?mode=ro", uri=True)
    fix = {s for s, in h.execute("select sha from commit_ where fix=1 and merge=0 and bot=0")}
    tot: dict[str, int] = {}
    hit: dict[str, int] = {}
    for path, sha in h.execute("select t.path, t.sha from touch t join commit_ c on c.sha=t.sha "
                               "where c.merge=0 and c.bot=0"):
        tot[path] = tot.get(path, 0) + 1
        if sha in fix:
            hit[path] = hit.get(path, 0) + 1
    h.close()
    files = [p_ for p_ in tot if tot[p_] >= min_commits]
    if len(files) < 20:
        return float("nan"), len(files)
    denom = sum(tot[p_] for p_ in files)
    pbar = sum(hit.get(p_, 0) for p_ in files) / denom if denom else 0
    if not 0 < pbar < 1:
        return float("nan"), len(files)
    logs = [math.log((hit.get(p_, 0) + 0.5) / (tot[p_] + 1.0)) for p_ in files]
    samp = st.mean([(1 - pbar) / (pbar * tot[p_]) for p_ in files])
    return math.sqrt(max(0.0, st.pstdev(logs) ** 2 - samp)), len(files)


def simulate(frame, sens, spec, tau, alpha, rnd) -> float | None:
    """one replicate under the null; returns the lift HR-1 would report"""
    locs = [f[1] for f in frame]
    tot = sum(l ** alpha for l in locs) or 1.0
    obs_prior, obs_post, L = [], [], []
    for _p, loc, nb, na in frame:
        a = math.exp(rnd.gauss(0, tau)) if tau > 0 else 1.0
        pr_true = (loc ** alpha) / tot                      # TRUE fix rate: size only, no recidivism
        see_fix = min(1.0, sens * a)
        see_noise = min(1.0, (1.0 - spec) * a)
        # prior: each pre-cut commit is a true fix w.p. pr_true, observed w.p. see_fix; else noise
        k = 0
        for _ in range(min(nb, 400)):
            k += 1 if (rnd.random() < pr_true and rnd.random() < see_fix) else \
                 (1 if rnd.random() < see_noise else 0)
        obs_prior.append(k)
        # outcome: was any post-cut commit observed as a fix
        hit = 0
        for _ in range(min(na, 400)):
            if (rnd.random() < pr_true and rnd.random() < see_fix) or rnd.random() < see_noise:
                hit = 1
                break
        obs_post.append(hit)
        L.append(loc)
    if sum(obs_post) < 20:
        return None
    a1, a2 = auc(obs_prior, obs_post), auc(L, obs_post)
    return None if (a1 is None or a2 is None) else a1 - a2


def cmd_sweep(a) -> int:
    """Per repo: estimate tau from its own data, simulate the null there, compare to the observed lifts."""
    obs = {}
    for tag, f in (("raw", "docs/hr1.json"), ("v3c", "docs/hr1b.json")):
        p = Path(f)
        if p.exists():
            for r in json.loads(p.read_text())["repos"]:
                if r.get("evaluable") and r.get("lift") is not None:
                    obs.setdefault(r["repo"], {})[tag] = r["lift"]
    print(f"{'repo':14}{'tau':>7}{'files':>7}{'null med':>10}{'null p95':>10}"
          f"{'raw lift':>10}{'v3c lift':>10}  verdict (vs the null at its own tau)")
    for repo in a.sweep.split(","):
        try:
            tau, nf = estimate_tau(repo)
            frame = repo_frame(repo)
        except Exception as e:
            print(f"{repo:14} error: {e}"); continue
        if not frame or tau != tau:
            print(f"{repo:14} no usable frame"); continue
        rnd = random.Random(2982)
        vals = sorted(v for v in (simulate(frame, a.sens, a.spec, tau, a.alpha, rnd)
                                  for _ in range(a.reps)) if v is not None)
        if not vals:
            print(f"{repo:14}{tau:>7.2f}{nf:>7}  (no replicate reached the positives floor)"); continue
        med, p95 = vals[len(vals) // 2], vals[int(0.95 * len(vals)) - 1]
        o = obs.get(repo, {})
        fmt = lambda v: f"{v:+.4f}" if v is not None else "   --   "
        best = o.get("v3c", o.get("raw"))
        # A lift at or below zero is not evidence of a positive effect, whatever the null does -- the null
        # can sit well below zero (non-differential noise attenuates the predictor BELOW size), and "beats a
        # more-negative null" is not a finding.
        if best is None:
            verd = "-"
        elif best <= 0:
            verd = "no positive effect"
        elif best > p95:
            verd = "EXCEEDS null"
        else:
            verd = "inside null"
        print(f"{repo:14}{tau:>7.2f}{nf:>7}{med:>10.4f}{p95:>10.4f}"
              f"{fmt(o.get('raw')):>10}{fmt(o.get('v3c')):>10}  {verd}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="curl")
    ap.add_argument("--reps", type=int, default=400)
    ap.add_argument("--sens", type=float, default=0.41)
    ap.add_argument("--spec", type=float, default=0.83)
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--observed", type=float, help="the lift actually reported, for comparison")
    ap.add_argument("--taus", type=lambda s: tuple(float(x) for x in s.split(",")))
    ap.add_argument("--sweep", help="comma-separated repos: estimate tau per repo and test its observed lifts")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.sweep:
        return cmd_sweep(a)
    frame = repo_frame(a.repo)
    print(f"{a.repo}: {len(frame):,} files at the cut; null = fixes land by size alone (alpha={a.alpha}), "
          f"label sensitivity {a.sens}, specificity {a.spec}\n")
    print(f"{'tau (announcement spread)':28}{'median lift':>13}{'95th pct':>11}{'max':>9}  reading")
    res = {}
    for tau in (a.taus or (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)):
        rnd = random.Random(2982 + int(tau * 100))
        vals = [v for v in (simulate(frame, a.sens, a.spec, tau, a.alpha, rnd) for _ in range(a.reps))
                if v is not None]
        if not vals:
            print(f"{tau:<28}{'(no replicate produced enough positives)':>40}"); continue
        vals.sort()
        med = vals[len(vals) // 2]
        p95 = vals[int(0.95 * len(vals)) - 1]
        res[tau] = {"median": med, "p95": p95, "max": vals[-1], "n": len(vals)}
        note = ""
        if a.observed is not None:
            note = ("observed lift is INSIDE this null" if a.observed <= p95
                    else "observed lift exceeds the 95th pct")
        print(f"{tau:<28}{med:>13.4f}{p95:>11.4f}{vals[-1]:>9.4f}  {note}")
    if a.observed is not None:
        print(f"\nobserved HR-1 lift for {a.repo}: {a.observed:+.4f}")
    if a.out:
        a.out.write_text(json.dumps({"repo": a.repo, "sens": a.sens, "spec": a.spec,
                                     "alpha": a.alpha, "observed": a.observed, "grid": res}, indent=1) + "\n")
        print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
