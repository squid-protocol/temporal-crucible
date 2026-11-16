#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The sensitivities of Amendment 5 section 6 as variants of part 1's route (docs/process/
comparison_scorer_part2_spec.md, Revision 2, section 4). Decoys only; on real data they run inside the scoring
job (a later specification), after the reference `score`.

  PU_named_streams                 part 1's scorer with named streams (streams.NamedStreams); baseline: the
                                   frozen run (the reference's result)
  PU_tracker_keys_case_sensitive   } the outcome files rebuilt from harvest copies (harvest_variant.py), label
  PU_late_revert_ticket_dropped    } tables in the frozen order, floors from the rebuilt files, scored on named
                                   streams; baseline: PU_named_streams
  the other seven                  printed with the reason they are not scored (equal from the counts published
                                   before scoring, or not run)

Rules (section 4): a repo whose harvest copy lost no row keeps its frozen file; a repo that lost rows is rebuilt,
and the rebuilt file is used only when the builder, run unchanged on the UNMODIFIED copy, reproduces the frozen
file (as parsed JSON, the over-cap sample left out; the owner job's "A equals the stored file") -- otherwise
the repo keeps its frozen file and the output says so. In a rebuilt file, commits also in the frozen file keep
its order and new ones follow (harvest_variant.reorder). Floors: the rebuilt file's `clears_floor` for that
repo; every other repo the frozen marginals file's.

Output: per variant, for each primary on each outcome, the mean of bAUC over the drawn repos with its 95%
interval, the number of repos and "above zero", "below zero", "not detected" or "not fitted (fewer than three
repos)"; beside each, the difference from the baseline. No Holm level, no confirmatory word. Every variant is
printed, in the spec's order, whatever it shows.

    python3 tools/compare/variants.py --decoy-study BASE/N --scratch D --out O     (decoys only)
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if "tools_compare__util" not in sys.modules:
    import importlib.util as _iu
    _s = _iu.spec_from_file_location("tools_compare__util", str(HERE / "_util.py"))
    _m = _iu.module_from_spec(_s)
    sys.modules["tools_compare__util"] = _m
    _s.loader.exec_module(_m)
U = sys.modules["tools_compare__util"]
SCO = U.sibling("scorer")
ST = U.sibling("streams")
HV = U.sibling("harvest_variant")
CM = U.sibling("cellmap")
T = U.sibling("tables")

OUTCOMES = SCO.OUTCOMES
PRIMARIES = SCO.PRIMARIES
SENTENCE = ("None of these replaces the confirmatory reading. Every one is reported, in this order, whatever it "
            "shows.")
# (name, how it is reported, the fixed text for one that is not scored)
TABLE = (
    ("PU_named_streams", "scored", None),
    ("PU_tracker_keys_case_sensitive", "scored", None),
    ("PU_late_revert_ticket_dropped", "scored", None),
    ("PU_reachable_universe", "equal",
     "equals the frozen run: 0 universe files the history walk cannot touch, in every repo "
     "(docs/sa3_prescoring_counts.md); not scored"),
    ("PU_unreachable_made_reachable", "equal",
     "equals the frozen run: 0 such files (docs/sa3_prescoring_counts.md); not scored"),
    ("PU_new_completeness", "equal",
     "equals the frozen run: the new measure drops the same six repos as the registered one "
     "(docs/sa3_prescoring_counts.md); not scored"),
    ("PU_nesting_floor", "equal",
     "equals the frozen run: nesting coverage is 100% wherever a nesting file exists, and a repo without one "
     "already has silent nesting cells (docs/sa3_prescoring_counts.md); not scored"),
    ("PU_window_assertion", "equal",
     "equals the frozen run: no repo's window ends before it starts (docs/sa3_prescoring_counts.md); not scored"),
    ("PU_generic_dirs_restored", "not run",
     "not run: the stored history records no touch for paths under cache/, dist/, extern/ or env/, so restored "
     "files could never be positive; their labels need a new extraction from the clones. Size: 65 scanned files "
     "in seven repos scored on the primary outcome"),
    ("S8", "not run", "not run, as Amendment 4 reported: rename following is a new rule, not a variant"),
)
WORD = {"supported": "above zero", "contradicted": "below zero", "not detected": "not detected"}
BANNED = ("supported", "contradicted", "holm", "0.9833", "0.975")


# =================================================================================================== scoring
def score_named(sealed: Path, data: dict, marg: list[dict] | None = None) -> dict:
    """part 1 on named streams; `marg` replaces the sealed marginals rows (a variant's floors)"""
    sc = ST.NamedStreams(sealed, copy.deepcopy(data))
    if marg is not None:
        sc.marg = marg
    return json.loads(SCO.dumps(sc.score()))


def apply_rebuilt(marg: list[dict], repo: str, new: dict) -> None:
    """the floors of a rebuilt outcome file into that repo's marginals row (in place); other rows untouched"""
    for row in marg:
        if row["repo"] == repo:
            for oc in OUTCOMES:
                row[oc] = {**row[oc], **{k: new["outcomes"][oc][k] for k in
                                         ("n_files", "n_commits", "largest_commit_share", "clears_floor")}}


def variant_inputs(L: "HV.Layout", repos: list[str], which: str, frozen_dir: Path, labels: Path, marg: list[dict],
                   work: Path) -> dict:
    """the variant's label tables and marginals rows. Returns {"labels", "marg", "repos": {repo: what was done}}"""
    outs = HV.variant_outcomes(L, repos, which)
    lt = work / f"labels_{which}"
    if lt.exists():
        shutil.rmtree(lt)
    shutil.copytree(labels, lt)
    od = work / f"outcomes_{which}"
    if od.exists():
        shutil.rmtree(od)
    od.mkdir(parents=True)
    marg = copy.deepcopy(marg)
    info = {}
    for r, rec in outs.items():
        if not rec["deleted_rows"]:
            info[r] = {"deleted_rows": 0, "applied": False, "reason": "no row deleted: the frozen file stands"}
            continue
        frozen = json.loads((Path(frozen_dir) / f"{r}.json").read_text())
        plain = HV.build(L, r, HV.prepare(L, r), "plain")
        if HV.comparable(plain) != HV.comparable(frozen):
            info[r] = {"deleted_rows": rec["deleted_rows"], "applied": False,
                       "reason": "the builder does not reproduce the frozen file from the unmodified copy: the "
                                 "frozen file stands"}
            continue
        new = HV.reorder(frozen, rec["rebuilt"])
        (od / f"{r}.json").write_text(json.dumps(new) + "\n")
        shutil.rmtree(lt / r)
        T.build_label_tables(od, [r], lt)
        apply_rebuilt(marg, r, new)
        diff = HV.commit_diff(frozen, new)
        info[r] = {"deleted_rows": rec["deleted_rows"], "applied": True, "reason": "rebuilt",
                   "commits_changed": {k: {s: len(v[s]) for s in v} for k, v in diff.items()}}
    return {"labels": lt, "marg": marg, "repos": info}


# ==================================================================================================== output
def summary_row(res: dict, oc: str, p: str) -> dict:
    s = res.get("summaries", {}).get(f"{oc}|{p}|bauc|all_drawn", {"n": 0, "reading": "not fitted"})
    if "mean" not in s:
        return {"n": s.get("n", 0), "mean": None, "ci": None, "word": "not fitted (fewer than three repos)"}
    return {"n": s["n"], "mean": s["mean"], "ci": list(s["ci"]), "word": WORD[s["reading"]]}


def block(name: str, res: dict, base: dict, base_name: str) -> dict:
    rows = []
    for oc in OUTCOMES:
        for p in PRIMARIES:
            a, b = summary_row(res, oc, p), summary_row(base, oc, p)
            d = {"n": a["n"] - b["n"]}
            if a["mean"] is not None and b["mean"] is not None:
                d.update({"mean": a["mean"] - b["mean"], "lo": a["ci"][0] - b["ci"][0], "hi": a["ci"][1] - b["ci"][1]})
            rows.append({"outcome": oc, "predictor": p, **a, "difference": d})
    return {"name": name, "status": "scored", "baseline": base_name, "rows": rows}


def changed_cells(res: dict, base: dict) -> dict:
    """the per-repo cells that differ from the baseline (exact equality), as (repo, outcome or "control",
    predictor), and how many study-level cells differ"""
    a, b = dict(CM.flatten(res)), dict(CM.flatten(base))
    out: dict = {}
    study = 0
    for p in set(a) | set(b):
        if p in a and p in b and CM.same(a[p], b[p]):
            continue
        pos = CM.position(p)
        if pos[0] == "study":
            study += 1
        else:
            out.setdefault(pos[0], set()).add(tuple(pos[1:3]))
    return {"repos": {r: sorted(v) for r, v in sorted(out.items())}, "study_cells": study}


def _f(v) -> str:
    return "-" if v is None else f"{v:+.6f}"


def _d(v) -> str:
    return "-" if v is None else f"{v:+.2e}"


def render(blocks: list[dict]) -> str:
    L = [SENTENCE, ""]
    for b in blocks:
        if b["status"] != "scored":
            L += [f"{b['name']}: {b['text']}", ""]
            continue
        L.append(f"{b['name']} (difference from {b['baseline']})")
        for k, v in b.get("inputs", {}).items():
            L.append(f"  input {k}: {v}")
        L.append(f"  {'outcome':<14}{'predictor':<26}{'n':>3}{'mean':>11}{'95% interval':>24}  {'reads':<36}"
                 f"{'d n':>4}{'d mean':>11}{'d lo':>11}{'d hi':>11}")
        for r in b["rows"]:
            ci = "-" if r["ci"] is None else f"[{_f(r['ci'][0])}, {_f(r['ci'][1])}]"
            d = r["difference"]
            L.append(f"  {r['outcome']:<14}{r['predictor']:<26}{r['n']:>3}{_f(r['mean']):>11}{ci:>24}  "
                     f"{r['word']:<36}{d['n']:>+4}{_d(d.get('mean')):>11}{_d(d.get('lo')):>11}{_d(d.get('hi')):>11}")
        L.append("")
    return "\n".join(L)


def vocabulary_ok(text: str) -> list[str]:
    """the banned words and levels found in a variant's printed output (empty: none)"""
    low = text.lower()
    return [w for w in BANNED if w in low]


# ================================================================================================== the run
def run(study: dict, scratch: Path, frozen: dict, named: dict | None = None, which=("case", "late"),
        results: dict | None = None) -> dict:
    """study: {"decoy": DIR (study/, pool/), "pb", "ct", "lt", "sealed"}; frozen: the reference's result.
    Returns {"blocks", "results", "inputs", "text"}. `named` and `results` reuse runs already made"""
    SR = U.sandbox_ro()
    scratch = SR.check_rw(Path(scratch))
    sealed = Path(study["sealed"])
    data = SCO.load_data(Path(study["pb"]), Path(study["ct"]), Path(study["lt"]), sealed)
    marg = json.loads((sealed / "docs" / "sa3_outcome_marginals.json").read_text())
    repos = [r["repo"] for r in marg if r["status"] == "ok"]
    results = dict(results or {})
    if named is None:
        named = score_named(sealed, data)
    results["PU_named_streams"] = named
    inputs = {}
    L = HV.Layout(Path(study["decoy"]) / "study", Path(study["decoy"]) / "pool", scratch / "harvest")
    for w in which:
        name = HV.VARIANTS[w]
        vi = variant_inputs(L, repos, w, Path(study["decoy"]) / "study" / "sa3_outcomes", Path(study["lt"]), marg,
                            scratch)
        inputs[name] = vi["repos"]
        if name in results:
            continue
        if not any(v["applied"] for v in vi["repos"].values()):
            results[name] = named                         # no input changed: the same inputs as the baseline
            continue
        vdata = SCO.load_data(Path(study["pb"]), Path(study["ct"]), vi["labels"], sealed)
        results[name] = score_named(sealed, vdata, vi["marg"])
    blocks = []
    for name, how, text in TABLE:
        if how != "scored":
            blocks.append({"name": name, "status": how, "text": text})
            continue
        if name == "PU_named_streams":
            b = block(name, results[name], frozen, "the frozen run")
        else:
            b = block(name, results[name], results["PU_named_streams"], "PU_named_streams")
            b["inputs"] = {r: f"{v['deleted_rows']} rows deleted; {v['reason']}" for r, v in inputs[name].items()
                           if v["deleted_rows"]}
            if not b["inputs"]:
                b["inputs"] = {"all repos": "no row deleted: every frozen file stands; equal to PU_named_streams"}
        blocks.append(b)
    text = render(blocks)
    found = vocabulary_ok(text + json.dumps(blocks))
    if found:
        raise ValueError(f"a variant's output carries {found}")
    return {"blocks": blocks, "results": results, "inputs": inputs, "text": text}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decoy-study", required=True, help="a decoy study built by decoy_study.py (BASE/N or BASE/P)")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--real", action="store_true")
    a = ap.parse_args(argv)
    if a.real:
        print("variants: real data is scored only inside the scoring job (a later specification); refused")
        return 2
    b = HV.check_decoy(Path(a.decoy_study))
    rec = json.loads((b / "built.json").read_text())
    p = rec["paths"]
    study = {"decoy": p["decoy"], "pb": Path(p["tables"]) / "phase_b", "ct": Path(p["tables"]) / "compare",
             "lt": Path(p["tables"]) / "labels", "sealed": p["sealed"]}
    out = run(study, Path(a.scratch), json.loads(Path(p["result"]).read_text()))
    o = U.sandbox_ro().check_rw(Path(a.out).parent) / Path(a.out).name
    o.write_text(out["text"])
    print(out["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
