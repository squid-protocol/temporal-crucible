"""Named variants of the control repository, each re-creating a past fault from docs/STUDY_DEFECT_LOG.md.

A mutation changes one thing. It acts at one of four hooks, and draws only from its own random streams, so
everything it does not name stays as it was:

  layout     extra files                         vendored_half, test_fixtures, mixed_language
  timeline   commit types / extra commits        tickets_for_everything, renames_after_snapshot, huge_import_merge
  content    targets and wording of commits      reverts_of_new_code, sweep_labelled_fix, no_references
             (applied inside history.Simulator, which asks `active(name)`)
  delivery   how logical commits reach main      merge_workflow, bot_merges, squash_merges, huge_import_merge
"""
from __future__ import annotations

import math

import history as hi

REGISTRY = {
    "merge_workflow": {
        "truth": "planted properties and true fixes unchanged; the same logical commits reach main on branches joined by merge commits, so the units SA3 labels are the merges (labels: see `ambiguous`)",
        "change": "work arrives through merge commits; the fix reference is in the brought-in commit, not the merge",
        "log": [4, 17]},
    "bot_merges": {
        "truth": "as merge_workflow, and every merge is authored by a [bot] account; the expected labels are merge_workflow's (section 4 bars inheritance from a bot's commit, not by a bot-authored merge)",
        "change": "every merge is authored by an account matching the bot pattern (implies merge_workflow)",
        "log": [29], "implies": ["merge_workflow"]},
    "squash_merges": {
        "truth": "planted properties and true fixes unchanged; each squash commit carries every reference of the commits it squashes and is the labelled unit",
        "change": "the same work squashed, references kept in the squash message",
        "log": [17], "conflicts": ["merge_workflow", "bot_merges"]},
    "sweep_labelled_fix": {
        "truth": "planted properties and true fixes unchanged; the licence sweep now carries a fix reference; HP's tree-wide rule still removes it when it is tree-wide",
        "change": "the licence sweep's message says \"Fix\" and names a ticket", "log": [11]},
    "tickets_for_everything": {
        "truth": "planted properties and true fixes unchanged; each converted commit carries a ticket, so HP counts it although it fixes nothing",
        "change": "60% of ordinary commits become feature_with_ticket", "log": [30]},
    "reverts_of_new_code": {
        "truth": ("planted properties and true fixes unchanged; reverts in the outcome window target post-snapshot "
                  "commits, which HP does not count as reverts (HP_allreverts would); one that quotes a ticket from "
                  "its target's subject is listed under `ambiguous`"),
        "change": ("every revert in the outcome window targets a commit made after the snapshot, where one exists; the "
                   "exceptions are listed (changed.kept_pre_snapshot_target)"), "log": [16]},
    "vendored_half": {
        "truth": "unit files unchanged; the added files are imported code (is_unit false) that no .gitattributes line marks",
        "change": "half the unit-looking files sit under an imported third-party directory (src/contrib/)",
        "log": [29]},
    "test_fixtures": {
        "truth": "unit files unchanged; the added fixtures are test files (is_unit false)",
        "change": "a large directory of tiny generated test inputs in the main language", "log": [29]},
    "mixed_language": {
        "truth": "unit files unchanged; the added files are in the other language (is_unit false)",
        "change": "a second language holds 40% of the files", "log": [1, 6]},
    "renames_after_snapshot": {
        "truth": ("planted properties at both points and true fixes unchanged; renamed files' later paths differ from "
                  "their snapshot paths; the renames edit no other file, so Python callers' imports of a moved file go "
                  "stale (per file: `stale_imports`; per rename commit: notes.stale_imports)"),
        "change": ("20% of the snapshot's unit files are renamed in the outcome window; these renames edit no other "
                   "file"), "log": [39]},
    "no_references": {
        "truth": "planted properties and true fixes unchanged; no fix carries a fix reference, CVE id or trailer, so HP counts none",
        "change": "fixes carry keywords only", "log": [3]},
    "huge_import_merge": {
        "truth": "planted properties and true fixes unchanged (when the window holds fewer than 500 commits, filler note commits are added); the merge is over the 50-commit cap, so nothing it brings in is counted",
        "change": "one merge brings in 500 commits", "log": [17]},
}

GROUP_SIZES = [1, 2, 3, 4]
GROUP_WEIGHTS = [0.35, 0.30, 0.20, 0.15]
HUGE = 500


class MutationSet:
    def __init__(self, names):
        names = list(dict.fromkeys(names or []))
        for n in names:
            if n not in REGISTRY:
                raise ValueError(f"unknown mutation {n!r}; see --list-mutations")
        implied = []
        for n in list(names):
            for imp in REGISTRY[n].get("implies", []):
                if imp not in names:
                    names.append(imp)
                    implied.append(imp)
        for n in names:
            for c in REGISTRY[n].get("conflicts", []):
                if c in names:
                    raise ValueError(f"mutations {n} and {c} cannot be combined: both decide how work reaches main")
        self.names = sorted(names)
        self.requested = sorted(set(names) - set(implied))
        self.implied = sorted(implied)
        self.changed = {}

    def active(self, name):
        return name in self.names

    def record(self, name, key, value=None, add=None):
        """Note in the manifest what a mutation changed: append `value` to a list, or add `add` to a count."""
        d = self.changed.setdefault(name, {})
        if add is not None:
            d[key] = d.get(key, 0) + add
        else:
            d.setdefault(key, []).append(value)

    # -- layout -----------------------------------------------------------------------------------------
    def extend_layout(self, cfg, layout):
        units = [r for r in layout.files if r.kind == "unit" and r.initial]
        self._initial_units = len(units)
        lang2 = "c" if cfg.language == "python" else "python"
        if self.active("vendored_half"):
            rng = hi.stream(cfg.seed, "mutation", "vendored_half")
            libs = ["zlibx", "yamlite", "tinyjson"]
            added = []
            for i in range(len(units)):
                lib = libs[i % len(libs)]
                stem = f"{lib}_{layout.new_stem(rng)}"
                rec = layout._code(f"vc{i:04d}", "vendored_contrib", f"src/contrib/{lib}/{stem}{cfg.ext}", stem, rng)
                added.append(rec.fid)
            self.changed["vendored_half"] = {"files_added": len(added), "unit_files_unchanged": len(units)}
        if self.active("test_fixtures"):
            rng = hi.stream(cfg.seed, "mutation", "test_fixtures")
            n = int(round(1.5 * len(units)))
            for i in range(n):
                k = rng.randint(1, 4)
                if cfg.language == "python":
                    lines = [f"value_{j} = {rng.randint(0, 999)}" for j in range(k)] + [f"expected = value_0 * {rng.randint(2, 9)}"]
                else:
                    lines = [f"long value_{j} = {rng.randint(0, 999)};" for j in range(k)] + [f"long expected = {rng.randint(2, 9)};"]
                text = "\n".join(lines) + "\n"
                layout.files.append(hi.FileRec(f"f{i:04d}", "fixture", cfg.language,
                                               f"tests/fixtures/generated/case_{i:04d}{cfg.ext}", False,
                                               hi.UNIT_REASONS["fixture"], model=text))
            self.changed["test_fixtures"] = {"files_added": n}
        if self.active("mixed_language"):
            rng = hi.stream(cfg.seed, "mutation", "mixed_language")
            base = sum(1 for r in layout.files if r.kind != "unit" or r.initial)   # files of the initial import
            n = int(math.ceil(base * 0.4 / 0.6))
            ext2 = ".c" if lang2 == "c" else ".py"
            for i in range(n):
                d = rng.choice(layout.unit_dirs)
                stem = layout.new_stem(rng)
                sub = "native" if lang2 == "c" else "scripts"
                layout._code(f"ol{i:04d}", "other_language", f"{d}/{sub}/{stem}{ext2}", stem, rng, lang=lang2)
            self.changed["mixed_language"] = {"files_added": n, "language": lang2,
                                              "share_of_files": round(n / (base + n), 3)}

    # -- timeline ---------------------------------------------------------------------------------------
    def adjust_timeline(self, cfg, entries, snap_lid, prior_lid):
        snap_pos = next(i for i, e in enumerate(entries) if e.lid == snap_lid)
        snap_time = entries[snap_pos].time
        if self.active("tickets_for_everything"):
            conv = []
            for e in entries:
                if e.type == "ordinary" and hi.stream(cfg.seed, "mutation", "tickets", e.lid).random() < 0.6:
                    e.type = "feature_with_ticket"
                    e.notes["mutated_from"] = "ordinary"
                    conv.append(e.lid)
            n_ord = sum(1 for e in entries if e.type == "ordinary") + len(conv)
            self.changed["tickets_for_everything"] = {"converted": len(conv), "of_ordinary": n_ord}
        if self.active("renames_after_snapshot"):
            rng = hi.stream(cfg.seed, "mutation", "renames_after_snapshot")
            pre = entries[1:snap_pos + 1]
            units_at_snapshot = (self._initial_units + sum(e.type == "add" for e in pre)
                                 - sum(e.type == "delete" for e in pre))
            n = max(1, int(round(0.2 * units_at_snapshot)))
            post = list(range(snap_pos, len(entries) - 1))
            gaps = sorted(rng.sample(post, min(n, len(post))))
            out, k = [], 0
            gap_set = {}
            for g in gaps:
                gap_set[g] = gap_set.get(g, 0) + 1
            for i, e in enumerate(entries):
                out.append(e)
                for j in range(gap_set.get(i, 0)):
                    t = (e.time + entries[i + 1].time) // 2 + j
                    k += 1
                    author = hi.DEVELOPERS[hi.stream(cfg.seed, "author", f"M{k}").randrange(len(hi.DEVELOPERS))]
                    out.append(hi.Entry(f"M{k:04d}", "mrename", t, author, -1))
            entries = out
            self.changed["renames_after_snapshot"] = {"rename_commits_inserted": k, "target_share": 0.2}
        if self.active("huge_import_merge"):
            rng = hi.stream(cfg.seed, "mutation", "huge_import_merge")
            snap_pos = next(i for i, e in enumerate(entries) if e.lid == snap_lid)
            post = entries[snap_pos + 1:]
            if len(post) >= HUGE:
                off = rng.randrange(len(post) - HUGE + 1)
                block = post[off:off + HUGE]
                fillers = []
            else:
                block = post
                lo = snap_time + 1
                hi_t = max(e.time for e in post)
                used = {e.time for e in entries}
                fillers = []
                for k in range(HUGE - len(post)):
                    t = rng.randint(lo, hi_t)
                    while t in used:
                        t += 1
                    used.add(t)
                    author = hi.DEVELOPERS[hi.stream(cfg.seed, "author", f"H{k}").randrange(len(hi.DEVELOPERS))]
                    fillers.append(hi.Entry(f"H{k + 1:04d}", "filler", t, author, -1))
                entries = sorted(entries + fillers, key=lambda e: e.time)
                block = block + fillers
            for e in block:
                e.block = True
            self.changed["huge_import_merge"] = {"commits_brought_in": len(block), "filler_commits": len(fillers),
                                                 "first": min(block, key=lambda e: e.time).lid}
        return entries

    # -- delivery ---------------------------------------------------------------------------------------
    def delivery(self, cfg, entries, snap_lid, prior_lid):
        """Group logical commits into what reaches main: [{"kind": direct|merge|squash, "entries": [...]}].
        Groups never cross the snapshot or prior point, so both stay commits of the first-parent chain."""
        merge, squash = self.active("merge_workflow"), self.active("squash_merges")
        units, group = [], []
        state = {"size": None, "n": 0}

        def close():
            if group:
                units.append({"kind": "merge" if merge else "squash", "entries": list(group)})
                for name in (["merge_workflow"] + (["bot_merges"] if self.active("bot_merges") else [])
                             if merge else ["squash_merges"]):
                    self.record(name, "groups", add=1)
                    self.record(name, "logical_commits_grouped", add=len(group))
                group.clear()
            state["size"] = None

        def target_size():
            if state["size"] is None:
                state["n"] += 1
                rng = hi.stream(cfg.seed, "mutation", "grouping", state["n"])
                state["size"] = GROUP_SIZES[hi._weighted_index(rng, GROUP_WEIGHTS)]
            return state["size"]

        i = 0
        while i < len(entries):
            e = entries[i]
            if i == 0:
                units.append({"kind": "direct", "entries": [e]})
                i += 1
                continue
            if e.block:
                close()
                blk = []
                while i < len(entries) and entries[i].block:
                    blk.append(entries[i])
                    i += 1
                units.append({"kind": "merge", "entries": blk, "huge": True})
                self.record("huge_import_merge", "merges", add=1)
                if self.active("bot_merges"):
                    self.record("bot_merges", "groups", add=1)
                continue
            if merge or squash:
                if squash:
                    lids = {x.lid for x in group}
                    refs = {e.revert_target, e.notes.get("fixes_trailer_target")}
                    if e.type == "bot" or refs & lids:
                        close()
                    if e.type == "bot":
                        units.append({"kind": "direct", "entries": [e]})
                        i += 1
                        continue
                group.append(e)
                if len(group) >= target_size() or e.lid in (snap_lid, prior_lid):
                    close()
            else:
                units.append({"kind": "direct", "entries": [e]})
            i += 1
        close()
        return units

    def merge_author(self, cfg, k):
        if self.active("bot_merges"):
            return hi.MERGE_BOT
        return hi.DEVELOPERS[hi.stream(cfg.seed, "merge-author", k).randrange(len(hi.DEVELOPERS))]

    def summary(self):
        return {"applied": self.names, "requested": self.requested, "implied": self.implied,
                "definitions": {n: REGISTRY[n] for n in self.names}, "changed": self.changed}


def list_mutations() -> str:
    out = []
    for n, d in REGISTRY.items():
        out.append(f"{n:24s} log {','.join(map(str, d['log'])):6s} {d['change']}")
    return "\n".join(out)
