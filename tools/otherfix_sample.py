#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Draw the `other-fix` precision-audit sample (docs/otherfix_audit.md).

`other-fix` is xc_harvest's residual: a fix-like message with 1-50 C files that is not a known
security-fix event, not a revert / regression-word / recent-sha reference, and does not name an
environment. The three named classes have audited precision (docs/xc_label_audit.md); this
residual never has, and it carries 85-97% of the outcome mass in every repo, so it is the de
facto dependent variable of every file-year model in the programme.

The question here is NOT "is this the right class" (there is no narrower class to be right
about) but the precision of the FIXLIKE gate itself: **is this commit actually fixing a defect
in the code's behaviour?** A commit counts as correct iff it repairs behaviour that was wrong.
It does NOT count if it is a feature or refactor whose message merely contains a fix word, a
docs/tests/build-only change, or a cosmetic or compiler-warning-only change.

    python tools/otherfix_sample.py --repos libgit2,postgres,... --n 30 > docs/otherfix_sample.md
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT = "libgit2,postgres,libxml2,redis,prometheus,commons-lang,sphinx,ripgrep"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", default=DEFAULT)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=2982)
    a = ap.parse_args()

    print("# `other-fix` precision audit — sample\n")
    print(f"Seeded random sample, seed {a.seed}, {a.n} per repo, drawn from `other-fix` events only.")
    print("Judge each: does this commit repair behaviour that was wrong? Not a fix if it is a "
          "feature/refactor with a fix word in the message, a docs/tests/build-only change, or a "
          "cosmetic or warning-only change.\n")
    for r in a.repos.split(","):
        p = REPO_ROOT / "events" / f"{r}_xc.json"
        if not p.exists():
            continue
        ev = [e for e in json.loads(p.read_text())["events"] if e.get("class") == "other-fix"]
        rng = random.Random(a.seed)
        rng.shuffle(ev)
        pick = ev[:a.n]
        print(f"\n## {r} — {len(pick)} of {len(ev)} `other-fix` events\n")
        for e in pick:
            subj = e["subject"].replace("\n", " ").strip()
            print(f"- [ ] `{e['sha'][:10]}` ({len(e['c_files'])}f) {subj[:150]}")


if __name__ == "__main__":
    main()
