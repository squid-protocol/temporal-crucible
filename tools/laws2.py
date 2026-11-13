#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS2 — the run frame: one declarative pipeline that is also the checklist.

    python tools/laws2.py status                 # what is done, ready, blocked, missing
    python tools/laws2.py checklist --write      # regenerate docs/laws2_checklist.md FROM this file
    python tools/laws2.py run <stage>            # run one stage (refuses if a gate above it has not passed)
    python tools/laws2.py verify                 # re-hash every recorded output and report drift
    python tools/laws2.py figures                # build every figure whose inputs now exist
    python tools/laws2.py controls               # the control registry and which laws each one covers

**Why this file exists.** LAWS 1 failed because the expensive, irreversible steps (frame, fingerprint, draw,
seating) ran BEFORE the cheap step that decided everything (can the oracle run at all?). The order is not a
matter of taste, so it is encoded here rather than written in prose: a stage marked `gate` must PASS before any
later phase runs, and `run` refuses otherwise. docs/laws2_checklist.md is generated from STAGES, so the
checklist cannot drift from the pipeline.

**Reproducibility.** Every stage records its outputs' sha256, the tool version, the engine pin and the wall
clock into docs/laws2_manifest.json. `verify` recomputes them: a changed input with an unchanged output, or the
reverse, is reported as drift rather than discovered months later.

Nothing here computes a law. It sequences the work and holds the evidence that each step was done.
"""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, sys, time
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFEST = DOCS / "laws2_manifest.json"
VERSION = "laws2-frame/1"

# --------------------------------------------------------------------------------------------------------
# The controls. LAWS 1 shipped with essentially one (a per-law null) and no way to tell the instrument from
# the finding. Each control below answers a question the first study could not answer about its own numbers.
# --------------------------------------------------------------------------------------------------------
CONTROLS = {
    "neg-shuffle": dict(
        question="If the law is absent by construction, does the pipeline still report it?",
        how="degree-preserving shuffle of every snapshot; every law re-run end to end on the shuffled graphs",
        expect="every law's effect within its SESOI of zero; anything else is an estimator defect",
        laws="LAW-1..LAW-9", why_laws1_needed_it="never run end to end; only per-estimator unit tests existed"),
    "pos-synthetic": dict(
        question="If the law is present at a KNOWN strength, does the pipeline recover it?",
        how="graphs grown with a known attachment exponent / known hub churn, pushed through the real scan path",
        expect="recovered effect within 2 SE of the planted value",
        laws="LAW-1..LAW-5", why_laws1_needed_it="estimators were tested on simulated data, the PIPELINE was not"),
    "coverage-ladder": dict(
        question="Does the number describe the code or the extractor?",
        how="re-run every law with 100 / 75 / 50 / 25% of resolved call edges kept (seeded)",
        expect="pre-registered per-law tolerance; a law outside it is descriptive, not confirmatory",
        laws="LAW-1..LAW-5",
        why_laws1_needed_it="measured once, late, as an amendment: LAW-3 moved 157%, LAW-2 only 10%"),
    "size-adjust": dict(
        question="Is the structural effect just size?",
        how="LOC and function count as registered covariates; the ADJUSTED effect is the primary",
        expect="adjusted effect reported as primary; raw reported beside it",
        laws="LAW-6..LAW-8", why_laws1_needed_it="adjustment removed 60-90% of LAW-7's signal, and was secondary"),
    "test-split": dict(
        question="Is the law about the code or about testing conventions?",
        how="every law re-run with test and vendored files excluded (the scan profile already splits them)",
        expect="same sign and within tolerance; otherwise report both",
        laws="LAW-1..LAW-8",
        why_laws1_needed_it="never run; commons-lang has 363 test files against 264 unit files"),
    "time-split": dict(
        question="Does the law hold in both halves of history, or only across the whole span?",
        how="each law estimated on the first and second half of the snapshot series",
        expect="same sign in both halves; a law that appears only end-to-end is a growth artefact",
        laws="LAW-1..LAW-5", why_laws1_needed_it="never run"),
    "merge-rate": dict(
        question="Is the in-degree tail an artefact of collapsed identities?",
        how="node-merge rate carried as a per-snapshot covariate and reported with LAW-1/3/4",
        expect="effects stable across the observed merge range, or the law is descriptive",
        laws="LAW-1, LAW-3, LAW-4", why_laws1_needed_it="merge rate ran 0-19.2% per snapshot and was never used"),
    "spec-curve": dict(
        question="Is the result a property of the data, or of one defensible choice among many?",
        how="every research parameter in docs/laws2/params.json carries a `grid`; each law is re-estimated "
            "across the grid and the DISTRIBUTION of effects is reported, not one point",
        expect="the sign is stable across the grid; a law that changes sign inside it is descriptive",
        laws="LAW-1..LAW-5",
        why_laws1_needed_it="research choices (5-year hub window, top-1%, x_min rule) sat as bare module "
                            "constants, indistinguishable in the code from a bootstrap count"),
    "as-published": dict(
        question="Does the ORIGINAL claim reproduce under the ORIGINAL method?",
        how="each law run twice: the source paper's estimator, null and figure, beside our registered one",
        expect="both published; the GAP between them is the finding, not a footnote",
        laws="LAW-1..LAW-9",
        why_laws1_needed_it="only the strengthened method was registered, so a null result could always be "
                            "answered with 'you did not do what we did'"),
    "oracle-calibrate": dict(
        question="How far is the compile-free graph from a compiler-grade one, where we can check?",
        how="agreement on languages whose oracle actually runs; carried as stated uncertainty elsewhere",
        expect="per-language agreement published; NOT a gate that removes a language from the study",
        laws="all", why_laws1_needed_it="the oracle was a gate, so 3 of 4 confirmatory languages were removed"),
}

# --------------------------------------------------------------------------------------------------------
# The pipeline. `gate=True` blocks every later phase until it passes. `cmd` is runnable today; `todo` is a
# stage whose code does not exist yet and is named so the frame is honest about what is missing.
# --------------------------------------------------------------------------------------------------------
def S(id, phase, title, why, needs=(), outputs=(), cmd=None, todo=None, gate=False, controls=()):
    return dict(id=id, phase=phase, title=title, why=why, needs=list(needs), outputs=list(outputs),
                cmd=cmd, todo=todo, gate=gate, controls=list(controls))

STAGES = [
    # ---- Phase 0: feasibility. Cheap, reversible, and decides whether the study is possible at all. ----
    S("oracle-screen", 0, "Can each language's oracle run on OLD snapshots?",
      "THE lesson of LAWS 1. Java 0/4 and Python 0/4 because their oracles must build the snapshot. Run this "
      "on a throwaway sample before any frame, draw or seat exists.",
      outputs=["docs/laws2/oracle_availability.json"], gate=True,
      todo="tools/laws2_oracle_screen.py: N throwaway repos per language x 2 boundaries, record run/parse/fail",
      controls=["oracle-calibrate"]),
    S("data-availability", 0, "Does the per-repo side data exist?",
      "LAW-9 was evaluable in 1 of 5 repos because the rest had no sized OSV fix table. Knowable up front.",
      outputs=["docs/laws2/data_availability.json"], gate=True,
      todo="tools/laws2_data_screen.py: OSV/CVE tables, issue labels, build files, per candidate"),
    S("pilot-e2e", 0, "One repo per language, all the way to a law statistic",
      "A pilot that stops before the last step hides the failure that killed LAWS 1.",
      needs=["oracle-screen", "data-availability"], outputs=["docs/laws2/pilot_e2e.json"], gate=True,
      cmd="python tools/laws_run.py --out {study} --repos {pilot_repos} --tag laws2_pilot",
      controls=["neg-shuffle", "pos-synthetic", "coverage-ladder"]),

    # ---- Phase 1: fix the design, using the pilot's own variance. ----
    S("sizing", 1, "Panel size PER LAW from the pilot's between-repo variance",
      "One uniform panel size is wrong: the pilot puts LAW-2 at ~2 repos per language and LAW-3 at ~30.",
      needs=["pilot-e2e"], outputs=["docs/laws2/panel_sizes.json"],
      cmd="python tools/laws2_size.py --run {run} --out docs/laws2/panel_sizes.json --md docs/laws2/panel_sizes.md"),
    S("sesoi", 1, "A smallest effect size worth caring about, per law",
      "Margin 0 plus 100 snapshots makes everything significant: LAW-4 was 'detected' at a Gini gap of 0.026.",
      needs=["pilot-e2e"], outputs=["docs/laws2/sesoi.json"],
      todo="a registered table: law -> SESOI, direction, and the tolerance for the coverage ladder"),
    S("register", 1, "Freeze the registration and hash it",
      "Fewer bars, all of them met once end to end. One editor; the hash is the anti-collision device.",
      needs=["sizing", "sesoi"], outputs=["docs/laws2/registration.md", "docs/laws2/registration.sha256"],
      gate=True, todo="write it, then `sha256sum` it into the manifest"),

    # ---- Phase 2: sampling. Only now is anything irreversible. ----
    S("frame", 2, "Build the sampling frame", "Unchanged from LAWS 1; it worked.",
      needs=["register"], outputs=["docs/laws2/frame/"],
      cmd="python tools/laws_frame.py search --language {lang} --out {study} --confirm"),
    S("exclude", 2, "Apply the registered exclusions before the draw",
      "LAWS 1 Amendment 9: exclusions must precede the draw and be logged.",
      needs=["frame"], outputs=["docs/laws2/panel/"], cmd="python tools/laws_exclude.py --out docs/laws2/panel"),
    S("draw", 2, "Seeded draw, deep enough on the FIRST pass",
      "LAWS 1 went 40 -> 400 -> 2,000 in three amendments. Measured pass rate is 5.8%, so draw depth is "
      "repos_needed / 0.058 with headroom, once.",
      needs=["exclude"], outputs=["docs/laws2/draw/"],
      cmd="python tools/laws_frame.py draw --language {lang} --n {draw_depth} --eligible docs/laws2/panel "
          "--record docs/laws2/draw/{lang}.json"),
    S("seat", 2, "Walk the draw and seat the panel",
      "Licence rule enforced from the start this time; it cost 30% of seats when applied late.",
      needs=["draw"], outputs=["docs/laws2/seating/"],
      cmd="python tools/laws_seat.py --want {want} --language {lang}"),

    # ---- Phase 3: measurement. ----
    S("scan", 3, "Scan every seated repo at every boundary",
      "The engine was never the problem: 18/18 scans succeeded in LAWS 1.",
      needs=["seat"], outputs=["docs/laws2/scans/"],
      todo="tools/laws2_scan.py: quarterly walk per seated repo into one walk DB, resumable"),
    S("profile", 3, "Resolution profile per snapshot",
      "Resolved share, per-step drops and merge rate become INPUTS, not an appendix.",
      needs=["scan"], outputs=["docs/laws2/profiles.json"], controls=["merge-rate"],
      todo="tools/laws2_profile.py: one row per snapshot"),
    S("oracle-agree", 3, "Agreement where the oracle genuinely runs",
      "Calibration, not a gate. C and post-modules Go can carry uncertainty for the rest.",
      needs=["scan"], outputs=["docs/laws2/oracle_agreement.json"], controls=["oracle-calibrate"],
      cmd="python tools/accp_eval.py score --langs {oracle_langs}"),

    # ---- Phase 4: the controls, each a first-class arm. ----
    S("ctrl-negative", 4, "Negative control: shuffled graphs", CONTROLS["neg-shuffle"]["question"],
      needs=["scan"], outputs=["docs/laws2/arms/negative.json"], controls=["neg-shuffle"],
      todo="tools/laws2_arms.py negative: degree-preserving shuffle, then the full law run"),
    S("ctrl-positive", 4, "Positive control: planted effects", CONTROLS["pos-synthetic"]["question"],
      needs=["pilot-e2e"], outputs=["docs/laws2/arms/positive.json"], controls=["pos-synthetic"],
      todo="tools/laws2_arms.py positive: grow graphs with a known exponent, run the real pipeline"),
    S("ctrl-coverage", 4, "Coverage ladder 100/75/50/25", CONTROLS["coverage-ladder"]["question"],
      needs=["scan"], outputs=["docs/laws2/arms/coverage.json"], controls=["coverage-ladder"],
      cmd="python tools/laws_run.py --out {study} --repos {panel_repos} --thin {share} --tag cov{share}"),
    S("ctrl-testsplit", 4, "Tests and vendored code excluded", CONTROLS["test-split"]["question"],
      needs=["scan"], outputs=["docs/laws2/arms/no_tests.json"], controls=["test-split"],
      todo="tools/laws2_arms.py no-tests: drop test/vendored files, re-run"),
    S("ctrl-timesplit", 4, "First half vs second half of history", CONTROLS["time-split"]["question"],
      needs=["scan"], outputs=["docs/laws2/arms/time_split.json"], controls=["time-split"],
      todo="tools/laws2_arms.py time-split"),

    S("ctrl-speccurve", 4, "Specification curve over every research parameter",
      CONTROLS["spec-curve"]["question"],
      needs=["scan"], outputs=["docs/laws2/arms/spec_curve.json"], controls=["spec-curve"],
      todo="tools/laws2_arms.py spec-curve: walk params.json grids, re-estimate, keep the effect distribution"),

    # ---- Phase 5: the laws themselves. ----
    S("laws-main", 5, "Every law on the main arm",
      "Unchanged estimators: 182 tests, never the weak link in LAWS 1.",
      needs=["scan", "profile"], outputs=["docs/laws2/laws_main.json"], controls=["size-adjust"],
      cmd="python tools/laws_run.py --out {study} --repos {panel_repos} --matched-coverage --tag laws2_main"),

    S("arm-as-published", 5, "Every law ALSO under its source paper's own method",
      "A replication that only uses a modernised method can be answered with 'you did not do what we did'. "
      "The gap between the two arms is the most valuable thing this study can report.",
      needs=["scan"], outputs=["docs/laws2/arms/as_published.json"], controls=["as-published"],
      todo="tools/laws2_as_published.py: per law, the source estimator + null + original figure form, "
           "each citing the paper and equation it reproduces"),

    # ---- Phase 6: synthesis, figures, report. ----
    S("synthesis", 6, "Pool per language, refusing to pool below the sized k",
      "LAWS 1 pooled k=2 and returned a 99% interval of -3.76 to 4.00 with a NaN prediction interval.",
      needs=["laws-main", "sizing"], outputs=["docs/laws2/synthesis.json"],
      todo="tools/laws2_synth.py: refuse, loudly, when k < panel_sizes[law]"),
    S("figures", 6, "Every figure that has its inputs",
      "The graphs are declared up front and render themselves as the arms land.",
      needs=["laws-main"], outputs=["docs/laws2/figs/"],
      cmd="python tools/laws_explore.py --run docs/laws2/laws_main.json --figs docs/laws2/figs "
          "--md docs/laws2/tables.md"),
    S("report", 6, "The write-up, with every arm beside the main number",
      "A result is the main number AND what the controls did to it.",
      needs=["synthesis", "figures", "ctrl-negative", "ctrl-coverage", "arm-as-published"],
      outputs=["docs/laws2/report.md"],
      todo="assembled from the arms; no number is published without its control row"),
]

# Figures declared now, built when their inputs exist ("graphs waiting to be built").
FIGURES = [
    dict(id="f1_network_laws", needs="laws-main", shows="each law's effect vs its SESOI, per repo"),
    dict(id="f2_law1_tail", needs="laws-main", shows="what share of nodes each fit calls 'the tail'"),
    dict(id="f3_law3_ceiling", needs="laws-main", shows="observed persistence against its null"),
    dict(id="f4_law5_decay", needs="laws-main", shows="modularity slope per year against zero"),
    dict(id="f5_law7_size", needs="laws-main", shows="effect before and after size adjustment"),
    dict(id="f6_law8_auc", needs="laws-main", shows="AUC with and without network metrics"),
    dict(id="f7_coverage_sensitivity", needs="ctrl-coverage", shows="% change in each law across the ladder"),
    dict(id="f8_negative_control", needs="ctrl-negative", shows="every law on shuffled graphs; must be ~0"),
    dict(id="f9_positive_recovery", needs="ctrl-positive", shows="recovered vs planted effect"),
    dict(id="f10_time_split", needs="ctrl-timesplit", shows="first half vs second half, per law"),
    dict(id="f11_test_split", needs="ctrl-testsplit", shows="with and without test code"),
    dict(id="f12_oracle_agreement", needs="oracle-agree", shows="compile-free vs oracle, where it runs"),
    dict(id="f13_as_published_vs_strengthened", needs="arm-as-published",
         shows="per law, the source paper's own estimate beside ours - the gap IS the result"),
    dict(id="f14_original_figure_form", needs="arm-as-published",
         shows="each paper's own figure redrawn on our data (log-log CCDF, modularity-over-time)"),
    dict(id="f15_specification_curve", needs="ctrl-speccurve",
         shows="every law's effect across all defensible parameter choices, sorted"),
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    if p.is_dir():
        for f in sorted(x for x in p.rglob("*") if x.is_file()):
            h.update(f.relative_to(p).as_posix().encode()); h.update(f.read_bytes())
    else:
        h.update(p.read_bytes())
    return h.hexdigest()


def manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"version": VERSION, "stages": {}}


def save(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=1) + "\n")


def state(stage: dict, m: dict) -> str:
    """done | ready | blocked | missing-code"""
    rec = m["stages"].get(stage["id"])
    if rec and rec.get("status") == "done":
        return "done"
    for n in stage["needs"]:
        if (m["stages"].get(n) or {}).get("status") != "done":
            return "blocked"
    for g in STAGES:
        if g["gate"] and g["phase"] < stage["phase"] and (m["stages"].get(g["id"]) or {}).get("status") != "done":
            return "blocked"
    return "ready" if stage["cmd"] else "missing-code"


def cmd_status(a) -> int:
    m = manifest()
    print(f"LAWS2 run frame ({VERSION}) — {sum(1 for s in STAGES if state(s,m)=='done')}/{len(STAGES)} stages done\n")
    ph = None
    for s in STAGES:
        if s["phase"] != ph:
            ph = s["phase"]
            print(f"\nPHASE {ph}")
        st = state(s, m)
        mark = {"done": "[x]", "ready": "[ ]", "blocked": "[-]", "missing-code": "[!]"}[st]
        gate = " GATE" if s["gate"] else ""
        print(f"  {mark} {s['id']:16} {s['title'][:62]:62}{gate}")
        if st == "missing-code" and a.verbose:
            print(f"        needs building: {s['todo']}")
    print("\n  [x] done   [ ] ready to run   [-] blocked by a need or an unpassed gate   [!] code not written yet")
    print("  `laws2.py status --verbose` names what each [!] stage still needs.")
    return 0


def params() -> dict:
    p = DOCS / "laws2" / "params.json"
    return json.loads(p.read_text()) if p.exists() else {}


def cmd_params(a) -> int:
    d = params()
    if not d:
        raise SystemExit("docs/laws2/params.json is missing")
    r = d.get("research", {})
    print(f"RESEARCH parameters ({len(r)}) — each changes the CLAIM, so each is registered and each is walked\n"
          f"by the specification-curve arm. {sum(len(v['grid']) for v in r.values())} grid cells in total.\n")
    for k, v in r.items():
        print(f"  {k}")
        print(f"    value : {v['value']}")
        print(f"    grid  : {v['grid']}")
        print(f"    laws  : {', '.join(v['laws'])}   ({v['module']})")
        print(f"    why   : {v['why']}\n")
    print(f"PRECISION knobs ({len(d.get('precision', {}))}) — move the error bars, not the claim:")
    for k, v in d.get("precision", {}).items():
        print(f"  {k:14} {str(v['value']):28} {v['why']}")
    print(f"\nGUARDS ({len(d.get('guard', {}))}) — implementation floors; every one that BINDS is counted and published:")
    for k, v in d.get("guard", {}).items():
        print(f"  {k:16} {str(v['value']):12} {v.get('note', '')}")
    return 0


def cmd_controls(a) -> int:
    print("LAWS2 controls — each answers a question LAWS 1 could not answer about its own numbers.\n")
    for k, c in CONTROLS.items():
        stages = [s["id"] for s in STAGES if k in s["controls"]]
        print(f"  {k}  [{', '.join(stages) or 'unassigned'}]")
        print(f"    asks    : {c['question']}")
        print(f"    how     : {c['how']}")
        print(f"    expects : {c['expect']}")
        print(f"    laws    : {c['laws']}")
        print(f"    LAWS 1  : {c['why_laws1_needed_it']}\n")
    return 0


def cmd_checklist(a) -> int:
    L = ["# LAWS2 — the run checklist", "",
         "**Generated from `tools/laws2.py`. Do not hand-edit:** the checklist and the pipeline are the same",
         "object, so they cannot drift apart. Regenerate with `python tools/laws2.py checklist --write`.", "",
         "A stage marked **GATE** blocks every later phase until it passes. `laws2.py run` enforces it; this is",
         "the single rule LAWS 1 most needed, because its irreversible steps ran before its decisive one.", ""]
    m = manifest()
    ph = None
    for s in STAGES:
        if s["phase"] != ph:
            ph = s["phase"]
            L += ["", f"## Phase {ph}", ""]
        st = state(s, m)
        box = "x" if st == "done" else " "
        L.append(f"- [{box}] **{s['id']}** — {s['title']}" + ("  **(GATE)**" if s["gate"] else ""))
        L.append(f"  - why: {s['why']}")
        if s["needs"]:
            L.append(f"  - needs: {', '.join(s['needs'])}")
        if s["controls"]:
            L.append(f"  - controls: {', '.join(s['controls'])}")
        L.append(f"  - outputs: {', '.join(s['outputs'])}")
        L.append(f"  - {'command: `' + s['cmd'] + '`' if s['cmd'] else 'TO BUILD: ' + (s['todo'] or '')}")
    L += ["", "## Controls", "",
          "| control | asks | covers | LAWS 1 |", "|---|---|---|---|"]
    for k, c in CONTROLS.items():
        L.append(f"| `{k}` | {c['question']} | {c['laws']} | {c['why_laws1_needed_it']} |")
    d = params()
    if d:
        L += ["", "## Registered research parameters", "",
              "Each changes the claim, so each is registered with a grid of defensible alternatives that the",
              "`ctrl-speccurve` arm walks. Precision knobs and guards are in `docs/laws2/params.json`.", "",
              "| parameter | value | grid | laws | why it is a research choice |", "|---|---|---|---|---|"]
        for k, v in d.get("research", {}).items():
            L.append(f"| `{k}` | `{v['value']}` | `{v['grid']}` | {', '.join(v['laws'])} | {v['why']} |")
    L += ["", "## Figures declared in advance", "",
          "Each renders as soon as its stage lands, so no figure is invented after seeing the numbers.", "",
          "| figure | needs | shows |", "|---|---|---|"]
    for f in FIGURES:
        L.append(f"| `{f['id']}` | {f['needs']} | {f['shows']} |")
    out = DOCS / "laws2_checklist.md"
    text = "\n".join(L) + "\n"
    if a.write:
        out.write_text(text); print(f"checklist -> {out}")
    else:
        print(text)
    return 0


def cmd_run(a) -> int:
    m = manifest()
    s = next((x for x in STAGES if x["id"] == a.stage), None)
    if not s:
        raise SystemExit(f"no stage {a.stage!r}; `laws2.py status` lists them")
    st = state(s, m)
    if st == "blocked":
        raise SystemExit(f"{s['id']} is blocked: a need or an earlier GATE has not passed. This refusal is the "
                         f"point of the frame -- see `laws2.py status`.")
    if st == "missing-code":
        raise SystemExit(f"{s['id']} has no runnable command yet.\n  TO BUILD: {s['todo']}")
    cmd = s["cmd"]
    for k, v in (a.var or []):
        cmd = cmd.replace("{" + k + "}", v)
    if "{" in cmd:
        raise SystemExit(f"unfilled placeholders in:\n  {cmd}\nPass them: --var name=value")
    print(f"$ {cmd}", flush=True)
    if a.dry_run:
        return 0
    t0 = time.time()
    rc = subprocess.run(cmd, shell=True, cwd=ROOT).returncode
    rec = {"status": "done" if rc == 0 else "failed", "rc": rc, "cmd": cmd,
           "t": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "seconds": round(time.time() - t0, 1), "version": VERSION,
           "outputs": {o: (sha(ROOT / o) if (ROOT / o).exists() else None) for o in s["outputs"]}}
    m["stages"][s["id"]] = rec
    save(m)
    print(f"\n{s['id']}: {rec['status']} in {rec['seconds']}s; manifest updated")
    return rc


def cmd_verify(a) -> int:
    m = manifest()
    drift = []
    for sid, rec in m["stages"].items():
        for o, want in (rec.get("outputs") or {}).items():
            p = ROOT / o
            if not p.exists():
                drift.append(f"{sid}: {o} recorded but MISSING now"); continue
            got = sha(p)
            if want and got != want:
                drift.append(f"{sid}: {o} CHANGED since the stage ran ({want[:12]} -> {got[:12]})")
    if not drift:
        print(f"verify: {len(m['stages'])} recorded stage(s), no drift")
        return 0
    print("VERIFY FAILED — recorded evidence no longer matches what is on disk:")
    for d in drift:
        print(f"  {d}")
    return 1


def cmd_figures(a) -> int:
    m = manifest()
    for f in FIGURES:
        ok = (m["stages"].get(f["needs"]) or {}).get("status") == "done"
        print(f"  [{'x' if ok else ' '}] {f['id']:26} needs {f['needs']:16} — {f['shows']}")
    print("\nFigures whose stage is done are built by `laws2.py run figures`.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="LAWS2 run frame")
    sub = ap.add_subparsers(dest="c", required=True)
    p = sub.add_parser("status"); p.add_argument("--verbose", action="store_true"); p.set_defaults(f=cmd_status)
    p = sub.add_parser("checklist"); p.add_argument("--write", action="store_true"); p.set_defaults(f=cmd_checklist)
    p = sub.add_parser("controls"); p.set_defaults(f=cmd_controls)
    p = sub.add_parser("params"); p.set_defaults(f=cmd_params)
    p = sub.add_parser("figures"); p.set_defaults(f=cmd_figures)
    p = sub.add_parser("verify"); p.set_defaults(f=cmd_verify)
    p = sub.add_parser("run")
    p.add_argument("stage"); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--var", action="append", type=lambda s: tuple(s.split("=", 1)))
    p.set_defaults(f=cmd_run)
    a = ap.parse_args()
    return a.f(a)


if __name__ == "__main__":
    raise SystemExit(main())
