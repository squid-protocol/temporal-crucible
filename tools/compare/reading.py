#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The corrected readings (docs/process/comparison_scorer_part2_spec.md, Revision 2, section 2; Amendment 5
section 4 with the owner's dated note of 2026-11-15, docs/sa3_amendment5_note_reading_draft.md). The first build.

    coded(tests, gate_valid)     -> {name: words}     the reference's Holm block (tools/sa3_score.py:424-444)
    corrected(tests, gate_valid) -> {name: words}     the same rule with the two changes of section 2.1

`tests` is a list of three mappings in the order B, C, D, each with `name`, `p` (the primary statistic's
two-sided p at 95%), `primary` and `residualised` (each "supported", "contradicted", "not detected" or "not
fitted", read at the test's Holm level) and `control` ("supported" or anything else). Holm order is ascending p,
ties kept in the order given. Pure: no input, no output, no randomness.

Also here, for the words printed beside the reference's result (sections 2.2 and 2.3): `applies` (the "a
correction applies" predicate of section 2.4), `beside` (coded, corrected, same / depends), `level_word`
(defect 47's words) and `allreverts_same_repos` (defect 48). And the table for the owner (`table_markdown`),
which `python3 tools/compare/reading.py table --out docs/process/reading_rule_table.md` writes.
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

sys.dont_write_bytecode = True

SUPPORTED, CONTRADICTED, NOT_DETECTED, NOT_FITTED = "supported", "contradicted", "not detected", "not fitted"
READINGS = (SUPPORTED, CONTRADICTED, NOT_DETECTED, NOT_FITTED)
HOLM = "not detected (Holm: an earlier test in the family failed)"
NOT_ROBUST = "not robust to the statistic"
SPECIFIC = "supported, defect-specific"
ACTIVITY = "supported, but tracks activity, not defects"
GATE = "NO FINDING: the placebo gate failed"
WORDS = (SPECIFIC, ACTIVITY, NOT_ROBUST, HOLM, CONTRADICTED, NOT_DETECTED, NOT_FITTED, GATE)
SAME = "same"
DEPENDS = "reading depends on a rule corrected after the estimates were partly seen"


def _check(tests) -> None:
    if len(tests) != 3:
        raise ValueError("three confirmatory tests are expected")
    for t in tests:
        if t["primary"] not in READINGS or t["residualised"] not in READINGS:
            raise ValueError("a reading outside the four the summary can give")


def holm_order(tests) -> list[int]:
    """indices in Holm order: ascending p, ties in the order given (Python's sort is stable)"""
    return sorted(range(len(tests)), key=lambda i: tests[i]["p"])


def _rule(tests, gate_valid: bool, change1: bool, change2: bool) -> dict[str, str]:
    _check(tests)
    out: dict[str, str] = {}
    still = True
    for i in holm_order(tests):
        t = tests[i]
        primary, resid = t["primary"], t["residualised"]
        reading = primary
        if reading == SUPPORTED and not still:
            reading = HOLM
        if (primary not in (SUPPORTED, CONTRADICTED)) if change1 else (primary != SUPPORTED):
            still = False
        coded_nr = reading == SUPPORTED and resid != SUPPORTED
        # change 2 extends the coded condition; owner ruling 2026-11-15: the extension does not act when either side
        # is "not fitted" (no reading), so the coded behaviour stays and change 2 never creates a "supported"
        ext_nr = reading != HOLM and primary != resid and NOT_FITTED not in (primary, resid)
        if (coded_nr or ext_nr) if change2 else coded_nr:
            reading = NOT_ROBUST
        elif reading == SUPPORTED:
            reading = SPECIFIC if t["control"] == SUPPORTED else ACTIVITY
        if not gate_valid:
            reading = GATE
        out[t["name"]] = reading
    return out


def coded(tests, gate_valid: bool) -> dict[str, str]:
    """the reference's Holm block as coded"""
    return _rule(tests, gate_valid, False, False)


def corrected(tests, gate_valid: bool) -> dict[str, str]:
    """the coded rule with change 1 (defect 42: only a primary reading neither supported nor contradicted stops
    the step-down) and change 2 (defect 43: not robust whenever the two statistics read differently, except a
    test already reworded by the Holm step)"""
    return _rule(tests, gate_valid, True, True)


def change1_only(tests, gate_valid: bool) -> dict[str, str]:
    return _rule(tests, gate_valid, True, False)


def change2_only(tests, gate_valid: bool) -> dict[str, str]:
    return _rule(tests, gate_valid, False, True)


def applies(tests) -> dict[str, bool]:
    """section 2.4's predicate: change 1 applies when a test whose primary reads "contradicted" comes, in Holm
    order, before a test whose primary reads "supported"; change 2 when some test's two statistics differ"""
    prim = [tests[i]["primary"] for i in holm_order(tests)]
    c1 = any(prim[i] == CONTRADICTED and SUPPORTED in prim[i + 1:] for i in range(len(prim)))
    c2 = any(t["primary"] != t["residualised"] and "not fitted" not in (t["primary"], t["residualised"])
             and t["primary"] != SUPPORTED for t in tests)                        # where the extension, not the coded rule, acts
    return {"change1": c1, "change2": c2, "any": c1 or c2}


# ============================================================================== beside the reference's result
NAMES = ("struct_branch", "risk_safety_score", "amplified_cascading_flux")      # B, C, D


def tests_from_result(res: dict) -> tuple[list[dict], bool]:
    """the interface's inputs from a result file in the reference's shape (tools/sa3_score.py's `tests` block):
    p from the primary summary (1.0 when it has none, as the reference's `first[p].get("p", 1.0)`); the
    readings at the Holm level as stored; the control's reading (absent: not "supported")"""
    out = []
    for n in NAMES:
        t = res["tests"][n]
        out.append({"name": n, "p": t["bauc"].get("p", 1.0), "primary": t["bauc"]["reading"],
                    "residualised": t["residual"]["reading"],
                    "control": t["minus_control"].get("reading", "")})
    return out, bool(res["valid"])


def beside(res: dict) -> dict[str, dict]:
    """section 2.2: per confirmatory test, the coded reading (the result's own), the corrected reading, and
    "same" or the sentence. The coded reading recomputed here must equal the stored one (else ValueError)"""
    tests, gate = tests_from_result(res)
    c, k = coded(tests, gate), corrected(tests, gate)
    out = {}
    for n in NAMES:
        if c[n] != res["tests"][n]["reading"]:
            raise ValueError(f"{n}: the stored reading is not the coded rule's")
        out[n] = {"coded": c[n], "corrected": k[n], "status": SAME if c[n] == k[n] else DEPENDS}
    return out


def level_word(summary: dict) -> str:
    """defect 47: the words of every summary outside the three confirmatory tests"""
    r = summary.get("reading", NOT_FITTED)
    return {SUPPORTED: "above zero", CONTRADICTED: "below zero"}.get(r, r)


def exploratory_word(summary: dict) -> str:
    r = summary.get("reading", NOT_FITTED)
    return {SUPPORTED: "positive", CONTRADICTED: "negative"}.get(r, r)


def allreverts_same_repos(res: dict, marg: list[dict], summarize, corrected_words: dict[str, str]) -> dict:
    """defect 48: per confirmatory test, the HP_allreverts summary at the test's Holm level over the drawn repos
    whose marginals rows clear BOTH the HP and the HP_allreverts floors; the number of repos; and the sentence
    exactly when that summary reads "above zero" and the corrected reading does not begin with "supported".
    `summarize` is the reference's summary rule (the comparison scorer's transcription)."""
    keep = {r["repo"] for r in marg if r["status"] == "ok" and r["drawn"] and r["HP"]["clears_floor"]
            and r["HP_allreverts"]["clears_floor"]}
    out = {}
    for n in NAMES:
        level = res["tests"][n]["holm_level"]
        vals = {}
        for repo, rec in res["repos"].items():
            c = rec["outcomes"].get("HP_allreverts", {}).get(n, {})
            if repo in keep and c.get("status") == "ok":
                vals[repo] = c["bauc"]
        s = summarize(vals, level)
        word = level_word(s)
        out[n] = {"repos_where_both_clear": len(keep), "n": s["n"], "mean": s.get("mean"), "ci": s.get("ci"),
                  "word": word,
                  "tracks_reverts": word == "above zero" and not corrected_words[n].startswith("supported")}
        if out[n]["tracks_reverts"]:
            out[n]["sentence"] = "tracks reverted changes, not fixes"
    return out


# ================================================================================= the enumeration and table
def dense_orders(k: int = 3) -> list[tuple[int, ...]]:
    """every weak order of k p-values (ties included) as dense ranks: 13 for k = 3"""
    return [r for r in itertools.product(range(k), repeat=k) if set(r) == set(range(max(r) + 1))]


def make_tests(states, ranks=(0, 1, 2)) -> list[dict]:
    """states: three (primary, residualised, control) in the order B, C, D; ranks: their p ranks"""
    return [{"name": n, "p": 0.01 * (rk + 1), "primary": a, "residualised": b, "control": c}
            for n, (a, b, c), rk in zip(NAMES, states, ranks)]


def counts_729() -> dict:
    """section 2.1's counts: three tests in Holm order, primary and residualised each supported, contradicted or
    not detected, control supported, gate passed. "differ": the three readings are not all the same;
    "more": the rule gives more readings beginning with "supported" than the coded rule"""
    S3 = (SUPPORTED, CONTRADICTED, NOT_DETECTED)
    out = {k: {"differ": 0, "more": 0, "fewer": 0} for k in ("change1", "change2", "both")}
    out["total"] = 0
    for combo in itertools.product(itertools.product(S3, S3, (SUPPORTED,)), repeat=3):
        t = make_tests(combo)
        out["total"] += 1
        c = coded(t, True)
        nc = sum(v.startswith("supported") for v in c.values())
        for k, f in (("change1", change1_only), ("change2", change2_only), ("both", corrected)):
            r = f(t, True)
            nr = sum(v.startswith("supported") for v in r.values())
            out[k]["differ"] += r != c
            out[k]["more"] += nr > nc
            out[k]["fewer"] += nr < nc
    null = make_tests([(NOT_DETECTED, NOT_DETECTED, SUPPORTED)] * 3)
    out["plain_null_same"] = coded(null, True) == corrected(null, True)
    return out


CODE = {SUPPORTED: "S", CONTRADICTED: "C", NOT_DETECTED: "N", NOT_FITTED: "F"}
WORD_CODE = {SPECIFIC: "DS", ACTIVITY: "TA", NOT_ROBUST: "NR", HOLM: "H", CONTRADICTED: "C", NOT_DETECTED: "N",
             NOT_FITTED: "F", GATE: "G"}


def table_rows():
    """every combination of the three tests' (primary, residualised, control) in Holm order, gate passed then
    failed: (states, gate, coded words, corrected words) in Holm order"""
    per = list(itertools.product(READINGS, READINGS, (SUPPORTED, "other")))
    for gate in (True, False):
        for combo in itertools.product(per, repeat=3):
            t = make_tests(combo)
            c, k = coded(t, gate), corrected(t, gate)
            yield combo, gate, [c[n] for n in NAMES], [k[n] for n in NAMES]


def table_markdown() -> str:
    rows = list(table_rows())
    differ = sum(c != k for _s, _g, c, k in rows)
    n = len(rows)
    by_word: dict[tuple[str, str], int] = {}
    for _s, _g, c, k in rows:
        for a, b in zip(c, k):
            if a != b:
                by_word[(a, b)] = by_word.get((a, b), 0) + 1
    cnt = counts_729()
    lines = [
        "# The reading rule: coded against corrected, every combination (generated)",
        "",
        "Generated by `python3 tools/compare/reading.py table --out docs/process/reading_rule_table.md` from",
        "`tools/compare/reading.py` (docs/process/comparison_scorer_part2_spec.md, Revision 2, section 2.4). Do not",
        "edit: `tests/test_compare_part2.py` regenerates it and compares. Nothing here reads data.",
        "",
        "**What a row is.** The three confirmatory tests taken in Holm order (positions 1, 2, 3: ascending p of the",
        "primary statistic, ties in the order B, C, D). For each: the primary statistic's reading at its Holm level,",
        "the residualised statistic's reading at the same level, and whether the matched control reads \"supported\";",
        "then whether the placebo gate passed. The coded words (`tools/sa3_score.py`'s Holm block, as it runs) and",
        "the corrected words (the coded rule with the two changes of the owner's note of 2026-11-15) follow, one per",
        "position. Which of B, C, D sits at each position does not change the words; only the order does.",
        "",
        f"**{n:,} rows** (4 x 4 x 2 states per test, cubed, times the gate). **{differ:,} differ** (marked `*`), all",
        f"with the gate passed; with the gate failed every reading is the gate sentence under both rules.",
        "",
        "Codes. Readings: `S` supported, `C` contradicted, `N` not detected, `F` not fitted; control `+` supported,",
        "`-` anything else. Words: `DS` \"supported, defect-specific\", `TA` \"supported, but tracks activity, not",
        "defects\", `NR` \"not robust to the statistic\", `H` \"not detected (Holm: an earlier test in the family",
        "failed)\", `C` \"contradicted\", `N` \"not detected\", `F` \"not fitted\", `G` \"NO FINDING: the placebo gate",
        "failed\". A cell `S N +` is primary S, residualised N, control supported.",
        "",
        "Section 2.1's counts, reproduced by `counts_729` (three readings per statistic, control supported, gate",
        f"passed: {cnt['total']} combinations):",
        "",
        "| | readings differ | more \"supported\" | fewer \"supported\" |",
        "|---|---|---|---|",
        f"| change 1 alone | {cnt['change1']['differ']} | {cnt['change1']['more']} | {cnt['change1']['fewer']} |",
        f"| change 2 alone | {cnt['change2']['differ']} | {cnt['change2']['more']} | {cnt['change2']['fewer']} |",
        f"| both | {cnt['both']['differ']} | {cnt['both']['more']} | {cnt['both']['fewer']} |",
        "",
        f"The plain null (every statistic not detected) reads the same: {'yes' if cnt['plain_null_same'] else 'NO'}.",
        "",
        "Test readings that change, coded -> corrected, counted over the rows above (a row can change more than one):",
        "",
        "| coded | corrected | tests |",
        "|---|---|---|",
    ]
    for (a, b), v in sorted(by_word.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {a} | {b} | {v:,} |")
    lines += ["", "| row | position 1 | position 2 | position 3 | gate | coded | corrected | differs |",
              "|---|---|---|---|---|---|---|---|"]
    for i, (states, gate, c, k) in enumerate(rows, 1):
        cells = [f"{CODE[a]} {CODE[b]} {'+' if s == SUPPORTED else '-'}" for a, b, s in states]
        lines.append(f"| {i} | {cells[0]} | {cells[1]} | {cells[2]} | {'pass' if gate else 'fail'} | "
                     f"{' '.join(WORD_CODE[w] for w in c)} | {' '.join(WORD_CODE[w] for w in k)} | "
                     f"{'*' if c != k else ''} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("table", "counts"))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.what == "counts":
        print(counts_729())
        return 0
    text = table_markdown()
    if a.out:
        Path(a.out).write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
