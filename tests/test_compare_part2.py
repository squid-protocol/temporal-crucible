"""Tests of the comparison scorer, part 2 (docs/process/comparison_scorer_part2_spec.md, Revision 2): the
corrected readings (tools/compare/reading.py, against tools/compare/reading_b.py when the second build exists),
the named streams (tools/compare/streams.py and the one hook in scorer.py), the harvest variants
(tools/compare/harvest_variant.py) and the sensitivities (tools/compare/variants.py).

DECOYS only: part 1's two decoy studies (tools/compare/decoy_study.py; reused from COMPARE_STUDY_CACHE when that
names a finished build under ~/.claude/jobs or /tmp, else built under pytest's directory), copies of their files
edited here, and synthetic inputs. Every call into SA3 code runs inside tools/harness/sandbox_ro.py's sandbox:
the reference `stage_score` (its Holm block, on synthetic readings) and the reference outcome builder (on harvest
copies). In this process: the comparison scorer, the sealed copy of sa3_stats.py, and tools/owner's own code.

Scorer results are kept beside each study build (part2-<tag>-<key>.json, the key a hash of tools/compare/*.py,
this file, the sealed copies and the tables' indexes) so that tests run alone or in reverse do not recompute
them.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata as md
import itertools
import json
import os
import random
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
        try:
            spec.loader.exec_module(mod)
        except BaseException:
            del sys.modules[key]
            raise
    return sys.modules[key]


U = _load("_util")
sys.modules.setdefault("tools_compare__util", U)
RD = _load("reading")
SCO = _load("scorer")
ST = _load("streams")
HV = _load("harvest_variant")
V = _load("variants")
CM = _load("cellmap")
DS = _load("decoy_study")
T = _load("tables")
SB = U.harness_sandbox()
SR = U.sandbox_ro()
P = U.phase_b()

S, C, N, F = RD.SUPPORTED, RD.CONTRADICTED, RD.NOT_DETECTED, RD.NOT_FITTED
DSPEC, TRACK, NR, H, G = RD.SPECIFIC, RD.ACTIVITY, RD.NOT_ROBUST, RD.HOLM, RD.GATE
NAMES = RD.NAMES


# ============================================================================================ environment
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
    """decided INSIDE the harness sandbox, as part 1's tests decide it"""
    w = SB.prepare(base / "engine-probe")
    (w / "tree/tools/harness").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "tools/harness/sandbox.py", w / "tree/tools/harness/sandbox.py")
    p = SB.run(["/usr/bin/python3", "-I", "-B", "-c",
                f"import os; print(os.path.isdir({str(SB.ENGINE / 'gitgalaxy')!r}))"], w, timeout=120)
    return p.stdout.strip() == "True"


@pytest.fixture(scope="session")
def base2(tmp_path_factory) -> Path:
    why = _skip_reason()
    if why:
        pytest.skip(why)
    env = os.environ.get("COMPARE_STUDY_CACHE")
    b = SB.check_work(Path(env)) if env else tmp_path_factory.mktemp("compare2")
    b.mkdir(parents=True, exist_ok=True)
    if not _engine_present(b):
        pytest.skip("engine export not present")
    return b


def _code_key(extra: str = "") -> str:
    h = hashlib.sha256(extra.encode())
    for f in sorted(CMPDIR.glob("*.py")) + [Path(__file__)]:
        h.update(f.name.encode() + b"\0" + f.read_bytes())
    return h.hexdigest()[:16]


class Study2:
    def __init__(self, b: Path, which: str):
        self.rec = DS.build(b, which)
        self.which = which
        self.dir = b / which
        p = self.rec["paths"]
        self.decoy = Path(p["decoy"])
        self.tables = Path(p["tables"])
        self.sealed = Path(p["sealed"])
        self.result = json.loads(Path(p["result"]).read_text())
        self.marg = json.loads((self.decoy / "docs" / "sa3_outcome_marginals.json").read_text())
        self.repos = [r["repo"] for r in self.marg if r["status"] == "ok"]
        self.inputs = {"decoy": str(self.decoy), "pb": self.tables / "phase_b", "ct": self.tables / "compare",
                       "lt": self.tables / "labels", "sealed": self.sealed}
        self._data = None

    def data(self) -> dict:
        if self._data is None:
            self._data = SCO.load_data(self.tables / "phase_b", self.tables / "compare", self.tables / "labels",
                                       self.sealed)
        return self._data

    def key(self, tag: str) -> str:
        h = hashlib.sha256(_code_key(tag).encode())
        for f in sorted(self.sealed.rglob("*")) + sorted(self.tables.rglob("index.json")):
            if f.is_file():
                h.update(str(f).encode() + b"\0" + f.read_bytes())
        return h.hexdigest()[:20]

    def cached(self, tag: str, make) -> dict:
        f = self.dir / f"part2-{tag}-{self.key(tag)}.json"
        if os.environ.get("COMPARE_PART2_NO_KEEP"):        # recompute; keep nothing
            return json.loads(json.dumps(make(), indent=1))
        if f.exists():
            return json.loads(f.read_text())
        res = make()
        text = json.dumps(res, indent=1) + "\n"
        f.write_text(text)
        return json.loads(text)

    def score(self, tag: str, cls, data=None, marg=None) -> dict:
        def make():
            sc = cls(self.sealed, copy.deepcopy(self.data() if data is None else data))
            if marg is not None:
                sc.marg = marg
            return json.loads(SCO.dumps(sc.score()))
        return self.cached(tag, make)

    def frozen_outcome(self, repo: str) -> dict:
        return json.loads((self.decoy / "study" / "sa3_outcomes" / f"{repo}.json").read_text())


@pytest.fixture(scope="session")
def s2n(base2) -> Study2:
    return Study2(base2, "N")


@pytest.fixture(scope="session")
def s2p(base2) -> Study2:
    return Study2(base2, "P")


@pytest.fixture(scope="session")
def hscratch(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("part2_harvest")


# ===================================================================================== 1. the reading rule
def _inputs(control_states=(S, N)):
    """every input of section 2.4: three tests, primary and residualised each of four readings, control
    supported or not, every weak order of the three p-values (13), the gate passed or failed"""
    per = list(itertools.product(RD.READINGS, RD.READINGS, control_states))
    orders = RD.dense_orders()
    for combo in itertools.product(per, repeat=3):
        for ranks in orders:
            t = RD.make_tests(combo, ranks)
            for gate in (True, False):
                yield t, gate


def test_1a_the_counts_of_section_2_1():
    c = RD.counts_729()
    assert c["total"] == 729
    assert (c["change1"]["differ"], c["change1"]["more"]) == (135, 51)
    assert (c["change2"]["differ"], c["change2"]["more"]) == (604, 0)
    assert (c["both"]["differ"], c["both"]["more"]) == (631, 51)
    assert c["change1"]["fewer"] == c["change2"]["fewer"] == c["both"]["fewer"] == 0
    assert c["plain_null_same"]


def test_1b_equal_where_no_correction_applies():
    """over every input of section 2.4 (851,968): where the predicate says no correction applies, the corrected
    words equal the coded words letter for letter; every corrected word is a word the coded rule can print;
    corrected never gives fewer readings beginning "supported"; change 2 never gives more"""
    n = n_free = 0
    for t, gate in _inputs():
        n += 1
        c, k = RD.coded(t, gate), RD.corrected(t, gate)
        assert set(k.values()) <= set(RD.WORDS)
        assert sum(v.startswith("supported") for v in k.values()) >= sum(v.startswith("supported")
                                                                          for v in c.values())
        k2 = RD.change2_only(t, gate)
        assert sum(v.startswith("supported") for v in k2.values()) <= sum(v.startswith("supported")
                                                                           for v in c.values())
        if not RD.applies(t)["any"]:
            n_free += 1
            assert k == c, (t, gate, c, k)
        if not gate:
            assert set(c.values()) == set(k.values()) == {G}
    assert n == 32 ** 3 * 13 * 2
    print(f"\n{n} inputs, {n_free} where no correction applies")
    assert n_free > 0


def _t(*rows, ranks=(0, 1, 2)):
    """rows: (primary, residualised, control) for B, C, D"""
    return RD.make_tests(rows, ranks)


def test_1c_named_cases():
    # defect 42: the first test contradicted, the next two supported
    t = _t((C, C, S), (S, S, S), (S, S, N))
    assert RD.coded(t, True) == dict(zip(NAMES, (C, H, H)))
    assert RD.corrected(t, True) == dict(zip(NAMES, (C, DSPEC, TRACK)))
    # defect 43: primary supported, residualised not detected -- "not robust" under both rules
    t = _t((S, N, S), (N, N, S), (N, N, S))
    assert RD.coded(t, True) == dict(zip(NAMES, (NR, N, N)))
    assert RD.corrected(t, True) == dict(zip(NAMES, (NR, N, N)))
    # defect 43: primary not detected, residualised supported -- only the corrected rule says "not robust"
    t = _t((N, S, S), (N, N, S), (N, N, S))
    assert RD.coded(t, True) == dict(zip(NAMES, (N, N, N)))
    assert RD.corrected(t, True) == dict(zip(NAMES, (NR, N, N)))
    # the plain null
    t = _t((N, N, N), (N, N, N), (N, N, N))
    assert RD.coded(t, True) == RD.corrected(t, True) == dict(zip(NAMES, (N, N, N)))
    assert not RD.applies(t)["any"]
    # the gate failed
    t = _t((S, S, S), (C, N, S), (N, S, S))
    assert RD.coded(t, False) == RD.corrected(t, False) == dict(zip(NAMES, (G, G, G)))
    # all three not fitted, on both statistics
    t = _t((F, F, ""), (F, F, ""), (F, F, ""))
    assert RD.coded(t, True) == RD.corrected(t, True) == dict(zip(NAMES, (F, F, F)))
    # Holm order: by p, ties in the order given (B before C before D)
    t = _t((S, S, S), (C, C, S), (S, S, S), ranks=(1, 0, 1))
    assert list(RD.coded(t, True)) == ["risk_safety_score", "struct_branch", "amplified_cascading_flux"]
    assert RD.coded(t, True) == {"risk_safety_score": C, "struct_branch": H, "amplified_cascading_flux": H}
    assert RD.corrected(t, True) == {"risk_safety_score": C, "struct_branch": DSPEC,
                                     "amplified_cascading_flux": DSPEC}
    # a test after a stop that reads contradicted keeps "contradicted" (the owner's note, item 1)
    t = _t((N, N, S), (C, C, S), (S, S, S))
    assert RD.coded(t, True) == RD.corrected(t, True) == dict(zip(NAMES, (N, C, H)))


def test_1d_the_table_for_the_owner_is_the_generated_one():
    f = ROOT / "docs" / "process" / "reading_rule_table.md"
    text = RD.table_markdown()
    assert f.read_text() == text, "regenerate: python3 tools/compare/reading.py table --out " + str(f)
    rows = [ln for ln in text.splitlines() if ln.startswith("| ") and ln.split("|")[1].strip().isdigit()]
    assert len(rows) == 65536
    marked = [ln for ln in rows if ln.rstrip().endswith("| * |")]
    differ = sum(c != k for _s, _g, c, k in RD.table_rows())
    assert len(marked) == differ
    assert f"**65,536 rows**" in text and f"**{differ:,} differ**" in text
    print(f"\n{len(rows)} rows, {differ} differ")


READING_B = CMPDIR / "reading_b.py"


@pytest.mark.skipif(not READING_B.exists(), reason="tools/compare/reading_b.py (the second builder's file) does not "
                                                    "exist yet")
def test_1e_the_second_build_agrees_on_every_input():
    RB = _load("reading_b")
    n = nbad = 0
    first = []
    for t, gate in itertools.chain(_inputs(), _inputs(control_states=("contradicted", "not fitted", ""))):
        n += 1
        a = (RD.coded(t, gate), RD.corrected(t, gate))
        b = (RB.coded(copy.deepcopy(t), gate), RB.corrected(copy.deepcopy(t), gate))
        if a != b:
            nbad += 1
            if len(first) < 3:
                first.append((t, gate, a, b))
    assert not nbad, f"{nbad} of {n} inputs differ; first: {first}"
    print(f"\nreading.py and reading_b.py agree on {n} inputs")


# the reference's Holm block, transcribed line for line (tools/sa3_score.py:424-444); test 1f checks it is the
# file's text, and its driver runs the file's own stage_score
HOLM_BLOCK = '''    first = {p: summarize(pick(("HP", p, "bauc"), drawn)) for p in CONFIRMATORY}
    order = sorted(CONFIRMATORY, key=lambda p: first[p].get("p", 1.0))
    still = True
    for rank, p in enumerate(order):
        level = 1 - 0.05 / (len(order) - rank)
        b = summarize(pick(("HP", p, "bauc"), drawn), level)
        co = summarize(pick(("HP", p, "residual"), drawn), level)
        sp = summarize(pick(("HP", p, "minus_control"), drawn))
        reading = b["reading"]
        if reading == "supported" and not still:
            reading = "not detected (Holm: an earlier test in the family failed)"
        if b["reading"] != "supported":
            still = False
        if reading == "supported" and co["reading"] != "supported":
            reading = "not robust to the statistic"
        elif reading == "supported":
            reading = "supported, defect-specific" if sp.get("reading") == "supported" else \\
                      "supported, but tracks activity, not defects"
        if not res["valid"]:
            reading = "NO FINDING: the placebo gate failed"
        res["tests"][p] = {"holm_level": level, "bauc": b, "residual": co, "minus_control": sp, "reading": reading}
'''

DRIVER = r'''
"""in sandbox_ro only: the reference stage_score, its code unchanged, with its inputs replaced by synthetic
readings. Module globals of sa3_score are rebound (load, scored_repos, silent, design_for, S, churn_any,
control_effects, summarize, DOCS, SCANS, SEALED, PREDICTORS -> the four primaries); the Holm block runs as written."""
import contextlib, io, json, sys
from pathlib import Path
import numpy as np
code, rundir, cases_file = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(code / "tools"))
sys.path.insert(0, str(code / "tools" / "harness"))
import sandbox_ro
sandbox_ro.assert_inside_ro()
import sa3_score as SC
assert Path(SC.__file__).resolve().parent == (code / "tools").resolve()
OUTS = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")
docs = rundir / "docs"; docs.mkdir(exist_ok=True)
(docs / "sa3_lock.json").write_text(json.dumps({"files": {}}))
scans = rundir / "scans"; scans.mkdir(exist_ok=True)
(scans / "r0.json").write_text(json.dumps({"engine": "stub"}))
SC.DOCS, SC.SCANS, SC.SEALED = docs, scans, ()
PRIM = {p: SC.PREDICTORS[p] for p in SC.PRIMARIES}
SC.PREDICTORS = PRIM
CODE = {p: float(i + 1) for i, p in enumerate(PRIM)}
NAME = {v: p for p, v in CODE.items()}
row = {"repo": "r0", "drawn": True, "status": "ok", "merge_units": False, "window_days": 730.0, "family": "C",
       **{oc: {"clears_floor": oc == "HP"} for oc in OUTS}}
SC.scored_repos = lambda: [row]
NF = 4
def load(repo, with_predictors):
    return {"repo": repo, "paths": [f"f{i}" for i in range(NF)], "loc": np.ones(NF), "n": NF,
            "band": np.zeros(NF, int), "k": 1, "y": {oc: np.array([1, 0, 1, 0]) for oc in OUTS},
            "hp_commits": {}, "pool": {}, "x": {p: np.full(NF, CODE[p]) for p in PRIM}}
class Des:
    def clears_pair_floor(self): return True
    def effect(self, xv): return float(xv[0])
class FakeStats:
    CALIPER = 1.0
    block_permute = staticmethod(lambda xv, lv, pv, rng: xv)
    residual_effect = staticmethod(lambda xv, yv, band, k, cov: 1000.0 + float(xv[0]))
    auc_plain = staticmethod(lambda x, y: 0.0)
    sauc_minus_loc = staticmethod(lambda *a: 0.0)
    logistic_z = staticmethod(lambda *a: 0.0)
    boot_ci = staticmethod(lambda *a: [0.0, 0.0])
SC.load = load
SC.silent = lambda x, name="": False
SC.design_for = lambda d, y, valid=None, caliper=None, k=None: (Des(), d["band"], d["k"], np.arange(d["n"]))
SC.S = FakeStats
SC.churn_any = lambda d: np.zeros(d["n"], int)
SC.control_effects = lambda d, preds, rng: {p: 2000.0 + CODE[p] for p in preds}
CASE = {}
def summarize(vals, level=0.95):
    v = list(vals.values())
    if len(v) != 1:
        return {"n": len(v), "reading": "not fitted"}
    stat, c = divmod(v[0], 1000.0)
    t = CASE.get(NAME.get(c))
    if t is None:
        return {"n": 1, "reading": "not detected", "p": 0.5}
    if stat == 0:
        return {"n": 1, "reading": t["primary"], "p": t["p"]}
    return {"n": 1, "reading": t["residualised"] if stat == 1 else t["control"], "p": 0.5}
SC.summarize = summarize
out = []
for case in json.loads(cases_file.read_text()):
    CASE.clear()
    for t in case["tests"]:
        CASE[t["name"]] = t
    (docs / "sa3_placebo.json").write_text(json.dumps({"valid": case["gate"], "repos": {}}))
    with contextlib.redirect_stdout(io.StringIO()):
        rc = SC.stage_score()
    res = json.loads((docs / "sa3_result.json").read_text())
    out.append({"rc": rc, "readings": {t["name"]: res["tests"][t["name"]]["reading"] for t in case["tests"]},
                "order": [k for k in res["tests"] if k != "in_degree"]})
(rundir / "readings.json").write_text(json.dumps(out) + "\n")
'''


def _reference_holm(cases: list[dict], scratch: Path) -> list[dict]:
    """the reference stage_score in sandbox_ro on synthetic readings, one case after another in one sandbox"""
    code = HV.code_copy(SR.check_rw(scratch))
    rd = scratch / "holm"
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir()
    (rd / "driver.py").write_text(DRIVER)
    (rd / "cases.json").write_text(json.dumps(cases))
    home, tmp = rd / "home", rd / "tmp"
    home.mkdir()
    tmp.mkdir()
    P.write_gitconfig(home)
    spec = SR.Spec(rw=[rd], code=[code], inputs=[(str(P.LINGUIST_HOST / n), P.LINGUIST_DST / n)
                                                   for n in ("vendor.yml", "documentation.yml")],
                   env={"LAWS_LINGUIST_DIR": str(P.LINGUIST_DST)}, cwd=rd)
    p = SR.run(["/usr/bin/python3", "-I", "-B", str(rd / "driver.py"), str(code), str(rd), str(rd / "cases.json")],
               spec, home, tmp, timeout=3600)
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
    return json.loads((rd / "readings.json").read_text())


def test_1f_coded_is_the_reference_holm_block(tmp_path):
    """the transcription is the file's text, line for line; and the reference's own stage_score, run in the
    sandbox on synthetic readings, prints what `coded` prints: every state combination in B, C, D order with
    both gates (65,536), and every weak order of the p-values on every 16th combination (2,048 x 13)"""
    if not Path(SB.BWRAP).exists():
        pytest.skip("bwrap not installed")
    src = (ROOT / "tools" / "sa3_score.py").read_text().splitlines(keepends=True)
    assert "".join(src[423:444]) == HOLM_BLOCK
    per = list(itertools.product(RD.READINGS, RD.READINGS, (S, N)))
    combos = list(itertools.product(per, repeat=3))
    cases = [{"tests": RD.make_tests(c), "gate": g} for g in (True, False) for c in combos]
    cases += [{"tests": RD.make_tests(c, r), "gate": True} for c in combos[::16] for r in RD.dense_orders()]
    out = _reference_holm(cases, tmp_path)
    assert len(out) == len(cases) == 65536 + 2048 * 13
    bad = [(c, o) for c, o in zip(cases, out) if o["rc"] != 0 or RD.coded(c["tests"], c["gate"]) != o["readings"]
           or list(RD.coded(c["tests"], c["gate"])) != o["order"]]
    assert not bad, bad[:3]
    print(f"\nreference stage_score and coded agree on {len(cases)} synthetic inputs")


def test_1g_coded_on_the_decoy_results(s2n, s2p, base2):
    """on both studies and the gate-failed variant: the coded rule reproduces the reference's stored readings
    (beside() raises otherwise); the corrected reading and defect 48's comparison are printed"""
    gate = json.loads((base2 / "P" / "gate" / "done.json").read_text())
    for name, res, marg in (("N", s2n.result, s2n.marg), ("P", s2p.result, s2p.marg),
                            ("P gate failed", json.loads(Path(gate["result"]).read_text()), s2p.marg)):
        b = RD.beside(res)
        words = {n: b[n]["corrected"] for n in NAMES}
        ar = RD.allreverts_same_repos(res, marg, SCO.Scorer.summarize, words)
        print(f"\n{name}: " + "; ".join(f"{n}: {v['coded']} / {v['corrected']} ({v['status']})" for n, v in b.items()))
        print("  all reverts, same repos: " + "; ".join(f"{n} n={v['n']} {v['word']}" for n, v in ar.items()))
        for n in NAMES:
            assert b[n]["status"] in (RD.SAME, RD.DEPENDS)
            assert ar[n]["word"] in ("above zero", "below zero", "not detected", "not fitted")
    assert all(v["coded"] == G for v in RD.beside(json.loads(Path(gate["result"]).read_text())).values())


def test_1h_words_outside_the_confirmatory_tests():
    assert RD.level_word({"reading": S}) == "above zero"
    assert RD.level_word({"reading": C}) == "below zero"
    assert RD.level_word({"reading": N}) == "not detected"
    assert RD.level_word({"n": 1, "reading": F}) == "not fitted"
    assert RD.exploratory_word({"reading": S}) == "positive" and RD.exploratory_word({"reading": C}) == "negative"


# ===================================================================================== 2. the named streams
VECTORS = {   # DECISIONS.md, part 2, item 4: Generator(PCG64(SeedSequence(2982, spawn_key=K))).random(3)
    ("perm", "bun", "HP", "struct_branch"): ((635298010877155848, 0, 0, 5),
                                             ("0x1.9637eb8542ca7p-1", "0x1.0023445ff2650p-3", "0x1.d054f708354dap-1")),
    ("control", "bun"): ((635298010877155848, 1),
                         ("0x1.7e5e656551998p-3", "0x1.eea28f0cd2800p-7", "0x1.23efcb47b8c34p-2")),
}


def test_2a_stream_keys_and_vectors():
    for key, (sk, draws) in VECTORS.items():
        assert ST.spawn_key(key) == sk
        assert tuple(float(v).hex() for v in ST.generator(sk).random(3)) == draws
    assert ST.repo_int("bun") == int.from_bytes(hashlib.sha256(b"bun").digest()[:8], "big")
    assert ST.OUTCOMES == SCO.OUTCOMES and ST.PREDICTOR_ORDER == tuple(SCO.PREDICTORS)
    rng = np.random.default_rng(2982)
    assert SCO.Scorer.stream(None, ("perm", "x", "HP", "in_degree"), rng) is rng      # part 1: the shared stream
    assert SCO.Scorer.stream(None, ("control", "x"), rng) is rng


def _repo_cells(res: dict) -> dict:
    return dict(CM.flatten(res["repos"], ("repos",)))


def _study_close(a: dict, b: dict, rel: float = 1e-12) -> list:
    """study-level leaves (everything but `repos`) that differ beyond `rel` (relative) or in type/value"""
    fa = {p: v for p, v in CM.flatten(a) if p[0] != "repos"}
    fb = {p: v for p, v in CM.flatten(b) if p[0] != "repos"}
    bad = [p for p in set(fa) ^ set(fb)]
    for p in set(fa) & set(fb):
        x, y = fa[p], fb[p]
        if isinstance(x, float) and isinstance(y, float):
            if not (x == y or (x != x and y != y) or abs(x - y) <= rel * max(abs(x), abs(y))):
                bad.append(p)
        elif not CM.same(x, y):
            bad.append(p)
    return bad


class _Reverse:
    def repo_order(self, rows):
        return list(reversed(rows))


class NamedReversed(_Reverse, ST.NamedStreams):
    pass


class SharedReversed(_Reverse, SCO.Scorer):
    pass


def _named(s: Study2) -> dict:
    return s.score("named", ST.NamedStreams)


def _shared(s: Study2) -> dict:
    return s.score("shared", SCO.Scorer)


def test_2b_part1_with_the_hook_is_still_all_equal(s2n, s2p):
    for s in (s2n, s2p):
        m = CM.cell_map(s.result, _shared(s))
        assert m["all_equal"], CM.render(m)


def test_2c_reversed_repo_order(s2n):
    """named streams: every per-repo cell bit-identical, every study summary within 1e-12 relative; the shared
    stream: R cells change"""
    base, rev = _named(s2n), s2n.score("named_reversed", NamedReversed)
    a, b = _repo_cells(base), _repo_cells(rev)
    assert set(a) == set(b)
    diff = [p for p in a if not CM.same(a[p], b[p])]
    assert not diff, diff[:5]
    assert not _study_close(base, rev)
    m = CM.cell_map(_shared(s2n), s2n.score("shared_reversed", SharedReversed))
    print(f"\nshared stream, repos reversed:\n{CM.render(m, 4)}")
    assert m["classes"]["R"]["not_equal"] > 0


def _drop(monkeypatch, name: str):
    monkeypatch.setattr(SCO, "PREDICTORS", {k: v for k, v in SCO.PREDICTORS.items() if k != name})


DROPPED = "out_degree"


def test_2d_one_predictor_dropped(s2n, monkeypatch):
    """named streams: every other per-repo cell identical (the matched control's cells allowed to change: they
    draw for all predictors together); the shared stream: R cells of other predictors change"""
    base, sbase = _named(s2n), _shared(s2n)
    _drop(monkeypatch, DROPPED)
    got = s2n.score(f"named_drop_{DROPPED}", ST.NamedStreams)
    sgot = s2n.score(f"shared_drop_{DROPPED}", SCO.Scorer)
    a, b = _repo_cells(base), _repo_cells(got)
    keep = [p for p in a if DROPPED not in p]
    assert all(p in b for p in keep)
    control = [p for p in keep if p[2] == "specificity" and not CM.same(a[p], b[p])]
    other = [p for p in keep if p[2] != "specificity" and not CM.same(a[p], b[p])]
    assert not other, other[:5]
    print(f"\nnamed streams, {DROPPED} dropped: other per-repo cells identical; control cells changed: {len(control)}")
    sa, sb = _repo_cells(sbase), _repo_cells(sgot)
    moved = [p for p in sa if DROPPED not in p and p in sb and CM.classify(p) == "R" and not CM.same(sa[p], sb[p])]
    assert moved, "the shared stream should move R cells when a drawing predictor is dropped"
    print(f"shared stream, {DROPPED} dropped: {len(moved)} R cells of other predictors changed")


# ================================================================================ 3. the harvest variants
def _layout(study_dir: Path, pool: Path, scratch: Path) -> "HV.Layout":
    return HV.Layout(study_dir, pool, scratch)


UNPLANTED = ("django", "circuitpython", "mediawiki", "freebsd-src", "go", "racket")


def test_3a_an_unmodified_copy_reproduces_the_stored_file(s2n, hscratch):
    """section 5 test 4, second half: the reference builder, unchanged, in the sandbox, on the unmodified harvest
    copy, gives the stored outcome file (as parsed JSON, the over-cap sample left out) for every repo whose
    outcome file the decoy recipe did not edit"""
    L = _layout(s2n.decoy / "study", s2n.decoy / "pool", hscratch / "n_plain")
    for r in UNPLANTED:
        plain = HV.build(L, r, HV.prepare(L, r), "plain")
        assert HV.comparable(plain) == HV.comparable(s2n.frozen_outcome(r)), r


def _pool_commits(outcome: dict) -> list[str]:
    return sorted(s for s, v in outcome["outcomes"]["control_pool"]["commits"].items() if v)


def _edited_study(s: Study2, repo: str, dst: Path, rows: list[tuple[str, str, str]]) -> Path:
    """a study directory holding one repo's files, its harvest with `rows` added (as hist_meta would store them)"""
    st = dst / "study"
    for sub, names in (("history", [f"{repo}.db"]), ("sa3_scans", [f"{repo}.json", f"{repo}_master.db"]),
                       ("sa3_outcomes", [f"{repo}.json"]), ("sa3_nesting", [f"{repo}.json"]),
                       ("meta_sa3", [f"{repo}.db"])):
        (st / sub).mkdir(parents=True, exist_ok=True)
        for n in names:
            for sfx in ("", "-wal", "-shm"):
                src = s.decoy / "study" / sub / (n + sfx)
                if src.exists():
                    shutil.copyfile(src, st / sub / (n + sfx))
    con = sqlite3.connect(str(st / "meta_sa3" / f"{repo}.db"))
    try:
        con.executemany("insert into link values (?, ?, ?)", rows)
        con.commit()
        if con.execute("pragma journal_mode").fetchone()[0] == "wal":
            con.execute("pragma wal_checkpoint(TRUNCATE)")
    finally:
        con.close()
    return st


@pytest.fixture(scope="session")
def planted(s2n, tmp_path_factory):
    """django of study N with nine commits of its control pool given links (chosen by rule: the pool's commits
    with files, in hash order). EXPECTED, written before any variant was run on it:

      c_lower      issue_fix 'abc-12'                        case: leaves HP, HP_allreverts, HP_fixref; joins the pool
      c_lower2     issue_fix 'abc-14' and 'ABC-15'           case: stays (keeps a capital key)
      c_upper      issue_fix 'ABC-13'                        stays
      c_late       revert <a commit in the window>, issue_fix  late: leaves HP and HP_fixref; stays in HP_allreverts
      c_early      revert <the walk's first commit>, issue_fix  stays (the revert qualifies; rows kept)
      c_unres      revert '0000000deadbeef', issue_fix        stays (unresolved: rows kept)
      c_quote      revert '' (a quoted Revert line), issue_fix stays (rows kept)
      c_trailer    revert <late>, issue_fix <sha12>, trailer:fixes <sha12>  late: issue_fix row goes, the
                                                             trailer keeps it in HP and HP_fixref
      c_cve        revert <late>, cve, issue_fix              late: issue_fix row goes, the CVE keeps it in HP, HP_cve
    """
    repo = "django"
    fz = s2n.frozen_outcome(repo)
    pool = _pool_commits(fz)
    names = ("c_lower", "c_lower2", "c_upper", "c_late", "c_early", "c_unres", "c_quote", "c_trailer", "c_cve")
    c = dict(zip(names, pool[:9]))
    late_t = pool[20]                                      # a window commit: after the cut
    h = sqlite3.connect(f"file:{s2n.decoy / 'study' / 'history' / (repo + '.db')}?mode=ro", uri=True)
    try:
        early_t = h.execute("select sha from commit_ order by rowid limit 1").fetchone()[0]
    finally:
        h.close()
    rows = [(c["c_lower"], "issue_fix", "abc-12"),
            (c["c_lower2"], "issue_fix", "abc-14"), (c["c_lower2"], "issue_fix", "ABC-15"),
            (c["c_upper"], "issue_fix", "ABC-13"),
            (c["c_late"], "revert", late_t), (c["c_late"], "issue_fix", "9001"),
            (c["c_early"], "revert", early_t), (c["c_early"], "issue_fix", "9002"),
            (c["c_unres"], "revert", "0000000deadbeef"), (c["c_unres"], "issue_fix", "9003"),
            (c["c_quote"], "revert", ""), (c["c_quote"], "issue_fix", "9004"),
            (c["c_trailer"], "revert", late_t), (c["c_trailer"], "issue_fix", late_t[:12]),
            (c["c_trailer"], "trailer:fixes", late_t[:12] + ' ("a subject")'),
            (c["c_cve"], "revert", late_t), (c["c_cve"], "cve", "CVE-2020-12345"), (c["c_cve"], "issue_fix", "9005")]
    d = tmp_path_factory.mktemp("planted")
    st = _edited_study(s2n, repo, d, rows)
    L = _layout(st, s2n.decoy / "pool", d / "scratch")
    prep = HV.prepare(L, repo)
    out = {"repo": repo, "c": c, "late_t": late_t, "early_t": early_t, "L": L, "prep": prep, "rows": rows,
           "frozen": HV.build(L, repo, prep, "plain"), "case": HV.build(L, repo, prep, "case"),
           "late": HV.build(L, repo, prep, "late")}
    U0 = _layout(s2n.decoy / "study", s2n.decoy / "pool", d / "scratch0")      # the unedited django
    p0 = HV.prepare(U0, repo)
    out["natural_late"] = HV.changed_commits(HV.build(U0, repo, p0, "plain"), HV.build(U0, repo, p0, "late"))
    out["natural_late_rows"] = p0["result"]["late"]["deleted_rows"]
    return out


def test_3b_case_variant_on_the_edited_decoy(planted):
    c, fz, v = planted["c"], planted["frozen"], planted["case"]
    assert planted["prep"]["result"]["aprime"]["deleted_rows"] == 2           # abc-12, abc-14; nothing natural
    d = HV.commit_diff(fz, v)
    assert d["HP"] == {"left": [c["c_lower"]], "joined": []}
    assert d["HP_allreverts"] == {"left": [c["c_lower"]], "joined": []}
    assert d["HP_fixref"] == {"left": [c["c_lower"]], "joined": []}
    assert d["control_pool"] == {"left": [], "joined": [c["c_lower"]]}
    assert d["HP_revert"] == d["HP_cve"] == {"left": [], "joined": []}
    assert HV.changed_commits(fz, v) == {c["c_lower"]}
    for k in ("c_lower2", "c_upper", "c_late", "c_early", "c_unres", "c_quote", "c_trailer", "c_cve"):
        assert c[k] in fz["outcomes"]["HP"]["commits"] and c[k] in v["outcomes"]["HP"]["commits"], k


def test_3c_late_variant_on_the_edited_decoy(planted):
    c, fz, v = planted["c"], planted["frozen"], planted["late"]
    det = planted["prep"]["late_detail"]["commits"]
    assert det[c["c_unres"]]["reverts"][0]["target"] is None                   # preconditions of the plants
    assert det[c["c_quote"]]["reverts"][0]["target"] is None
    assert det[c["c_early"]]["reverts"][0]["target"] == planted["early_t"]
    assert not det[c["c_early"]]["reverts"][0]["late"] and det[c["c_late"]]["reverts"][0]["late"]
    natural = planted["natural_late"]
    assert not natural & set(c.values())
    expected = {c["c_late"]} | natural
    assert HV.changed_commits(fz, v) == expected
    d = HV.commit_diff(fz, v)
    assert c["c_late"] in d["HP"]["left"] and c["c_late"] in d["HP_fixref"]["left"]
    assert c["c_late"] in v["outcomes"]["HP_allreverts"]["commits"]
    assert d["control_pool"] == {"left": [], "joined": []}
    for k in ("c_early", "c_unres", "c_quote", "c_trailer", "c_cve"):
        assert c[k] in v["outcomes"]["HP"]["commits"], k
    assert c["c_trailer"] in v["outcomes"]["HP_fixref"]["commits"]
    assert c["c_cve"] in v["outcomes"]["HP_cve"]["commits"]
    assert c["c_early"] in v["outcomes"]["HP_revert"]["commits"]
    # rows deleted: c_late, c_trailer, c_cve (one issue_fix row each) and the natural ones
    assert planted["prep"]["result"]["late"]["deleted_rows"] == 3 + planted["natural_late_rows"]
    print(f"\nnatural late-revert commits leaving in unedited django: {len(natural)}")


def _rows(db: Path, table: str) -> list[tuple]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return sorted(con.execute(f"select * from {table}").fetchall(), key=repr)
    finally:
        con.close()


def test_3d_a_harvest_copy_differs_only_in_its_deleted_rows(planted):
    """section 5 test 4, first half: each variant copy is the unmodified copy minus exactly the rows its rule
    names; `meta` and `body` unchanged"""
    db = planted["prep"]["dir"] / "db"
    late = set(planted["prep"]["late_detail"]["late"])
    for name, gone in (("harvest_aprime.db", lambda r: r[1] == "issue_fix" and r[2] and "-" in r[2]
                        and r[2] != r[2].upper()),
                       ("harvest_late.db", lambda r: r[1] == "issue_fix" and r[0] in late)):
        a, b = _rows(db / "harvest.db", "link"), _rows(db / name, "link")
        assert sorted([r for r in a if not gone(r)], key=repr) == b, name
        assert len(a) > len(b)
        for t in ("meta", "body"):
            assert _rows(db / "harvest.db", t) == _rows(db / name, t), (name, t)
        assert dict(_rows(db / name, "meta"))["done"] == "1"


def test_3e_late_resolution_agrees_with_the_reference_split(s2n, s2p, hscratch):
    """the resolution of section 4 against the reference's own split between the primary and the all-reverts
    outcomes, on every repo of both studies: zero disagreements"""
    total = 0
    for s in (s2n, s2p):
        L = _layout(s.decoy / "study", s.decoy / "pool", hscratch / f"val_{s.which}")
        for r in s.repos:
            v = HV.validate_late(HV.prepare(L, r)["late_detail"], s.frozen_outcome(r))
            assert not v["disagreements"], (s.which, r, v["disagreements"])
            total += v["cases"]
    print(f"\n{total} revert-only cases, all agree")
    assert total > 100


def test_3f_merge_time_rule_on_a_synthetic_history(tmp_path):
    """a commit brought in by a merge takes the merge's time: a branch commit made before the cut and merged
    after it is late; one merged before the cut is not (a synthetic repository, this module's code only)"""
    g = tmp_path / "repo"
    g.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@invalid"}

    def git(*a, when=None):
        e = dict(env)
        if when is not None:
            e["GIT_AUTHOR_DATE"] = e["GIT_COMMITTER_DATE"] = f"@{when} +0000"
        return subprocess.run(["git", "-C", str(g), "-c", "gc.auto=0", *a], capture_output=True, text=True,
                              env=e, check=True).stdout.strip()

    git("init", "-q", "-b", "main")
    def commit(msg, when):
        (g / "f.txt").write_text(f"{msg}\n")
        git("add", "f.txt")
        git("commit", "-q", "-m", msg, when=when)
        return git("rev-parse", "HEAD")
    root = commit("root", 100)
    git("checkout", "-q", "-b", "b1")
    b1 = commit("b1", 200)                                 # before the cut, merged before it
    git("checkout", "-q", "main")
    git("merge", "-q", "--no-ff", "-m", "m1", "b1", when=300)
    m1 = git("rev-parse", "HEAD")
    git("checkout", "-q", "-b", "b2")
    b2 = commit("b2", 400)                                 # before the cut, merged after it
    git("checkout", "-q", "main")
    git("merge", "-q", "--no-ff", "-m", "m2", "b2", when=600)
    m2 = git("rev-parse", "HEAD")
    cut = 500
    hist = tmp_path / "history.db"
    con = sqlite3.connect(str(hist))
    con.execute("create table commit_ (sha text primary key, ct integer)")
    con.executemany("insert into commit_ values (?, ?)", [(root, 100), (m1, 300), (m2, 600)])   # first parent
    con.commit()
    con.close()
    hv = tmp_path / "harvest.db"
    con = sqlite3.connect(str(hv))
    con.execute("create table link (sha text, kind text, value text)")
    rows = [("x1", "revert", b1), ("x2", "revert", b2[:9].upper()), ("x3", "revert", root[:7]), ("x4", "revert", m2)]
    con.executemany("insert into link values (?, ?, ?)", rows)
    con.commit()
    con.close()
    rv = HV.resolve_reverts(hv, hist, g, cut)
    r = {s: c["reverts"][0] for s, c in rv["commits"].items()}
    assert r["x1"]["target"] == b1 and r["x1"]["by_merge"] == m1 and not r["x1"]["late"]
    assert r["x2"]["target"] == b2 and r["x2"]["by_merge"] == m2 and r["x2"]["own_time"] == 400 and r["x2"]["late"]
    assert r["x3"]["target"] == root and not r["x3"]["late"]
    assert r["x4"]["target"] == m2 and r["x4"]["by_merge"] is None and r["x4"]["late"]
    assert rv["late"] == ["x2", "x4"]


def test_3g_case_variant_on_the_unedited_decoys(s2n, s2p, hscratch):
    """no lower-case key in either study: the variant deletes no row, every frozen file stands, and the copy
    rebuilt anyway equals the frozen file where the recipe did not edit it"""
    for s in (s2n, s2p):
        L = _layout(s.decoy / "study", s.decoy / "pool", hscratch / f"case_{s.which}")
        for r in s.repos:
            prep = HV.prepare(L, r)
            assert prep["result"]["aprime"]["deleted_rows"] == 0, (s.which, r)
            if s.which == "N" and r in UNPLANTED[:2]:
                assert HV.comparable(HV.build(L, r, prep, "case")) == HV.comparable(s.frozen_outcome(r))


# =================================================================================== 4. the sensitivities
def _shuffled(o: dict, seed: int) -> dict:
    """the same outcome file with every commit list in another order (as another hash seed would give)"""
    rnd = random.Random(seed)
    out = json.loads(json.dumps(o))
    for oc in HV.COMMIT_LISTS:
        items = list(out["outcomes"][oc]["commits"].items())
        rnd.shuffle(items)
        out["outcomes"][oc]["commits"] = dict(items)
    return out


def test_4a_commit_order_and_a_change_in_one_repo(s2n, tmp_path):
    """section 5 test 5 (and review M1, M2): a rebuilt file with one HP commit removed and its lists in another
    order keeps the frozen order for every other commit; two different orders give the same label tables; on
    named streams the variant changes cells of that repo only (its matched control among them), on the shared
    stream R cells of later repos change too"""
    repo = "django"
    fz = s2n.frozen_outcome(repo)
    hp = list(fz["outcomes"]["HP"]["commits"])
    gone = hp[3]
    reb = json.loads(json.dumps(fz))
    del reb["outcomes"]["HP"]["commits"][gone]
    new = HV.reorder(fz, _shuffled(reb, 1))
    assert list(new["outcomes"]["HP"]["commits"]) == [s for s in hp if s != gone]
    for oc in HV.COMMIT_LISTS:
        if oc != "HP":
            assert list(new["outcomes"][oc]["commits"]) == list(fz["outcomes"][oc]["commits"])
    joined = json.loads(json.dumps(reb))
    joined["outcomes"]["control_pool"]["commits"]["f" * 40] = []
    j = HV.reorder(fz, _shuffled(joined, 2))
    assert list(j["outcomes"]["control_pool"]["commits"]) == list(fz["outcomes"]["control_pool"]["commits"]) + ["f" * 40]
    tabs = []
    for seed in (1, 7):
        od, lt = tmp_path / f"o{seed}", tmp_path / f"l{seed}"
        od.mkdir()
        (od / f"{repo}.json").write_text(json.dumps(HV.reorder(fz, _shuffled(reb, seed))) + "\n")
        tabs.append(T.build_label_tables(od, [repo], lt))
    assert tabs[0] == tabs[1]
    lt = tmp_path / "labels"
    shutil.copytree(s2n.tables / "labels", lt)
    shutil.rmtree(lt / repo)
    T.build_label_tables(tmp_path / "o1", [repo], lt)
    data = SCO.load_data(s2n.tables / "phase_b", s2n.tables / "compare", lt, s2n.sealed)
    got = s2n.score("named_django_minus_one", ST.NamedStreams, data=data)
    cc = V.changed_cells(got, _named(s2n))
    assert set(cc["repos"]) == {repo}, cc["repos"].keys()
    assert any(x[0] == "control" for x in cc["repos"][repo])
    shared = s2n.score("shared_django_minus_one", SCO.Scorer, data=data)
    sc = V.changed_cells(shared, _shared(s2n))
    later = [r for r in s2n.repos[s2n.repos.index(repo) + 1:] if r in sc["repos"]]
    print(f"\nnamed: changed only in {repo} ({len(cc['repos'][repo])} cells); shared: also in {later}")
    assert later


def test_4b_floors_from_the_rebuilt_file(s2n):
    marg = copy.deepcopy(s2n.marg)
    fz = s2n.frozen_outcome("django")
    new = json.loads(json.dumps(fz))
    new["outcomes"]["HP"]["clears_floor"] = False
    new["outcomes"]["HP"]["n_commits"] = 19
    V.apply_rebuilt(marg, "django", new)
    row = next(r for r in marg if r["repo"] == "django")
    assert row["HP"]["clears_floor"] is False and row["HP"]["n_commits"] == 19
    assert row["KW"]["clears_floor"] == next(r for r in s2n.marg if r["repo"] == "django")["KW"]["clears_floor"]
    assert [r for r in marg if r["repo"] != "django"] == [r for r in s2n.marg if r["repo"] != "django"]


def _variants(s: Study2, scratch: Path) -> dict:
    named = _named(s)
    keep = s.dir / f"part2-variants-{s.key('variants')}.json"
    nokeep = bool(os.environ.get("COMPARE_PART2_NO_KEEP"))
    results = json.loads(keep.read_text()) if keep.exists() and not nokeep else None
    out = V.run(s.inputs, scratch, s.result, named=named, results=results)
    if results is None and not nokeep:
        keep.write_text(json.dumps(out["results"]) + "\n")
    return out


# observed on the first run of the late variant on both studies (rows deleted in django 2, go 1, racket 1, bun 1,
# ctrl-early2 2; bun's and ctrl-early2's outcome files were edited by the decoy recipe, so the builder does not
# reproduce them and their frozen files stand): a regression value, not an expectation set beforehand
EXPECTED_LATE = {"django", "go", "racket"}


@pytest.mark.parametrize("which", ["N", "P"])
def test_4c_every_variant_is_printed_in_order_without_confirmatory_words(request, which, tmp_path):
    s = request.getfixturevalue("s2n" if which == "N" else "s2p")
    out = _variants(s, tmp_path)
    names = [b["name"] for b in out["blocks"]]
    assert names == [n for n, _h, _t in V.TABLE]
    text = out["text"]
    for n in names:
        assert sum(line.startswith(n + " ") or line.startswith(n + ":") for line in text.splitlines()) == 1, n
    assert text.startswith(V.SENTENCE)
    assert V.vocabulary_ok(text) == [] and V.vocabulary_ok(json.dumps(out["blocks"])) == []
    for b in out["blocks"]:
        if b["status"] == "scored":
            assert len(b["rows"]) == len(V.OUTCOMES) * len(V.PRIMARIES)
            assert all(set(r) == {"outcome", "predictor", "n", "mean", "ci", "word", "difference"} for r in b["rows"])
    unmapped = json.dumps(s.result["tests"])               # the reference's own block: Holm levels and readings
    assert V.vocabulary_ok(unmapped), "the search must find what an unmapped block carries"
    res = out["results"]
    case = V.changed_cells(res["PU_tracker_keys_case_sensitive"], res["PU_named_streams"])
    assert case == {"repos": {}, "study_cells": 0}
    late = V.changed_cells(res["PU_late_revert_ticket_dropped"], res["PU_named_streams"])
    applied = {r for r, v in out["inputs"]["PU_late_revert_ticket_dropped"].items() if v["applied"]}
    assert applied == EXPECTED_LATE
    assert set(late["repos"]) <= applied
    named = V.changed_cells(res["PU_named_streams"], s.result)
    m = CM.cell_map(s.result, res["PU_named_streams"])
    print(f"\nstudy {which}: named streams change cells in {len(named['repos'])} repos "
          f"({named['study_cells']} study cells; {CM.render(m, 0).splitlines()[0]}); late variant changes "
          + ", ".join(f"{r}: {sorted({x[0] for x in v})} ({len(v)})" for r, v in late["repos"].items())
          + f"; {late['study_cells']} study cells")
    assert m["classes"]["W"]["not_equal"] == 0 and m["classes"]["D"]["not_equal"] == 0, CM.render(m)
