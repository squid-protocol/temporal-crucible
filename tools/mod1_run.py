#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""MOD-1 preparation: history + commit bodies + ONE structural snapshot per repo. It never scores.

    python tools/mod1_run.py --draw docs/draw40.json [--only a,b]

Per drawn repo: symlink the pool clone -> harvest history in the repo's language (C and C++ together for a
C-family repo) -> harvest commit bodies, merges included -> locate the commit at the cut, counting merges where
the history made them the unit -> scan that one revision with the panel engine. The eight earlier repos only
need the body harvest. Scoring is tools/mod1_score.py, and only after every amendment is committed.

Resumable: a repo is skipped once it is recorded under the current rules (RULES).
"""
from __future__ import annotations

import argparse, json, subprocess, sqlite3, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import POOL_DIR, REPO_ROOT, GITGALAXY_PATH  # noqa: E402
from hist_replicate import CUT_Q  # noqa: E402

SRC = Path("/nvme-data/gitgalaxy-data")
STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
META = STUDY / "meta_mod1"
AMEND = Path("docs/mod1_language_amend.json")  # Amendment 2: the corrected language of ten repos
PRIOR = ("commons-lang", "curl", "libxml2", "ndpi", "postgres", "prometheus", "redis", "sphinx")
RULES = "A3"  # docs/moderator_registration.md, Amendment 3
PY = sys.executable
HIST_TIMEOUT, SCAN_TIMEOUT = 7200, 10800


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def bodies(r: str) -> str | None:
    """the commit-body harvest the cascade's top tiers read; merges included"""
    p = subprocess.run([PY, "tools/hist_meta.py", "--pool", str(POOL_DIR), "--out", str(META), "--repos", r,
                        "--with-merges"], capture_output=True, text=True, cwd=REPO_ROOT, timeout=HIST_TIMEOUT)
    try:
        ok = ro(META / f"{r}.db").execute("select value from meta where key='done'").fetchone()
    except Exception:
        ok = None
    return None if ok else f"body harvest failed: {(p.stdout + p.stderr)[-300:]}"


def one(rec: dict) -> dict:
    r, lang = rec["repo"], rec["lang"]
    out = {"repo": r, "lang": lang, "rules": RULES}
    link = POOL_DIR / r
    if not link.exists():
        link.symlink_to(SRC / r)
    want_units = "c+cpp" if lang in ("c", "cpp") else lang
    hist = STUDY / "history" / f"{r}.db"
    if hist.exists():  # a history harvested under other unit rules is not this study's history
        try:
            m = dict(ro(hist).execute("select key, value from meta"))
        except Exception:
            m = {}
        if m.get("language") != lang or m.get("units", m.get("language")) != want_units:
            log(f"{r}: history has units {m.get('units', m.get('language'))}, want {want_units} -- re-harvesting")
            hist.unlink()
            Path(str(hist) + "-journal").unlink(missing_ok=True)
    if not hist.exists():
        log(f"{r}: harvesting history ({want_units})")
        p = subprocess.run([PY, "tools/laws_history.py", "--repo", r, "--language", lang, "--out", str(STUDY),
                            "--c-family"], capture_output=True, text=True, cwd=REPO_ROOT, timeout=HIST_TIMEOUT)
        if not hist.exists() or p.returncode:
            hist.unlink(missing_ok=True)
            out["error"] = f"history failed: {(p.stdout + p.stderr)[-300:]}"
            return out
    err = bodies(r)
    if err:
        out["error"] = err
        return out
    h = ro(hist)
    unit = h.execute("select value from meta where key='unit'").fetchone()[0]
    where = "bot=0" + ("" if unit.startswith("first-parent") else " and merge=0")
    cts = [x[0] for x in h.execute(f"select ct from commit_ where {where} order by ct")]
    out["merge_units"], out["usable_commits"] = unit.startswith("first-parent"), len(cts)
    if len(cts) < 500:
        h.close(); out["error"] = f"only {len(cts)} usable commits"; return out
    cut = cts[int(len(cts) * CUT_Q)]
    row = h.execute(f"select sha, ct from commit_ where {where} and ct<=? order by ct desc limit 1", (cut,)).fetchone()
    h.close()
    sha, ct = row
    out["cut_sha"], out["cut_ct"] = sha, ct
    db = STUDY / "dbs" / f"{r}.db"

    def scanned() -> bool:
        try:
            return db.exists() and ro(db).execute(
                "select count(*) from snap where rc=0 and commit_hash=?", (sha,)).fetchone()[0] > 0
        except Exception:
            return False

    if scanned():
        out["scanned"] = "already"; return out
    walk = REPO_ROOT / "walks" / f"{r}_quarterly.json"
    walk.parent.mkdir(exist_ok=True)
    walk.write_text(json.dumps({"repo": r, "revisions": [
        {"sha": sha, "ref": "cut", "boundary": time.strftime("%Y-%m-%d", time.gmtime(ct)),
         "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ct)), "status": "ok"}]}))
    log(f"{r}: scanning snapshot {sha[:9]}")
    p = subprocess.run([PY, "tools/laws_build.py", "--gg", str(GITGALAXY_PATH), "--py", PY,
                        "--out", str(STUDY), "--repos", r], capture_output=True, text=True,
                       cwd=REPO_ROOT, timeout=SCAN_TIMEOUT)
    if scanned():
        out["scanned"] = "ok"
    else:
        out["error"] = f"scan did not record the cut snapshot: {(p.stdout + p.stderr).strip()[-300:]}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draw", type=Path, default=Path("docs/draw40.json"))
    ap.add_argument("--only")
    ap.add_argument("--out", type=Path, default=Path("docs/mod1_prep.json"))
    a = ap.parse_args()
    draw = json.loads(a.draw.read_text())["draw"]
    amend = json.loads(AMEND.read_text())["repos"] if AMEND.exists() else {}
    draw = [{**d, **amend.get(d["repo"], {})} for d in draw]
    if a.only:
        keep = set(a.only.split(","))
        draw = [d for d in draw if d["repo"] in keep]
    else:
        for r in PRIOR:
            log(f"prior {r}: bodies {bodies(r) or 'ok'}")
    res = json.loads(a.out.read_text()) if a.out.exists() else []
    have = {x["repo"] for x in res if not x.get("error") and x.get("rules") == RULES}
    draw = [d for d in draw if d["repo"] not in have]
    redo = {d["repo"] for d in draw}
    res = [x for x in res if x["repo"] not in redo]  # one record per repo: the retry replaces it
    log(f"{len(draw)} repos to prepare")
    for i, rec in enumerate(draw, 1):
        try:
            r = one(rec)
        except subprocess.TimeoutExpired:
            r = {"repo": rec["repo"], "error": "timeout"}
        except Exception as e:
            r = {"repo": rec["repo"], "error": f"{type(e).__name__}: {e}"}
        res.append(r)
        a.out.write_text(json.dumps(res, indent=1) + "\n")
        log(f"  [{i}/{len(draw)}] {r['repo']}: {r.get('error') or r.get('scanned')}")
    ok = sum(1 for x in res if not x.get("error"))
    log(f"done: {ok}/{len(res)} prepared -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
