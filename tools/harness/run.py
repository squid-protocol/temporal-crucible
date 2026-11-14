#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Run the existing, unmodified SA3 pipeline on one control repository, inside the sandbox (harness_spec.md).

    python tools/harness/run.py --control DIR --work WORK [--name NAME] [--routes own,manifest] [--no-shim-lock]

DIR holds `repo/` and `manifest.json` (tools/control_repo/generate.py). Two routes, each in its own sandbox WORK:

  own        the pipeline chooses its snapshot: mod1_run (history walk, MOD-1 body harvest, the cut, the
             laws_build scan of the cut) -> mod1_lift (writes docs/mod1/lift_NAME.json) -> sa3_scan (reads it)
  manifest   the manifest's snapshot is handed in: laws_history (exactly as mod1_run calls it) ->
             sa3_scan --sha <points.snapshot.hash>

then, on both: sa3_outcomes (which runs hist_meta) -> sa3_nest_scan -> the marginals file (the harness writes it
from the outcome file; no tool does) -> sa3_score placebo -> sa3_score lock -> sa3_score score -> the probe
(tools/harness/probe.py, which reads the results through the tools' own functions). Every stage runs in the
sandbox through its guard; a stage that fails stops its route and is recorded with its output. Outputs:
WORK/<route>/ (the sandbox WORKs), WORK/report/NAME.json and NAME.md (tools/harness/compare.py).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox as SB  # noqa: E402

WORKTREE = SB.WORKTREE
PY = "/usr/bin/python3"
SEALED_DOCS = ("sa3_registration_consolidated.md", "sa3_power.md")    # sealed docs the scorer reads/hashes
STAGE_TIMEOUT = 3600


@dataclass
class Ctx:
    work: Path                      # this route's sandbox WORK
    name: str                       # the repo name the tools see (a clone under WORK/pool)
    log: list = field(default_factory=list)

    @property
    def tree(self) -> Path:
        return self.work / "tree"

    @property
    def study(self) -> Path:
        return self.work / "study"

    @classmethod
    def for_test(cls, work: Path) -> "Ctx":
        return cls(work=Path(work), name="test")


def stage(ctx: Ctx, label: str, argv: list[str], sandboxed: bool = True, timeout: float = STAGE_TIMEOUT) -> dict:
    """Run one pipeline stage. sandboxed=True: inside bwrap, through the in-sandbox guard. sandboxed=False is
    allowed only when this process is itself already inside the sandbox; anywhere else it is refused before
    anything runs."""
    if not sandboxed:
        SB.assert_inside(ctx.work)                     # raises outside the sandbox
        t0 = time.time()
        p = subprocess.run(argv, capture_output=True, text=True, cwd=ctx.tree, timeout=timeout)
    else:
        t0 = time.time()
        p = SB.run(argv, ctx.work, cwd=ctx.tree, timeout=timeout)
    rec = {"stage": label, "argv": argv, "rc": p.returncode, "seconds": round(time.time() - t0, 1),
           "stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]}
    ctx.log.append(rec)
    print(f"  [{ctx.work.name}] {label}: rc={p.returncode} {rec['seconds']}s "
          f"{(p.stdout.strip().splitlines() or [''])[-1][:160]}", flush=True)
    return rec


def setup(work: Path, name: str, control: Path) -> Ctx:
    """A fresh sandbox WORK: a copy of tools/ and of the sealed docs under tree/, the clone under pool/,
    linguist's lists under home/."""
    if work.exists():
        shutil.rmtree(work)
    SB.prepare(work)
    ctx = Ctx(work=work, name=name)
    shutil.copytree(WORKTREE / "tools", ctx.tree / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    (ctx.tree / "docs" / "mod1").mkdir(parents=True, exist_ok=True)
    for d in SEALED_DOCS:
        shutil.copyfile(WORKTREE / "docs" / d, ctx.tree / "docs" / d)
    if not SB.copy_linguist_cache(work):
        raise SystemExit("linguist cache absent under ~/.cache: laws_units would fetch it, and the sandbox has no "
                         "network. Stopping before any stage.")
    shutil.copytree(control / "repo", work / "pool" / name, symlinks=True)
    return ctx


def write_marginals(ctx: Ctx) -> dict:
    """docs/sa3_outcome_marginals.json, which no tool writes: one row built from the outcome file's own values
    (status, clears_floor, counts), in the shape of the frozen file."""
    o = json.loads((ctx.study / "sa3_outcomes" / f"{ctx.name}.json").read_text())
    row = {"repo": ctx.name, "drawn": True, "status": o["status"], "why": o.get("why"),
           "language": o.get("language"), "family": o.get("family"), "merge_units": o.get("merge_units"),
           "unit_files": o.get("unit_files"), "complete": o.get("complete"), "window_days": o.get("window_days")}
    for oc in ("HP", "HP_allreverts", "HP_revert", "HP_cve", "HP_fixref", "KW"):
        v = o.get("outcomes", {}).get(oc, {})
        row[oc] = {k: v.get(k) for k in ("n_files", "n_commits", "largest_commit_share")} | \
                  {"clears_floor": bool(v.get("clears_floor", False))}
    pool = o.get("outcomes", {}).get("control_pool", {})
    row["control_pool_commits"] = pool.get("n_commits")
    row["inheritance"] = {k: v for k, v in o.get("inheritance", {}).items() if k != "over_cap"}
    (ctx.tree / "docs" / "sa3_outcome_marginals.json").write_text(json.dumps([row], indent=1) + "\n")
    return row


def tail(ctx: Ctx, out: dict, placeholder_review: bool) -> None:
    """sa3_outcomes -> nesting -> marginals -> placebo -> lock -> score -> probe. Stops at the first failure,
    except that lock/score refusing is the expected stop and the probe still runs."""
    n = ctx.name
    r = stage(ctx, "sa3_outcomes", [PY, "-B", "tools/sa3_outcomes.py", "--repo", n])
    of = ctx.study / "sa3_outcomes" / f"{n}.json"
    if r["rc"] or not of.exists():
        out["stopped_at"] = "sa3_outcomes"
        return
    r = stage(ctx, "sa3_nest_scan", [PY, "-B", "tools/sa3_nest_scan.py", "--repo", n])
    if r["rc"]:
        out["stopped_at"] = "sa3_nest_scan"
        return
    out["marginals"] = write_marginals(ctx)
    r = stage(ctx, "sa3_score placebo", [PY, "-B", "tools/sa3_score.py", "placebo"])
    out["placebo_rc"] = r["rc"]
    r = stage(ctx, "sa3_score lock", [PY, "-B", "tools/sa3_score.py", "lock"])
    out["lock"] = {"rc": r["rc"], "said": r["stdout"].strip()[-500:]}
    r = stage(ctx, "sa3_score score", [PY, "-B", "tools/sa3_score.py", "score"])
    out["score"] = {"rc": r["rc"], "said": r["stdout"].strip()[-500:]}
    if placeholder_review and out["lock"]["rc"]:
        # SHIM (DECISIONS.md): a placeholder code-review document, to see what lock and score do past that stop
        (ctx.tree / "docs" / "sa3_code_review.md").write_text(
            "# PLACEHOLDER written by tools/harness/run.py -- not a code review\n\nThis file exists only so that "
            "`sa3_score.py lock` can be observed past its missing-file check on a control repository.\n")
        r = stage(ctx, "sa3_score lock (placeholder review)", [PY, "-B", "tools/sa3_score.py", "lock"])
        out["lock_with_placeholder"] = {"rc": r["rc"], "said": r["stdout"].strip()[-500:]}
        r = stage(ctx, "sa3_score score (placeholder review)", [PY, "-B", "tools/sa3_score.py", "score"])
        out["score_with_placeholder"] = {"rc": r["rc"], "said": r["stdout"].strip()[-800:],
                                         "err": r["stderr"].strip()[-1500:]}
    r = stage(ctx, "probe", [PY, "-B", "tools/harness/probe.py", "--repo", n, "--out", str(ctx.work / "probe.json")])
    out["probe_rc"] = r["rc"]
    if r["rc"]:
        out["stopped_at"] = "probe"


def route_own(ctx: Ctx, lang: str, out: dict, placeholder_review: bool) -> None:
    n = ctx.name
    (ctx.tree / "docs" / "harness_draw.json").write_text(json.dumps({"draw": [{"repo": n, "lang": lang}]}) + "\n")
    r = stage(ctx, "mod1_run", [PY, "-B", "tools/mod1_run.py", "--draw", "docs/harness_draw.json", "--only", n,
                                "--out", "docs/mod1_prep.json"])
    prep = ctx.tree / "docs" / "mod1_prep.json"
    out["mod1_prep"] = json.loads(prep.read_text()) if prep.exists() else None
    if r["rc"] or not out["mod1_prep"] or out["mod1_prep"][0].get("error"):
        out["stopped_at"] = "mod1_run"
        return
    r = stage(ctx, "mod1_lift", [PY, "-B", "tools/mod1_lift.py", "--repo", n, "--out", f"docs/mod1/lift_{n}.json"])
    lift = ctx.tree / "docs" / "mod1" / f"lift_{n}.json"
    out["lift"] = json.loads(lift.read_text()) if lift.exists() else None
    if r["rc"] or not out["lift"] or not out["lift"].get("snapshot"):
        out["stopped_at"] = "mod1_lift"
        return
    r = stage(ctx, "sa3_scan", [PY, "-B", "tools/sa3_scan.py", "--repo", n])
    if r["rc"]:
        out["stopped_at"] = "sa3_scan"
        return
    tail(ctx, out, placeholder_review)


def route_manifest(ctx: Ctx, lang: str, sha: str, out: dict, placeholder_review: bool) -> None:
    n = ctx.name
    r = stage(ctx, "laws_history", [PY, "-B", "tools/laws_history.py", "--repo", n, "--language", lang,
                                    "--out", str(SB.PILOT), "--c-family"])
    if r["rc"]:
        out["stopped_at"] = "laws_history"
        return
    r = stage(ctx, "sa3_scan --sha", [PY, "-B", "tools/sa3_scan.py", "--repo", n, "--sha", sha])
    if r["rc"]:
        out["stopped_at"] = "sa3_scan"
        return
    tail(ctx, out, placeholder_review)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--name", help="report name (default: the control directory's name)")
    ap.add_argument("--routes", default="own,manifest")
    ap.add_argument("--no-shim-lock", action="store_true", help="do not try lock/score with a placeholder review")
    a = ap.parse_args()
    control = a.control.resolve()
    top = SB.check_work(a.work)
    top.mkdir(parents=True, exist_ok=True)
    name = a.name or control.name
    manifest = json.loads((control / "manifest.json").read_text())
    lang = manifest["arguments"]["language"]
    repo = f"ctrl-{name}"                               # never the name of a real study repo
    results = {"control": str(control), "name": name, "repo": repo, "language": lang,
               "arguments": manifest["arguments"], "routes": {}}
    for route in a.routes.split(","):
        print(f"{name}: route {route}", flush=True)
        ctx = setup(top / route, repo, control)
        out: dict = {"work": str(ctx.work)}
        t0 = time.time()
        if route == "own":
            route_own(ctx, lang, out, placeholder_review=False)
        elif route == "manifest":
            route_manifest(ctx, lang, manifest["points"]["snapshot"]["hash"], out,
                           placeholder_review=not a.no_shim_lock)
        else:
            raise SystemExit(f"unknown route {route}")
        out["seconds"] = round(time.time() - t0, 1)
        out["stages"] = ctx.log
        results["routes"][route] = out
    (top / "report").mkdir(exist_ok=True)
    (top / "report" / f"{name}.run.json").write_text(json.dumps(results, indent=1) + "\n")
    import compare as C
    table = C.compare(results, manifest)
    (top / "report" / f"{name}.json").write_text(json.dumps(table, indent=1) + "\n")
    (top / "report" / f"{name}.md").write_text(C.markdown(table))
    s = table["summary"]
    print(f"{name}: {s['agree']} agree, {s['differ']} differ, {s['undecided']} undecided, {s['not_run']} not run "
          f"-> {top / 'report' / (name + '.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
