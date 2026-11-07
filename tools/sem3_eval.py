#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""S3-H1..H2 (docs/sem3_hypotheses.md): SEM-3 = fix lines/fragments new to the whole file; zlib + expat; blind audit.

    SFS_SRC=... <engine venv>/bin/python tools/sem3_eval.py prepare | score
"""
from __future__ import annotations

import json
import multiprocessing
import pathlib
import random
import sys
import time
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cmb_eval as C  # noqa: E402
import sem_eval as S  # noqa: E402
import vz_eval as Z  # noqa: E402
import vzt_eval as T  # noqa: E402

PRIV = C.PRIV
SEED, CAP, ALPHA = 2986, 30, 0.01 / 2
git = C.git


def code_set(text):
    return {x for x in (Z.U.norm(y) for y in text.splitlines()) if Z.code_line(x)}


def stream(text):
    return "\x01" + "\x01".join(S.norm_toks(text)) + "\x01"


def augment(libs):
    """Add A*, R*, F* to every (fix, file) of both libraries."""
    revs = {}  # (lib, fix key) -> [(repo, pre_rev, post_rev)]
    for f in Z.FIXES:
        revs[("zlib", f[:9])] = [(Z.ZLIB, f + "^", f)]
    for it in C.expat_fixes():
        revs[("expat", it["merges"][0][:9])] = [(C.EXPAT, m + "^1", m) for m in it["merges"]]
    for ln, lib in libs.items():
        for fk, fx in lib["fixes"].items():
            for stem_, ra in fx["files"].items():
                pre_lines, post_lines, pre_stream = set(), set(), ""
                for repo, pre, post in revs[(ln, fk)]:
                    paths = [p for p in git(repo, "diff", "--name-only", pre, post).split() if C.stem(p) == stem_]
                    for p in paths:
                        a, b = git(repo, "show", f"{pre}:{p}"), git(repo, "show", f"{post}:{p}")
                        pre_lines |= code_set(a)
                        post_lines |= code_set(b)
                        pre_stream += stream(a)
                ra["A3"] = {x for x in ra["A"] if x not in pre_lines}
                ra["R3"] = {x for x in ra["R"] if x not in post_lines}
                frags = set()
                for x in ra["A"]:
                    frags |= S.fragments({x})
                ra["F3"] = {x for x in frags if not S.present(x, pre_stream)}
    return libs


def sem3(text, ra):
    lines = {Z.U.norm(x) for x in text.splitlines()}
    if ra["F3"]:
        st = stream(text)
        if sum(S.present(f, st) for f in ra["F3"]) / len(ra["F3"]) >= 0.5:
            return "patched"
    if ra["A3"] and sum(x in lines for x in ra["A3"]) / len(ra["A3"]) >= 0.5:
        return "patched"
    if ra["R3"] and sum(x in lines for x in ra["R3"]) / len(ra["R3"]) >= 0.5:
        return "unpatched"
    return "undetermined"


def build():
    libs = augment(C.libraries())
    tasks = []
    for ln, lib in libs.items():
        for name, cfg in lib["hosts"].items():
            tasks += [(ln, name, cfg[0], cfg[1], lib["files"], s, c) for s, c in C.states_of(lib, name, cfg)]
    with multiprocessing.get_context("fork").Pool(8) as p:
        states = list(p.imap_unordered(C.state_files, tasks, chunksize=2))
    units = []
    for ln, name, sha, ct, ver, texts in states:
        lib = libs[ln]
        for fk, fx in lib["fixes"].items():
            rel = fx["release"]
            for fname, ra in fx["files"].items():
                if fname not in texts or not (ra["R"] or ra["A"]):
                    continue
                txt = texts[fname]
                verb = lib["up"].get(fname, {}).get(T.normws(txt))
                cvv, _ = C.cv_verdict(lib["up"].get(fname, {}), txt, rel)
                units.append({"lib": ln, "host": name, "sha": sha[:12], "fix": fk, "file": fname,
                              "sem3": sem3(txt, ra), "sem2": S.sem(txt, ra["R"], ra["A"], ra["F"]), "cv": cvv,
                              "truth": None if not verb else ("patched" if verb >= rel else "unpatched")})
    return libs, states, units


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    t0 = time.time()
    libs, states, units = build()
    L = ["# S3-H1..H2 — SEM-3 (new-to-file fix lines) on zlib + expat (SCORED; aggregates only)", "",
         f"- units {len(units):,}; host states {len(states):,}", "",
         "| claim | result | verdict |", "|---|---|---|"]
    ok1, parts = True, []
    for ln in libs:
        vv = [u for u in units if u["lib"] == ln and u["truth"]]
        dec = [u for u in vv if u["sem3"] in ("patched", "unpatched")]
        w = sum(u["sem3"] != u["truth"] for u in dec)
        up = 1 - T.wilson(len(dec) - w, len(dec)) if dec else float("nan")
        ok1 &= bool(dec) and w / len(dec) <= 0.01 and up <= 0.02
        parts.append(f"{ln}: wrong {w}/{len(dec)} decided (upper {up:.2%}), coverage {len(dec) / max(len(vv), 1):.0%} of {len(vv)} verbatim")
    L.append(f"| **S3-H1** no new errors on verbatim truth, each library | {'; '.join(parts)} | **{'SUPPORTED' if ok1 else 'not supported'}** |")
    # audit sample, excluding earlier audited units
    used = set()
    for f in ("cmb_audit_keys.json",):
        used |= {(u["host"], u["sha"], u["fix"], u["file"]) for u in json.loads((PRIV / f).read_text())}
    for f, k in (("vzt_timelines.json", "audit_sample"),):
        used |= {(u["host"], u["sha"], u["fix"], u["file"]) for u in json.loads((PRIV / f).read_text())[k]}
    for f in ("sem_audit.json", "sem2_audit.json"):
        used |= {(u["host"], u["sha"], u["fix"], u["file"]) for u in json.loads((PRIV / f).read_text())["units"]}
    rnd = random.Random(SEED)
    sample = []
    for ln in libs:
        d = sorted((u for u in units if u["lib"] == ln and not u["truth"] and u["sem3"] in ("patched", "unpatched") and u["cv"]
                    and u["sem3"] != u["cv"] and (u["host"], u["sha"], u["fix"], u["file"]) not in used),
                   key=lambda u: (u["host"], u["sha"], u["fix"], u["file"]))
        sample += rnd.sample(d, CAP) if len(d) > CAP else d
    if mode == "prepare":
        stmap = {(s[0], s[1], s[2][:12]): s for s in states}
        packets = []
        for i, u in enumerate(sample):
            fx = libs[u["lib"]]["fixes"][u["fix"]]
            texts = stmap[(u["lib"], u["host"], u["sha"])][5]
            packets.append({"id": i, "library": u["lib"], "vulnerability": fx["text"], "file": u["file"],
                            "upstream_fix_diff": fx["diff"].get(u["file"], "")[:15000],
                            "host_code_of_changed_functions": C.fn_excerpt(texts[u["file"]], set(fx["files"][u["file"]]["pre"]))})
        (PRIV / "sem3_audit_packets.json").write_text(json.dumps(packets, indent=1))
        (PRIV / "sem3_audit_keys.json").write_text(json.dumps(sample, indent=1))
        heads = sum(p["host_code_of_changed_functions"].lstrip().startswith(("/*", "#", "//")) for p in packets)
        L.append(f"- audit packets {len(packets)} (" + ", ".join(f"{ln} {sum(u['lib'] == ln for u in sample)}" for ln in libs) + f"); packets starting at a file header: {heads}")
    else:
        from scipy.stats import binomtest
        keys = json.loads((PRIV / "sem3_audit_keys.json").read_text())
        lab = sorted(json.loads((PRIV / "sem3_audit_labels.json").read_text()), key=lambda x: x["id"])
        per = {}
        s_ok = c_ok = n = 0
        for k, l in zip(keys, lab):
            if l["label"] not in ("patched", "unpatched"):
                continue
            n += 1
            s_ok += k["sem3"] == l["label"]
            c_ok += k["cv"] == l["label"]
            r = per.setdefault(k["lib"], [0, 0, 0])
            r[0] += 1
            r[1] += k["sem3"] == l["label"]
            r[2] += k["cv"] == l["label"]
        p = binomtest(s_ok, s_ok + c_ok, 0.5, alternative="greater").pvalue if s_ok + c_ok else 1.0
        v = "not evaluable" if n < 10 else ("SUPPORTED" if s_ok > c_ok and p < ALPHA else "not supported")
        L.append(f"| **S3-H2** SEM-3 beats closest-version (fresh blind audit) | SEM-3 right {s_ok}/{n}, CV right {c_ok}/{n}; sign test p = {p:.2g} | **{v}** |")
        L.append("- per library (labelled n, SEM-3 right, CV right): " + ", ".join(f"{k} {v}" for k, v in per.items()))
    L += ["", "## Descriptive", ""]
    for ln in libs:
        uu = [u for u in units if u["lib"] == ln]
        vv = [u for u in uu if u["truth"]]
        for m in ("sem3", "sem2", "cv"):
            dec = [u for u in vv if u[m] in ("patched", "unpatched")]
            L.append(f"- {ln} {m}: verbatim wrong {sum(u[m] != u['truth'] for u in dec)}/{len(dec)}; coverage all units "
                     f"{sum(u[m] in ('patched', 'unpatched') for u in uu) / max(len(uu), 1):.0%}")
    cmbk = json.loads((PRIV / "cmb_audit_keys.json").read_text())
    cmbl = sorted(json.loads((PRIV / "cmb_audit_labels.json").read_text()), key=lambda x: x["id"])
    idx = {(u["host"], u["sha"], u["fix"], u["file"]): u for u in units}
    ins = Counter()
    for k, l in zip(cmbk, cmbl):
        u = idx.get((k["host"], k["sha"], k["fix"], k["file"]))
        if u and l["label"] in ("patched", "unpatched"):
            ins[(k["lib"], "sem3 right" if u["sem3"] == l["label"] else "sem3 wrong/abstain")] += 1
    L += [f"- CMB's audited units (in-sample; motivated the design): {dict(ins)}", "", f"Runtime {time.time() - t0:.0f}s · seed {SEED}."]
    out = C.DOCS_DIR / ("sem3.md" if mode == "score" else "sem3_prepare.md")
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
