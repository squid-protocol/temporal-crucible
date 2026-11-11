#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The LAWS driver: every law over a set of repos, then the synthesis (should-fix 9, the pilot requirement that
the full scorer runs end to end before the scorer hash is frozen).

    python tools/laws_run.py --out DIR --repos a,b,c                 -> DIR/laws_run.json

Per repo it builds the quarterly and yearly networks once and feeds every law from them, so a law is never handed
an input another law has already paid for. Each law runs inside its own guard: a law that raises is recorded as a
failure with its exception and the run continues, because the registration asks for the failure modes to be
published rather than for the run to stop at the first one.

    LAW-1 tails        the in-degrees (k >= 1) of the LAST quarterly snapshot
    LAW-2 attach       every consecutive pair of quarterly snapshots
    LAW-3 hubs         the yearly snapshots, pairs 5 years apart
    LAW-4 central      the quarterly snapshots, replayed under the repo's own fitted LAW-2 kernel
    LAW-5 decay        the yearly snapshots (descriptive; two legs, Q and PC)
    LAW-6/7 defects    the file-years of tools/laws_panel.py
    LAW-8 predict      the same file-years, forward and effort-aware
    LAW-9 security     the fix-commit table of tools/laws_osv.py (descriptive)

`--labels workflow` computes the defect laws from the M6 workflow fix label (tools/laws_github.py) instead of the
history database's keyword label; see docs/laws_defect_labels.md. The default is `keyword`, the registered one.

The synthesis groups repos by language and applies tools/laws_synth.py: a random-effects pool per language, the
one-sided p against each law's registered margin, and the primary and extended partial-conjunction calls. With
one repo per language -- which is what the development set is -- a pool is a single study and its p is that
repo's; the synthesis is exercised end to end but says nothing about any language, and the record says so rather
than presenting a one-repo pool as a language result.

Margins and directions are the registered ones, from each estimator's own docstring: LAW-1 to LAW-4 and LAW-6
margin 0 in the positive direction; LAW-7 margin 0.5 for each of its three metrics; LAW-8 margin 0.02 with the
+-0.02 equivalence test; LAW-9's three metrics margin 0 in the NEGATIVE direction (a CVE fix is smaller). LAW-5
and LAW-9 are descriptive and are pooled for the record only, never tested for universality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

import laws_attach as A  # noqa: E402
import laws_central as C  # noqa: E402
import laws_decay as DE  # noqa: E402
import laws_defects as D  # noqa: E402
import laws_github as G  # noqa: E402
import laws_hubs as H  # noqa: E402
import laws_net as N  # noqa: E402
import laws_panel as P  # noqa: E402
import laws_predict as R  # noqa: E402
import laws_security as S  # noqa: E402
import laws_synth as SY  # noqa: E402
import laws_tails as T  # noqa: E402
from laws_defect_run import LANGUAGE, labels_for  # noqa: E402

# law -> (margin, direction, confirmatory). A metric-bearing law lists its metrics instead of one effect.
SPEC: dict[str, dict] = {
    "LAW-1": {"margin": 0.0, "direction": 1, "confirmatory": True},
    # Amendment 5: LAW-2's effect is the excess over the fitness-only null, not alpha against zero. Pure
    # fitness yields alpha about 1.09, above a true exponent of 1.0, so alpha against 0 does not test the law.
    "LAW-2": {"margin": 0.0, "direction": 1, "confirmatory": True,
              "path": ("fitness_null",), "effect_key": "excess", "se_key": "se_excess"},
    "LAW-3": {"margin": 0.0, "direction": 1, "confirmatory": True},
    "LAW-4": {"margin": 0.0, "direction": 1, "confirmatory": True},
    "LAW-5": {"margin": 0.0, "direction": 1, "confirmatory": False,
              "legs": {"q": ("q_slope", "q_se", -1), "pc": ("pc_slope", "pc_se", 1)}},
    "LAW-6": {"margin": 0.0, "direction": 1, "confirmatory": True},
    "LAW-7": {"margin": 0.5, "direction": 1, "confirmatory": True, "metrics": D.METRICS},
    "LAW-8": {"margin": 0.02, "direction": 1, "confirmatory": True, "equivalence": 0.02},
    # Amendment 5: LAW-9's effect is P(cve smaller) against a null of 0.5. The registered Hodges-Lehmann shift
    # is exactly 0.00 with SE 0.00 on two of three legs, so it cannot enter a variance-weighted pool at all.
    "LAW-9": {"margin": 0.5, "direction": 1, "confirmatory": False, "metrics": S.METRICS,
              "effect_key": "p_smaller", "se_key": "se_p_smaller"},
}


def _edge_kept(edge, share: float, seed: int) -> bool:
    """Whether one edge survives thinning. Keyed on the EDGE IDENTITY, not on the draw order, so the same edge
    gets the same verdict in every snapshot it appears in."""
    h = hashlib.blake2b(repr(edge).encode(), digest_size=8, key=str(seed).encode()).digest()
    return int.from_bytes(h, "big") / 2 ** 64 < share


def thinned(nets: list, share: float, seed: int) -> list:
    """The same networks with a `share` of the edges kept, the SAME edges at every snapshot: the coverage
    sensitivity.

    The engine resolves ~99% of call sites in C and ~56-60% in Java, Go and Python
    (docs/laws_driver_pilot.md). Thinning a C repo's edges to the others' share answers the question that
    matters -- whether a law's reading survives being measured as badly as the Java networks are. A law that
    holds under thinning is not an artefact of C's better coverage; one that does not cannot support a
    between-language claim however much engine work is done.

    **The mask must be persistent, and a per-snapshot draw is wrong.** Coverage failure is a property of the
    call site: an `obj.method()` whose receiver type cannot be inferred is unresolved at every snapshot, not at a
    random subset of them. Thinning each snapshot independently instead drops an edge at t and keeps it at t + 1,
    which LAW-2 reads as a NEW edge -- the first run of this sensitivity inflated libgit2's choice count from
    16,593 to 121,112 and libxml2's from 10,746 to 235,931, and corrupted LAW-3's persistence pairs and LAW-4's
    replay the same way. Hashing the edge identity fixes it: the verdict is the same wherever the edge appears.
    LAW-1 was unaffected either way, because it reads one snapshot.

    Uniform thinning is still a LOWER BOUND on the damage. Real failures are selective -- the dominant
    unresolved step is `receiver`, concentrating on dynamically dispatched calls rather than falling evenly -- so
    a selective null would hurt more, and is not modelled here.
    """
    out = []
    for n in nets:
        m = N.Net(n.sha, n.date)
        m.nodes = n.nodes  # read-only downstream; the node set is not what coverage loses
        m.edges = {e for e in n.edges if _edge_kept(e, share, seed)}
        m.profile = {**n.profile, "thinned_to": share, "edges": len(m.edges), "edges_before": len(n.edges)}
        out.append(m)
    return out


def guarded(name: str, fn, failures: dict):
    t0 = time.time()
    try:
        rec = fn()
        rec["seconds"] = round(time.time() - t0, 1)
        return rec
    except Exception as e:  # noqa: BLE001 -- the registration asks for failure modes, not for the run to stop
        failures[name] = {"error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-800:],
                          "seconds": round(time.time() - t0, 1)}
        return {"evaluable": False, "why": f"the estimator raised {type(e).__name__}", "failed": True}


def one_repo(out: Path, repo: str, language: str, labels: dict[str, bool], boot: int, sims: int | None,
             thin: float | None = None, thin_seed: int = 2982) -> dict:
    t0 = time.time()
    failures: dict = {}
    rec: dict = {"repo": repo, "language": language, "failures": failures}
    con = sqlite3.connect(f"file:{out / 'dbs' / f'{repo}.db'}?mode=ro", uri=True)
    snaps = N.snapshots(con)
    nets = [N.network(con, sha, date, language) for sha, date, _ in snaps]
    yearly = [N.network(con, sha, date, language) for sha, date, _ in N.yearly(snaps)]
    con.close()
    rec["snapshots"] = {"quarterly": len(nets), "yearly": len(yearly)}
    if not nets:
        return {**rec, "why": "no scanned snapshot", "seconds": round(time.time() - t0, 1)}
    rec["profile"] = nets[-1].profile
    if thin is not None:
        # the network laws see the thinned networks; the defect panel is not thinned in this pass (it builds its
        # own networks inside laws_panel.file_years), which the record states rather than implies
        nets, yearly = thinned(nets, thin, thin_seed), thinned(yearly, thin, thin_seed)
        rec["thinned"] = {"share": thin, "seed": thin_seed, "applies_to": "LAW-1 to LAW-5",
                          "edges_last": len(nets[-1].edges), "edges_last_before": rec["profile"]["edges"]}
    rec["nodes_last"] = len(nets[-1].nodes)

    degrees = [k for k in nets[-1].in_degree().values() if k >= 1]
    rec["LAW-1"] = guarded("LAW-1", lambda: T.fit(degrees, boot=boot), failures)
    rec["LAW-2"] = guarded("LAW-2", lambda: A.fit(nets), failures)
    # Amendment 5: the law's effect is the excess over the fitness-only null; the plain fit stays descriptive
    rec["LAW-2"]["fitness_null"] = guarded("LAW-2-null", lambda: A.fitness_null(nets), failures)
    rec["LAW-3"] = guarded("LAW-3", lambda: H.fit(yearly, boot=boot), failures)
    law2 = rec["LAW-2"]
    rec["LAW-4"] = guarded("LAW-4", lambda: C.fit(nets, law2, **({"sims": sims} if sims else {})), failures)
    rec["LAW-5"] = guarded("LAW-5", lambda: DE.fit(yearly, boot=boot), failures)

    rows, summary = P.file_years(out / "dbs" / f"{repo}.db", out / "history" / f"{repo}.db", language, labels)
    rec["panel"] = summary
    rec["LAW-6"] = guarded("LAW-6", lambda: D.law6(rows, boot=boot), failures)
    rec["LAW-7"] = guarded("LAW-7", lambda: D.law7(rows, boot=boot), failures)
    rec["LAW-8"] = guarded("LAW-8", lambda: R.fit(rows), failures)

    osv = out / "osv" / f"{repo}.json"
    if osv.exists() and (o := json.loads(osv.read_text())).get("sized"):
        rec["LAW-9"] = guarded("LAW-9", lambda: S.law9(o["commits"], boot=boot), failures)
    else:
        rec["LAW-9"] = {"evaluable": False, "why": "no sized OSV fix-commit table for this repo"}
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def _rec_for(repo: dict, law: str, spec: dict) -> dict:
    """The record a law's effect is read from: its own, or a nested one where the spec names a `path` (LAW-2's
    effect lives in its fitness-null record, not in the plain fit)."""
    rec = repo.get(law) or {}
    for step in spec.get("path", ()):
        rec = rec.get(step) or {}
    return rec


def _effects(repos: list[dict], law: str, spec: dict, key: str | None = None) -> list[tuple[str, float, float]]:
    """(repo, effect, se) for the repos where this law (or one metric of it) is evaluable. The effect and SE keys
    come from the spec, because Amendment 5 gives LAW-2 and LAW-9 effects that are not called `effect`."""
    ekey, skey = spec.get("effect_key", "effect"), spec.get("se_key", "se")
    out = []
    for r in repos:
        rec = _rec_for(r, law, spec)
        ok = bool(rec.get("evaluable"))
        if key:
            sub = (rec.get("metrics") or {}).get(key) or {}
            # A metric record may carry its own evaluability (LAW-7's, which gates each metric separately) or
            # not (LAW-9's, which are shift() records that exist only when the law itself is evaluable). Falling
            # back to the law's own flag is what makes the second kind reachable at all.
            ok = bool(sub.get("evaluable", ok))
            rec = sub
        if not ok:
            continue
        e, se = rec.get(ekey), rec.get(skey)
        if e is None or se is None or not (se == se) or se <= 0:  # NaN or non-positive SE: unusable in a pool
            continue
        out.append((r["repo"], float(e), float(se)))
    return out


def _leg_effects(repos: list[dict], law: str, eff_key: str, se_key: str) -> list[tuple[str, float, float]]:
    out = []
    for r in repos:
        rec = r.get(law) or {}
        if not rec.get("evaluable"):
            continue
        e, se = rec.get(eff_key), rec.get(se_key)
        if e is None or se is None or not (se == se) or se <= 0:
            continue
        out.append((r["repo"], float(e), float(se)))
    return out


def _pool_one(rows: list[tuple[str, float, float]], margin: float, direction: int,
              equivalence: float | None) -> dict:
    if not rows:
        return {"repos": 0, "poolable": False, "why": "no repo is evaluable for this law"}
    y = [e for _, e, _ in rows]
    v = [se ** 2 for _, _, se in rows]
    out = {"repos": len(rows), "by_repo": {n: {"effect": e, "se": se} for n, e, se in rows}}
    if len(rows) == 1:
        # The registered synthesis is a random-effects pool and needs k >= 2: tau^2 is not identified from one
        # study. The development set has one repo per language, so no language-level estimate exists here. The
        # repo's own one-sided p is reported, clearly not as a pooled or language result, and the universality
        # test still receives 1.0 for this language (not evaluable counts against, and is not re-scaled).
        name, e, se = rows[0]
        z = direction * (e - margin) / se
        return {**out, "poolable": False,
                "why": "the registered random-effects pool needs at least 2 repos; this language has 1",
                "single_study": {"repo": name, "effect": e, "se": se,
                                 "p": float(stats.norm.sf(z)), "p_opposite": float(stats.norm.cdf(z))}}
    try:
        pooled = SY.pool(y, v)
    except Exception as e:  # noqa: BLE001
        return {**out, "poolable": False, "why": f"pool raised {type(e).__name__}: {e}"}
    out["pooled"] = pooled
    out["poolable"] = True
    out["p"] = SY.one_sided_p(pooled, margin, direction)
    out["p_opposite"] = SY.one_sided_p(pooled, margin, -direction)
    if equivalence is not None:
        out["equivalence_p"] = SY.tost_p(pooled, equivalence)
    return out


def matched_share(repos: list[dict]) -> float | None:
    """The coverage share every network is thinned to for Amendment 5's matched-coverage pass: the MINIMUM over
    languages of that language's median `share_confident_of_repo_links`.

    Minimum over languages, median within one: a language is represented by its typical repo, and the comparison
    is then made at the quality of the worst-measured language, because that is the only level every language can
    actually be measured at. The figure is a floor rather than a true rate (the `unresolved` table cannot be
    scoped like the numerator), so this is a conservative amount of thinning."""
    by_lang: dict[str, list[float]] = {}
    for r in repos:
        share = (r.get("profile") or {}).get("share_confident_of_repo_links")
        if share:
            by_lang.setdefault(r["language"], []).append(float(share))
    if not by_lang:
        return None
    medians = [sorted(v)[len(v) // 2] for v in by_lang.values()]
    return min(medians)


def synthesise(repos: list[dict]) -> dict:
    languages = sorted({r["language"] for r in repos})
    by_lang = {lang: [r for r in repos if r["language"] == lang] for lang in languages}
    per_law: dict = {}
    law_ps: dict[str, dict[str, float]] = {}
    opp_ps: dict[str, dict[str, float]] = {}
    for law, spec in SPEC.items():
        entry: dict = {"confirmatory": spec["confirmatory"], "margin": spec["margin"],
                       "direction": spec["direction"], "languages": {}}
        for lang, rs in by_lang.items():
            if "metrics" in spec:
                entry["languages"][lang] = {
                    m: _pool_one(_effects(rs, law, spec, m), spec["margin"], spec["direction"],
                                 spec.get("equivalence"))
                    for m in spec["metrics"]}
            elif "legs" in spec:
                entry["languages"][lang] = {
                    name: _pool_one(_leg_effects(rs, law, ek, sk), spec["margin"], d, None)
                    for name, (ek, sk, d) in spec["legs"].items()}
            else:
                entry["languages"][lang] = _pool_one(_effects(rs, law, spec), spec["margin"], spec["direction"],
                                                     spec.get("equivalence"))
        per_law[law] = entry
        if not spec["confirmatory"]:
            continue
        # a law with metrics enters the universality test through its weakest metric (the conjunction M2 names)
        def pick(rec: dict) -> tuple[float, float]:
            if "metrics" in spec:
                ps = [rec[m].get("p", 1.0) for m in spec["metrics"] if rec.get(m, {}).get("poolable")]
                qs = [rec[m].get("p_opposite", 1.0) for m in spec["metrics"] if rec.get(m, {}).get("poolable")]
                return (max(ps) if ps else 1.0, max(qs) if qs else 1.0)
            return (rec.get("p", 1.0) if rec.get("poolable") else 1.0,
                    rec.get("p_opposite", 1.0) if rec.get("poolable") else 1.0)
        law_ps[law] = {lang: pick(entry["languages"][lang])[0] for lang in languages}
        opp_ps[law] = {lang: pick(entry["languages"][lang])[1] for lang in languages}
    return {"languages": languages, "repos_per_language": {k: len(v) for k, v in by_lang.items()},
            "per_law": per_law, "universal": SY.universal(law_ps, opp_ps, languages),
            "caveat": ("The development set has one repo per language. Every pool below is a single study, so the "
                       "universality calls exercise the code path and are not evidence about any language.")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repos", required=True, help="comma-separated")
    ap.add_argument("--labels", choices=("keyword", "workflow"), default="keyword")
    ap.add_argument("--boot", type=int, default=D.BOOT)
    ap.add_argument("--sims", type=int, default=None, help="LAW-4 replays (default: the registered SIMS)")
    ap.add_argument("--tag", default=None, help="names the output file")
    ap.add_argument("--thin", type=float, default=None,
                    help="keep this share of each network's edges (the coverage sensitivity; LAW-1 to LAW-5)")
    ap.add_argument("--matched-coverage", action="store_true",
                    help="Amendment 5 item 4: after the full-coverage pass, re-run every law with each network "
                         "thinned to the minimum per-language median coverage across the run's languages")
    ap.add_argument("--thin-seed", type=int, default=2982)
    a = ap.parse_args()
    t0 = time.time()
    repos = []
    for name in [r.strip() for r in a.repos.split(",") if r.strip()]:
        language = LANGUAGE.get(name)
        if language is None:
            print(f"{name}: no registered language; skipped")
            continue
        labels, note = ({}, "keyword label") if a.labels == "keyword" else labels_for(a.out, name)
        rec = one_repo(a.out, name, language, labels, a.boot, a.sims, a.thin, a.thin_seed)
        rec["labels_note"] = note
        repos.append(rec)
        laws = " ".join(f"{k.split('-')[1]}{'+' if (rec.get(k) or {}).get('evaluable') else '-'}"
                        for k in SPEC)
        print(f"{name} ({language}): laws {laws}  {len(rec['failures'])} failed  [{rec['seconds']}s]")
        for law, f in rec["failures"].items():
            print(f"    {law} FAILED: {f['error']}")
    matched = None
    if a.matched_coverage and repos and a.thin is None:
        share = matched_share(repos)
        if share is None:
            print("\nmatched coverage: no repo reports a coverage share; skipped")
        else:
            print(f"\n=== matched-coverage pass: thinning every network to {share:.3f} "
                  f"(the minimum per-language median) ===")
            matched = {"share": share, "repos": []}
            for name in [r["repo"] for r in repos]:
                language = LANGUAGE[name]
                labels, _ = ({}, "") if a.labels == "keyword" else labels_for(a.out, name)
                m = one_repo(a.out, name, language, labels, a.boot, a.sims, share, a.thin_seed)
                matched["repos"].append(m)
                laws = " ".join(f"{k.split('-')[1]}{'+' if (m.get(k) or {}).get('evaluable') else '-'}"
                                for k in SPEC)
                print(f"{name} ({language}) [matched {share:.3f}]: laws {laws}  "
                      f"{len(m['failures'])} failed  [{m['seconds']}s]")
            matched["synthesis"] = synthesise(matched["repos"])

    rec = {"repos": repos, "synthesis": synthesise(repos) if repos else None, "matched_coverage": matched,
           "labels": a.labels, "boot": a.boot, "sims": a.sims, "thin": a.thin,
           "seconds": round(time.time() - t0, 1),
           "failures": {r["repo"]: list(r["failures"]) for r in repos if r["failures"]}}
    f = a.out / f"laws_run_{a.tag or a.labels}.json"
    f.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"\n{len(repos)} repos, {sum(len(r['failures']) for r in repos)} law failures, "
          f"{rec['seconds']}s total -> {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
