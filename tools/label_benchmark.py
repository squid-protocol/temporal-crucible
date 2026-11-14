#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Score OUR fix labellers against an EXTERNAL corpus with validated positives AND negatives.

    python tools/label_benchmark.py --csv <evaluation_data/1-mined-combined.csv>

Every precision number this programme has is self-reported: we drew our own sample and judged it ourselves.
This scores the same rules against ground truth somebody else validated, on repositories we have never
touched and never tuned on -- the only way to find out where we actually sit.

Corpus: Koenig et al. (arXiv:2609.21616), github.com/Raubkatz/BugFixCommitLabelling. 36,270 commits over 73
repositories, overwhelmingly SmartSHARK, which is the only public corpus carrying manually validated
NEGATIVES as well as positives. `is_bugfix` is the ground truth; `isBugfix_stemming` is their keyword
baseline; the remaining columns are eight local LLMs they evaluated.

One honest limitation, stated up front: our v3c rule A ("all touched files are test/doc paths") cannot fire
here, because the corpus ships messages and no file lists. What is scored is our MESSAGE rules -- which is
most of the gate, and exactly the part the recall audit indicted.
"""
from __future__ import annotations

import argparse, csv, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixlike_v2 as F  # noqa: E402

# The keyword gate the history harvest uses, reproduced over message text alone.
KEYWORD = re.compile(r"\b(fix(es|ed|ing)?|bug|defect|error|fault|flaw|crash|broke(n)?|regress\w*|"
                     r"wrong|incorrect|fail(s|ed|ure)?|issue|patch|repair|resolve[sd]?)\b", re.I)


def ours(msg: str, rules: str | None) -> bool:
    """our label: the keyword gate, optionally cleaned by FIXLIKE (rule A inert -- no file list here)."""
    if not KEYWORD.search(msg or ""):
        return False
    if rules is None:
        return True
    subj = (msg or "").split("\n", 1)[0]
    return F.drop_reason({"class": "other-fix", "subject": subj, "c_files": []}, rules=rules) is None


def score(pred, truth):
    tp = sum(1 for p, t in zip(pred, truth) if p and t)
    fp = sum(1 for p, t in zip(pred, truth) if p and not t)
    fn = sum(1 for p, t in zip(pred, truth) if not p and t)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return prec, rec, f1, tp, fp, fn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--dataset", help="limit to one dataset, e.g. smartshark")
    a = ap.parse_args()
    rows = [r for r in csv.DictReader(a.csv.open())
            if not a.dataset or r["dataset"] == a.dataset]
    yes = lambda v: str(v).strip().lower() == "true"
    truth = [yes(r["is_bugfix"]) for r in rows]
    msgs = [r["message"] or "" for r in rows]

    cands = {
        "OURS keyword gate": [ours(m, None) for m in msgs],
        "OURS v3c (cleaned)": [ours(m, "v3c") for m in msgs],
        "OURS v2": [ours(m, "v2") for m in msgs],
    }
    for col in rows[0]:
        if col.startswith("isBugfix_"):
            cands[("their " + col[len("isBugfix_"):])] = [yes(r[col]) for r in rows]

    print(f"{len(rows):,} commits, {sum(truth):,} real bug-fixes "
          f"({sum(truth)/len(rows):.0%}), {len({r['repo'] for r in rows})} repositories"
          + (f", dataset={a.dataset}" if a.dataset else ""))
    print(f"\n{'labeller':26}{'precision':>10}{'recall':>9}{'F1':>8}{'TP':>8}{'FP':>8}{'FN':>8}")
    out = []
    for name, pred in cands.items():
        p, r, f1, tp, fp, fn = score(pred, truth)
        out.append((f1, name, p, r, f1, tp, fp, fn))
    for f1, name, p, r, _f, tp, fp, fn in sorted(out, reverse=True):
        mark = " <-- us" if name.startswith("OURS") else ""
        print(f"{name:26}{p:>10.3f}{r:>9.3f}{f1:>8.3f}{tp:>8,}{fp:>8,}{fn:>8,}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
