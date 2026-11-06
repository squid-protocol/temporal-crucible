#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""XC harvest: label every non-merge mainline commit as latent / regression / extrinsic / other-fix
(docs/xc_hypotheses.md, registered 2026-11-06). Rules are applied in that order; first match wins.

    python tools/xc_harvest.py --repo curl          -> events/curl_xc.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import POOL_DIR, REPO_ROOT  # noqa: E402

DAY = 86400
MAX_C_FILES = 50
REGR_DAYS = 90
FIXLIKE = re.compile(r"\b(fix(es|ed)?|bug|broke(n)?|break(s|age)?|regress\w*|crash\w*|wrong|incorrect|segfault|leak|"
                     r"overflow|oops|restore)\b", re.I)
REGR_WORD = re.compile(r"\bregress(ion|ed|es)?\b", re.I)
REVERT_SUBJ = re.compile(r'^Revert "')
REVERT_BODY = re.compile(r"This reverts commit [0-9a-f]{7,40}")
SHA_TOKEN = re.compile(r"(?<![0-9a-zA-Z])[0-9a-f]{7,40}(?![0-9a-zA-Z])")
EXT_ENV = re.compile(
    r"\b(gcc\d*|clang\d*|msvc|visual studio|vs20\d\d|mingw\w*|cygwin|msys\w*|windows|win32|win64|uwp|macos|mac os|osx|"
    r"darwin|apple|freebsd|netbsd|openbsd|dragonfly|android|ios|solaris|illumos|aix|hp-?ux|haiku|qnx|vxworks|"
    r"32-?bit|64-?bit|big.?endian|little.?endian|endian\w*|glibc|musl|uclibc|c89|c90|c99|c11|c17|c23|ansi c|"
    r"openssl\s*[0-9.]*|boringssl|libressl|wolfssl|mbedtls|gnutls|schannel|securetransport|nss|rustls|quiche|ngtcp2|"
    r"nghttp2|nghttp3|libssh2?|zlib|brotli|zstd|libidn2?|c-ares|libpsl|libpcap|gcrypt|libgcrypt|json-c|"
    r"newer|older|api change|deprecat\w*|toolchain|cross-?compil\w*|sanitizer version|autoconf|automake|libtool|"
    r"cmake|compiler|linker|-W[a-z-]+|warnings?)\b", re.I)
EXT_ACTION = re.compile(r"\b(fix(es|ed)?|silence\w*|suppress\w*|avoid\w*|work ?around|adapt\w*|compat\w*|port(ed|ing)?|"
                        r"make .{0,40}\b(build|compile|work)\w*|build(s)? (with|on|again)|compile(s)? (with|on)|"
                        r"support)\b", re.I)


def _git(repo, *a, inp=None):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, errors="replace",
                          input=inp).stdout


def is_c(p):
    return p.endswith((".c", ".h"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    repo = POOL_DIR / a.repo
    walk = json.loads((REPO_ROOT / "walks" / f"{a.repo}_quarterly.json").read_text())
    head = walk["events_head"]
    first_ct = int(_git(repo, "show", "-s", "--format=%ct", walk["revisions"][0]["sha"]).strip())
    since = first_ct - 365 * DAY
    sec = {e["sha"] for e in json.loads((REPO_ROOT / "events" / f"{a.repo}.json").read_text())["events"]
           if e["class"] == "security-fix" and e.get("on_master", True)}

    raw = _git(repo, "-c", "core.quotepath=off", "log", "--no-merges", f"--since={since}", "--name-only",
               "--format=%x00%x01%H%x1f%ct%x1f%s%x1f%b%x1f", head)
    commits = []
    for chunk in raw.split("\x00\x01")[1:]:
        h, ct, subj, body, files = chunk.split("\x1f", 4)
        commits.append({"sha": h, "ct": int(ct), "subject": subj.strip(), "body": body.strip(),
                        "files": [f for f in files.strip().splitlines() if f.strip()]})
    ct_of = {c["sha"]: c["ct"] for c in commits}

    # resolve every SHA-looking token once
    tokens = sorted({t for c in commits for t in SHA_TOKEN.findall(c["subject"] + "\n" + c["body"])})
    resolved = {}
    if tokens:
        out = _git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)", inp="\n".join(t + "^{commit}" for t in tokens) + "\n")
        for t, line in zip(tokens, out.splitlines()):
            parts = line.split()
            if len(parts) == 2 and parts[1] == "commit":
                resolved[t] = parts[0]

    counts, out_events = Counter(), []
    for c in commits:
        cf = [f for f in c["files"] if is_c(f)]
        if not cf:
            counts["no C file"] += 1
            continue
        if len(cf) > MAX_C_FILES:
            counts["sweep (> 50 C files)"] += 1
            continue
        msg = c["subject"] + "\n" + c["body"]
        fixlike = bool(FIXLIKE.search(msg))
        cls, why = None, ""
        if c["sha"] in sec:
            cls, why = "latent", "security-fix event"
        else:
            if REVERT_SUBJ.search(c["subject"]) or REVERT_BODY.search(c["body"]):
                cls, why = "regression", "revert"
            elif fixlike:
                if REGR_WORD.search(msg):
                    cls, why = "regression", "regression word"
                else:
                    for t in SHA_TOKEN.findall(msg):
                        full = resolved.get(t)
                        if not full or full == c["sha"]:
                            continue
                        rct = ct_of.get(full) or int(_git(repo, "show", "-s", "--format=%ct", full).strip() or 0)
                        if 0 < c["ct"] - rct <= REGR_DAYS * DAY and subprocess.run(
                                ["git", "-C", str(repo), "merge-base", "--is-ancestor", full, c["sha"]]).returncode == 0:
                            cls, why = "regression", f"references {full[:10]} ({(c['ct'] - rct) // DAY} d earlier)"
                            break
            if cls is None and EXT_ENV.search(c["subject"]) and EXT_ACTION.search(c["subject"]):
                cls, why = "extrinsic", f"env '{EXT_ENV.search(c['subject']).group(0)}'"
            if cls is None and fixlike:
                cls, why = "other-fix", ""
        if cls is None:
            counts["not a fix"] += 1
            continue
        counts[cls] += 1
        out_events.append({"sha": c["sha"], "ct": c["ct"], "class": cls, "why": why, "subject": c["subject"],
                           "c_files": cf})
    dest = REPO_ROOT / "events" / f"{a.repo}_xc.json"
    dest.write_text(json.dumps({"repo": a.repo, "head": head, "branch": walk.get("branch"), "since": since,
                                "rules": "docs/xc_hypotheses.md (2026-11-06)", "counts": dict(counts),
                                "events": out_events}, indent=1))
    print(a.repo, len(commits), "commits;", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
