"""Ground-truth manifest: schema, the expected-label derivation, writer and loader.

The expected labels apply SA3's primary outcome rule, HP, as written in docs/sa3_registration_consolidated.md
section 4, to each commit after the snapshot. They are derived from what the generator knows each commit
carries (its `signals`), never by parsing the message, and each label names the clause that decides it.
Where the written rule gives two answers for a generated case, the case goes under `ambiguous` with both
readings and `counted` is null.
"""
from __future__ import annotations

import datetime as dt
import json
import re

import history as hi

SCHEMA_VERSION = 4
TREE_WIDE_SHARE, TREE_WIDE_MIN = 0.10, 20     # section 4: >= 10% of the unit files and >= 20 of them
MAX_BROUGHT = 50                              # section 4: no inheritance past 50 brought-in commits
WINDOW_DAYS = 730                             # section 2: the outcome window

# The clauses of docs/sa3_registration_consolidated.md section 4 (and the section 2 rule they rest on) that decide
# a label. Quoted where the text is quoted; the bracketed part of a label's clause says what in the commit fired.
CLAUSES = {
    "fixref": "HP: \"carries a fix reference (issue, Jira, bpo, PR, GnuPG bug id, `Fixes:`/`Bug:`/`Reported-by:` "
              "trailer)\"",
    "cve": "HP: carries \"a CVE id\"",
    "revert_ok": "HP: \"a revert whose target resolves to a commit that existed at the cut\"",
    "revert_late": "HP counts only \"a revert whose target resolves to a commit that existed at the cut\"; this "
                   "revert's target was made after the cut (HP_allreverts would count it)",
    "jira_bare": "HP as SA3's code reads it (tools/hist_meta.py issue_fix_sa3): a tracker key is a fix reference "
                 "only after a fix word; this commit carries a bare key",
    "keyword": "HP: no fix reference, CVE id or qualifying revert; fix wording alone is the KW tier "
               "(\"KW: the cleaned keyword rule, and no HP link\"), not HP",
    "none": "HP: no fix reference, CVE id or revert",
    "tree_wide": "\"Tree-wide commits (>= 10% of the unit files and >= 20 of them) are removed from every outcome\"",
    "window": "outside \"the 730 days after\" the snapshot (section 2)",
    "side": "section 2: \"Merges are kept as the unit where the history was walked first-parent\": this commit is "
            "off the first-parent chain and is not a unit; its merge is",
    "over_cap": "\"Tainted merges -- over the cap [...] -- are in no outcome\" (\"No inheritance past 50 "
                "brought-in commits\")",
    "tainted": "\"Tainted merges -- [...] bringing in a linked or fix-worded commit -- are in no outcome\"",
    "inherit": "\"Merge inheritance. In a merge-workflow repo a merge inherits the fix reference, CVE or qualifying "
               "revert of a commit it brings in [...] Positive files = the merge's first-parent diff ∩ the linking "
               "commit's files\"",
    "no_shared_file": "Merge inheritance: \"Positive files = the merge's first-parent diff ∩ the linking commit's "
                      "files\" is empty: the merge's diff shares no file with the linked commit",
    "nothing_to_inherit": "Merge inheritance: no brought-in commit carries a fix reference, CVE id or qualifying "
                          "revert, and the merge itself carries none",
}

# Readings where section 4 can be read more than one way (see DECISIONS.md, "merge readings" and "reverts that
# quote a ticket"). Merge readings apply to every first-parent merge; revert readings are crossed with them only
# when a brought-in revert of a non-qualifying target quotes a ticket.
READINGS = {
    "inherit": "the inheritance paragraph governs; \"tainted\" means bringing in a fix-worded (keyword-only) "
               "commit, or a linked commit the merge may not inherit from (a bot's, or a revert of a commit "
               "brought in by the same merge); a revert that does not qualify under HP is not a link",
    "nonqualifying_revert_taints": "as `inherit`, but a revert that does not qualify under HP (its target is "
                                   "after the cut, or brought in by the same merge) still counts as \"a linked "
                                   "commit\" and taints the merge",
    "literal_taint": "the taint sentence read literally: \"bringing in a linked [...] commit\" taints, so any merge "
                     "that brings in a linked commit is in no outcome, and inheritance never yields a positive",
    "taint_governs_control_pool_only": "what tools/sa3_outcomes.py does: a merge is counted when its first-parent "
                                       "diff shares a file with a linked brought-in commit that is not a bot's "
                                       "(a same-merge revert's revert link excluded); the taint only keeps merges "
                                       "out of the keyword outcome and the control pool",
}
RULED_MERGE_READING = "taint_governs_control_pool_only"
READINGS_JIRA = {   # r4: a tracker key with no fix word ("PROJ-12: ...")
    "code": "SA3's code (tools/hist_meta.py, issue_fix_sa3): a tracker key is a fix reference only after a fix word "
            "(\"Fixes PROJ-12\"); a bare key is not counted. Decides the label",
    "registration_wording": "the registration's wording, \"carries a fix reference (issue, Jira, ...)\", read to "
                            "include any Jira key: the commit is counted. Not ruled; recorded as the alternative",
}
RULING = {"date": "2026-11-14", "by": "owner",
          "ruling": "tainted merges follow SA3's code (tools/sa3_outcomes.py): a merge's expected label is decided "
                    "by the reading `taint_governs_control_pool_only`; the other merge readings are kept on the "
                    "label under `unruled_readings`, marked not ruled",
          "applies_to": "first-parent merges (merge_workflow, bot_merges, huge_import_merge)",
          "not_ruled": "a revert of a commit made after the cut that quotes a ticket from its target's subject "
                       "stays ambiguous, in merges and in direct and squash commits"}
RULING_JIRA = {"date": "2026-11-14", "by": "control_repo_spec.md revision 4",
               "ruling": "a fix that carries a tracker key without a fix word (convention jira_bare, \"PROJ-12: ...\") "
                         "is not counted, as SA3's code reads it; the registration's looser wording is recorded on "
                         "the label under `unruled_readings` (reading `registration_wording`)",
               "applies_to": "commits carrying a bare tracker key, delivered directly, squashed or in a merge"}
RULING_TAG = "[decided by the owner ruling of 2026-11-14: tainted merges follow the code] "
REVERT_READINGS = {
    "reference_counts": "a revert of a commit made after the cut that quotes a ticket from its target's subject "
                        "carries a fix reference, and HP counts it through that reference",
    "nonqualifying_revert": "such a revert is a revert whose target does not resolve to a commit that existed at "
                            "the cut: HP does not count it, the quoted ticket notwithstanding",
}


def iso(t: int) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry_tiers(e, hash_of, cut_set, same_merge=frozenset()):
    """What one logical commit carries under HP, from the signals the generator wrote into its message.

    Returns (tiers, contested, nonqual, keyword):
      tiers     [(clause key, detail)]: links HP counts under every reading;
      contested a ticket quoted by a revert whose target does not qualify (counted or not by reading), or None;
      nonqual   a revert whose target is after the cut or, inside a merge, brought in by the same merge, or None;
      keyword   the message is fix-worded."""
    s = e.signals or {}
    tiers, contested, nonqual = [], None, None
    if s.get("fixref"):
        tiers.append(("fixref", s["fixref"]))
    if s.get("cve"):
        tiers.append(("cve", "CVE id"))
    if s.get("revert"):
        tgt = s["revert"]
        if tgt in same_merge:
            nonqual = f"reverts {tgt}, brought in by the same merge"
        elif hash_of.get(tgt) in cut_set:
            tiers.append(("revert_ok", f"reverts {tgt}, made before the cut"))
        else:
            nonqual = f"reverts {tgt}, made after the cut"
        if s.get("quoted_fixref"):
            if nonqual:
                contested = s["quoted_fixref"]
            else:
                tiers.append(("fixref", s["quoted_fixref"]))
    return tiers, contested, nonqual, bool(s.get("keyword"))


class _Labeller:
    """The facts every label needs: the cut, the delivered hashes, the snapshot's unit files and their paths."""

    def __init__(self, plan, realised, snap_hash):
        self.entries = {e.lid: e for e in plan.entries}
        self.files = plan.files
        order = [r["hash"] for r in realised]
        self.cut = order.index(snap_hash)
        self.cut_set = set(order[:self.cut + 1])
        self.hash_of = {lid: r["hash"] for r in realised if r["kind"] != "merge" for lid in r["lids"]}
        self.snap_path = {f: p for f, p in plan.paths_at["snapshot"].items() if plan.files[f].is_unit}

    def positives(self, fids):
        """Snapshot unit files among `fids`, as ids with their path at the snapshot."""
        return [{"id": f, "path_at_snapshot": self.snap_path[f]}
                for f in sorted((f for f in fids if f in self.snap_path), key=lambda f: self.snap_path[f])]


def _merge_label(L, r):
    """Label a first-parent merge under every reading. Returns (counted or None, clause, positives, readings)."""
    brought = r["brought"]
    same = frozenset(brought)
    kids = []                                          # (lid, tiers, contested, nonqual, keyword, bot)
    for lid in brought:
        e = L.entries[lid]
        t, c, nq, kw = _entry_tiers(e, L.hash_of, L.cut_set, same)
        kids.append((lid, t, c, nq, kw, hi.BOT_PATTERN in e.author, (e.signals or {}).get("revert") in same))
    has_contested = any(k[2] for k in kids)
    merge_files = set(r["file_ids"])

    bare = {lid for lid in brought if (L.entries[lid].signals or {}).get("bare_key")}

    def one(m, rr, bare_counts=False):
        links, barred, fix_worded, nonqual = [], [], [], []
        for lid, t, c, nq, kw, bot, same_rev in kids:
            linked = bool(t) or (c is not None and rr == "reference_counts") or (bare_counts and lid in bare)
            if nq:
                nonqual.append(f"{lid} {nq}")
            if kw and not linked and not c:
                fix_worded.append(f"{lid}: fix-worded, no link")
            if not linked:
                continue
            if bot:
                barred.append(f"{lid}: linked commit by a bot: \"never from a bot's commit\"")
            elif same_rev and m != "taint_governs_control_pool_only":
                barred.append(f"{lid}: \"never a revert of a commit brought in by the same merge\"")
            else:
                links.append(lid)
        shared = set()
        for lid in links:
            shared |= merge_files & set(L.entries[lid].touched)
        if m == "literal_taint":
            counted = False
            why = (CLAUSES["tainted"] + " [read literally; linked: " + ", ".join(links + barred) + "]"
                   if links or barred else None)
        elif m == "taint_governs_control_pool_only":
            counted = bool(shared)
            why = None
        else:
            taint = barred + fix_worded + (nonqual if m == "nonqualifying_revert_taints" else [])
            counted = bool(shared) and not taint
            why = CLAUSES["tainted"] + " [" + "; ".join(taint) + "]" if taint and links else None
        if counted:
            clause = CLAUSES["inherit"] + " [linked: " + ", ".join(links) + "]"
        elif why:
            clause = why
        elif barred or fix_worded:
            clause = CLAUSES["tainted"] + " [" + "; ".join(barred + fix_worded) + "]"
        elif links:
            clause = CLAUSES["no_shared_file"] + " [linked: " + ", ".join(links) + "]"
        elif nonqual:
            clause = CLAUSES["revert_late"] + " [brought in: " + "; ".join(nonqual) + "]"
        else:
            clause = CLAUSES["nothing_to_inherit"]
        return counted, clause, (L.positives(shared) if counted else [])

    revert_readings = list(REVERT_READINGS) if has_contested else [None]
    results = {(m, rr): one(m, rr) for m in READINGS for rr in revert_readings}

    def entry(m, rr):
        counted, clause, pos = results[(m, rr)]
        return {"reading": m if rr is None else f"{m} + {rr}",
                "meaning": READINGS[m] + ("" if rr is None else "; and " + REVERT_READINGS[rr]),
                "ruled": m == RULED_MERGE_READING, "counted": counted, "clause": clause, "positives": pos}

    # The owner's ruling decides the merge reading; the others are kept for the record when they differ.
    unruled = [entry(m, rr) for m in READINGS if m != RULED_MERGE_READING for rr in revert_readings
               if results[(m, rr)][::2] != results[(RULED_MERGE_READING, rr)][::2]]
    for rr in revert_readings if bare else []:      # r4: a bare tracker key read as the registration words it
        alt = one(RULED_MERGE_READING, rr, bare_counts=True)
        if alt[::2] != results[(RULED_MERGE_READING, rr)][::2]:
            unruled.append({"reading": "registration_wording" if rr is None else f"registration_wording + {rr}",
                            "meaning": READINGS_JIRA["registration_wording"], "ruled": False,
                            "counted": alt[0], "clause": alt[1], "positives": alt[2]})
    ruled = {rr: results[(RULED_MERGE_READING, rr)] for rr in revert_readings}
    if len({(c, json.dumps(p)) for c, _cl, p in ruled.values()}) == 1:
        counted, clause, pos = ruled[revert_readings[0]]
        return counted, RULING_TAG + clause, pos, None, unruled
    # still open: a brought-in revert of post-cut code that quotes a ticket (not ruled)
    return None, "ambiguous: see `ambiguous`", [], [entry(RULED_MERGE_READING, rr) for rr in revert_readings], unruled


def expected_labels(plan, realised, snap_hash):
    """Expected HP label for every realised commit after the snapshot. Returns (labels, ambiguous).

    Derived from the signals the generator itself wrote into each message (never by parsing the text), and from
    the delivered history. `counted` is True or False with the clause that decides it, or None for a case the
    written rule leaves open, which is then listed under `ambiguous` with every reading. Positives are the
    snapshot's unit files only (the set SA3 ranks), by id and path at the snapshot; unit files a commit touches
    that did not exist at the snapshot are listed apart and are never positives."""
    L = _Labeller(plan, realised, snap_hash)
    snap_time = realised[L.cut]["time"]
    n_units = len(L.snap_path)
    labels, ambiguous = [], []
    for r in realised[L.cut + 1:]:
        lab = {"hash": r["hash"], "kind": r["kind"], "commits": r["lids"],
               "types": [L.entries[x].type for x in r["lids"]], "counted": False, "clause": None,
               "positives": [],
               "touched_unit_files_not_at_snapshot": [
                   {"id": f, "path": r["paths_by_id"][f]} for f in r["file_ids"]
                   if L.files[f].is_unit and f not in L.snap_path]}
        snap_units = [f for f in r["file_ids"] if f in L.snap_path]
        excluded = []                                  # every exclusion that applies, not just the first
        if r["kind"] == "side":
            excluded.append(CLAUSES["side"] + f" [merge {r['merge']}]")
        else:
            if r["time"] - snap_time > WINDOW_DAYS * hi.DAY:
                excluded.append(CLAUSES["window"])
            if len(snap_units) >= TREE_WIDE_SHARE * n_units and len(snap_units) >= TREE_WIDE_MIN:
                excluded.append(CLAUSES["tree_wide"] + f" [{len(snap_units)} of the snapshot's {n_units} unit files]")
            if r["kind"] == "merge" and len(r["brought"]) > MAX_BROUGHT:
                excluded.append(CLAUSES["over_cap"] + f" [{len(r['brought'])} brought in]")
        if excluded:
            lab["clause"] = ("; ".join(excluded) if r["kind"] != "merge"
                             else RULING_TAG + "; ".join(excluded))
        elif r["kind"] in ("direct", "squash"):
            tiers, contested, nonqual, keyword, bare = [], [], [], False, []
            for lid in r["lids"]:
                t, c, nq, kw = _entry_tiers(L.entries[lid], L.hash_of, L.cut_set)
                key = (L.entries[lid].signals or {}).get("bare_key")
                bare += [f"{lid}: {key}"] if key else []
                tiers += [(k, f"{lid}: {d}") for k, d in t]
                contested += [f"{lid}: {c}; {nq}"] if c else []
                nonqual += [f"{lid} {nq}"] if nq else []
                keyword |= kw
            if bare and not tiers:                     # r4: the registration's looser wording, not ruled
                lab["unruled_readings"] = [{
                    "reading": "registration_wording", "meaning": READINGS_JIRA["registration_wording"],
                    "ruled": False, "counted": True, "clause": CLAUSES["fixref"] + " [" + "; ".join(bare) + "]",
                    "positives": L.positives(snap_units)}]
            if tiers:
                lab["counted"] = True
                lab["clause"] = "; ".join(CLAUSES[k] + f" [{d}]" for k, d in tiers)
                lab["positives"] = L.positives(snap_units)
            elif contested:
                lab["counted"], lab["clause"] = None, "ambiguous: see `ambiguous`"
                ambiguous.append({"hash": r["hash"], "commits": r["lids"], "readings": [
                    {"reading": "reference_counts", "meaning": REVERT_READINGS["reference_counts"],
                     "counted": True, "clause": CLAUSES["fixref"] + " [" + "; ".join(contested) + "]",
                     "positives": L.positives(snap_units)},
                    {"reading": "nonqualifying_revert", "meaning": REVERT_READINGS["nonqualifying_revert"],
                     "counted": False, "clause": CLAUSES["revert_late"] + " [" + "; ".join(nonqual) + "]",
                     "positives": []}]})
            elif bare:                                 # r4: decided by the code's reading
                lab["clause"] = CLAUSES["jira_bare"] + " [" + "; ".join(bare) + "]"
            elif nonqual:
                lab["clause"] = CLAUSES["revert_late"] + " [" + "; ".join(nonqual) + "]"
            elif keyword:
                lab["clause"] = CLAUSES["keyword"]
            else:
                lab["clause"] = CLAUSES["none"]
        else:
            counted, clause, pos, readings, unruled = _merge_label(L, r)
            lab["counted"], lab["clause"], lab["positives"] = counted, clause, pos
            if unruled:
                lab["unruled_readings"] = unruled
            if readings:
                ambiguous.append({"hash": r["hash"], "commits": r["lids"], "readings": readings,
                                  "unruled_readings": unruled})
        labels.append(lab)
    return labels, ambiguous


def build(plan, realised, snap_hash, prior_hash) -> dict:
    """Assemble manifest.json."""
    cfg = plan.cfg
    files = plan.files
    by_hash = {r["hash"]: r for r in realised}
    snap_time = by_hash[snap_hash]["time"]
    delivered = {}
    for r in realised:
        for lid in r["lids"]:
            if r["kind"] != "merge":
                delivered[lid] = r["hash"]
    labels, ambiguous = expected_labels(plan, realised, snap_hash)

    # realised truth: true fixes after the snapshot, per unit file
    fixes_after, fixes_window = {}, {}
    for e in plan.entries:
        if e.type == "fix" and e.time > snap_time:
            for f in e.notes["defect_files"]:
                fixes_after[f] = fixes_after.get(f, 0) + 1
                if e.time - snap_time <= WINDOW_DAYS * hi.DAY:
                    fixes_window[f] = fixes_window.get(f, 0) + 1

    out_files = []
    for fid in sorted(files):
        r = files[fid]
        if r.created is None:
            continue
        rec = {"id": fid, "kind": r.kind, "language": r.lang, "is_unit": r.is_unit, "unit_reason": r.reason,
               "path_at_snapshot": plan.paths_at["snapshot"].get(fid),
               "path_at_prior": plan.paths_at["prior"].get(fid),
               "path_final": r.path if r.alive else None,
               "path_history": [{"path": p, "commit": c} for p, c in r.history],
               "created": r.created, "deleted": r.deleted}
        if r.targets is not None:
            rec["planted_density"] = {k: v for k, v in r.targets.items() if k != "loc"}
            rec["planted_loc_target"] = r.targets["loc"]
        if r.kind == "unit":
            rec["busyness"] = r.busy
            rec["true_fixes_after_snapshot"] = fixes_after.get(fid, 0)
            rec["true_fixes_in_window"] = fixes_window.get(fid, 0)
            if fid in plan.fix_weights:
                rec["fix_weight"] = plan.fix_weights[fid]
                rec["z"] = {k: plan.z[k][fid] for k in plan.z}
        rec["properties"] = {pt: plan.points[pt].get(fid) for pt in ("snapshot", "prior")}
        if r.generic_dir:
            rec["generic_dir"] = r.generic_dir
        stale = {callee: path for (caller, callee), path in sorted(plan.stale.items()) if caller == fid}
        if stale:
            rec["stale_imports"] = stale             # renames_after_snapshot: callee id -> path still imported
        out_files.append(rec)

    def resolve(msg):                                  # the same text generate.py wrote into the commit
        return re.sub(r"\{\{H(12|40):(\w+)\}\}", lambda m: delivered[m.group(2)][:int(m.group(1))], msg)

    commits = []
    for e in plan.entries:
        c = {"id": e.lid, "hash": delivered.get(e.lid), "time": e.time, "time_iso": iso(e.time), "type": e.type,
             "convention": e.convention, "author": e.author, "message": resolve(e.message),
             "files": sorted(e.changes), "file_ids": list(e.touched),
             "unit_files": sorted(p for p, f in e.path_fid.items() if files[f].is_unit),
             "caller_edit_ids": sorted(e.caller_edits),
             "after_snapshot": e.time > snap_time}
        if e.type == "fix":
            c["defect"] = e.defect
            c["defect_files"] = e.notes["defect_files"]
        if e.revert_target:
            tgt = next(x for x in plan.entries if x.lid == e.revert_target)
            c["revert_target"] = {"id": e.revert_target, "hash": delivered.get(e.revert_target),
                                  "before_snapshot": tgt.time <= snap_time}
        if e.notes:
            c["notes"] = e.notes
        commits.append(c)

    both = [f for f, p in plan.points["snapshot"].items() if files[f].is_unit and f in plan.points["prior"]]
    moved = [f for f in both if plan.points["snapshot"][f]["branches"] != plan.points["prior"][f]["branches"]]
    change = {"unit_files_at_both_points": len(both), "branch_density_changed": len(moved),
              "share": round(len(moved) / len(both), 4) if both else 0.0,
              "up": sum(1 for f in moved if plan.points["snapshot"][f]["branches"] > plan.points["prior"][f]["branches"]),
              "rule": "each unit file is scheduled to change with probability " + str(hi.CHURN_SHARE) + "; sign a "
                      "fair coin; capped, for both signs, by the branch units it could remove"}
    py = cfg.language == "python"
    return {
        "schema_version": SCHEMA_VERSION,
        "generator_version": hi.GENERATOR_VERSION,
        "arguments": cfg.args(),
        "constants": {"a": hi.A_SIZE, "b": hi.B_BUSY, "ordinary_size_exponent": hi.ORD_SIZE,
                      "ordinary_busyness_coefficient": hi.ORD_BUSY, "beta": dict(cfg.effects),
                      "tree_wide": [TREE_WIDE_SHARE, TREE_WIDE_MIN], "max_brought": MAX_BROUGHT,
                      "window_days": WINDOW_DAYS},
        "fix_model": "P(file i touched by a given fix after the snapshot) ∝ loc_i^a * exp(b*busyness_i) * "
                     "exp(sum_k beta_k * z_k(i)); z_k = within-repo z-score of property k's density at the snapshot "
                     "over the snapshot's unit files (d_branches: branch density at the snapshot minus at the prior "
                     "point, 0 for files absent at the prior point); before the snapshot all beta are 0",
        "risk_operations": ("not planted: Python files carry no pointer or allocation operations" if py else
                            "planted: pointer_ops (*cursor = ...) and alloc_ops (malloc/free calls) per file"),
        "pointer_mapping": (None if py else
                            "pointer_ops counts dereference writes (`*cursor = ...;`) only. pointer_declarations "
                            "counts declarations of a pointer (`long *data` in every definition, prototype and "
                            "extern; the locals `long *cursor`, `long *buf`). A keyword-family instrument that "
                            "counts pointer syntax is expected to see both, pointer_declarations + pointer_ops; an "
                            "instrument of pointer use, pointer_ops only. Which one the engine's pointer family "
                            "is, the generator cannot know: phase 2 must establish it."),
        "branch_mapping": ("branches = count of the keywords if, elif, for, while" if py else
                           "branches = count of the keywords if, for, while, switch (an `else if` carries one if)"),
        "points": {"snapshot": {"hash": snap_hash, "time": snap_time, "time_iso": iso(snap_time),
                                "commit": plan.snap_lid},
                   "prior": {"hash": prior_hash, "time": by_hash[prior_hash]["time"],
                             "time_iso": iso(by_hash[prior_hash]["time"]), "commit": plan.prior_lid,
                             "rule": "the last first-parent commit at or before 365 days before the snapshot",
                             "clamped_to_first_commit": by_hash[prior_hash]["time"] > snap_time - 365 * hi.DAY}},
        "mutations": plan.mutation_set.summary() | {"notes": plan.mutation_notes},
        "change_in_prior_year": change,
        "rulings": [RULING, RULING_JIRA],
        "counts": {"unit_files_at_snapshot": sum(1 for f in plan.points["snapshot"] if files[f].is_unit),
                   "logical_commits": len(plan.entries), "realised_commits": len(realised),
                   "true_fixes_after_snapshot": sum(1 for e in plan.entries if e.type == "fix" and e.time > snap_time)},
        "files": out_files,
        "commits": commits,
        "realised": [{k: v for k, v in r.items() if k not in ("paths_by_id",)} for r in realised],
        "expected_labels": labels,
        "ambiguous": ambiguous,
    }


def write(path, manifest: dict):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=False)
        fh.write("\n")


def load(path) -> dict:
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)
    if m.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"manifest schema {m.get('schema_version')} is not {SCHEMA_VERSION}")
    return m
