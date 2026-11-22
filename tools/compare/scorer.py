#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The comparison scorer (docs/process/comparison_scorer_spec.md, section 4): tables in, predictors by
derive.py, and its own scoring loop, written by reading the reference (`stage_score`, `control_effects`,
`churn_any`, `summarize` of tools/sa3_score.py). Independence is not claimed for the loop: it is a second route
to the same numbers, transcribed from the code.

Its code and its public inputs come from the SEALED COPIES, a directory passed to it, never from the tree under
test: sealed/tools/sa3_stats.py (loaded by file, after its imports are checked: _util.load_sealed_stats),
sealed/docs/sa3_outcome_marginals.json, sealed/docs/sa3_placebo.json, and sealed/docs/sa3_lock.json for the
result's `sealed` key (absent: that key is null).

The order is also the order in which the one shared random stream (seed 2982) is consumed: repos (the marginals
rows with status ok, in the file's order); outcomes HP, HP_allreverts, HP_revert, HP_cve, HP_fixref, KW, each
only if its marginals row clears the floor; predictors in the declared order, primaries only for outcomes other
than HP and KW; a silent predictor or a design under the pair floor draws nothing; otherwise 200 block
permutations; after a repo's outcomes, if HP clears its floor, the matched control (draws first, checks after).

    res = Scorer(sealed, data).score()       # data: {repo: derive.derive(..., labels=...)}
    python3 tools/compare/scorer.py --tables PB --compare-tables CT --labels LT --sealed SC --out result.json

The loop's steps are methods (repo_order, outcome_order, on_silent, control_draw, finish_cell) so that the
stream tests can change one step in a subclass in the test file; nothing here switches a fault on. `stream` is
part 2's one hook (docs/process/comparison_scorer_part2_spec.md, section 3): the generator for one use of
randomness, by key; here it returns the one shared stream every time (tools/compare/streams.py overrides it).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if "tools_compare__util" not in sys.modules:
    import importlib.util as _iu
    _s = _iu.spec_from_file_location("tools_compare__util", str(HERE / "_util.py"))
    _m = _iu.module_from_spec(_s)
    sys.modules["tools_compare__util"] = _m
    _s.loader.exec_module(_m)
U = sys.modules["tools_compare__util"]
D = U.sibling("derive")

PREDICTORS = D.PREDICTORS
PRIMARIES = D.PRIMARIES
OUTCOMES = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")
CONFIRMATORY = ("struct_branch", "risk_safety_score", "amplified_cascading_flux")
NEW_LANGS = {"racket", "ghostty", "swift", "wrf-fortran", "fieldtrip", "rails", "bugzilla", "discourse",
             "tigerbeetle", "bun"}
POST_UNBLINDING = "PU_"
N_PERMS = N_DRAWS = 200
SEED = 2982
UNAVAILABLE = {"dampened_flux": "named as a D secondary in the registration; the pinned engine emits no such value"}
NOT_RUN = {"S5": "tree-wide commits left in", "S8": "positives followed through renames",
           "nest_*": "Racket not measured; see docs for parse-error rates"}
STATS = ("bauc", "residual", "minus_surrogate", "S4_replaces", "S6_sauc_minus", "S7_tight", "S9_logistic_z")


class Scorer:
    def __init__(self, sealed: Path, data: dict[str, dict]):
        self.sealed = Path(sealed)
        self.S = U.load_sealed_stats(self.sealed)
        self.marg = json.loads((self.sealed / "docs" / "sa3_outcome_marginals.json").read_text())
        self.plac = json.loads((self.sealed / "docs" / "sa3_placebo.json").read_text())
        lock = self.sealed / "docs" / "sa3_lock.json"
        self.lock_files = json.loads(lock.read_text())["files"] if lock.exists() else None
        self.data = data

    # ------------------------------------------------------------------------------- the steps a test may change
    def repo_order(self, rows: list[dict]) -> list[dict]:
        return rows

    def outcome_order(self, r: dict) -> tuple[str, ...]:
        return OUTCOMES

    def on_silent(self, d: dict, oc: str, p: str, x: np.ndarray, rng) -> None:
        """a silent predictor records "instrument silent" and draws nothing"""

    def control_draw(self, d: dict, rng, pool: list, hp: list, K: int):
        """one draw of the matched control: K pool commits by position without replacement, then, only if there
        are more primary-outcome commits than K, K of those; (yc, yh) or None to drop the draw"""
        yc = np.zeros(d["n"], int)
        for s in rng.choice(len(pool), K, replace=False):
            yc[d["pool"][pool[s]]] = 1
        yh = np.zeros(d["n"], int)
        for s in (rng.choice(len(hp), K, replace=False) if K < len(hp) else range(len(hp))):
            yh[d["hp_commits"][hp[s]]] = 1
        return yc, yh

    def finish_cell(self, repo: str, oc: str, p: str, c: dict) -> dict:
        return c

    def stream(self, key: tuple, rng):
        """the generator for one use of randomness: key ("perm", repo, outcome, predictor) for a cell's block
        permutations, ("control", repo) for a repo's matched control. Part 1: the shared stream, every time"""
        return rng

    # --------------------------------------------------------------------------------------- the reference's parts
    def design_for(self, d: dict, y, valid=None, caliper: float | None = None, k: int | None = None):
        S = self.S
        caliper = S.CALIPER if caliper is None else caliper
        if valid is None or valid.all():
            band, kk = (d["band"], d["k"]) if k is None else S.bands(d["loc"], d["paths"], k)
            return S.Design(d["loc"], y, band, kk, caliper), band, kk, np.arange(d["n"])
        idx = np.flatnonzero(valid)
        paths = [d["paths"][i] for i in idx]
        band, kk = S.bands(d["loc"][idx], paths, k)
        return S.Design(d["loc"][idx], y[idx], band, kk, caliper), band, kk, idx

    @staticmethod
    def summarize(vals: dict, level: float = 0.95) -> dict:
        v = np.array([x for x in vals.values() if x == x])
        if len(v) < 3:
            return {"n": len(v), "reading": "not fitted"}
        m, se = float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v)))
        tcrit = float(sps.t.ppf(1 - (1 - level) / 2, len(v) - 1))
        lo, hi = m - tcrit * se, m + tcrit * se
        p = float(2 * sps.t.sf(abs(m / se), len(v) - 1)) if se > 0 else 1.0
        return {"n": len(v), "mean": m, "se": se, "level": level, "ci": [lo, hi], "p": p,
                "positive": int((v > 0).sum()), "negative": int((v < 0).sum()),
                "reading": "supported" if lo > 0 else "contradicted" if hi < 0 else "not detected"}

    def control_effects(self, d: dict, preds: list[str], rng) -> dict:
        S = self.S
        hp, pool = list(d["hp_commits"]), list(d["pool"])
        K = min(len(hp), len(pool))
        if K < 5:                                          # skipped: draws nothing
            return {}
        diffs = {p: [] for p in preds}
        sub = {}
        for p in preds:
            v = np.flatnonzero(~np.isnan(d["x"][p]))
            sub[p] = None if len(v) == d["n"] else v
        for _ in range(N_DRAWS):
            drawn = self.control_draw(d, rng, pool, hp, K)
            if drawn is None:
                continue
            yc, yh = drawn
            if not (0 < yc.sum() < d["n"]) or not (0 < yh.sum() < d["n"]):    # after the stream was used
                continue
            dc, dh = S.Design(d["loc"], yc, d["band"], d["k"]), S.Design(d["loc"], yh, d["band"], d["k"])
            for p in preds:
                if sub[p] is None:
                    e = dh.effect(d["x"][p]) - dc.effect(d["x"][p])
                else:
                    v = sub[p]
                    pv = [d["paths"][i] for i in v]
                    band, k = S.bands(d["loc"][v], pv)
                    if not (0 < yc[v].sum() < len(v)) or not (0 < yh[v].sum() < len(v)):
                        continue
                    e = (S.Design(d["loc"][v], yh[v], band, k).effect(d["x"][p][v])
                         - S.Design(d["loc"][v], yc[v], band, k).effect(d["x"][p][v]))
                if e == e:
                    diffs[p].append(e)
        return {p: float(np.mean(v)) for p, v in diffs.items() if v}

    @staticmethod
    def churn_any(d: dict) -> np.ndarray:
        y = np.zeros(d["n"], int)
        for files in d["pool"].values():
            y[files] = 1
        return y

    # ------------------------------------------------------------------------------------------------ the loop
    def score(self) -> dict:
        S = self.S
        rows = [r for r in self.marg if r["status"] == "ok"]
        meta = {r["repo"]: r for r in rows}
        res = {"valid": self.plac["valid"], "unavailable": dict(UNAVAILABLE), "repos": {}, "tests": {},
               "sealed": self.lock_files, "engine": self.data[rows[0]["repo"]]["engine"],
               "not_run": dict(NOT_RUN)}
        eff: dict = {}
        rng = np.random.default_rng(SEED)
        for r in self.repo_order(rows):
            d = self.data[r["repo"]]
            rec = {"n": d["n"], "outcomes": {}}
            for oc in self.outcome_order(r):
                if not r[oc]["clears_floor"]:
                    continue
                y = d["y"][oc]
                cell = {}
                for p, (_inst, role, count) in PREDICTORS.items():
                    if oc not in ("HP", "KW") and role != "primary":
                        continue
                    x = d["x"][p]
                    valid = ~np.isnan(x)
                    g = self.stream(("perm", r["repo"], oc, p), rng)
                    if D.silent(x, p):
                        cell[p] = {"status": "instrument silent"}
                        self.on_silent(d, oc, p, x, g)
                        continue
                    des, band, k, idx = self.design_for(d, y, valid)
                    if not des.clears_pair_floor():
                        cell[p] = {"status": "under pair floor"}
                        continue
                    xv, lv, yv = x[idx], d["loc"][idx], y[idx]
                    pv = [d["paths"][i] for i in idx]
                    e = des.effect(xv)
                    null = np.array([des.effect(S.block_permute(xv, lv, pv, g)) for _ in range(N_PERMS)])
                    c = {"status": "ok", "bauc": e, "dropped_null": int((~valid).sum()),
                         "null_sd": float(null.std(ddof=1)), "nonzero_share": float((xv != 0).mean()),
                         "residual": S.residual_effect(xv, yv, band, k, [np.log(lv)]),
                         "perm_p": float((np.abs(null - null.mean()) >= abs(e - null.mean())).mean()),
                         "S4_replaces": S.auc_plain(xv, yv) - S.auc_plain(lv, yv),
                         "S6_sauc_minus": S.sauc_minus_loc(xv, lv, yv, band, k),
                         "S9_logistic_z": S.logistic_z(xv, np.log(lv), yv, band, k, count)}
                    if len(idx) >= 600:
                        d7, *_ = self.design_for(d, y, valid, caliper=1.25, k=20)
                        c["S7_tight"] = d7.effect(xv) if d7.clears_pair_floor() else None
                    if role == "primary" and oc == "HP":
                        c["ci95"] = S.boot_ci(des, xv, band, k, yv)
                        c["minus_surrogate"] = e - self.plac["repos"].get(r["repo"], {}).get(
                            "surrogate_mean", {}).get(p, 0.0)
                    c = self.finish_cell(r["repo"], oc, p, c)
                    cell[p] = c
                    for stat in STATS:
                        if c.get(stat) is not None:
                            eff.setdefault((oc, p, stat), {})[r["repo"]] = c[stat]
                rec["outcomes"][oc] = cell
            if r["HP"]["clears_floor"]:
                rec["specificity"] = self.control_effects(d, list(PREDICTORS), self.stream(("control", r["repo"]), rng))
                for p, v in rec["specificity"].items():
                    eff.setdefault(("HP", p, "minus_control"), {})[r["repo"]] = v
                ya = self.churn_any(d)
                if 30 <= ya.sum() <= d["n"] - 30:
                    da = S.Design(d["loc"], ya, d["band"], d["k"])
                    for p in PRIMARIES:
                        hp = rec["outcomes"].get("HP", {}).get(p, {})
                        if hp.get("status") == "ok" and not np.isnan(d["x"][p]).any():
                            eff.setdefault(("HP", p, "minus_churn_any"), {})[r["repo"]] = \
                                hp["bauc"] - da.effect(d["x"][p])
            res["repos"][r["repo"]] = rec
        self.aggregate(res, eff, meta)
        return res

    # ----------------------------------------------------------------------------------------- the aggregation
    def aggregate(self, res: dict, eff: dict, meta: dict) -> None:
        summarize = self.summarize

        def pick(key, keep):
            return {k: v for k, v in eff.get(key, {}).items() if keep(meta[k])}

        def drawn(m):
            return m["drawn"]

        first = {p: summarize(pick(("HP", p, "bauc"), drawn)) for p in CONFIRMATORY}
        order = sorted(CONFIRMATORY, key=lambda p: first[p].get("p", 1.0))
        still = True
        for rank, p in enumerate(order):                   # the Holm step and the readings, as coded
            level = 1 - 0.05 / (len(order) - rank)
            b = summarize(pick(("HP", p, "bauc"), drawn), level)
            co = summarize(pick(("HP", p, "residual"), drawn), level)
            sp = summarize(pick(("HP", p, "minus_control"), drawn))
            reading = b["reading"]
            if reading == "supported" and not still:
                reading = "not detected (Holm: an earlier test in the family failed)"
            if b["reading"] != "supported":
                still = False
            if reading == "supported" and co["reading"] != "supported":
                reading = "not robust to the statistic"
            elif reading == "supported":
                reading = "supported, defect-specific" if sp.get("reading") == "supported" else \
                    "supported, but tracks activity, not defects"
            if not res["valid"]:
                reading = "NO FINDING: the placebo gate failed"
            res["tests"][p] = {"holm_level": level, "bauc": b, "residual": co, "minus_control": sp, "reading": reading}
        a = summarize(pick(("HP", "in_degree", "bauc"), drawn))
        res["tests"]["in_degree"] = {"exploratory": True, "bauc": a,
                                     "residual": summarize(pick(("HP", "in_degree", "residual"), drawn)),
                                     "reading": {"supported": "positive", "contradicted": "negative"}.get(
                                         a["reading"], a["reading"])}
        res["side_counts"] = {}
        for p in PRIMARIES:
            above = below = across = 0
            for name, rec in res["repos"].items():
                c = rec["outcomes"].get("HP", {}).get(p, {})
                if c.get("status") != "ok" or not meta[name]["drawn"]:
                    continue
                if c["perm_p"] < 0.05:
                    above += c["bauc"] > 0
                    below += c["bauc"] < 0
                else:
                    across += 1
            vals = pick(("HP", p, "bauc"), drawn)
            pos, neg = sum(v > 0 for v in vals.values()), sum(v < 0 for v in vals.values())
            res["side_counts"][p] = {"above": int(above), "below": int(below), "across": int(across),
                                     "sign_test_p": float(sps.binomtest(pos, pos + neg, 0.5).pvalue)
                                     if pos + neg else None}
        res["random_effects"] = {}
        for p in PRIMARIES:
            vals = pick(("HP", p, "bauc"), drawn)
            v = np.array([res["repos"][k]["outcomes"]["HP"][p]["null_sd"] ** 2 for k in vals])
            e = np.array(list(vals.values()))
            if len(e) >= 3 and (v > 0).all():
                w = 1 / v
                q = float((w * (e - (w * e).sum() / w.sum()) ** 2).sum())
                tau2 = max(0.0, (q - (len(e) - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
                ws = 1 / (v + tau2)
                res["random_effects"][p] = {"mean": float((ws * e).sum() / ws.sum()), "se": float(ws.sum() ** -0.5),
                                            "tau": float(tau2 ** 0.5)}
        for p in CONFIRMATORY:
            allr = summarize(pick(("HP_allreverts", p, "bauc"), drawn), res["tests"][p]["holm_level"])
            res["tests"][p]["allreverts"] = allr
            if allr["reading"] == "supported" and not res["tests"][p]["reading"].startswith("supported"):
                res["tests"][p]["allreverts_reading"] = "tracks reverted changes, not fixes"
        cuts = {"all_drawn": drawn, "earlier_eight": lambda m: not m["drawn"],
                POST_UNBLINDING + "django_circuitpython_removed":
                    lambda m: m["drawn"] and m["repo"] not in ("django", "circuitpython"),
                POST_UNBLINDING + "mediawiki_freebsd_removed":
                    lambda m: m["drawn"] and m["repo"] not in ("mediawiki", "freebsd-src"),
                "S1_new_languages_removed": lambda m: m["drawn"] and m["repo"] not in NEW_LANGS,
                "S2_merge_workflow_removed": lambda m: m["drawn"] and not m["merge_units"],
                "S3_full_window": lambda m: m["drawn"] and m["window_days"] >= 730,
                "go_django_removed": lambda m: m["drawn"] and m["repo"] not in ("go", "django"),
                "C_family": lambda m: m["drawn"] and m["family"] == "C",
                "managed": lambda m: m["drawn"] and m["family"] != "C"}

        def summ(key, name, keep):
            vals = pick(key, keep)
            if name in ("C_family", "managed") and len(vals) < 5:
                return {"n": len(vals), "reading": "not fitted (fewer than five repos)"}
            return summarize(vals)

        res["summaries"] = {f"{oc}|{p}|{stat}|{name}": summ((oc, p, stat), name, keep)
                            for (oc, p, stat) in sorted(eff) for name, keep in cuts.items()
                            if name == "all_drawn" or (oc == "HP" and stat == "bauc")}


def load_data(pb: Path, ct: Path, lt: Path, sealed: Path, repos: list[str] | None = None) -> dict:
    """{repo: derived arrays with labels} for the marginals' ok rows, from the three table directories"""
    stats = U.load_sealed_stats(sealed)
    marg = json.loads((Path(sealed) / "docs" / "sa3_outcome_marginals.json").read_text())
    out = {}
    for r in marg:
        if r["status"] != "ok" or (repos and r["repo"] not in repos):
            continue
        a, b, c = D.load_dirs(Path(pb) / r["repo"], Path(ct) / r["repo"], Path(lt) / r["repo"])
        out[r["repo"]] = D.derive(r["repo"], a, b, stats, c)
    return out


def dumps(res: dict) -> str:
    """the result as the reference writes its own (indent 1, NaN as the bare token), with no default=: every
    value must already be a JSON type"""
    return json.dumps(res, indent=1) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", required=True)
    ap.add_argument("--compare-tables", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--sealed", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    SR = U.sandbox_ro()
    out = SR.check_rw(Path(a.out).parent) / Path(a.out).name
    data = load_data(Path(a.tables), Path(a.compare_tables), Path(a.labels), Path(a.sealed))
    out.write_text(dumps(Scorer(Path(a.sealed), data).score()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
