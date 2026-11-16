#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Build the stored tables of one repo from what SA3's pipeline already wrote (tables_spec.md, phase A).

    python tools/tables/build.py --repo NAME        # inside the harness sandbox only (tools/harness/run.py --tables)

Runs ONLY inside the harness sandbox: it imports SA3 modules that hold the study path, and it refuses before
importing any of them when it is not inside. Reads WORK/study/{history,sa3_scans,sa3_outcomes,meta_sa3,
sa3_nesting} and the pool clone; writes WORK/study/sa3_tables/NAME/: one file per table named by its hash
(canon.py), protected tables under protected/, index.json, datacard.json and datacard.md. If an invariant fails,
nothing but build_failed.json is written and the exit code is 1.

No rule is re-implemented here. Every fact is a tool's output or the return value of an SA3 function called
unchanged: mod1_lift.frame, sa3_outcomes.universe, laws_units.Excluder.why / language_of, and
laws_history.harvest (for history_can_touch, run on a one-commit repository holding the snapshot's tree).
Every gap is in DECISIONS.md.

The `file`, `measure`, `repo` and `snapshot` builders are module functions (file_table, measure_table, repo_row,
snapshot_row, read_scan), so phase B (tools/tables/phase_b.py) can import them. Imported, this module guards
first too: inside phase B's read-only sandbox (PHASEB_SANDBOX=1) by sandbox_ro's guard, anywhere else by the
harness guard; both before any SA3 import.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS / "harness"))
import sandbox as SB  # noqa: E402

if os.environ.get("PHASEB_SANDBOX") == "1":       # phase B's read-only, declared-inputs sandbox
    import sandbox_ro as SR  # noqa: E402
    SR.assert_inside_ro()                         # before any SA3 import
else:
    SB.assert_inside(Path(os.environ.get("HARNESS_WORK", "/nonexistent")))    # before any SA3 import
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(TOOLS))
import canon as C  # noqa: E402
import datacard as D  # noqa: E402
import invariants as I  # noqa: E402
import schema as S  # noqa: E402
import laws_history as LH  # noqa: E402
import laws_units as U  # noqa: E402
import mod1_lift as L  # noqa: E402
import sa3_outcomes as O  # noqa: E402
import sa3_score as SC  # noqa: E402
from _engine import POOL_DIR  # noqa: E402

KNOWN_GAPS = [
    "event has no linking-commit column: the outcome file does not record which brought-in commit gave a merge "
    "its positives (tables_spec.md); not reconstructed",
    "event.how is null where the outcome file cannot say whether a merge's positives are its own or inherited "
    "(DECISIONS.md 9)",
    "event holds no KW rows: the outcome file gives KW's files and counts but no per-commit list; marginal KW is "
    "not recounted (DECISIONS.md 10)",
    "marginal.clears_floor is the outcome file's own verdict; it is not recounted, since that needs the floor "
    "numbers (DECISIONS.md 11)",
    "link has no resolved-target column (DECISIONS.md 12); measure has no in_degree/out_degree (DECISIONS.md 13); "
    "touch has no tree-wide flag (DECISIONS.md 14)",
]


def git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    p = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True, timeout=3600)
    if p.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.decode('utf-8', 'replace')[:300]}")
    return p.stdout


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def code_hash() -> str:
    h = hashlib.sha256()
    for f in sorted(HERE.glob("*.py")):
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def tree_paths(repo: Path, sha: str) -> list[str]:
    """every path of the snapshot's tree, once per tree entry (`git ls-tree -r -z`), undecodable bytes kept by
    surrogateescape"""
    out = []
    for ent in git(repo, "ls-tree", "-r", "-z", "--full-tree", sha).split(b"\0"):
        if ent:
            out.append(ent.split(b"\t", 1)[1].decode("utf-8", "surrogateescape"))
    return out


def archive_paths(repo: Path, sha: str) -> set[str]:
    """the files `git archive` of the snapshot holds (what the engine scanned: export-ignore honoured)"""
    with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", sha)), mode="r:") as tf:
        return {m.name for m in tf.getmembers() if not m.isdir()}


def history_touchable(repo: Path, sha: str, language: str, c_family: bool, tmp: Path) -> set[str]:
    """The paths the history walk's own unit rule would record a touch of: laws_history.harvest, unchanged, on a
    repository with one root commit whose tree is the snapshot's tree (objects shared through alternates)."""
    g = tmp / "snaprepo"
    subprocess.run(["git", "init", "-q", str(g)], check=True, capture_output=True)
    objects = git(repo, "rev-parse", "--path-format=absolute", "--git-path", "objects").decode().strip()
    (g / ".git" / "objects" / "info" / "alternates").write_text(objects + "\n")
    env = {**os.environ, "GIT_AUTHOR_DATE": "@0 +0000", "GIT_COMMITTER_DATE": "@0 +0000"}
    c = subprocess.run(["git", "-C", str(g), "commit-tree", f"{sha}^{{tree}}", "-m", "snapshot tree"],
                       capture_output=True, text=True, env=env, check=True).stdout.strip()
    subprocess.run(["git", "-C", str(g), "update-ref", "HEAD", c], check=True, capture_output=True)
    db = tmp / "snaphist.db"
    LH.harvest(g, language, db, c_family=c_family)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    got = {p for (p,) in con.execute("select path from touch")}
    con.close()
    return got


def read_scan(r: str, scan_db: Path, side: dict) -> dict[str, tuple]:
    """the scan's file_data rows by path, src_root removed exactly as universe() removes it: (SCAN_COLS...,
    mitigation_telemetry)"""
    root = side["src_root"].rstrip("/") + "/"
    cols = ", ".join(S.SCAN_COLS)
    w = L.ro(scan_db)
    scan: dict[str, tuple] = {}
    for row in w.execute(f"select file_path, {cols}, mitigation_telemetry from file_data"):
        p = row[0][len(root):] if row[0].startswith(root) else row[0].lstrip("/")
        if p in scan:
            raise SystemExit(f"{r}: the scan holds {p!r} twice")
        scan[p] = row[1:]
    w.close()
    return scan


def file_table(r: str, langs, files: set[str], side: dict, scan: dict, tree: list[str], arch: set[str] | None,
               touchable: set[str] | None) -> list[dict]:
    """The `file` table. arch None (phase B: `git archive` unavailable, a tree-only clone): in_archive is null and
    the archive test is skipped, so a unit file the scan lacks is `not_scanned`. touchable None: the history walk
    could not be run on the snapshot's tree; history_can_touch is null. Phase A always passes both."""
    gen = set(side["generated"])
    ex = U.Excluder(side["attrs"], include_tutorials=True)        # exactly as sa3_outcomes.universe builds it
    ex_no_tut = U.Excluder(side["attrs"], include_tutorials=False)
    ex_no_attr = U.Excluder({}, include_tutorials=True)
    loc_i = S.SCAN_COLS.index("total_loc")

    def reason(p: str) -> tuple[str | None, str | None]:
        if U.language_of(p) not in langs:
            return "language", None
        g = p in gen
        why = ex.why(p, g)
        if why is not None:
            if why in ("vendored", "generated") and ex_no_attr.why(p, g) != why:
                return "gitattributes", None
            if why == "example" and ex_no_tut.why(p, g) != "example":
                return "tutorial", None
            pats = {"vendored": ex.vendor, "documentation": ex.docs}.get(why)
            pat = next((x.pattern for x in pats if x.search(p)), None) if pats else None
            return why, pat
        if arch is not None and p not in arch:
            return "not_in_archive", None
        if p not in scan:
            return "not_scanned", None
        if not scan[p][loc_i]:
            return "zero_loc", None
        return None, None

    file_rows = []
    for p in dict.fromkeys(tree):                     # duplicates (impossible in git) are left to invariant 1
        why, pat = reason(p)
        sc = scan.get(p)
        file_rows.append({"repo": r, "path": p, "in_universe": p in files, "reason": why, "pattern": pat,
                          "loc": sc[loc_i] if sc else None, "language": U.language_of(p), "scanned": sc is not None,
                          "in_archive": None if arch is None else p in arch,
                          "history_can_touch": None if touchable is None else p in touchable})
    return file_rows


def measure_table(r: str, side: dict, scan: dict, in_tree: set[str], files: set[str], nest: dict) -> list[dict]:
    """The `measure` table: the scan's columns for every scanned path of the tree, nesting for every universe file.
    nest: the nesting file's content ({} when there is none)."""
    measure_rows = []
    eng = side.get("engine")
    for p in sorted(in_tree & set(scan)):
        vals = scan[p]
        for c, v in zip(S.SCAN_COLS, vals[:-1]):
            measure_rows.append({"repo": r, "path": p, "name": c, "value": None if v is None else float(v),
                                 "absent_means": S.ABSENT_MEANS[c], "instrument": "engine", "version": eng})
        tel, am = None, S.ABSENT_MEANS["amplified_cascading_flux"]
        try:
            v = (json.loads(vals[-1]) if vals[-1] else {}).get("amplified_cascading_flux")
            tel = None if v is None else float(v)
        except (ValueError, TypeError, AttributeError):
            am = "missing"                            # sa3_score.load leaves NaN when the JSON does not parse
        measure_rows.append({"repo": r, "path": p, "name": "amplified_cascading_flux", "value": tel,
                             "absent_means": am, "instrument": "engine mitigation_telemetry", "version": eng})
    nf = nest.get("files", {})
    for p in sorted(files):
        got = nf.get(p)
        for i, c in enumerate(S.NEST_COLS):
            measure_rows.append({"repo": r, "path": p, "name": c, "value": None if not got else float(got[i]),
                                 "absent_means": S.ABSENT_MEANS[c], "instrument": "sa3_nest_scan",
                                 "version": nest.get("pack")})
    return measure_rows


def repo_row(r: str, hmeta: dict, f: dict, side: dict, oc: dict, pool_tip: str | None, walk: list,
             scan: dict, in_tree: set[str]) -> dict:
    """The `repo` row. oc supplies status, why, complete, unit_files, tree_unit_files: phase A passes the outcome
    file; phase B passes the same keys from public sources (phase_b.py)."""
    cts = [ct for _, ct, _ in walk]
    return {"repo": r, "language": hmeta.get("language"), "langs": ",".join(f["langs"]),
            "units": hmeta.get("units"), "unit_rule": hmeta.get("unit"), "first_parent": f["merge_units"],
            "status": oc.get("status"), "why": oc.get("why"),
            "pool_tip": pool_tip, "history_head": hmeta.get("head"),
            "engine": side.get("engine"),
            "hashseed": None if side.get("hashseed") is None else str(side["hashseed"]),
            "commits": int(hmeta["commits"]), "bots": int(hmeta["bots"]), "merges": int(hmeta["merges"]),
            "first_parent_commits": int(hmeta["first_parent_commits"]),
            "merge_share": float(hmeta["merge_share"]),
            "walk_out_of_time_order": sum(1 for x, y in zip(cts, cts[1:]) if y < x),
            "pipeline_complete": oc.get("complete"), "pipeline_unit_files": oc.get("unit_files"),
            "pipeline_tree_unit_files": oc.get("tree_unit_files"),
            "scanned_not_in_tree": len(set(scan) - in_tree)}


def snapshot_row(r: str, snap: str, snap_ct: int | None, f: dict, window_start: int | None) -> dict:
    return {"repo": r, "sha": snap, "ct": snap_ct, "cut_ct": f["cut"], "window_start": window_start,
            "window_end": f["end"], "usable_commits": f["usable_commits"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", type=Path, help="default: <study>/sa3_tables/NAME")
    a = ap.parse_args()
    r = a.repo
    out_dir = a.out or (L.STUDY / "sa3_tables" / r)
    if (out_dir / "index.json").exists():
        print(f"{r}: {out_dir} already holds a build; refused")
        return 2
    repo_git = POOL_DIR / r
    inputs = {"history": L.STUDY / "history" / f"{r}.db", "scan_sidecar": O.SCANS / f"{r}.json",
              "scan_db": O.SCANS / f"{r}_master.db", "outcomes": O.OUT / f"{r}.json",
              "meta_sa3": O.META / f"{r}.db", "nesting": SC.NESTING / f"{r}.json"}
    # the measures schema.py names must be the ones the scorer reads
    assert tuple(SC.COLS[:-1]) == S.SCAN_COLS and SC.COLS[-1] == "mitigation_telemetry", \
        "sa3_score.COLS no longer matches schema.SCAN_COLS"

    f = L.frame(r)
    files, u = O.universe(r, f["langs"])
    side = json.loads(inputs["scan_sidecar"].read_text())
    oc = json.loads(inputs["outcomes"].read_text())
    snap = side["snapshot"]
    h = L.ro(inputs["history"])
    hmeta = dict(h.execute("select key, value from meta"))
    walk = [(s, ct, m) for s, ct, m in h.execute("select sha, ct, merge from commit_ order by rowid")]
    h.close()

    # ------------------------------------------------------------------------------------------------ file
    tree = tree_paths(repo_git, snap)
    arch = archive_paths(repo_git, snap)
    scan = read_scan(r, inputs["scan_db"], side)
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        touchable = history_touchable(repo_git, snap, hmeta["language"], hmeta.get("units") == "c+cpp", Path(tmp))
    file_rows = file_table(r, f["langs"], files, side, scan, tree, arch, touchable)
    in_tree = set(tree)

    # --------------------------------------------------------------------------------------------- measure
    nest = json.loads(inputs["nesting"].read_text()) if inputs["nesting"].exists() else {}
    measure_rows = measure_table(r, side, scan, in_tree, files, nest)

    # ------------------------------------------------------------------------------------- repo, snapshot
    snap_ct = int(git(repo_git, "show", "-s", "--format=%ct", snap).decode().strip())
    repo_row_ = repo_row(r, hmeta, f, side, oc, git(repo_git, "rev-parse", "HEAD").decode().strip(), walk, scan,
                         in_tree)
    snap_row = snapshot_row(r, snap, snap_ct, f, oc.get("window_start"))

    # ------------------------------------------------------------------------------------------------ touch
    touch_rows = []
    if oc.get("window_start") is not None:
        pos = {s: i for i, (s, _, _) in enumerate(walk)}
        h = L.ro(inputs["history"])
        where_c = "c." + f["where"].replace(" and ", " and c.")      # as sa3_outcomes.build restricts it
        seen = set()
        for s, p, ct in h.execute(f"select t.sha, t.path, c.ct from touch t join commit_ c on c.sha=t.sha "
                                  f"where {where_c} and c.ct>? and c.ct<=?", (oc["window_start"], f["end"])):
            if p in files and (s, p) not in seen:
                seen.add((s, p))
                touch_rows.append({"repo": r, "sha": s, "path": p, "ct": ct, "walk_pos": pos[s]})
        h.close()

    # -------------------------------------------------------------------------- event, pool, marginal, link
    outs = oc.get("outcomes", {})
    merge_of = {s: m for s, _, m in walk}
    link_rows, linked = [], set()
    if inputs["meta_sa3"].exists():
        m = L.ro(inputs["meta_sa3"])
        cnt = Counter((s, k, v if v is not None else "") for s, k, v in m.execute("select sha, kind, value from link"))
        m.close()
        linked = {s for s, _, _ in cnt}
        link_rows = [{"repo": r, "sha": s, "kind": k, "value": v, "n": n} for (s, k, v), n in cnt.items()]
    pairs: dict[tuple[str, str], dict] = {}
    for oc_name, col in (("HP", "hp"), ("HP_allreverts", "hp_allreverts")):
        for s, ps in outs.get(oc_name, {}).get("commits", {}).items():
            for p in ps:
                pairs.setdefault((s, p), {"hp": False, "hp_allreverts": False, "tier": None})[col] = True
    for oc_name, tier in S.TIER_OUTCOME.items():
        for s, ps in outs.get(oc_name, {}).get("commits", {}).items():
            for p in ps:
                e = pairs.setdefault((s, p), {"hp": False, "hp_allreverts": False, "tier": None})
                if e["tier"] not in (None, tier):
                    raise SystemExit(f"{r}: an event row is in two exclusive tiers "
                                     "(protected: commit and path not named)")
                e["tier"] = tier

    def how(s: str) -> str | None:
        if not merge_of.get(s):
            return "own"                   # sa3_outcomes gives inherited events only to merges of the walk
        return "inherited" if s not in linked else None   # a merge with no link row of its own has no own event

    event_rows = [{"repo": r, "sha": s, "path": p, **e, "how": how(s)} for (s, p), e in pairs.items()]
    pool_rows = [{"repo": r, "sha": s, "path": p}
                 for s, ps in outs.get("control_pool", {}).get("commits", {}).items() for p in ps]
    marginal_rows = []
    for oc_name in S.OUTCOMES:
        v = outs.get(oc_name)
        if v is None:
            continue
        if oc_name == "control_pool":
            marginal_rows.append({"repo": r, "outcome": oc_name, "n_files": v.get("n_files_any"),
                                  "n_commits": v.get("n_commits"), "largest_commit_share": None, "clears_floor": None})
        else:
            marginal_rows.append({"repo": r, "outcome": oc_name, "n_files": v.get("n_files"),
                                  "n_commits": v.get("n_commits"), "largest_commit_share": v.get("largest_commit_share"),
                                  "clears_floor": v.get("clears_floor")})

    tables = {"repo": [repo_row_], "snapshot": [snap_row], "file": file_rows, "measure": measure_rows,
              "touch": touch_rows, "link": link_rows, "event": event_rows, "pool": pool_rows,
              "marginal": marginal_rows}
    fails = I.check(tables, tree)
    out_dir.mkdir(parents=True, exist_ok=True)
    if fails:
        (out_dir / "build_failed.json").write_text(json.dumps({"repo": r, "failures": fails}, indent=1) + "\n")
        print(f"{r}: BUILD FAILED, {len(fails)} invariant failures:")
        for x in fails:
            print("  " + x)
        return 1
    index = {"repo": r, "builder_code_sha256": code_hash(), "schema_version": S.SCHEMA_VERSION,
             "inputs": {k: ({"sha256": sha256_file(p), **({"wal_sha256": sha256_file(Path(str(p) + "-wal"))}
                                                         if Path(str(p) + "-wal").exists() else {})}
                            if p.exists() else None) for k, p in inputs.items()},
             "pool_clone_tip": repo_row_["pool_tip"], "snapshot": snap, "linguist_commit": U.LINGUIST,
             "known_gaps": KNOWN_GAPS, "tables": {}}
    for name in S.TABLES:
        index["tables"][name] = C.write_table(out_dir, name, tables[name])
    card = D.compute(tables)
    (out_dir / "datacard.json").write_text(json.dumps(card, indent=1, sort_keys=True) + "\n")
    (out_dir / "datacard.md").write_text(D.markdown(card))
    (out_dir / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    print(f"{r}: tables built: " + ", ".join(f"{n} {t['rows']}" for n, t in index["tables"].items()), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
