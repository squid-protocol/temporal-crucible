#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""MOD-1 pipeline: harvest history + ONE structural snapshot per drawn repo, then score it.

    python tools/mod1_run.py --draw docs/draw40.json [--only a,b] [--jobs 2]

struct_null.py needs structure at the cut and a fix label after it -- NOT a full quarterly time course. So
each repo costs one scan, not a hundred, which is what makes 38 repos affordable at all.

Per repo: symlink the pool clone -> harvest history -> locate the commit nearest the cut -> write a
one-revision walk -> scan it with the panel engine -> leave struct_null.py to do the scoring.

Resumable: a repo whose history DB and scanned snapshot both exist is skipped.
"""
from __future__ import annotations

import argparse, json, subprocess, sqlite3, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import POOL_DIR, REPO_ROOT, GITGALAXY_PATH  # noqa: E402
from hist_replicate import CUT_Q  # noqa: E402

SRC = Path("/nvme-data/gitgalaxy-data")
STUDY = Path("/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot")
PY = sys.executable
HIST_TIMEOUT, SCAN_TIMEOUT = 5400, 7200


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def one(rec: dict) -> dict:
    r, lang = rec["repo"], rec["lang"]
    out = {"repo": r, "lang": lang, "age": rec["age"], "family": rec["family"], "year": rec["year"]}
    link = POOL_DIR / r
    if not link.exists():
        link.symlink_to(SRC / r)
    hist = STUDY / "history" / f"{r}.db"
    if not hist.exists():
        log(f"{r}: harvesting history ({lang})")
        p = subprocess.run([PY, "tools/laws_history.py", "--repo", r, "--language", lang,
                            "--out", str(STUDY)], capture_output=True, text=True,
                           cwd=REPO_ROOT, timeout=HIST_TIMEOUT)
        if not hist.exists():
            out["error"] = f"history failed: {(p.stdout + p.stderr)[-300:]}"
            return out
    h = sqlite3.connect(f"file:{hist}?mode=ro", uri=True)
    cts = [x[0] for x in h.execute("select ct from commit_ where merge=0 and bot=0 order by ct")]
    if len(cts) < 500:
        h.close(); out["error"] = f"only {len(cts)} usable commits"; return out
    cut = cts[int(len(cts) * CUT_Q)]
    row = h.execute("select sha, ct from commit_ where merge=0 and bot=0 and ct<=? "
                    "order by ct desc limit 1", (cut,)).fetchone()
    h.close()
    if not row:
        out["error"] = "no commit at the cut"; return out
    sha, ct = row
    out["cut_sha"], out["cut_ct"] = sha, ct
    db = STUDY / "dbs" / f"{r}.db"
    if db.exists():
        try:
            if sqlite3.connect(f"file:{db}?mode=ro", uri=True).execute(
                    "select count(*) from snap where rc=0").fetchone()[0] > 0:
                out["scanned"] = "already"; return out
        except Exception:
            pass
    walk = REPO_ROOT / "walks" / f"{r}_quarterly.json"
    walk.parent.mkdir(exist_ok=True)
    walk.write_text(json.dumps({"repo": r, "revisions": [
        {"sha": sha, "ref": "cut", "boundary": time.strftime("%Y-%m-%d", time.gmtime(ct)),
         "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ct)), "status": "ok"}]}))
    log(f"{r}: scanning snapshot {sha[:9]} ({out['age']}/{out['family']}, {rec['year']})")
    p = subprocess.run([PY, "tools/laws_build.py", "--gg", str(GITGALAXY_PATH), "--py", PY,
                        "--out", str(STUDY), "--repos", r], capture_output=True, text=True,
                       cwd=REPO_ROOT, timeout=SCAN_TIMEOUT)
    out["scanned"] = "ok" if "1 scanned now" in p.stdout or "scanned now" in p.stdout else "check"
    out["build_out"] = p.stdout.strip()[-200:]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draw", type=Path, default=Path("docs/draw40.json"))
    ap.add_argument("--only")
    ap.add_argument("--out", type=Path, default=Path("docs/mod1_prep.json"))
    a = ap.parse_args()
    draw = json.loads(a.draw.read_text())["draw"]
    if a.only:
        keep = set(a.only.split(","))
        draw = [d for d in draw if d["repo"] in keep]
    res = []
    if a.out.exists():
        res = json.loads(a.out.read_text())
        have = {x["repo"] for x in res if not x.get("error")}
        draw = [d for d in draw if d["repo"] not in have]
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
