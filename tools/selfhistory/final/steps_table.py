#!/usr/bin/env python3
"""One row per EVENT (LOCALISED refinements, passes merged, deduped by found commit). Writes out/steps_table.{csv,md,json}."""
import csv, json
from common import *

det = load_detected(); ref, rinfo = load_refined_info()
pm, dates, cf, cache, its = pos(), commit_dates(), commit_files(), diff_cache(), items()
events = make_events(ref, pm)
SH = snapshot_hash()
rows = []
for e in events:
    sha = e["sha"]
    subj, files = cf.get(sha, (git("show", "-s", "--format=%s", sha).strip(), []))
    num_ = pr_number(subj, its); it = its.get(num_) if num_ else None
    kc = {k: 0 for k in KINDS}
    for p in files: kc[kind(p)] += 1
    add, dele = numstat(sha)
    nf = n_core_funcs(cache, sha); gap = cache_gap(cache, sha, files)
    rows.append({"date": dates[sha].strftime("%Y-%m-%d %H:%M") if sha in dates else "", "index": e["index"], "commit": sha[:10], "sha": sha, "subject": subj,
                 "pr": num_, "pr_title": it["title"] if it else "", "pr_labels": ",".join(it["labels"]) if it else "",
                 "corpora": "; ".join(f"{c} {v['boundary_rel']:+.0%}" + ("" if v["metric"] == "cpu_s" else " (files)") + (f" [also files {v['files_rel']:+.0%} (files)]" if v["metric"] == "cpu_s" and v["files_rel"] is not None else "") + (" (pair %+.0f%%)" % (100 * v["dcpu_pair"])) for c, v in e["corpora"].items()),
                 "n_corpora": len(e["corpora"]), "size_cpu": None if e["size_cpu"] is None else round(e["size_cpu"], 3), "size_files": None if e["size_files"] is None else round(e["size_files"], 3), "direction": e["direction"],
                 **{f"files_{k}": kc[k] for k in KINDS}, "files_total": len(files), "core_funcs": nf, "cache_gap": gap, "lines_added": add, "lines_deleted": dele, "bucket": bucket(files, nf, 3, gap),
                 "text_screen_hit": bool(PERF.search(subj) or (it and PERF.search(it["title"])))})
with open(OUT / "steps_table.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=(list(rows[0].keys()) if rows else ["none"]) + ["snapshot_hash"]); w.writeheader()
    for r in rows: w.writerow({**r, "snapshot_hash": SH})
other = [r for r in ref if r["class"] != "LOCALISED"]
unres = det["unresolved_failed_commits"]
total = len(det["candidates"]); done = rinfo["n_distinct"]
json.dump({"snapshot_hash": SH, "events": rows, "refined_done": done, "candidates": total, "not_localised": other, "unresolved": unres, "refinement_info": rinfo}, open(OUT / "steps_table.json", "w"), indent=1)

L = [stamp_md(), "# Step events (one row per commit named by a LOCALISED refinement)", "",
     f"Refinements: {done} of {total} candidates ({'COMPLETE' if done >= total else 'PARTIAL'}); pass 1 {rinfo['n_pass1_distinct']}, pass 2 {rinfo['n_pass2_distinct']} (pass 2 supersedes), {rinfo['n_changed_class']} changed class between passes. Events: {len(rows)}. Dates are US Eastern commit dates.",
     "Sizes: size_cpu = largest |boundary_rel| of CPU-metric corpora; size_files = file-count change (files mapped), never mixed with CPU. '(files)' marks a files_mapped figure. 'pair' = the original sampled-pair dCPU. Direction is by the CPU boundary pairs (files-only events: by files).",
     "Core funcs = engine Python functions in core files touched (diff cache). Buckets: a standards (no core), b core <=3 funcs, c core >3 funcs, d only tools/tests/docs/other, e no files, gap = core commit absent from the diff cache (function count unknown).",
     "Lines are against the first parent (merges included). PR = last '(#N)' in the subject that is a known PR.", ""]
for r in rows:
    L += [f"## {r['date'][:10]}  idx {r['index']}  {r['commit']}  bucket ({r['bucket']})  {r['direction']}  CPU {'n/a' if r['size_cpu'] is None else format(r['size_cpu'], '.0%')} / files {'n/a' if r['size_files'] is None else format(r['size_files'], '.0%') + ' (files)'}",
          f"- Subject: {r['subject']}", f"- PR: " + (f"#{r['pr']} {r['pr_title']} [{r['pr_labels']}]" if r['pr'] else "none found"), f"- Corpora: {r['corpora']}",
          f"- Files by kind: " + ", ".join(f"{k} {r['files_'+k]}" for k in KINDS) + f" (total {r['files_total']}); core funcs touched {r['core_funcs']}{' (cache gap)' if r['cache_gap'] else ''}; lines +{r['lines_added']} -{r['lines_deleted']}", ""]
L += ["## UNCONFIRMED / UNEVALUABLE candidates (counted, not analysed as steps)", ""]
for r in other: L.append(f"- {r['class']} (pass {r['_pass']}) {r['corpus']} {r['from_date']}..{r['to_date']} pair dCPU {r['dcpu']:+.0%}; metric {r.get('metric')}; bisect named {str(r.get('found'))[:10]}; boundary rel {r.get('boundary_rel')}")
if not other: L.append("- none")
L += ["", "## Candidates not yet refined", ""]
rk = {rkey(r) for r in ref}
pend = [c for c in det["candidates"] if (c["corpus"], c["from_sha"], c["to_sha"]) not in rk]
for c in pend: L.append(f"- {c['corpus']} {c['from_date']}..{c['to_date']} idx {c['from']}-{c['to']} dCPU {c['dcpu']:+.0%}")
if not pend: L.append("- none")
L += ["", f"## Unresolved crash commits ({len(unres)} failed timed runs)", ""]
for u in unres: L.append(f"- {u['corpus']} idx {u['index']} {u['date']} {u['sha'][:10]}")
(OUT / "steps_table.md").write_text("\n".join(L) + "\n")
print(f"steps_table: {len(rows)} events from {done}/{total} refinements")
