#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""INP-H1..H6: does input-facing code mark where CVEs land? (docs/inp_hypotheses.md, registered 2026-11-06). Git only.

    python tools/inp_eval.py
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from sc_discover import recall20  # noqa: E402

IN = (r"\b(?:recv|recvfrom|recvmsg|read|pread|readv|fread|fgets|getline|fgetc|getc|SSL_read|SSL_read_ex|SSL_peek|BIO_read|"
      r"BIO_read_ex|BIO_gets|gnutls_record_recv|mbedtls_ssl_read|wolfSSL_read|pcap_next|pcap_next_ex|pcap_dispatch|pcap_loop)\s*\(")
BUF = (r"(?:unsigned\s+char|uint8_t|u_int8_t|u_char|guint8|char|void)\s*(?:const\s*)?\*\s*\w+\s*,\s*(?:const\s+)?"
       r"(?:size_t|ssize_t|unsigned(?:\s+int|\s+long)?|int|long|uint16_t|uint32_t|u_int16_t|u_int32_t|off_t)\s+\w*len\w*"
       r"|\b(?:memcpy|memmove|strncpy)\s*\([^;]*\b\w*len\w*\b")
REPOS = {"curl": (".c", ".h"), "ndpi": (".c", ".h"), "openssl": (".c", ".h"),
         "harfbuzz": (".c", ".h", ".cc", ".hh", ".cpp", ".hpp")}
SEED, ITERS, DAY, WINDOW, MIN_SNAPS, EQUIV = 2982, 5000, 86400, 180, 20, 0.02
ALPHA = 0.01 / 6


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace").stdout


def grep_counts(repo, sha, pat, exts):
    out = {}
    for line in _git(repo, "-c", "core.quotepath=off", "grep", "-c", "-P", pat, sha, "--", *[f"*{e}" for e in exts]).splitlines():
        _, _, rest = line.partition(":")
        p, _, n = rest.rpartition(":")
        if n.isdigit():
            out[p] = int(n)
    return out


def snap_task(t):
    r, sha = t
    repo, exts = POOL_DIR / r, REPOS[r]
    return sha, grep_counts(repo, sha, "", exts), grep_counts(repo, sha, IN, exts), grep_counts(repo, sha, BUF, exts)


def events(r):
    repo, exts = POOL_DIR / r, REPOS[r]
    xc = json.loads((REPO_ROOT / "events" / f"{r}_xc.json").read_text())["events"]
    if r != "harfbuzz":
        return [e for e in xc if e["class"] in ("latent", "extrinsic", "other-fix")]
    head = json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())["events_head"]
    lat = []
    for e in json.loads((REPO_ROOT / "events" / f"{r}.json").read_text())["events"]:
        if e["class"] != "security-fix":
            continue
        if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", e["sha"], head]).returncode != 0:
            continue
        ct = int(_git(repo, "show", "-s", "--format=%ct", e["sha"]).strip())
        files = [f for f in _git(repo, "-c", "core.quotepath=off", "diff-tree", "--no-commit-id", "--name-only", "-r",
                                 e["sha"]).splitlines() if f.endswith(exts)]
        lat.append({"sha": e["sha"], "ct": ct, "class": "latent", "c_files": files})
    ls = {e["sha"] for e in lat}
    return lat + [e for e in xc if e["class"] in ("extrinsic", "other-fix") and e["sha"] not in ls]


def main() -> int:
    t0 = time.time()
    res, desc = {}, {}
    for r in REPOS:
        repo = POOL_DIR / r
        snaps = [s for s in json.loads((REPO_ROOT / "walks" / f"{r}_quarterly.json").read_text())["revisions"]
                 if s.get("status", "ok") == "ok"]
        for s in snaps:
            s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
        ev = events(r)
        with multiprocessing.get_context("fork").Pool(6) as p:
            data = {sha: (ln, i, b) for sha, ln, i, b in p.imap_unordered(snap_task, [(r, s["sha"]) for s in snaps])}
        per = defaultdict(list)
        any_in, any_buf = [], []
        for s in snaps:
            lines, cin, cbuf = data[s["sha"]]
            if not lines:
                continue
            paths = sorted(lines)
            loc = np.array([float(max(lines[p], 1)) for p in paths])
            pr = np.argsort(np.argsort(np.array(paths)))
            S = {"IN": np.array([cin.get(p, 0) for p in paths], float) / loc,
                 "BUF": np.array([cbuf.get(p, 0) for p in paths], float) / loc}
            any_in.append(float(np.mean(S["IN"] > 0)))
            any_buf.append(float(np.mean(S["BUF"] > 0)))
            pos, prior_lat = defaultdict(set), set()
            for e in ev:
                if e["ct"] <= s["ct"]:
                    if e["class"] == "latent":
                        prior_lat.update(e["c_files"])
                elif e["ct"] <= s["ct"] + WINDOW * DAY:
                    pos[e["class"]].update(e["c_files"])
            lifts = {}
            for k in ("latent", "extrinsic", "other-fix"):
                y = np.array([1.0 if p in pos[k] else 0.0 for p in paths])
                if y.sum() == 0:
                    continue
                base = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
                lifts[k] = {m: recall20(v, loc, pr, y) - base for m, v in S.items()}
            row = {"lifts": lifts}
            # H5/H6: candidates with no prior latent fix
            keep = np.array([p not in prior_lat for p in paths])
            y = np.array([1.0 if p in pos["latent"] else 0.0 for p in paths])
            if keep.sum() >= 2 and y[keep].sum() > 0:
                kp = [p for p, k in zip(paths, keep) if k]
                l2, y2 = loc[keep], y[keep]
                pr2 = np.argsort(np.argsort(np.array(kp)))
                b2 = max(recall20(l2, l2, pr2, y2), recall20(-l2, l2, pr2, y2))
                row["nohist"] = {m: recall20(v[keep], l2, pr2, y2) - b2 for m, v in S.items()}
            per["rows"].append(row)
        rows = per["rows"]
        scored = [x for x in rows if "latent" in x["lifts"]]
        desc[r] = {"snaps": len(rows), "lat_snaps": len(scored), "any_in": np.median(any_in), "any_buf": np.median(any_buf),
                   "n_lat": sum(e["class"] == "latent" for e in ev)}
        if len(scored) >= MIN_SNAPS:
            vec = {}
            for m in ("IN", "BUF"):
                vec[f"h_beat_{m}"] = np.array([x["lifts"]["latent"][m] for x in scored])
                spec = [x["lifts"]["latent"][m] - np.mean([x["lifts"][k][m] for k in ("extrinsic", "other-fix") if k in x["lifts"]])
                        for x in scored if any(k in x["lifts"] for k in ("extrinsic", "other-fix"))]
                vec[f"h_spec_{m}"] = np.array(spec)
                vec[f"h_nohist_{m}"] = np.array([x["nohist"][m] for x in rows if "nohist" in x])
            res[r] = vec
        print(f"{r}: {len(scored)} latent-scored snapshots ({time.time() - t0:.0f}s)", flush=True)

    claims = [("INP-H1", "h_beat_IN", "IN beats size on CVE fixes"), ("INP-H2", "h_beat_BUF", "BUF beats size on CVE fixes"),
              ("INP-H3", "h_spec_IN", "IN: CVE lift − placebo-class lift"), ("INP-H4", "h_spec_BUF", "BUF: CVE lift − placebo-class lift"),
              ("INP-H5", "h_nohist_IN", "IN beats size where no prior CVE"), ("INP-H6", "h_nohist_BUF", "BUF beats size where no prior CVE")]
    spawn = iter(np.random.SeedSequence(SEED).spawn(len(claims)))
    L = ["# INP-H1..H6 — input-facing code vs CVE fixes (SCORED)", "",
         f"- evaluable repos (≥ {MIN_SNAPS} snapshots with a CVE positive): {', '.join(res) or 'none'}", "",
         "| claim | what | pooled mean | lo (α=0.0017) | 90% CI | per repo | verdict |", "|---|---|---:|---:|---|---|---|"]
    verdicts = {}
    for c, key, what in claims:
        arrs = {r: v[key] for r, v in res.items() if len(v[key])}
        rng = np.random.default_rng(next(spawn))
        if not arrs:
            L.append(f"| **{c}** | {what} | — | — | — | — | **not evaluable** |")
            verdicts[c] = "not evaluable"
            continue
        mean = float(np.mean([a.mean() for a in arrs.values()]))
        b = np.array([np.mean([a[rng.integers(0, len(a), len(a))].mean() for a in arrs.values()]) for _ in range(ITERS)])
        lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
        v = ("SUPPORTED" if mean > 0 and lo > 0 else
             "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        verdicts[c] = v
        pr = " / ".join(f"{r} {a.mean():+.3f}" for r, a in arrs.items())
        L.append(f"| **{c}** | {what} | {mean:+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | {pr} | **{v}** |")
    shown = any(all(verdicts.get(h) == "SUPPORTED" for h in hs) for hs in (("INP-H1", "INP-H3", "INP-H5"), ("INP-H2", "INP-H4", "INP-H6")))
    L += ["", f"**Headline: input-facing code {'IS' if shown else 'is NOT'} shown** (needs H1+H3+H5 or H2+H4+H6).", "",
          "| repo | quarterly snapshots | with CVE positive | CVE commits | files with any IN (median) | files with any BUF (median) |",
          "|---|---:|---:|---:|---:|---:|"]
    for r, d in desc.items():
        L.append(f"| {r} | {d['snaps']} | {d['lat_snaps']} | {d['n_lat']} | {d['any_in']:.1%} | {d['any_buf']:.1%} |")
    L += ["", f"Runtime {time.time() - t0:.0f}s · within-repo snapshot bootstrap, {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "inp.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
