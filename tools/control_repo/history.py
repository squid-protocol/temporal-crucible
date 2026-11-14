"""The commit timeline: layout, commit types and times, and the simulation that edits the files.

Nothing here touches git. `plan(cfg)` returns a `Plan`: the files (with their models and planted properties at
the snapshot and prior points), the logical commits in time order (each with its true type, message parts,
signals for labelling and the exact file changes it makes), and the realised truth. `generate.py` writes the
plan into a repository; `manifest.py` turns it into manifest.json.

Random streams. Every random choice is drawn from a stream named for its purpose and the entity it concerns,
`random.Random(f"{seed}:{purpose}:{entity}")`: one stream per file for its structure, size and busyness; one
per commit for ordinary file selection, for non-unit touches, for fix targets, for message wording; one per
mutation. So a change to one thing (an effect size, a mutation) cannot shift the draws of anything else.

Selection rules (the negative-control mechanism, restated in README.md):
* ordinary and feature commits pick unit files with weight  loc_p^ORD_SIZE * exp(ORD_BUSY * busyness),
  loc_p the file's planned size (drawn before any structure exists, so no density can leak in through it);
* fixes before the snapshot pick with weight              loc^A * exp(B * busyness);
* fixes after the snapshot pick with weight               loc_s^A * exp(B * busyness) * exp(sum_k beta_k z_k),
  z_k the within-repo z-score of property k's density at the snapshot (loc_s = loc at the snapshot);
* nothing else in the history depends on a planted property, and no edit changes structure except the
  prior-year structural changes, whose sign is a fair coin per file drawn from the file's own stream.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field

import codegen as cg

GENERATOR_VERSION = "1.2.0"
T0 = 1577836800                       # 2020-01-01T00:00:00Z
DAY = 86400
A_SIZE, B_BUSY = 0.6, 1.0             # fix weight: loc^a * exp(b * busyness)
ORD_SIZE, ORD_BUSY = 0.6, 1.0         # ordinary weight: loc^c * exp(d * busyness)
CHURN_SHARE = 0.90                    # share of unit files scheduled to change structure in the prior year
PROFILES = {"small": {"files": 60, "commits_per_file": 5.0},
            "default": {"files": 400, "commits_per_file": 7.5}}
EFFECT_NAMES = ("branches", "max_nesting", "calls_in", "calls_out", "state_writes_in_branches", "d_branches")
C_EFFECT_NAMES = ("pointer_ops", "alloc_ops")
DEVELOPERS = ["Ada Moreau <ada.moreau@example.invalid>", "Bram Okafor <bram.okafor@example.invalid>",
              "Chen Wei <chen.wei@example.invalid>", "Dana Kowalski <dana.k@example.invalid>",
              "Emil Haddad <emil.haddad@example.invalid>", "Farah Lind <farah.lind@example.invalid>",
              "Gus Tanaka <gus.tanaka@example.invalid>", "Hana Novak <hana.novak@example.invalid>"]
DEP_BOT = "dependabot[bot] <dependabot-bot@example.invalid>"
MERGE_BOT = "merge-queue[bot] <merge-queue-bot@example.invalid>"
BOT_PATTERN = "[bot]"


def stream(seed: int, *parts) -> random.Random:
    """A named, seeded random stream (string seeding is stable across Python runs and versions >= 3.2)."""
    return random.Random(":".join([str(seed)] + [str(p) for p in parts]))


@dataclass
class Config:
    seed: int
    language: str = "python"
    files: int | None = None
    years: float = 4.0
    profile: str = "default"
    effects: dict = field(default_factory=dict)
    mutations: tuple = ()

    def __post_init__(self):
        prof = PROFILES[self.profile]
        if self.files is None:
            self.files = prof["files"]
        self.commits = int(round(self.files * prof["commits_per_file"]))
        allowed = EFFECT_NAMES + (C_EFFECT_NAMES if self.language == "c" else ())
        for k in self.effects:
            if k not in allowed:
                raise ValueError(f"unknown effect {k!r} for language {self.language}; allowed: {allowed}")
        self.effects = {k: float(self.effects.get(k, 0.0)) for k in allowed}

    @property
    def ext(self):
        return ".py" if self.language == "python" else ".c"

    def args(self) -> dict:
        return {"seed": self.seed, "language": self.language, "files": self.files, "years": self.years,
                "profile": self.profile, "effects": dict(self.effects), "mutations": list(self.mutations),
                "commits_planned": self.commits}


# ----------------------------------------------------------------------------------------------- files
@dataclass
class FileRec:
    fid: str
    kind: str                 # unit test vendor docs readme generated licence attributes deps export_ignored ...
    lang: str | None
    path: str
    is_unit: bool
    reason: str
    model: object = None      # cg.CodeFile, or a list of lines for docs, or a str for fixed text files
    busy: float = 0.0
    targets: dict | None = None
    initial: bool = True
    alive: bool = False
    created: str | None = None
    deleted: str | None = None
    history: list = field(default_factory=list)   # [(path, commit id)]
    text: str = ""
    loc: int = 0              # line count of `text`
    ord_weight: float = 0.0   # ordinary-selection weight (constant: planned size and busyness)
    planned_dir: str = ""
    stem: str = ""

    @property
    def is_code(self):
        return isinstance(self.model, cg.CodeFile)


UNIT_REASONS = {
    "unit": "source file in the repo's language, not test/vendored/docs/example/generated",
    "test": "test file (under tests/)",
    "vendor": "vendored: vendor/thirdparty/ is marked linguist-vendored in .gitattributes",
    "docs": "documentation",
    "readme": "documentation",
    "generated": "generated file (its header says it is generated by tablegen)",
    "licence": "licence text, not source",
    "attributes": ".gitattributes, not source",
    "deps": "dependency list, not source",
    "export_ignored": "export-ignore in .gitattributes: absent from `git archive` of the snapshot (see DECISIONS.md)",
    "fixture": "test fixture (under tests/)",
    "vendored_contrib": "imported third-party code (src/contrib/), vendored although no attribute marks it",
    "other_language": "not the repo's language",
    "imported_note": "documentation (a note brought in by the huge import merge)",
}


def _zipf_weights(rng, n, s=1.2):
    ranks = list(range(1, n + 1))
    rng.shuffle(ranks)
    return [1.0 / r ** s for r in ranks]


def _weighted_index(rng, weights):
    total = sum(weights)
    x = rng.random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if x < acc:
            return i
    return len(weights) - 1


def sample_without_replacement(rng, items, weights, k):
    items, weights = list(items), list(weights)
    out = []
    for _ in range(min(k, len(items))):
        i = _weighted_index(rng, weights)
        out.append(items.pop(i))
        weights.pop(i)
    return out


class Layout:
    """Directories and the planned file list. Unit sizes and directories come from the layout stream; each
    file's structure from its own stream."""

    def __init__(self, cfg: Config, n_adds: int):
        self.cfg = cfg
        rng = stream(cfg.seed, "layout")
        n = cfg.files
        n_docs, n_tests = max(2, round(0.05 * n)), max(3, round(0.12 * n))
        n_vendor, n_xign = max(2, round(0.06 * n)), max(2, round(0.02 * n))
        n_units_initial = max(20, n - 5 - n_docs - n_tests - n_vendor - n_xign)
        n_units = n_units_initial + n_adds
        # directories: a few big, many small, two to three deep under src/
        n_dirs = max(4, round(n_units / 9))
        tops = rng.sample(cg.DIR_WORDS, max(2, min(8, round(n_dirs / 3))))
        dirs = []
        while len(dirs) < n_dirs:
            if dirs and rng.random() < 0.3:
                parent = rng.choice([d for d in dirs if d.count("/") == 2] or dirs)
                if parent.count("/") >= 3:
                    continue
            else:
                parent = "src/" + rng.choice(tops)
            name = rng.choice(cg.DIR_WORDS)
            cand = f"{parent}/{name}"
            if cand not in dirs and name not in parent.split("/"):
                dirs.append(cand)
        self.unit_dirs = sorted(dirs)
        dir_w = _zipf_weights(rng, len(self.unit_dirs))
        self.stems = set()
        self.files: list[FileRec] = []
        ext = cfg.ext
        # unit files: lognormal sizes, with a share of exact ties copied from another file
        sizes = []
        for i in range(n_units):
            if sizes and rng.random() < 0.15:
                sizes.append(rng.choice(sizes))
            else:
                sizes.append(int(round(min(3000, max(12, 70 * math.exp(rng.gauss(0, 0.95)))))))
        for i in range(n_units):
            d = self.unit_dirs[_weighted_index(rng, dir_w)]
            stem = self.new_stem(rng)
            fid = f"u{i:04d}"
            rec = FileRec(fid, "unit", cfg.language, f"{d}/{stem}{ext}", True, UNIT_REASONS["unit"],
                          initial=i < n_units_initial, planned_dir=d, stem=stem)
            srng = stream(cfg.seed, "density", fid)
            rec.targets = cg.draw_targets(srng, cfg.language, sizes[i])
            rec.busy = stream(cfg.seed, "busy", fid).gauss(0.0, 1.0)
            self.files.append(rec)
        # other kinds
        top0 = sorted(tops)[0]
        for i in range(n_xign):
            stem = self.new_stem(rng)
            self._code(f"x{i:02d}", "export_ignored", f"src/{top0}/experimental/{stem}{ext}", stem, rng)
        for i in range(n_tests):
            stem = "test_" + self.new_stem(rng)
            self._code(f"t{i:03d}", "test", f"tests/{stem}{ext}", stem, rng, scale=0.6)
        for i in range(n_vendor):
            stem = "mini_" + self.new_stem(rng)
            self._code(f"v{i:02d}", "vendor", f"vendor/thirdparty/libmini/{stem}{ext}", stem, rng)
        for i in range(n_docs):
            name = rng.choice(cg.DIR_WORDS)
            path = f"docs/{name}_{i}.md"
            self.files.append(FileRec(f"d{i:02d}", "docs", None, path, False, UNIT_REASONS["docs"],
                                      model=[f"# {name.capitalize()}", ""] + cg.doc_lines(rng, rng.randint(4, 12))))
        gen_dir = rng.choice(self.unit_dirs)
        self.files.append(FileRec("gen", "generated", cfg.language, f"{gen_dir}/gen_tables{ext}", False,
                                  UNIT_REASONS["generated"], model=cg.generated_table(cfg.language, 40, rng)))
        self.files.append(FileRec("lic", "licence", None, "LICENSE", False, UNIT_REASONS["licence"],
                                  model=cg.LICENCE_TEXT))
        self.files.append(FileRec("attr", "attributes", None, ".gitattributes", False, UNIT_REASONS["attributes"],
                                  model=f"vendor/thirdparty/** linguist-vendored\nsrc/{top0}/experimental/** export-ignore\n"))
        self.files.append(FileRec("readme", "readme", None, "README.md", False, UNIT_REASONS["readme"],
                                  model=["# Example project", "", "A generated control repository."]))
        deps_path = "requirements.txt" if cfg.language == "python" else "deps.txt"
        self.files.append(FileRec("deps", "deps", None, deps_path, False, UNIT_REASONS["deps"],
                                  model={"alpha-lib": [1, 2, 0], "beta-codec": [0, 9, 3], "gamma-net": [2, 0, 1],
                                         "delta-store": [3, 1, 4]}))
        self.top0 = top0

    def new_stem(self, rng):
        for k in range(1000):
            stem = f"{rng.choice(cg.FILE_NOUNS)}_{rng.choice(cg.FILE_ROLES)}"
            if k > 50:
                stem += f"{k}"
            if stem not in self.stems:
                self.stems.add(stem)
                return stem
        raise RuntimeError("stem space exhausted")

    def _code(self, fid, kind, path, stem, rng, scale=1.0, lang=None):
        lang = lang or self.cfg.language
        rec = FileRec(fid, kind, lang, path, False, UNIT_REASONS[kind], stem=stem)
        loc = int(round(min(1500, max(12, 60 * scale * math.exp(rng.gauss(0, 0.8))))))
        rec.targets = cg.draw_targets(stream(self.cfg.seed, "density", fid), lang, loc)
        self.files.append(rec)
        return rec


# ------------------------------------------------------------------------------------------- timeline
@dataclass
class Entry:
    """One logical commit: what happens, independent of how it is delivered (direct, merge, squash)."""
    lid: str
    type: str
    time: int
    author: str
    index: int                # position in the base timeline (mutation-inserted commits: -1)
    sweep: dict | None = None
    convention: str | None = None
    message: str = ""         # may hold {{H40:lid}} / {{H12:lid}} placeholders, filled at write time
    signals: dict = field(default_factory=dict)
    changes: dict = field(default_factory=dict)   # path -> text, or None for a deletion
    touched: list = field(default_factory=list)   # file ids
    path_fid: dict = field(default_factory=dict)  # every changed path -> the file id it belongs to
    defect: str | None = None
    revert_target: str | None = None
    edits: list = field(default_factory=list)     # literal edits, for reverts
    structural: bool = False
    notes: dict = field(default_factory=dict)
    block: bool = False       # inside the huge_import_merge block
    caller_edits: list = field(default_factory=list)   # file ids edited only because they call a moved/deleted file


SWEEPS_SMALL = [(0.35, "reformat", "Apply code formatter"), (0.86, "licence", "Add SPDX licence headers"),
                (0.93, "reformat", "Fix lint")]
SWEEPS_DEFAULT = [(0.30, "reformat", "Apply code formatter"), (0.60, "reformat", "Fix lint warnings"),
                  (0.86, "licence", "Add SPDX licence headers"), (0.93, "reformat", "Fix lint")]


def type_counts(n: int) -> dict:
    return {"add": max(2, round(n * 0.012)), "delete": max(1, round(n * 0.006)),
            "rename": max(2, round(n * 0.008)), "bot": max(3, round(n * 0.04)),
            "revert": max(3, round(n * 0.015)), "feature_with_ticket": max(3, round(n * 0.05)),
            "fix": round(n * 0.2), "vendor_import": 1 if n < 1000 else 3}


def build_timeline(cfg: Config):
    """Base commit types and times. Returns (entries, snapshot index, prior index)."""
    n = cfg.commits
    rng = stream(cfg.seed, "timeline")
    counts = type_counts(n)
    sweeps = SWEEPS_SMALL if n < 1000 else SWEEPS_DEFAULT
    fixed = {0: ("add", None)}
    for frac, kind, msg in sweeps:
        fixed[round(frac * (n - 1))] = ("sweep", {"kind": kind, "message": msg})
    free = [i for i in range(n) if i not in fixed]
    bag = []
    for t, c in counts.items():
        bag += [t] * c
    bag += ["ordinary"] * (len(free) - len(bag))
    if len(bag) > len(free):
        raise ValueError("too few commits for the planned types")
    rng.shuffle(bag)
    types = dict(fixed)
    for i, t in zip(free, bag):
        types[i] = (t, None)
    snap = math.ceil(0.8 * n) - 1
    # reverts need something to revert: none in the first commits, at least one on each side of the snapshot
    def swap_into(pos_range, want):
        j = next((j for j in pos_range if types[j][0] == "ordinary"), None)
        src = next((i for i in range(6, n) if types[i][0] == want and i not in pos_range), None)
        if j is not None and src is not None:
            types[j], types[src] = types[src], types[j]
    for i in range(6):
        if types[i][0] == "revert":
            j = next(j for j in range(6, n) if types[j][0] == "ordinary")
            types[i], types[j] = types[j], types[i]
    if not any(types[i][0] == "revert" for i in range(snap + 4, n)):
        swap_into(range(snap + 4, n), "revert")
    if not any(types[i][0] == "revert" for i in range(6, snap + 1)):
        swap_into(range(6, snap + 1), "revert")
    # times: exponential gaps scaled to the span, at least a minute apart
    span = int(cfg.years * 365.25 * DAY)
    gaps = [rng.expovariate(1.0) for _ in range(n - 1)]
    scale = (span - 60 * (n - 1)) / sum(gaps)
    times = [T0]
    for g in gaps:
        times.append(times[-1] + 60 + int(g * scale))
    entries = []
    for i in range(n):
        t, extra = types[i]
        arng = stream(cfg.seed, "author", i)
        author = DEP_BOT if t == "bot" else DEVELOPERS[arng.randrange(len(DEVELOPERS))]
        entries.append(Entry(f"L{i:05d}", t, times[i], author, i, sweep=extra))
    cut = times[snap] - 365 * DAY
    prior = max([i for i in range(n) if times[i] <= cut], default=0)   # 0: --years too short, clamped
    return entries, snap, prior


# ------------------------------------------------------------------------------------------ simulation
class Plan:
    """Everything `generate` and `manifest` need."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.files: dict[str, FileRec] = {}
        self.entries: list[Entry] = []
        self.snap_lid = self.prior_lid = None
        self.points = {}          # "snapshot"/"prior" -> {fid: props}
        self.paths_at = {}        # "snapshot"/"prior" -> {fid: path}
        self.fix_weights = {}
        self.z = {}
        self.mutation_notes = {}
        self.stale = {}           # (caller, callee) -> stale import path, filled by the simulator
        self.layout = None


class Simulator:
    def __init__(self, cfg: Config, mut):
        self.cfg = cfg
        self.mut = mut
        self.plan = Plan(cfg)
        self.lit = 100            # unique literal values for tweaks, in timeline order
        self.defects = 0
        self.vendor_version = 1

    # -- helpers ---------------------------------------------------------------------------------------
    @property
    def files(self):
        return self.plan.files

    def path_of(self, fid):
        return self.files[fid].path

    def import_paths_for(self, caller_fid):
        """How file `caller_fid` imports other files: by their current path, except where a
        renames_after_snapshot move left this caller's import stale (`self.stale[(caller, callee)]`)."""
        return lambda fid: self.stale.get((caller_fid, fid)) or self.files[fid].path

    def next_lit(self):
        self.lit += 1
        return self.lit

    def alive_units(self):
        return [r for r in self.files.values() if r.alive and r.is_unit]

    def render(self, rec: FileRec) -> str:
        m = rec.model
        if isinstance(m, cg.CodeFile):
            return cg.render(m, self.import_paths_for(rec.fid))
        if isinstance(m, list):
            return "\n".join(m) + "\n"
        if isinstance(m, dict):
            return "".join(f"{k}=={'.'.join(map(str, v))}\n" for k, v in sorted(m.items()))
        return m

    def callers_of(self, fid):
        return [r for r in self.alive_units() if r.fid != fid and any(f == fid for f, _ in cg.ext_refs(r.model))]

    def pick_call_target_factory(self, self_fid, pool):
        """Callee choice for a new call site: unit file with weight planned loc * attractiveness."""
        cands = [r for r in pool if r.fid != self_fid]
        weights = [r.targets["loc"] * r.targets["calls_in_attract"] for r in cands]

        def pick(rng):
            if not cands:
                return None
            r = cands[_weighted_index(rng, weights)]
            fn = r.model.functions[rng.randrange(len(r.model.functions))]
            return (r.fid, fn.name)
        return pick

    def start_models(self, recs):
        """Phase one for a batch of files: function names, so the batch can call each other."""
        self._rngs = getattr(self, "_rngs", {})
        for rec in recs:
            rng = stream(self.cfg.seed, "structure", rec.fid)
            self._rngs[rec.fid] = rng
            rec.model = cg.start_code_file(rng, rec.fid, rec.lang, rec.kind, rec.stem, rec.targets)

    def fill_model(self, rec: FileRec, call_pool=None):
        pick = self.pick_call_target_factory(rec.fid, call_pool) if call_pool is not None else None
        cg.fill_code_file(self._rngs.pop(rec.fid), rec.model, rec.targets, pick)

    def commit_files(self, e: Entry, fids, old_paths=None):
        """Re-render `fids`, record what changed in the entry. `old_paths` maps fid -> path before a rename."""
        old_paths = old_paths or {}
        for fid in dict.fromkeys(fids):
            rec = self.files[fid]
            if fid in old_paths and old_paths[fid] != rec.path:
                e.changes[old_paths[fid]] = None
                e.path_fid[old_paths[fid]] = fid
            if not rec.alive:
                if rec.text:
                    e.changes[rec.path] = None
                    e.path_fid[rec.path] = fid
                    rec.text, rec.loc = "", 0
                if fid not in e.touched:
                    e.touched.append(fid)
                continue
            text = self.render(rec)
            if text != rec.text or fid in old_paths:
                e.changes[rec.path] = text
                e.path_fid[rec.path] = fid
                rec.text = text
                rec.loc = text.count("\n")
                if fid not in e.touched:
                    e.touched.append(fid)

    def ordinary_weights(self, units):
        """Ordinary selection weight: planned size ** ORD_SIZE * exp(ORD_BUSY * busyness). The planned size
        (`targets["loc"]`) and busyness are drawn from their own streams before any structure exists, so this
        weight cannot depend on a planted density, even through a file's realised length."""
        for r in units:
            if not r.ord_weight:
                r.ord_weight = r.targets["loc"] ** ORD_SIZE * math.exp(ORD_BUSY * r.busy)
        return [r.ord_weight for r in units]

    # -- measurement -----------------------------------------------------------------------------------
    def measure_all(self):
        out = {}
        calls_in = {}
        for r in self.files.values():
            if r.alive and r.is_code and r.is_unit:
                for fid, _name in cg.ext_refs(r.model):
                    calls_in[fid] = calls_in.get(fid, 0) + 1
        for r in self.files.values():
            if r.alive and r.is_code:
                p = cg.measure(r.model, r.text)
                p["calls_in"] = calls_in.get(r.fid, 0)
                loc = max(1, p["loc"])
                dens = {"branches": p["branches"] / loc, "max_nesting": float(p["max_nesting"]),
                        "calls_in": p["calls_in"] / loc, "calls_out": p["calls_out"] / loc,
                        "state_writes_in_branches": p["state_writes_in_branches"] / loc}
                if r.lang == "c":
                    dens["pointer_ops"] = p["pointer_ops"] / loc
                    dens["alloc_ops"] = p["alloc_ops"] / loc
                p["density"] = dens
                out[r.fid] = p
        return out

    def capture(self, name, lid):
        self.plan.points[name] = self.measure_all()
        self.plan.paths_at[name] = {r.fid: r.path for r in self.files.values() if r.alive}
        if name == "snapshot":
            self.plan.snap_lid = lid
        else:
            self.plan.prior_lid = lid

    def compute_fix_weights(self):
        """Post-snapshot fix weights: loc^a * exp(b busy) * exp(sum beta_k z_k), z over unit files at the
        snapshot, from densities at the snapshot (d_branches: change since the prior point)."""
        snap, prior = self.plan.points["snapshot"], self.plan.points.get("prior", {})
        units = [fid for fid in snap if self.files[fid].is_unit]
        dens = {}
        for k, beta in self.cfg.effects.items():
            if k == "d_branches":
                vals = [snap[f]["density"]["branches"] - prior[f]["density"]["branches"] if f in prior else 0.0
                        for f in units]
            else:
                vals = [snap[f]["density"][k] for f in units]
            mu = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
            dens[k] = {f: ((v - mu) / sd if sd > 0 else 0.0) for f, v in zip(units, vals)}
        self.plan.z = dens
        w = {}
        for f in units:
            lin = sum(beta * dens[k][f] for k, beta in self.cfg.effects.items())
            w[f] = snap[f]["loc"] ** A_SIZE * math.exp(B_BUSY * self.files[f].busy) * math.exp(lin)
        self.plan.fix_weights = w

    # -- the run ---------------------------------------------------------------------------------------
    def run(self, entries, snap_lid, prior_lid, layout):
        self.plan.layout = layout
        for rec in layout.files:
            self.files[rec.fid] = rec
        self.window = False
        self.churn = {}
        self.sched = {}           # logical id -> unit files scheduled for a structural edit in that commit
        self.stale = self.plan.stale   # (caller, callee) -> the path the caller still imports the callee by
        snap_time = next(e.time for e in entries if e.lid == snap_lid)
        self.snap_time = snap_time
        self.prior_time = next(e.time for e in entries if e.lid == prior_lid)
        self.after_snapshot = False
        for e in entries:
            if e.time > self.prior_time and not self.window and not self.after_snapshot:
                self.start_churn_window(entries)
            handler = getattr(self, "do_" + e.type)
            if e.lid == entries[0].lid:
                self.do_initial(e)
            else:
                handler(e)
            self.plan.entries.append(e)
            if e.lid == prior_lid:
                self.capture("prior", e.lid)
            if e.lid == snap_lid:
                self.capture("snapshot", e.lid)
                self.compute_fix_weights()
                self.window = False
                self.after_snapshot = True
        return self.plan

    def start_churn_window(self, entries):
        """Plan the structural change of the year before the snapshot, from each file's own stream and nothing
        else: with probability CHURN_SHARE the file changes; the sign is a fair coin; it is scheduled into
        1 + floor(Exp(mean 1.5)) ordinary commits of the window drawn uniformly. The schedule never looks at
        structure, size or busyness, so the activity it adds is blind to every planted property. What does
        depend on structure is how far the file can move: each scheduled touch applies max(1, round(0.1 x
        branches)) steps, and the total is capped, for both signs alike, by the branch units the file could
        remove (`codegen.removable_units`); a file with none does not change."""
        self.window = True
        window = [e.lid for e in entries if self.prior_time < e.time <= self.snap_time
                  and e.type in ("ordinary", "feature_with_ticket")]
        for r in self.alive_units():
            rng = stream(self.cfg.seed, "churn", r.fid)
            changes = rng.random() < CHURN_SHARE
            sign = 1 if rng.random() < 0.5 else -1
            n_touch = min(len(window), 1 + int(rng.expovariate(1 / 1.5)))
            if not changes or not window:
                continue
            for lid in rng.sample(window, n_touch):
                self.sched.setdefault(lid, []).append(r.fid)
            b = cg.measure(r.model)["branches"]
            per_touch = max(1, round(0.1 * b))
            m = len(cg.removable_units(r.model))
            self.churn[r.fid] = [sign, min(n_touch * per_touch, m), per_touch]

    # -- commit types ----------------------------------------------------------------------------------
    def do_initial(self, e: Entry):
        layout = self.plan.layout
        initial_units = [r for r in layout.files if r.kind == "unit" and r.initial]
        batch = [r for r in layout.files if r.targets is not None and r.model is None
                 and (r.kind != "unit" or r.initial)]
        self.start_models(batch)
        for r in batch:
            self.fill_model(r, initial_units if r.kind == "unit" else None)
        for r in layout.files:
            if r.kind != "unit" or r.initial:
                r.alive = True
                r.created = e.lid
                r.history.append((r.path, e.lid))
        self.commit_files(e, [r.fid for r in layout.files if r.alive])
        e.message = "Initial import"
        e.type = "add"

    def do_add(self, e: Entry):
        pending = [r for r in self.plan.layout.files if r.kind == "unit" and not r.initial and r.created is None]
        if not pending:
            return self.do_ordinary(e)
        r = pending[0]
        self.start_models([r])
        self.fill_model(r, self.alive_units())
        r.alive, r.created = True, e.lid
        r.history.append((r.path, e.lid))
        self.commit_files(e, [r.fid])
        e.message = f"Add {r.stem.replace('_', ' ')} module"

    def _touch_nonunits(self, e, rng, room):
        """Sometimes also edit a test file and/or a docs file, while the commit stays within 10 files."""
        if rng.random() < 0.3 and room > 0:
            room -= 1
            tests = [r for r in self.files.values() if r.alive and r.kind == "test"]
            if tests:
                r = tests[rng.randrange(len(tests))]
                sid, old, new = cg.tweak(rng, r.model, self.next_lit())
                e.edits.append(("code", r.fid, sid, old, new))
                self.commit_files(e, [r.fid])
        if rng.random() < 0.08 and room > 0:
            docs = [r for r in self.files.values() if r.alive and r.kind == "docs"]
            if docs:
                r = docs[rng.randrange(len(docs))]
                i = rng.randrange(2, len(r.model))
                old = r.model[i]
                r.model[i] = cg.doc_lines(rng, 1)[0].rstrip(".") + f" (rev {self.next_lit()})."
                e.edits.append(("doc", r.fid, i, old, r.model[i]))
                self.commit_files(e, [r.fid])

    def do_ordinary(self, e: Entry):
        rng = stream(self.cfg.seed, "ordinary", e.lid)
        units = self.alive_units()
        k = 1
        while k < 10 and rng.random() < 0.45:
            k += 1
        scheduled = [self.files[f] for f in self.sched.get(e.lid, []) if self.files[f].alive][:10]
        pool = [r for r in units if r not in scheduled]
        chosen = sample_without_replacement(rng, pool, self.ordinary_weights(pool), min(k, 10 - len(scheduled)))
        chosen += scheduled
        for r in chosen:
            for _ in range(1 + (rng.random() < 0.3)):
                sid, old, new = cg.tweak(rng, r.model, self.next_lit())
                e.edits.append(("code", r.fid, sid, old, new))
        for r in scheduled:                          # the year-before-snapshot structural change
            plan = self.churn[r.fid]
            for _ in range(min(plan[2], plan[1])):
                plan[1] -= 1
                if cg.structure_step(rng, r.model, plan[0], self.next_lit()):
                    e.structural = True
                    e.notes.setdefault("structure_steps", []).append([r.fid, plan[0]])
        if scheduled:
            e.notes["scheduled_structure_edits"] = [r.fid for r in scheduled]
        self.commit_files(e, [r.fid for r in chosen])
        self._touch_nonunits(e, stream(self.cfg.seed, "nonunit", e.lid), 10 - len(chosen))
        lab = stream(self.cfg.seed, "label", e.lid)
        stem = chosen[0].stem.replace("_", " ") if chosen else "core"
        if e.type == "feature_with_ticket":
            e.convention = "ticket_feature"
            e.message = f"Fixed #{lab.randint(100, 9999)} -- Added {lab.choice(cg.DOC_NOUNS)} support to {stem}."
            e.signals = {"fixref": "issue", "keyword": True}
        else:
            verb = lab.choice(["Add", "Refactor", "Update", "Improve", "Simplify", "Extend", "Tidy", "Rework"])
            e.convention = "plain"
            e.message = f"{verb} {stem} {lab.choice(cg.DOC_NOUNS)}"

    do_feature_with_ticket = do_ordinary

    def do_fix(self, e: Entry):
        rng = stream(self.cfg.seed, "fix", e.lid)
        if self.after_snapshot:
            pool = [fid for fid in self.plan.fix_weights if self.files[fid].alive]
            weights = [self.plan.fix_weights[f] for f in pool]
            recs = [self.files[f] for f in pool]
        else:
            recs = self.alive_units()
            weights = [max(1, r.loc) ** A_SIZE * math.exp(B_BUSY * r.busy) for r in recs]
        x = rng.random()
        k = 1 if x < 0.7 else 2 if x < 0.9 else 3
        chosen = sample_without_replacement(rng, recs, weights, k)
        self.defects += 1
        e.defect = f"D{self.defects:04d}"
        e.notes["defect_files"] = [r.fid for r in chosen]
        intro = self.last_touch(chosen[0].fid)
        for r in chosen:
            sid, old, new = cg.tweak(rng, r.model, self.next_lit(), prefer_cond=True)
            e.edits.append(("code", r.fid, sid, old, new))
        self.commit_files(e, [r.fid for r in chosen])
        if rng.random() < 0.35:
            tests = [r for r in self.files.values() if r.alive and r.kind == "test"]
            if tests:
                t = tests[rng.randrange(len(tests))]
                sid, old, new = cg.tweak(rng, t.model, self.next_lit())
                self.commit_files(e, [t.fid])
        lab = stream(self.cfg.seed, "label", e.lid)
        conv = ["issue", "trailer", "cve", "jira", "keyword", "silent"][
            _weighted_index(lab, [0.30, 0.10, 0.08, 0.12, 0.25, 0.15])]
        e.notes["base_convention"] = conv
        if self.mut.active("no_references"):
            self.mut.record("no_references", "fixes_rewritten", add=1)
            if conv not in ("keyword", "silent"):
                self.mut.record("no_references", "fixes_that_lost_a_reference", add=1)
            conv = "keyword"
        stem = chosen[0].stem.replace("_", " ")
        what = lab.choice(["empty input", "short frames", "a zero count", "an unknown key", "a stale cursor",
                           "an overlong header"])
        num = lab.randint(100, 9999)
        e.convention = conv
        if conv == "issue":
            e.message = f"Handle {what} in {stem}\n\nFixes #{num}"
            e.signals = {"fixref": "issue"}
        elif conv == "trailer":
            subj = self.subject_of(intro)
            e.message = f"{stem}: reject {what}\n\nFixes: {{{{H12:{intro}}}}} (\"{subj}\")"
            e.signals = {"fixref": "Fixes: trailer"}
            e.notes["fixes_trailer_target"] = intro
        elif conv == "cve":
            e.message = f"Guard against {what} in {stem} (CVE-{lab.randint(2021, 2026)}-{lab.randint(10000, 49999)})"
            e.signals = {"cve": True}
        elif conv == "jira":
            e.message = f"PROJ-{num}: handle {what} in {stem}"
            e.signals = {"fixref": "jira"}
        elif conv == "keyword":
            word = lab.choice(["fix crash in", "fix bug in", "fix wrong total in", "fix error in"])
            e.message = f"{word} {stem} on {what}"
            e.signals = {"keyword": True}
        else:
            e.message = f"Adjust {stem} handling of {what}"
            e.signals = {}

    def last_touch(self, fid):
        """The last commit that edited the file's code (the commit a `Fixes:` trailer names)."""
        for prev in reversed(self.plan.entries):
            if fid in prev.touched and prev.type in ("add", "ordinary", "feature_with_ticket", "fix"):
                return prev.lid
        return self.plan.entries[0].lid

    def subject_of(self, lid):
        for prev in self.plan.entries:
            if prev.lid == lid:
                return prev.message.split("\n")[0].replace("\"", "'")
        return ""

    def _revert_applicable(self, target: Entry):
        out = []
        for ed in target.edits:
            kind, fid, ref, old, new = ed
            rec = self.files[fid]
            if not rec.alive:
                continue
            if kind == "code":
                s = cg.find_simple(rec.model, ref)
                if s is not None and s.lit != old:
                    out.append(ed)
            elif ref < len(rec.model) and rec.model[ref] != old:
                out.append(ed)
        return out

    def _pick_revert_target(self, rng, elig):
        """A revertable commit from `elig` (in time order): usually a recent one, sometimes any. Returns
        (target, the edits that still apply) or (None, None)."""
        if not elig:
            return None, None
        if rng.random() < 0.7:
            first = len(elig) - 1 - rng.randrange(min(30, len(elig)))
        else:
            first = rng.randrange(len(elig))
        for i in [first] + [i for i in reversed(range(len(elig))) if i != first]:
            app = self._revert_applicable(elig[i])
            if app:
                return elig[i], app
        return None, None

    def do_revert(self, e: Entry):
        """Revert an earlier ordinary or ticket-feature commit that changed no structure: put back the literal
        values it changed (those that still differ). The message quotes the target's subject, as git does."""
        rng = stream(self.cfg.seed, "revert", e.lid)
        reverted = {x.revert_target for x in self.plan.entries if x.revert_target}
        elig = [x for x in self.plan.entries if x.type in ("ordinary", "feature_with_ticket")
                and not x.structural and x.edits and x.lid not in reverted]
        target, app = None, None
        if self.mut.active("reverts_of_new_code") and self.after_snapshot:
            target, app = self._pick_revert_target(rng, [x for x in elig if x.time > self.snap_time])
            if target is None:
                self.mut.record("reverts_of_new_code", "kept_pre_snapshot_target", e.lid)
                self.plan.mutation_notes.setdefault("reverts_of_new_code", []).append(
                    f"{e.lid}: no revertable post-snapshot commit yet; kept a pre-snapshot target")
        if target is None:
            target, app = self._pick_revert_target(rng, elig)
        if target is None:                       # nothing revertable: an ordinary commit instead
            e.type = "ordinary"
            e.notes["revert_fallback"] = True
            return self.do_ordinary(e)
        touched = []
        for kind, fid, ref, old, new in app:
            rec = self.files[fid]
            if kind == "code":
                cg.find_simple(rec.model, ref).lit = old
            else:
                rec.model[ref] = old
            touched.append(fid)
        self.commit_files(e, touched)
        e.revert_target = target.lid
        e.convention = "revert"
        subj = self.subject_of(target.lid)
        e.message = f"Revert \"{subj}\"\n\nThis reverts commit {{{{H40:{target.lid}}}}}."
        e.signals = {"revert": target.lid}
        if self.mut.active("reverts_of_new_code") and self.after_snapshot and target.time > self.snap_time:
            self.mut.record("reverts_of_new_code", "retargeted_to_post_snapshot", e.lid)
        if re.search(r"#\d+", subj):                     # quoting a ticket feature's subject quotes its ticket
            e.signals["quoted_fixref"] = "issue (quoted from the reverted commit's subject)"
        e.notes["target_before_snapshot"] = target.time <= self.snap_time

    def do_sweep(self, e: Entry):
        rng = stream(self.cfg.seed, "sweep", e.lid)
        units = self.alive_units()
        chosen = rng.sample(units, int(math.ceil(0.85 * len(units))))
        tests = [r for r in self.files.values() if r.alive and r.kind == "test"]
        chosen += rng.sample(tests, len(tests) // 2)
        for r in chosen:
            if e.sweep["kind"] == "licence":
                r.model.header = True
            else:
                r.model.style += 1
        self.commit_files(e, [r.fid for r in chosen])
        e.message = e.sweep["message"]
        e.convention = "sweep"
        e.signals = {"keyword": True} if e.message.lower().startswith("fix") else {}
        if e.sweep["kind"] == "licence" and self.mut.active("sweep_labelled_fix"):
            num = stream(self.cfg.seed, "mutation", "sweep_labelled_fix", e.lid).randint(100, 9999)
            e.message = f"Fix licence headers (#{num})"
            e.convention = "sweep_ticket"
            e.signals = {"fixref": "issue", "keyword": True}
            self.mut.record("sweep_labelled_fix", "commits", e.lid)
        e.notes["sweep_kind"] = e.sweep["kind"]

    def _move(self, e, rec, new_path, rewrite_callers=True):
        """Move a file. A Python caller imports by path, so a base-history move also rewrites every caller's
        import line in the same commit (recorded as caller edits); `rewrite_callers=False` (the
        renames_after_snapshot mutation) edits no other file and leaves the callers' imports stale."""
        old = rec.path
        rec.path = new_path
        rec.history.append((new_path, e.lid))
        callers = []
        if rewrite_callers:
            callers = [c.fid for c in self.callers_of(rec.fid)] if rec.lang == "python" else []
            for c in callers:
                self.stale.pop((c, rec.fid), None)
        elif rec.lang == "python":
            for c in self.callers_of(rec.fid):
                self.stale.setdefault((c.fid, rec.fid), old)
        e.caller_edits = list(callers)
        self.commit_files(e, [rec.fid] + callers, old_paths={rec.fid: old})
        e.message = f"Move {old} to {new_path}"
        e.notes["rename"] = [old, new_path]

    def _taken(self):
        return {r.path for r in self.files.values() if r.alive}

    def do_rename(self, e: Entry):
        rng = stream(self.cfg.seed, "rename", e.lid)
        units = sorted(self.alive_units(), key=lambda r: r.fid)
        rec = units[rng.randrange(len(units))]
        taken = self._taken()
        cur_dir, name = rec.path.rsplit("/", 1)
        for _ in range(100):
            if rng.random() < 0.7:
                d = rng.choice([x for x in self.plan.layout.unit_dirs if x != cur_dir])
                new = f"{d}/{name}"
            else:
                new = f"{cur_dir}/{rng.choice(cg.FILE_NOUNS)}_{name}"
            if new not in taken:
                break
        self._move(e, rec, new)

    def do_mrename(self, e: Entry):
        """renames_after_snapshot: move a not-yet-moved snapshot unit file to another directory."""
        rng = stream(self.cfg.seed, "mutation", "renames_after_snapshot", e.lid)
        done = set(self.plan.mutation_notes.get("renamed_after_snapshot", []))
        cands = sorted([r for r in self.alive_units() if r.fid in self.plan.points["snapshot"] and r.fid not in done],
                       key=lambda r: r.fid)
        if not cands:
            e.type = "rename"
            e.message = "Move nothing"
            return
        rec = cands[rng.randrange(len(cands))]
        taken = self._taken()
        cur_dir, name = rec.path.rsplit("/", 1)
        dirs = [x for x in self.plan.layout.unit_dirs if x != cur_dir and f"{x}/{name}" not in taken]
        self._move(e, rec, f"{rng.choice(dirs)}/{name}", rewrite_callers=False)
        if rec.lang == "python":
            callers = sorted(c.fid for c in self.callers_of(rec.fid))
            if callers:
                e.notes["stale_imports"] = {"file": rec.fid, "callers_still_import": {
                    c: self.stale[(c, rec.fid)] for c in callers}}
        e.type = "rename"
        self.plan.mutation_notes.setdefault("renamed_after_snapshot", []).append(rec.fid)

    def do_delete(self, e: Entry):
        rng = stream(self.cfg.seed, "delete", e.lid)
        units = sorted(self.alive_units(), key=lambda r: r.fid)
        rec = units[rng.randrange(len(units))]
        callers = self.callers_of(rec.fid)
        rec.alive, rec.deleted = False, e.lid
        for c in callers:
            cg.drop_calls_to(c.model, rec.fid)
        e.caller_edits = [c.fid for c in callers]
        self.commit_files(e, [rec.fid] + [c.fid for c in callers])
        e.message = f"Remove {rec.path}"

    def do_bot(self, e: Entry):
        rng = stream(self.cfg.seed, "bot", e.lid)
        deps = self.files["deps"]
        name = rng.choice(sorted(deps.model))
        old = ".".join(map(str, deps.model[name]))
        v = deps.model[name]
        v[2] += 1
        if rng.random() < 0.2:
            v[1], v[2] = v[1] + 1, 0
        new = ".".join(map(str, v))
        self.commit_files(e, ["deps"])
        e.message = (f"Bump {name} from {old} to {new}\n\nBumps {name} from {old} to {new}.\n\n"
                     f"Signed-off-by: {DEP_BOT}")
        e.convention = "bot"

    def do_vendor_import(self, e: Entry):
        self.vendor_version += 1
        vendors = [r for r in self.files.values() if r.kind == "vendor" and r.alive]
        for r in vendors:
            rng = stream(self.cfg.seed, "vendor", r.fid, self.vendor_version)
            r.model = cg.build_code_file(rng, r.fid, r.lang, r.kind, r.stem, r.targets, None)
        self.commit_files(e, [r.fid for r in vendors])
        e.message = f"Import libmini 1.{self.vendor_version}.0 into vendor/thirdparty"
        e.convention = "vendor_import"

    def do_filler(self, e: Entry):
        """huge_import_merge padding: a docs note brought in with the block."""
        fid = "h" + e.lid[1:]
        rng = stream(self.cfg.seed, "mutation", "huge_import_merge", e.lid)
        rec = FileRec(fid, "imported_note", None, f"docs/imported/note_{e.lid[1:]}.md", False,
                      UNIT_REASONS["imported_note"],
                      model=cg.doc_lines(rng, 3))
        rec.alive, rec.created = True, e.lid
        rec.history.append((rec.path, e.lid))
        self.files[fid] = rec
        self.commit_files(e, [fid])
        e.message = f"Add imported note {e.lid[1:]}"
        e.type = "add"
        e.convention = "plain"
        e.notes["huge_import_filler"] = True


def plan(cfg: Config, mut=None) -> Plan:
    """Build the whole history in memory."""
    import mutations as mm
    mut = mut or mm.MutationSet(cfg.mutations)
    entries, snap, prior = build_timeline(cfg)
    snap_lid, prior_lid = entries[snap].lid, entries[prior].lid
    counts = type_counts(cfg.commits)
    layout = Layout(cfg, counts["add"])
    mut.extend_layout(cfg, layout)
    entries = mut.adjust_timeline(cfg, entries, snap_lid, prior_lid)
    sim = Simulator(cfg, mut)
    p = sim.run(entries, snap_lid, prior_lid, layout)
    p.mutation_set = mut
    return p
