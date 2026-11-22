"""Tests of the stored tables, phase A (tools/tables/, docs/process/tables_spec.md).

Tests 3, 4 and 7 are pure (no pipeline, no sandbox). Tests 1, 2, 5 and 6 generate control repositories (generator
1.3.0, seed 11, --years 10) under pytest's tmp_path and run the harness with --tables (route manifest only), so
every SA3 tool and the table builder run inside the sandbox; they are skipped, with the reason, when bwrap,
tree_sitter_language_pack 1.20.0, linguist's cached lists or the engine export are unavailable. One run takes
about 6-8 s; each repository is run once per session (twice for Python, for test 5).

Nothing here imports an SA3 tool: the manifest side of test 1 is read from the manifest alone, and test 7 reads
the SA3 tools' source as text (ast), never importing them.
"""
from __future__ import annotations

import ast
import importlib.metadata as md
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "tools" / "tables"
HARNESS = ROOT / "tools" / "harness"
GEN = ROOT / "tools" / "control_repo" / "generate.py"
sys.path.insert(0, str(TABLES))
sys.path.insert(0, str(HARNESS))
import canon as C  # noqa: E402
import datacard as D  # noqa: E402
import invariants as I  # noqa: E402
import schema as S  # noqa: E402
import sandbox as SB  # noqa: E402

DAY = 86400


# ------------------------------------------------------------------------------------------ pipeline runs
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


class Runs:
    """one harness run per (language, mutation, copy), cached for the session"""

    def __init__(self, base: Path):
        self.base = base
        self.cache: dict = {}
        self.engine_checked: bool | None = None

    def engine_present(self) -> bool:
        if self.engine_checked is None:          # decided INSIDE the sandbox (laws-study is never looked at outside)
            w = SB.prepare(self.base / "engine-probe")
            (w / "tree/tools/harness").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HARNESS / "sandbox.py", w / "tree/tools/harness/sandbox.py")
            p = SB.run(["/usr/bin/python3", "-I", "-B", "-c",
                        f"import os; print(os.path.isdir({str(SB.ENGINE / 'gitgalaxy')!r}))"], w, timeout=120)
            self.engine_checked = p.stdout.strip() == "True"
        return self.engine_checked

    def get(self, language: str = "python", mutation: str | None = None, copy: int = 0) -> dict:
        key = (language, mutation, copy)
        if key in self.cache:
            return self.cache[key]
        why = _skip_reason()
        if why:
            pytest.skip(why)
        if not self.engine_present():
            pytest.skip("engine export not present")
        tag = f"{language}-{mutation or 'base'}"         # the repo name: the same for every copy
        ctrl = self.base / "controls" / f"{language}-{mutation or 'base'}"
        if not ctrl.exists():
            argv = [sys.executable, "-B", str(GEN), "--out", str(ctrl), "--seed", "11", "--years", "10",
                    "--language", language] + (["--mutation", mutation] if mutation else [])
            subprocess.run(argv, check=True, capture_output=True, cwd=str(self.base))
        work = self.base / "work" / f"{tag}-{copy}"
        p = subprocess.run([sys.executable, "-B", str(HARNESS / "run.py"), "--control", str(ctrl), "--work", str(work),
                            "--name", tag, "--routes", "manifest", "--no-shim-lock", "--tables"],
                           capture_output=True, text=True, timeout=1800)
        assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
        rec = json.loads((work / "report" / f"{tag}.run.json").read_text())
        repo = rec["repo"]
        man = rec["routes"]["manifest"]
        stage = next(s for s in man["stages"] if s["stage"] == "tables")
        out = {"ctrl": ctrl, "manifest": json.loads((ctrl / "manifest.json").read_text()), "repo": repo,
               "study": work / "manifest" / "study", "tables_dir": work / "manifest" / "study" / "sa3_tables" / repo,
               "stage": stage}
        self.cache[key] = out
        return out


@pytest.fixture(scope="session")
def runs(tmp_path_factory):
    return Runs(tmp_path_factory.mktemp("tables"))


def load(tdir: Path) -> tuple[dict, dict]:
    idx = json.loads((tdir / "index.json").read_text())
    return idx, {n: C.read_rows(tdir / t["file"]) for n, t in idx["tables"].items()}


# --------------------------------------------------------------------- 1. against the manifest, base repos
def classify(man: dict, t: dict, outcome: dict) -> dict:
    """every difference between event (HP) and the manifest's expected positives, by cause. The causes are the
    ones docs/process/harness_report.md and tools/harness/DECISIONS.md (items 23, 32) already name; anything
    else is 'UNEXPLAINED'."""
    snap = t["snapshot"][0]
    ws, we, cut = snap["window_start"], snap["window_end"], snap["cut_ct"]
    t0 = man["points"]["snapshot"]["time"]
    t1 = t0 + 730 * DAY
    real = {r["hash"]: r for r in man["realised"]}
    labels = {e["hash"]: e for e in man["expected_labels"] if real.get(e["hash"], {}).get("kind") != "side"}
    commit = {c["id"]: c for c in man["commits"]}
    mfiles = {f["id"]: f for f in man["files"]}
    by_snap = {f["path_at_snapshot"]: f for f in man["files"] if f.get("path_at_snapshot")}
    F = {r["path"]: r for r in t["file"]}
    touch = {(r["sha"], r["path"]) for r in t["touch"]}
    ev = {(r["sha"], r["path"]) for r in t["event"] if r["hp"]}
    want = {(h, x["path_at_snapshot"]) for h, e in labels.items() if e["counted"] is True for x in e["positives"]}

    def path_at(fid, lid):
        got = None
        for x in mfiles[fid].get("path_history", []):
            if x["commit"] <= lid:
                got = x["path"]
        return got

    def cause_manifest_only(h, p):
        tm = real[h]["time"]
        if tm <= ws:
            return "window offset: before the code's window start (its cut)"
        if tm > we:
            return "window offset: after the code's window end"
        if not F[p]["in_universe"]:
            return "UNEXPLAINED: outside the code's universe"
        if (h, p) not in touch:
            fid = by_snap[p]["id"]
            if any(fid in commit[l]["file_ids"] and path_at(fid, l) != p for l in labels[h]["commits"]):
                return "rename after the snapshot"
            return "UNEXPLAINED: no touch row"
        return "UNEXPLAINED"

    def cause_pipeline_only(h, p):
        e = labels.get(h)
        if e is None:
            return "UNEXPLAINED: not a manifest label"
        if e["counted"] is None:
            return "ambiguous in the manifest (listed apart, not a difference)"
        if real[h]["time"] > t1:
            return "window offset: after the manifest's window end"
        for l in e["commits"]:
            tg = commit[l].get("revert_target")
            if tg and t0 < commit[tg["id"]]["time"] <= cut:
                return "window offset: revert of code made between the manifest's snapshot and the code's cut"
        return "UNEXPLAINED"

    nofile = [h for h, e in labels.items() if e["counted"] is True and not e["positives"]
              and t0 < real[h]["time"] <= t1]
    return {"manifest_pairs": len(want), "event_pairs": len(ev),
            "manifest_only": dict(Counter(cause_manifest_only(h, p) for h, p in want - ev)),
            "pipeline_only": dict(Counter(cause_pipeline_only(h, p) for h, p in ev - want)),
            "counted_commits_with_no_file_at_the_snapshot": len(nofile),
            "outcome_hp_pairs": {(s, p) for s, ps in outcome["outcomes"]["HP"]["commits"].items() for p in ps}}


@pytest.mark.parametrize("language", ["python", "c"])
def test_1_against_the_manifest(runs, language):
    r = runs.get(language)
    assert r["stage"]["rc"] == 0, r["stage"]["stdout"] + r["stage"]["stderr"]
    idx, t = load(r["tables_dir"])
    man = r["manifest"]
    by_snap = {f["path_at_snapshot"]: f for f in man["files"] if f.get("path_at_snapshot")}
    F = {x["path"]: x for x in t["file"]}
    assert set(F) == set(by_snap), "the tree and the manifest's snapshot paths differ"
    bad = [p for p in F if bool(F[p]["in_universe"]) != by_snap[p]["is_unit"]]
    assert not bad, f"in_universe != is_unit on {len(bad)} paths: {bad[:5]}"
    bad = [(p, F[p]["loc"], by_snap[p]["properties"]["snapshot"]["loc"]) for p in F if F[p]["in_universe"]
           and F[p]["loc"] != by_snap[p]["properties"]["snapshot"]["loc"] + 1]
    assert not bad, f"loc != manifest + 1 on {len(bad)} files: {bad[:5]}"
    outcome = json.loads((r["study"] / "sa3_outcomes" / f"{r['repo']}.json").read_text())
    c = classify(man, t, outcome)
    ev = {(x["sha"], x["path"]) for x in t["event"] if x["hp"]}
    assert ev == c.pop("outcome_hp_pairs"), "event (HP) is not exactly the outcome file's HP list"
    print(f"\n{language}: {json.dumps(c)}")
    unexplained = {k: v for side in ("manifest_only", "pipeline_only") for k, v in c[side].items() if "UNEXPLAINED" in k}
    assert not unexplained, f"differences with no named cause (a finding): {unexplained}; all: {c}"


# ----------------------------------------------------------------------------------------- 2. mutations
def test_2a_generic_dir_names(runs):
    r = runs.get("python", "generic_dir_names")
    idx, t = load(r["tables_dir"])
    sys.path.insert(0, str(ROOT / "tools" / "control_repo"))
    from mutations import GENERIC_DIRS                     # the generator's own list of what it planted
    moved = {f["path_at_snapshot"]: f["generic_dir"] for f in r["manifest"]["files"]
             if f.get("generic_dir") and f.get("path_at_snapshot")}
    assert moved
    F = {x["path"]: x for x in t["file"]}
    for p, g in moved.items():
        assert F[p]["reason"] == "vendored" and not F[p]["in_universe"], (p, F[p])
        assert F[p]["pattern"] == GENERIC_DIRS[g], (p, F[p]["pattern"], GENERIC_DIRS[g])
    card = json.loads((r["tables_dir"] / "datacard.json").read_text())
    by_pat = card["github_patterns"]["by_pattern"]
    for g, pat in GENERIC_DIRS.items():
        assert by_pat.get(pat) == sum(1 for x in moved.values() if x == g), (g, by_pat)
    assert card["files"]["by_reason"]["vendored"] >= len(moved)


def test_2b_vendored_half(runs):
    r = runs.get("python", "vendored_half")
    base = runs.get("python")
    idx, t = load(r["tables_dir"])
    imported = {f["path_at_snapshot"] for f in r["manifest"]["files"]
                if f.get("path_at_snapshot") and f["path_at_snapshot"].startswith("src/contrib/")}
    assert imported
    F = {x["path"]: x for x in t["file"]}
    assert all(F[p]["in_universe"] for p in imported), "imported files left the universe"
    card = json.loads((r["tables_dir"] / "datacard.json").read_text())
    bcard = json.loads((base["tables_dir"] / "datacard.json").read_text())
    uni = card["files"]["in_universe"]
    big = card["largest_directory_of_universe"]["first_two_components"]
    assert big["share"] == round(len(imported) / uni, 4)            # the largest directory is the imported one
    assert big["untouched_in_window_share"] == 1.0                   # and nothing ever touches it
    assert bcard["largest_directory_of_universe"]["first_two_components"]["untouched_in_window_share"] < 0.5
    assert card["universe_untouched_in_window_share"] > 0.4 > bcard["universe_untouched_in_window_share"]


def test_2c_bot_merges_fails_invariant_7(runs):
    r = runs.get("python", "bot_merges")
    assert r["stage"]["rc"] == 1, r["stage"]
    failed = json.loads((r["tables_dir"] / "build_failed.json").read_text())["failures"]
    assert failed and all(x.startswith("invariant 7:") for x in failed), failed
    assert f"snapshot('{r['repo']}',)" in failed[0] and "window_end" in failed[0]
    assert not (r["tables_dir"] / "index.json").exists() and not list(r["tables_dir"].glob("*.jsonl"))


def test_2d_merge_workflow_inherited(runs):
    r = runs.get("python", "merge_workflow")
    idx, t = load(r["tables_dir"])
    hows = Counter(e["how"] for e in t["event"])
    assert hows.get("inherited", 0) > 0, hows


# ---------------------------------------------------------------------------------------- 3. hash stability
def _sample_rows():
    rows = []
    for i in range(30):
        rows.append({"repo": "r", "path": f"src/d{i % 4}/f{i}.py", "name": "struct_branch", "value": float(i * 3),
                     "absent_means": "missing", "instrument": "engine", "version": "v"})
    rows.append({"repo": "r", "path": "src/é/ü.py", "name": "pagerank_score", "value": 0.1 + 0.2,
                 "absent_means": "missing", "instrument": "engine", "version": None})
    rows.append({"repo": "r", "path": b"src/bad\xff.py".decode("utf-8", "surrogateescape"), "name": "x",
                 "value": None, "absent_means": "zero", "instrument": "engine", "version": "v"})
    return rows


def test_3_hash_stability():
    rows = _sample_rows()
    h = C.table_hash("measure", rows)
    assert C.table_hash("measure", list(reversed(rows))) == h                      # row order
    assert C.table_hash("measure", [{k: r[k] for k in reversed(list(r))} for r in rows]) == h   # dict order
    trows = [{"repo": "r", "sha": f"{i:040x}", "path": "a.py", "ct": i * 10, "walk_pos": i} for i in range(5)]
    th = C.table_hash("touch", trows)
    assert C.table_hash("touch", [{**r, "ct": float(r["ct"]), "walk_pos": float(r["walk_pos"])} for r in trows]) == th
    ints_as_reals = [{**r, "value": (int(r["value"]) if r["value"] is not None and float(r["value"]).is_integer()
                                     else r["value"])} for r in rows]
    assert C.table_hash("measure", ints_as_reals) == h                              # 6 and 6.0 in a real column
    changed = [dict(r) for r in rows]
    changed[5]["value"] += 1e-12
    assert C.table_hash("measure", changed) != h                                    # one value changes it
    changed = [dict(r) for r in rows]
    changed[0]["version"] = "w"
    assert C.table_hash("measure", changed) != h
    # the stated bytes: fixed column order, float.hex() strings, no spaces, \udcXX for an undecodable byte
    b = C.table_bytes("measure", rows)
    line = next(x for x in b.split(b"\n") if b"bad" in x)
    assert line == (b'{"repo":"r","path":"src/bad\\udcff.py","name":"x","value":null,"absent_means":"zero",'
                    b'"instrument":"engine","version":"v"}')
    back = json.loads(line)["path"].encode("utf-8", "surrogateescape")
    assert back == b"src/bad\xff.py"                                                 # reversible
    assert b'"value":"' + (0.1 + 0.2).hex().encode() + b'"' in b
    keys = [json.loads(x)["path"].encode("utf-8", "surrogateescape") for x in b.splitlines()]
    assert keys == sorted(keys)                                                      # byte order of the key
    with pytest.raises(C.CanonError):
        C.table_bytes("measure", rows + [rows[0]])                                   # a duplicate key
    with pytest.raises(C.CanonError):
        C.table_bytes("touch", [{**trows[0], "ct": 1.5}])                            # not a whole number
    with pytest.raises(C.CanonError):
        C.table_bytes("measure", [{**rows[0], "value": float("nan")}])


def test_3b_written_once(tmp_path):
    rows = _sample_rows()
    a = C.write_table(tmp_path, "measure", rows)
    f = tmp_path / a["file"]
    assert f.name == f"measure.{a['hash'][:16]}.jsonl" and f.read_bytes() == C.table_bytes("measure", rows)
    assert C.write_table(tmp_path, "measure", list(reversed(rows))) == a          # same content: accepted
    f.write_bytes(b"tampered\n")
    with pytest.raises(C.CanonError):
        C.write_table(tmp_path, "measure", rows)                                    # never written over
    p = C.write_table(tmp_path, "pool", [{"repo": "r", "sha": "a" * 40, "path": "x.py"}])
    assert p["file"].startswith("protected/") and p["protected"]


# ----------------------------------------------------------------------------------------- 4. invariants bite
def valid_tables() -> tuple[dict, list[str]]:
    r, s1, s2 = "r", "1" * 40, "2" * 40
    t = {
        "repo": [{"repo": r}],
        "snapshot": [{"repo": r, "sha": "f" * 40, "ct": 100, "cut_ct": 100, "window_start": 100, "window_end": 900,
                      "usable_commits": 5}],
        "file": [
            {"repo": r, "path": "src/a.py", "in_universe": 1, "reason": None, "pattern": None, "loc": 10,
             "language": "python", "scanned": 1, "in_archive": 1, "history_can_touch": 1},
            {"repo": r, "path": "README.md", "in_universe": 0, "reason": "language", "pattern": None, "loc": 3,
             "language": None, "scanned": 1, "in_archive": 1, "history_can_touch": 0},
            {"repo": r, "path": "vendor/x.py", "in_universe": 0, "reason": "vendored", "pattern": "^vendor/",
             "loc": None, "language": "python", "scanned": 0, "in_archive": 1, "history_can_touch": 0}],
        "measure": [{"repo": r, "path": "src/a.py", "name": n, "value": 1.0, "absent_means": S.ABSENT_MEANS[n],
                     "instrument": "engine", "version": "v"} for n in S.SCORER_MEASURES],
        "touch": [{"repo": r, "sha": s1, "path": "src/a.py", "ct": 200, "walk_pos": 3},
                  {"repo": r, "sha": s2, "path": "src/a.py", "ct": 300, "walk_pos": 4}],
        "link": [],
        "event": [{"repo": r, "sha": s1, "path": "src/a.py", "hp": 1, "hp_allreverts": 1, "tier": "issue_fix",
                   "how": "own"}],
        "pool": [{"repo": r, "sha": s2, "path": "src/a.py"}],
        "marginal": [{"repo": r, "outcome": o, "n_files": n, "n_commits": n, "largest_commit_share": sh,
                      "clears_floor": 0} for o, n, sh in
                     (("HP", 1, 1.0), ("HP_allreverts", 1, 1.0), ("HP_fixref", 1, 1.0), ("HP_revert", 0, None),
                      ("HP_cve", 0, None), ("KW", 0, None), ("control_pool", 1, None))],
    }
    return t, ["src/a.py", "README.md", "vendor/x.py"]


def _plant(num):
    import copy
    t, tree = valid_tables()
    t = copy.deepcopy(t)
    if num == 1:
        tree = tree + ["src/missing.py"]
        return t, tree, "'src/missing.py'"
    if num == 2:
        t["file"][0]["loc"] = 0
        return t, tree, "file('r', 'src/a.py')"
    if num == 3:
        t["file"][1]["reason"] = "too dull"
        return t, tree, "file('r', 'README.md')"
    if num == 4:
        t["touch"].append({"repo": "r", "sha": "3" * 40, "path": "README.md", "ct": 400, "walk_pos": 5})
        return t, tree, f"touch('r', '{'3' * 40}', 'README.md')"
    if num == 5:
        t["touch"] = [x for x in t["touch"] if x["sha"] != "2" * 40]          # the pool commit's touch row
        # a protected table's row is never named: number, table and count only (tables_phase_b_spec.md)
        return t, tree, "invariant 5: 1 row of protected table pool fail (rows not named)"
    if num == 6:
        t["marginal"][0]["n_files"] = 2
        return t, tree, "marginal('r', 'HP')"
    if num == 7:
        t["snapshot"][0]["window_end"] = 100
        return t, tree, "snapshot('r',)"
    if num == 8:
        t["measure"] = [m for m in t["measure"] if m["name"] != "nest_max"]
        return t, tree, "file('src/a.py'): no measure row for nest_max"
    raise AssertionError(num)


def test_4_invariants_bite():
    t, tree = valid_tables()
    assert I.check(t, tree) == []
    for num in range(1, 9):
        pt, ptree, names = _plant(num)
        fails = I.check(pt, ptree)
        assert fails, f"invariant {num} did not fail"
        assert all(f.startswith(f"invariant {num}:") for f in fails), (num, fails)
        assert any(names in f for f in fails), (num, names, fails)
        if num == 5:                                 # the planted pool row's commit and path are not named
            assert not any("2" * 40 in f or "src/a.py" in f for f in fails), fails
    # a protected row failing invariants 4 and 5 (an event outside the universe, with no touch row): not named
    t, tree = valid_tables()
    t["event"].append({"repo": "r", "sha": "4" * 40, "path": "secret/positive.py", "hp": 1, "hp_allreverts": 1,
                       "tier": "issue_fix", "how": "own"})
    fails = I.check(t, tree)
    assert "invariant 4: 1 row of protected table event fail (rows not named)" in fails, fails
    assert "invariant 5: 1 row of protected table event fail (rows not named)" in fails, fails
    assert not any("4" * 40 in f or "secret/positive.py" in f for f in fails), fails
    # more plants on single invariants
    t, tree = valid_tables()
    t["file"].append(dict(t["file"][0]))                                     # a path twice
    assert any("appears 2 times" in f and "src/a.py" in f for f in I.check(t, tree))
    t, tree = valid_tables()
    t["file"][2]["pattern"] = None                                           # vendored with no pattern
    assert any(f.startswith("invariant 3:") and "vendor/x.py" in f for f in I.check(t, tree))
    t, tree = valid_tables()
    t["snapshot"][0]["usable_commits"] = 0
    assert any(f.startswith("invariant 7:") and "usable commits 0" in f for f in I.check(t, tree))
    t, tree = valid_tables()
    t["measure"].append({**t["measure"][0], "path": "nowhere.py"})
    assert any(f.startswith("invariant 8:") and "nowhere.py" in f for f in I.check(t, tree))
    t, tree = valid_tables()
    t["marginal"][0]["largest_commit_share"] = 0.5
    assert any(f.startswith("invariant 6:") and "marginal('r', 'HP')" in f for f in I.check(t, tree))


# -------------------------------------------------------------------------------------------- 5. determinism
def test_5_determinism(runs):
    a, b = runs.get("python"), runs.get("python", copy=1)
    ia, _ = load(a["tables_dir"])
    ib, _ = load(b["tables_dir"])
    ha = {n: (x["hash"], x["rows"]) for n, x in ia["tables"].items()}
    hb = {n: (x["hash"], x["rows"]) for n, x in ib["tables"].items()}
    assert ha == hb
    assert (a["tables_dir"] / "datacard.json").read_bytes() == (b["tables_dir"] / "datacard.json").read_bytes()


# --------------------------------------------------------------------------------------- 6. no leak in the card
def _strings(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)
    elif isinstance(x, str):
        yield x


@pytest.mark.parametrize("which", [("python", None), ("python", "merge_workflow")])
def test_6_no_leak(runs, which):
    r = runs.get(*which)
    idx, t = load(r["tables_dir"])
    card = json.loads((r["tables_dir"] / "datacard.json").read_text())
    md_text = (r["tables_dir"] / "datacard.md").read_text()
    strings = set(_strings(card))
    secret = {row[k] for n in S.PROTECTED for row in t[n] for k in S.TABLES[n]["key"]}
    assert secret
    hit = sorted(s for s in secret if s in strings)
    assert not hit, f"protected key strings in the card: {hit[:10]}"
    # substrings: every path and commit hash of a protected table (and every path of the tree) in the text
    longs = {row[k] for n in S.PROTECTED for row in t[n] for k in ("sha", "path") if k in row}
    longs |= {row["path"] for row in t["file"]}
    blob = json.dumps(card) + md_text
    leaked = sorted(s for s in longs if s in blob)
    assert not leaked, leaked[:10]
    assert not re.search(r"\b[0-9a-f]{40}\b", blob), "a 40-hex string is in the card"


# -------------------------------------------------------------------------------------- 7. nothing recomputed
def _tool_constants():
    """the registered numbers and the pattern / keyword strings of SA3's tools, read from their source as text"""
    nums, pats, words = set(), set(), set()
    wanted = {"MAX_BROUGHT", "FLOOR_FILES", "FLOOR_COMMITS", "MAX_COMMIT_SHARE", "MIN_COMPLETE", "WIDE_SHARE",
              "WIDE_MIN_FILES", "MERGE_SHARE", "CUT_Q", "WINDOW_DAYS", "MIN_POSITIVES"}
    for f in ("sa3_outcomes.py", "mod1_lift.py", "laws_history.py", "hist_replicate.py", "hist_meta.py",
              "laws_units.py", "hist_fixlabel.py", "sa3_score.py"):
        tree = ast.parse((ROOT / "tools" / f).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                names += [e.id for t in node.targets if isinstance(t, ast.Tuple) for e in t.elts
                          if isinstance(e, ast.Name)]
                vals = node.value.elts if isinstance(node.value, ast.Tuple) else [node.value]
                if isinstance(node.targets[0], ast.Tuple):
                    pairs = zip(names, vals)
                else:
                    pairs = [(n, node.value) for n in names]
                for n, v in pairs:
                    if n in wanted and isinstance(v, ast.Constant):
                        nums.add(v.value)
                    if n in {"TEST_PARTS", "EXAMPLE_PARTS", "TUTORIAL_PARTS", "TEST_NAMES", "GENERATED_NAMES"} and \
                            isinstance(v, (ast.Set, ast.Tuple)):
                        words |= {e.value for e in v.elts if isinstance(e, ast.Constant)}
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "compile" and node.args \
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                pats.add(node.args[0].value)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "compile" and node.args \
                    and isinstance(node.args[0], ast.JoinedStr):
                pass
    return nums, pats, words


def test_7_nothing_recomputed():
    nums, pats, words = _tool_constants()
    assert {50, 30, 20, 0.25, 0.9, 0.1, 0.3, 0.8, 730} <= nums, nums      # the parse found the registered values
    assert any("fix" in p for p in pats) and len(pats) > 5
    words -= set(S.REASONS)            # the reason names ("test", "example", ...) are labels, not keyword lists
    linguist = set()
    cache = Path.home() / SB.LINGUIST_SUB
    for n in ("vendor.yml", "documentation.yml"):
        if (cache / n).is_file():
            linguist |= {ln[2:].strip() for ln in (cache / n).read_text().splitlines() if ln.startswith("- ")}
    for f in sorted(TABLES.glob("*.py")):
        src = f.read_text()
        tree = ast.parse(src)
        lits = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)]
        bad_nums = sorted({v for v in lits if isinstance(v, (int, float)) and not isinstance(v, bool) and v in nums})
        assert not bad_nums, f"{f.name}: registered numbers {bad_nums}"
        strs = [v for v in lits if isinstance(v, str)]
        assert not [p for p in pats if p in src], f"{f.name}: an SA3 pattern string"
        assert not [w for w in words if w in strs], f"{f.name}: a laws_units keyword {[w for w in words if w in strs]}"
        assert not [p for p in linguist if p in strs], f"{f.name}: a linguist pattern"
        for mod in ("fnmatch", "FIXLIKE", "CLOSES", "is_fix_message", "fix_shas", "WIDE_", "FLOOR_"):
            assert mod not in src, f"{f.name}: uses {mod}"


def test_8_builder_refuses_outside_the_sandbox(tmp_path):
    """the builder's guard runs before any SA3 import: outside the sandbox it stops at once"""
    p = subprocess.run([sys.executable, "-B", str(TABLES / "build.py"), "--repo", "x"], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "HARNESS_WORK": str(tmp_path)}, timeout=60)
    assert p.returncode != 0 and "SandboxError" in p.stderr and "refused" in p.stderr, p.stderr[-800:]
