"""Tests of the comparison scorer, part 1 (tools/compare/; docs/process/comparison_scorer_spec.md, Revision 2).

Everything runs on DECOYS. Two decoy studies of 12 control repositories each (N: no effect; P: branches=0.5) are
built once per session by tools/compare/decoy_study.py (the generator, the unmodified pipeline through the
harness, the reference placebo / lock / score in a git checkout, phase B, this directory's tables), under
pytest's temporary directory, or under COMPARE_STUDY_CACHE when that names a directory under ~/.claude/jobs or
/tmp (a finished build there with the same recipe and code hash is reused: that is how each test can run alone
in its own process without rebuilding). Every call into SA3 code runs inside a sandbox (the reference loader in
tools/harness/sandbox_ro.py's, the pipeline, placebo, lock and score in tools/harness/sandbox.py's). The only
SA3 module run in this process is the SEALED COPY of tools/sa3_stats.py, after its imports were checked.

Nothing here opens, lists or stats the real study directory, the corpus, the pool, the tables root, the
protected root, the owner's report directory or ~/.blind.

Pipeline tests are skipped, with the reason, when bwrap, tree_sitter_language_pack 1.20.0, linguist's cached
lists or the engine export are unavailable.
"""
from __future__ import annotations

import copy
import importlib.metadata as md
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
CMPDIR = ROOT / "tools" / "compare"


def _load(name: str):
    import importlib.util
    key = f"tools_compare_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, str(CMPDIR / f"{name}.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


U = _load("_util")
sys.modules.setdefault("tools_compare__util", U)
T = _load("tables")
D = _load("derive")
IC = _load("input_check")
SCO = _load("scorer")
CM = _load("cellmap")
DS = _load("decoy_study")
BR = _load("blind_runner")
SB = U.harness_sandbox()
SR = U.sandbox_ro()
P = U.phase_b()
R = U.owner_report()

PY = sys.executable
MARK_SHA = "badc0de" + "5eed" * 8 + "a"                 # 40 hex, in no clone
MARK_TEXT = "LABELMARKER-zz9q-7731"
MARK_PATH = "zz_label_marker_dir_q9x7/only_in_outcome_7f3a.py"


# --------------------------------------------------------------------------------------------- environment
def _skip_reason() -> str | None:
    if not Path(SB.BWRAP).exists():
        return "bwrap not installed"
    try:
        if md.version("tree_sitter_language_pack") != "1.20.0":
            return "tree_sitter_language_pack is not 1.20.0 in this interpreter"
    except md.PackageNotFoundError:
        return "tree_sitter_language_pack not installed"
    if not (Path.home() / SB.LINGUIST_SUB / "vendor.yml").is_file():
        return "linguist cache absent"
    return None


def _engine_present(base: Path) -> bool:
    """decided INSIDE the harness sandbox: laws-study is never looked at from outside"""
    w = SB.prepare(base / "engine-probe")
    (w / "tree/tools/harness").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "tools/harness/sandbox.py", w / "tree/tools/harness/sandbox.py")
    p = SB.run(["/usr/bin/python3", "-I", "-B", "-c",
                f"import os; print(os.path.isdir({str(SB.ENGINE / 'gitgalaxy')!r}))"], w, timeout=120)
    return p.stdout.strip() == "True"


@pytest.fixture(scope="session")
def base(tmp_path_factory) -> Path:
    why = _skip_reason()
    if why:
        pytest.skip(why)
    env = os.environ.get("COMPARE_STUDY_CACHE")
    b = SB.check_work(Path(env)) if env else tmp_path_factory.mktemp("compare")
    b.mkdir(parents=True, exist_ok=True)
    if not _engine_present(b):
        pytest.skip("engine export not present")
    return b


class Study:
    def __init__(self, b: Path, which: str):
        self.rec = DS.build(b, which)
        self.which = which
        self.dir = b / which
        self.decoy = Path(self.rec["paths"]["decoy"])
        self.tree = Path(self.rec["paths"]["tree"])
        self.tables = Path(self.rec["paths"]["tables"])
        self.sealed = Path(self.rec["paths"]["sealed"])
        self.result = json.loads(Path(self.rec["paths"]["result"]).read_text())
        self.marg = json.loads((self.decoy / "docs" / "sa3_outcome_marginals.json").read_text())
        self.repos = [r["repo"] for r in self.marg if r["status"] == "ok"]
        self._loaders: dict = {}
        self._label_loaders: dict = {}
        self._data = None
        self._cmp = None

    def layout(self, scratch: Path, tables: Path | None = None, sealed: Path | None = None) -> "IC.Layout":
        t = tables or self.tables
        return IC.Layout(self.decoy / "study", self.tree, t / "phase_b", t / "compare", sealed or self.sealed, scratch,
                         label_tables=t / "labels")

    def loaders(self, scratch: Path) -> dict:
        """the reference loader's arrays (stub outcome files), one sandbox run per repo, kept for the session"""
        if not self._loaders:
            L = self.layout(scratch)
            for r in self.repos:
                ld, code = IC.run_loader(L, r)
                assert code == "none", (r, code)
                self._loaders[r] = ld
        return self._loaders

    def label_loaders(self, scratch: Path) -> dict:
        if not self._label_loaders:
            L = self.layout(scratch)
            for r in self.repos:
                ld, code = IC.run_loader(L, r, self.decoy / "study" / "sa3_outcomes" / f"{r}.json")
                assert code == "none", (r, code)
                self._label_loaders[r] = ld
        return self._label_loaders

    def data(self) -> dict:
        if self._data is None:
            self._data = SCO.load_data(self.tables / "phase_b", self.tables / "compare", self.tables / "labels",
                                       self.sealed)
        return self._data

    def _key(self) -> str:
        """the unmodified comparison's inputs: this directory's code, the sealed copies, the tables' indexes"""
        import hashlib
        h = hashlib.sha256()
        files = sorted(CMPDIR.glob("*.py")) + sorted(self.sealed.rglob("*")) + sorted(self.tables.rglob("index.json"))
        for f in files:
            if f.is_file():
                h.update(str(f.relative_to(f.anchor)).encode() + b"\0" + f.read_bytes())
        return h.hexdigest()[:20]

    def comparison(self, cls=None) -> dict:
        """the comparison scorer's result, read back from its JSON text as the reference's is. The unmodified
        scorer's result is kept beside the build, under a key of its code and inputs, so that tests run one per
        process do not recompute it"""
        if cls is None and self._cmp is not None:
            return self._cmp
        keep = self.dir / f"comparison-{self._key()}.json" if cls is None else None
        if keep is not None and keep.exists():
            self._cmp = json.loads(keep.read_text())
            return self._cmp
        text = SCO.dumps((cls or SCO.Scorer)(self.sealed, copy.deepcopy(self.data())).score())
        res = json.loads(text)
        if cls is None:
            keep.write_text(text)
            self._cmp = res
        return res


@pytest.fixture(scope="session")
def study_n(base) -> Study:
    return Study(base, "N")


@pytest.fixture(scope="session")
def study_p(base) -> Study:
    return Study(base, "P")


@pytest.fixture(scope="session")
def scratch(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("compare_scratch")


# ============================================================================== 1. the input check (layer 1)
def _public(obj: dict, L, label: bool, out: Path) -> str:
    return IC.write_public(out, obj, IC.vocab(L), label=label)


def test_1a_input_check_passes_on_study_n(study_n, scratch, tmp_path):
    """predictor side (stub outcome files) and label side: every item equal, every repo; validated output"""
    L = study_n.layout(scratch / "n")
    pred = IC.predictor_check(L, loaders=study_n.loaders(scratch / "n"))
    _public(pred, L, False, tmp_path / "pred.json")
    bad = {r: [i for i, v in rec["items"].items() if v is not True] for r, rec in pred["repos"].items()}
    assert pred["all_equal"], {r: v for r, v in bad.items() if v}
    assert pred["repos_checked"] == len(study_n.repos) == 12
    assert all(rec["flux_flagged"] == 0 and rec["code"] == "none" for rec in pred["repos"].values())
    lab = IC.label_check(L, study_n.decoy / "study" / "sa3_outcomes", loaders=study_n.label_loaders(scratch / "n"))
    _public(lab, L, True, tmp_path / "lab.json")
    assert lab["all_equal"], lab


def test_1b_input_check_passes_on_study_p(study_p, scratch, tmp_path):
    L = study_p.layout(scratch / "p")
    pred = IC.predictor_check(L, loaders=study_p.loaders(scratch / "p"))
    _public(pred, L, False, tmp_path / "pred.json")
    assert pred["all_equal"], {r: [i for i, v in rec["items"].items() if v is not True]
                               for r, rec in pred["repos"].items()}
    lab = IC.label_check(L, study_p.decoy / "study" / "sa3_outcomes", loaders=study_p.label_loaders(scratch / "p"))
    assert lab["all_equal"], lab


def _table_copy(study: Study, dst: Path) -> Path:
    shutil.copytree(study.tables, dst)
    return dst


def _rewrite(d: Path, table: str, change, module="phase_b") -> None:
    """replace one table of one repo's directory by `change(rows)`, through the canonical writer, and point the
    index at the new file"""
    C = U.canon()
    idx = json.loads((d / "index.json").read_text())
    f = d / idx["tables"][table]["file"]
    spec = None if module == "phase_b" else T.TABLES[table]
    cols = (spec or sys.modules["schema"].TABLES[table])["columns"]
    reals = [c for c, t in cols if t == "real"]
    rows = [{**r, **{c: (None if r[c] is None else float.fromhex(r[c])) for c in reals}} for r in C.read_rows(f)]
    new = C.write_table(d, table, change(rows), spec)
    idx["tables"][table] = new
    (d / "index.json").write_text(json.dumps(idx, indent=1) + "\n")


def _not_equal(obj: dict, repo: str) -> list[str]:
    return sorted(i for i, v in obj["repos"][repo]["items"].items() if v is False)


def test_1c_input_check_fails_naming_the_item(study_n, scratch, tmp_path):
    """each planted change to a copy of the tables makes the check say "not equal" for exactly the items the
    change reaches, naming the item (a predictor by its name) and never a file or a value"""
    repo = "django"
    loaders = study_n.loaders(scratch / "n")
    uni = loaders[repo]["paths"]
    cd0 = {r["path"]: r for r in T.read_dir(study_n.tables / "compare" / repo)["call_degree"]}
    target = next(p for p in uni[10:] if cd0[p]["in_degree"] > 0)

    def run(tables: Path) -> dict:
        L = study_n.layout(scratch / "n", tables=tables)
        obj = IC.predictor_check(L, repos=[repo], loaders=loaders)
        text = _public(obj, L, False, tmp_path / f"{tables.name}.json")
        for s in (target, "0x", "nan"):
            assert s not in text and s not in json.dumps(obj)
        return obj

    cases = {}
    # one measure value changed (struct_branch of a universe file)
    t = _table_copy(study_n, tmp_path / "measure_changed")
    _rewrite(t / "phase_b" / repo, "measure", lambda rows: [
        {**r, "value": r["value"] + 1.0} if (r["path"], r["name"]) == (target, "struct_branch")
        else r for r in rows])
    cases["measure_changed"] = run(t)
    # one made missing
    t = _table_copy(study_n, tmp_path / "measure_missing")
    _rewrite(t / "phase_b" / repo, "measure", lambda rows: [
        {**r, "value": None} if (r["path"], r["name"]) == (target, "risk_safety_score") else r for r in rows])
    cases["measure_missing"] = run(t)
    # one flux value changed
    t = _table_copy(study_n, tmp_path / "flux_changed")
    _rewrite(t / "compare" / repo, "flux", lambda rows: [
        {**r, "value": r["value"] + 1.0} if r["path"] == target else r for r in rows],
        module="compare")
    cases["flux_changed"] = run(t)
    # one resolved call row removed: one fewer in-degree for its target, one fewer out-degree for its source
    t = _table_copy(study_n, tmp_path / "call_removed")
    cd = {r["path"]: r for r in T.read_dir(t / "compare" / repo)["call_degree"]}
    assert cd[target]["in_degree"] > 0
    src = next(p for p in uni if p != target and cd[p]["out_degree"] > 0)

    def drop_call(rows):
        out = []
        for r in rows:
            if r["path"] == target:
                r = {**r, "in_degree": r["in_degree"] - 1}
            if r["path"] == src:
                r = {**r, "out_degree": r["out_degree"] - 1}
            out.append(r)
        return out
    _rewrite(t / "compare" / repo, "call_degree", drop_call, module="compare")
    cases["call_removed"] = run(t)
    assert _not_equal(cases["measure_changed"], repo) == ["x:struct_branch", "x:struct_branch_per_loc"]
    nm = _not_equal(cases["measure_missing"], repo)
    assert {"x:risk_safety_score", "x:risk_safety_nonzero", "x:risk_safety_among_nonzero",
            "in_use:risk_safety_score", "in_use:risk_safety_nonzero"} <= set(nm), nm
    assert all(i.split(":")[1].startswith("risk_safety") for i in nm), nm
    assert _not_equal(cases["flux_changed"], repo) == ["x:amplified_cascading_flux",
                                                       "x:amplified_cascading_flux_per_loc"]
    nc = _not_equal(cases["call_removed"], repo)
    assert set(nc) - {"silent:in_degree_per_loc"} == {"x:in_degree", "x:in_degree_per_loc", "x:out_degree"}, nc


def test_1d_label_side_fails_naming_the_item(study_n, scratch, tmp_path):
    """label side: one positive moved, two pool commits swapped in order, a commit with no path dropped"""
    L0 = study_n.layout(scratch / "n")
    lab_loaders = study_n.label_loaders(scratch / "n")

    def run(tables: Path, repo: str) -> list[str]:
        L = study_n.layout(scratch / "n", tables=tables)
        obj = IC.label_check(L, study_n.decoy / "study" / "sa3_outcomes", repos=[repo], loaders=lab_loaders)
        text = IC.write_public(tmp_path / f"{tables.name}.json", obj, IC.vocab(L0), label=True)
        assert "0x" not in text
        return sorted(i for i, v in obj["repos"][repo]["items"].items() if v is False)

    repo = "django"
    uni = lab_loaders[repo]["paths"]
    t = _table_copy(study_n, tmp_path / "positive_moved")
    pos = sorted(r["path"] for r in T.read_dir(t / "labels" / repo)["outcome_file"] if r["outcome"] == "HP")
    neg = next(p for p in uni if p not in pos)
    _rewrite(t / "labels" / repo, "outcome_file", lambda rows: [
        {**r, "path": neg} if (r["outcome"], r["path"]) == ("HP", pos[0]) else r for r in rows], module="compare")
    assert run(t, repo) == ["y:HP"]
    t = _table_copy(study_n, tmp_path / "pool_swapped")
    _rewrite(t / "labels" / repo, "pool_commit", lambda rows: [
        {**r, "position": {0: 1, 1: 0}.get(r["position"], r["position"])} for r in rows], module="compare")
    _rewrite(t / "labels" / repo, "pool_commit_file", lambda rows: [
        {**r, "position": {0: 1, 1: 0}.get(r["position"], r["position"])} for r in rows], module="compare")
    assert run(t, repo) == ["pool"]
    # ctrl-mw2's pool holds 400 commits with no path: drop one (its commit row; it has no file row)
    repo = "ctrl-mw2"
    lt = T.read_dir(study_n.tables / "labels" / repo)
    empty = next(r["position"] for r in lt["pool_commit"] if r["n_paths"] == 0)
    t = _table_copy(study_n, tmp_path / "empty_dropped")

    def drop(rows):
        return [{**r, "position": r["position"] - (r["position"] > empty)} for r in rows if r["position"] != empty]
    _rewrite(t / "labels" / repo, "pool_commit", drop, module="compare")
    _rewrite(t / "labels" / repo, "pool_commit_file", drop, module="compare")
    assert run(t, repo) == ["pool"]


def test_1e_universe_differs_means_not_compared(study_n, scratch, tmp_path):
    """a universe file missing from the `file` table: universe not equal, every item indexed by it not compared
    (null), and the label side says "not comparable" only"""
    repo = "go"
    t = _table_copy(study_n, tmp_path / "universe")
    gone = study_n.loaders(scratch / "n")[repo]["paths"][3]
    _rewrite(t / "phase_b" / repo, "file", lambda rows: [r for r in rows if r["path"] != gone])
    L = study_n.layout(scratch / "n", tables=t)
    obj = IC.predictor_check(L, repos=[repo], loaders=study_n.loaders(scratch / "n"))
    items = obj["repos"][repo]["items"]
    assert items["universe"] is False and all(v is None for i, v in items.items() if i != "universe")
    lab = IC.label_check(L, study_n.decoy / "study" / "sa3_outcomes", repos=[repo],
                         loaders=study_n.label_loaders(scratch / "n"))
    assert lab["repos"][repo]["comparable"] is False and all(v is None for v in lab["repos"][repo]["items"].values())
    text = IC.write_public(tmp_path / "u.json", lab, IC.vocab(L), label=True)
    assert "not comparable: universe differs" in text and gone not in text
    # review M8: the missing file positive or not, the public bytes are the same
    flipped = copy.deepcopy(study_n.label_loaders(scratch / "n"))
    i = flipped[repo]["paths"].index(gone)
    flipped[repo]["y"]["HP"][i] = 1 - flipped[repo]["y"]["HP"][i]
    lab2 = IC.label_check(L, study_n.decoy / "study" / "sa3_outcomes", repos=[repo], loaders=flipped)
    IC.write_public(tmp_path / "u2.json", lab2, IC.vocab(L), label=True)
    assert (tmp_path / "u.json").read_bytes() == (tmp_path / "u2.json").read_bytes()
    assert (tmp_path / "u.txt").read_bytes() == (tmp_path / "u2.txt").read_bytes()


# ======================================================================= 2. derivation, rule by rule
SCAN_COLS = ("total_loc", "coding_loc", "pagerank_score", "betweenness_score", "struct_branch", "state_danger",
             "state_pointers", "state_memory_alloc", "def_safety", "state_flux", "state_heat_triggers",
             "risk_safety_score", "risk_tech_debt", "risk_cognitive_load", "risk_state_flux", "risk_concurrency")
FLUX_CASES = [  # (record, section 2's stated value, the flux table's case)
    (None, 0.0, "empty_record"), ("", 0.0, "empty_record"), ("{}", 0.0, "key_absent"),
    ('{"other": 2}', 0.0, "key_absent"), ('{"amplified_cascading_flux": 0}', 0.0, "falsy_value"),
    ('{"amplified_cascading_flux": ""}', 0.0, "falsy_value"), ('{"amplified_cascading_flux": null}', 0.0, "falsy_value"),
    ('{"amplified_cascading_flux": false}', 0.0, "falsy_value"), ('{"amplified_cascading_flux": []}', 0.0, "falsy_value"),
    ('{"amplified_cascading_flux": {}}', 0.0, "falsy_value"), ('{"amplified_cascading_flux": 7}', 7.0, "number"),
    ('{"amplified_cascading_flux": 2.25}', 2.25, "number"), ('{"amplified_cascading_flux": true}', 1.0, "number"),
    ('{"amplified_cascading_flux": "3.5"}', 3.5, "numeric_text"), ('{"amplified_cascading_flux": " "}', None, "unreadable_value"),
    ('{"amplified_cascading_flux": "abc"}', None, "unreadable_value"),
    ('{"amplified_cascading_flux": [1]}', None, "unreadable_value"),
    ('{"amplified_cascading_flux": {"a": 1}}', None, "unreadable_value"), ("not json {", None, "not_json"),
    ('{"amplified_cascading_flux": Infinity}', math.inf, "number"), ('{"amplified_cascading_flux": NaN}', None, "number"),
]


class Tiny:
    """a one-repo study built by hand: the history of a decoy repo, a sidecar with a scan root, and a planted scan
    database with one row per case of section 2; the tables built from the same planted values"""

    def __init__(self, study: Study, d: Path, non_object: bool = False):
        self.d, self.repo = d, "tiny"
        st = d / "study"
        for sub in ("history", "sa3_scans", "sa3_nesting"):
            (st / sub).mkdir(parents=True)
        src = study.decoy / "study"
        shutil.copyfile(src / "history" / "django.db", st / "history" / "tiny.db")
        side = json.loads((src / "sa3_scans" / "django.json").read_text())
        side.update({"repo": "tiny", "src_root": "/scanroot/src/", "generated": []})
        (st / "sa3_scans" / "tiny.json").write_text(json.dumps(side) + "\n")
        self.root = "/scanroot/src/"
        rng = np.random.default_rng(5)
        n = 321
        self.paths = [f"src/pkg/m{i:03d}.py" for i in range(n - 1)] + ["src/pkg/edge.py"]
        rows = []                                # (id, stored path, values dict, telemetry)
        for i, p in enumerate(self.paths):
            stored = (self.root + p) if i % 3 == 0 else ("//" + p if i % 3 == 1 else p)
            if p == "src/pkg/edge.py":
                stored = self.root + "/" + p     # one slash removed with the root: the path keeps a leading slash
            v = {"total_loc": float(rng.integers(5, 900)), "coding_loc": float(rng.integers(1, 5))}
            for c in SCAN_COLS[2:]:
                v[c] = float(rng.integers(0, 40)) if c.startswith(("state", "struct", "def")) else float(rng.random() * 50)
            rows.append([i + 1, stored, v, json.dumps({"amplified_cascading_flux": int(rng.integers(0, 30))})])
        for j, c in enumerate(SCAN_COLS[2:]):  # each column null on two files
            for i in (5 + 2 * j, 6 + 2 * j):
                rows[i][2][c] = None
        for i in range(120, 150):              # def_safety missing on 30 files: 291 in use, 5 bands not 10
            rows[i][2]["def_safety"] = None
        rows[60][2]["risk_safety_score"] = -1.5
        rows[61][2]["risk_safety_score"] = 0.0
        for k, (rec, _v, _c) in enumerate(FLUX_CASES):
            rows[70 + k][3] = rec
        if non_object:
            rows[95][3] = "[]"
        # duplicate paths: m100 again (later: struct_branch differs, pagerank null, telemetry unreadable); m101
        # again (later telemetry parses and wins)
        rows.append([1001, "//src/pkg/m100.py", {**rows[100][2], "struct_branch": 99.0, "pagerank_score": None},
                     "not json {"])
        rows.append([1002, "src/pkg/m101.py", {**rows[101][2], "risk_tech_debt": 3.25}, '{"amplified_cascading_flux": 41}'])
        others = [[2001, "tests/test_a.py", {c: 1.0 for c in SCAN_COLS}, None],
                  [2002, "README.md", {c: 1.0 for c in SCAN_COLS}, None],
                  [2003, "src/pkg/zero.py", {**{c: 1.0 for c in SCAN_COLS}, "total_loc": 0.0}, None],
                  [2004, "src/pkg/noloc.py", {**{c: 1.0 for c in SCAN_COLS}, "total_loc": None}, None]]
        self.rows = rows + others
        db = st / "sa3_scans" / "tiny_master.db"
        con = sqlite3.connect(str(db))
        con.execute("create table file_data (id integer primary key, file_path text, "
                    + ", ".join(f"{c} real" for c in SCAN_COLS) + ", mitigation_telemetry text)")
        con.execute("create table fcall_data (src_file_id int, dst_file_id int, dst_func_id int)")
        for fid, stored, v, tel in self.rows:
            con.execute(f"insert into file_data values (?, ?, {', '.join('?' * len(SCAN_COLS))}, ?)",
                        [fid, stored] + [v[c] for c in SCAN_COLS] + [tel])
        calls = []
        for i in range(n):
            calls.append((i + 1, (i * 7) % n + 1, 1))            # resolved
            calls.append((i + 1, (i * 11) % n + 1, None))        # unresolved: counts nowhere
        calls += [(5, 2001, 1), (2001, 9, 1), (2002, 9, 1), (13, 13, 1), (1001, 40, 1), (41, 1001, 1), (7, 9999, 1)]
        con.executemany("insert into fcall_data values (?, ?, ?)", calls)
        con.commit()
        con.close()
        nest = {p: [int(rng.integers(1, 9)), float(rng.random() * 4)] for p in self.paths}
        del nest["src/pkg/m110.py"]
        nest["src/pkg/m111.py"] = [3, None]
        nest["src/pkg/m112.py"] = [None, 2.5]
        self.nest = nest
        (st / "sa3_nesting" / "tiny.json").write_text(json.dumps({"repo": "tiny", "files": nest}) + "\n")
        self.sealed = d / "sealed"
        (self.sealed / "tools").mkdir(parents=True)
        (self.sealed / "docs").mkdir()
        shutil.copyfile(study.sealed / "tools" / "sa3_stats.py", self.sealed / "tools" / "sa3_stats.py")
        (self.sealed / "docs" / "sa3_outcome_marginals.json").write_text(json.dumps([{"repo": "tiny", "status": "ok"}]))
        self.write_tables(side)

    def universe_paths(self) -> list[str]:
        """by the planted values: a .py file under src/ with a size above zero (what phase B's file table holds)"""
        out = set()
        for _fid, stored, v, _t in self.rows:
            p = T.scan_path(stored, self.root)
            if p.endswith(".py") and "/tests/" not in "/" + p and v["total_loc"]:
                out.add(p)
        return sorted(out)

    def write_tables(self, side: dict) -> None:
        C = U.canon()
        S = sys.modules["schema"]
        uni = self.universe_paths()
        vals: dict[str, dict] = {}
        for _fid, stored, v, _t in self.rows:            # per column the later non-null value (the loader's rule)
            p = T.scan_path(stored, self.root)
            cur = vals.setdefault(p, {c: None for c in SCAN_COLS})
            for c in SCAN_COLS:
                if v[c] is not None:
                    cur[c] = v[c]
        pb = self.d / "tables" / "phase_b" / "tiny"
        pb.mkdir(parents=True)
        repo_row = {c: None for c in S.columns("repo")}
        repo_row.update({"repo": "tiny", "engine": side["engine"]})
        file_rows = [{**{c: None for c in S.columns("file")}, "repo": "tiny", "path": p, "in_universe": p in uni,
                      "loc": vals[p]["total_loc"]} for p in vals]
        meas = []
        for p in uni:
            for c in SCAN_COLS:
                meas.append({"repo": "tiny", "path": p, "name": c, "value": vals[p][c], "absent_means": "missing",
                             "instrument": "engine", "version": None})
            got = self.nest.get(p)
            for i, c in enumerate(("nest_max", "nest_mean")):
                meas.append({"repo": "tiny", "path": p, "name": c, "value": None if not got or got[i] is None
                             else float(got[i]), "absent_means": "missing", "instrument": "sa3_nest_scan",
                             "version": None})
        written = {n: C.write_table(pb, n, r) for n, r in (("repo", [repo_row]), ("file", file_rows), ("measure", meas))}
        (pb / "index.json").write_text(json.dumps({"tables": written}) + "\n")
        built = T.predictor_rows("tiny", self.d / "study" / "sa3_scans" / "tiny_master.db", side)
        self.flux = {r["path"]: r for r in built["rows"]["flux"]}
        self.degrees = {r["path"]: r for r in built["rows"]["call_degree"]}
        self.duplicates = built["duplicate_paths"]
        ct = self.d / "tables" / "compare" / "tiny"
        T.write_index(ct, {"repo": "tiny"}, T.write(ct, built["rows"]))

    def layout(self, scratch: Path, tree: Path) -> "IC.Layout":
        return IC.Layout(self.d / "study", tree, self.d / "tables" / "phase_b", self.d / "tables" / "compare",
                         self.sealed, scratch)


@pytest.fixture(scope="session")
def tiny(study_n, tmp_path_factory):
    d = tmp_path_factory.mktemp("tiny")
    t = Tiny(study_n, d)
    ld, code = IC.run_loader(t.layout(d / "scratch", study_n.tree), "tiny")
    assert code == "none", code
    return t, ld


def test_2a_derivation_equals_the_reference_loader_on_planted_cases(tiny, tmp_path):
    """every item of the input check on the planted scan: the reference loader (in the sandbox, unchanged) and
    the table route agree, element by element, with missing values in the same places"""
    t, ld = tiny
    stats = U.load_sealed_stats(t.sealed)
    pb, cmp, _ = D.load_dirs(t.d / "tables/phase_b/tiny", t.d / "tables/compare/tiny")
    d = D.derive("tiny", pb, cmp, stats)
    items = IC.compare_predictor(ld, d, stats)
    assert all(v is True for v in items.values()), [i for i, v in items.items() if v is not True]
    assert ld["paths"] == t.universe_paths() and "/src/pkg/edge.py" in ld["paths"]      # the path rule's halves
    assert "src/pkg/zero.py" not in ld["paths"] and "src/pkg/noloc.py" not in ld["paths"]
    obj = IC.predictor_check(t.layout(tmp_path, tiny[0].d), loaders={"tiny": ld})
    assert obj["all_equal"] and obj["repos"]["tiny"]["flux_flagged"] == 0


def test_2b_flux_case_by_case(tiny):
    """each row of section 2's telemetry-record table gives the stated value in the loader and in the table"""
    t, ld = tiny
    ix = {p: i for i, p in enumerate(ld["paths"])}
    lx = [U.dec(v) for v in ld["x"]["amplified_cascading_flux"]]
    for k, (rec, want, case) in enumerate(FLUX_CASES):
        p = t.paths[70 + k]
        got = lx[ix[p]]
        if want is None:
            assert math.isnan(got), (rec, got)
            assert t.flux[p]["value"] is None and t.flux[p]["special"] is None
        else:
            assert got == want, (rec, got)
            if math.isinf(want):
                assert t.flux[p]["special"] == "inf" and t.flux[p]["value"] is None
            else:
                assert t.flux[p]["value"] == want
        assert t.flux[p]["case"] == case, (rec, t.flux[p]["case"])
        assert t.flux[p]["loader_stops"] is False
    # duplicate paths: the later record that parses wins; a later unreadable one leaves the earlier value
    assert t.duplicates == 2
    assert lx[ix["src/pkg/m101.py"]] == 41.0 == t.flux["src/pkg/m101.py"]["value"]
    first100 = json.loads(t.rows[100][3])["amplified_cascading_flux"]
    assert lx[ix["src/pkg/m100.py"]] == float(first100) == t.flux["src/pkg/m100.py"]["value"]


def test_2c_degrees_nesting_bands(tiny, study_n):
    """out_degree counts every resolved call from the file whatever the target; a null nesting element is missing
    for its own value only; the bands, and 5 against 10, are recomputed on the files in use"""
    t, ld = tiny
    ix = {p: i for i, p in enumerate(ld["paths"])}
    xin = [U.dec(v) for v in ld["x"]["in_degree"]]
    xout = [U.dec(v) for v in ld["x"]["out_degree"]]
    # src id 5 (m004) calls tests/test_a.py (not in the universe): that call counts in its out-degree
    assert t.degrees["src/pkg/m004.py"]["out_degree"] == 2 and xout[ix["src/pkg/m004.py"]] == 2.0
    assert t.degrees["tests/test_a.py"]["in_degree"] == 1                    # stored, not in the universe
    assert xin[ix["src/pkg/m012.py"]] == t.degrees["src/pkg/m012.py"]["in_degree"]     # the self-call counts in both
    nm, nn = ([U.dec(v) for v in ld["x"][k]] for k in ("nest_max", "nest_mean"))
    assert math.isnan(nm[ix["src/pkg/m110.py"]]) and math.isnan(nn[ix["src/pkg/m110.py"]])
    assert nm[ix["src/pkg/m111.py"]] == 3.0 and math.isnan(nn[ix["src/pkg/m111.py"]])
    assert math.isnan(nm[ix["src/pkg/m112.py"]]) and nn[ix["src/pkg/m112.py"]] == 2.5
    assert ld["k"] == 10 and ld["in_use"]["def_safety"]["k"] == 5 and len(ld["in_use"]["def_safety"]["idx"]) < 300
    # m110 (absent), m112 (null first element) and /src/pkg/edge.py (the nesting file names it without the slash)
    assert ld["in_use"]["nest_max"]["k"] == 10 and len(ld["in_use"]["nest_max"]["idx"]) == len(ld["paths"]) - 3
    stats = U.load_sealed_stats(t.sealed)
    pb, cmp, _ = D.load_dirs(t.d / "tables/phase_b/tiny", t.d / "tables/compare/tiny")
    d = D.derive("tiny", pb, cmp, stats)
    idx, band, k = D.in_use(d, "def_safety", stats)
    assert k == 5 and list(idx) == ld["in_use"]["def_safety"]["idx"] and list(band) == ld["in_use"]["def_safety"]["band"]
    rs = [U.dec(v) for v in ld["x"]["risk_safety_nonzero"]]
    ra = [U.dec(v) for v in ld["x"]["risk_safety_among_nonzero"]]
    assert rs[ix["src/pkg/m060.py"]] == 0.0 and math.isnan(ra[ix["src/pkg/m060.py"]])        # negative
    assert rs[ix["src/pkg/m061.py"]] == 0.0 and math.isnan(ra[ix["src/pkg/m061.py"]])        # zero


def test_2d_a_record_that_stops_the_loader_is_flagged(study_n, tmp_path):
    """valid JSON that is not an object: the reference loader stops; the flux table flags the row, and the check
    reports the count (and the stage's code, by exception type)"""
    t = Tiny(study_n, tmp_path / "t2", non_object=True)
    assert t.flux[t.paths[95]]["loader_stops"] is True and t.flux[t.paths[95]]["case"] == "not_object"
    L = t.layout(tmp_path / "scratch", study_n.tree)
    obj = IC.predictor_check(L)
    rec = obj["repos"]["tiny"]
    assert rec["code"] == "unclassified" and rec["flux_flagged"] == 1 and all(v is None for v in rec["items"].values())
    IC.write_public(tmp_path / "o.json", obj, IC.vocab(L))


def test_2e_predictor_list_and_constants_equal_the_reference():
    """derive.PREDICTORS (order, role, count flag) and the scorer's constants equal the reference's, read from its
    source by ast"""
    src = ROOT / "tools" / "sa3_score.py"
    assert list(U.literal(src, "PREDICTORS").items()) == list(D.PREDICTORS.items())
    assert U.literal(src, "CONFIRMATORY") == SCO.CONFIRMATORY
    assert U.literal(src, "NEW_LANGS") == SCO.NEW_LANGS
    assert U.literal(src, "UNAVAILABLE") == SCO.UNAVAILABLE
    assert U.literal(src, "SEED") == SCO.SEED and U.literal(src, "N_PERMS") == SCO.N_PERMS == SCO.N_DRAWS
    assert U.literal(src, "POST_UNBLINDING") == SCO.POST_UNBLINDING
    assert tuple(IC.PREDICTOR_NAMES) == tuple(D.PREDICTORS)


# ========================================================================================= 3. the cell map
def _all_equal(study: Study) -> dict:
    m = CM.cell_map(study.result, study.comparison())
    print(f"\nstudy {study.which}:\n" + CM.render(m))
    return m


def test_3a_cell_map_all_equal_on_study_n(study_n):
    m = _all_equal(study_n)
    assert m["all_equal"], CM.render(m)
    assert set(m["per_repo"]) == set(study_n.repos)
    assert all(m["classes"][c]["equal"] > 0 for c in "WDR")
    assert set(study_n.result) == set(study_n.comparison())      # every key the reference writes


def test_3b_cell_map_all_equal_on_study_p(study_p):
    m = _all_equal(study_p)
    assert m["all_equal"], CM.render(m)
    assert set(study_p.result) == set(study_p.comparison())


def test_3c_cell_map_semantics():
    """exact equality; NaN, null and an absent key distinguished; a whole number is not a real; nothing excused;
    the first not-equal R cell named by position, later ones marked and counted"""
    ref = {"valid": True, "engine": "e", "repos": {
        "a": {"n": 3, "outcomes": {"HP": {"x": {"status": "ok", "bauc": 0.1, "null_sd": 0.2, "perm_p": 0.5,
                                               "S9_logistic_z": float("nan"), "S7_tight": None}}},
              "specificity": {"x": 0.01}},
        "b": {"n": 4, "outcomes": {"HP": {"x": {"status": "ok", "bauc": 0.3, "null_sd": 0.4, "perm_p": 0.1}}},
              "specificity": {}}},
           "side_counts": {"x": {"above": 1, "sign_test_p": None}}}
    assert CM.cell_map(ref, json.loads(json.dumps(ref)))["all_equal"]
    cases = {
        "nan vs null": (("repos", "a", "outcomes", "HP", "x", "S9_logistic_z"), None, "D"),
        "null vs nan": (("repos", "a", "outcomes", "HP", "x", "S7_tight"), float("nan"), "D"),
        "int vs real": (("repos", "a", "n"), 3.0, "W"),
        "one bit": (("repos", "b", "outcomes", "HP", "x", "bauc"), math.nextafter(0.3, 1), "D"),
        "zero sign": (("side_counts", "x", "sign_test_p"), None, "D"),
    }
    for name, (path, val, cls) in cases.items():
        c = copy.deepcopy(ref)
        o = c
        for k in path[:-1]:
            o = o[k]
        o[path[-1]] = val
        m = CM.cell_map(ref, c)
        if name == "zero sign":
            assert m["all_equal"]
            continue
        assert not m["all_equal"] and m["classes"][cls]["not_equal"] == 1, (name, m)
    c = copy.deepcopy(ref)
    del c["repos"]["a"]["outcomes"]["HP"]["x"]["S7_tight"]                      # absent key
    m = CM.cell_map(ref, c)
    assert m["classes"]["W"]["not_equal"] == 1 and m["not_equal"][0]["kind"] == "only in the reference"
    c = copy.deepcopy(ref)
    c["repos"]["b"]["specificity"] = {"x": 0.0}                                  # {} against a value: R
    assert CM.cell_map(ref, c)["classes"]["R"]["not_equal"] == 2
    c = copy.deepcopy(ref)
    c["repos"]["a"]["outcomes"]["HP"]["x"]["null_sd"] = 0.25                     # first R difference
    c["repos"]["b"]["outcomes"]["HP"]["x"]["perm_p"] = 0.2                       # a later one
    c["side_counts"]["x"]["above"] = 2
    m = CM.cell_map(ref, c)
    assert m["first_R"] == ["a", "HP", "x"] and m["classes"]["R"]["not_equal"] == 3
    assert [x["note"] for x in m["not_equal"]] == ["first not-equal R cell", "may follow from the first",
                                                   "may follow from the first"]
    assert m["R_after_first"] == {"equal": 4, "not_equal": 2}
    assert CM.classify(("summaries", "HP|x|minus_control|all_drawn", "mean")) == "R"
    assert CM.classify(("summaries", "HP|x|bauc|all_drawn", "mean")) == "D"
    assert CM.classify(("summaries", "HP|x|bauc|all_drawn", "n")) == "W"
    assert CM.classify(("tests", "struct_branch", "reading")) == "R"
    assert CM.classify(("tests", "struct_branch", "bauc", "ci", 0)) == "D"
    assert CM.classify(("random_effects", "x", "mean")) == "R"


# ============================================================================================ 4. the stream
class SwapRepos(SCO.Scorer):
    def repo_order(self, rows):
        rows = list(rows)
        rows[0], rows[1] = rows[1], rows[0]
        return rows


class SwapOutcomes(SCO.Scorer):
    def outcome_order(self, r):
        return tuple(reversed(SCO.OUTCOMES))


class SilentDraws(SCO.Scorer):
    """a silent predictor that still draws its 200 permutations (and still records "instrument silent")"""

    def on_silent(self, d, oc, p, x, rng):
        if p == "state_danger":
            v = np.flatnonzero(~np.isnan(x))
            for _ in range(SCO.N_PERMS):
                self.S.block_permute(x[v], d["loc"][v], [d["paths"][i] for i in v], rng)


class SecondDrawAlways(SCO.Scorer):
    def control_draw(self, d, rng, pool, hp, K):
        yc = np.zeros(d["n"], int)
        for s in rng.choice(len(pool), K, replace=False):
            yc[d["pool"][pool[s]]] = 1
        yh = np.zeros(d["n"], int)
        for s in rng.choice(len(hp), K, replace=False):                         # even when K == len(hp)
            yh[d["hp_commits"][hp[s]]] = 1
        return yc, yh


class ChecksBeforeDraws(SCO.Scorer):
    """the empty-control check made between the two draws: a dropped draw no longer uses the second draw"""

    def control_draw(self, d, rng, pool, hp, K):
        yc = np.zeros(d["n"], int)
        for s in rng.choice(len(pool), K, replace=False):
            yc[d["pool"][pool[s]]] = 1
        if not (0 < yc.sum() < d["n"]):
            return None                                                         # before the second draw
        yh = np.zeros(d["n"], int)
        for s in (rng.choice(len(hp), K, replace=False) if K < len(hp) else range(len(hp))):
            yh[d["hp_commits"][hp[s]]] = 1
        return yc, yh


class LateDFault(SilentDraws):
    """SilentDraws (an early stream slip) and one D value changed in a late repo"""

    def finish_cell(self, repo, oc, p, c):
        if (repo, oc, p) == ("ctrl-plain", "HP", "struct_branch"):
            c = {**c, "S4_replaces": c["S4_replaces"] + 1e-6}
        return c


class OnlyDFault(SCO.Scorer):
    def finish_cell(self, repo, oc, p, c):
        if (repo, oc, p) == ("circuitpython", "HP", "struct_branch"):
            c = {**c, "residual": c["residual"] + 1e-9}
        return c


STREAM = {"two repos swapped": (SwapRepos, ["django", "HP", "in_degree"]),
          "two outcomes swapped": (SwapOutcomes, ["django", "HP", "in_degree"]),
          "a silent predictor made to draw": (SilentDraws, ["django", "HP", "def_safety"]),
          "the control's second draw unconditional": (SecondDrawAlways, ["django", "control", "in_degree"]),
          "the control's checks before its draws": (ChecksBeforeDraws, ["ctrl-early1", "HP", "in_degree"])}


@pytest.mark.parametrize("fault", list(STREAM))
def test_4a_stream_faults(study_n, fault):
    """each change to the loop makes R cells not equal while every W and D cell stays equal, and the first
    difference is named by its position"""
    cls, first = STREAM[fault]
    m = CM.cell_map(study_n.result, study_n.comparison(cls))
    print(f"\n{fault}:\n" + CM.render(m, 8))
    assert m["classes"]["R"]["not_equal"] > 0, fault
    assert m["classes"]["W"]["not_equal"] == 0 and m["classes"]["D"]["not_equal"] == 0, CM.render(m)
    assert m["first_R"][:len(first)] == first, (fault, m["first_R"])


def test_4b_a_local_fault_is_not_hidden(study_n):
    """one D value changed in a late repo is reported although an earlier R cell already differs; and alone, a
    D fault leaves every R cell equal"""
    m = CM.cell_map(study_n.result, study_n.comparison(LateDFault))
    assert m["first_R"][:3] == ["django", "HP", "def_safety"]
    d_cells = [c for c in m["not_equal"] if c["class"] == "D"]
    assert d_cells and d_cells[0]["cell"][:6] == ["repos", "ctrl-plain", "outcomes", "HP", "struct_branch",
                                                  "S4_replaces"], d_cells[:3]
    assert m["classes"]["W"]["not_equal"] == 0
    m = CM.cell_map(study_n.result, study_n.comparison(OnlyDFault))
    assert m["classes"]["R"]["not_equal"] == 0 and m["first_R"] is None
    assert m["classes"]["D"]["not_equal"] >= 1
    assert m["not_equal"][0]["cell"][:6] == ["repos", "circuitpython", "outcomes", "HP", "struct_branch", "residual"]


def _leaves(o, path=()):
    return dict(CM.flatten(o, path))


def test_4c_a_swap_of_non_adjacent_repos_also_moves_d_summaries(study_n):
    """FINDING (spec section 5 / blind-test table): a study summary is a mean over repos in loop order, so a swap
    of two repos that are not the first two changes the summation order and the last bits of D summaries. W stays
    equal; every D difference is in a study-level summary or test, and is a rounding difference"""
    class Swap05(SCO.Scorer):
        def repo_order(self, rows):
            rows = list(rows)
            rows[0], rows[5] = rows[5], rows[0]
            return rows
    cmp = study_n.comparison(Swap05)
    m = CM.cell_map(study_n.result, cmp)
    assert m["classes"]["W"]["not_equal"] == 0 and m["classes"]["R"]["not_equal"] > 0
    dcells = [c for c in m["not_equal"] if c["class"] == "D"]
    assert dcells, "expected summation-order differences"
    a, b = _leaves(study_n.result), _leaves(cmp)
    for c in dcells:
        key = tuple(int(x) if x.isdigit() else x for x in c["cell"])
        assert key[0] in ("summaries", "tests"), c
        x, y = a[key], b[key]
        assert abs(x - y) <= 1e-12 * max(1.0, abs(x)), (c, x, y)
    print(f"\nnon-adjacent swap: {len(dcells)} D cells differ by rounding only")


# ============================================================================ 5. the independent statistic
@pytest.mark.skip(reason="section 6: written by the second builder (a different model, without the reference); "
                         "tools/compare/indep_stat.py does not exist yet")
def test_5_independent_statistic():
    """Interface (section 6): effect(files, readings) -> float | None, where files is the files in use (after
    files with a missing value are dropped), each with size, path, value and label, and readings selects one
    reading of each of the seven open choices. Exactly one combination must equal the reference on every one of
    2,000 synthetic cases built to make every choice bite; every other reading must differ on at least one."""
    IS = _load("indep_stat")
    files = [{"size": 10.0, "path": "a.py", "value": 1.0, "label": 1}, {"size": 12.0, "path": "b.py", "value": 0.0,
                                                                          "label": 0}]
    IS.effect(files, IS.READINGS_PRIOR)


# ================================================================================ 6. the blind test's runner
def _side(study: Study, dst: Path) -> Path:
    """study's reference side in the runner's layout: tree/ (no .git), study/, pool/"""
    shutil.copytree(study.tree, dst / "tree", ignore=shutil.ignore_patterns(".git", "__pycache__"))
    shutil.copytree(study.decoy / "study", dst / "study")
    shutil.copytree(study.decoy / "pool", dst / "pool", symlinks=True)
    return dst


def test_6_blind_runner_on_two_example_copies(study_p, tmp_path, capsys):
    """two copies of my own: 01 clean; 02 with one nesting value changed (a fault of a kind not in the spec's
    table). The runner prints per copy and per layer fired or silent, with and without the seal"""
    pristine = _side(study_p, tmp_path / "pristine")
    seal = BR.manifest(pristine)
    copies = tmp_path / "copies"
    _side(study_p, copies / "01")
    c2 = _side(study_p, copies / "02")
    nf = c2 / "study" / "sa3_nesting" / "django.json"
    n = json.loads(nf.read_text())
    p0 = sorted(n["files"])[11]
    n["files"][p0] = [n["files"][p0][0] + 3, n["files"][p0][1]]
    nf.write_text(json.dumps(n) + "\n")
    rows = BR.run(copies, study_p.tables, study_p.sealed, seal, tmp_path / "work")
    out = capsys.readouterr().out
    print(BR.header())
    for k, r in rows.items():
        print(BR.line(k, r))
    assert rows["01"]["layers"] == {k: "silent" for k in BR.LAYERS}, rows["01"]
    assert not rows["01"]["flagged_with_seal"] and not rows["01"]["flagged_seal_withheld"]
    l2 = rows["02"]["layers"]
    assert l2["seal"] == "fired" and l2["input_check"] == "fired" and l2["cell_map_WD"] == "fired", l2
    assert l2["placebo"] == "silent", l2           # nest_max is not a primary: the placebo cannot see it
    assert rows["02"]["flagged_with_seal"] and rows["02"]["flagged_seal_withheld"]
    assert "01" in out and "02" in out


# ============================================================== 7. no way out for label-side text (markers)
def _marked_study(study: Study, dst: Path, repo: str, bad_path: bool) -> Path:
    st = dst / "study"
    for sub in ("history", "sa3_scans", "sa3_outcomes", "meta_sa3", "sa3_nesting"):
        (st / sub).mkdir(parents=True)
        for f in (study.decoy / "study" / sub).glob(f"{repo}*"):
            if f.name.startswith(repo + ".") or f.name.startswith(repo + "_"):
                shutil.copy2(f, st / sub / f.name)
    of = st / "sa3_outcomes" / f"{repo}.json"
    o = json.loads(of.read_text())
    uni = study._loaders[repo]["paths"] if repo in study._loaders else None
    o["note"] = MARK_TEXT
    o["outcomes"]["control_pool"]["commits"][MARK_SHA] = [uni[5] if uni else o["outcomes"]["HP"]["files"][0]]
    o["outcomes"]["HP"]["commits"][MARK_SHA[::-1]] = [o["outcomes"]["HP"]["files"][0]]
    if bad_path:
        o["outcomes"]["HP"]["files"].append(MARK_PATH)
        o["outcomes"]["HP"]["commits"][MARK_SHA[::-1]].append(MARK_PATH)
    of.write_text(json.dumps(o) + "\n")
    T.build_label_tables(st / "sa3_outcomes", [repo], dst / "labels")
    return st


@pytest.mark.parametrize("bad_path", [False, True], ids=["markers", "marker-path-stops-the-loader"])
def test_7_markers_appear_in_no_public_output(study_n, scratch, tmp_path, bad_path):
    """planted markers in a decoy's outcome file (a commit hash, a free-text field, a path the loader refuses)
    appear in no public output of either side of the input check, and a value outside the fixed shapes is
    refused naming the field only"""
    repo = "go"
    study_n.loaders(scratch / "n")
    st = _marked_study(study_n, tmp_path, repo, bad_path)
    L = IC.Layout(st, study_n.tree, study_n.tables / "phase_b", study_n.tables / "compare", study_n.sealed,
                  tmp_path / "scratch", label_tables=tmp_path / "labels")
    pred = IC.predictor_check(L, repos=[repo])
    lab = IC.label_check(L, st / "sa3_outcomes", repos=[repo])
    texts = [IC.write_public(tmp_path / "pred.json", pred, IC.vocab(L)),
             IC.write_public(tmp_path / "lab.json", lab, IC.vocab(L), label=True),
             (tmp_path / "pred.json").read_text(), (tmp_path / "lab.json").read_text()]
    for t in texts:
        for mk in (MARK_SHA, MARK_SHA[::-1], MARK_TEXT, MARK_PATH, "zz_label_marker", "LABELMARKER"):
            assert mk not in t, mk
    assert pred["all_equal"], pred
    if bad_path:
        assert lab["repos"][repo]["code"] == "assertion" and not lab["all_equal"]
    else:
        assert lab["all_equal"], lab
    voc = IC.vocab(L)
    for bad in ({**pred, "note": MARK_TEXT},
                {**pred, "repos": {repo: {**pred["repos"][repo], "code": MARK_TEXT}}},
                {**pred, "repos": {repo: {**pred["repos"][repo], "flux_flagged": MARK_TEXT}}},
                {**pred, "repos": {MARK_TEXT: pred["repos"][repo]}},
                {**pred, "repos": {repo: {**pred["repos"][repo], "items": {**pred["repos"][repo]["items"],
                                                                           "universe": "equal"}}}}):
        with pytest.raises(R.ReportError) as e:
            IC.write_public(tmp_path / "bad.json", bad, voc)
        assert MARK_TEXT not in str(e.value) and str(e.value).startswith("invalid report value: input_check")
    assert not (tmp_path / "bad.json").exists()


# ================================================================================ 8. the coverage list
def test_8_coverage_list(study_n, study_p):
    """stage_score, control_effects, churn_any and summarize under the standard library's tracer on both
    studies: every executable line not executed is listed with the reason no decoy reaches it; the list may not
    grow"""
    cov = DS.coverage([study_n.dir, study_p.dir], ROOT / "tools" / "sa3_score.py")
    print("\nexecutable lines:", cov["executable"])
    unexplained = []
    for f, ls in cov["unexecuted"].items():
        for x in ls:
            why = DS.reason_for(x["text"])
            print(f"  {f}:{x['line']}  {x['text'][:70]}  -- {why}")
            if why is None:
                unexplained.append((f, x["line"], x["text"]))
    assert not unexplained, unexplained
    for b in (study_n, study_p):
        assert json.loads((b.decoy / "reference" / "coverage.json").read_text())["rc"] == 0
        assert b.rec["reference"]["traced_result_identical"]


# ===================================================== 9. the comparison route reads the sealed copies only
def test_9_a_fault_in_the_tree_under_test_moves_only_the_reference(study_n, tmp_path):
    """the caliper changed in the tree under test's statistics module: the reference's numbers move; the
    comparison scorer, which reads the sealed copies, does not; and had it read the tree under test, both routes
    would have shared the fault and agreed"""
    side = _side(study_n, tmp_path / "side")
    f = side / "tree" / "tools" / "sa3_stats.py"
    src = f.read_text()
    assert "CALIPER = 1.5\n" in src
    f.write_text(src.replace("CALIPER = 1.5\n", "CALIPER = 1.4\n"))
    faulty = BR.reference_result(side, tmp_path / "scratch")
    assert faulty is not None
    moved = CM.cell_map(study_n.result, faulty)
    assert moved["classes"]["D"]["not_equal"] > 0                       # the reference's numbers moved
    cmp = study_n.comparison()
    assert CM.cell_map(study_n.result, cmp)["all_equal"]                 # the comparison's did not
    m = CM.cell_map(faulty, cmp)
    assert m["classes"]["D"]["not_equal"] > 0                            # so the cell map fires
    shared = tmp_path / "shared_sealed"
    shutil.copytree(study_n.sealed, shared)
    shutil.copyfile(f, shared / "tools" / "sa3_stats.py")
    shutil.copyfile(tmp_path / "scratch" / "score" / "tree" / "docs" / "sa3_lock.json", shared / "docs" / "sa3_lock.json")
    both = json.loads(SCO.dumps(SCO.Scorer(shared, SCO.load_data(
        study_n.tables / "phase_b", study_n.tables / "compare", study_n.tables / "labels", shared)).score()))
    mb = CM.cell_map(faulty, both)
    assert mb["all_equal"], CM.render(mb)                                # a shared fault is invisible


def test_9b_the_sealed_statistics_module_is_checked_before_it_is_loaded(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "sa3_stats.py").write_text("import os\nCALIPER = 1.5\n")
    with pytest.raises(RuntimeError):
        U.load_sealed_stats(tmp_path)
    assert U.stats_imports(ROOT / "tools" / "sa3_stats.py") <= U.STATS_IMPORTS


# ======================================================================================= 10. label tables
def test_10_label_tables_positions_empty_commits_duplicate_hashes(tmp_path):
    outcome = {"outcomes": {**{oc: {"files": [], "commits": {}} for oc in T.SCORED},
                            "control_pool": {"commits": {}}}}
    outcome["outcomes"]["HP"]["files"] = ["b.py", "a.py"]
    hp = {f"{i:040x}": (["a.py"] if i % 3 else []) for i in range(14)}
    outcome["outcomes"]["HP"]["commits"] = hp
    outcome["outcomes"]["control_pool"]["commits"] = {"f" * 40: ["a.py", "a.py", "b.py"]}
    built = T.label_rows("r", outcome)
    assert built["repeated_paths"] == 1
    w = T.write(tmp_path / "r", built["rows"])
    T.write_index(tmp_path / "r", {}, w)
    lines = (tmp_path / "r" / w["hp_commit"]["file"]).read_text().splitlines()
    assert [json.loads(x)["position"] for x in lines] == list(range(14))          # 10 after 9, not after 1
    assert w["hp_commit"]["protected"] and "protected" in w["hp_commit"]["file"]
    back = T.read_dir(tmp_path / "r")
    got = T.commits_in_order(back["hp_commit"], back["hp_commit_file"])
    assert [s for s, _ in got] == list(hp) and [ps for _, ps in got] == [sorted(v) for v in hp.values()]
    assert sum(1 for _, ps in got if not ps) == 5                                   # commits with no path kept
    # a JSON object cannot hold one hash twice: the parsed file keeps the first position and the last value,
    # exactly as the loader's dict does; the table route follows the parsed object
    parsed = json.loads('{"outcomes": {"HP": {"files": [], "commits": {"aa": ["x"], "bb": [], "aa": ["y"]}}}}')
    assert list(parsed["outcomes"]["HP"]["commits"].items()) == [("aa", ["y"]), ("bb", [])]
    # two positions carrying one hash (possible only in a damaged table): refused, by count, never by name
    rows = [{"repo": "r", "position": 0, "sha": "c" * 40, "n_paths": 0},
            {"repo": "r", "position": 1, "sha": "c" * 40, "n_paths": 0}]
    with pytest.raises(T.TableError) as e:
        T.commits_in_order(rows, [])
    assert "c" * 10 not in str(e.value)
    with pytest.raises(T.TableError):
        T.commits_in_order([{**rows[0], "position": 1}], [])
    C = U.canon()
    with pytest.raises(C.CanonError):
        C.table_bytes("hp_commit", [{"repo": "r", "position": "0", "sha": "x", "n_paths": 0}], T.TABLES["hp_commit"])
    with pytest.raises(C.CanonError):
        C.table_bytes("hp_commit", [{"repo": "r", "position": True, "sha": "x", "n_paths": 0}], T.TABLES["hp_commit"])


def test_10b_schema_tables_hash_as_before(study_n):
    """the canonical writer's change leaves every table of schema.TABLES as it was: phase B's stored hashes are
    recomputed here with the old key rule (the UTF-8 bytes of string keys), and PHASE_A in
    tests/test_tables_phase_b.py is checked by that file"""
    import hashlib
    C = U.canon()
    S = sys.modules["schema"]
    for r in ("django", "racket"):
        idx = json.loads((study_n.tables / "phase_b" / r / "index.json").read_text())
        for name, t in idx["tables"].items():
            rows = C.read_rows(study_n.tables / "phase_b" / r / t["file"])
            reals = [c for c, ty in S.TABLES[name]["columns"] if ty == "real"]
            rows = [{**x, **{c: (None if x[c] is None else float.fromhex(x[c])) for c in reals}} for x in rows]
            old = sorted(((tuple(x[k].encode("utf-8", "surrogateescape") for k in S.TABLES[name]["key"]),
                           C.row_bytes(name, x)) for x in rows), key=lambda kv: kv[0])
            assert hashlib.sha256(b"".join(b + b"\n" for _, b in old)).hexdigest() == t["hash"] == \
                C.table_hash(name, rows)


# ================================================================== 11. the decoy studies' conditions
@pytest.mark.parametrize("which", ["N", "P"])
def test_11_decoy_study_conditions(request, which):
    s = request.getfixturevalue(f"study_{which.lower()}")
    m, res = {r["repo"]: r for r in s.marg}, s.result
    drawn = [r for r in s.repos if m[r]["drawn"]]
    assert len(s.repos) == 12 and len(drawn) == 10
    assert sum(m[r]["family"] == "C" for r in drawn) >= 5 and sum(m[r]["family"] != "C" for r in drawn) >= 5
    assert {"django", "circuitpython", "mediawiki", "freebsd-src", "go"} <= set(s.repos)
    assert len(set(s.repos) & SCO.NEW_LANGS) >= 2
    assert sum(bool(m[r]["merge_units"]) for r in s.repos) >= 2
    assert any(m[r]["window_days"] < 730 for r in drawn) and any(m[r]["window_days"] >= 730 for r in drawn)
    big = [r for r in s.repos if res["repos"][r]["n"] >= 600]
    assert big and any("S7_tight" in c for c in res["repos"][big[0]]["outcomes"]["HP"].values())
    assert any(res["repos"][r].get("specificity") == {} for r in s.repos)                      # pool under five
    o = {r: json.loads((s.decoy / "study/sa3_outcomes" / f"{r}.json").read_text())["outcomes"] for r in s.repos}
    more = [r for r in s.repos if len(o[r]["HP"]["commits"]) > len(o[r]["control_pool"]["commits"]) >= 5
            and m[r]["HP"]["clears_floor"]]
    assert any(res["repos"][r]["specificity"] for r in more)                                 # the second draw
    assert any(res["repos"][r]["specificity"] == {} for r in more)              # every draw dropped after both
    cells = [c for r in s.repos for oc in res["repos"][r]["outcomes"].values() for c in oc.values()]
    assert any(c["status"] == "instrument silent" for c in cells)
    assert any(c["status"] == "under pair floor" for c in cells)
    assert any(not m[r]["HP"]["clears_floor"] for r in s.repos)                                # a floor failed
    assert all(not m[r][oc]["clears_floor"] for r in s.repos for oc in ("HP_revert", "HP_cve"))
    for cut in ("C_family", "managed"):
        assert "mean" in res["summaries"][f"HP|struct_branch|bauc|{cut}"]
    assert any(c.get("dropped_null") for c in cells)
    assert any(t.get("bands") == 5 for t in [{"bands": ld["in_use"]["struct_branch"]["k"]}
                                              for ld in s.loaders(s.dir / "ld").values()])


# ============================================================================== 12. refusals and the guard
def test_12_refusals_and_guards(tmp_path, capsys):
    assert T.main(["predictor", "--real", "--out", str(tmp_path / "o")]) == 2
    assert T.main(["labels", "--real", "--i-am-the-reviewer-session", "--out", str(tmp_path / "o")]) == 2
    assert T.main(["predictor", "--decoy", str(SR.STUDY), "--out", str(tmp_path / "o")]) == 2
    argv = ["--tables", "t", "--compare-tables", "c", "--sealed", "s", "--ref", "r", "--scratch", str(tmp_path / "s"),
            "--out", str(tmp_path / "o.json")]
    assert IC.main(["--real"] + argv) == 2
    assert IC.main(argv) == 2
    assert IC.main(["--decoy", str(SR.LAWS / "x")] + argv) == 2
    for bad in (SR.STUDY / "x", SR.POOL / "x", ROOT / "x", Path("/nvme-data/x"), SR.HOME / ".blind/x"):
        with pytest.raises(SR.SandboxError):
            SR.check_rw(bad)
    assert not (tmp_path / "o").exists() and not (tmp_path / "o.json").exists()
    import builtins
    opened = []
    real_open = builtins.open

    def spy(f, *k, **kw):
        opened.append(str(f))
        return real_open(f, *k, **kw)
    for fn, args in ((IC.stage, ["--repo", "django", "--ref", str(tmp_path), "--rundir", str(tmp_path)]),
                     (T.stage, ["--repo", "django", "--rundir", str(tmp_path), "--out", str(tmp_path)])):
        opened.clear()
        builtins.open = spy
        try:
            with pytest.raises(SR.SandboxError):
                fn(args)
        finally:
            builtins.open = real_open
        assert opened == ["/proc/self/mountinfo"], opened
    assert not (tmp_path / "result.json").exists()


def test_3d_cell_map_all_equal_on_the_gate_failed_variant(study_p):
    """study P with its placebo gate failed (the reference's NO FINDING branch), compared like the studies"""
    g = study_p.rec["gate"]
    ref = json.loads(Path(g["result"]).read_text())
    assert not ref["valid"] and all(t["reading"].startswith("NO FINDING") for p, t in ref["tests"].items()
                                    if p in SCO.CONFIRMATORY)
    cmp = json.loads(SCO.dumps(SCO.Scorer(Path(g["sealed"]), copy.deepcopy(study_p.data())).score()))
    m = CM.cell_map(ref, cmp)
    assert m["all_equal"], CM.render(m)
