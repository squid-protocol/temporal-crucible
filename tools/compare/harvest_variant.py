#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The two harvest variants of docs/process/comparison_scorer_part2_spec.md (Revision 2, section 4): copies of
the link harvest with rows deleted, and the reference outcome builder run UNCHANGED on each copy.

  PU_tracker_keys_case_sensitive   the owner job's A' harvest: tools/owner/prepare.py's `stage_copy` (copy,
                                   checkpoint, rollback mode) and tools/owner/tracker_keys.py's `strip_harvest`
                                   (every `issue_fix` row whose value has a hyphen and is not its own upper-case
                                   form), both imported by file and called unchanged
  PU_late_revert_ticket_dropped    the same converted copy, without the `issue_fix` rows of each commit that has a
                                   revert link whose target resolves to a commit after the cut (`late_strip`)

The late-revert resolution, as section 4 states it (Amendment 5 section 5): a revert link's stored value (the
hash after "This reverts commit"; the empty value of a quoted `Revert "` line never resolves), lower-cased, is
matched as a prefix against every commit reachable from the clone's HEAD; a unique match is the target. The
target's time is its commit time, or, for a commit brought in by a merge, that merge's commit time: brought in
by the EARLIEST merge of the history walk (`commit_` in rowid order) whose parents after the first reach it
without passing through a commit of the walk. A target whose time is later than the cut (the frozen outcome
file's `cut`) is late. Unresolved reverts keep their rows; `trailer:*` and `cve` rows are never touched.

Stages, each in tools/harness/sandbox_ro.py's read-only sandbox (its guard reads the mount table first), with
one repo's declared inputs bound at their study paths:

  prepare   the owner job's `stage_copy` on the declared originals (history, scan, harvest with side files),
            then the late-revert copy and its resolution detail; writes db/harvest.db (the unmodified copy),
            db/harvest_aprime.db, db/harvest_late.db, late_detail.json
  build     `sa3_outcomes.build(repo)` from the code copy, unchanged, with one of those harvests bound at
            <study>/meta_sa3/<repo>.db; writes outcome.json (as `sa3_outcomes.py --repo` writes its file)

    python3 tools/compare/harvest_variant.py variant --study S --pool P --repos a,b --variant case|late \
            --scratch D --out O                                  (decoys only; --real is refused)
    python3 tools/compare/harvest_variant.py stage prepare|build --args F --rundir D   (inside the sandbox only)

On real data these copies are made only inside the scoring job (a later specification); this module refuses a
study or pool that is not under a session scratch root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if "tools_compare__util" not in sys.modules:
    import importlib.util as _iu
    _s = _iu.spec_from_file_location("tools_compare__util", str(HERE / "_util.py"))
    _m = _iu.module_from_spec(_s)
    sys.modules["tools_compare__util"] = _m
    _s.loader.exec_module(_m)
U = sys.modules["tools_compare__util"]

VARIANTS = {"case": "PU_tracker_keys_case_sensitive", "late": "PU_late_revert_ticket_dropped"}
HARVEST = {"plain": "harvest.db", "case": "harvest_aprime.db", "late": "harvest_late.db"}
COMMIT_LISTS = ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "control_pool")
LISTS = ("vendor.yml", "documentation.yml")


def owner(name: str):
    """tools/owner/<name>.py under the name tools/owner's own loader gives it (tools_owner_<name>)"""
    return U.load_path(U.TOOLS / "owner" / f"{name}.py", f"tools_owner_{name}")


# ============================================================================================ in the sandbox
def ro(p: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def reachable(clone: Path) -> dict[str, tuple[list[str], int]]:
    """sha -> (parents, commit time) for every commit reachable from the clone's HEAD"""
    p = subprocess.run(["git", "-C", str(clone), "log", "--format=%H%x00%P%x00%ct"], capture_output=True,
                       text=True, errors="replace", timeout=3600, check=True)
    out = {}
    for line in p.stdout.splitlines():
        sha, par, ct = line.split("\x00")
        out[sha] = (par.split(), int(ct))
    return out


def merge_owner(reach: dict, walk: list[str]) -> dict[str, str]:
    """commit -> the earliest merge of the walk that brings it in (reachable from that merge's parents after the
    first without passing through a commit of the walk)"""
    on_walk = set(walk)
    own: dict[str, str] = {}
    for m in walk:
        pars = reach.get(m, ([], 0))[0]
        stack = list(pars[1:])
        while stack:
            c = stack.pop()
            if c in on_walk or c in own or c not in reach:
                continue
            own[c] = m
            stack.extend(reach[c][0])
    return own


def resolve_reverts(harvest: Path, history: Path, clone: Path, cut: int) -> dict:
    """per commit with a revert link: each link's value, its unique target (or None) and the target's time; and
    the commits whose `issue_fix` rows the late-revert variant deletes"""
    reach = reachable(clone)
    by7: dict[str, list[str]] = defaultdict(list)
    for s in reach:
        by7[s[:7]].append(s)
    h = ro(history)
    try:
        walk = [s for (s,) in h.execute("select sha from commit_ order by rowid")]
    finally:
        h.close()
    own = merge_owner(reach, walk)
    m = ro(harvest)
    try:
        links: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for sha, kind, value in m.execute("select sha, kind, value from link"):
            links[sha].append((kind, value or ""))
    finally:
        m.close()
    commits = {}
    late_commits = []
    for sha, ls in links.items():
        reverts = [v for k, v in ls if k == "revert"]
        if not reverts:
            continue
        rec = []
        for v in reverts:
            v2 = v.lower()
            hit = [s for s in by7.get(v2[:7], ()) if s.startswith(v2)] if len(v2) >= 7 else []
            tgt = hit[0] if len(hit) == 1 else None
            t = reach[own.get(tgt, tgt)][1] if tgt else None
            rec.append({"value": v, "target": tgt, "by_merge": own.get(tgt) if tgt else None, "time": t,
                        "own_time": reach[tgt][1] if tgt else None, "late": bool(tgt) and t > cut})
        commits[sha] = {"reverts": rec, "kinds": sorted({k for k, _ in ls}),
                        "brings_linked": any(own.get(k) == sha for k in links if k != sha)}
        if any(r["late"] for r in rec):
            late_commits.append(sha)
    merges: dict[str, list[str]] = defaultdict(list)       # a walk merge -> the commits it brings in that link
    for k in links:
        if k in own:
            merges[own[k]].append(k)
    return {"cut": cut, "commits": commits, "late": sorted(late_commits),
            "merges": {m: sorted(v) for m, v in merges.items()},
            "own_kinds": {m: sorted({k for k, _ in links.get(m, ())}) for m in merges}}


def late_strip(src: Path, dst: Path, late: list[str]) -> dict:
    """dst = src without the `issue_fix` rows of the given commits; the `meta` rows are kept"""
    shutil.copyfile(src, dst)
    con = sqlite3.connect(str(dst))
    try:
        gone = 0
        for s in late:
            gone += con.execute("delete from link where sha = ? and kind = 'issue_fix'", (s,)).rowcount
        con.commit()
        meta = dict(con.execute("select key, value from meta"))
        mode = con.execute("pragma journal_mode").fetchone()[0]
    finally:
        con.close()
    kept = meta.get("done") == "1" and meta.get("with_merges") == "1" and meta.get("sa3_links") == "1"
    return {"deleted_rows": gone, "commits": len(late), "meta_kept": kept, "journal_mode": mode}


def stage_prepare(a: dict, rundir: Path) -> dict:
    SR = U.sandbox_ro()
    PR = owner("prepare")
    repo = a["repo"]
    res = PR.stage_copy({"repo": repo}, rundir)            # the owner job's copy and its A' harvest, unchanged
    d = rundir / "db"
    detail = json.loads((rundir / "detail.json").read_text())
    stored = json.loads((SR.STUDY / "sa3_outcomes" / f"{repo}.json").read_text())
    rv = resolve_reverts(d / "harvest.db", d / "history.db", SR.POOL / repo, int(stored["cut"]))
    st = late_strip(d / "harvest.db", d / "harvest_late.db", rv["late"])
    (rundir / "late_detail.json").write_text(json.dumps(rv, indent=1) + "\n")
    return {"aprime": detail.get("aprime"), "late": st, "aprime_meta_kept": res["aprime_meta_kept"]}


def stage_build(a: dict, rundir: Path) -> dict:
    ref = Path(a["ref_tools"])
    sys.path.insert(0, str(ref))
    import sa3_outcomes as SO                              # the reference builder, from the code copy, unchanged
    assert Path(SO.__file__).resolve().parent == ref.resolve(), "the reference builder was not the copy"
    r = SO.build(a["repo"])
    (rundir / "outcome.json").write_text(json.dumps(r) + "\n")
    return {"build_status": r.get("status")}


STAGES = {"prepare": stage_prepare, "build": stage_build}


def stage_main(argv: list[str]) -> int:
    SR = U.sandbox_ro()
    SR.assert_inside_ro()                                  # first: the mount table, before any path is touched
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=sorted(STAGES))
    ap.add_argument("--rundir", type=Path, required=True)
    ap.add_argument("--args", type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    try:
        res = {"status": "ok", **STAGES[a.name](json.loads(a.args.read_text()), a.rundir)}
    except BaseException as e:                             # noqa: BLE001
        traceback.print_exc()
        res = {"status": "failed", "code": type(e).__name__}
    res["seconds"] = round(time.time() - t0, 1)
    (a.rundir / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0 if res["status"] == "ok" else 1


# ============================================================================================== the launcher
def check_decoy(p: Path) -> Path:
    """a decoy location: under ~/.claude/jobs or /tmp, outside every data root (a string test)"""
    SR = U.sandbox_ro()
    p = Path(os.path.abspath(p))
    if any(p == b or b in p.parents for b in SR.FORBIDDEN + (SR.PROJECTS,)) or \
            not any(a in p.parents for a in SR.ALLOWED_RW_ROOTS):
        raise SR.SandboxError(f"{p}: harvest variants run on decoys only; refused")
    return p


def code_copy(scratch: Path) -> Path:
    """this worktree's tools/ copied into scratch under a name that carries a hash of its contents (the worktree
    is hidden inside every sandbox; a stale copy is never reused)"""
    h = hashlib.sha256()
    files = sorted(p for p in U.TOOLS.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                   and p.suffix != ".pyc")
    for f in files:
        h.update(str(f.relative_to(U.TOOLS)).encode() + b"\0" + f.read_bytes())
    code = scratch / f"code-{h.hexdigest()[:12]}"
    if not (code / "tools").is_dir():
        shutil.copytree(U.TOOLS, code / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return code


class Layout:
    def __init__(self, study: Path, pool: Path, scratch: Path, linguist: Path | None = None):
        SR = U.sandbox_ro()
        P = U.phase_b()
        self.study, self.pool = check_decoy(Path(study)), check_decoy(Path(pool))
        self.scratch = SR.check_rw(Path(scratch))
        self.linguist = Path(linguist or P.LINGUIST_HOST)
        self.code = code_copy(self.scratch)


def _run(L: Layout, name: str, repo: str, rundir: Path, inputs: list, args: dict) -> dict:
    SR = U.sandbox_ro()
    P = U.phase_b()
    PR = owner("prepare")
    home, tmp = rundir / "home", rundir / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    P.write_gitconfig(home)
    (rundir / "args.json").write_text(json.dumps(args) + "\n")
    ins = list(inputs) + [(str(L.linguist / n), PR.LINGUIST_DST / n) for n in LISTS]
    spec = SR.Spec(rw=[rundir], code=[L.code], inputs=ins, clone=(repo, str(L.pool / repo)),
                   env={"LAWS_LINGUIST_DIR": str(PR.LINGUIST_DST)}, cwd=rundir)
    argv = ["/usr/bin/python3", "-I", "-B", str(L.code / "tools" / "compare" / "harvest_variant.py"), "stage", name,
            "--rundir", str(rundir), "--args", str(rundir / "args.json")]
    with open(rundir / "stage.log", "w") as log:
        try:
            rc = SR.run(argv, spec, home, tmp, timeout=PR.STAGE_TIMEOUT, stdout=log).returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    rf = rundir / "result.json"
    return json.loads(rf.read_text()) if rf.exists() else {"status": "failed", "code": f"no result (rc {rc})"}


def prepare(L: Layout, repo: str) -> dict:
    """the copies of one repo (fresh on every call): {"result", "dir", "late_detail"}"""
    PR = owner("prepare")
    rd = L.scratch / repo / "prepare"
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    res = _run(L, "prepare", repo, rd, PR.originals(L.study, repo), {"repo": repo})
    if res["status"] != "ok":
        raise RuntimeError(f"{repo}: prepare stage failed ({res.get('code')}); see {rd / 'stage.log'}")
    return {"result": res, "dir": rd, "late_detail": json.loads((rd / "late_detail.json").read_text())}


def build(L: Layout, repo: str, prep: dict, which: str) -> dict:
    """the reference builder, unchanged, on one harvest copy ('plain', 'case' or 'late'): the outcome file"""
    PR = owner("prepare")
    SR = U.sandbox_ro()
    db = prep["dir"] / "db"
    F = PR.study_files(L.study, repo)
    rd = L.scratch / repo / f"build_{which}"
    if rd.exists():
        shutil.rmtree(rd)
    rd.mkdir(parents=True)
    ins = [(str(db / "history.db"), F["history"][1]), (str(db / "scan_db.db"), F["scan_db"][1]), F["scan_sidecar"],
           (str(db / HARVEST[which]), SR.STUDY / "meta_sa3" / f"{repo}.db")]
    res = _run(L, "build", repo, rd, ins, {"repo": repo, "ref_tools": str(L.code / "tools")})
    if res["status"] != "ok":
        raise RuntimeError(f"{repo}: build stage failed ({res.get('code')}); see {rd / 'stage.log'}")
    return json.loads((rd / "outcome.json").read_text())


# ======================================================================================= comparing outcomes
def comparable(o: dict) -> dict:
    """an outcome file as compared: parsed JSON, the over-cap sample (which 20 of the over-cap merges a set
    iteration lists) left out; commit lists are objects, so their order is not compared"""
    o = json.loads(json.dumps(o))
    o.get("inheritance", {}).pop("over_cap", None)
    return o


def commit_diff(frozen: dict, rebuilt: dict) -> dict:
    """per commit list: the commits that left and the commits that joined, and for KW the files"""
    out = {}
    for oc in COMMIT_LISTS:
        a, b = set(frozen["outcomes"][oc]["commits"]), set(rebuilt["outcomes"][oc]["commits"])
        out[oc] = {"left": sorted(a - b), "joined": sorted(b - a)}
    a, b = set(frozen["outcomes"]["KW"]["files"]), set(rebuilt["outcomes"]["KW"]["files"])
    out["KW_files"] = {"left": sorted(a - b), "joined": sorted(b - a)}
    return out


def changed_commits(frozen: dict, rebuilt: dict) -> set[str]:
    d = commit_diff(frozen, rebuilt)
    return {s for oc in COMMIT_LISTS for side in ("left", "joined") for s in d[oc][side]}


def reorder(frozen: dict, rebuilt: dict) -> dict:
    """the rebuilt file with every commit list in the frozen file's order: commits also in the frozen list first,
    in its order; commits new to the variant after them, in the rebuilt file's (hash) order"""
    out = json.loads(json.dumps(rebuilt))
    for oc in COMMIT_LISTS:
        new = rebuilt["outcomes"][oc]["commits"]
        old = list(frozen["outcomes"][oc]["commits"])
        keep = [s for s in old if s in new] + [s for s in new if s not in frozen["outcomes"][oc]["commits"]]
        out["outcomes"][oc]["commits"] = {s: new[s] for s in keep}
    return out


def variant_outcomes(L: Layout, repos: list[str], which: str) -> dict:
    """{repo: {"deleted_rows", "rebuilt" (None: no row deleted, the frozen file stands), "late_detail"}}"""
    out = {}
    for r in repos:
        prep = prepare(L, r)
        key = "aprime" if which == "case" else "late"
        n = prep["result"][key]["deleted_rows"]
        rec = {"deleted_rows": n, "rebuilt": None, "late_detail": prep["late_detail"] if which == "late" else None}
        if n:
            rec["rebuilt"] = build(L, r, prep, which)
        out[r] = rec
        print(f"{r} {VARIANTS[which]} rows deleted {n}", flush=True)
    return out


QUALIFY = ("issue_fix", "cve", "trailer:fixes", "trailer:bug", "trailer:reported-by")


def validate_late(detail: dict, frozen: dict) -> dict:
    """decoys: the resolution against the reference's own split. For each unit commit of the frozen all-reverts
    outcome whose own links can qualify it only through a revert (no fix-reference, CVE or fix trailer row, and,
    for a merge, no commit it brings in carries a link), the reference puts it in the primary outcome exactly
    when one of its reverts qualifies; the resolution predicts that when one of its reverts resolves to a target
    at or before the cut. Likewise a merge with no link of its own that brings in exactly one linking commit,
    whose links can qualify it only through a revert (the merge is in the all-reverts outcome, so that commit's
    files meet the merge's). Returns the cases and every disagreement"""
    hp, allr = frozen["outcomes"]["HP"]["commits"], frozen["outcomes"]["HP_allreverts"]["commits"]
    cases, bad = [], []
    for sha, c in detail["commits"].items():
        if sha not in allr or set(c["kinds"]) & set(QUALIFY) or c["brings_linked"]:
            continue
        pred = any(r["target"] and not r["late"] for r in c["reverts"])
        case = {"sha": sha, "predicted_primary": pred, "reference_primary": sha in hp,
                "reverts": [{"resolved": bool(r["target"]), "late": r["late"], "by_merge": bool(r["by_merge"])}
                            for r in c["reverts"]]}
        cases.append(case)
        if pred != (sha in hp):
            bad.append(case)
    for m, kids in detail.get("merges", {}).items():      # a merge that inherits from exactly one commit
        if m not in allr or detail["own_kinds"].get(m) or len(kids) != 1:
            continue
        c = detail["commits"].get(kids[0])
        if c is None or set(c["kinds"]) & set(QUALIFY):
            continue
        pred = any(r["target"] and not r["late"] for r in c["reverts"])
        case = {"sha": m, "inherited_from": kids[0], "predicted_primary": pred, "reference_primary": m in hp,
                "reverts": [{"resolved": bool(r["target"]), "late": r["late"], "by_merge": bool(r["by_merge"])}
                            for r in c["reverts"]]}
        cases.append(case)
        if pred != (m in hp):
            bad.append(case)
    return {"cases": len(cases), "agree": len(cases) - len(bad), "disagreements": bad,
            "early": sum(c["predicted_primary"] for c in cases),
            "late_or_unresolved": sum(not c["predicted_primary"] for c in cases)}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "stage":
        return stage_main(argv[1:])
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("variant",))
    ap.add_argument("--study")
    ap.add_argument("--pool")
    ap.add_argument("--repos")
    ap.add_argument("--variant", choices=sorted(VARIANTS))
    ap.add_argument("--scratch")
    ap.add_argument("--out")
    ap.add_argument("--real", action="store_true")
    a = ap.parse_args(argv)
    if a.real:
        print("harvest_variant: real data is handled only inside the scoring job (a later specification); refused")
        return 2
    if not (a.study and a.pool and a.repos and a.variant and a.scratch and a.out):
        print("harvest_variant: --study, --pool, --repos, --variant, --scratch and --out are required")
        return 2
    L = Layout(Path(a.study), Path(a.pool), Path(a.scratch))
    res = variant_outcomes(L, a.repos.split(","), a.variant)
    out = U.sandbox_ro().check_rw(Path(a.out).parent) / Path(a.out).name
    out.write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
