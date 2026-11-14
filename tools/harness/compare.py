#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The first three-way table (harness_spec.md, "What is compared"): per rule, what the SA3 pipeline produced,
what the control repository's manifest says, and agree / differ / undecided in the manifest.

    python tools/harness/compare.py --work WORK --name NAME --control DIR    # re-make the table from a run

It reads only files under WORK (the run's own outputs) and DIR/manifest.json; it imports no SA3 tool except
tools/sa3_stats.py, which is pure functions with no I/O (checked: its only imports are sys, numpy and scipy).
A row is never empty: a stage that did not run gives "not run" with the stage that stopped. Nothing here is
tuned to make a row agree; where the two sides measure different things by design, the row says so.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sa3_stats as S  # noqa: E402

DAY = 86400
WINDOW_DAYS = 730
EFFECT_TOL = 0.01      # planted-effect row: |pipeline - manifest| within this is "agree" (DECISIONS.md)
FLOOR_FILES, FLOOR_COMMITS, MAX_SHARE = 30, 20, 0.25
# planted property -> the scorer's predictor that reads it (sa3_score.PREDICTORS); None = no predictor
PREDICTOR_OF = {"branches": "struct_branch", "max_nesting": "nest_max", "calls_in": "in_degree",
                "calls_out": "out_degree", "state_writes_in_branches": None, "d_branches": None,
                "pointer_ops+alloc_ops": "state_pointers_alloc"}


def row(rule, pipeline, manifest, verdict, detail="", data=None):
    assert verdict in ("agree", "differ", "undecided in the manifest", "not run")
    return {"rule": rule, "pipeline": pipeline if pipeline not in (None, "") else "(none)",
            "manifest": manifest if manifest not in (None, "") else "(none)", "verdict": verdict,
            "detail": detail, "data": data or {}}


def snapshot_texts(repo: Path, sha: str, paths) -> dict[str, str]:
    """The text of each path at `sha`, read by the harness itself (one `git cat-file --batch`), for the
    diagnostic notes only; never used for a verdict."""
    paths = sorted(paths)
    if not paths or not repo.is_dir():
        return {}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(repo), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_NO_LAZY_FETCH": "1", "LC_ALL": "C"}
    p = subprocess.run(["git", "-c", "gc.auto=0", "-C", str(repo), "cat-file", "--batch"], env=env,
                       input="".join(f"{sha}:{x}\n" for x in paths).encode(), capture_output=True)
    out, buf, i = {}, p.stdout, 0
    for x in paths:
        head_end = buf.index(b"\n", i)
        head = buf[i:head_end].split()
        if len(head) < 3:
            i = head_end + 1
            continue
        n = int(head[2])
        out[x] = buf[head_end + 1:head_end + 1 + n].decode("utf-8", "replace")
        i = head_end + 1 + n + 1
    return out


def iso(t):
    import datetime as dt
    return dt.datetime.fromtimestamp(int(t), dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ") if t else "?"


def short(xs, n=8):
    xs = sorted(xs)
    return ", ".join(xs[:n]) + (f", ... ({len(xs) - n} more)" if len(xs) > n else "")


class M:
    """Manifest views."""

    def __init__(self, m: dict):
        self.m = m
        self.snap = m["points"]["snapshot"]
        self.t0 = self.snap["time"]
        self.t1 = self.t0 + WINDOW_DAYS * DAY
        self.files = {f["id"]: f for f in m["files"]}
        self.units = {f["path_at_snapshot"]: f for f in m["files"] if f["is_unit"] and f.get("path_at_snapshot")}
        self.by_snap_path = {f["path_at_snapshot"]: f for f in m["files"] if f.get("path_at_snapshot")}
        self.commit = {c["id"]: c for c in m["commits"]}
        self.realised = {r["hash"]: r for r in m["realised"]}
        self.labels = {e["hash"]: e for e in m["expected_labels"]}
        self.lang = m["arguments"]["language"]

    def prop(self, f, name):
        return f["properties"]["snapshot"].get(name)

    def in_window(self, h):
        t = self.realised.get(h, {}).get("time")
        return t is not None and self.t0 < t <= self.t1

    def touched_units(self, label) -> set[str]:
        """snapshot unit paths a first-parent unit touches: the union over its logical commits, by file id"""
        out = set()
        for lid in label["commits"]:
            for fid in self.commit[lid].get("file_ids", []):
                f = self.files.get(fid)
                if f and f["is_unit"] and f.get("path_at_snapshot"):
                    out.add(f["path_at_snapshot"])
        return out

    def is_tree_wide(self, label):
        return "Tree-wide" in label["clause"] or "tree-wide" in label["clause"]

    def is_bot(self, h):
        r = self.realised.get(h, {})
        # a bot-authored unit, or a direct / squash unit made only of bot commits; a human merge that brings
        # in a bot's branch commit is not a bot unit (the bot commit itself is off the first-parent chain)
        return "[bot]" in r.get("author", "") or (r.get("kind") != "merge" and bool(r.get("lids"))
                                                  and all(self.commit[l]["type"] == "bot" for l in r["lids"]))

    def counted(self):
        return {h: e for h, e in self.labels.items() if e["counted"] is True}

    def ambiguous(self):
        return {h: e for h, e in self.labels.items() if e["counted"] is None}


def per_file_row(rule, pipe: dict, man: dict, mapping_note: str, what: str):
    common = sorted(set(pipe) & set(man))
    same = [p for p in common if pipe[p] is not None and float(pipe[p]) == float(man[p])]
    diff = [p for p in common if p not in same]
    missing = [p for p in common if pipe[p] is None]
    deltas = [float(pipe[p]) - float(man[p]) for p in diff if pipe[p] is not None]
    examples = [f"{p}: pipeline {pipe[p]}, manifest {man[p]}" for p in diff[:6]]
    verdict = "agree" if common and not diff else "differ"
    d = (f"{len(same)} of {len(common)} files equal" + (f"; {len(missing)} with no pipeline value" if missing else "")
         + (f"; differences pipeline - manifest: mean {np.mean(deltas):+.2f}, min {min(deltas):+g}, "
            f"max {max(deltas):+g}; e.g. {'; '.join(examples)}" if deltas else "") + (f". {mapping_note}" if mapping_note else ""))
    return row(rule, f"{what}: {len(common)} files compared", f"{len(common)} unit files", verdict, d,
               {"equal": len(same), "compared": len(common), "differ": diff})


def compare(results: dict, manifest: dict) -> dict:
    mv = M(manifest)
    rows = []
    repo = results["repo"]
    rt = results["routes"]
    own, man = rt.get("own", {}), rt.get("manifest", {})

    def load(route, rel):
        p = Path(route.get("work", "/nonexistent")) / rel
        return json.loads(p.read_text()) if p.exists() else None

    probe = load(man, "probe.json")
    oc = load(man, f"study/sa3_outcomes/{repo}.json")
    nest = load(man, f"study/sa3_nesting/{repo}.json")
    scored = load(man, "tree/docs/sa3_result.json")

    # ---- snapshot
    lift = own.get("lift") or {}
    prep = (own.get("mod1_prep") or [{}])[0] if own else {}
    if lift.get("snapshot"):
        same = lift["snapshot"] == mv.snap["hash"]
        order = [r["hash"] for r in manifest["realised"]]
        pi = order.index(lift["snapshot"]) if lift["snapshot"] in order else None
        mi = order.index(mv.snap["hash"])
        rows.append(row("snapshot",
                        f"{lift['snapshot'][:12]} (realised commit #{pi}, cut {iso(prep.get('cut_ct'))}; "
                        f"{lift.get('usable_commits')} usable commits, bots excluded)",
                        f"{mv.snap['hash'][:12]} (realised commit #{mi}, {mv.snap['time_iso']}, logical commit "
                        f"{mv.snap['commit']})", "agree" if same else "differ",
                        "the pipeline's own choice (route `own`). By design the two rules differ: the pipeline takes "
                        "commit int(0.8 n) of the non-bot commits of its walk; the manifest takes logical commit "
                        "ceil(0.8 n) - 1 of the whole base timeline. Every row below uses route `manifest`, where "
                        "the manifest's snapshot was handed to sa3_scan --sha."
                        + ("" if same else f" Offset: {None if pi is None else pi - mi} realised commits."),
                        {"pipeline": lift["snapshot"], "manifest": mv.snap["hash"]}))
    else:
        rows.append(row("snapshot", f"not run: route `own` stopped at {own.get('stopped_at', 'not started')}",
                        mv.snap["hash"][:12], "not run"))
    if not probe or not oc:
        stop = man.get("stopped_at", "not started")
        for rule in ("window", "universe", "scan completeness", "LOC", "branch keywords", "nesting", "calls in",
                     "pointer and allocation counts (C)", "bots", "tree-wide commits", "HP qualifying commits",
                     "HP positive files", "keyword outcome", "control pool", "floors", "planted effect"):
            rows.append(row(rule, f"not run: route `manifest` stopped at {stop}", "see manifest", "not run"))
        return finish(results, manifest, rows)

    # ---- window
    lo, hi = oc.get("window_start"), oc.get("end")
    ok = lo == mv.t0 and hi == mv.t1
    rows.append(row("window", f"({iso(lo)}, {iso(hi)}]  [{(hi - lo) / DAY:.1f} days]",
                    f"({iso(mv.t0)}, {iso(mv.t1)}]  [snapshot + 730 days]", "agree" if ok else "differ",
                    f"the pipeline's window starts at max(its own cut {iso(oc.get('cut'))}, the scanned snapshot) and "
                    f"ends at its own cut + 730 days (sa3_outcomes.py:164-169, mod1_lift.frame), whatever snapshot is "
                    f"scanned; so with the manifest's snapshot handed in, start differs by {(lo - mv.t0) / DAY:+.1f} "
                    f"days and end by {(hi - mv.t1) / DAY:+.1f} days." if not ok else ""))

    # ---- universe
    uni = set(probe["universe"])
    mun = set(mv.units)
    only_p, only_m = uni - mun, mun - uni
    why_p = Counter(mv.by_snap_path.get(p, {}).get("unit_reason", "not in the manifest at the snapshot") for p in only_p)
    arch = probe["archive"]
    scan = probe["scan"]

    def why_missing(p):
        a = arch.get(p)
        if a is None:
            return "absent from git archive of the snapshot"
        if a["why"]:
            return f"excluded by laws_units: {a['why']}"
        if a["language"] not in probe["frame"]["langs"]:
            return f"language {a['language']}"
        if not a["in_scan"]:
            return "not scanned by the engine"
        if not scan[p]["total_loc"]:
            return "LOC 0 in the scan"
        return "?"
    why_m = Counter(why_missing(p) for p in only_m)
    rows.append(row("universe", f"{len(uni)} unit files (sa3_outcomes.universe)", f"{len(mun)} files with is_unit at "
                    "the snapshot", "agree" if not only_p and not only_m else "differ",
                    (f"pipeline-only {len(only_p)}: {dict(why_p)} [{short(only_p, 5)}]. " if only_p else "")
                    + (f"manifest-only {len(only_m)}: {dict(why_m)} [{short(only_m, 5)}]." if only_m else ""),
                    {"pipeline_only": sorted(only_p), "manifest_only": sorted(only_m)}))

    # ---- scan completeness
    c = oc.get("complete")
    rows.append(row("scan completeness", f"{c} ({oc.get('unit_files')} unit files with LOC in the scan; "
                    f"{oc.get('tree_unit_files')} unit files in the archive by the pipeline's rule)", "1.0 expected",
                    "agree" if c == 1.0 else "differ",
                    "the pipeline's numerator and denominator are both its own unit rule, so a file it does not "
                    "call a unit cannot lower completeness; compare the universe row."))

    # ---- per-file measures
    both = sorted(uni & mun)
    rows.append(per_file_row("LOC", {p: scan.get(p, {}).get("total_loc") for p in both},
                             {p: mv.prop(mv.units[p], "loc") for p in both}, "", "the scan's total_loc"))
    texts = snapshot_texts(Path(results["control"]) / "repo", mv.snap["hash"], both)
    extra_rx = (r"\belse\b", r"\bcase\b", r"\bdefault\b", r"&&", r"\|\|", r"\band\b", r"\bor\b")
    n_else = {p: len(re.findall(r"\belse\b", t)) for p, t in texts.items()}
    n_more = {p: sum(len(re.findall(rx, t)) for rx in extra_rx) for p, t in texts.items()}
    sb = {p: scan.get(p, {}).get("struct_branch") for p in both}
    expl = sum(1 for p in both if p in n_else and sb[p] is not None
               and sb[p] == mv.prop(mv.units[p], "branches") + n_else[p])
    expl2 = sum(1 for p in both if p in n_more and sb[p] is not None
                and sb[p] == mv.prop(mv.units[p], "branches") + n_more[p])
    rows.append(per_file_row("branch keywords", sb, {p: mv.prop(mv.units[p], "branches") for p in both},
                             f"manifest mapping: {manifest.get('branch_mapping')}; the engine's struct_branch "
                             "keyword family is its own and is not stated by the manifest. Diagnostic (harness's own "
                             f"count of words in the file at the snapshot; the generator writes no keyword in a comment "
                             f"or string): struct_branch = branches + #else in {expl} of {len(both)} files; = branches + "
                             f"#(else, case, default, &&, ||, and, or) in {expl2} of {len(both)} files",
                             "the scan's struct_branch"))
    nf = (nest or {}).get("files", {})
    rows.append(per_file_row("nesting", {p: (nf.get(p) or [None])[0] for p in both},
                             {p: mv.prop(mv.units[p], "max_nesting") for p in both},
                             f"sa3_nest_scan measured {len(nf)} files, {(nest or {}).get('not_measured')} not measured, "
                             f"{(nest or {}).get('parse_errors')} with a parse error", "sa3_nest_scan nest_max"))
    sp = probe["scorer_paths"]
    ix = {p: i for i, p in enumerate(sp)}
    indeg = probe["scorer_x"]["in_degree"]
    cross, intra = Counter(), Counter()
    mdb = Path(man["work"]) / "study" / "sa3_scans" / f"{repo}_master.db"
    if mdb.exists():
        con = sqlite3.connect(f"file:{mdb}?mode=ro", uri=True)
        root = probe["scan_side"]["src_root"].rstrip("/") + "/"
        fpath = {i: (q[len(root):] if q.startswith(root) else q.lstrip("/")) for i, q in con.execute("select id, file_path from file_data")}
        for s_, d_ in con.execute("select src_file_id, dst_file_id from fcall_data where dst_func_id is not null"):
            (intra if s_ == d_ else cross)[fpath.get(d_)] += 1
        con.close()
    x_eq = sum(1 for p in both if cross[p] == mv.prop(mv.units[p], "calls_in"))
    rows.append(per_file_row("calls in", {p: indeg[ix[p]] if p in ix else None for p in both},
                             {p: mv.prop(mv.units[p], "calls_in") for p in both},
                             "in_degree = resolved fcall_data rows landing in the file (sa3_score.load:125-130); "
                             "calls_in = call sites in other files whose callee is in this file. Diagnostic (the scan's "
                             f"fcall_data split by caller file): same-file calls are {sum(intra[p] for p in both)} of "
                             f"in_degree's {int(sum(indeg[ix[p]] for p in both if p in ix))}; the cross-file part "
                             f"equals calls_in in {x_eq} of {len(both)} files",
                             "in_degree as the scorer computes it"))

    # ---- pointer and allocation counts
    rule = "pointer and allocation counts (C)"
    sptr = {p: scan.get(p, {}).get("state_pointers") for p in both}
    salloc = {p: scan.get(p, {}).get("state_memory_alloc") for p in both}
    if mv.lang == "c":
        r1 = per_file_row(rule, sptr, {p: mv.prop(mv.units[p], "pointer_ops") for p in both}, "", "state_pointers vs pointer_ops")
        r2 = per_file_row(rule, sptr, {p: (mv.prop(mv.units[p], "pointer_declarations") or 0) for p in both}, "",
                          "state_pointers vs pointer_declarations")
        r3 = per_file_row(rule, sptr, {p: mv.prop(mv.units[p], "pointer_ops") + (mv.prop(mv.units[p], "pointer_declarations") or 0)
                                       for p in both}, "", "state_pointers vs pointer_ops + pointer_declarations")
        r4 = per_file_row(rule, salloc, {p: mv.prop(mv.units[p], "alloc_ops") for p in both}, "", "state_memory_alloc vs alloc_ops")
        agree = r4["verdict"] == "agree" and any(r["verdict"] == "agree" for r in (r1, r2, r3))
        rows.append(row(rule, f"state_pointers / state_memory_alloc over {len(both)} files",
                        f"pointer_ops, pointer_declarations, alloc_ops; pointer_mapping: {manifest.get('pointer_mapping')}",
                        "agree" if agree else "differ",
                        " | ".join(f"[{r['pipeline'].split(':')[0]}] {r['detail']}" for r in (r1, r2, r3, r4)),
                        {"pointer_ops": r1["data"]["equal"], "pointer_declarations": r2["data"]["equal"],
                         "both": r3["data"]["equal"], "alloc_ops": r4["data"]["equal"], "compared": len(both)}))
    else:
        nzp = sum(1 for v in sptr.values() if v)
        nza = sum(1 for v in salloc.values() if v)
        rows.append(row(rule, f"state_pointers non-zero in {nzp}, state_memory_alloc non-zero in {nza} of {len(both)} files",
                        manifest.get("risk_operations"), "agree" if not nzp and not nza else "differ",
                        "a Python repository: the manifest plants no pointer or allocation operation, so 0 is expected"))

    # ---- bots
    hist = probe["history"]
    walked = {c["sha"] for c in hist}
    pbot = {c["sha"] for c in hist if c["bot"]}
    mbot_all = {h for h in mv.realised if mv.is_bot(h)}
    mbot = mbot_all & walked
    rows.append(row("bots", f"{len(pbot)} commits flagged bot in the history walk ({len(walked)} commits walked, "
                    f"unit: {probe['history_meta'].get('unit')})",
                    f"{len(mbot_all)} bot commits / bot-authored merges ({len(mbot)} of them in the walk)",
                    "agree" if pbot == mbot else "differ",
                    (f"flagged by the pipeline, not bots in the manifest: {len(pbot - mbot)} [{short({h[:10] for h in pbot - mbot})}]; "
                     if pbot - mbot else "") + (f"bots the pipeline did not flag: {len(mbot - pbot)} "
                                                 f"[{short({h[:10] for h in mbot - pbot})}]" if mbot - pbot else "")))

    # ---- tree-wide
    o = oc["outcomes"]
    hp_commits = set(o["HP"]["commits"])
    pool = set(o["control_pool"]["commits"])
    mwide = {h for h, e in mv.labels.items() if mv.is_tree_wide(e) and mv.in_window(h)}
    leaked = {h for h in mwide if h in hp_commits or h in pool}
    pw = oc.get("wide_commits")
    rows.append(row("tree-wide commits", f"{pw} (sa3_outcomes reports only the count; none of the manifest's "
                    f"tree-wide commits {'is' if not leaked else 'IS'} in HP or the control pool"
                    + (f": {short({h[:10] for h in leaked})}" if leaked else "") + ")",
                    f"{len(mwide)} [{short({h[:10] for h in mwide})}]",
                    "agree" if pw == len(mwide) and not leaked else "differ",
                    "the pipeline's denominator is its universe and its count is the commit's touches of universe "
                    "files by equal path; the manifest's is the snapshot's unit files touched, by file id"))

    # ---- HP commits and files
    mc = mv.counted()
    amb = mv.ambiguous()
    mset = set(mc)
    decided_p = hp_commits - set(amb)
    only_p, only_m = decided_p - mset, mset - hp_commits

    def lab(h):
        e = mv.labels.get(h)
        r = mv.realised.get(h, {})
        return (f"{h[:10]} ({'+'.join(e['types']) if e else r.get('kind', '?')}: "
                f"{(r.get('message') or '').splitlines()[0][:50] if r else ''})")
    def cause_m(h):
        e = mv.labels[h]
        pos = {x["path_at_snapshot"] for x in e["positives"]}
        if pos and not pos & uni:
            return "every positive is outside the pipeline's universe"
        at_commit = {fid: path for l in e["commits"] for path, fid in zip(mv.commit[l]["files"], mv.commit[l]["file_ids"])}
        ids = {x["id"] for x in e["positives"] if x["path_at_snapshot"] in uni}
        if ids and all(at_commit.get(i) != mv.files[i]["path_at_snapshot"] for i in ids):
            return "touched under a later path (renamed after the snapshot; SA3 matches by equal path)"
        if not mv.in_window(h) or mv.realised[h]["time"] <= oc.get("window_start", 0):
            return "before the pipeline's window start"
        conv = sorted({mv.commit[l].get("convention") or mv.commit[l]["type"] for l in e["commits"]
                       if mv.commit[l]["type"] in ("fix", "feature_with_ticket", "revert")})
        return "convention " + "+".join(conv)

    def cause_p(h):
        e = mv.labels.get(h)
        if not e:
            return "not a manifest label"
        for l in e["commits"]:
            t = mv.commit[l].get("revert_target")
            if t:
                tt = mv.commit[t["id"]]["time"]
                return (f"revert of {t['hash'][:10]} made {iso(tt)}: after the manifest's snapshot, at or before the "
                        f"pipeline's cut {iso(oc.get('cut'))}" if tt <= oc.get("cut", 0) else f"revert of {t['hash'][:10]}")
        return "+".join(e["types"])
    amb_txt = "; ".join(f"{h[:10]} pipeline {'counts' if h in hp_commits else 'does not count'} it "
                        f"(readings: {', '.join(x['reading'] + '=' + str(x['counted']) for x in next((a['readings'] for a in manifest['ambiguous'] if a['hash'] == h), []))})"
                        for h in amb)
    rows.append(row("HP qualifying commits", f"{len(hp_commits)} commits in the outcome file's HP list",
                    f"{len(mset)} expected labels with counted: true; {len(amb)} ambiguous (listed apart)",
                    "agree" if not only_p and not only_m else "differ",
                    (f"pipeline-only {len(only_p)} by cause: {dict(Counter(cause_p(h) for h in only_p))}; e.g. "
                     f"{'; '.join(lab(h) for h in sorted(only_p)[:4])}. " if only_p else "")
                    + (f"manifest-only {len(only_m)} by cause: {dict(Counter(cause_m(h) for h in only_m))}; e.g. "
                       f"{'; '.join(lab(h) for h in sorted(only_m)[:4])}. " if only_m else "")
                    + (f"Ambiguous: {amb_txt}" if amb else ""),
                    {"pipeline_only": sorted(only_p), "manifest_only": sorted(only_m), "ambiguous": sorted(amb)}))
    pfiles = set(o["HP"]["files"])
    mfiles = set().union(*({x["path_at_snapshot"] for x in e["positives"]} for e in mc.values())) if mc else set()
    per_commit_diff = []
    for h in sorted(hp_commits & mset):
        a, b = set(o["HP"]["commits"][h]), {x["path_at_snapshot"] for x in mc[h]["positives"]}
        if a != b:
            per_commit_diff.append(f"{h[:10]}: pipeline {sorted(a - b)} extra, {sorted(b - a)} missing")
    rows.append(row("HP positive files", f"{len(pfiles)} files", f"{len(mfiles)} files (union of expected positives)",
                    "agree" if pfiles == mfiles else "differ",
                    (f"pipeline-only {len(pfiles - mfiles)} [{short(pfiles - mfiles, 5)}]; " if pfiles - mfiles else "")
                    + (f"manifest-only {len(mfiles - pfiles)} [{short(mfiles - pfiles, 5)}]; " if mfiles - pfiles else "")
                    + (f"shared commits with different files: {len(per_commit_diff)} ({'; '.join(per_commit_diff[:4])})"
                       if per_commit_diff else ""),
                    {"pipeline_only": sorted(pfiles - mfiles), "manifest_only": sorted(mfiles - pfiles)}))

    # ---- keyword outcome
    def kw_label(e):
        cs = [mv.commit[l] for l in e["commits"]]
        return (e["counted"] is False and not mv.is_tree_wide(e)
                and any(c["type"] == "fix" and c.get("convention") == "keyword" for c in cs))
    mkw = {h: mv.touched_units(e) for h, e in mv.labels.items() if kw_label(e) and mv.in_window(h)}
    mkw = {h: v for h, v in mkw.items() if v}
    mkwf = set().union(*mkw.values()) if mkw else set()
    pkw = o["KW"]
    pkwf = set(pkw["files"])
    rows.append(row("keyword outcome", f"{pkw['n_commits']} commits, {pkw['n_files']} files (KW; the outcome file "
                    "lists no KW commits, only files)", f"{len(mkw)} fixes written in the keyword convention, no "
                    f"reference, not tree-wide; {len(mkwf)} snapshot unit files",
                    "agree" if pkw["n_commits"] == len(mkw) and pkwf == mkwf else "differ",
                    f"files: pipeline-only {len(pkwf - mkwf)} [{short(pkwf - mkwf, 4)}], manifest-only "
                    f"{len(mkwf - pkwf)} [{short(mkwf - pkwf, 4)}]. KW is the v3c keyword gate on the subject "
                    "(hist_fixlabel.fix_shas), which also fires on other fix-worded commits (e.g. silent fixes that "
                    "say 'Fix', ticket features 'Fixed #N', sweeps 'Fix lint') and is then removed if any HP link "
                    "exists; the manifest side is the spec's narrower definition."))

    # ---- control pool
    def pool_label(h, e):
        cs = [mv.commit[l] for l in e["commits"]]
        return (mv.in_window(h) and not mv.is_tree_wide(e) and not mv.is_bot(h)
                and not any(c["type"] == "fix" for c in cs) and mv.touched_units(e))
    mpool = {h for h, e in mv.labels.items() if pool_label(h, e)}
    tp = Counter("+".join(mv.labels[h]["types"]) + ("/counted" if mv.labels[h]["counted"] else "")
                 + ("" if mv.touched_units(mv.labels[h]) & uni else "/touches no pipeline-universe file")
                 for h in mpool - pool)
    tpp = Counter(("+".join(mv.labels[h]["types"]) + "/" + (mv.commit[mv.labels[h]["commits"][0]].get("convention") or ""))
                  if h in mv.labels else "not a manifest label" for h in pool - mpool)
    rows.append(row("control pool", f"{len(pool)} commits", f"{len(mpool)} commits that are not fixes, not tree-wide, "
                    "not bots, in the window, touching a snapshot unit file", "agree" if pool == mpool else "differ",
                    (f"manifest-only {len(mpool - pool)} by type: {dict(tp)}. " if mpool - pool else "")
                    + (f"pipeline-only {len(pool - mpool)} by type/convention: {dict(tpp)}." if pool - mpool else "")))

    # ---- floors
    def floor(files_by_commit: dict, n_units: int):
        allf = set().union(*files_by_commit.values()) if files_by_commit else set()
        big = max((len(v) for v in files_by_commit.values()), default=0)
        ok = (len(allf) >= FLOOR_FILES and n_units - len(allf) >= FLOOR_FILES and len(files_by_commit) >= FLOOR_COMMITS
              and (big / len(allf) if allf else 1) <= MAX_SHARE)
        return ok, len(allf), len(files_by_commit), round(big / len(allf), 3) if allf else None
    mhp = {h: {x["path_at_snapshot"] for x in e["positives"]} for h, e in mc.items()}
    mhp = {h: v for h, v in mhp.items() if v}
    f_hp = floor(mhp, len(mun))
    f_kw = floor(mkw, len(mun))
    p_hp, p_kw = o["HP"]["clears_floor"], o["KW"]["clears_floor"]
    rows.append(row("floors", f"HP clears_floor={p_hp} ({o['HP']['n_files']} files, {o['HP']['n_commits']} commits, "
                    f"largest share {o['HP']['largest_commit_share']}); KW clears_floor={p_kw}",
                    f"HP {f_hp[0]} ({f_hp[1]} files, {f_hp[2]} commits, largest share {f_hp[3]}); KW {f_kw[0]} "
                    f"({f_kw[1]} files, {f_kw[2]} commits, largest share {f_kw[3]})",
                    "agree" if (p_hp, p_kw) == (f_hp[0], f_kw[0]) else "differ",
                    "recomputed from the manifest with sa3_outcomes' floor (>= 30 positive files from >= 20 commits, "
                    "largest commit <= 25% of positives, >= 30 negatives) over the manifest's unit files"))

    # ---- planted effect
    props = ["branches", "max_nesting", "calls_in", "calls_out", "state_writes_in_branches", "d_branches"]
    if mv.lang == "c":
        props += ["pointer_ops+alloc_ops"]
    betas = manifest["constants"]["beta"]
    paths = sorted(mun)
    loc = np.array([float(mv.prop(mv.units[p], "loc")) for p in paths])
    band, k = S.bands(loc, paths)
    y_lab = np.array([1 if p in mfiles else 0 for p in paths])
    y_true = np.array([1 if mv.units[p].get("true_fixes_in_window", 0) > 0 else 0 for p in paths])
    d_lab, d_true = S.Design(loc, y_lab, band, k), S.Design(loc, y_true, band, k)
    common_paths = [p for p in paths if p in ix]
    for prop in props:
        pred = PREDICTOR_OF[prop]
        if prop == "d_branches":
            def val(f):
                pr = f["properties"].get("prior") or {}
                if not pr.get("loc"):
                    return 0.0
                return f["properties"]["snapshot"]["branches"] / f["properties"]["snapshot"]["loc"] - pr["branches"] / pr["loc"]
            xm = np.array([val(mv.units[p]) for p in paths])
        elif prop == "pointer_ops+alloc_ops":
            xm = np.array([float(mv.prop(mv.units[p], "pointer_ops") + mv.prop(mv.units[p], "alloc_ops")) for p in paths])
        else:
            xm = np.array([float(mv.prop(mv.units[p], prop)) for p in paths])
        e_lab, e_true = d_lab.effect(xm), d_true.effect(xm)
        cell = probe["scorer_effects"]["HP"].get(pred) if pred else None
        pe = cell.get("effect") if cell else None
        decomp, e1, e2 = "", None, None
        if pred and pred in probe["scorer_x"] and common_paths:
            # one step at a time from the manifest's side to the pipeline's: (1) the pipeline's universe, (2) its
            # instrument and LOC; the remaining step to the pipeline's number is its labels
            ci = [paths.index(p) for p in common_paths]
            pi_ = [ix[p] for p in common_paths]
            l1 = loc[ci]
            b1, k1 = S.bands(l1, common_paths)
            e1 = S.Design(l1, y_lab[ci], b1, k1).effect(xm[ci])
            xp = np.array([np.nan if v is None else v for v in probe["scorer_x"][pred]])[pi_]
            lp = np.array(probe["scorer_loc"])[pi_]
            ok_ = ~np.isnan(xp)
            cp = [q for q, g in zip(common_paths, ok_) if g]
            b2, k2 = S.bands(lp[ok_], cp)
            e2 = S.Design(lp[ok_], y_lab[ci][ok_], b2, k2).effect(xp[ok_])
            decomp = (f". Decomposition: manifest labels and counts on the {len(common_paths)} files both call units "
                      f"{e1:+.4f}; plus the pipeline's instrument and LOC {e2:+.4f}; plus the pipeline's labels "
                      f"= the pipeline's " + ("none" if pe is None else f"{pe:+.4f}"))
        sc = (((scored or {}).get("repos", {}).get(repo, {}).get("outcomes", {}).get("HP", {}).get(pred) or {})
              if pred else {})
        sc_txt = (f"; sa3_score score (run past its seal with the placeholder review) gives "
                  f"{sc['bauc']:+.4f}" if "bauc" in sc else
                  f"; sa3_score score: {sc.get('status') or 'did not run'}" if pred else "")
        beta = (betas.get("pointer_ops", 0.0), betas.get("alloc_ops", 0.0)) if prop == "pointer_ops+alloc_ops" \
            else betas.get(prop, 0.0)
        man_txt = f"{e_lab:+.4f} on the expected labels (true fixes in the window: {e_true:+.4f}); beta {beta}"
        if pred is None:
            verdict = "undecided in the manifest"
            ptxt = "no predictor of sa3_score reads this property"
        elif pe is None:
            verdict, ptxt = "differ", f"{pred}: no effect ({cell})"
        else:
            verdict = "agree" if abs(pe - e_lab) <= EFFECT_TOL else "differ"
            ptxt = (f"{pred} {pe:+.4f} (pairs {cell.get('pairs')}, pair floor {'cleared' if cell.get('clears_pair_floor') else 'NOT cleared'}"
                    f"{', instrument silent' if cell.get('silent') else ''})")
        if pred:
            ptxt += sc_txt
        rows.append(row(f"planted effect: {prop}", ptxt, man_txt, verdict,
                        ("the pipeline's statistic on its own universe, labels and instrument; the manifest's on its "
                         f"unit files, expected labels and planted counts (sa3_stats.Design, {k} bands); agree = within "
                         f"{EFFECT_TOL}") + (". pointer_ops and alloc_ops are read together, as the scorer's "
                                             "state_pointers_alloc sums the two families" if prop == "pointer_ops+alloc_ops" else "")
                        + decomp
                        + (". The manifest names no instrument for this property" if pred is None else ""),
                        {"pipeline": pe, "manifest_expected_labels": e_lab, "manifest_true_fixes": e_true, "beta": beta,
                         "manifest_on_common_units": e1, "pipeline_instrument_manifest_labels": e2}))
    return finish(results, manifest, rows)


def finish(results, manifest, rows):
    v = Counter(r["verdict"] for r in rows)
    return {"name": results["name"], "repo": results["repo"], "arguments": manifest["arguments"],
            "mutations": {k: manifest["mutations"].get(k) for k in ("applied", "definitions", "changed", "notes")},
            "routes": {k: {"stopped_at": r.get("stopped_at"), "seconds": r.get("seconds"),
                           "stages": [(s["stage"], s["rc"], s["seconds"]) for s in r.get("stages", [])],
                           "lock": r.get("lock"), "score": r.get("score"),
                           "lock_with_placeholder": r.get("lock_with_placeholder"),
                           "score_with_placeholder": {k2: v2 for k2, v2 in (r.get("score_with_placeholder") or {}).items()},
                           "placebo_rc": r.get("placebo_rc")}
                       for k, r in results["routes"].items()},
            "rows": rows,
            "summary": {"agree": v["agree"], "differ": v["differ"], "undecided": v["undecided in the manifest"],
                        "not_run": v["not run"], "rows": len(rows)}}


def markdown(t: dict) -> str:
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    out = [f"# Three-way table: {t['name']}", "",
           f"Arguments: `{json.dumps(t['arguments'])}`", "",
           f"Summary: {t['summary']['agree']} agree, {t['summary']['differ']} differ, {t['summary']['undecided']} "
           f"undecided in the manifest, {t['summary']['not_run']} not run.", ""]
    for name, r in t["routes"].items():
        out.append(f"- route `{name}`: stopped at {r['stopped_at'] or 'nothing (ran to the end)'}; "
                   f"{r['seconds']} s; stages " + ", ".join(f"{s} rc={rc} {sec}s" for s, rc, sec in r["stages"]))
    out += ["", "| rule | pipeline | manifest | verdict | detail |", "|---|---|---|---|---|"]
    for r in t["rows"]:
        out.append(f"| {esc(r['rule'])} | {esc(r['pipeline'])} | {esc(r['manifest'])} | **{r['verdict']}** | {esc(r['detail'])} |")
    if t["mutations"].get("applied"):
        out += ["", "## Mutations", "", "```", json.dumps(t["mutations"], indent=1)[:4000], "```"]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--control", type=Path, required=True)
    a = ap.parse_args()
    results = json.loads((a.work / "report" / f"{a.name}.run.json").read_text())
    manifest = json.loads((a.control / "manifest.json").read_text())
    t = compare(results, manifest)
    (a.work / "report" / f"{a.name}.json").write_text(json.dumps(t, indent=1) + "\n")
    (a.work / "report" / f"{a.name}.md").write_text(markdown(t))
    print(json.dumps(t["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
