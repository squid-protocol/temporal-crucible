#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SA3 scorer (docs/sa3_registration.md, Amendments 1-3). Two stages, and the second is locked.

    python tools/sa3_score.py placebo     # gates + power. Scores NO real predictor against any outcome.
    python tools/sa3_score.py score       # the registered tests. Refuses to run until the three markers exist.

`placebo` runs the path-hash and directory-hash placebos and the block-permutation placebo (the real predictor's
values shuffled among size-adjacent files; only shuffled values are ever scored), checks they centre on zero, and
states the smallest detectable effect. It writes docs/sa3_placebo.json.

`score` needs, committed in docs/: sa3_power.md (the power amendment), sa3ch_frozen.md (SA3-CH Amendment 1 rule 8:
everything for the change study is built and reviewed first) and sa3_code_review.md (checklist item 15b).
"""
from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sa3_stats as S  # noqa: E402
from mod1_lift import frame, ro, STUDY  # noqa: E402
from sa3_outcomes import universe, SCANS, OUT as OUTCOMES  # noqa: E402

DOCS = Path("docs")
MARKERS = ("sa3_power.md", "sa3ch_frozen.md", "sa3_code_review.md")
NESTING = STUDY / "sa3_nesting"
NEW_LANGS = {"racket", "ghostty", "swift", "wrf-fortran", "fieldtrip", "rails", "bugzilla", "discourse",
             "tigerbeetle", "bun"}                      # MOD-1 Amendment 1: language first measured 2026-11-13
N_SALTS = N_PERMS = N_DRAWS = 200
SEED = 2982

# name -> (instrument, role, is a count)      role: primary | secondary
PREDICTORS = {
    "in_degree": ("A", "primary", True), "in_degree_per_loc": ("A", "secondary", False),
    "out_degree": ("A", "secondary", True), "pagerank_score": ("A", "secondary", False),
    "betweenness_score": ("A", "secondary", False),
    "struct_branch": ("B", "primary", True), "struct_branch_per_loc": ("B", "secondary", False),
    "state_danger": ("B", "secondary", True), "state_pointers_alloc": ("B", "secondary", True),
    "def_safety": ("B", "secondary", True), "state_flux": ("B", "secondary", True),
    "nest_max": ("B", "secondary", True), "nest_mean": ("B", "secondary", False),
    "risk_safety_score": ("C", "primary", False), "risk_tech_debt": ("C", "secondary", False),
    "risk_cognitive_load": ("C", "secondary", False), "risk_state_flux": ("C", "secondary", False),
    "risk_concurrency": ("C", "secondary", False), "risk_safety_nonzero": ("C", "secondary", False),
    "risk_safety_among_nonzero": ("C", "secondary", False),
    "amplified_cascading_flux": ("D", "primary", True), "amplified_cascading_flux_per_loc": ("D", "secondary", False),
    "state_heat_triggers": ("D", "secondary", True),
}
PRIMARIES = [k for k, v in PREDICTORS.items() if v[1] == "primary"]
CONFIRMATORY = ("struct_branch", "risk_safety_score", "amplified_cascading_flux")   # B, C, D; A is exploratory
UNAVAILABLE = {"dampened_flux": "named as a D secondary in the registration; the pinned engine emits no such value"}
COLS = ("total_loc", "coding_loc", "pagerank_score", "betweenness_score", "struct_branch", "state_danger",
        "state_pointers", "state_memory_alloc", "def_safety", "state_flux", "state_heat_triggers",
        "risk_safety_score", "risk_tech_debt", "risk_cognitive_load", "risk_state_flux", "risk_concurrency",
        "mitigation_telemetry")


def scored_repos() -> list[dict]:
    return [r for r in json.loads((DOCS / "sa3_outcome_marginals.json").read_text()) if r["status"] == "ok"]


def load(repo: str, with_predictors: bool) -> dict:
    """the universe, its size, the outcomes -- and, only when asked, the structural predictors"""
    f = frame(repo)
    files, _ = universe(repo, f["langs"])
    paths = sorted(files)
    ix = {p: i for i, p in enumerate(paths)}
    n = len(paths)
    side = json.loads((SCANS / f"{repo}.json").read_text())
    root = side["src_root"].rstrip("/") + "/"
    w = ro(SCANS / f"{repo}_master.db")
    raw = {c: np.full(n, np.nan) for c in COLS[:-1]}
    acf = np.full(n, np.nan)
    fid_of = {}
    for row in w.execute(f"select id, file_path, {', '.join(COLS)} from file_data"):
        p = row[1][len(root):] if row[1].startswith(root) else row[1].lstrip("/")
        i = ix.get(p)
        if i is None:
            continue
        fid_of[row[0]] = i
        for c, v in zip(COLS[:-1], row[2:-1]):
            if v is not None:
                raw[c][i] = float(v)
        try:
            acf[i] = float((json.loads(row[-1]) if row[-1] else {}).get("amplified_cascading_flux", 0) or 0)
        except (ValueError, TypeError):
            pass
    loc = raw["total_loc"]
    assert not np.isnan(loc).any() and (loc > 0).all(), f"{repo}: a ranked file has no LOC"
    d = {"repo": repo, "paths": paths, "loc": loc, "lg": np.log(loc), "frame": f, "n": n}
    d["band"], d["k"] = S.bands(loc, paths)
    o = json.loads((OUTCOMES / f"{repo}.json").read_text())["outcomes"]

    def yvec(fl):
        y = np.zeros(n, int)
        bad = [p for p in fl if p not in ix]
        assert not bad, f"{repo}: {len(bad)} outcome files are not unit files of the universe"   # the assertion
        y[[ix[p] for p in fl]] = 1
        return y

    d["y"] = {k: yvec(o[k]["files"]) for k in ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")}
    d["hp_commits"] = {s: [ix[p] for p in v] for s, v in o["HP"]["commits"].items()}
    d["pool"] = {s: [ix[p] for p in v] for s, v in o["control_pool"]["commits"].items()}
    if not with_predictors:
        w.close()
        return d
    indeg, outdeg = np.zeros(n), np.zeros(n)
    for sf, df in w.execute("select src_file_id, dst_file_id from fcall_data where dst_func_id is not null"):
        if df in fid_of:
            indeg[fid_of[df]] += 1
        if sf in fid_of:
            outdeg[fid_of[sf]] += 1
    w.close()
    x = {"in_degree": indeg, "in_degree_per_loc": indeg / loc, "out_degree": outdeg,
         "pagerank_score": raw["pagerank_score"], "betweenness_score": raw["betweenness_score"],
         "struct_branch": raw["struct_branch"], "struct_branch_per_loc": raw["struct_branch"] / loc,
         "state_danger": raw["state_danger"], "state_pointers_alloc": raw["state_pointers"] + raw["state_memory_alloc"],
         "def_safety": raw["def_safety"], "state_flux": raw["state_flux"],
         "risk_safety_score": raw["risk_safety_score"], "risk_tech_debt": raw["risk_tech_debt"],
         "risk_cognitive_load": raw["risk_cognitive_load"], "risk_state_flux": raw["risk_state_flux"],
         "risk_concurrency": raw["risk_concurrency"],
         "risk_safety_nonzero": np.where(np.isnan(raw["risk_safety_score"]), np.nan, (raw["risk_safety_score"] > 0) * 1.0),
         "risk_safety_among_nonzero": np.where(raw["risk_safety_score"] > 0, raw["risk_safety_score"], np.nan),
         "amplified_cascading_flux": acf, "amplified_cascading_flux_per_loc": acf / loc,
         "state_heat_triggers": raw["state_heat_triggers"]}
    nest = NESTING / f"{repo}.json"
    nm, nn = np.full(n, np.nan), np.full(n, np.nan)
    if nest.exists():
        for p, (a, b) in json.loads(nest.read_text())["files"].items():
            if p in ix:
                nm[ix[p]], nn[ix[p]] = a, b
    x["nest_max"], x["nest_mean"] = nm, nn
    d["x"] = x
    return d


def hash_placebo(paths: list[str], salt: int, by_dir: bool) -> np.ndarray:
    key = (lambda p: p.rsplit("/", 1)[0] if "/" in p else "") if by_dir else (lambda p: p)
    return np.array([int(hashlib.sha1(f"{salt}:{key(p)}".encode()).hexdigest()[:12], 16) for p in paths], float)


def summarize(vals: dict[str, float], level: float = 0.95) -> dict:
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


def design_for(d: dict, y: np.ndarray, valid: np.ndarray | None = None, caliper: float = S.CALIPER, k: int | None = None):
    if valid is None or valid.all():
        band, kk = (d["band"], d["k"]) if k is None else S.bands(d["loc"], d["paths"], k)
        return S.Design(d["loc"], y, band, kk, caliper), band, kk, np.arange(d["n"])
    idx = np.flatnonzero(valid)
    paths = [d["paths"][i] for i in idx]
    band, kk = S.bands(d["loc"][idx], paths, k)
    return S.Design(d["loc"][idx], y[idx], band, kk, caliper), band, kk, idx


def silent(x: np.ndarray) -> bool:
    v = x[~np.isnan(x)]
    return len(v) == 0 or (v != 0).mean() < 0.10 or len(np.unique(v)) < 20


# ----------------------------------------------------------------------------------------------- stage 1: placebo
def stage_placebo() -> int:
    repos = [r for r in scored_repos() if r["HP"]["clears_floor"]]
    print(f"{len(repos)} repos clear the HP floor ({sum(r['drawn'] for r in repos)} drawn). No real predictor is scored here.")
    per, drawn = {}, []
    hashes = {"path_hash": np.zeros((len(repos), N_SALTS)), "dir_hash": np.zeros((len(repos), N_SALTS))}
    perm = {p: np.full((len(repos), N_PERMS), np.nan) for p in PRIMARIES}
    for ri, r in enumerate(repos):
        d = load(r["repo"], with_predictors=True)        # predictors are read ONLY to be shuffled
        y = d["y"]["HP"]
        des, band, k, _ = design_for(d, y)
        info = {"n": d["n"], "positives": int(y.sum()), "pairs": des.n, "pairs_gt": des.n_gt, "pairs_lt": des.n_lt,
                "clears_pair_floor": des.clears_pair_floor(), "bands": k, "drawn": r["drawn"]}
        for name, by_dir in (("path_hash", False), ("dir_hash", True)):
            for s in range(N_SALTS):
                hashes[name][ri, s] = des.effect(hash_placebo(d["paths"], s, by_dir))
        rng = np.random.default_rng(SEED)
        info["silent"] = {}
        for p in PRIMARIES:
            x = d["x"][p]
            valid = ~np.isnan(x)
            info["silent"][p] = bool(silent(x))
            dz, _, _, idx = design_for(d, y, valid)
            xv, lv, pv = x[idx], d["loc"][idx], [d["paths"][i] for i in idx]
            for s in range(N_PERMS):
                perm[p][ri, s] = dz.effect(S.block_permute(xv, lv, pv, rng))
        per[r["repo"]] = info
        drawn.append(r["drawn"])
        print(f"  {r['repo']:<16} files {d['n']:>6} HP {int(y.sum()):>4} pairs {des.n:>8}  path-hash "
              f"{hashes['path_hash'][ri].mean():+.4f}  dir-hash {hashes['dir_hash'][ri].mean():+.4f}", flush=True)
    drawn = np.array(drawn)
    out = {"repos": per, "n_drawn": int(drawn.sum()), "placebos": {}}

    def study(mat):                                      # the study mean over DRAWN repos, one value per salt
        m = np.nanmean(mat[drawn], axis=0)
        lo, hi = np.quantile(m, [0.025, 0.975])
        return {"mean": float(m.mean()), "sd_of_study_mean": float(m.std(ddof=1)), "range95": [float(lo), float(hi)],
                "centred": bool(lo <= 0 <= hi and abs(m.mean()) <= 0.002)}

    for name, mat in hashes.items():
        out["placebos"][name] = study(mat)
    for p, mat in perm.items():
        out["placebos"][f"block_perm:{p}"] = study(mat)
    gate = ["path_hash"] + [f"block_perm:{p}" for p in PRIMARIES]
    out["valid"] = all(out["placebos"][g]["centred"] for g in gate)
    # power: the Holm-first interval (98.33% two-sided) at 80% power, from each null spread, for three values of
    # the between-repo SD of true effects
    n = int(drawn.sum())
    zc = float(sps.t.ppf(1 - 0.05 / 3 / 2, n - 1)) + 0.8416
    out["power"] = {}
    for name in ("path_hash", "dir_hash"):
        sd = out["placebos"][name]["sd_of_study_mean"]
        out["power"][name] = {f"tau={t}": round(zc * float(np.sqrt(sd ** 2 + t ** 2 / n)), 4) for t in (0.0, 0.02, 0.04)}
    (DOCS / "sa3_placebo.json").write_text(json.dumps(out, indent=1) + "\n")
    print()
    for g, v in out["placebos"].items():
        print(f"  {g:<38} mean {v['mean']:+.4f}  95% range [{v['range95'][0]:+.4f}, {v['range95'][1]:+.4f}]  "
              f"sd {v['sd_of_study_mean']:.4f}  {'centred' if v['centred'] else 'NOT CENTRED'}")
    print(f"\n  validity gate: {'PASS' if out['valid'] else 'FAIL -- no SA3 result may be reported as a finding'}")
    print(f"  detectable mean effect, 80% power, Holm-first interval, {n} drawn repos: {json.dumps(out['power'])}")
    print("-> docs/sa3_placebo.json")
    return 0


# ------------------------------------------------------------------------------------------------- stage 2: score
def control_effects(d: dict, preds: list[str], rng) -> dict:
    """the matched control: K ordinary commits per draw, K = number of HP commits (HP subsampled if the pool is
    smaller); returns, per predictor, the mean over draws of effect(HP) - effect(control)"""
    hp, pool = list(d["hp_commits"]), list(d["pool"])
    K = min(len(hp), len(pool))
    if K < 5:
        return {}
    diffs = {p: [] for p in preds}
    for _ in range(N_DRAWS):
        yc = np.zeros(d["n"], int)
        for s in rng.choice(len(pool), K, replace=False):
            yc[d["pool"][pool[s]]] = 1
        yh = np.zeros(d["n"], int)
        for s in (rng.choice(len(hp), K, replace=False) if K < len(hp) else range(len(hp))):
            yh[d["hp_commits"][hp[s]]] = 1
        if not (0 < yc.sum() < d["n"]) or not (0 < yh.sum() < d["n"]):
            continue
        dc, dh = S.Design(d["loc"], yc, d["band"], d["k"]), S.Design(d["loc"], yh, d["band"], d["k"])
        for p in preds:
            x = np.nan_to_num(d["x"][p], nan=0.0)
            e = dh.effect(x) - dc.effect(x)
            if e == e:
                diffs[p].append(e)
    return {p: float(np.mean(v)) for p, v in diffs.items() if v}


def stage_score() -> int:
    missing = [m for m in MARKERS if not (DOCS / m).exists()]
    if missing:
        print("LOCKED. SA3 is not scored until these exist in docs/: " + ", ".join(missing))
        print("  sa3_power.md        the power amendment, from `placebo`\n"
              "  sa3ch_frozen.md     SA3-CH fully built, gated and reviewed (its Amendment 1, rule 8)\n"
              "  sa3_code_review.md  the independent code review of this scorer (checklist item 15b)")
        return 2
    plac = json.loads((DOCS / "sa3_placebo.json").read_text())
    rows = scored_repos()
    meta = {r["repo"]: r for r in rows}
    res = {"valid": plac["valid"], "unavailable": UNAVAILABLE, "repos": {}, "tests": {}}
    eff: dict = {}                                       # (outcome, predictor, statistic) -> {repo: value}
    rng = np.random.default_rng(SEED)
    for r in rows:
        d = load(r["repo"], with_predictors=True)
        rec = {"n": d["n"], "outcomes": {}}
        for oc in ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW"):
            if not r[oc]["clears_floor"]:
                continue
            y = d["y"][oc]
            cell = {}
            for p, (_inst, role, count) in PREDICTORS.items():
                if oc not in ("HP", "KW") and role != "primary":
                    continue
                x = d["x"][p]
                valid = ~np.isnan(x)
                if silent(x):
                    cell[p] = {"status": "instrument silent"}
                    continue
                des, band, k, idx = design_for(d, y, valid)
                if not des.clears_pair_floor():
                    cell[p] = {"status": "under pair floor"}
                    continue
                xv, lv, yv = x[idx], d["loc"][idx], y[idx]
                pv = [d["paths"][i] for i in idx]
                e = des.effect(xv)
                null = np.array([des.effect(S.block_permute(xv, lv, pv, rng)) for _ in range(N_PERMS)])
                c = {"status": "ok", "bauc": e, "dropped_null": int((~valid).sum()),
                     "residual": S.residual_effect(xv, yv, band, k, [np.log(lv)]),
                     "perm_p": float((np.abs(null - null.mean()) >= abs(e - null.mean())).mean()),
                     "S4_replaces": S.auc_plain(xv, yv) - S.auc_plain(lv, yv),
                     "S6_sauc_minus": S.sauc_minus_loc(xv, lv, yv, band, k),
                     "S9_logistic_z": S.logistic_z(xv, np.log(lv), yv, band, k, count)}
                if len(idx) >= 600:
                    d7, *_ = design_for(d, y, valid, caliper=1.25, k=20)
                    c["S7_tight"] = d7.effect(xv) if d7.clears_pair_floor() else None
                if role == "primary" and oc == "HP":
                    c["ci95"] = S.boot_ci(des, xv, band, k, yv)
                cell[p] = c
                for stat in ("bauc", "residual", "S4_replaces", "S6_sauc_minus", "S7_tight"):
                    if c.get(stat) is not None:
                        eff.setdefault((oc, p, stat), {})[r["repo"]] = c[stat]
            rec["outcomes"][oc] = cell
        if r["HP"]["clears_floor"]:
            rec["specificity"] = control_effects(d, list(PREDICTORS), rng)
            for p, v in rec["specificity"].items():
                eff.setdefault(("HP", p, "minus_control"), {})[r["repo"]] = v
        res["repos"][r["repo"]] = rec
        print(f"  scored {r['repo']}", flush=True)

    def pick(key, keep):
        return {k: v for k, v in eff.get(key, {}).items() if keep(meta[k])}

    drawn = lambda m: m["drawn"]                                                       # noqa: E731
    # Holm over B, C, D on HP, drawn repos
    first = {p: summarize(pick(("HP", p, "bauc"), drawn)) for p in CONFIRMATORY}
    order = sorted(CONFIRMATORY, key=lambda p: first[p].get("p", 1.0))
    still = True
    for rank, p in enumerate(order):
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
    res["tests"]["in_degree"] = {"exploratory": True, "bauc": a, "residual": summarize(pick(("HP", "in_degree", "residual"), drawn)),
                                 "reading": {"supported": "positive", "contradicted": "negative"}.get(a["reading"], a["reading"])}
    cuts = {"all_drawn": drawn, "earlier_eight": lambda m: not m["drawn"],
            "S1_new_languages_removed": lambda m: m["drawn"] and m["repo"] not in NEW_LANGS,
            "S2_merge_workflow_removed": lambda m: m["drawn"] and not m["merge_units"],
            "S3_full_window": lambda m: m["drawn"] and m["window_days"] >= 730,
            "go_django_removed": lambda m: m["drawn"] and m["repo"] not in ("go", "django"),
            "C_family": lambda m: m["drawn"] and m["family"] == "C",
            "managed": lambda m: m["drawn"] and m["family"] != "C"}
    res["summaries"] = {f"{oc}|{p}|{stat}|{name}": summarize(pick((oc, p, stat), keep))
                        for (oc, p, stat) in sorted(eff) for name, keep in cuts.items()
                        if name == "all_drawn" or (oc == "HP" and stat == "bauc")}
    (DOCS / "sa3_result.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print("\nSA3, primary outcome, drawn repos:")
    for p, t in res["tests"].items():
        b = t["bauc"]
        if "mean" in b:
            print(f"  {p:<26} mean {b['mean']:+.4f}  CI [{b['ci'][0]:+.4f}, {b['ci'][1]:+.4f}] n={b['n']} "
                  f"(+{b['positive']}/-{b['negative']})  {t['reading']}")
    print("-> docs/sa3_result.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("placebo", "score"))
    a = ap.parse_args()
    return stage_placebo() if a.stage == "placebo" else stage_score()


if __name__ == "__main__":
    raise SystemExit(main())
