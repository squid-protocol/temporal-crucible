"""Tests of the control-repository generator (tools/control_repo/), as listed in docs/process/control_repo_spec.md.

Every generated repository lives under pytest's tmp_path. Every git call here is read-only, runs with
GIT_NO_LAZY_FETCH=1 and gc.auto=0, and names the generated repository explicitly (`git -C`).

Runtime: the two 20-seed statistics tests (5 and 6) build about 100 histories in memory and take most of the
time; see tools/control_repo/DECISIONS.md for the measured total.
"""
from __future__ import annotations

import ast
import io
import json
import os
import re
import statistics
import subprocess
import sys
import tarfile
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GEN_DIR = ROOT / "tools" / "control_repo"
GENERATE = GEN_DIR / "generate.py"
NESTING = ROOT / "tools" / "sa3_nesting.py"
sys.path.insert(0, str(GEN_DIR))
import generate as G  # noqa: E402
import mutations as MM  # noqa: E402

HEX40 = re.compile(r"\b[0-9a-f]{40}\b|\b[0-9a-f]{12}\b")


# ----------------------------------------------------------------------------------------------- helpers
def git(repo, *args, text=True):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(repo), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_NO_LAZY_FETCH": "1", "LC_ALL": "C", "TZ": "UTC"}
    out = subprocess.run(["git", "-c", "gc.auto=0", "-C", str(repo), *args], env=env, check=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out.stdout.decode() if text else out.stdout


def run_cli(out_dir, *args, env_extra=None, cwd=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    subprocess.run([sys.executable, str(GENERATE), "--out", str(out_dir), *args], check=True, env=env,
                   cwd=cwd or str(out_dir.parent), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return json.loads((out_dir / "manifest.json").read_text()), out_dir / "repo"


_CACHE = {}


def generated(tmp_path_factory, *args):
    """Generate once per argument list per session (the repositories are read-only afterwards)."""
    key = tuple(args)
    if key not in _CACHE:
        d = tmp_path_factory.mktemp("ctrl") / "out"
        _CACHE[key] = run_cli(d, "--profile", "small", *args)
    return _CACHE[key]


def tree_texts(repo, commit):
    """{path: text} of every file in the tree of `commit`."""
    listing = git(repo, "ls-tree", "-r", "-z", commit).split("\0")
    paths, shas = [], []
    for item in listing:
        if item:
            meta, path = item.split("\t", 1)
            paths.append(path)
            shas.append(meta.split()[2])
    env = {"PATH": os.environ.get("PATH", ""), "GIT_NO_LAZY_FETCH": "1", "HOME": str(repo)}
    out = subprocess.run(["git", "-c", "gc.auto=0", "-C", str(repo), "cat-file", "--batch"],
                         input="".join(s + "\n" for s in shas).encode(), env=env, check=True,
                         stdout=subprocess.PIPE).stdout
    texts, pos = {}, 0
    for path in paths:
        nl = out.index(b"\n", pos)
        size = int(out[pos:nl].split()[2])
        texts[path] = out[nl + 1:nl + 1 + size].decode("utf-8")
        pos = nl + 1 + size + 1
    return texts


def code_files(m, point):
    """[(file record, path, planted properties)] for every code file present at `point`."""
    out = []
    for f in m["files"]:
        props = (f.get("properties") or {}).get(point)
        path = f.get(f"path_at_{point}")
        if props and path:
            out.append((f, path, props))
    return out


# ------------------------------------------------------------------- independent counts (tests 3 and 8)
PY_BRANCH = {"if", "elif", "for", "while"}
C_BRANCH = re.compile(r"\b(if|for|while|switch)\b")


def py_branch_keywords(text):
    return sum(1 for t in tokenize.generate_tokens(io.StringIO(text).readline)
               if t.type == tokenize.NAME and t.string in PY_BRANCH)


def c_strip(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return re.sub(r'"(\\.|[^"\\])*"', '""', text)


class PyFacts(ast.NodeVisitor):
    """Independent reading of a generated Python file with `ast`: nesting with else-if chains flat (an `elif`
    is an If alone in its parent If's orelse whose line starts with `elif`; `else:` + an indented `if` is real
    nesting), assignments to `_STATE[...]` inside an if-arm at any depth, and calls to names imported from
    other files."""
    CONTROL = (ast.If, ast.For, ast.While, ast.Try, ast.Match)

    def __init__(self, tree, text):
        self.lines = text.split("\n")
        self.imported = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                         for a in n.names}
        self.max_depth = 0
        self.state_in_if = 0
        self.calls_out = 0
        self.callees = []
        self._walk(tree.body, 0, False)

    def _walk(self, body, depth, in_if):
        for node in body:
            self._node(node, depth, in_if)

    def _node(self, node, depth, in_if, chain=False):
        if isinstance(node, self.CONTROL):
            d = depth if chain else depth + 1
            self.max_depth = max(self.max_depth, d)
            if isinstance(node, ast.If):
                self._scan_expr(node.test)
                self._walk(node.body, d, True)
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If) \
                        and self.lines[node.orelse[0].lineno - 1].lstrip().startswith("elif "):
                    self._node(node.orelse[0], d, in_if, chain=True)   # elif: same depth as its head
                else:
                    self._walk(node.orelse, d, True)
            elif isinstance(node, ast.Try):
                self._walk(node.body, d, in_if)
                for h in node.handlers:
                    self._walk(h.body, d, in_if)
                self._walk(node.orelse, d, in_if)
                self._walk(node.finalbody, d, in_if)
            else:
                self._walk(node.body, d, in_if)
                self._walk(node.orelse, d, in_if)
            return
        if isinstance(node, ast.FunctionDef):
            self._walk(node.body, depth, in_if)
            return
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == "_STATE" \
                        and in_if:
                    self.state_in_if += 1
        self._scan_expr(node)

    def _scan_expr(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in self.imported:
                self.calls_out += 1
                self.callees.append(n.func.id)


# ------------------------------------------------------------------------------------- test 1: hashes
def test_same_arguments_same_hashes_different_seed_different(tmp_path):
    args = ["--seed", "11", "--profile", "small", "--mutation", "merge_workflow"]
    m1, r1 = run_cli(tmp_path / "a", *args, env_extra={"PYTHONHASHSEED": "1", "TZ": "America/Detroit"})
    m2, r2 = run_cli(tmp_path / "b", *args, env_extra={"PYTHONHASHSEED": "2", "TZ": "Asia/Tokyo",
                                                         "GIT_AUTHOR_NAME": "Someone Else"},
                     cwd=str(tmp_path))
    h1 = [c["hash"] for c in m1["realised"]]
    h2 = [c["hash"] for c in m2["realised"]]
    assert h1 == h2
    assert git(r1, "rev-list", "--all") == git(r2, "rev-list", "--all")
    assert (tmp_path / "a" / "manifest.json").read_bytes() == (tmp_path / "b" / "manifest.json").read_bytes()
    m3, _ = run_cli(tmp_path / "c", "--seed", "12", "--profile", "small", "--mutation", "merge_workflow")
    h3 = [c["hash"] for c in m3["realised"]]
    assert not set(h1) & set(h3)


def test_effects_leave_history_to_the_snapshot_unchanged(tmp_path_factory):
    """The negative-control mechanism, checked end to end: an effect acts only on fixes after the snapshot,
    so every commit up to and including the snapshot is byte-identical with and without it."""
    m0, _ = generated(tmp_path_factory, "--seed", "5")
    m1, _ = generated(tmp_path_factory, "--seed", "5", "--effect", "branches=1.0", "--effect", "calls_in=-0.5")
    assert m0["points"] == m1["points"]
    cut = [r["hash"] for r in m0["realised"]].index(m0["points"]["snapshot"]["hash"])
    assert [r["hash"] for r in m0["realised"][:cut + 1]] == [r["hash"] for r in m1["realised"][:cut + 1]]
    assert m1["constants"]["beta"]["branches"] == 1.0 and m1["constants"]["beta"]["calls_in"] == -0.5
    assert m0["constants"]["beta"] == {k: 0.0 for k in m0["constants"]["beta"]}
    for k in ("a", "b"):
        assert isinstance(m0["constants"][k], float)


# ------------------------------------------------------------------------------------ test 2: validity
@pytest.mark.parametrize("args", [(), ("--language", "c"), ("--mutation", "merge_workflow"),
                                  ("--mutation", "squash_merges"), ("--mutation", "huge_import_merge")])
def test_repository_is_valid(tmp_path_factory, args):
    m, repo = generated(tmp_path_factory, "--seed", "3", *args)
    fsck = subprocess.run(["git", "-c", "gc.auto=0", "-C", str(repo), "fsck", "--full", "--strict"],
                          env={"PATH": os.environ["PATH"], "GIT_NO_LAZY_FETCH": "1", "HOME": str(repo)},
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert fsck.returncode == 0 and not fsck.stdout.strip(), fsck.stdout.decode()
    assert not (repo / ".git" / "shallow").exists()
    assert git(repo, "rev-parse", "--is-bare-repository").strip() == "false"
    assert git(repo, "status", "--porcelain") == ""
    every = set(git(repo, "rev-list", "--all").split())
    realised = {r["hash"] for r in m["realised"]}
    assert realised == every
    for c in m["commits"]:
        assert c["hash"] in every
    for lab in m["expected_labels"]:
        assert lab["hash"] in every
    raw = subprocess.run(["git", "-c", "gc.auto=0", "-C", str(repo), "cat-file", "--batch"],
                         input="".join(r["hash"] + "\n" for r in m["realised"]).encode(), check=True,
                         env={"PATH": os.environ["PATH"], "GIT_NO_LAZY_FETCH": "1", "HOME": str(repo)},
                         stdout=subprocess.PIPE).stdout
    pos = 0
    by_lid = {c["id"]: c for c in m["commits"]}
    for r in m["realised"]:                           # messages, authors and dates are what the manifest says
        nl = raw.index(b"\n", pos)
        size = int(raw[pos:nl].split()[2])
        head, _, msg = raw[nl + 1:nl + 1 + size].decode().partition("\n\n")
        pos = nl + 1 + size + 1
        assert msg == r["message"]
        assert f"author {r['author']} {r['time']} +0000" in head
        if r["kind"] in ("direct", "side"):
            assert by_lid[r["lids"][0]]["message"] == msg
    first_parent = git(repo, "rev-list", "--first-parent", "main").split()
    for point in ("snapshot", "prior"):
        h = m["points"][point]["hash"]
        assert h in first_parent
        paths = set(git(repo, "ls-tree", "-r", "--name-only", h).split("\n")) - {""}
        listed = {f[f"path_at_{point}"] for f in m["files"] if f[f"path_at_{point}"]}
        assert listed == paths, (point, listed ^ paths)
    snap_t, prior_t = m["points"]["snapshot"]["time"], m["points"]["prior"]["time"]
    assert prior_t <= snap_t - 365 * 86400
    fp_times = [int(t) for t in git(repo, "log", "--first-parent", "--format=%ct", "main").split()]
    assert not [t for t in fp_times if prior_t < t <= snap_t - 365 * 86400], "prior point is not the last one"
    base = [c["id"] for c in m["commits"] if c["id"].startswith("L")]     # the timeline before mutations
    assert base.index(m["points"]["snapshot"]["commit"]) == -(-8 * len(base) // 10) - 1   # ceil(0.8 n) - 1


def test_layout_attributes_and_unit_reasons(tmp_path_factory):
    m, repo = generated(tmp_path_factory, "--seed", "3")
    snap = m["points"]["snapshot"]["hash"]
    attrs = git(repo, "show", f"{snap}:.gitattributes")
    assert "vendor/thirdparty/** linguist-vendored" in attrs
    xign = re.search(r"^(\S+)/\*\* export-ignore$", attrs, re.M).group(1)
    tar = tarfile.open(fileobj=io.BytesIO(git(repo, "archive", "--format=tar", snap, text=False)))
    archived = {n for n in tar.getnames() if not n.endswith("/")}
    kinds = {}
    for f in m["files"]:
        p = f["path_at_snapshot"]
        if not p:
            continue
        kinds.setdefault(f["kind"], []).append(f)
        assert f["unit_reason"]
        assert f["is_unit"] == (f["kind"] == "unit")
        assert (p in archived) == (not p.startswith(xign + "/")), p
        if f["kind"] == "vendor":
            assert p.startswith("vendor/thirdparty/")
        if f["kind"] == "test":
            assert p.startswith("tests/")
        if f["kind"] == "docs":
            assert p.startswith("docs/")
        if f["kind"] == "unit":
            assert p.startswith("src/") and 3 <= p.count("/") <= 4
    for k in ("unit", "test", "vendor", "docs", "generated", "licence", "attributes", "export_ignored"):
        assert k in kinds, k
    gen = kinds["generated"][0]["path_at_snapshot"]
    assert "generated by" in git(repo, "show", f"{snap}:{gen}").split("\n")[0]
    sizes = sorted(f["properties"]["snapshot"]["loc"] for f in kinds["unit"])
    assert sizes[len(sizes) // 2] < sum(sizes) / len(sizes)          # right-skewed
    assert len(sizes) > len(set(sizes))                              # exact ties
    py = m["risk_operations"]
    assert "not planted" in py


# ------------------------------------------------------------------- test 3: planted structure is real
@pytest.mark.parametrize("language", ["python", "c"])
def test_planted_counts_equal_the_text(tmp_path_factory, language):
    m, repo = generated(tmp_path_factory, "--seed", "3", "--language", language)
    for point in ("snapshot", "prior"):
        texts = tree_texts(repo, m["points"][point]["hash"])
        calls_in = {}
        by_func = {}
        checked = 0
        for f, path, props in code_files(m, point):
            text = texts[path]
            assert props["loc"] == text.count("\n") == len(text.splitlines()), path
            if language == "python":
                assert props["branches"] == py_branch_keywords(text), path
                tree = ast.parse(text)
                facts = PyFacts(tree, text)
                assert props["max_nesting"] == facts.max_depth, path
                assert props["state_writes_in_branches"] == facts.state_in_if, path
                assert props["calls_out"] == facts.calls_out, path
                for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
                    by_func[fn.name] = f["id"]
                for callee in facts.callees:
                    calls_in[callee] = calls_in.get(callee, 0) + 1
                assert "pointer_ops" not in props
            else:
                body = c_strip(text)
                assert props["branches"] == len(C_BRANCH.findall(body)), path
                assert props["pointer_ops"] == len(re.findall(r"^\s*\*cursor = ", body, re.M)), path
                assert props["alloc_ops"] == len(re.findall(r"\b(malloc|free)\(", body)), path
                assert props["pointer_declarations"] == len(re.findall(r"\blong \*\w+", body)), path
                assert props["max_nesting"] >= (1 if props["branches"] else 0)
                externs = set(re.findall(r"^extern long (\w+)\(", body, re.M))
                calls = [c for c in re.findall(r"\b(\w+)\(data, ", body) if c in externs]
                assert props["calls_out"] == len(calls), path
                for name in re.findall(r"^long (\w+)\(long \*data, long n\) \{$", body, re.M):
                    by_func[name] = f["id"]
                for callee in calls:
                    calls_in[callee] = calls_in.get(callee, 0) + 1
            checked += 1
        got = {}                                     # calls_in: call sites elsewhere into this file's functions
        for name, n in calls_in.items():
            got[by_func[name]] = got.get(by_func[name], 0) + n
        for f, path, props in code_files(m, point):
            assert props["calls_in"] == got.get(f["id"], 0), path
        assert checked >= 40
        # densities are the counts over loc
        for f, path, props in code_files(m, point):
            if f["is_unit"]:
                assert props["density"]["branches"] == pytest.approx(props["branches"] / props["loc"])


def test_c_files_compile(tmp_path_factory, tmp_path):
    """Beyond the spec: the generated C is not only parseable but valid C11 (gcc -fsyntax-only)."""
    import shutil
    gcc = shutil.which("gcc") or shutil.which("cc")
    if gcc is None:
        pytest.skip("no C compiler on PATH (the C text is still checked by tests 3 and 4)")
    m, repo = generated(tmp_path_factory, "--seed", "3", "--language", "c")
    texts = tree_texts(repo, m["points"]["snapshot"]["hash"])
    n = 0
    for f, path, _p in code_files(m, "snapshot"):
        if path.endswith(".c"):
            local = tmp_path / path.replace("/", "_")
            local.write_text(texts[path])
            res = subprocess.run([gcc, "-std=c11", "-fsyntax-only", "-Werror=implicit-function-declaration",
                                  str(local)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert res.returncode == 0, (path, res.stdout.decode())
            n += 1
    assert n >= 40


# --------------------------------------------------------------------------------- test 4: sa3_nesting
def _tree_sitter_python():
    """An interpreter that imports tree_sitter_language_pack at the version sa3_nesting.py pins."""
    pin = re.search(r'PACK_VERSION = "([^"]+)"', NESTING.read_text()).group(1)
    cands = [os.environ.get("CONTROL_REPO_TS_PYTHON"), sys.executable]
    for c in [c for c in cands if c]:
        try:
            v = subprocess.run([c, "-c", "import importlib.metadata as m, tree_sitter_language_pack;"
                                         "print(m.version('tree_sitter_language_pack'))"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60).stdout.decode().strip()
        except (OSError, subprocess.TimeoutExpired):
            continue
        if v == pin:
            return c, pin
    return None, pin


NEST_RUNNER = """
import json, sys
sys.path.insert(0, sys.argv[1])
import sa3_nesting as N
out = {}
for path, lang in json.load(sys.stdin):
    g = N.grammar_for(lang, path)
    r = N.nesting(open(path, "rb").read(), g)
    out[path] = [r["nest_max"], r["parse_error"], g]
print(json.dumps(out))
"""


@pytest.mark.parametrize("args", [("--language", "python"), ("--language", "c"),
                                  ("--mutation", "mixed_language")])
def test_sa3_nesting_agrees_with_max_nesting(tmp_path_factory, tmp_path, args):
    py, pin = _tree_sitter_python()
    if py is None:
        pytest.skip(f"no interpreter with tree_sitter_language_pack=={pin} (the version tools/sa3_nesting.py "
                    f"pins); set CONTROL_REPO_TS_PYTHON to one")
    m, repo = generated(tmp_path_factory, "--seed", "3", *args)
    jobs, want = [], {}
    for point in ("snapshot", "prior"):
        texts = tree_texts(repo, m["points"][point]["hash"])
        for f, path, props in code_files(m, point):
            local = tmp_path / point / path
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text(texts[path])
            jobs.append([str(local), f["language"]])
            want[str(local)] = props["max_nesting"]
    res = subprocess.run([py, "-B", "-c", NEST_RUNNER, str(NESTING.parent)], input=json.dumps(jobs).encode(),
                         stdout=subprocess.PIPE, check=True)
    got = json.loads(res.stdout)
    assert len(got) == len(want) > 80
    bad = {p: (got[p], want[p]) for p in want if got[p][0] != want[p] or got[p][1]}
    assert not bad, list(bad.items())[:5]
    assert max(want.values()) >= 3                   # the check reached nested code, not only flat files


# ----------------------------------------------------------------------------- tests 5 and 6: the truth
STAT_FILES = 800          # see DECISIONS.md: 60 files cannot resolve +-0.03 (its sampling SE is about 0.05)
STAT_WORKERS = 2          # the machine is shared: at most two processes
SEEDS = range(1, 21)


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def _spearman(a, b):
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    da = sum((x - ma) ** 2 for x in ra)
    db = sum((y - mb) ** 2 for y in rb)
    if da == 0 or db == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (da * db) ** 0.5


def within_decile_rank_correlation(rows, prop):
    """Mean over the ten equal-count size deciles (by loc at the snapshot, ties by id) of Spearman's rho
    between the property's density at the snapshot and the file's number of true fixes after it. A decile in
    which either side is constant has no rho and is left out."""
    rows = sorted(rows, key=lambda r: (r["loc"], r["id"]))
    n, vals = len(rows), []
    for d in range(10):
        g = rows[d * n // 10:(d + 1) * n // 10]
        rho = _spearman([r["density"][prop] for r in g], [r["fixes"] for r in g])
        if rho is not None:
            vals.append(rho)
    return sum(vals) / len(vals)


def truth_rows(plan):
    """Per unit file at the snapshot: loc, densities at the snapshot (plus d_branches = the change in branch
    density since the prior point, 0 if absent then), and the number of true fixes after the snapshot."""
    snap, prior = plan.points["snapshot"], plan.points["prior"]
    snap_t = next(e.time for e in plan.entries if e.lid == plan.snap_lid)
    fixes = {}
    for e in plan.entries:
        if e.type == "fix" and e.time > snap_t:
            for f in e.notes["defect_files"]:
                fixes[f] = fixes.get(f, 0) + 1
    rows = []
    for fid, p in snap.items():
        if plan.files[fid].is_unit:
            d = dict(p["density"])
            d["d_branches"] = d["branches"] - prior[fid]["density"]["branches"] if fid in prior else 0.0
            rows.append({"id": fid, "loc": p["loc"], "density": d, "fixes": fixes.get(fid, 0)})
    return rows


def _one_seed(job):
    seed, language, effects, props = job
    cfg = G.make_config(seed, language=language, files=STAT_FILES, profile="small", effects=effects)
    plan, _units = G.build_plan(cfg)
    rows = truth_rows(plan)
    return {k: within_decile_rank_correlation(rows, k) for k in props}


def _statistic(language, effects, props):
    """Per property, the statistic for each of the 20 seeds (two worker processes, results in seed order)."""
    import concurrent.futures
    import multiprocessing
    jobs = [(seed, language, effects, props) for seed in SEEDS]
    with concurrent.futures.ProcessPoolExecutor(STAT_WORKERS, mp_context=multiprocessing.get_context("fork")) as ex:
        results = list(ex.map(_one_seed, jobs))
    return {k: [r[k] for r in results] for k in props}


def test_truth_rows_match_the_manifest(tmp_path_factory):
    """Tests 5 and 6 read the truth from the in-memory plan (no git, for speed); it is the manifest's truth."""
    seed = 3
    m, _ = generated(tmp_path_factory, "--seed", str(seed))
    plan, _ = G.build_plan(G.make_config(seed, profile="small"))
    rows = {r["id"]: r for r in truth_rows(plan)}
    units = [f for f in m["files"] if f["is_unit"] and f["properties"]["snapshot"]]
    assert {f["id"] for f in units} == set(rows)
    for f in units:
        assert f["true_fixes_after_snapshot"] == rows[f["id"]]["fixes"]
        assert f["properties"]["snapshot"]["loc"] == rows[f["id"]]["loc"]
    assert sum(r["fixes"] for r in rows.values()) > 0


@pytest.mark.parametrize("language", ["python", "c"])
def test_negative_control_is_null_in_the_truth(language):
    props = ["branches", "max_nesting", "calls_in", "calls_out", "state_writes_in_branches", "d_branches"]
    if language == "c":
        props += ["pointer_ops", "alloc_ops"]
    per = _statistic(language, {}, props)
    summary = {k: (statistics.mean(v), statistics.stdev(v) / len(v) ** 0.5) for k, v in per.items()}
    print(language, {k: (round(m, 4), round(se, 4)) for k, (m, se) in summary.items()})
    for k, (mean, se) in summary.items():          # spec [r2]: within 3 of its own SEs and within +-0.03
        assert abs(mean) <= 3 * se and abs(mean) <= 0.03, (k, mean, se)


def test_positive_control_is_real_and_grows_with_beta():
    means = {}
    for beta in (0.25, 0.5, 1.0):
        per = _statistic("python", {"branches": beta}, ["branches"])["branches"]
        sd = statistics.stdev(per)
        means[beta] = statistics.mean(per)
        assert means[beta] / (sd / len(per) ** 0.5) > 4, (beta, means[beta], sd)   # clearly positive
    print(means)
    assert means[0.25] > 0.03
    assert means[0.25] < means[0.5] < means[1.0]


# ----------------------------------------------------------------------------------- test 7: mutations
def _norm_commit(c):
    out = {k: v for k, v in c.items() if k not in ("hash",)}
    out["message"] = HEX40.sub("<H>", c["message"])
    if "revert_target" in out:
        out["revert_target"] = {k: v for k, v in out["revert_target"].items() if k != "hash"}
    return out


def _diff(base, mut):
    """(files added, files removed, files changed {id: [fields]}, commits added, removed, changed)."""
    bf, mf_ = {f["id"]: f for f in base["files"]}, {f["id"]: f for f in mut["files"]}
    bc = {c["id"]: _norm_commit(c) for c in base["commits"]}
    mc = {c["id"]: _norm_commit(c) for c in mut["commits"]}
    fchg = {i: sorted(k for k in set(bf[i]) | set(mf_[i]) if bf[i].get(k) != mf_[i].get(k))
            for i in bf.keys() & mf_.keys()}
    cchg = {i: sorted(k for k in set(bc[i]) | set(mc[i]) if bc[i].get(k) != mc[i].get(k))
            for i in bc.keys() & mc.keys()}
    return (sorted(mf_.keys() - bf.keys()), sorted(bf.keys() - mf_.keys()), {i: v for i, v in fchg.items() if v},
            sorted(mc.keys() - bc.keys()), sorted(bc.keys() - mc.keys()), {i: v for i, v in cchg.items() if v})


def _truth(m):
    return {f["id"]: (f.get("true_fixes_after_snapshot"), f["properties"]) for f in m["files"] if f["is_unit"]}


ALL_MUTATIONS = list(MM.REGISTRY)


@pytest.mark.parametrize("name", ALL_MUTATIONS)
def test_mutation_changes_what_it_says_and_nothing_else(tmp_path_factory, name):
    base, _ = generated(tmp_path_factory, "--seed", "4")
    mut, repo = generated(tmp_path_factory, "--seed", "4", "--mutation", name)
    assert mut["mutations"]["requested"] == [name]
    assert name in mut["mutations"]["applied"] and name in mut["mutations"]["changed"]
    f_add, f_rm, f_chg, c_add, c_rm, c_chg = _diff(base, mut)
    assert not f_rm and not c_rm
    base_commits = {c["id"]: c for c in base["commits"]}
    mut_commits = {c["id"]: c for c in mut["commits"]}
    if name not in ("renames_after_snapshot",):
        assert _truth(base) == _truth(mut)             # planted properties and true fixes: unchanged
    # spec [r2]: which unit files each commit touches is unchanged, for every commit both histories have
    units = {f["id"] for f in mut["files"] if f["is_unit"]}
    snap_t = base["points"]["snapshot"]["time"]
    for i, c in mut_commits.items():
        if name == "reverts_of_new_code" and c["type"] == "revert" and c["time"] > snap_t:
            continue                                  # retargeting these reverts is the mutation
        if i in base_commits:
            assert set(c["file_ids"]) & units == set(base_commits[i]["file_ids"]) & units, i
            assert c["caller_edit_ids"] == base_commits[i]["caller_edit_ids"], i
    if name in ("merge_workflow", "bot_merges", "squash_merges"):
        assert not f_add and not f_chg and not c_add and not c_chg
        kinds = {r["kind"] for r in mut["realised"]}
        assert ("merge" in kinds and "side" in kinds) if name != "squash_merges" else ("squash" in kinds)
        merges = [r for r in mut["realised"] if r["kind"] == "merge"]
        if name == "bot_merges":
            assert merges and all("[bot]" in r["author"] for r in merges)
            assert "merge_workflow" in mut["mutations"]["implied"]
            # against merge_workflow itself: only the merges' authors (and so the hashes) differ
            mw, _ = generated(tmp_path_factory, "--seed", "4", "--mutation", "merge_workflow")

            def strip(r):
                return {k: (HEX40.sub("<H>", v) if isinstance(v, str) else v) for k, v in r.items()
                        if k not in ("hash", "parents", "merge", "author", "commits")}
            assert len(mw["realised"]) == len(mut["realised"])
            for a, b in zip(mw["realised"], mut["realised"]):
                assert strip(a) == strip(b)
                assert a["author"] == b["author"] or (a["kind"] == b["kind"] == "merge")
            assert [strip(x) for x in mw["expected_labels"]] == [strip(x) for x in mut["expected_labels"]]
            assert len(mw["ambiguous"]) == len(mut["ambiguous"])
        if name == "merge_workflow":
            assert merges and not any("[bot]" in r["author"] for r in merges)
            for r in merges:                         # the reference is in the brought-in commit, not the merge
                assert not re.search(r"#\d|CVE-|PROJ-|Fixes:", r["message"])
        if name == "squash_merges":                  # references kept in the squash message
            for r in mut["realised"]:
                for lid in r["lids"]:
                    for ref in re.findall(r"#\d+|CVE-\d+-\d+|PROJ-\d+", mut_commits[lid]["message"]):
                        assert ref in r["message"]
    elif name == "sweep_labelled_fix":
        assert not f_add and not f_chg and not c_add
        (lid, fields), = c_chg.items()
        assert base_commits[lid]["type"] == "sweep" and base_commits[lid]["notes"]["sweep_kind"] == "licence"
        assert set(fields) <= {"message", "convention"}
        assert re.match(r"Fix .*#\d+", mut_commits[lid]["message"])
    elif name == "tickets_for_everything":
        assert not f_add and not f_chg and not c_add
        converted = [i for i, c in mut_commits.items() if c.get("notes", {}).get("mutated_from") == "ordinary"]
        n_ord = sum(1 for c in base["commits"] if c["type"] == "ordinary")
        assert abs(len(converted) / n_ord - 0.6) < 0.1
        for i, fields in c_chg.items():
            if i in converted:
                assert base_commits[i]["type"] == "ordinary" and mut_commits[i]["type"] == "feature_with_ticket"
                assert set(fields) <= {"type", "convention", "message", "notes"}
            else:                                    # a revert or a Fixes: trailer quoting a converted subject
                assert set(fields) == {"message"}, (i, fields)
                assert mut_commits[i]["type"] in ("revert", "fix")
    elif name == "reverts_of_new_code":
        assert not f_add and not f_chg and not c_add
        snap_t = mut["points"]["snapshot"]["time"]
        post = [c for c in mut["commits"] if c["type"] == "revert" and c["time"] > snap_t]
        assert post
        noted = mut["mutations"]["notes"].get("reverts_of_new_code", [])
        for c in post:
            if not any(n.startswith(c["id"] + ":") for n in noted):
                assert not c["revert_target"]["before_snapshot"]
        for i in c_chg:
            assert mut_commits[i]["type"] == "revert" and mut_commits[i]["time"] > snap_t
    elif name in ("vendored_half", "test_fixtures", "mixed_language"):
        assert f_add and not f_chg and not c_add
        assert set(c_chg) <= {"L00000"} and set(c_chg.get("L00000", [])) <= {"files", "file_ids"}
        added = [f for f in mut["files"] if f["id"] in f_add]
        assert all(not f["is_unit"] for f in added)
        kind = {"vendored_half": "vendored_contrib", "test_fixtures": "fixture",
                "mixed_language": "other_language"}[name]
        assert {f["kind"] for f in added} == {kind}
        n_unitlike = sum(1 for f in mut["files"] if f["kind"] == "unit" and f["created"] == "L00000")
        if name == "vendored_half":
            assert len(added) == n_unitlike           # half of all unit-looking files are imported code
        if name == "test_fixtures":
            assert len(added) > n_unitlike and all(f["path_at_snapshot"].startswith("tests/") for f in added)
        if name == "mixed_language":
            at_start = [f for f in mut["files"] if f["created"] == "L00000"]
            share = len(added) / len(at_start)
            assert 0.38 <= share <= 0.42
            assert {f["language"] for f in added} == {"c"}
    elif name == "renames_after_snapshot":
        assert not f_add and c_add
        assert all(mut_commits[i]["type"] == "rename" for i in c_add)
        renamed_by = [mut_commits[i]["file_ids"] for i in c_add]
        assert all(len(ids) == 1 for ids in renamed_by)          # the inserted renames edit no other file
        assert all(not mut_commits[i]["caller_edit_ids"] for i in c_add)
        snap_t = mut["points"]["snapshot"]["time"]
        assert all(mut_commits[i]["time"] > snap_t for i in c_add)
        renamed = set(mut["mutations"]["notes"]["renamed_after_snapshot"])
        n_units = sum(1 for f in base["files"] if f["is_unit"] and f["path_at_snapshot"])
        assert abs(len(renamed) / n_units - 0.2) <= 0.05
        assert renamed == {ids[0] for ids in renamed_by}
        for i, fields in f_chg.items():
            assert set(fields) <= {"path_final", "path_history", "stale_imports"}, (i, fields)
        assert renamed <= set(f_chg)
        stale = {callee for f in mut["files"] for callee in f.get("stale_imports", {})}
        if mut["arguments"]["language"] == "python":
            assert stale and stale <= renamed                    # callers' imports of a moved file go stale
        for i, fields in c_chg.items():               # later commits name the new paths
            assert set(fields) <= {"files", "unit_files", "message"}, (i, fields)
            if "message" in fields:
                assert mut_commits[i]["type"] in ("delete", "rename")
        for f in mut["files"]:                        # truth and the snapshot itself are untouched
            bf = next(x for x in base["files"] if x["id"] == f["id"])
            assert f["properties"] == bf["properties"] and f.get("true_fixes_after_snapshot") == \
                bf.get("true_fixes_after_snapshot") and f["path_at_snapshot"] == bf["path_at_snapshot"]
    elif name == "no_references":
        assert not f_add and not f_chg and not c_add
        for i, fields in c_chg.items():
            assert mut_commits[i]["type"] == "fix" and set(fields) <= {"message", "convention", "notes"}
            if "notes" in fields:                     # only the trailer's target goes with the trailer
                bn, mn = base_commits[i]["notes"], mut_commits[i]["notes"]
                assert set(bn) - set(mn) == {"fixes_trailer_target"} and not set(mn) - set(bn)
        assert {c["convention"] for c in mut["commits"] if c["type"] == "fix"} == {"keyword"}
    elif name == "huge_import_merge":
        assert not f_chg and not c_chg
        assert all(mut_commits[i]["type"] == "add" for i in c_add)
        huge = [r for r in mut["realised"] if r.get("huge")]
        assert len(huge) == 1 and len(huge[0]["brought"]) == 500
        lab = next(x for x in mut["expected_labels"] if x["hash"] == huge[0]["hash"])
        assert lab["counted"] is False and "over the cap" in lab["clause"]
    else:
        raise AssertionError(f"no check written for mutation {name}")
    assert mut["points"]["snapshot"]["commit"] == base["points"]["snapshot"]["commit"]


def test_mutations_compose(tmp_path_factory):
    names = ["bot_merges", "renames_after_snapshot", "vendored_half", "no_references", "reverts_of_new_code"]
    args = []
    for n in names:
        args += ["--mutation", n]
    m, repo = generated(tmp_path_factory, "--seed", "6", *args)
    assert set(m["mutations"]["applied"]) == set(names) | {"merge_workflow"}
    assert set(m["mutations"]["changed"]) >= set(names)
    with pytest.raises(subprocess.CalledProcessError):
        run_cli(tmp_path_factory.mktemp("bad") / "o", "--seed", "1", "--profile", "small",
                "--mutation", "squash_merges", "--mutation", "merge_workflow")


def test_list_mutations():
    out = subprocess.run([sys.executable, str(GENERATE), "--list-mutations"], stdout=subprocess.PIPE,
                         check=True).stdout.decode()
    for name, d in MM.REGISTRY.items():
        assert name in out
        assert d["log"]
    assert len(MM.REGISTRY) == 12


# ------------------------------------------------------------------------------- test 8: commit types
@pytest.mark.parametrize("args", [(), ("--mutation", "tickets_for_everything"), ("--language", "c")])
def test_sweeps_are_wide_and_ticket_features_fix_nothing(tmp_path_factory, args):
    m, _ = generated(tmp_path_factory, "--seed", "3", *args)
    order = {c["id"]: i for i, c in enumerate(m["commits"])}
    units = [f for f in m["files"] if f["is_unit"]]
    sweeps = [c for c in m["commits"] if c["type"] == "sweep"]
    assert len(sweeps) >= 3
    for c in sweeps:
        i = order[c["id"]]
        alive = [f for f in units if order[f["created"]] < i and (f["deleted"] is None or order[f["deleted"]] > i)]
        touched = set(c["file_ids"]) & {f["id"] for f in alive}
        assert len(touched) >= len(alive) / 2, (c["id"], len(touched), len(alive))
    assert any(c["message"].startswith("Fix") for c in sweeps) and any(
        not c["message"].startswith("Fix") for c in sweeps)
    feats = [c for c in m["commits"] if c["type"] == "feature_with_ticket"]
    assert feats
    for c in feats:
        assert "defect" not in c and re.match(r"Fixed #\d+ -- Added ", c["message"])
    defects = [c["defect"] for c in m["commits"] if c["type"] == "fix"]
    assert len(defects) == len(set(defects))
    for c in m["commits"]:
        if c["type"] == "ordinary":
            assert 1 <= len(c["file_ids"]) <= 10
        if c["type"] == "bot":
            assert "[bot]" in c["author"]
        if c["type"] == "revert":
            assert "This reverts commit " in c["message"] and "revert_target" in c
    conv = {c["convention"] for c in m["commits"] if c["type"] == "fix"}
    assert conv == {"issue", "trailer", "cve", "jira", "keyword", "silent"}


# -------------------------------------------------------------------------- the change effect ([r2])
@pytest.mark.parametrize("language", ["python", "c"])
def test_at_least_40_percent_change_in_the_prior_year(tmp_path_factory, language):
    m, _ = generated(tmp_path_factory, "--seed", "3", "--language", language)
    both = [f for f in m["files"] if f["is_unit"] and f["properties"]["snapshot"] and f["properties"]["prior"]]
    moved = [f for f in both if f["properties"]["snapshot"]["branches"] != f["properties"]["prior"]["branches"]]
    rec = m["change_in_prior_year"]
    assert rec["unit_files_at_both_points"] == len(both) and rec["branch_density_changed"] == len(moved)
    assert rec["share"] >= 0.40, rec
    up = sum(1 for f in moved if f["properties"]["snapshot"]["branches"] > f["properties"]["prior"]["branches"])
    assert rec["up"] == up and 0 < up < len(moved)
    for f in moved:                    # a change never moves nesting or state writes (calls move only by deletes)
        a, b = f["properties"]["snapshot"], f["properties"]["prior"]
        for k in ("max_nesting", "state_writes_in_branches"):
            assert a[k] == b[k], (f["id"], k)


# -------------------------------------------------------------------------------- expected labels
def test_expected_labels_follow_the_written_rule(tmp_path_factory):
    m, _ = generated(tmp_path_factory, "--seed", "3")
    by_id = {c["id"]: c for c in m["commits"]}
    snap_path = {f["id"]: f["path_at_snapshot"] for f in m["files"] if f["is_unit"] and f["path_at_snapshot"]}
    labs = m["expected_labels"]
    snap_t = m["points"]["snapshot"]["time"]
    assert {lab["hash"] for lab in labs} == {c["hash"] for c in m["realised"] if c["time"] > snap_t}
    for lab in labs:
        assert lab["clause"]
        (lid,) = lab["commits"]
        c = by_id[lid]
        if "Tree-wide" in lab["clause"]:
            assert lab["counted"] is False
            continue
        if c["type"] == "fix":
            assert lab["counted"] == (c["convention"] in ("issue", "trailer", "cve", "jira")), (lid, lab)
        if c["type"] == "feature_with_ticket":
            assert lab["counted"] is True and "fix reference" in lab["clause"]
        if c["type"] == "revert":
            if c["revert_target"]["before_snapshot"]:
                assert lab["counted"] is True
            elif "#" in c["message"]:                  # a late revert quoting a ticket: listed, not decided
                assert lab["counted"] is None
                (case,) = [a for a in m["ambiguous"] if a["hash"] == lab["hash"]]
                assert {r["reading"]: r["counted"] for r in case["readings"]} == {
                    "reference_counts": True, "nonqualifying_revert": False}
            else:
                assert lab["counted"] is False and "after the cut" in lab["clause"]
        if c["type"] in ("ordinary", "bot", "add", "delete", "rename", "vendor_import"):
            assert lab["counted"] is False
        if lab["counted"]:                            # positives may be empty only if it touched no snapshot unit
            assert lab["positives"] or not set(c["file_ids"]) & set(snap_path)
        for p in lab["positives"]:                    # spec [r2]: snapshot unit files, by snapshot path
            assert snap_path[p["id"]] == p["path_at_snapshot"]
        for t in lab["touched_unit_files_not_at_snapshot"]:
            assert t["id"] not in snap_path and t["id"] in set(c["file_ids"])
        assert {p["id"] for p in lab["positives"]} <= set(c["file_ids"])
    for case in m["ambiguous"]:                       # in a direct history only the revert case is open
        assert all(by_id[x]["type"] == "revert" for x in case["commits"])


def test_merge_labels_list_every_reading(tmp_path_factory):
    m, _ = generated(tmp_path_factory, "--seed", "3", "--mutation", "merge_workflow")
    labs = {lab["hash"]: lab for lab in m["expected_labels"]}
    by_id = {c["id"]: c for c in m["commits"]}
    linked = ("issue", "trailer", "cve", "jira", "ticket_feature")
    assert m["ambiguous"]
    for case in m["ambiguous"]:
        assert labs[case["hash"]]["counted"] is None
        outcomes = {r["reading"]: r["counted"] for r in case["readings"]}
        merge_readings = {n.split(" + ")[0] for n in outcomes}
        assert merge_readings == {"inherit", "nonqualifying_revert_taints", "literal_taint",
                                  "taint_governs_control_pool_only"}
        assert not any(v for n, v in outcomes.items() if n.startswith("literal_taint"))
        assert any(outcomes.values())
        for r in case["readings"]:
            assert r["clause"] and r["meaning"]
            assert r["counted"] or not r["positives"]
    # spec [r2]: a merge that brings in a linked commit and a fix-worded one is open, not decided
    both = [lab for lab in labs.values() if lab["kind"] == "merge" and len(lab["commits"]) <= 50
            and "Tree-wide" not in (lab["clause"] or "")
            and any(by_id[x]["convention"] in linked for x in lab["commits"])
            and any(by_id[x]["convention"] == "keyword" for x in lab["commits"])]
    for lab in both:
        if lab["counted"] is not None:              # decided only if no reading counts it (no shared file)
            assert "shares no file" in lab["clause"] or "bot" in lab["clause"], lab
    for lab in labs.values():
        if lab["kind"] == "side":
            assert lab["counted"] is False
