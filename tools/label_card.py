#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The LABEL CARD: what every fix label's precision is, per repo, and the rule that makes it binding.

    python tools/label_card.py --write            # regenerate docs/LABEL_CARD.md and label_card.json
    python tools/label_card.py --assert commons-lang raw     # exit 1 if that label is not fit to use

**Why this exists.** On 2026-11-13 HR-1 reported that recidivism beats size on this cohort, pooled lift
+0.082. It had run on a keyword fix label whose precision had already been measured two days earlier at
**0.27 on commons-lang** -- the repo carrying the largest effect. Cleaning the label reversed that repo
(+0.143 -> -0.015) and the pooled result fell to +0.009, below its own registered bar. The audit existed.
Nobody consulted it, because nothing made consulting it necessary.

**The rule.** No study may use a label whose precision on that repo is unpublished, and a label under the
0.70 gate is reported as descriptive or not used. `--assert` is how a tool checks before it runs, so the next
study cannot repeat this by omission.
"""
from __future__ import annotations

import argparse, json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = 0.70

# Measured in docs/otherfix_audit.md. Round 1: the raw FIXLIKE gate, seeded sample (2982), 30 per repo.
# Confirmatory round: v3c on a FRESH sample (seed 2984, 25 drawn per repo, all round-1 commits excluded);
# the v3c denominator is smaller because the rules drop candidates before judging.
CARD = {
    "libxml2":      {"lang": "c",      "raw": (24, 30), "v3c": (19, 22)},
    "postgres":     {"lang": "c",      "raw": (23, 30), "v3c": (14, 19)},
    "redis":        {"lang": "c",      "raw": (22, 30), "v3c": (12, 16)},
    "libgit2":      {"lang": "c",      "raw": (19, 30), "v3c": (9, 15)},
    "sphinx":       {"lang": "python", "raw": (18, 30), "v3c": (18, 23)},
    "prometheus":   {"lang": "go",     "raw": (12, 30), "v3c": (10, 12)},
    "commons-lang": {"lang": "java",   "raw": (8, 30),  "v3c": (14, 20)},
    "ripgrep":      {"lang": "rust",   "raw": (8, 30),  "v3c": (9, 11)},
}
SOURCE = "docs/otherfix_audit.md (round 1 2026-11-11; confirmatory round, fresh sample, same doc)"
TRANSFER = ("docs/fixlabel_transfer.md: 98-100% of the LAWS history-DB `fix` set appears in xc's events for "
            "seven of eight repos (ripgrep 72%), so the precision measured on xc's pipeline carries to the "
            "LAWS flag with a stated basis rather than an assumption.")


def precision(repo: str, label: str) -> tuple[float, int, int] | None:
    rec = CARD.get(repo)
    if not rec or label not in rec:
        return None
    k, n = rec[label]
    return k / n, k, n


def card_rows():
    for repo, rec in sorted(CARD.items(), key=lambda kv: -(kv[1]["raw"][0] / kv[1]["raw"][1])):
        r = precision(repo, "raw"); v = precision(repo, "v3c")
        yield {"repo": repo, "language": rec["lang"],
               "raw_precision": round(r[0], 3), "raw_n": r[2],
               "v3c_precision": round(v[0], 3), "v3c_n": v[2],
               "raw_fit": r[0] >= GATE, "v3c_fit": v[0] >= GATE}


def cmd_write(a) -> int:
    rows = list(card_rows())
    (ROOT / "docs" / "label_card.json").write_text(json.dumps(
        {"gate": GATE, "source": SOURCE, "transfer": TRANSFER, "repos": rows}, indent=1) + "\n")
    L = ["# LABEL CARD — fix-label precision per repo, and the rule that binds on it", "",
         f"**The rule.** No study may use a fix label whose precision on that repo is unpublished. A label",
         f"below the **{GATE:.2f}** gate is reported as descriptive, or not used as an outcome at all.",
         "`tools/label_card.py --assert <repo> <label>` is how a tool checks before it runs.", "",
         f"**Source.** {SOURCE}", "", f"**Transfer.** {TRANSFER}", "",
         "| repo | lang | raw precision | n | fit? | v3c precision | n | fit? |",
         "|---|---|---|---|---|---|---|---|"]
    for x in rows:
        L.append(f"| {x['repo']} | {x['language']} | **{x['raw_precision']:.2f}** | {x['raw_n']} | "
                 f"{'✓' if x['raw_fit'] else '✗'} | **{x['v3c_precision']:.2f}** | {x['v3c_n']} | "
                 f"{'✓' if x['v3c_fit'] else '✗'} |")
    nraw = sum(1 for x in rows if x["raw_fit"]); nv3 = sum(1 for x in rows if x["v3c_fit"])
    L += ["", f"**{nraw} of {len(rows)} repos** clear the gate on the raw label; **{nv3} of {len(rows)}** on v3c.", "",
          "## What this card already changed", "",
          "HR-1 reported recidivism beating size at pooled **+0.082** using the raw label. The two repos",
          "carrying its largest lifts are the two with the **worst** precision here — commons-lang at **0.27**,",
          "where nearly three in four 'fix' commits do not repair behaviour. Under v3c, commons-lang reverses",
          "(+0.143 → −0.015) and the pooled result falls to **+0.009**, below its own registered bar.",
          "The audit predated the run by two days. Nothing required reading it. That is what this card fixes.", "",
          "## Known gaps", "",
          "- **libgit2 fails both labels** (0.63 raw, 0.60 v3c) and is the one repo HR could not evaluate at all.",
          "  It needs a better label before it can carry an outcome.",
          "- Precision is measured **from the commit subject**. A label validated against the diff would be",
          "  stronger and nobody has paid for one.",
          "- Recall is known only on the tuning set (v3c keeps ~81% of real fixes there) and is **not**",
          "  separately measured on the confirmatory sample. A study whose claim depends on recall must say so."]
    (ROOT / "docs" / "LABEL_CARD.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:14]))
    print(f"\n-> docs/LABEL_CARD.md, docs/label_card.json")
    return 0


def cmd_assert(a) -> int:
    p = precision(a.repo, a.label)
    if p is None:
        print(f"REFUSED: no published precision for label {a.label!r} on {a.repo!r}. "
              f"Measure it (docs/otherfix_audit.md pattern) or pick a label that has one.")
        return 1
    val, k, n = p
    if val < GATE:
        print(f"REFUSED: {a.repo} / {a.label} precision {val:.2f} ({k}/{n}) is under the {GATE:.2f} gate. "
              f"Use it descriptively, or clean the label first.")
        return 1
    print(f"ok: {a.repo} / {a.label} precision {val:.2f} ({k}/{n}) clears the {GATE:.2f} gate")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="c")
    w = ap.add_argument_group()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--assert", dest="assert_", nargs=2, metavar=("REPO", "LABEL"))
    a = ap.parse_args()
    if a.assert_:
        a.repo, a.label = a.assert_
        return cmd_assert(a)
    return cmd_write(a)


if __name__ == "__main__":
    raise SystemExit(main())
