#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""Apply the registered PANEL exclusion to the frame candidates, then fingerprint the result.

Required before the seeded draw by **Amendment 8 item 1**: the frame search writes RAW GitHub search
candidates, and every repo the registration excludes still appears among them, while no code anywhere
in tools/laws_*.py applied the exclusion. Since the draw is "uniformly at random from the eligible
list", an unfiltered list would silently draw an excluded repo and the guard would fail at exactly the
step it exists to protect.

This tool does three things and nothing else:
  1. removes the excluded repos from each language's candidate list;
  2. logs every removal by name, per language, so the draw record shows what went;
  3. writes the POST-EXCLUSION candidate list and its fingerprint (M9).

**The exclusion list is the registration's own** (PANEL, "Excluded"), transcribed below - this tool
does not invent or widen it.

### An honest limit, and why this tool warns instead of guessing

The registered rule is prose: "every repo used in any temporal-crucible study to date", followed by a
list of names. The names are machine-checkable; "every repo used in any study" is not, because no
machine-readable record of that set exists. So the tool:
  - removes everything the registration NAMES (exact `owner/repo` and bare-name matches), and
  - **warns** about any surviving candidate whose repo name matches a directory in the clone pool,
    which is the de facto record of what this programme has actually scanned.
A warning is not a removal. The operator resolves each warning and records the decision with the draw.
Silently widening a registered exclusion would be as wrong as not applying it.

    python tools/laws_exclude.py --frame <laws-study>/pilot/frame --out <laws-study>/pilot/panel
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

# ---- the registration's own exclusion list (PANEL, "Excluded"), transcribed ---------------------
# "every repo used in any temporal-crucible study to date (curl, OpenSSL, libarchive, harfbuzz, nDPI,
#  zlib, expat, the KF-R libraries, PostgreSQL, libgit2, libxml2, redis, prometheus, commons-lang,
#  sphinx, ripgrep, GitGalaxy) and the gitgalaxy population-DB pilot repos."
# Amendment 0 also excludes the ACC repos (apache/commons-io among them) and the engine's call-graph
# gate corpus (tests/import_graph_corpus.json), read from disk below when present.
# Matched on the FULL owner/repo, case-insensitively. Bare-name matching was tried first and
# over-removed badly: sphinxsearch/sphinx is a search engine, not sphinx-doc/sphinx; amov-lab/Prometheus
# is a drone autopilot; cujojs/curl and MishaLaskin/curl are a JS module loader and an RL paper.
# Dropping eligible repos that were never studied biases the frame exactly as much as keeping repos
# that were, so unexpected name collisions are WARNED about, never removed.
EXCLUDED_REPOS = {
    "curl/curl", "openssl/openssl", "libarchive/libarchive", "harfbuzz/harfbuzz", "ntop/ndpi",
    "madler/zlib", "libexpat/libexpat", "postgres/postgres", "libgit2/libgit2", "gnome/libxml2",
    "redis/redis", "prometheus/prometheus", "apache/commons-lang", "sphinx-doc/sphinx",
    "burntsushi/ripgrep",
    "apache/commons-io",                         # Amendment 0: ACC repo
    "google/boringssl", "pnggroup/libpng", "glennrp/libpng", "libsdl-org/libtiff",
    "libtiff/libtiff", "libexif/libexif", "file/file",   # the KF-R libraries
}
# Bare names of the excluded projects. A candidate whose repo name matches one of these but whose
# owner/repo is NOT in EXCLUDED_REPOS is reported for the operator to resolve, and is kept.
EXCLUDED_BARE = {r.split("/")[-1] for r in EXCLUDED_REPOS} | {"ndpi", "expat", "gitgalaxy", "commons-lang3"}

# Amendment 1 item 3 — the engine-tuning set. The engine is tuned on these, so they cannot validate it.
ENGINE_TUNING = {
    "google/leveldb", "gabime/spdlog", "jbeder/yaml-cpp",                      # C++
    "jqlang/jq", "facebook/zstd", "jedisct1/libsodium",                        # C
    "sharkdp/fd", "sharkdp/hyperfine", "casey/just",                           # Rust
    "immerjs/immer", "ianstormtaylor/superstruct", "typestack/class-validator",  # TypeScript
    "psf/requests", "pallets/click", "python-attrs/attrs",                     # Python
    "jhy/jsoup", "jodaorg/joda-time",                                          # Java
    "gin-gonic/gin", "spf13/viper",                                            # Go
    "koajs/koa",                                                               # JavaScript
}
# Amendment 2 item 6 — the language-admission survey repos, and any logged substitute.
SURVEY_REPOS = {"jamesnk/newtonsoft.json", "square/kotlinpoet", "composer/composer"}

# Where each removal came from, for the draw log.
SOURCES = [("PANEL 'Excluded'", EXCLUDED_REPOS),
           ("Amendment 1 item 3 (engine-tuning set)", ENGINE_TUNING),
           ("Amendment 2 item 6 (survey repos)", SURVEY_REPOS)]

POOL_DIR = Path(os.environ.get("EXPOSURE_POOL", "/srv/storage_16tb/projects/temporal-crucible-pool"))
NON_REPO_POOL = {"gg_weekly_scans", "kw_scan", "agent_habits_scans", "ossfuzz-coverage",
                 "openssl-release-metadata", "ut_forks", "ut_private", "vz_hosts", "vz_private",
                 "vz_scans", "vzt_hist"}


def norm(name: str) -> str:
    """Bare repo name, lowercased, with common decorations stripped."""
    base = name.split("/")[-1].lower()
    return re.sub(r"[._]", "-", base)


def full(name: str) -> str:
    """owner/repo, lowercased, decorations normalised."""
    return re.sub(r"[._]", "-", name.strip().lower())


def pool_names() -> set[str]:
    if not POOL_DIR.is_dir():
        return set()
    return {norm(p.name) for p in POOL_DIR.iterdir()
            if p.is_dir() and p.name not in NON_REPO_POOL}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True, type=Path, help="dir of <language>.json from the frame search")
    ap.add_argument("--out", required=True, type=Path, help="dir for the post-exclusion lists")
    ap.add_argument("--corpus", type=Path,
                    help="the ENGINE repo's tests/import_graph_corpus.json (Amendment 1 item 3). "
                         "It lives in gitgalaxy, not here; if omitted the tool says so and that "
                         "part of the exclusion is NOT applied.")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    by_source = {label: {full(n) for n in names} for label, names in SOURCES}
    corpus = set()
    if a.corpus and a.corpus.exists():
        try:
            raw = json.loads(a.corpus.read_text())
        except ValueError:
            raw = None
        if isinstance(raw, dict):
            raw = raw.get("repos") or raw.get("entries") or list(raw)
        for e in raw or []:
            v = e.get("repo") or e.get("name") or e.get("slug") if isinstance(e, dict) else e
            if isinstance(v, str) and "/" in v:
                corpus.add(full(v))
        by_source["Amendment 1 item 3 (call-graph gate corpus)"] = corpus
    excluded = set().union(*by_source.values())
    pool = pool_names()
    warn_bare = EXCLUDED_BARE | pool

    report, combined, total_in, total_out = [], hashlib.sha256(), 0, 0
    warnings = []
    for fp in sorted(a.frame.glob("*.json")):
        lang = fp.stem
        d = json.loads(fp.read_text())
        cands = d.get("candidates") or []
        kept, removed = [], []
        for c in cands:
            (removed if full(c) in excluded else kept).append(c)
        hits = sorted({c for c in kept if norm(c) in warn_bare})
        warnings += [(lang, h) for h in hits]

        kept = sorted(set(kept))
        digest = hashlib.sha256("\n".join(kept).encode()).hexdigest()
        combined.update(f"{lang}:{digest}\n".encode())
        total_in += len(cands)
        total_out += len(kept)
        out = {"language": lang, "n_candidates_in": len(cands), "n_candidates_out": len(kept),
               "removed": sorted(removed), "n_removed": len(removed),
               "removed_by_source": {lab: sorted(r for r in removed if full(r) in names)
                                     for lab, names in by_source.items()
                                     if any(full(r) in names for r in removed)},
               "fingerprint_sha256": digest,
               "fingerprint_definition": "sha256 of the newline-joined, de-duplicated, sorted "
                                         "post-exclusion candidate list",
               "exclusion_source": "registration PANEL 'Excluded' + Amendment 1 item 3 + "
                                   "Amendment 2 item 6; applied per Amendment 8 item 1",
               "candidates": kept}
        (a.out / f"{lang}_eligible.json").write_text(json.dumps(out, indent=1))
        report.append((lang, len(cands), len(kept), sorted(removed), digest))

    print(f"{'language':12s} {'in':>7s} {'out':>7s} {'removed':>8s}  fingerprint")
    for lang, n_in, n_out, rm, dg in report:
        print(f"{lang:12s} {n_in:7d} {n_out:7d} {len(rm):8d}  {dg[:16]}…")
        for r in rm:
            print(f"               - removed: {r}")
    print(f"\ntotal candidates {total_in} -> {total_out}  ({total_in - total_out} removed)")
    if not (a.corpus and a.corpus.exists()):
        print("!! --corpus not supplied: the call-graph gate corpus part of Amendment 1 item 3 was")
        print("   NOT applied. Pass the engine repo's tests/import_graph_corpus.json before the draw.")
    print(f"COMBINED FINGERPRINT (M9): {combined.hexdigest()}")
    (a.out / "fingerprint.json").write_text(json.dumps(
        {"combined_sha256": combined.hexdigest(),
         "per_language": {l: d for l, _, _, _, d in report},
         "definition": "sha256 over '<lang>:<per-language digest>\\n' for languages in sorted order",
         "required_by": "Amendment 8 item 1"}, indent=1) + "\n")

    (a.out / "name_collisions.json").write_text(json.dumps(
        [{"language": l, "candidate": c} for l, c in warnings], indent=1) + "\n")
    if warnings:
        print(f"\n!! {len(warnings)} surviving candidate(s) share a BARE NAME with an excluded project")
        print("   or a clone-pool directory, but their owner/repo is not on the registered list.")
        print("   They are KEPT. Each is a different project unless shown otherwise; resolve against")
        print('   "every repo used in any temporal-crucible study to date" and record the decision')
        print("   with the draw. Written to name_collisions.json:")
        for lang, c in warnings:
            print(f"     {lang:10s} {c}")
    else:
        print("\nno bare-name collisions among the surviving candidates")


if __name__ == "__main__":
    main()
