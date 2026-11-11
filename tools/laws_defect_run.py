#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Run the defect laws (LAW-6, LAW-7, LAW-8) over a set of repos, with the keyword fix label and with the M6
workflow label, and record both. This is the defect leg of the driver; the full driver that hands every law's
records to tools/laws_synth.py is still owed.

    python tools/laws_defect_run.py --out DIR --repos libgit2,prometheus      -> DIR/defect_laws_<tag>.json

`--labels` chooses which fix label the laws are computed from:
  `keyword`   the history database's own label (what the pilot used);
  `workflow`  tools/laws_github.py's revised label where it has one, the keyword label elsewhere (M6);
  `both`      (the default) runs each repo twice and records the pair, so the effect of the label is visible
              rather than inferred.

A repo whose GitHub record is missing or was skipped (libxml2 is on gitlab.gnome.org) has no revised label, so
its `workflow` run is identical to its `keyword` run by construction. That is reported, not hidden: it is the
differential-evidence problem the M6 write-up raises.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import laws_defects as D  # noqa: E402
import laws_github as G  # noqa: E402
import laws_panel as P  # noqa: E402
import laws_predict as R  # noqa: E402

LANGUAGE = {"libgit2": "c", "libxml2": "c", "redis": "c", "postgres": "c", "commons-lang": "java",
            "prometheus": "go", "sphinx": "python", "ripgrep": "rust"}


def labels_for(out: Path, repo: str) -> tuple[dict[str, bool], str]:
    f = out / "github" / f"{repo}.json"
    if not f.exists():
        return {}, "no GitHub record"
    rec = json.loads(f.read_text())
    if rec.get("skipped"):
        return {}, f"skipped: {rec['skipped']}"
    return G.fix_labels(f), f"{rec['changed']} labels changed by M6"


def run(out: Path, repo: str, language: str, labels: dict[str, bool], boot: int) -> dict:
    t0 = time.time()
    rows, summary = P.file_years(out / "dbs" / f"{repo}.db", out / "history" / f"{repo}.db", language, labels)
    rec = {"summary": summary, "law6": D.law6(rows, boot=boot), "law7": D.law7(rows, boot=boot),
           "law8": R.fit(rows), "seconds": round(time.time() - t0, 1)}
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repos", required=True, help="comma-separated")
    ap.add_argument("--labels", choices=("keyword", "workflow", "both"), default="both")
    ap.add_argument("--boot", type=int, default=D.BOOT)
    a = ap.parse_args()
    which = ("keyword", "workflow") if a.labels == "both" else (a.labels,)
    results: dict[str, dict] = {}
    for repo in [r.strip() for r in a.repos.split(",") if r.strip()]:
        language = LANGUAGE.get(repo)
        if language is None:
            print(f"{repo}: no registered language; skipped")
            continue
        labels, note = labels_for(a.out, repo)
        results[repo] = {"language": language, "labels_note": note}
        for tag in which:
            rec = run(a.out, repo, language, labels if tag == "workflow" else {}, a.boot)
            results[repo][tag] = rec
            s, l6, l7, l8 = rec["summary"], rec["law6"], rec["law7"], rec["law8"]
            print(f"{repo} [{tag}] {s['rows']} file-years, {s['positives']} positive "
                  f"({s['positives']/max(1,s['rows']):.1%}), labels {s['fix_labels']['changed']} changed; "
                  f"LAW-6 {l6.get('effect', float('nan')):+.3f}+-{l6.get('se', float('nan')):.3f}"
                  f"{'' if l6['evaluable'] else ' (not evaluable)'}; "
                  f"LAW-7 " + ", ".join(f"{m}={l7['metrics'][m].get('effect', float('nan')):+.2f}"
                                        for m in D.METRICS if l7["metrics"].get(m, {}).get("evaluable"))
                  + f"; LAW-8 {l8.get('effect', float('nan')):+.4f}"
                  f"{'' if l8['evaluable'] else ' (not evaluable)'}  [{rec['seconds']}s]")
    tag = a.labels
    f = a.out / f"defect_laws_{tag}.json"
    f.write_text(json.dumps(results, indent=1) + "\n")
    print(f"-> {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
