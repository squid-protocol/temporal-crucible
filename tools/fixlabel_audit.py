#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Does the audited precision of the xc fix label transfer to the label HR-1/2/3 actually used?

    python tools/fixlabel_audit.py --out docs/fixlabel_transfer.md

`otherfix_audit.md` already measured fix-label precision on these eight repos, twice: the raw gate
(0.27-0.80 per repo) and v3c on a fresh confirmatory sample (pooled 0.761, 7 of 8 repos over the 0.70 gate).
So the audit HR needs does not have to be bought again -- **but those numbers were measured on xc_harvest's
label pipeline, and HR ran on the LAWS history DB's `fix` flag.** They are two keyword gates over the same
repositories, not the same gate.

This measures the agreement between them, so the audited precision can be carried across with a stated basis
instead of assumed. No ratings are produced and nothing is spent: it is a set comparison.
"""
from __future__ import annotations

import argparse, json, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hist_fixlabel import fix_shas  # noqa: E402

STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
REPOS = ("commons-lang", "libgit2", "libxml2", "postgres", "prometheus", "redis", "ripgrep", "sphinx")
# otherfix_audit.md: round 1 raw gate, and the confirmatory v3c round (seed 2984, fresh sample)
AUDITED_RAW = {"libxml2": 0.80, "postgres": 0.77, "redis": 0.73, "libgit2": 0.63,
               "sphinx": 0.60, "prometheus": 0.40, "commons-lang": 0.27, "ripgrep": 0.27}
AUDITED_V3C = {"libxml2": 0.86, "postgres": 0.74, "sphinx": 0.78, "redis": 0.75,
               "prometheus": 0.83, "commons-lang": 0.70, "libgit2": 0.60, "ripgrep": 0.82}


def xc_shas(root: Path, repo: str, which: str) -> set[str]:
    p = root / "events" / f"{repo}_xc{'2' if which == 'clean' else ''}.json"
    if not p.exists():
        return set()
    d = json.loads(p.read_text())
    ev = d if isinstance(d, list) else (d.get("events") or [])
    return {e["sha"] for e in ev if e.get("sha")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    rows = []
    for r in REPOS:
        h = sqlite3.connect(f"file:{STUDY/'history'/f'{r}.db'}?mode=ro", uri=True)
        raw = {s for s, in h.execute("select sha from commit_ where fix=1 and merge=0 and bot=0")}
        clean = fix_shas(h, "v3c") or set()
        h.close()
        x1, x2 = xc_shas(a.root, r, "raw"), xc_shas(a.root, r, "clean")
        def ov(A, B):
            return (len(A & B) / len(A)) if A else None
        rows.append({"repo": r, "laws_raw": len(raw), "laws_v3c": len(clean),
                     "xc_raw": len(x1), "xc_clean": len(x2),
                     "share_of_laws_raw_in_xc": ov(raw, x1),
                     "share_of_laws_v3c_in_xc_clean": ov(clean, x2),
                     "audited_raw_precision": AUDITED_RAW.get(r),
                     "audited_v3c_precision": AUDITED_V3C.get(r)})
    L = ["# Does the audited fix-label precision transfer to the label HR used?", "",
         "`otherfix_audit.md` measured precision on these eight repos for **xc_harvest's** label pipeline.",
         "HR-1/2/3 ran on the **LAWS history DB's `fix` flag**. Two keyword gates, same repositories.",
         "This is a set comparison, not new ratings: nothing was rated and nothing was spent.", "",
         "| repo | LAWS raw | LAWS v3c | xc raw | xc clean | LAWS-raw ∩ xc | LAWS-v3c ∩ xc-clean | audited raw prec. | audited v3c prec. |",
         "|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        f = lambda v: (f"{v:.0%}" if isinstance(v, float) else "—")
        L.append(f"| {x['repo']} | {x['laws_raw']} | {x['laws_v3c']} | {x['xc_raw'] or '—'} | "
                 f"{x['xc_clean'] or '—'} | {f(x['share_of_laws_raw_in_xc'])} | "
                 f"{f(x['share_of_laws_v3c_in_xc_clean'])} | {x['audited_raw_precision']:.2f} | "
                 f"{x['audited_v3c_precision']:.2f} |")
    print("\n".join(L))
    if a.out:
        a.out.write_text("\n".join(L) + "\n")
        print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
