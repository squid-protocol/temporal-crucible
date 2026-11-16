#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""report.md of the scoring job (docs/process/scoring_step_spec.md section 4), rendered from VALIDATED values
(tools/scoring/schema.py, score_sa3.REPORT) and the fixed texts of tools/scoring/texts.py only. Three committed
texts are carried in as they are at the pinned commit: the deviation table (its last column filled from this run
by fixed words), and variants.py's fixed sentences for the variants that are not scored."""
from __future__ import annotations

import datetime as dt
import importlib.util
try:
    from zoneinfo import ZoneInfo
    EASTERN = ZoneInfo("America/New_York")
except Exception:                                                # noqa: BLE001  no time-zone data: UTC only
    EASTERN = None
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def _texts():
    key = "tools_scoring_texts"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, HERE / "texts.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


TX = _texts()
NAMES = TX.TEST_NAMES
PART_LABEL = {"labels": "label tables and the label-side input check (step 11)",
              "compare": "the comparison scorer and the cell map (step 12)",
              "readings": "the corrected readings (step 13)", "named": "PU_named_streams (step 13)",
              "hv_prepare": "the harvest copies of the two harvest variants (step 13)",
              "PU_tracker_keys_case_sensitive": "PU_tracker_keys_case_sensitive (step 13)",
              "PU_late_revert_ticket_dropped": "PU_late_revert_ticket_dropped (step 13)"}


def day(t: int) -> str:
    """UTC, and US Eastern beside it (the owner reads Eastern; build review, minor 11)"""
    u = dt.datetime.fromtimestamp(t, dt.timezone.utc)
    if EASTERN is None:
        return f"{u:%Y-%m-%d %H:%M} UTC"
    e = u.astimezone(EASTERN)
    return f"{u:%Y-%m-%d %H:%M} UTC ({e:%Y-%m-%d} {e:%I:%M %p}".replace(" 0", " ", 1) + f" {e.tzname()})"


def f4(v) -> str:
    return "n/a" if v is None else f"{v:+.4f}"


def interval(ci) -> str:
    return "n/a" if ci is None else f"[{ci[0]:+.4f}, {ci[1]:+.4f}]"


def pct(level: float) -> str:
    return f"{100 * level:.2f}%"


def later_word(vals: dict) -> str:
    return "" if vals["later"] is None else " (" + TX.PARAGRAPHS["later"].format(date=day(vals["later"])) + ")"


# ============================================================================================ the deviation table
def fill_deviation(text: str, vals: dict) -> str:
    """the committed table with every `{{run:...}}` token replaced by fixed words from this run's values; a token
    this function does not know reads "not filled by the job" """
    tests, ap, allr = vals["tests"], vals["applies"], vals["allreverts"]
    variants = {v["name"]: v for v in vals["variants"]}

    def readings() -> str:
        if not tests:
            return "not read (the result's shape is unexpected)"
        if any(t["status"] is None for t in tests.values()):
            p = vals["parts"]["readings"]
            return f"not computed (failed: {p['code']})"
        differ = [NAMES[n] for n, t in tests.items() if t["status"] != "same"]
        return "differs for " + ", ".join(differ) if differ else "same for SA3-B, SA3-C and SA3-D"

    def change(k: str) -> str:
        if ap is None:
            return f"not computed (failed: {vals['parts']['readings']['code']})"
        return "applies in this run" if ap[k] else "does not apply in this run"

    def allreverts() -> str:
        if allr is None:
            return f"not computed (failed: {vals['parts']['readings']['code']})"
        hit = [NAMES[n] for n, v in allr.items() if v["tracks_reverts"]]
        return ("the sentence \"tracks reverted changes, not fixes\" applies to " + ", ".join(hit)) if hit else \
            "the sentence does not apply"

    def variant(name: str) -> str:
        v = variants.get(name)
        if v is None:
            return "not filled by the job"
        if v["status"] != "ok":
            return f"failed: {v['code']}"
        d = sum(1 for r in v["block"]["rows"] if r["difference"]["n"] != 0 or
                (r["difference"]["mean"] is not None and r["difference"]["mean"] != 0.0))
        return f"differs from its baseline in {d} of {len(v['block']['rows'])} rows" if d else \
            f"equal to its baseline in all {len(v['block']['rows'])} rows"

    fill = {"readings": readings, "change1": lambda: change("change1"), "change2": lambda: change("change2"),
            "allreverts": allreverts}

    def sub(m):
        key = m.group(1)
        if key.startswith("variant:"):
            return variant(key[8:])
        return fill[key]() if key in fill else "not filled by the job"

    return re.sub(r"\{\{run:([A-Za-z0-9_:]+)\}\}", sub, text)


# ===================================================================================================== render
def render(vals: dict, deviation: str, variant_table: list) -> str:
    L = []
    label = TX.LABEL + (f" {TX.LABEL_ADDITION[0].upper()}{TX.LABEL_ADDITION[1:]}." if vals["label_addition"] else "")
    L += [f"**{label}**", ""]
    if vals["score_stage"] != "none":
        L += [(TX.RESULT_LINES["stage_modules"] if vals["score_stage"] == "modules_differ"
               else TX.RESULT_LINES["stage_failed"].format(code=vals["score_stage"])).capitalize() + ".", ""]
    if vals["result_shape"] != "expected":
        L += [f"result_shape: unexpected, at {vals['result_shape_at']}. The result is published byte for byte; "
              f"{TX.STOP_CODES['result_shape_unexpected']}.", ""]
    for r in vals["rerun_reasons"]:
        L += [f"A second start of the reference score was made with --rerun, reason recorded in the ledger: \"{r}\".",
              ""]
    if not vals["tests"]:
        L.append("- SA3-B, SA3-C, SA3-D: not read from the result (its shape is unexpected); see sa3_result.json.")
    for n, t in vals["tests"].items():
        cor = t["corrected"] if t["corrected"] is not None else f"not computed (failed: {vals['parts']['readings']['code']})"
        st = t["status"] if t["status"] is not None else "not computed"
        L.append(f"- **{NAMES[n]}** ({n}): mean {f4(t['mean'])}, {pct(t['holm_level'])} interval "
                 f"{interval(t['ci'])}, n {t['n']}. As coded: **{t['coded']}**. As corrected: {cor}"
                 f"{later_word(vals) if t['corrected'] is not None else ''}. {st}.")
    e = vals["exploratory"]
    if e is not None:
        L.append(f"- **SA3-A** (in_degree), exploratory: mean {f4(e['mean'])}, 95% interval {interval(e['ci'])}, "
                 f"n {e['n']}; reading: {e['reading']}.")
    gw = "not read (the result's shape is unexpected)" if vals["gate_valid"] is None else TX.GATE_WORDS[vals["gate_valid"]]
    L.append(f"- Placebo gate: {gw}. {TX.SENTENCES['gate']}")
    L.append("- The check: " + check_line(vals))
    for s in vals["sentences"]:
        if s != "gate":
            L.append(f"- {TX.sentence(s, vals['check_code'])}")
    L.append("- Attempts and resumes: " + attempts_line(vals))
    L += ["", "# SA3 — the confirmatory result", "",
          f"Target: {vals['target']}. Written {day(vals['made'])} by tools/scoring/score_sa3.py ({vals['mode']}). "
          "The result is `sa3_result.json` beside this file, the reference's own file byte for byte.", "",
          TX.PARAGRAPHS["raw_words"], "", TX.PARAGRAPHS["what_seen"], "", TX.PARAGRAPHS["recovery"], "",
          TX.PARAGRAPHS["power"], "", TX.PARAGRAPHS["counts"], "", TX.PARAGRAPHS["blind"], ""]
    # ---- parts
    L += ["## The parts after the score", "", "| part | status | code |", "|---|---|---|"]
    for k, p in vals["parts"].items():
        L.append(f"| {PART_LABEL[k]} | {'done' if p['status'] == 'ok' else 'failed'}{later_word(vals)} | {p['code']} |")
    L.append("")
    if "part_failed" in vals["sentences"]:
        L += [TX.SENTENCES["part_failed"], ""]
    # ---- the check
    L += ["## The check (Amendment 5 section 9)", "", TX.PARAGRAPHS["match"], ""]
    cm = vals["cellmap"]
    if cm["map"] is None:
        L += [f"Cell map: failed: {cm['code']}.", ""]
    else:
        m = cm["map"]
        L += [f"Cell map{later_word(vals)}: {m['cells']} cells; " + ", ".join(
            f"{c} {v['equal']} equal / {v['not_equal']} not equal" for c, v in m["classes"].items())
            + (". ALL EQUAL." if m["all_equal"] else ". NOT ALL EQUAL."), ""]
        if m["first_R"]:
            L += [f"First not-equal R cell at {' / '.join(m['first_R'])}; R cells after it: "
                  f"{m['R_after_first']['equal']} equal, {m['R_after_first']['not_equal']} not equal.", ""]
        L += ["| repo | W equal / not | D equal / not | R equal / not |", "|---|---|---|---|"]
        for r, v in m["per_repo"].items():
            L.append(f"| {r} | " + " | ".join(f"{v[c]['equal']} / {v[c]['not_equal']}" for c in "WDR") + " |")
        L.append("")
    lc = vals["label_check"]
    if lc["check"] is None:
        L += [f"Label-side input check: failed: {lc['code']}.", ""]
    else:
        c = lc["check"]
        L += [f"Label-side input check{later_word(vals)}: {c['repos_checked']} repos; "
              + ("all equal." if c["all_equal"] else "NOT all equal."), "",
              "| repo | code | comparable | " + " | ".join(next(iter(c["repos"].values()))["items"]) + " |"
              if c["repos"] else "", "|---|---|---|" + "---|" * len(next(iter(c["repos"].values()))["items"])
              if c["repos"] else ""]
        word = {True: "equal", False: "not equal", None: "not compared"}
        for r, v in c["repos"].items():
            L.append(f"| {r} | {v['code']} | {word[v['comparable']] if v['comparable'] is not None else 'n/a'} | "
                     + " | ".join(word[x] for x in v["items"].values()) + " |")
        L.append("")
    L += ["The predictor side of the input check was run before scoring, on the same tables (section 2, step 2); "
          "its verdict and the tables' hashes are in the pinned commit (docs/sa3_predictor_check.json), and step 5 "
          "checked the tables against them.", ""]
    # ---- readings beside
    L += ["## The readings, as coded and as corrected (Amendment 5 section 4)", ""]
    if vals["allreverts"] is not None:
        L += ["The all-reverts comparison on one named repo set (defect 48), at each test's Holm level:", "",
              "| test | repos where both floors clear | n | mean | interval | words |", "|---|---:|---:|---:|---|---|"]
        for n, v in vals["allreverts"].items():
            L.append(f"| {NAMES[n]} | {v['repos_where_both_clear']} | {v['n']} | {f4(v['mean'])} | "
                     f"{interval(v['ci'])} | {v['word']}"
                     + ("; tracks reverted changes, not fixes" if v["tracks_reverts"] else "") + " |")
        L.append("")
    # ---- part 2
    L += ["## The sensitivities (Amendment 5 section 6; part 2 of the comparison scorer)", "",
          TX.PARAGRAPHS["variants_intro"], ""]
    by = {v["name"]: v for v in vals["variants"]}
    for name, how, text in variant_table:
        if how != "scored":
            L += [f"**{name}**: {text}", ""]
            continue
        v = by.get(name)
        if v is None or v["status"] != "ok":
            L += [f"**{name}**: failed: {v['code'] if v else 'not_run'}.", ""]
            continue
        b = v["block"]
        L += [f"**{name}**{later_word(vals)} (difference from {b['baseline']})", ""]
        if v["inputs"] is not None:
            changed = {r: x for r, x in v["inputs"].items() if x["deleted_rows"]}
            if not changed:
                L += ["Inputs: no row deleted in any repo; every frozen file stands; equal to PU_named_streams.", ""]
            for r, x in changed.items():
                L.append(f"- input {r}: {x['deleted_rows']} rows deleted; {x['reason']}")
            if changed:
                L.append("")
        L += ["| outcome | predictor | n | mean | 95% interval | reads | d n | d mean | d lo | d hi |",
              "|---|---|---:|---:|---|---|---:|---:|---:|---:|"]
        for r in b["rows"]:
            d = r["difference"]
            L.append(f"| {r['outcome']} | {r['predictor']} | {r['n']} | {f4(r['mean'])} | {interval(r['ci'])} | "
                     f"{r['word']} | {d['n']:+d} | {e2(d['mean'])} | {e2(d['lo'])} | {e2(d['hi'])} |")
        L.append("")
    # ---- deviation table
    L += ["## The deviation table (Amendment 5 section 8)", "",
          "Committed at the pinned commit; only its last column is filled from this run.", "",
          fill_deviation(deviation, vals).rstrip(), ""]
    # ---- provenance
    pv = vals["provenance"]
    L += ["## Provenance", "",
          f"- Result's commit: {pv['commit']} (tag {pv['tag']}); the code of this report's parts: {pv['code_commit']}; "
          f"tree of tools/ at it: {pv['tools_tree']}.",
          f"- Run-2's seal: SHA-256 {pv['seal_sha256']}.",
          f"- Receipt: sa3_result.json sha256 {pv['result_sha256']} commit {pv['commit']} seal sha256 "
          f"{pv['seal_sha256']}.",
          f"- The reference lock: sealed at {pv['lock']['sealed_at_commit']}; "
          + "; ".join(f"{k} {v}" for k, v in pv["lock"]["files"].items()) + ".",
          f"- The clone's status after the score: {'exactly the lock and the result' if pv['after_score_status_ok'] else 'NOT exactly the lock and the result'}.",
          f"- The deviation table's SHA-256: {pv['deviation_table_sha256']}.", "",
          "The ledger (a copy is `ledger.jsonl`):", ""]
    for e in vals["ledger"]:
        L.append(f"- {day(e['time'])}: {e['event']}" + (f", code {e['code']}" if e["code"] != "none" else "")
                 + (f", result sha256 {e['result_sha256']}" if e["result_sha256"] else "")
                 + (f", rerun reason \"{e['rerun_reason']}\"" if e["rerun_reason"] else "") + f", commit {e['commit']}")
    L += ["", "Every module each stage loaded (SHA-256; each equal to `git ls-tree` of the commit):", ""]
    for st, mods in pv["modules"].items():
        L.append(f"- {st}: " + ", ".join(f"{p} {h}" for p, h in mods.items()))
    L += ["", "Do not paste anything from the protected directory into a session.", ""]
    return "\n".join(L)


def e2(v) -> str:
    return "-" if v is None else f"{v:+.2e}"


def check_line(vals: dict) -> str:
    cm, lc = vals["cellmap"], vals["label_check"]
    a = f"cell map failed: {cm['code']}" if cm["map"] is None else \
        ("cell map all equal" if cm["map"]["all_equal"] else
         "cell map NOT all equal (" + ", ".join(f"{c} {v['not_equal']}" for c, v in cm["map"]["classes"].items())
         + " not equal)")
    b = f"label-side input check failed: {lc['code']}" if lc["check"] is None else \
        ("label-side input check all equal" if lc["check"]["all_equal"] else "label-side input check NOT all equal")
    return f"{a}; {b}{later_word(vals)}."


def attempts_line(vals: dict) -> str:
    out = []
    for a in vals["attempts"]:
        if a["event"] == "attempt_started":
            out.append(f"{a['mode']} started {day(a['time'])}")
        else:
            out.append(f"ended at step {a['step']}" + (f" ({a['code']})" if a["code"] != "none" else ""))
    return "; ".join(out) + "." if out else "none recorded."


def render_stopped(vals: dict) -> str:
    """a stop's short record; the sentences follow what the ledger held at the stop (build review M4)"""
    L = [f"STOPPED at step {vals['step']} ({TX.STEPS.get(vals['step'], '')}): {vals['code']}", "",
         TX.STOP_CODES.get(vals["code"], ""), ""]
    if vals["ledger_state"] == "empty":
        s = "run2_placebo" if (vals["step"] == 1 and vals["code"] == "run2_placebo") else \
            "rehearsal" if vals["step"] == 6 else "before_score" if vals["step"] <= 8 else None
        if s:
            L += [TX.SENTENCES[s], ""]
    L += [TX.LEDGER_STATE[vals["ledger_state"]], ""]
    L += [f"Target: {vals['target']}. Written {day(vals['made'])}.", "",
          "Attempts and resumes: " + attempts_line(vals), "",
          "Do not paste anything from the protected directory into a session.", ""]
    return "\n".join(L)
