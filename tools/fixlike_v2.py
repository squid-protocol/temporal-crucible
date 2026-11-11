#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""FIXLIKE v2 (amendment 2): drop non-behavioural "fixes" from xc_harvest's keyword gate.

The v1 gate asks only whether a fix WORD is present, so it keeps every commit whose message
says "fix" regardless of what was fixed. docs/otherfix_audit.md measured the cost: `other-fix`
precision is 0.73 pooled on C but **0.38 outside C**, because Go, Java, Python and Rust projects
say "fix" for lint, mypy, javadoc, formatting and typos far more than C projects do.

v2 keeps v1's fix words and adds two exclusions:

  A. PATHS - drop a commit whose touched in-scope files are ALL under test, doc, example or
     benchmark trees. This is language-general and far more reliable than parsing intent out of
     a subject line.
  B. SUBJECT - drop a commit whose subject matches a narrow, high-precision non-behavioural
     marker: a conventional-commit docs/chore/style/test/build type, a named linter or type
     checker, javadoc/doxygen/docstring, typo/spelling/grammar, whitespace/formatting, a
     compiler- or build-warning-only change, or changelog/release-note edits.

Rule A alone cannot carry this: in Java, Python and Rust the documentation lives INSIDE the
source file (javadoc, docstrings, doc comments), so a doc-only fix is indistinguishable from a
code change by path. That is a large part of why non-C precision was so much worse.

`latent` is exempt: it comes from a curated security-fix event list, not the keyword gate.

Non-destructive: reads events/<repo>_xc.json and writes events/<repo>_xc2.json, so v1 results
stay reproducible and the two can be compared directly.

    python tools/fixlike_v2.py --repos libgit2,postgres,... --report docs/fixlike_v2_impact.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT = "libgit2,postgres,libxml2,redis,prometheus,commons-lang,sphinx,ripgrep"

# ---- A. path exclusion: test / doc / example / benchmark trees ----------------------------------
TEST_DOC_PATH = re.compile(
    r"(^|/)(tests?|testing|test_fixtures|fixtures|spec|specs|docs?|doc_src|documentation|"
    r"examples?|samples?|demos?|bench|benches|benchmarks?)(/|$)"
    r"|(^|/)test_[^/]*$|[^/]*_test\.[a-z]+$|[^/]*Test(s|Case)?\.java$|[^/]*_spec\.[a-z]+$"
    r"|(^|/)conftest\.py$", re.I)

# ---- B. subject exclusion: narrow, high-precision non-behavioural markers -----------------------
NONFIX_SUBJ = re.compile(
    # conventional-commit types that are never a behavioural fix
    r"^\s*(?:\[[^\]]*\]\s*)?(?:docs?|doc|documentation|javadoc|chore|style|ci|build|deps|"
    r"dependencies|test|tests|refactor|perf|typo|lint)\s*(?:\([^)]*\))?\s*:"
    r"|^\s*\[(?:javadoc|docs?|build|ci|chore|style|lint|imp)\]"
    # prose and naming hygiene
    r"|\btypos?\b|\bspell(?:ing)?\b|\bspeling\b|\bgrammar\b|\bwording\b"
    r"|\bjavadoc\b|\bdoxygen\b|\bdocstrings?\b|\b@since\b|\bchangelog\b|\bchanges\.xml\b"
    r"|\brelease notes?\b|\bnews file\b"
    r"|\bwhite ?space\b|\btrailing (?:space|whitespace)\b|\bindentation\b|\breformat\w*\b"
    r"|\bfix(?:es|ed)? (?:the )?(?:formatting|comment|comments|javadoc|docs?|documentation|"
    r"doc comment|internal name|@\w+ tag)\b"
    # linters, formatters, type checkers, static analysers
    r"|\blints?\b|\blinter\b|\bclippy\b|\bgocritic\b|\bcheckstyle\b|\bmypy\b|\bflake8\b|\bpylint\b"
    r"|\brustfmt\b|\bgofmt\b|\bclang-format\b|\bspotbugs\b|\bsonar\w*\b|\bpmd\b"
    r"|\bmypy violations?\b|\bfix(?:es|ed)? annotations?\b"
    # warning-only and build-only changes
    r"|\b(?:compiler|build|compile|gcc|clang|msvc|xcode|varargs|lint)[ -]warnings?\b"
    r"|\bwarnings?\b(?=[^.]*\b(?:silence|suppress|avoid|quiet)\w*\b)"
    r"|\bunused (?:variable|import|include|parameter|function)\b"
    r"|\bdeprecated types?\b|\bcompile error\b|\bbuild (?:error|failure|break\w*)\b"
    # test-suite maintenance named in the subject
    r"|\b(?:unit )?tests?\b(?=[^.]*\b(?:suite|flaky|coverage)\b)|\btest suite\b|\bflaky\b"
    r"|\bbenchmarks?\b|\bbroken test\b|\bfix(?:es|ed)? tests?\b",
    re.I)

# ---- extra non-behavioural families found on the development set --------------------------------
NONFIX_SUBJ2 = re.compile(
    # refactors, cleanups, performance
    r"\brewrite\b|\brewrit\w+\b|\brework\w*\b|\brefactor\w*\b|\bclean[ -]?ups?\b|\bcleaning\b"
    r"|\btidy\w*\b|\bsimplif\w+\b|\boptimiz\w+\b|\boptimis\w+\b|\bdeduplicat\w+\b"
    r"|\breadability\b|\bcoding style\b|\bstyle issues?\b|\bmove to use\b|\befficient\b"
    r"|\breduce (?:alignment|padding|memory|allocation)\w*\b"
    # prose and annotations the first pass missed
    r"|\bdocumentation\b|\bdoc improvement\b|\bhelp text\b|\bdoc_cfg\b|\bdoc_auto_cfg\b"
    r"|\blog messages?\b|\blogs? fixed\b|\btweak docs?\b"
    # build / portability / includes
    r"|\bmissing include\b|\badd #include\b|\bportability\b|\bfix(?:es|ed)? build\b"
    r"|\bbuild for\b|\bbad merge\b"
    # warning-avoidance with the verb BEFORE the noun ("avoid a warning ...")
    r"|\b(?:silence|suppress|avoid|quiet)\w*\b[^.]{0,30}\bwarnings?\b"
    # test additions named in the subject
    r"|\badd(?:s|ed|ing)? (?:a )?tests?\b|\btests? for\b",
    re.I)
# A code comment being edited, as opposed to comments as parsed CONTENT (an HTML/XML parser fixing
# "EOF handling in comments" is a real fix, so operations on comments are exempted).
COMMENT_EDIT = re.compile(r"\bcomments?\b", re.I)
COMMENT_OP = re.compile(r"\b(?:handl\w+|pars\w+|process\w+|strip\w*|output\w*|serializ\w+"
                        r"|incomplete|nested|unclosed|escap\w+)\b", re.I)

EXEMPT_CLASS = "latent"


# v1's gate matched the fix word anywhere in subject OR body, which keeps plain feature commits
# whose body happens to say "fixes #123". Rule C requires the fix word in the SUBJECT. It is the
# single biggest precision lever and the only one with a real recall cost, so it is separable.
FIXWORD = re.compile(r"\b(fix(es|ed)?|bug|broke(n)?|break(s|age)?|regress\w*|crash\w*|wrong|incorrect"
                     r"|segfault|leak|overflow|oops|restore)\b", re.I)


def drop_reason(ev, rules="v3c") -> str | None:
    if ev.get("class") == EXEMPT_CLASS:
        return None
    subj = ev.get("subject", "")
    files = ev.get("c_files") or []
    if files and all(TEST_DOC_PATH.search(f) for f in files):
        return "A:test/doc path only"
    if NONFIX_SUBJ.search(subj):
        return "B:non-behavioural subject"
    if rules in ("v3", "v3c"):
        if NONFIX_SUBJ2.search(subj):
            return "B2:refactor/prose/build subject"
        if COMMENT_EDIT.search(subj) and not COMMENT_OP.search(subj):
            return "B3:edits a code comment"
    if rules == "v3c" and not FIXWORD.search(subj):
        return "C:no fix word in the subject"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default=DEFAULT)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--rules", default="v3c", choices=("v2", "v3", "v3c"))
    a = ap.parse_args()

    rows, lines = [], []
    for r in a.repos.split(","):
        p = REPO_ROOT / "events" / f"{r}_xc.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        kept, dropped = [], Counter()
        per_class_before, per_class_after = Counter(), Counter()
        for ev in d["events"]:
            per_class_before[ev.get("class")] += 1
            why = drop_reason(ev, a.rules)
            if why:
                dropped[(ev.get("class"), why.split(":")[0])] += 1
            else:
                kept.append(ev)
                per_class_after[ev.get("class")] += 1
        d2 = dict(d)
        d2["events"] = kept
        d2["rules"] = f"docs/xc_hypotheses.md + FIXLIKE {a.rules} (amendment 2, 2026-11-11); see docs/otherfix_audit.md"
        d2["v2_dropped"] = {f"{c}|{k}": n for (c, k), n in sorted(dropped.items(), key=lambda x: str(x[0]))}
        (REPO_ROOT / "events" / f"{r}_xc2.json").write_text(json.dumps(d2, indent=1))
        ob, oa = per_class_before["other-fix"], per_class_after["other-fix"]
        rows.append((r, len(d["events"]), len(kept), ob, oa,
                     per_class_before["regression"], per_class_after["regression"],
                     per_class_before["extrinsic"], per_class_after["extrinsic"]))
        lines.append((r, dropped))

    hdr = f"{'repo':14s} {'events':>14s} {'other-fix':>14s} {'regression':>13s} {'extrinsic':>13s}"
    print(hdr)
    for r, b, k, ob, oa, rb, ra, eb, ea in rows:
        print(f"{r:14s} {b:6d}->{k:6d} {ob:6d}->{oa:6d} {rb:5d}->{ra:5d} {eb:5d}->{ea:5d}")
    tb, tk = sum(x[1] for x in rows), sum(x[2] for x in rows)
    tob, toa = sum(x[3] for x in rows), sum(x[4] for x in rows)
    print(f"\ntotal events {tb} -> {tk}  ({100*(tb-tk)/tb:.1f}% dropped)")
    print(f"other-fix    {tob} -> {toa}  ({100*(tob-toa)/tob:.1f}% dropped)")

    if a.report:
        L = ["# FIXLIKE v2 (amendment 2) — impact on the event sets\n",
             "Generated by `tools/fixlike_v2.py`. Non-destructive: v2 event sets are written to",
             "`events/<repo>_xc2.json`; `events/<repo>_xc.json` (v1) is untouched, so every published v1",
             "result stays reproducible.\n",
             "`latent` is exempt (curated security-fix list, not the keyword gate).\n",
             "| repo | events v1 → v2 | `other-fix` v1 → v2 | `regression` | `extrinsic` |",
             "|---|---|---|---|---|"]
        for r, b, k, ob, oa, rb, ra, eb, ea in rows:
            L.append(f"| {r} | {b:,} → {k:,} ({100*(b-k)/b:.0f}% cut) | {ob:,} → {oa:,} "
                     f"({100*(ob-oa)/max(ob,1):.0f}% cut) | {rb:,} → {ra:,} | {eb:,} → {ea:,} |")
        L += ["", f"**Total events {tb:,} → {tk:,}** ({100*(tb-tk)/tb:.1f}% dropped) · "
                  f"**`other-fix` {tob:,} → {toa:,}** ({100*(tob-toa)/tob:.1f}% dropped)\n",
              "## Why each commit was dropped\n"]
        for r, dropped in lines:
            if not dropped:
                continue
            L.append(f"- **{r}**: " + ", ".join(f"{c} via rule {k} ×{n}" for (c, k), n in
                                                sorted(dropped.items(), key=lambda x: -x[1])))
        a.report.write_text("\n".join(L) + "\n")
        print(f"\nwrote {a.report}")


if __name__ == "__main__":
    main()
