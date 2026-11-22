#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Stored tables, phase B: SA3's data, predictor side only (docs/process/tables_phase_b_spec.md, Revision 2).

    python3 tools/tables/phase_b.py --decoy DIR --out OUT [--scratch S] [--repos a,b] [--preflight-only]
    python3 tools/tables/phase_b.py --real --i-am-the-reviewer-session --out OUT [--scratch S] [...]

With no target it refuses (exit 2). `--decoy DIR` is the ordinary mode: DIR holds `study/` (laid out like the
study directory), `pool/<repo>` clones and `docs/sa3_outcome_marginals.json` (and, optionally,
`docs/sa3_placebo.json`). `--real` needs the second flag; the real locations are parameters (`--real-study`,
`--real-pool`, `--real-docs`) whose defaults are the production paths. This launcher never opens, lists or stats
the study directory or the pool: it names their paths to bwrap only, and every look at them happens inside
tools/harness/sandbox_ro.py's sandbox, after that sandbox's guard has read the kernel's mount table and found the
study path, the pool and the clone mounted read-only.

Per repo, in its own sandboxes, with only that repo's declared inputs bound, read-only (nothing from
`sa3_outcomes/`, `meta_sa3/`, `meta_mod1/`, `dbs/` or any other repo):

  preflight  (all repos first) which inputs exist, SQLite header and side files, the clone's state
  copy       SHA-256 of each input; each database copied with its -wal/-shm/-journal into scratch, the copy
             opened (never the original), checkpointed and set to rollback mode
  tables     repo, snapshot, file, measure (phase A's builders, tools/tables/build.py) and the repo's counts
             (study_card.py), the copies bound where the originals were
  silence    count 1: sa3_score.load and silent as at edc5c53 and as at 8fb7fe0, each in its own sandbox and
             process, with a stub outcome file the job writes (silence.py)

From outside the job, in a read-only sandbox of its own, a stat manifest of every declared input and every
clone's .git is taken before and after (manifest_stat.py; the after is taken even when a stage crashes).

Writes OUT/: <repo>/<table>.<hash16>.jsonl, <repo>/index.json, <repo>/datacard.json, study_card.json,
study_card.md, preflight.json, run_log.json. The terminal gets `repo stage status` lines only; each stage's
output goes to a file under the scratch directory, never to OUT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS / "harness"))
import sandbox_ro as SR  # noqa: E402

WORKTREE = TOOLS.parent
VERSIONS = ("edc5c53", "8fb7fe0")
DOCS = Path("docs/")                       # (spelt with its slash: the bare word is one of laws_units' keywords)
LINGUIST_DST = SR.HOME / ".phaseb" / "linguist"          # in-sandbox (under the hidden home tmpfs)
LINGUIST_HOST = Path.home() / ".cache" / "temporal-crucible" / "linguist-e0c78d62c42a"
SIDE = ("-wal", "-shm", "-journal")
STAGE_TIMEOUT = 7200
HEADER = [
    "What a rehearsal on decoys cannot show (tables_phase_b_spec.md, 'Before the real run' item 3); for each the "
    "job fails safe with a recorded reason, and the preflight reports the inputs per repo before any table:",
    "the real layout's sizes (a stage that runs out of time or memory is recorded as failed for that repo)",
    "the earlier eight repos' later window start (the window start is the later of the cut and the snapshot's "
    "commit time; count 2 reports both)",
    "C-family repos with headers (the unit rule is the history's own; history.units is reported, count 10)",
    "whether the engine left side files beside the scan databases (preflight: header mode and side files; the "
    "copy stage carries them)",
]


# =============================================================================================== declared inputs
def declared(study: Path, repo: str, copies: Path | None = None) -> list[tuple[str, Path]]:
    """(host source, in-sandbox destination) of one repo's declared study files. With `copies` (the copy stage's
    directory), the two databases are the copies, in rollback mode, with no side file."""
    S = SR.STUDY
    out = []
    if copies is None:
        for sub, name in (("history", f"{repo}.db"), ("sa3_scans", f"{repo}_master.db")):
            out += [(str(study / sub / (name + sfx)), S / sub / (name + sfx)) for sfx in ("",) + SIDE]
    else:
        out += [(str(copies / "history.db"), S / "history" / f"{repo}.db"),
                (str(copies / "scan.db"), S / "sa3_scans" / f"{repo}_master.db")]
    out += [(str(study / "sa3_scans" / f"{repo}.json"), S / "sa3_scans" / f"{repo}.json"),
            (str(study / "sa3_nesting" / f"{repo}.json"), S / "sa3_nesting" / f"{repo}.json")]
    return out


def roles(repo: str) -> dict[str, Path]:
    """in-sandbox path of each declared input, by role"""
    S = SR.STUDY
    return {"history": S / "history" / f"{repo}.db", "scan_db": S / "sa3_scans" / f"{repo}_master.db",
            "scan_sidecar": S / "sa3_scans" / f"{repo}.json", "nesting": S / "sa3_nesting" / f"{repo}.json"}


DBS = ("history", "scan_db")


# ============================================================================================== in the sandbox
def listing() -> dict:
    """what the study path and the pool hold, seen from inside (names only)"""
    st = sorted(str(p.relative_to(SR.STUDY)) for p in SR.STUDY.rglob("*"))
    return {"study": st, "pool": sorted(os.listdir(SR.POOL))}


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=STAGE_TIMEOUT)
    if check and p.returncode:
        raise RuntimeError(f"git {args[0]}: exit {p.returncode}: {p.stderr.decode('utf-8', 'replace')[:200]}")
    return p


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def db_header(p: Path) -> dict:
    """SQLite's header read as bytes (the file is never opened by SQLite): bytes 18 and 19 are 1 for rollback
    mode, 2 for write-ahead mode; and the side files beside it"""
    with open(p, "rb") as fh:
        head = fh.read(100)
    mode = {(1, 1): "rollback", (2, 2): "wal"}.get((head[18], head[19]), f"{head[18]},{head[19]}") \
        if len(head) == 100 and head.startswith(b"SQLite format 3\0") else "not sqlite"
    return {"mode": mode, "size": p.stat().st_size,
            **{sfx.lstrip("-"): (Path(str(p) + sfx).stat().st_size if Path(str(p) + sfx).exists() else None)
               for sfx in SIDE}}


def clone_state(repo: str, snap: str | None) -> dict:
    c = SR.POOL / repo
    if not c.is_dir():
        return {"present": False}
    gd = c / ".git"
    out = {"present": True, "git_dir": "directory" if gd.is_dir() else ("file (a linked worktree)" if gd.is_file()
                                                                        else "none (bare?)")}
    g = gd if gd.is_dir() else c
    out["alternates"] = (g / "objects" / "info" / "alternates").exists()
    out["commondir"] = (g / "commondir").exists()
    out["shallow"] = (g / "shallow").exists()
    out["packs"] = len(list((g / "objects" / "pack").glob("*.pack"))) if (g / "objects" / "pack").is_dir() else 0
    pc = git(c, "config", "--get", "extensions.partialclone", check=False).stdout.decode().strip()
    prom = git(c, "config", "--get-regexp", r"^remote\..*\.promisor$", check=False).stdout.decode().split()
    out["partial_clone"] = bool(pc) or "true" in prom[1::2]
    out["promisor_packs"] = (len(list((g / "objects" / "pack").glob("*.promisor")))
                             if (g / "objects" / "pack").is_dir() else 0)
    out["head_resolves"] = git(c, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0
    if snap:
        out["snapshot_commit_present"] = git(c, "cat-file", "-e", f"{snap}^{{commit}}", check=False).returncode == 0
        out["snapshot_tree_lists"] = git(c, "ls-tree", "-r", "--name-only", snap, check=False).returncode == 0
    return out


def stage_preflight(repo: str) -> dict:
    """report only: nothing is opened by SQLite, nothing is written but the result"""
    rp = roles(repo)
    res = {"inputs": {k: ({"exists": True, "size": p.stat().st_size} if p.exists() else {"exists": False})
                      for k, p in rp.items()},
           "databases": {k: db_header(rp[k]) for k in DBS if rp[k].exists()}}
    snap = None
    if rp["scan_sidecar"].exists():
        try:
            snap = json.loads(rp["scan_sidecar"].read_text()).get("snapshot")
        except ValueError:
            res["sidecar"] = "does not parse"
    res["clone"] = clone_state(repo, snap)
    res["listing"] = listing()
    return res


def stage_copy(repo: str, rundir: Path) -> dict:
    """hash every input; copy each database with its side files; open the COPY (never the original), checkpoint
    it and set it to rollback mode, so it can be read from a read-only bind with no side file"""
    rp = roles(repo)
    res = {"sha256": {}, "copies": {}}
    for k, p in rp.items():
        if p.exists():
            res["sha256"][k] = sha256_file(p)
            for sfx in SIDE:
                if Path(str(p) + sfx).exists():
                    res["sha256"][k + sfx] = sha256_file(Path(str(p) + sfx))
    d = rundir / "db"
    d.mkdir(exist_ok=True)
    for k, name in (("history", "history.db"), ("scan_db", "scan.db")):
        src = rp[k]
        if not src.exists():
            res["copies"][k] = {"copied": False, "reason": "input absent"}
            continue
        before = db_header(src)
        dst = d / name
        shutil.copyfile(src, dst)
        for sfx in SIDE:
            if Path(str(src) + sfx).exists():
                shutil.copyfile(str(src) + sfx, str(dst) + sfx)
        con = sqlite3.connect(str(dst))                          # the copy, read-write, in scratch
        try:
            mode = con.execute("pragma journal_mode").fetchone()[0]
            if mode == "wal":
                con.execute("pragma wal_checkpoint(TRUNCATE)")
            new = con.execute("pragma journal_mode=DELETE").fetchone()[0]
            qc = con.execute("pragma quick_check").fetchone()[0]
        finally:
            con.close()
        left = [sfx for sfx in SIDE if Path(str(dst) + sfx).exists()]
        res["copies"][k] = {"copied": True, "original": before, "copy_mode_before": mode, "copy_mode_after": new,
                            "quick_check": qc, "side_files_left": left}
    return res


def archive_listing(clone: Path, snap: str) -> tuple[set[str] | None, str | None]:
    """the files `git archive` of the snapshot holds, streamed (never held in memory whole); None with the reason
    when git fails (a tree-only clone): the exit code is checked, unlike universe()'s own archive call"""
    import tarfile
    p = subprocess.Popen(["git", "-C", str(clone), "archive", snap], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    names: set[str] = set()
    err = None
    try:
        with tarfile.open(fileobj=p.stdout, mode="r|") as tf:
            for m in tf:
                if not m.isdir():
                    names.add(m.name)
    except tarfile.TarError as e:
        err = f"tar: {type(e).__name__}"
    rc = p.wait(timeout=STAGE_TIMEOUT)
    msg = p.stderr.read().decode("utf-8", "replace")[:200]
    if rc or err:                          # object names in git's message are not kept (a card holds no hash)
        msg = re.sub(r"\b[0-9a-f]{40}\b", "<object>", msg.strip())
        return None, f"git archive exit {rc}: {msg or err}"
    return names, None


def tree_modes(clone: Path, snap: str) -> Counter:
    out: Counter = Counter()
    for ent in git(clone, "ls-tree", "-r", "-z", "--full-tree", snap).stdout.split(b"\0"):
        if ent:
            out[ent.split(b" ", 1)[0].decode()] += 1
    return out


def generic_dirs(U, side: dict, file_rows: list[dict], langs, patterns: list[str]) -> dict:
    """count 5 (PU_generic_dirs_restored): files of the repo's language whose verdict is `vendored` with every
    rule, and no exclusion at all once the four registered patterns are taken out of laws_units' own compiled
    vendored list (the Excluder's `vendor` attribute; no rule is restated). Per pattern: those it matches."""
    import re as _re
    ex = U.Excluder(side["attrs"], include_tutorials=True)
    have = [x.pattern for x in ex.vendor]
    missing = [p for p in patterns if p not in have]
    if missing:
        raise RuntimeError(f"registered pattern(s) not in GitHub's vendored list: {missing}")
    ex_r = U.Excluder(side["attrs"], include_tutorials=True)
    ex_r.vendor = [x for x in ex_r.vendor if x.pattern not in patterns]
    gen = set(side["generated"])
    comp = {p: _re.compile(p) for p in patterns}
    per = {p: {"excluded_only_by": 0, "with_scan_rows": 0} for p in patterns}
    anyp = {"excluded_only_by": 0, "with_scan_rows": 0}
    for r in file_rows:
        if r["language"] not in langs or r["reason"] != "vendored":
            continue
        if ex_r.why(r["path"], r["path"] in gen) is not None:
            continue
        anyp["excluded_only_by"] += 1
        anyp["with_scan_rows"] += int(bool(r["scanned"]))
        for p, rx in comp.items():
            if rx.search(r["path"]):
                per[p]["excluded_only_by"] += 1
                per[p]["with_scan_rows"] += int(bool(r["scanned"]))
    return {**per, "_any": anyp}


def invariant_counts(fails: list[str]) -> dict[int, int]:
    """'invariant N: ...' lines -> {N: failing rows}, counting the '... and K more rows' line as K"""
    out: Counter = Counter()
    for x in fails:
        m = re.match(r"invariant (\d+): (.*)", x)
        if not m:
            continue
        n = int(m.group(1))
        more = re.fullmatch(r"\.\.\. and (\d+) more rows", m.group(2))
        prot = re.match(r"(\d+) rows? of protected table", m.group(2))
        out[n] += int(more.group(1)) if more else int(prot.group(1)) if prot else 1
    return dict(sorted(out.items()))


NOT_APPLICABLE = (4, 5, 6)      # need touch, event, pool, marginal: not built in phase B
NOT_BLOCKING = (7,)             # the window check is count 3 (PU_window_assertion), reported, not a build stop


def stage_tables(repo: str, rundir: Path, out: Path, args: dict) -> dict:
    os.environ.setdefault("PHASEB_SANDBOX", "1")
    import build as B                      # guards again (sandbox_ro) before any SA3 import
    import study_card as K
    L, O, U, S, C, I = B.L, B.O, B.U, B.S, B.C, B.I
    assert tuple(B.SC.COLS[:-1]) == S.SCAN_COLS and B.SC.COLS[-1] == "mitigation_telemetry", \
        "sa3_score.COLS no longer matches schema.SCAN_COLS"
    r = repo
    rp = roles(r)
    res: dict = {"listing": listing()}
    side = json.loads(rp["scan_sidecar"].read_text())
    snap = side["snapshot"]
    f = L.frame(r)
    files, u = O.universe(r, f["langs"])
    h = L.ro(rp["history"])
    hmeta = dict(h.execute("select key, value from meta"))
    walk = [(s, ct, m) for s, ct, m in h.execute("select sha, ct, merge from commit_ order by rowid")]
    h.close()
    clone = SR.POOL / r
    tree = B.tree_paths(clone, snap)
    modes = tree_modes(clone, snap)
    arch, arch_err = archive_listing(clone, snap)
    scan = B.read_scan(r, rp["scan_db"], side)
    touch_err = None
    tmp = rundir / "tmp" / "snap"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        touchable = B.history_touchable(clone, snap, hmeta["language"], hmeta.get("units") == "c+cpp", tmp)
    except Exception as e:                                       # recorded, never hidden
        touchable, touch_err = None, f"{type(e).__name__}: {str(e)[:200]}"
    file_rows = B.file_table(r, f["langs"], files, side, scan, tree, arch, touchable)
    in_tree = set(tree)
    nest = json.loads(rp["nesting"].read_text()) if rp["nesting"].exists() else {}
    measure_rows = B.measure_table(r, side, scan, in_tree, files, nest)
    sp = git(clone, "show", "-s", "--format=%ct", snap, check=False)
    snap_ct = int(sp.stdout.decode().strip()) if sp.returncode == 0 and sp.stdout.strip() else None
    tip = git(clone, "rev-parse", "HEAD", check=False)
    pool_tip = tip.stdout.decode().strip() if tip.returncode == 0 else None
    # Amendment 1 rule 10 as Amendment 5 section 5 states it: the later of the cut and the scanned snapshot
    window_start = None if snap_ct is None else max(f["cut"], snap_ct)
    m = args.get("marginal") or {}
    oc = {"status": m.get("status"), "why": m.get("why"), "unit_files": u["unit_files"],
          "complete": u["complete"] if arch is not None else None,
          "tree_unit_files": u["tree_unit_files"] if arch is not None else None}
    repo_row = B.repo_row(r, hmeta, f, side, oc, pool_tip, walk, scan, in_tree)
    snap_row = B.snapshot_row(r, snap, snap_ct, f, window_start)
    tables = {"repo": [repo_row], "snapshot": [snap_row], "file": file_rows, "measure": measure_rows}
    empty = {n: [] for n in ("touch", "link", "event", "pool", "marginal")}
    fails = [x for x in I.check({**tables, **empty}, tree)
             if int(re.match(r"invariant (\d+)", x).group(1)) not in NOT_APPLICABLE]
    (rundir / "invariant_messages.txt").write_text("\n".join(fails) + "\n")   # scratch only: predictor-side keys
    inv = invariant_counts(fails)
    res["invariants"] = inv
    blocking = {n: c for n, c in inv.items() if n not in NOT_BLOCKING}
    lsha = {n: sha256_file(LINGUIST_DST / n) for n in ("vendor.yml", "documentation.yml")}
    generic = generic_dirs(U, side, file_rows, f["langs"], args["patterns"])
    counts = K.repo_counts(r, file_rows=file_rows, measure_rows=measure_rows, repo_row=repo_row, snap_row=snap_row,
                           frame=f, universe_meta=u, archive_ok=arch is not None, archive_error=arch_err,
                           touch_ok=touchable is not None, tree_modes=modes, side=side, hmeta=hmeta, nest=nest,
                           linguist_sha256=lsha, laws_units_linguist=U.LINGUIST, generic=generic, marginal=m or None)
    counts["invariants_failed"] = inv
    od = out / r
    od.mkdir(parents=True, exist_ok=True)
    (od / "datacard.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    if blocking:
        res.update({"status": "tables not written", "reason": f"invariants failed: {blocking}"})
        return res
    index = {"repo": r, "schema_version": S.SCHEMA_VERSION, "phase": "B (predictor side only)",
             "inputs_sha256": args.get("sha256"), "code_sha256": args.get("code_sha256"),
             "pool_clone_tip": pool_tip, "snapshot": snap, "linguist_commit": U.LINGUIST,
             "archive": "available" if arch is not None else "unavailable", "archive_error": arch_err,
             "history_can_touch": "computed" if touchable is not None else f"not computed: {touch_err}",
             "bound_study_files": res["listing"]["study"],
             "not_built": "touch, link, event, pool, marginal (the owner-run job)", "tables": {}}
    for name in ("repo", "snapshot", "file", "measure"):
        index["tables"][name] = C.write_table(od, name, tables[name])
    (od / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    res.update({"status": "ok", "tables": {n: t["hash"] for n, t in index["tables"].items()},
                "archive": index["archive"], "history_can_touch": index["history_can_touch"]})
    return res


def stage_main(argv: list[str]) -> int:
    """`phase_b.py stage NAME --repo R --rundir D [--out O] [--args FILE]`: runs inside the sandbox only"""
    SR.assert_inside_ro()                          # first: the mount table, before any path is touched
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=("preflight", "copy", "tables", "listing"))
    ap.add_argument("--repo", required=True)
    ap.add_argument("--rundir", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--args", type=Path)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    sys.path.insert(1, str(TOOLS))
    extra = json.loads(a.args.read_text()) if a.args else {}
    t0 = time.time()
    try:
        if a.name == "preflight":
            res = {"status": "ok", **stage_preflight(a.repo)}
        elif a.name == "copy":
            res = {"status": "ok", **stage_copy(a.repo, a.rundir)}
        elif a.name == "listing":
            res = {"status": "ok", "listing": listing()}
        else:
            res = stage_tables(a.repo, a.rundir, a.out, extra)
    except Exception as e:                         # the stage is recorded with its reason; the run continues
        import traceback
        traceback.print_exc()
        res = {"status": "failed", "reason": f"{type(e).__name__}: {str(e)[:300]}"}
    res["seconds"] = round(time.time() - t0, 1)
    (a.rundir / "result.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    return 0 if res.get("status") in ("ok", "tables not written") else 1


# ==================================================================================================== launcher
class Target:
    def __init__(self, study: Path, pool: Path, docs: Path, real: bool):
        self.study, self.pool, self.docs, self.real = study, pool, docs, real


def resolve_target(a) -> Target:
    if a.decoy and a.real:
        raise SystemExit("phase_b: --decoy and --real together; refused")
    if a.real:
        if not a.i_am_the_reviewer_session:
            raise SystemExit("phase_b: --real needs --i-am-the-reviewer-session; refused")
        return Target(Path(a.real_study), Path(a.real_pool), Path(a.real_docs), True)
    if a.decoy:
        d = Path(os.path.abspath(a.decoy))
        for bad in SR.FORBIDDEN + (SR.PROJECTS,):
            if d == bad or bad in d.parents:
                raise SystemExit(f"phase_b: a decoy may not be inside {bad}; refused")
        return Target(d / "study", d / "pool", d / DOCS, False)
    raise SystemExit("phase_b: no target. Use --decoy DIR (a decoy built from control repositories), or --real "
                     "--i-am-the-reviewer-session; refused")


def stage_spec(code: Path, rundir: Path, inputs: list, clone: tuple | None, extra_rw: list[Path] = (),
               linguist: Path | None = None) -> SR.Spec:
    ins = list(inputs)
    if linguist is not None:
        ins += [(str(linguist / n), LINGUIST_DST / n) for n in ("vendor.yml", "documentation.yml")]
    return SR.Spec(rw=[rundir, *extra_rw], code=[code], inputs=ins, clone=clone,
                   env={"LAWS_LINGUIST_DIR": str(LINGUIST_DST)}, cwd=rundir)


def write_gitconfig(home: Path) -> None:
    (home / ".gitconfig").write_text("[gc]\n\tauto = 0\n[maintenance]\n\tauto = false\n[user]\n\tname = phase-b\n"
                                     "\temail = phase-b@invalid\n[safe]\n\tdirectory = *\n")


def run_stage(name: str, repo: str, scratch: Path, spec: SR.Spec, rundir: Path, code: Path, out: Path | None = None,
              args: dict | None = None) -> dict:
    home, tmp = rundir / "home", rundir / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    write_gitconfig(home)
    argv = ["/usr/bin/python3", "-I", "-B", str(code / "tools" / "tables" / "phase_b.py"), "stage", name,
            "--repo", repo, "--rundir", str(rundir)]
    if out is not None:
        argv += ["--out", str(out)]
    if args is not None:
        (rundir / "args.json").write_text(json.dumps(args) + "\n")
        argv += ["--args", str(rundir / "args.json")]
    with open(rundir / "stage.log", "w") as log:
        try:
            p = SR.run(argv, spec, home, tmp, timeout=STAGE_TIMEOUT, stdout=log)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
    rf = rundir / "result.json"
    res = json.loads(rf.read_text()) if rf.exists() else {"status": "failed",
                                                          "reason": f"stage wrote no result (rc {rc}); see scratch"}
    res["rc"] = rc
    return res


def prepare_code(scratch: Path) -> dict:
    """The code the sandboxes run, copied in before any stage (the worktree is hidden inside): this worktree's
    tools/ (phase A and B code, the SA3 tools) and every tools/*.py as at edc5c53 and at 8fb7fe0 (silence.py)."""
    import silence as SL
    code = scratch / "code"
    wt = code / "wt"
    shutil.copytree(WORKTREE / "tools", wt / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    sums = {"wt": {str(p.relative_to(wt)): sha256_file(p) for p in sorted((wt / "tools").rglob("*.py"))}}
    for v in VERSIONS:
        sums[v] = SL.extract(WORKTREE, v, code / v)
    (scratch / "code_sha256.json").write_text(json.dumps(sums, indent=1) + "\n")
    return sums


def generic_patterns() -> list[str]:
    """The four patterns of PU_generic_dirs_restored, read from the registration's own row (Amendment 5
    section 6); each is checked against GitHub's list inside the sandbox"""
    text = (WORKTREE / DOCS / "sa3_registration.md").read_text()
    row = next(ln for ln in text.splitlines() if ln.startswith("| `PU_generic_dirs_restored`"))
    pats = [x for x in re.findall(r"`([^`]+)`", row) if x.startswith("(^")]
    if len(pats) != 4:
        raise SystemExit(f"phase_b: expected four patterns in the registration's PU_generic_dirs_restored row, "
                         f"found {pats}")
    return pats


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["stage"]:
        return stage_main(argv[1:])
    ap = argparse.ArgumentParser(description="stored tables, phase B (predictor side)")
    ap.add_argument("--decoy", help="a decoy directory: study/, pool/, docs/")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--i-am-the-reviewer-session", action="store_true")
    ap.add_argument("--real-study", default=str(SR.STUDY))
    ap.add_argument("--real-pool", default=str(SR.POOL))
    ap.add_argument("--real-docs", default=str(WORKTREE / DOCS))
    ap.add_argument("--linguist", default=str(LINGUIST_HOST), help="GitHub's two cached lists")
    ap.add_argument("--out", required=False)
    ap.add_argument("--scratch")
    ap.add_argument("--repos", help="comma-separated subset, in the marginals file's order")
    ap.add_argument("--preflight-only", action="store_true")
    a = ap.parse_args(argv)
    try:
        tgt = resolve_target(a)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    if not a.out:
        print("phase_b: --out is required; refused", file=sys.stderr)
        return 2
    try:
        out = SR.check_rw(Path(a.out))
        scratch = SR.check_rw(Path(a.scratch or (str(out) + ".scratch")))
    except SR.SandboxError as e:
        print(f"phase_b: {e}", file=sys.stderr)
        return 2
    if out.exists() or scratch.exists():
        print(f"phase_b: {out} or {scratch} already exists; a run writes a new directory; refused", file=sys.stderr)
        return 2
    return launch(tgt, out, scratch, Path(a.linguist), a.repos.split(",") if a.repos else None, a.preflight_only)


def launch(tgt: Target, out: Path, scratch: Path, linguist: Path, only: list[str] | None,
           preflight_only: bool) -> int:
    import manifest_stat as MS
    import silence as SL
    import study_card as K
    out.mkdir(parents=True)
    scratch.mkdir(parents=True)
    log = {"header": HEADER, "target": "real" if tgt.real else "decoy", "started": int(time.time()),
           "repos": {}, "manifest": None}

    def save():
        (out / "run_log.json").write_text(json.dumps(log, indent=1, default=str) + "\n")

    marg_rows = json.loads((tgt.docs / "sa3_outcome_marginals.json").read_text())
    marginals = {}
    for row in marg_rows:                     # public, frozen: status, why, drawn, clears_floor only are used
        name = row["repo"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", name):
            raise SystemExit(f"phase_b: repo name {name!r} refused")
        marginals[name] = {"status": row.get("status"), "why": row.get("why"), "drawn": row.get("drawn"),
                           **{oc: {"clears_floor": (row.get(oc) or {}).get("clears_floor")}
                              for oc in ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW")}}
    repos = [r for r in marginals if only is None or r in only]
    placebo_f = tgt.docs / "sa3_placebo.json"
    placebo = json.loads(placebo_f.read_text()) if placebo_f.is_file() else None
    sums = prepare_code(scratch)
    log["code_sha256_file"] = "scratch/code_sha256.json"
    code = scratch / "code" / "wt"
    patterns = generic_patterns()
    log["generic_patterns"] = patterns
    save()
    rc_total = 0
    before = MS.take(tgt.study, tgt.pool, repos, scratch / "manifest_before.json", scratch / "ms_before", code)
    try:
        pre = {}
        for r in repos:                                           # preflight first, on all repos
            rd = scratch / r / "preflight"
            rd.mkdir(parents=True)
            spec = stage_spec(code, rd, declared(tgt.study, r), (r, str(tgt.pool / r)))
            res = run_stage("preflight", r, scratch, spec, rd, code)
            pre[r] = {k: v for k, v in res.items() if k != "listing"}
            log["repos"][r] = {"preflight": {"rc": res["rc"], "status": res.get("status"),
                                             "reason": res.get("reason")}}
            print(f"{r} preflight {res.get('status')}", flush=True)
        (out / "preflight.json").write_text(json.dumps(pre, indent=1, default=str) + "\n")
        save()
        if preflight_only:
            return 0
        per_repo, silence_res = {}, {}
        stubs = scratch / "stubs"
        stubs.mkdir()
        for r in repos:
            L = log["repos"][r]
            rd = scratch / r / "copy"
            rd.mkdir(parents=True)
            spec = stage_spec(code, rd, declared(tgt.study, r), None)
            cp = run_stage("copy", r, scratch, spec, rd, code)
            L["copy"] = {"rc": cp["rc"], "status": cp.get("status"), "reason": cp.get("reason"),
                         "copies": cp.get("copies")}
            print(f"{r} copy {cp.get('status')}", flush=True)
            if cp.get("status") != "ok":
                per_repo[r] = {"status": f"copy failed: {cp.get('reason')}"}
                rc_total = 1
                continue
            copies = rd / "db"
            rt = scratch / r / "tables"
            rt.mkdir(parents=True)
            (out / r).mkdir()
            spec = stage_spec(code, rt, declared(tgt.study, r, copies), (r, str(tgt.pool / r)), [out / r],
                              linguist)
            tb = run_stage("tables", r, scratch, spec, rt, code, out=out,
                           args={"marginal": marginals.get(r), "patterns": patterns, "sha256": cp.get("sha256"),
                                 "code_sha256": hashlib.sha256(json.dumps(sums, sort_keys=True).encode()).hexdigest()})
            L["tables"] = {k: tb.get(k) for k in ("rc", "status", "reason", "invariants", "tables", "archive",
                                                   "history_can_touch", "seconds")}
            print(f"{r} tables {tb.get('status')}", flush=True)
            dc = out / r / "datacard.json"
            per_repo[r] = json.loads(dc.read_text()) if dc.exists() else {"status": f"tables: {tb.get('reason')}"}
            if tb.get("status") != "ok":
                rc_total = 1
            silence_res[r] = {}
            for v in VERSIONS:
                rs = scratch / r / f"silence_{v}"
                rs.mkdir(parents=True)
                sres = SL.run_one(r, v, scratch, rs, copies, tgt.study, linguist, stubs)
                silence_res[r][v] = {k: sres[k] for k in ("silent", "error", "n", "predictors", "confirmatory")
                                     if k in sres}
                L[f"silence_{v}"] = {"rc": sres.get("rc"), "status": "ok" if "silent" in sres else "failed",
                                     "reason": sres.get("error")}
                print(f"{r} silence {v} {'ok' if 'silent' in sres else 'failed'}", flush=True)
            save()
        consts = next((v for r in silence_res.values() for v in [r.get(VERSIONS[1], {})] if "predictors" in v), None)
        c1 = K.count_1(silence_res, marginals, consts["predictors"], tuple(consts["confirmatory"]),
                       SL.SCORED_OUTCOMES) if consts else None
        pc = K.placebo_check(silence_res, placebo)
        sc = K.card(per_repo, c1, pc, {"target": log["target"], "repos": repos})
        (out / "study_card.json").write_text(json.dumps(sc, indent=1, sort_keys=True, default=str) + "\n")
        (out / "study_card.md").write_text(K.markdown(sc))
    finally:
        after = MS.take(tgt.study, tgt.pool, repos, scratch / "manifest_after.json", scratch / "ms_after", code)
        diff = MS.compare(before, after) if before.get("ok") and after.get("ok") else None
        log["manifest"] = {"before": before.get("status"), "after": after.get("status"),
                           "unchanged": None if diff is None else not any(diff.values()),
                           "added": None if diff is None else len(diff["added"]),
                           "removed": None if diff is None else len(diff["removed"]),
                           "changed": None if diff is None else len(diff["changed"]),
                           "details": "scratch/manifest_diff.json"}
        if diff is not None:
            (scratch / "manifest_diff.json").write_text(json.dumps(diff, indent=1) + "\n")
        if diff is None or any(diff.values()):
            rc_total = 3
            print("MANIFEST: the declared inputs or a clone changed during the run, or a manifest failed",
                  flush=True)
        log["finished"] = int(time.time())
        save()
    return rc_total


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(main())
