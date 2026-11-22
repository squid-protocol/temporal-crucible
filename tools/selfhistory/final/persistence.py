#!/usr/bin/env python3
"""Reversal / persistence analysis (Amendment 2 rule). Writes out/persistence.{md,json}. CPU metric only; US Eastern dates throughout."""
import json
from common import *

det = load_detected(); T = det["T"]; ref = load_refined(); pm = pos(); dates = commit_dates(); series = load_series(dates)
events = make_events(ref, pm); steps = cpu_steps(events); SH = snapshot_hash()
files_only = [(c, e["sha"]) for e in events for c, v in e["corpora"].items() if v["metric"] != "cpu_s"]
tm = {t: [(i, s["cpu"], s["date"]) for i, s in timed(series, t)] for t in series}
sdates = {s["sha"]: dates[s["sha"]].strftime("%Y-%m-%d") for s in steps}
up, down, skipped = persistence_analyze(steps, tm, T, sdates)
S = persistence_summary(up)
json.dump({"snapshot_hash": SH, "summary": S, "up_steps": up, "down_steps": down, "not_evaluated": skipped, "files_only_not_evaluated": files_only}, open(OUT / "persistence.json", "w"), indent=1, default=str)

f = lambda x, d=2: "n/a" if x is None else f"{x:.{d}f}"
L = [stamp_md(), "# Persistence of CPU steps (Amendment 2 rule)", "",
     "Pre = median CPU of the 3 timed commits before the step commit; post = median of the first 3 timed commits at or after it. A step is evaluated only if post > pre x (1+T) and at least 6 timed commits lie at or after it. REVERSED = a later run of 3 consecutive timed commits (starting after the post window) whose median is <= pre x (1+T) (within T of pre, or beyond it: overshoot counts). ELEVATED AT TIP = median of the last 3 timed commits > pre x (1+T), independent of REVERSED. 'Removed by named DOWN' = a localised DOWN step on the same corpus lies between the last non-reversed commit and the end of the reversal window. OVERLAPPING = another localised CPU step on the same corpus lies inside the pre/post window span; excluded from pooled figures. Dates are US Eastern commit dates. One step per (corpus, found commit); files-only localisations are not evaluated.", ""]
def row(name, b):
    if not b.get("n"): return f"| {name} | 0 | | | | | | |"
    return (f"| {name} | {b['n']} | {b['n_reversed']} ({pct(b['share_reversed'])}; {pct(b['ci95_reversed'][0])} to {pct(b['ci95_reversed'][1])}) | {b['n_reversed_by_named_down']} | "
            f"{f(b['median_days_to_reversal'],0)} / {f(b['median_commits_to_reversal'],0)} | {pct(b['km_share_reversed_by_end'])} / {f(b['km_median_commits_to_reversal'],0)} | {b['n_not_reversed']} (median follow-up {f(b['median_follow_up_commits_not_reversed'],0)} commits) | {b['n_elevated_at_tip']} ({pct(b['share_elevated_at_tip'])}) |")
L += ["## Summary (non-overlapping evaluable UP steps)", "", f"Overlapping steps excluded from the pooled rows: {S['n_overlapping_excluded']}.", "",
      "| group | UP steps | reversed (share; 95% CI) | of which removed by a named DOWN | median days / commits to reversal | Kaplan-Meier share reversed by end / median commits (right-censoring) | not reversed | elevated at tip |", "|---|---|---|---|---|---|---|---|"]
for t, b in S["per_corpus"].items(): L.append(row(t, b))
L.append(row("pooled, per (corpus, commit)", S["pooled_corpus_commit_pairs"]))
c = S["pooled_per_commit"]
L += ["", f"Pooled per commit (deduped across corpora): {c['n_commits']} commits; reversed in all corpora that saw them {c['all_corpora_reversed']}, in none {c['none_reversed']}, mixed {c['mixed']}; elevated at the tip in all corpora {c['elevated_at_tip_in_all']}.",
      "Right-censoring: a step not yet reversed at the tip is censored, not 'persistent for ever'; the plain share reversed is therefore a lower bound and the Kaplan-Meier column treats unreversed steps as censored at their follow-up.", "",
      "## Every evaluated UP step", "", "| corpus | date | idx | commit | pre CPU s | post CPU s | size (medians) | reversed | days | commits | removed by named DOWN | overshoot | elevated at tip | tip vs pre | overlapping |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for x in up:
    L.append(f"| {x['corpus']} | {x['date']} | {x['index']} | {x['commit']} | {f(x['pre'])} | {f(x['post'])} | {x['size']:+.0%} | {'yes' if x['reversed'] else 'no'} | {x.get('days_to_reversal','')} | {x.get('commits_to_reversal','')} | {x.get('removed_by_named_down') or ''} | {'yes' if x.get('overshoot') else ''} | {'yes' if x['elevated_at_tip'] else 'no'} | {x['tip_vs_pre']:+.0%} | {', '.join(x['overlapping'])} |")
if not up: L.append("| none | | | | | | | | | | | | | | |")
L += ["", "## DOWN steps (size = boundary pair, never median levels)", "", "| corpus | date | idx | commit | boundary CPU s (parent -> commit) | boundary rel | timed commits after |", "|---|---|---|---|---|---|---|"]
for x in down: L.append(f"| {x['corpus']} | {x['date']} | {x['index']} | {x['commit']} | {x['boundary'][0]} -> {x['boundary'][1]} | {x['boundary_rel']:+.0%} | {x['n_after']} |")
if not down: L.append("| none | | | | | | |")
L += ["", "## UP steps not evaluated", ""] + [f"- {x['corpus']} {x['date']} idx {x['index']} {x['commit']}: {x['reason']}" for x in skipped] + [f"- {c} {s[:10]}: localised on files_mapped only (persistence is defined on CPU)" for c, s in files_only] + (["- none"] if not skipped and not files_only else [])
L += ["", "Notes: steps are not netted against each other; a localised step whose neighbours sit inside its windows is marked overlapping and left out of pooled rows. Pre levels are sensitive to the sparse early sampling."]
(OUT / "persistence.md").write_text("\n".join(L) + "\n")
print(f"persistence: {len(up)} UP evaluated, {len(down)} DOWN, {len(skipped)} not evaluated")
