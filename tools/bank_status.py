#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""What is actually in the repo bank, and which repos are fit to carry an analysis.

    python tools/bank_status.py [--md docs/BANK_STATUS.md]

One table, measured not asserted. A repo is in GOOD STANDING when it has every layer an analysis needs AND a
fix label whose precision on that repo clears the gate:

    clone · structural walk · commit history · line deltas · labelled events · carded label >= 0.70

Anything less is named, with the missing layer, so the next study knows what it would have to build first.
"""
from __future__ import annotations

import argparse, json, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = Path("/srv/storage_16tb/projects/temporal-crucible-pool")
STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
GATE = 0.70
# What each repo is FOR. dev = deliberately spent (replication/exploration); pilot = carries the programme's
# founding claims; reserved = sealed holdout, not to be opened without a registered hypothesis.
TIER = {**{r: "development" for r in ("commons-lang", "libgit2", "libxml2", "postgres",
                                      "prometheus", "redis", "ripgrep", "sphinx")},
        "curl": "pilot", "ndpi": "pilot", "openssl": "reserved"}


def count(db: Path, q: str):
    if not db.exists():
        return None
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        n = c.execute(q).fetchone()[0]
        c.close()
        return n
    except Exception:
        return None


def rows():
    card = {}
    p = ROOT / "docs" / "label_card.json"
    if p.exists():
        card = {r["repo"]: r for r in json.loads(p.read_text())["repos"]}
    names = sorted(set(TIER) | set(card))
    for r in names:
        hist = STUDY / "history" / f"{r}.db"
        lang = None
        if hist.exists():
            try:
                c = sqlite3.connect(f"file:{hist}?mode=ro", uri=True)
                lang = dict(c.execute("select key,value from meta")).get("language")
                c.close()
            except Exception:
                pass
        lang = lang or (card.get(r, {}) or {}).get("language")
        ev = ROOT / "events" / f"{r}_xc.json"
        n_ev = None
        if ev.exists():
            d = json.loads(ev.read_text())
            n_ev = len(d if isinstance(d, list) else (d.get("events") or []))
        cd = card.get(r, {})
        best = max([x for x in (cd.get("raw_precision"), cd.get("v3c_precision")) if x is not None] or [0])
        yield {
            "repo": r, "language": lang or "?", "tier": TIER.get(r, "?"),
            "clone": (POOL / r).is_dir(),
            "snapshots": count(STUDY / "dbs" / f"{r}.db", "select count(*) from snap"),
            "commits": count(hist, "select count(*) from commit_"),
            "deltas": count(STUDY / "deltas" / f"{r}.db", "select count(*) from delta"),
            "events": n_ev,
            "label_best": best or None,
            "label_fit": bool(best >= GATE),
        }


def standing(x) -> tuple[bool, list[str]]:
    missing = []
    if not x["clone"]:
        missing.append("clone")
    if not x["snapshots"]:
        missing.append("walk")
    if not x["commits"]:
        missing.append("history")
    if not x["deltas"]:
        missing.append("deltas")
    if not x["events"]:
        missing.append("events")
    if not x["label_fit"]:
        missing.append("label<0.70" if x["label_best"] else "label unmeasured")
    return (not missing), missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", type=Path)
    a = ap.parse_args()
    data = list(rows())
    L = ["# BANK STATUS — what is fit to carry an analysis", "",
         "Measured by `tools/bank_status.py`, not asserted. **Good standing** = every layer present **and** a",
         f"fix label whose precision on that repo clears {GATE:.2f}.", "",
         "| repo | lang | tier | walk | commits | deltas | events | best label | standing | missing |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    good = []
    for x in sorted(data, key=lambda y: (y["tier"], -(y["label_best"] or 0))):
        ok, miss = standing(x)
        if ok:
            good.append(x)
        f = lambda v: (f"{v:,}" if isinstance(v, int) else "—")
        L.append(f"| {x['repo']} | {x['language']} | {x['tier']} | {f(x['snapshots'])} | {f(x['commits'])} | "
                 f"{f(x['deltas'])} | {f(x['events'])} | "
                 f"{(f'{x['label_best']:.2f}' if x['label_best'] else '—')} | "
                 f"{'**GOOD**' if ok else 'not yet'} | {', '.join(miss) or '—'} |")
    langs = sorted({x["language"] for x in good})
    L += ["", f"**{len(good)} of {len(data)} repos in good standing**, covering {len(langs)} languages: "
              f"{', '.join(langs)}.", ""]
    print("\n".join(L))
    if a.md:
        a.md.write_text("\n".join(L) + "\n")
        print(f"-> {a.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
