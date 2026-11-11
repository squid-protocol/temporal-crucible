#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""REW-H1..H4 — does rewiring predict fixes, and the RIGHT KIND? (docs/rew_hypotheses.md, APPROVED).

Follows the registration as written. Nothing here chooses a bar, a class or a baseline; all of those are
fixed in the registration and Amendment 1.

    <engine venv>/bin/python tools/rew_eval.py depth --repos curl openssl   # cache nesting depth (slow)
    <engine venv>/bin/python tools/rew_eval.py score                        # -> docs/rew.md

Unit: a function at a quarterly snapshot that was also present at the preceding snapshot (rewiring is a
between-snapshot measure, so a function's first snapshot has none). Outcome: a fix of the class, mapped to
the function by chg_eval.map_fix, in the 180 days after the snapshot.
"""
from __future__ import annotations

import argparse
import bisect
import gzip
import json
import multiprocessing
import pathlib
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from chg_eval import fix_events, map_fix  # noqa: E402
from kwnest_eval import CONTROL, functions_in, keyword_profile  # noqa: E402
from nh_eval import DBS, snapshots  # noqa: E402

PRIMARY = "curl"
H12_REP = "libarchive"          # Amendment 1 item 2
H3_REP = "openssl"              # Amendment 1 item 2 (nDPI is the fallback, not run here)
WINDOW = 180 * 86400
SEED, ITERS = 2982, 5000
ALPHA = 0.01                    # per claim
ALPHA_H2 = 0.01 / 4             # Bonferroni across the four fix classes within REW-H2
EQUIV = 0.02                    # REW-H4 equivalence margin, the program's standing delta (LIB-H1..H3)
MIN_POS = 20                    # registered >= 20-positive rule per evaluated cell
CLASSES = ("extrinsic", "latent", "regression", "other-fix")
REG_PARTS = ("regression", "regression-linked")   # Amendment 1 item 3: the union is "regression"
CEXT = (".c", ".h")
CACHE = REPO_ROOT / "cache"


def _git(repo, *a, text=True):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *a], capture_output=True,
                          text=text, **({"errors": "replace"} if text else {})).stdout


# ------------------------------------------------------------------------------------------- renames (guard)
def rename_map(r):
    """old path -> new path, chronological, from `git log -M --diff-filter=R --name-status` (registered guard)."""
    fwd = {}
    for ln in _git(POOL_DIR / r, "log", "--reverse", "--no-merges", "-M", "--diff-filter=R",
                   "--name-status", "--format=").splitlines():
        if ln.startswith("R"):
            p = ln.split("\t")
            if len(p) == 3:
                fwd[p[1]] = p[2]
    return fwd


def canon(path, fwd):
    seen = set()
    while path in fwd and path not in seen:
        seen.add(path)
        path = fwd[path]
    return path


# ------------------------------------------------------------------------------------------- nesting depth
def _depth_task(task):
    r, sha = task
    repo = POOL_DIR / r
    want = {}
    for ln in _git(repo, "ls-tree", "-r", sha).splitlines():
        meta, _, path = ln.partition("\t")
        f = meta.split()
        if len(f) == 3 and f[1] == "blob" and path.endswith(CEXT):
            want[f[2]] = path
    if not want:
        return r, sha, {}
    proc = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.stdin.write(("\n".join(want) + "\n").encode())
    proc.stdin.close()
    out, fh = {}, proc.stdout
    while True:
        hdr = fh.readline()
        if not hdr:
            break
        parts = hdr.split()
        if len(parts) != 3:
            break
        oid, size = parts[0].decode(), int(parts[2])
        src = fh.read(size)
        fh.read(1)
        path = want.get(oid)
        if path is None:
            continue
        try:
            fns = functions_in(src)
        except Exception:
            continue
        for name, node in fns.items():
            d = [dep for kw, dep in keyword_profile(node) if kw in CONTROL]
            out[f"{path}\t{name}"] = (max(d) if d else 0, (sum(d) / len(d)) if d else 0.0)
    proc.wait()
    return r, sha, out


def cmd_depth(a) -> int:
    CACHE.mkdir(exist_ok=True)
    for r in a.repos:
        t0 = time.time()
        path = CACHE / f"rew_depth_{r}.json.gz"
        have = json.loads(gzip.decompress(path.read_bytes())) if path.exists() else {}
        todo = [(r, s["sha"]) for s in snapshots(r) if s["sha"] not in have]
        print(f"{r}: {len(todo)} snapshots to parse ({len(have)} cached)", flush=True)
        if todo:
            with multiprocessing.get_context("fork").Pool(a.jobs) as p:
                for i, (_, sha, d) in enumerate(p.imap_unordered(_depth_task, todo, chunksize=1), 1):
                    have[sha] = d
                    if i % 10 == 0:
                        print(f"  {i}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
            path.write_bytes(gzip.compress(json.dumps(have).encode()))
        print(f"{r}: depth cached for {len(have)} snapshots ({time.time() - t0:.0f}s)", flush=True)
    return 0


# ------------------------------------------------------------------------------------------- per-snapshot frame
def build(r, fwd, depth):
    """[(ct, keys, loc, rewire, branch, edits, fan_in, fan_out, maxd, meand)] per evaluable snapshot."""
    snaps = snapshots(r)
    con = sqlite3.connect(f"file:{DBS[r]}?mode=ro", uri=True)
    frames, prev, edits = [], None, Counter()
    for s in snaps:
        rows = con.execute(
            "SELECT fd.file_path, f.func_name, f.start_line, f.loc, f.struct_branch, f.struct_linear, "
            "f.func_fan_in, f.func_fan_out, f.calls_out_to, f.references_to "
            "FROM function_data f JOIN file_data fd ON f.file_id = fd.id WHERE fd.commit_hash = ? "
            "AND fd.language IN ('c','cpp') AND f.func_name IS NOT NULL AND f.func_name != ''",
            (s["sha"],)).fetchall()
        d = {}
        for path, name, st, loc, br, lin, fi, fo, calls, refs in sorted(rows, key=lambda x: (x[0], x[1], x[2] or 0)):
            key = (canon(path, fwd), name)
            if key in d:
                continue
            try:
                cs = frozenset(json.loads(calls)) if calls else frozenset()
            except Exception:
                cs = frozenset()
            d[key] = {"loc": loc or 0, "br": br or 0, "fi": fi or 0, "fo": fo or 0, "calls": cs,
                      "raw": path, "fp": (loc or 0, br or 0, lin or 0, cs, hash(refs or ""))}
        if prev is not None:
            # single-name move rescue, as in chg_eval.transitions: one gone, one new, same function name
            vn, nn = defaultdict(list), defaultdict(list)
            for k in prev:
                if k not in d:
                    vn[k[1]].append(k)
            for k in d:
                if k not in prev:
                    nn[k[1]].append(k)
            moved = {nn[n][0]: vn[n][0] for n in nn if len(nn[n]) == 1 and len(vn.get(n, [])) == 1}
            keys, rows_out = [], []
            for k, v in d.items():
                pk = k if k in prev else moved.get(k)
                if pk is None:
                    continue
                p = prev[pk]
                if v["fp"] != p["fp"]:
                    edits[k] += 1
                u = v["calls"] | p["calls"]
                rewire = len((v["calls"] ^ p["calls"])) / len(u) if u else 0.0
                dk = depth.get(s["sha"], {}).get(f"{v['raw']}\t{k[1]}") if depth else None
                keys.append(k)
                rows_out.append((v["loc"], rewire, v["br"], edits[k], v["fi"], v["fo"],
                                 (dk or (np.nan, np.nan))[0], (dk or (np.nan, np.nan))[1]))
            if rows_out:
                arr = np.array(rows_out, dtype=float)
                frames.append({"ct": s["ct"], "sha": s["sha"], "keys": keys, "loc": np.maximum(arr[:, 0], 1.0),
                               "rewire": arr[:, 1], "branch": arr[:, 2], "edits": arr[:, 3],
                               "fan_in": arr[:, 4], "fan_out": arr[:, 5],
                               "maxd": arr[:, 6], "meand": arr[:, 7]})
        prev = d
    con.close()
    return frames


def recall20(score, loc, path_rank, pos):
    """EA's recall_at(..., 0.20): rank by (-score, loc, path); whole functions while cumulative LOC <= 20%."""
    order = np.lexsort((path_rank, loc, -score))
    k = int(np.searchsorted(np.cumsum(loc[order]), 0.2 * loc.sum(), side="right"))
    return pos[order][:k].sum() / pos.sum()


def positives(repos):
    """(repo, canon path, func name) -> sorted [(ct, class)], via chg_eval.map_fix (the existing mapper)."""
    ev, last = [], {}
    for r in repos:
        e, last[r] = fix_events(r)
        ev += e
    print(f"fix events {len(ev):,}: {Counter(x[3] for x in ev)}", flush=True)
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=8) for h in hs]
    print(f"function hits {len(hits):,}", flush=True)
    return hits, last


# ------------------------------------------------------------------------------------------- statistics
def boot(per_snap, rng, alpha):
    a = np.array(per_snap, dtype=float)
    if len(a) == 0:
        return float("nan"), float("nan"), (float("nan"), float("nan"))
    b = np.array([a[rng.integers(0, len(a), len(a))].mean() for _ in range(ITERS)])
    return float(a.mean()), float(np.quantile(b, alpha)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))


def cell(frames, idx, r, klass, last_ct, depth_mode=False):
    """Per-snapshot recalls for one (repo, class) cell. Returns list of dicts, one per scored snapshot."""
    out = []
    for fr in frames:
        if fr["ct"] + WINDOW > last_ct:
            continue
        y = np.zeros(len(fr["keys"]))
        for i, k in enumerate(fr["keys"]):
            v = idx.get((r,) + k)
            if not v:
                continue
            j = bisect.bisect_right(v, (fr["ct"], "￿"))
            while j < len(v) and v[j][0] <= fr["ct"] + WINDOW:
                if v[j][1] == klass:
                    y[i] = 1.0
                    break
                j += 1
        if y.sum() == 0:
            continue
        loc = fr["loc"]
        pr = np.argsort(np.argsort(np.array([f"{a}\t{b}" for a, b in fr["keys"]])))
        size = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
        base = {"size": size, "branch": recall20(fr["branch"], loc, pr, y), "edits": recall20(fr["edits"], loc, pr, y),
                "fan_in": recall20(fr["fan_in"], loc, pr, y), "fan_out": recall20(fr["fan_out"], loc, pr, y)}
        rec = {"sha": fr["sha"], "pos": int(y.sum()), "n": len(y), "base": base, "rewire": recall20(fr["rewire"], loc, pr, y)}
        rec["h1"] = rec["rewire"] - max(base.values())
        rec["vs_edits"] = rec["rewire"] - base["edits"]
        if depth_mode and np.isfinite(fr["maxd"]).any():
            md = np.nan_to_num(fr["maxd"], nan=0.0)
            rec["maxd"] = recall20(md, loc, pr, y)
            rec["h3"] = rec["maxd"] - max(base["size"], base["branch"])
            rec["cov"] = float(np.isfinite(fr["maxd"]).mean())
        out.append(rec)
    return out


def verdict_one_sided(mean, lo):
    return "SUPPORTED" if (mean > 0 and lo > 0) else "not supported"


def cmd_score(a) -> int:
    t0 = time.time()
    repos = [PRIMARY, H12_REP, H3_REP]
    hits, last_ct = positives(repos)
    fwd = {r: rename_map(r) for r in repos}
    idx = defaultdict(list)
    for (r, path, nm, ct, klass) in hits:
        k = "regression" if klass in REG_PARTS else klass
        idx[(r, canon(path, fwd[r]), nm)].append((ct, k))
        short = nm.split("::")[-1]
        if short != nm:
            idx[(r, canon(path, fwd[r]), short)].append((ct, k))
    for v in idx.values():
        v.sort()
    depth = {}
    for r in (PRIMARY, H3_REP):
        p = CACHE / f"rew_depth_{r}.json.gz"
        depth[r] = json.loads(gzip.decompress(p.read_bytes())) if p.exists() else {}
        if not depth[r]:
            print(f"WARNING: no depth cache for {r} — run `rew_eval.py depth --repos {r}` first", flush=True)
    frames = {}
    for r in repos:
        frames[r] = build(r, fwd[r], depth.get(r, {}))
        print(f"{r}: {len(frames[r])} frames, {sum(len(f['keys']) for f in frames[r]):,} function-snapshots "
              f"({time.time() - t0:.0f}s)", flush=True)

    cells = {}
    for r in repos:
        for c in CLASSES:
            cells[(r, c)] = cell(frames[r], idx, r, c, last_ct[r], depth_mode=(r in depth and bool(depth[r])))
    rng_seq = iter(np.random.SeedSequence(SEED).spawn(32))

    def pos_of(r, c):
        return sum(x["pos"] for x in cells[(r, c)])

    L = ["# REW-H1..H4 — rewiring, nesting depth and the kind of fix (SCORED)", "",
         "Registration: [`rew_hypotheses.md`](rew_hypotheses.md), approved 2026-11-11 before any statistic; "
         "Amendment 1 (function-grain power, split replication, regression = the union of both sub-classes) "
         f"applies. Tool `tools/rew_eval.py`. Window **{WINDOW // 86400} days**, budget **20% of lines**, "
         f"α = {ALPHA} per claim ({ALPHA_H2:.4g} within REW-H2), {ITERS} snapshot bootstrap rounds, seed {SEED}. "
         f"Cells under {MIN_POS} positives are printed UNDERPOWERED and not read.", "",
         "Unit: a function at a quarterly snapshot **that was also present at the preceding snapshot** — "
         "rewiring is a between-snapshot measure, so a function's first appearance has none.", "",
         "## Positives per cell (function-snapshots with a fix of the class in the window)", "",
         "| repo | scored snapshots | " + " | ".join(CLASSES) + " |", "|---|---:|" + "---:|" * len(CLASSES)]
    for r in repos:
        L.append(f"| {r} | {max(len(cells[(r, c)]) for c in CLASSES)} | " +
                 " | ".join(f"{pos_of(r, c):,}" for c in CLASSES) + " |")

    # ---- REW-H1
    L += ["", "## REW-H1 (primary) — rewiring predicts extrinsic fixes beyond every baseline", "",
          "Lift = recall@20% of lines for rewiring **minus the strongest of** {stronger size order, branch "
          "count, edit count, fan-in level, fan-out level}. The registration requires it to beat all of them, "
          "so the single strongest baseline per snapshot is subtracted.", "",
          "| repo | snaps | positives | rewire | strongest baseline | lift | lo (α=0.01) | 90% CI | verdict |",
          "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    h1 = {}
    for r in (PRIMARY, H12_REP):
        v = cells[(r, "extrinsic")]
        n = pos_of(r, "extrinsic")
        if n < MIN_POS:
            L.append(f"| {r} | {len(v)} | {n} | — | — | — | — | — | **UNDERPOWERED** |")
            continue
        mean, lo, ci = boot([x["h1"] for x in v], np.random.default_rng(next(rng_seq)), ALPHA)
        h1[r] = (mean, lo, ci, v)
        L.append(f"| {r} | {len(v)} | {n:,} | {np.mean([x['rewire'] for x in v]):.3f} | "
                 f"{np.mean([max(x['base'].values()) for x in v]):.3f} | {mean:+.3f} | {lo:+.3f} | "
                 f"[{ci[0]:+.3f}, {ci[1]:+.3f}] | **{verdict_one_sided(mean, lo)}** |")
    L += ["", "Baselines separately (mean recall@20 over scored snapshots):", "",
          "| repo | rewire | stronger size | branch | edit count | fan-in | fan-out |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in (PRIMARY, H12_REP):
        v = cells[(r, "extrinsic")]
        if v:
            L.append(f"| {r} | {np.mean([x['rewire'] for x in v]):.3f} | " +
                     " | ".join(f"{np.mean([x['base'][b] for x in v]):.3f}" for b in ("size", "branch", "edits", "fan_in", "fan_out")) + " |")

    # ---- REW-H2
    L += ["", "## REW-H2 (class specificity) — the lift must be larger for extrinsic than for the rest", "",
          "Paired by snapshot within the primary repo. A lift that is flat across classes is reported as "
          "**churn in disguise**, not as support for REW-H1.", "",
          f"| comparison | snaps | lift(extrinsic) − lift(class) | lo (α={ALPHA_H2:.4g}) | 90% CI | verdict |",
          "|---|---:|---:|---:|---|---|"]
    ex = {x["sha"]: x["h1"] for x in cells[(PRIMARY, "extrinsic")]}
    h2_ok = []
    for c in CLASSES:
        if c == "extrinsic":
            continue
        other = cells[(PRIMARY, c)]
        n = pos_of(PRIMARY, c)
        paired = [(ex[x["sha"]] - x["h1"]) for x in other if x["sha"] in ex]
        if n < MIN_POS or len(paired) < 2:
            L.append(f"| extrinsic − {c} | {len(paired)} | — | — | — | **UNDERPOWERED** |")
            continue
        mean, lo, ci = boot(paired, np.random.default_rng(next(rng_seq)), ALPHA_H2)
        ok = mean > 0 and lo > 0
        h2_ok.append(ok)
        L.append(f"| extrinsic − {c} | {len(paired)} | {mean:+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | "
                 f"**{'larger for extrinsic' if ok else 'not larger'}** |")
    L += ["", f"Per-class lift over the strongest baseline, {PRIMARY} (descriptive):", "",
          "| class | snaps | positives | rewire | strongest baseline | lift |", "|---|---:|---:|---:|---:|---:|"]
    for c in CLASSES:
        v = cells[(PRIMARY, c)]
        flag = "" if pos_of(PRIMARY, c) >= MIN_POS else " (UNDERPOWERED)"
        if v:
            L.append(f"| {c}{flag} | {len(v)} | {pos_of(PRIMARY, c):,} | {np.mean([x['rewire'] for x in v]):.3f} | "
                     f"{np.mean([max(x['base'].values()) for x in v]):.3f} | {np.mean([x['h1'] for x in v]):+.3f} |")

    # ---- REW-H3
    L += ["", "## REW-H3 — maximum nesting depth predicts latent fixes beyond size and branch count", "",
          "Depth is measured with tree-sitter at each snapshot (`kwnest_eval.keyword_profile`), the first time "
          "this program has measured it: `complexity` in the walk database equals `struct_branch`, the branch "
          "count. Lift = recall@20 for max depth minus the stronger of {stronger size order, branch count}.", "",
          "| repo | snaps | positives | depth coverage | max depth | stronger baseline | lift | lo (α=0.01) | 90% CI | verdict |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    h3 = {}
    for r in (PRIMARY, H3_REP):
        v = [x for x in cells[(r, "latent")] if "h3" in x]
        n = sum(x["pos"] for x in v)
        if n < MIN_POS:
            L.append(f"| {r} | {len(v)} | {n} | — | — | — | — | — | — | **UNDERPOWERED** |")
            continue
        mean, lo, ci = boot([x["h3"] for x in v], np.random.default_rng(next(rng_seq)), ALPHA)
        h3[r] = (mean, lo)
        L.append(f"| {r} | {len(v)} | {n:,} | {np.mean([x['cov'] for x in v]):.0%} | "
                 f"{np.mean([x['maxd'] for x in v]):.3f} | {np.mean([max(x['base']['size'], x['base']['branch']) for x in v]):.3f} | "
                 f"{mean:+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | **{verdict_one_sided(mean, lo)}** |")

    # ---- REW-H4
    L += ["", "## REW-H4 (guard) — if REW-H1 fails, an equivalence test, not 'inconclusive'", ""]
    if PRIMARY in h1 and h1[PRIMARY][0] > 0 and h1[PRIMARY][1] > 0:
        L.append("REW-H1 is supported on the primary repo, so the guard does not fire.")
    else:
        v = cells[(PRIMARY, "extrinsic")]
        mean, _, ci = boot([x["vs_edits"] for x in v], np.random.default_rng(next(rng_seq)), ALPHA)
        inside = -EQUIV < ci[0] and ci[1] < EQUIV
        L += [f"REW-H1 did not pass, so the registered TOST applies. Rewiring **minus the churn baseline "
              f"(edit count)** on {PRIMARY} extrinsic: mean **{mean:+.3f}**, 90% CI "
              f"[{ci[0]:+.3f}, {ci[1]:+.3f}], δ = ±{EQUIV}.", "",
              f"**{'Equivalent to churn within δ' if inside else 'Not equivalent within δ either — the CI leaves the margin'}.**"]

    L += ["", "## What this cannot establish", "",
          "Carried from the registration §7, unchanged by the result: rewiring is chosen by developers, not "
          "assigned. A function gets rewired because someone decided to change it, possibly because they "
          "already suspected it. Confounding by indication is not closed by any control here, so a positive "
          "REW-H1 says rewiring **marks** extrinsic risk, never that it causes it. curl plus libarchive is "
          "two C projects: a pass is a replicated development-set result, not a panel result.", "",
          "Measurement limits specific to this run:", "",
          "- A function's **first** snapshot has no rewiring value and is excluded, so short-lived functions "
          "are under-represented.",
          "- Identity is `(canonical file path, function name)` with the registered `-M` rename map applied and "
          "chg_eval's single-name move rescue; a function renamed in place still reads as a death and a birth.",
          "- An **edit** is a change in the function's `(loc, struct_branch, struct_linear, call set, "
          "references)` fingerprint between snapshots — a proxy for a source edit, not a diff.",
          "- The walk is quarterly, so rewiring that happened and reverted inside a quarter is invisible, "
          "which pushes the measured rewiring rate **down**.",
          "", f"Runtime {time.time() - t0:.0f}s."]
    (DOCS_DIR / "rew.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("depth", help="cache per-function nesting depth per snapshot")
    d.add_argument("--repos", nargs="+", default=[PRIMARY, H3_REP])
    d.add_argument("--jobs", type=int, default=8)
    d.set_defaults(fn=cmd_depth)
    s = sub.add_parser("score", help="score REW-H1..H4 -> docs/rew.md")
    s.set_defaults(fn=cmd_score)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
