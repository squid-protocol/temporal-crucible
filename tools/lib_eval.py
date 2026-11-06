#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LIB-H1..H3: does a file's coupling to a library predict where that library's work lands?
(docs/lib_hypotheses.md, registered 2026-11-06). Git only.

    python tools/lib_eval.py
"""
from __future__ import annotations

import datetime as dt
import json
import multiprocessing
import pathlib
import re
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR, REPO_ROOT  # noqa: E402
from sc_discover import recall20  # noqa: E402  (EA's recall_at, vectorised; verified identical)

OPENSSL = (r"#include\s*[<\"]openssl/|\b(?:SSL|SSL_CTX|EVP|X509|BIO|ERR|PEM|RSA|EC_KEY|BN|OPENSSL)_\w+\s*\(")
ZLIB = r"#include\s*[<\"]zlib\.h|\b(?:inflate|deflate)\w*\s*\(|\bz_stream\b"
MBED = r"#include\s*[<\"]mbedtls/|\bmbedtls_\w+\s*\("
DEPS = {  # repo -> [(D, subject names, coupling regex)] -- the registered table, verbatim
    "curl": [("openssl", "openssl|boringssl|libressl|aws-lc|quictls", OPENSSL), ("zlib", "zlib", ZLIB),
             ("libssh2", "libssh2", r"#include\s*[<\"]libssh2|\blibssh2_\w+\s*\("),
             ("nghttp2", "nghttp2", r"#include\s*[<\"]nghttp2/|\bnghttp2_\w+\s*\("),
             ("c-ares", "c-ares|ares", r"#include\s*[<\"]ares\.h|\bares_\w+\s*\("),
             ("wolfssl", "wolfssl", r"#include\s*[<\"]wolfssl/|\bwolfSSL_\w+\s*\("),
             ("mbedtls", "mbedtls|mbed tls", MBED),
             ("gnutls", "gnutls", r"#include\s*[<\"]gnutls/|\bgnutls_\w+\s*\("),
             ("libidn2", "libidn2|idn2", r"#include\s*[<\"]idn2\.h|\bidn2_\w+\s*\(")],
    "libarchive": [("openssl", "openssl|libressl", OPENSSL), ("zlib", "zlib", ZLIB),
                   ("bzip2", "bzip2|bzlib", r"#include\s*[<\"]bzlib\.h|\bBZ2_\w+\s*\("),
                   ("xz", "xz|lzma|liblzma", r"#include\s*[<\"]lzma\.h|\blzma_\w+\s*\("),
                   ("zstd", "zstd", r"#include\s*[<\"]zstd\.h|\bZSTD_\w+\s*\("),
                   ("lz4", "lz4", r"#include\s*[<\"]lz4|\bLZ4\w*_\w+\s*\("),
                   ("libxml2", "libxml2|libxml", r"#include\s*[<\"]libxml/|\bxml(?:Text)?\w+\s*\("),
                   ("expat", "expat", r"#include\s*[<\"]expat\.h|\bXML_\w+\s*\("),
                   ("mbedtls", "mbedtls", MBED),
                   ("nettle", "nettle", r"#include\s*[<\"]nettle/|\bnettle_\w+\s*\(")],
    "ndpi": [("libgcrypt", "gcrypt|libgcrypt", r"#include\s*[<\"]gcrypt\.h|\bgcry_\w+\s*\("),
             ("json-c", "json-c|json_c", r"#include\s*[<\"](?:json-c/|json\.h)|\bjson_object_\w+\s*\("),
             ("libpcap", "pcap|libpcap", r"#include\s*[<\"]pcap|\bpcap_\w+\s*\("),
             ("maxminddb", "maxmind|maxminddb|geoip", r"#include\s*[<\"]maxminddb\.h|\bMMDB_\w+\s*\(")],
    "harfbuzz": [("freetype", "freetype", r"#include\s*(?:FT_\w+_H|[<\"]ft2build\.h)|\bFT_\w+\s*\("),
                 ("icu", "icu", r"#include\s*[<\"]unicode/|\b(?:u|ubrk|uscript|unorm2?)_\w+\s*\("),
                 ("coretext", "coretext|core text", r"#include\s*[<\"]CoreText|\bCT\w+\s*\("),
                 ("directwrite", "directwrite|dwrite", r"#include\s*[<\"]dwrite|\bIDWrite\w*"),
                 ("uniscribe", "uniscribe", r"#include\s*[<\"]usp10\.h|\bScript\w+\s*\("),
                 ("graphite", "graphite|graphite2", r"#include\s*[<\"]graphite2/|\bgr_\w+\s*\("),
                 ("glib", "glib", r"#include\s*[<\"]glib|\bg_\w+\s*\(")],
}
EXTS = {"curl": (".c", ".h"), "libarchive": (".c", ".h"), "ndpi": (".c", ".h"),
        "harfbuzz": (".c", ".h", ".cc", ".hh", ".cpp", ".hpp")}
SEED, ITERS, DAY, WINDOW, MIN_SNAPS, EQUIV = 2982, 5000, 86400, 180, 20, 0.02
ALPHA = 0.01 / 3


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


def work_commits(repo_name):
    repo = POOL_DIR / repo_name
    walk = json.loads((REPO_ROOT / "walks" / f"{repo_name}_quarterly.json").read_text())
    exts = EXTS[repo_name]
    subj = {d: re.compile(rf"\b(?:{s})\b", re.I) for d, s, _ in DEPS[repo_name]}
    raw = _git(repo, "-c", "core.quotepath=off", "log", "--no-merges", "--name-only", "--format=%x00%H%x1f%ct%x1f%s", walk["events_head"])
    out = defaultdict(list)
    for chunk in raw.split("\x00")[1:]:
        head, _, files = chunk.partition("\n")
        h, ct, s = head.split("\x1f", 2)
        cf = [f for f in files.splitlines() if f.strip() and f.endswith(exts)]
        if not 1 <= len(cf) <= 50:
            continue
        for d, rx in subj.items():
            if rx.search(s):
                out[d].append({"sha": h, "ct": int(ct), "subject": s, "files": cf})
    return out


def snapshot_task(task):
    repo_name, sha = task
    repo = POOL_DIR / repo_name
    exts = EXTS[repo_name]
    lines = grep_counts(repo, sha, "", exts)
    coup = {d: grep_counts(repo, sha, pat, exts) for d, _, pat in DEPS[repo_name]}
    return sha, lines, coup


def main() -> int:
    t0 = time.time()
    units, desc, desc_mig = {}, [], []
    for repo_name in DEPS:
        repo = POOL_DIR / repo_name
        walk = json.loads((REPO_ROOT / "walks" / f"{repo_name}_quarterly.json").read_text())
        snaps = [s for s in walk["revisions"] if s.get("status", "ok") == "ok"]
        for s in snaps:
            s["ct"] = int(_git(repo, "show", "-s", "--format=%ct", s["sha"]).strip())
        work = work_commits(repo_name)
        with multiprocessing.get_context("fork").Pool(6) as p:
            data = {sha: (ln, cp) for sha, ln, cp in p.imap_unordered(snapshot_task, [(repo_name, s["sha"]) for s in snaps])}
        deps = [d for d, _, _ in DEPS[repo_name]]
        subj_tok = {d: [t.strip().lower() for t in s.split("|")] for d, s, _ in DEPS[repo_name]}
        per = {d: [] for d in deps}
        for s in snaps:
            lines, coup = data[s["sha"]]
            if not lines:
                continue
            paths = sorted(lines)
            loc = np.array([float(max(lines[p], 1)) for p in paths])
            pr = np.argsort(np.argsort(np.array(paths)))
            S = {d: np.array([coup[d].get(p, 0) for p in paths], dtype=float) / loc for d in deps}
            for d in deps:
                touched = set()
                for c in work[d]:
                    if s["ct"] < c["ct"] <= s["ct"] + WINDOW * DAY:
                        touched.update(c["files"])
                y = np.array([1.0 if p in touched else 0.0 for p in paths])
                if y.sum() == 0:
                    continue
                base = max(recall20(loc, loc, pr, y), recall20(-loc, loc, pr, y))
                r_d = recall20(S[d], loc, pr, y)
                others = [recall20(S[o], loc, pr, y) for o in deps if o != d]
                path = np.array([1.0 if any(t in p.lower() for t in subj_tok[d]) else 0.0 for p in paths])
                per[d].append({"h1": r_d - base, "h2": r_d - float(np.mean(others)), "h3": r_d - recall20(path, loc, pr, y),
                               "r_d": r_d, "base": base, "pos": int(y.sum())})
        if "openssl" in deps and repo_name in ("curl", "libarchive"):  # registered descriptive: the OpenSSL 3 migration
            lo_t = dt.datetime(2020, 6, 1, tzinfo=dt.timezone.utc).timestamp()
            hi_t = dt.datetime(2023, 1, 1, tzinfo=dt.timezone.utc).timestamp()
            shares = []
            for c in work["openssl"]:
                if not lo_t <= c["ct"] < hi_t:
                    continue
                prev = [x for x in snaps if x["ct"] < c["ct"]]
                if not prev:
                    continue
                lines, coup = data[prev[-1]["sha"]]
                paths = sorted(lines)
                loc = np.array([float(max(lines[p], 1)) for p in paths])
                sc = np.array([coup["openssl"].get(p, 0) for p in paths], dtype=float) / loc
                order = np.lexsort((np.argsort(np.argsort(np.array(paths))), loc, -sc))
                k = int(np.searchsorted(np.cumsum(loc[order]), 0.2 * loc.sum(), side="right"))
                top = {paths[i] for i in order[:k]}
                t = [f for f in c["files"] if f in lines]
                if t:
                    shares.append(sum(f in top for f in t) / len(t))
            if shares:
                desc_mig.append((repo_name, len(shares), float(np.mean(shares))))
        for d in deps:
            n = len(per[d])
            desc.append((repo_name, d, len(work[d]), n))
            if n >= MIN_SNAPS:
                units[(repo_name, d)] = per[d]
        print(f"{repo_name}: done ({time.time() - t0:.0f}s)", flush=True)

    rng_seq = iter(np.random.SeedSequence(SEED).spawn(4))
    L = ["# LIB-H1..H3 — library-coupling surface (SCORED)", "",
         f"- evaluable (repo, dependency) units (≥ {MIN_SNAPS} snapshots with D-work): **{len(units)}** — " +
         ", ".join(f"{r}/{d}" for r, d in units), "",
         "| claim | what | units | mean | lo (α=0.0033) | 90% CI | verdict |", "|---|---|---:|---:|---:|---|---|"]
    what = {"h1": "coupling to D − stronger size order (recall@20)", "h2": "coupling to D − other libraries' coupling (placebo)",
            "h3": "coupling to D − file-name lookup"}
    for c, key in (("LIB-H1", "h1"), ("LIB-H2", "h2"), ("LIB-H3", "h3")):
        arrs = [np.array([x[key] for x in v]) for v in units.values()]
        mean = float(np.mean([a.mean() for a in arrs])) if arrs else float("nan")
        rng = np.random.default_rng(next(rng_seq))
        if len(arrs) == 0:
            L.append(f"| **{c}** | {what[key]} | 0 | — | — | — | **not evaluable** |")
            continue
        b = np.array([np.mean([a[rng.integers(0, len(a), len(a))].mean() for a in arrs]) for _ in range(ITERS)])
        lo, ci = float(np.quantile(b, ALPHA)), (float(np.quantile(b, 0.05)), float(np.quantile(b, 0.95)))
        v = ("SUPPORTED" if mean > 0 and lo > 0 else
             "replicated null (equivalence)" if -EQUIV < ci[0] and ci[1] < EQUIV else "not supported (inconclusive)")
        L.append(f"| **{c}** | {what[key]} | {len(arrs)} | {mean:+.3f} | {lo:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] | **{v}** |")
    L += ["", "## Per unit (descriptive)", "", "| repo | dependency | D-work commits | scored snapshots | recall@20 coupling | stronger size | H1 | H2 | H3 |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r, d, nc, ns in desc:
        v = units.get((r, d))
        if v:
            L.append(f"| {r} | {d} | {nc} | {ns} | {np.mean([x['r_d'] for x in v]):.3f} | {np.mean([x['base'] for x in v]):.3f} | "
                     f"{np.mean([x['h1'] for x in v]):+.3f} | {np.mean([x['h2'] for x in v]):+.3f} | {np.mean([x['h3'] for x in v]):+.3f} |")
        else:
            L.append(f"| {r} | {d} | {nc} | {ns} | — | — | not evaluable | | |")
    L += ["", "OpenSSL 3 migration (OpenSSL-work commits 2020-06 → 2022-12; share of each commit's touched files that fall in "
          "the top-20%-of-lines set ranked by OpenSSL coupling at the preceding quarterly snapshot):", ""]
    L += [f"- {r}: {n} commits, mean share {m:.0%}" for r, n, m in desc_mig] or ["- none"]
    L += ["", f"Runtime {time.time() - t0:.0f}s · within-unit snapshot bootstrap, {ITERS} rounds, seed {SEED}."]
    (DOCS_DIR / "lib.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
