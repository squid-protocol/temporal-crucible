#!/usr/bin/env python3
"""Quiet-step test (Amendment 2), text screen, bucket counts. Writes out/mechanisms.{md,json}."""
import json
from common import *

ref = load_refined(); pm = pos(); cf = commit_files(); cache = diff_cache(); its = items(); dates = commit_dates()
events = make_events(ref, pm); SH = snapshot_hash()
ev_sha = {e["sha"] for e in events}
cpu_ev = {e["sha"] for e in events if e["size_cpu"] is not None}
big_ev = {e["sha"] for e in events if e["size_cpu"] is not None and e["size_cpu"] > 0.25}


def info(sha):
    subj, files = cf[sha]
    n = pr_number(subj, its); it = its.get(n) if n else None
    ks = {kind(p) for p in files}; nf = n_core_funcs(cache, sha); gap = cache_gap(cache, sha, files)
    b3, b5 = bucket(files, nf, 3, gap), bucket(files, nf, 5, gap)
    title = it["title"] if it else ""
    return {"sha": sha, "era": era_of(dates[sha]), "bucket": b3, "bucket5": b5, "engine_path": bool(ks & {"core", "standards"}), "gap": gap, "nfuncs": nf,
            "hit": bool(PERF.search(subj) or PERF.search(title)), "hit_old": bool(PERF_OLD.search(subj) or PERF_OLD.search(title)),
            "q_ab3": b3 in ("a", "b"), "q_ab5": b5 in ("a", "b"), "q_strict_a": pure_a(files) and b3 == "a"}


allc = {s: info(s) for s in cf}
eng = {s: v for s, v in allc.items() if v["engine_path"]}
eng_ok = {s: v for s, v in eng.items() if not v["gap"]}
ev_info = {e["sha"]: allc[e["sha"]] for e in events if e["sha"] in allc}
R = {"snapshot_hash": SH, "n_events": len(events), "n_events_cpu": len(cpu_ev), "n_events_files_only": len(ev_sha - cpu_ev), "events_missing_commit_files": [e["sha"][:10] for e in events if e["sha"] not in cf],
     "n_first_parent_commits": len(allc), "n_engine_path_commits": len(eng), "n_cache_gap_commits": len(eng) - len(eng_ok), "n_engine_path_commits_used": len(eng_ok)}
cnt = lambda d, key="bucket": {b: sum(1 for v in d.values() if v[key] == b) for b in ["a", "b", "c", "d", "e", "gap"]}
R["bucket_counts_events"] = cnt(ev_info); R["bucket_counts_engine_path"] = cnt(eng); R["bucket_counts_all"] = cnt(allc)
R["bucket5_counts_events"] = cnt(ev_info, "bucket5"); R["bucket5_counts_engine_path"] = cnt(eng, "bucket5")
R["gap_events"] = [s[:10] for s in ev_info if ev_info[s]["gap"]]
R["strict_a_events"] = sum(1 for v in ev_info.values() if v["q_strict_a"]); R["strict_a_engine_path"] = sum(1 for v in eng.values() if v["q_strict_a"])
# effect of the cache gap on the base-rate quiet share (old behaviour: gap commits silently counted as 0 funcs = quiet (b))
base_ok = sum(1 for v in eng_ok.values() if v["q_ab3"]) / len(eng_ok)
base_old = (sum(1 for v in eng_ok.values() if v["q_ab3"]) + len(eng) - len(eng_ok)) / len(eng)
R["gap_effect"] = {"base_share_excluding_gap": base_ok, "base_share_gap_counted_as_quiet": base_old, "n_gap": len(eng) - len(eng_ok)}

VARS = [("q_ab3", "(a)+(b), quiet = core with <=3 functions (primary)"), ("q_ab5", "(a)+(b) with a cutoff of 5 functions"), ("q_strict_a", "strict bucket (a) alone (only standards files)")]
GROUPS = {"primary: CPU-metric events (files-only events excluded)": (cpu_ev, ev_sha),
          "all events incl. files-only": (ev_sha, ev_sha),
          "CPU events above 25%": (big_ev, big_ev)}
R["quiet_tests"] = {}
for gname, (gset, excl) in GROUPS.items():
    group = [eng_ok[s] for s in gset if s in eng_ok]
    others = [v for s, v in eng_ok.items() if s not in excl]
    R["quiet_tests"][gname] = {"events_in_group": len(gset), "events_not_engine_path_or_gap": len(gset) - len(group),
                               "variants": {vk: {**quiet_test(group, others, vk), "label": vl} for vk, vl in VARS}}
prim = [eng_ok[s] for s in cpu_ev if s in eng_ok]
R["share_all_events_incl_nonengine_not_quiet"] = {"quiet": sum(1 for s in ev_info if ev_info[s]["q_ab3"]), "n": len(ev_info)}

# text screen on the engine-path population (recall and precision over the SAME population)
def screen(key):
    hits = [s for s, v in eng.items() if v[key]]; ev_e = [s for s in ev_sha if s in eng]; evh = [s for s in ev_e if eng[s][key]]
    oth = [s for s in eng if s not in ev_sha]; oh = sum(1 for s in oth if eng[s][key])
    orr, p = fisher_exact(len(evh), len(ev_e) - len(evh), oh, len(oth) - oh) if ev_e and oth else (float("nan"), float("nan"))
    return {"population": "engine-path first-parent commits", "n_population": len(eng), "hits": len(hits), "hit_rate": len(hits) / len(eng), "events_in_population": len(ev_e), "events_hit": len(evh),
            "recall": len(evh) / len(ev_e) if ev_e else None, "recall_ci95": list(clopper_pearson(len(evh), len(ev_e))), "precision": len(evh) / len(hits) if hits else None,
            "event_base_rate": len(ev_e) / len(eng), "other_hit_rate": oh / len(oth) if oth else None, "fisher_odds_ratio": orr, "fisher_p": p,
            "events_all_hit": sum(1 for s in ev_sha if s in allc and allc[s][key]), "events_all": len(ev_sha), "hit_events": [s[:10] for s in ev_e if eng[s][key]]}
R["text_screen"] = {"corrected_regex": screen("hit"), "join_steps_regex_old": screen("hit_old")}
json.dump(R, open(OUT / "mechanisms.json", "w"), indent=1)

L = [stamp_md(), "# Mechanism buckets, quiet-step test, text screen (Amendment 1 + 2)", "",
     f"Events (LOCALISED, passes merged, deduped by commit): {R['n_events']} ({R['n_events_cpu']} with a CPU-metric corpus, {R['n_events_files_only']} files-only). First-parent commits {R['n_first_parent_commits']}; engine-path (touch core or standards) {R['n_engine_path_commits']}, "
     f"of which {R['n_cache_gap_commits']} are cache-gap core commits (merges/root absent from the diff cache; function count unknown) and excluded from the quiet test: {R['n_engine_path_commits_used']} used. EXPLORATORY.", "",
     f"Effect of the cache gap on the base-rate quiet share: {pct(base_ok,1)} excluding them vs {pct(base_old,1)} if they were silently counted as 0-function (quiet).", "",
     "## Bucket counts (cutoff 3 functions)", "", "| bucket | events | engine-path commits | all commits |", "|---|---|---|---|"]
for b, name in zip(["a", "b", "c", "d", "e", "gap"], ["a standards (no core)", "b core, <=3 funcs (quiet)", "c core, >3 funcs", "d only tools/tests/docs/other", "e no files", "gap: core, not in diff cache"]):
    L.append(f"| {name} | {R['bucket_counts_events'][b]} | {R['bucket_counts_engine_path'][b]} | {R['bucket_counts_all'][b]} |")
L += ["", f"Cutoff 5 functions: events b/c = {R['bucket5_counts_events']['b']}/{R['bucket5_counts_events']['c']}, engine-path b/c = {R['bucket5_counts_engine_path']['b']}/{R['bucket5_counts_engine_path']['c']}. "
      f"Strictly standards-only commits: events {R['strict_a_events']}, engine-path {R['strict_a_engine_path']}. Cache-gap events: {', '.join(R['gap_events']) or 'none'}.", "",
      "## Quiet-step test", "",
      "Each test compares the event group with its own complement among engine-path commits (cache-gap commits excluded): the share, its exact 95% interval, the pooled Fisher exact test and an era-stratified Mantel-Haenszel test use the SAME populations. 'Others' = engine-path commits minus ALL event commits for the all-events tests, minus the >25% events only for the >25% test. Eras by commit date: gemini <07-06, transition 07-06..07-21, claude 07-22..09-26, fleet >=09-27.", ""]
for gname, d in R["quiet_tests"].items():
    L += [f"### {gname} ({d['events_in_group']} events; {d['events_not_engine_path_or_gap']} not in the engine-path or cache-gap, excluded)", "", "| quiet definition | events quiet | share (95% CI) | others quiet | Fisher OR | Fisher p | MH OR | MH p (strata used) |", "|---|---|---|---|---|---|---|---|"]
    for vk, v in d["variants"].items():
        L.append(f"| {v['label']} | {v['quiet_events']}/{v['n_events']} | {pct(v['share'])} ({pct(v['ci95'][0])} to {pct(v['ci95'][1])}) | {v['quiet_others']}/{v['n_others']} = {pct(v['share_others'],1)} | {num(v['fisher_odds_ratio'],2)} | {num(v['fisher_p'],4)} | {num(v['mh_odds_ratio'],2)} | {num(v['mh_p'],4)} ({v['mh_strata_used']}) |")
    L += ["", "Per era (primary definition): " + "; ".join(f"{e}: events {s['events_quiet']}/{s['events']} quiet, others {s['others_quiet']}/{s['others']}" for e, s in d["variants"]["q_ab3"]["strata"].items()), ""]
a = R["share_all_events_incl_nonengine_not_quiet"]
L += [f"Reference: share of ALL events (including events outside the engine path, which count as not quiet) in (a)+(b) at cutoff 3: {a['quiet']}/{a['n']} = {pct(a['quiet']/a['n']) if a['n'] else 'n/a'}.", "",
      "## Text screen (performance words on commit subject + PR title)", "",
      "Population for both recall and precision: engine-path first-parent commits. Precision = events hit / all engine-path commits hit. Events missed by the sampling or below T are not events here, so they count against precision (it is a lower bound).", ""]
for nm, key in (("Corrected regex (DEVIATION from join_steps.py: closing word boundary, no 'batch', 'index' without trailing space)", "corrected_regex"), ("join_steps.py regex as inherited (for comparison)", "join_steps_regex_old")):
    t = R["text_screen"][key]
    L += [f"### {nm}", f"- Hits among engine-path commits: {t['hits']} of {t['n_population']} = {pct(t['hit_rate'],1)}; among non-event engine-path commits {pct(t['other_hit_rate'],1)}.",
          f"- Recall: {t['events_hit']} of {t['events_in_population']} engine-path events = {pct(t['recall'])} (95% {pct(t['recall_ci95'][0])} to {pct(t['recall_ci95'][1])}); over all {t['events_all']} events {t['events_all_hit']} hit.",
          f"- Precision: {t['events_hit']} of {t['hits']} = {pct(t['precision'],1)} (event base rate {pct(t['event_base_rate'],1)}). Fisher OR {num(t['fisher_odds_ratio'],2)}, p = {num(t['fisher_p'],4)}.", f"- Events hit: {', '.join(t['hit_events']) or 'none'}.", ""]
L += ["## Resolutions of ambiguities", "",
      "- Engine-path commit = touches at least one core or standards file. Engine functions = distinct (path, function) in the diff cache for core paths; absent core commits (merges, root) are flagged 'gap' and excluded, not counted as quiet.",
      "- Bucket order: no files -> e; any core -> gap/b/c; else any standards -> a; else d. (d)/(e) overlap in the plan; here (e) = no file changed. (a) allows tests/docs alongside; strict (a) is shown separately.",
      "- Primary excludes files-metric events; size above 25% uses the CPU boundary_rel only."]
(OUT / "mechanisms.md").write_text("\n".join(L) + "\n")
print(f"mechanisms: buckets {R['bucket_counts_events']}")
