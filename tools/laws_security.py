#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAW-9, security patches are local (docs/laws_hypotheses.md; methods review M6 item 6), from the fix-commit
records of tools/laws_osv.py.

Registered as **descriptive** (Amendment 0 item 2): it becomes confirmatory only if at least MIN_LANG_REPOS repos
per language are evaluable, a count this module reports (`confirmatory_gate`) and which is checked before any
LAW-9 statistic is read. The methods review expected 0 to 3 evaluable repos of 8 per language; the pilot found 3
of 8 (redis, libxml2, libgit2), so the registered descriptive reading stands.

Effect, per metric in METRICS (files touched, functions changed, non-test source lines changed):
  the **median difference CVE - other fix**, read as the Hodges-Lehmann shift: the median of all pairwise
  differences (cve_i - other_j). That is the two-sample "median difference" that goes with the rank test used for
  its p-value, and unlike the difference of two medians it is defined and stable on these small, heavily tied
  count distributions; `median_difference` reports the difference of medians beside it. SE and a percentile
  interval by a bootstrap of both classes (commits are the unit; a fix commit is in one class only).

  **What the pilot found about this estimator.** On libxml2 the shift is exactly 0.00 with SE 0.00 for files
  touched and functions changed, because those counts are tiny and heavily tied (median 1 file, 2 functions) and
  most pairwise differences are 0. The rank test on the same data is significant for files (p = 0.003), so the
  difference is real but smaller than one file -- and the registered conjunction "each < 0" can never fire on a
  shift that is pinned at 0. **Amendment 5 settled it: LAW-9's effect is `p_smaller`, against a null of 0.5, in
  the direction "CVE smaller".** It is the rank test's own effect size, it is never degenerate on tied counts, and
  it carries a bootstrap SE (`se_p_smaller`) so it can enter a variance-weighted pool -- which the shift could
  not, two of its three legs having SE exactly 0. The shift and the difference of medians stay in the record,
  descriptively.
  p one-sided Mann-Whitney (alternative "less": a CVE fix is smaller), tie-corrected.

The law holds for a repo when **all three** effects are negative with p < ALPHA. That conjunction is an
intersection-union test, so the law's p is the largest of the three and needs no multiplicity correction
(methods review, "Within-law conjunctions (LAW-5 'both', LAW-9 'each') are intersection-union tests").

Not evaluable: fewer than MIN_CVE advisory-labelled fix commits (the registration's "repos with >= 20 OSV-linked
fix commits") or fewer than MIN_OTHER other fix commits. The second is a computability guard, not a registered
bar: the shift of a class with a handful of commits has no usable interval.

Sensitivities. `capped` repeats the law over commits touching at most FILE_CAP unit source files, because the
prior work this replicates (xc_harvest.py's 50-file sweep cap) truncated the other-fix distribution that way;
the uncapped reading is the primary one. `by_signal` repeats it over the advisory-labelled commits whose signal is
a GIT `fixed` range alone, dropping the weaker commit-URL references.

The extension (CGT-3b, descriptive): call-edge rewiring rate, CVE against other fix, at matched size. `rewiring`
computes it when the records carry a `rewire` field and says so when they do not; nothing in the pilot produces
one, because it needs a call graph on both sides of each fix commit rather than a quarterly snapshot.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

SEED = 2982
BOOT = 1000
ALPHA = 0.05
MIN_CVE = 20
MIN_OTHER = 20
MIN_LANG_REPOS = 5
FILE_CAP = 50
METRICS = ("files", "functions", "lines")
SIZE_BINS = 4


def hodges_lehmann(a: np.ndarray, b: np.ndarray) -> float:
    """The median of all pairwise differences a_i - b_j."""
    if not len(a) or not len(b):
        return float("nan")
    return float(np.median(np.subtract.outer(np.asarray(a, float), np.asarray(b, float))))


def shift(cve: np.ndarray, other: np.ndarray, boot: int = BOOT, seed: int = SEED) -> dict:
    """The Hodges-Lehmann shift of one metric, with a bootstrap SE and interval and a one-sided rank p."""
    cve, other = np.asarray(cve, float), np.asarray(other, float)
    effect = hodges_lehmann(cve, other)
    mw = stats.mannwhitneyu(cve, other, alternative="less", method="asymptotic")
    rng = np.random.default_rng(seed)
    reps = np.empty(boot)
    reps_p = np.empty(boot)
    for i in range(boot):
        a = rng.choice(cve, len(cve), replace=True)
        b = rng.choice(other, len(other), replace=True)
        reps[i] = hodges_lehmann(a, b)
        # p_smaller needs an SE of its own: Amendment 5 makes it LAW-9's effect, so it has to enter a
        # variance-weighted pool, which the shift could not (its SE is exactly 0 on tied counts).
        reps_p[i] = 1 - stats.mannwhitneyu(a, b, alternative="less", method="asymptotic").statistic / (len(a) * len(b))
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return {"effect": effect, "se": float(np.std(reps, ddof=1)), "ci": [float(lo), float(hi)],
            "p": float(mw.pvalue), "u": float(mw.statistic), "boot": boot,
            # P(a random CVE fix is the smaller of a CVE/other pair), ties counted half: the rank test's own
            # effect size. Unlike the shift it is never degenerate on tied counts, so it says how big the
            # difference the p-value found actually is. 0.5 is no difference; above 0.5 is "CVE fixes smaller".
            "p_smaller": float(1 - mw.statistic / (len(cve) * len(other))),
            "se_p_smaller": float(np.std(reps_p, ddof=1)) if boot > 1 else float("nan"),
            "p_smaller_ci": [float(np.percentile(reps_p, 2.5)), float(np.percentile(reps_p, 97.5))],
            "median_cve": float(np.median(cve)), "median_other": float(np.median(other)),
            "median_difference": float(np.median(cve) - np.median(other)),
            "n_cve": int(len(cve)), "n_other": int(len(other))}


def evaluable(commits: list[dict]) -> str | None:
    n_cve = sum(bool(c["cve"]) for c in commits)
    n_other = len(commits) - n_cve
    if n_cve < MIN_CVE:
        return f"fewer than {MIN_CVE} advisory-labelled fix commits ({n_cve})"
    if n_other < MIN_OTHER:
        return f"fewer than {MIN_OTHER} other fix commits ({n_other})"
    return None


def _split(commits: list[dict], metric: str) -> tuple[np.ndarray, np.ndarray]:
    cve = np.array([c[metric] for c in commits if c["cve"]], dtype=float)
    other = np.array([c[metric] for c in commits if not c["cve"]], dtype=float)
    return cve, other


def _law(commits: list[dict], boot: int, seed: int) -> dict:
    out: dict = {"evaluable": False, "commits": len(commits),
                 "n_cve": sum(bool(c["cve"]) for c in commits), "metrics": {}}
    out["n_other"] = out["commits"] - out["n_cve"]
    if why := evaluable(commits):
        return {**out, "why": why}
    for metric in METRICS:
        out["metrics"][metric] = shift(*_split(commits, metric), boot=boot, seed=seed)
    ps = [out["metrics"][m]["p"] for m in METRICS]
    effects = [out["metrics"][m]["effect"] for m in METRICS]
    out["evaluable"] = True
    out["p"] = float(max(ps))  # intersection-union: the conjunction is as weak as its weakest part
    out["holds"] = bool(all(e < 0 for e in effects) and max(ps) < ALPHA)
    out["direction"] = "local" if all(e < 0 for e in effects) else (
        "mixed" if any(e < 0 for e in effects) else "not local")
    return out


def law9(commits: list[dict], boot: int = BOOT, seed: int = SEED) -> dict:
    """LAW-9 for one repo, with its two registered sensitivities."""
    out = _law(commits, boot, seed)
    if not out["evaluable"]:
        return out
    capped = [c for c in commits if c["files"] <= FILE_CAP]
    out["capped"] = _law(capped, boot, seed)
    out["capped"]["note"] = f"commits touching at most {FILE_CAP} unit source files, as in the prior work"
    primary = [c for c in commits if not c["cve"] or "git-range" in c.get("signals", ["git-range"])]
    out["by_signal"] = _law(primary, boot, seed)
    out["by_signal"]["note"] = "advisory labels from a GIT fixed range only, commit-URL references dropped"
    return out


def rewiring(commits: list[dict], boot: int = BOOT, seed: int = SEED, bins: int = SIZE_BINS) -> dict:
    """The CGT-3b extension, descriptive: call-edge rewiring rate CVE against other fix, within size strata
    (quantile bins of `lines`), pooled as the sample-size-weighted mean of the per-stratum shifts."""
    have = [c for c in commits if c.get("rewire") is not None]
    if len(have) < len(commits):
        return {"available": False, "why": f"{len(commits) - len(have)} of {len(commits)} fix commits carry no "
                                           "call-edge rewiring rate; it needs a call graph either side of the "
                                           "commit, which no pilot artefact holds"}
    if why := evaluable(have):
        return {"available": True, "evaluable": False, "why": why}
    lines = np.array([c["lines"] for c in have], dtype=float)
    edges = np.unique(np.quantile(lines, np.linspace(0, 1, bins + 1)))
    idx = np.clip(np.digitize(lines, edges[1:-1]), 0, len(edges) - 2)
    strata, weights = [], []
    for b in range(len(edges) - 1):
        sub = [c for c, k in zip(have, idx) if k == b]
        cve, other = _split(sub, "rewire")
        rec = {"bin": b, "lines_range": [float(edges[b]), float(edges[b + 1])], "n_cve": len(cve), "n_other": len(other)}
        if len(cve) and len(other):
            rec.update(shift(cve, other, boot=boot, seed=seed + b))
            weights.append(min(len(cve), len(other)))
        else:
            rec["why"] = "a stratum with only one class"
        strata.append(rec)
    if not strata or not weights:
        return {"available": True, "evaluable": False, "why": "no size stratum holds both classes"}
    w = np.array(weights, dtype=float)
    eff = np.array([s["effect"] for s in strata if "effect" in s], dtype=float)
    se = np.array([s["se"] for s in strata if "effect" in s], dtype=float)
    return {"available": True, "evaluable": True, "strata": strata, "bins": int(len(edges) - 1),
            "effect": float(np.sum(w * eff) / np.sum(w)),
            "se": float(np.sqrt(np.sum((w / np.sum(w)) ** 2 * se ** 2)))}


def confirmatory_gate(per_repo: dict[str, dict]) -> dict:
    """LAW-9 is confirmatory for a language only when at least MIN_LANG_REPOS of its repos are evaluable
    (registration, LAW-9). Reports the dropped repos and their CVE counts (methods review, not-evaluable
    dropout), so a descriptive verdict can be read with what it dropped."""
    kept = {r: v for r, v in per_repo.items() if v.get("evaluable")}
    dropped = {r: v.get("why", "not evaluable") for r, v in per_repo.items() if not v.get("evaluable")}
    return {"repos": len(per_repo), "evaluable": len(kept), "needed": MIN_LANG_REPOS,
            "class": "confirmatory" if len(kept) >= MIN_LANG_REPOS else "descriptive",
            "kept": sorted(kept), "dropped": dropped,
            "cve_fixes": {r: v.get("n_cve", 0) for r, v in sorted(per_repo.items())}}
