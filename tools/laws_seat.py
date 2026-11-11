#!/usr/bin/env python3
"""LAWS: the clone-time walk that seats the panel (M9; Amendment 10).

    python tools/laws_seat.py --want 2                 # seat the first 2 per language: ACC-P's inputs
    python tools/laws_seat.py --want 2 --language go   # one language
    python tools/laws_seat.py --report                 # what is seated so far, no network, no clones

**The panel is not the draw.** `docs/laws_draw/<lang>.json` holds a 400-deep head of a seeded permutation;
this walks it in order, applies the registered clone-time checks, and keeps the first `--want` that pass.
A candidate that fails is replaced by **the next in the order**, never by a re-draw, and every attempt is
logged with its reason (M9; Amendment 10 item 3).

**Two passes, because cloning is the expensive part.**

1. **API pre-screen (Amendment 10 item 4), reject-only.** One GraphQL query per 40 candidates reads the
   default branch's total commit count. That count is an **upper bound** on the first-parent count the rule
   actually tests, so a candidate under MIN_COMMITS is a *certain* fail and is never cloned. It can only
   reject: anything that clears the pre-screen still takes the full clone-time check. Measured 2026-11-11:
   this removes about 80% of candidates.
2. **Clone and check.** Blobless (`--filter=blob:none --no-checkout`): seating reads trees, never file
   contents, so blobs are not fetched. The checks are `laws_frame.eligible_history` -- imported, not
   restated -- fed a quarterly snapshot function built here.

Resumable: every attempt is written to `docs/laws_seating/<lang>.json` as it happens, so a killed run keeps
its work and the next one carries on (the flake_history.py pattern). `--budget-s` stops between candidates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import laws_frame as lf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DRAW = ROOT / "docs" / "laws_draw"
SEATING = ROOT / "docs" / "laws_seating"
POOL = Path(os.environ.get("LAWS_SEAT_POOL", "/srv/storage_16tb/projects/laws-seat-pool"))
PANEL_END = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)
EXTS = {"c": (".c", ".h"), "cpp": (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"),
        "csharp": (".cs",), "go": (".go",), "java": (".java",),
        "jsts": (".js", ".jsx", ".ts", ".tsx"), "kotlin": (".kt", ".kts"),
        "php": (".php",), "python": (".py",), "rust": (".rs",)}
LANGS = tuple(sorted(EXTS))
T0 = time.monotonic()


def log(m: str) -> None:
    print(f"[{time.monotonic() - T0:6.0f}s] {m}", flush=True)


def git(repo: Path, *args: str, timeout: int = 900) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=timeout)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def prescreen(names: list[str], batch: int = 40) -> dict[str, dict]:
    """owner/name -> {commits, archived, resolvable}. Reject-only; see the module docstring."""
    out: dict[str, dict] = {}
    fields = ("nameWithOwner isArchived isFork "
              "defaultBranchRef{target{... on Commit{history(first:1){totalCount}}}}")
    for i in range(0, len(names), batch):
        part = names[i:i + batch]
        body = " ".join(
            'r%d: repository(owner:%s,name:%s){%s}' % (j, json.dumps(n.split("/")[0]),
                                                       json.dumps(n.split("/")[1]), fields)
            for j, n in enumerate(part))
        r = subprocess.run(["gh", "api", "graphql", "-f", f"query=query {{{body}}}"],
                           capture_output=True, timeout=180)
        try:
            data = (json.loads(r.stdout).get("data") or {})
        except ValueError:
            data = {}
        for j, n in enumerate(part):
            g = data.get(f"r{j}")
            if not g or not g.get("defaultBranchRef"):
                out[n] = {"resolvable": False, "commits": 0, "archived": False}
                continue
            out[n] = {"resolvable": True, "archived": bool(g["isArchived"] or g["isFork"]),
                      "commits": g["defaultBranchRef"]["target"]["history"]["totalCount"]}
    return out


def clone(name: str, dest: Path) -> bool:
    """Blobless, no checkout: seating reads trees only."""
    if (dest / "HEAD").exists() or (dest / ".git").exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", "--quiet",
                        f"https://github.com/{name}.git", str(dest)], capture_output=True, timeout=3600)
    if r.returncode:
        shutil.rmtree(dest, ignore_errors=True)
        return False
    return True


def quarterly(repo: Path, language: str):
    """(quarters with >= MIN_FILES source files, quarters total, quarters holding a commit)."""
    exts = EXTS[language]
    head = git(repo, "rev-parse", "HEAD").strip()
    if not head:
        return 0, 0, 0
    # The repo's FIRST commit. `git log --reverse -1` does NOT give it: -n is applied before --reverse,
    # so it returns the newest commit (curl: 2026 instead of 1999). That bug made every candidate look
    # like it had one quarter of history and rejected all 400 rust candidates on 2026-11-11.
    roots = git(repo, "rev-list", "--max-parents=0", "HEAD").split()
    if not roots:
        return 0, 0, 0
    cts = [int(c) for c in (git(repo, "show", "-s", "--format=%ct", r).strip() for r in roots) if c]
    if not cts:
        return 0, 0, 0
    start = dt.datetime.fromtimestamp(min(cts), dt.timezone.utc)
    y, m = start.year, ((start.month - 1) // 3) * 3 + 1
    with_files = total = with_commit = 0
    started = False
    while True:
        b = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc)
        if b > PANEL_END:
            break
        sha = git(repo, "rev-list", "--first-parent", "-1", f"--before={b.isoformat()}", head).strip()
        if sha:
            n = sum(1 for p in git(repo, "ls-tree", "-r", "--name-only", sha).split("\n")
                    if p.endswith(exts))
            if n >= lf.MIN_FILES:
                started = True
            if started:
                total += 1
                with_commit += 1
                with_files += n >= lf.MIN_FILES
        elif started:
            total += 1
        m += 3
        if m > 12:
            y, m = y + 1, 1
    return with_files, total, with_commit


def record_path(language: str) -> Path:
    return SEATING / f"{language}.json"


def load(language: str) -> dict:
    p = record_path(language)
    if p.exists():
        return json.loads(p.read_text())
    return {"language": language, "attempts": [], "seated": []}


def save(language: str, rec: dict) -> None:
    SEATING.mkdir(parents=True, exist_ok=True)
    p = record_path(language)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1) + "\n")
    tmp.replace(p)


def seat_language(language: str, want: int, budget_s: int | None) -> dict:
    order = json.loads((DRAW / f"{language}.json").read_text())["draw_order_head"]
    rec = load(language)
    done = {a["repo"] for a in rec["attempts"]}
    if len(rec["seated"]) >= want:
        log(f"{language}: already seated {len(rec['seated'])}")
        return rec
    todo = [n for n in order if n not in done]
    screen = prescreen(todo[:200])
    log(f"{language}: pre-screened {len(screen)}; "
        f"{sum(1 for v in screen.values() if v['commits'] < lf.MIN_COMMITS)} rejected without cloning")
    for name in todo:
        if len(rec["seated"]) >= want:
            break
        if budget_s and time.monotonic() - T0 > budget_s:
            log(f"{language}: budget reached; {len(rec['seated'])} seated, the rest stays for next run")
            break
        s = screen.get(name)
        if s and (not s["resolvable"] or s["archived"] or s["commits"] < lf.MIN_COMMITS):
            why = ("unresolvable" if not s["resolvable"] else "archived/fork" if s["archived"]
                   else f"pre-screen: {s['commits']} commits < {lf.MIN_COMMITS} (upper bound)")
            rec["attempts"].append({"repo": name, "eligible": False, "why": why, "cloned": False})
            save(language, rec)
            continue
        dest = POOL / language / name.replace("/", "__")
        if not clone(name, dest):
            rec["attempts"].append({"repo": name, "eligible": False, "why": "clone failed", "cloned": False})
            save(language, rec)
            continue
        res = lf.eligible_history(dest, language, snapshots_fn=lambda r, l: quarterly(r, l))
        rec["attempts"].append({"repo": name, "cloned": True, **res})
        if res.get("eligible"):
            rec["seated"].append(name)
            log(f"{language}: SEATED {name} ({len(rec['seated'])}/{want}) "
                f"commits={res.get('first_parent_commits')} quarters={res.get('snapshots_with_files')}")
        else:
            log(f"{language}: rejected {name} -- {res.get('why')}")
            shutil.rmtree(dest, ignore_errors=True)   # a rejected candidate is not kept on disk
        save(language, rec)
    return rec


def cmd_report() -> int:
    print(f"{'language':9} {'seated':>7} {'attempts':>9} {'cloned':>7}  first seated")
    for l in LANGS:
        rec = load(l)
        cloned = sum(1 for a in rec["attempts"] if a.get("cloned"))
        print(f"{l:9} {len(rec['seated']):7} {len(rec['attempts']):9} {cloned:7}  "
              f"{', '.join(rec['seated'][:2]) or '-'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--want", type=int, default=2, help="how many to seat per language (ACC-P needs 2)")
    ap.add_argument("--language", choices=LANGS)
    ap.add_argument("--budget-s", type=int, help="stop between candidates after this many seconds")
    ap.add_argument("--report", action="store_true", help="print what is seated; no network, no clones")
    a = ap.parse_args()
    if a.report:
        return cmd_report()
    for l in ([a.language] if a.language else LANGS):
        try:
            seat_language(l, a.want, a.budget_s)
        except Exception as e:  # noqa: BLE001 -- one language must not stop the walk
            log(f"{l}: ERROR {type(e).__name__}: {e}")
    return cmd_report()


if __name__ == "__main__":
    sys.exit(main())
