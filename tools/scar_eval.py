#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""SCAR-R1/R2, SCAR-I1/I2 (docs/scar_hypotheses.md): do the danger comments a CVE fix leaves behind mark lasting
fragility, and is DC-2's birth signal inherited from the file's past CVE fixes? Engine venv:

    GITGALAXY_PATH=$E PYTHONPATH=$E <venv>/bin/python tools/scar_eval.py

Comment span and lexicon are DC's (dc_eval.comment_task's span walk, dc_eval.DANGER); line normalisation is CFIX's
(whitespace-collapsed, >= 3 characters); fixes are chg_eval.fix_events / map_fix; function identity is
ints_eval.lives. Aggregates only; writes docs/scar.md.
"""
from __future__ import annotations

import bisect
import multiprocessing
import pathlib
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine import DOCS_DIR, POOL_DIR  # noqa: E402
from chg_eval import CEXT, CPPEXT, _fname, _git, _parser, fix_events, map_fix  # noqa: E402
from chg_eval import REPOS as REPOS_R  # noqa: E402
from dc_eval import DANGER, comment_task, prism  # noqa: E402
from ints_eval import REPOS as REPOS_I  # noqa: E402
from ints_eval import YEAR, lives, mh_rate  # noqa: E402

SEED, ITERS = 2982, 2000
ALPHA = 0.01 / 4
HORIZON = 5 * YEAR
MIN_EV = 15
CLS4 = ("latent", "other-fix", "regression", "extrinsic")
EDIT_BINS = (2, 8, 32)  # 1-2, 3-8, 9-32, > 32
HUNK2 = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
T0 = time.time()


def log(m):
    print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)


def norm(line):
    s = " ".join(line.split())
    return s if len(line.strip()) >= 3 else ""


def lang(r, path):
    return "c" if path.endswith(CEXT) and r != "harfbuzz" else "cpp"


def spans(raw, lg):
    """First span per name in DC's traversal order (dc_eval.comment_task)."""
    out = {}
    stack = [_parser(lg).parse(raw).root_node]
    while stack:
        n = stack.pop()
        if n.type == "function_definition":
            nm = _fname(n)
            if nm and nm not in out:
                out[nm] = (n.start_point[0], n.end_point[0])
            continue
        stack.extend(n.children)
    return out


def span_comments(pos, lines, a, b):
    """dc_eval.comment_task's walk: comment lines inside [a, b] plus the block directly above. Raw lines."""
    idx = [i for i in range(a, min(b + 1, len(pos))) if pos[i].strip()]
    i, blank = a - 1, 0
    while i >= 0:
        if i < len(pos) and pos[i].strip():
            idx.append(i)
            blank = 0
        elif not lines[i].strip() and blank == 0:
            blank = 1
        else:
            break
        i -= 1
    return [pos[i] for i in sorted(set(idx))]


def version(r, rev, path):
    raw = _git(POOL_DIR / r, "show", f"{rev}:{path}", text=False)
    if not raw:
        return None
    txt = raw.decode("utf-8", "replace")
    try:
        pos = prism().split_positional_comment_stream(txt, lang(r, path)).split("\n")
    except Exception:
        return None
    return raw, txt.split("\n"), pos, spans(raw, lang(r, path))


# ------------------------------------------------------------------ Part R: scars of one fix commit
def scar_task(t):
    r, sha, ct, klass = t
    repo = POOL_DIR / r
    parent = _git(repo, "rev-parse", "-q", "--verify", f"{sha}^").strip()
    if not parent:
        return []
    old, new, cur = defaultdict(set), defaultdict(set), None
    for ln in _git(repo, "diff", "-U0", "--no-color", "--no-renames", parent, sha).splitlines():
        if ln.startswith("--- "):
            m = re.match(r"^--- (?:a/(.*)|/dev/null)$", ln)
            cur = m.group(1) if m and m.group(1) and m.group(1).endswith(CEXT + CPPEXT) else None
            continue
        if cur and ln.startswith("@@"):
            h = HUNK2.match(ln)
            if h:
                s, n = int(h.group(1)), int(h.group(2) or 1)
                old[cur].update(range(s, s + n) if n > 0 else [max(s, 1)])  # map_fix's rule
                s2, n2 = int(h.group(3)), int(h.group(4) or 1)
                if n2 > 0:
                    new[cur].update(range(s2, s2 + n2))
    out = []
    for path, ls in old.items():
        before = version(r, parent, path)
        if before is None:
            continue
        after = version(r, sha, path)
        for nm, (a, b) in before[3].items():
            touched = sum(1 for l in ls if a + 1 <= l <= b + 1)
            if not touched:
                continue
            rec = {"r": r, "sha": sha, "ct": ct, "klass": klass, "path": path, "name": nm, "loc": b - a + 1}
            nsp = after[3].get(nm) if after else None
            if nsp is None:
                rec["missing"] = True
                out.append(rec)
                continue
            pre = {norm(x) for x in span_comments(before[2], before[1], a, b)} - {""}
            post = span_comments(after[2], after[1], *nsp)
            scar = sorted({norm(x) for x in post if DANGER.search(x) and norm(x) and norm(x) not in pre})
            rec.update(missing=False, scar=scar,
                       words=sorted({m.group(1).lower() for x in scar for m in DANGER.finditer(x)}),
                       edit=touched + sum(1 for l in new[path] if nsp[0] + 1 <= l <= nsp[1] + 1))
            out.append(rec)
    return out


def last_task(t):
    """Are a unit's scar lines still in the function's span at its last live snapshot?"""
    key, r, sha, path, nm, scar = t
    v = version(r, sha, path)
    if v is None or nm not in v[3]:
        return key, None
    now = {norm(x) for x in span_comments(v[2], v[1], *v[3][nm])}
    return key, all(s in now for s in scar)


def birth_lines_task(t):
    r, sha, path, names = t
    v = version(r, sha, path)
    out = {}
    if v is None:
        return r, sha, path, out
    for nm in names:
        sp = v[3].get(nm) or v[3].get(nm.split("::")[-1])
        if sp:
            out[nm] = sorted({norm(x) for x in span_comments(v[2], v[1], *sp) if DANGER.search(x) and norm(x)})
    return r, sha, path, out


# ------------------------------------------------------------------ statistics
def codes(labels):
    _, si = np.unique(labels, return_inverse=True)
    return si, int(si.max()) + 1 if len(si) else 0


def mh_rate_codes(e, ev, pt, si, ns):
    a, b = np.bincount(si, ev * e, ns), np.bincount(si, ev * (1 - e), ns)
    t1, t0 = np.bincount(si, pt * e, ns), np.bincount(si, pt * (1 - e), ns)
    T = t1 + t0
    ok = (t1 > 0) & (t0 > 0)
    den = np.sum(b[ok] * t1[ok] / T[ok])
    return np.sum(a[ok] * t0[ok] / T[ok]) / den if den > 0 else np.nan


def mh_or_codes(e, y, si, ns):
    a, b = np.bincount(si, e * y, ns), np.bincount(si, e * (1 - y), ns)
    c, d = np.bincount(si, (1 - e) * y, ns), np.bincount(si, (1 - e) * (1 - y), ns)
    n = a + b + c + d
    ok = n > 0
    R, S = (a * d)[ok] / n[ok], (b * c)[ok] / n[ok]
    return R.sum() / S.sum() if S.sum() > 0 else np.nan


def file_groups(cl):
    _, ci = np.unique(cl, return_inverse=True)
    order = np.argsort(ci, kind="stable")
    return np.split(order, np.flatnonzero(np.diff(ci[order])) + 1)


def boot(stat, groups, rng):
    out = []
    for _ in range(ITERS):
        pick = np.concatenate([groups[j] for j in rng.integers(0, len(groups), len(groups))])
        out.append(stat(pick))
    return np.array(out, float)


def edit_bin(x):
    return sum(x > c for c in EDIT_BINS)


# ------------------------------------------------------------------ main
def main() -> int:
    ev, last = [], {}
    for r in REPOS_R:
        e, last[r] = fix_events(r)
        ev += [x for x in e if x[3] in CLS4]
    with multiprocessing.get_context("fork").Pool(8) as p:
        hits = [h for hs in p.imap_unordered(map_fix, ev, chunksize=8) for h in hs]
        rows = [x for xs in p.imap_unordered(scar_task, [x for x in ev if x[3] in ("latent", "other-fix")],
                                             chunksize=8) for x in xs]
    log(f"fix events {len(ev):,}; mapped hits {len(hits):,}; touched functions (latent + other-fix) {len(rows):,}")

    # ---------------- Part R
    LV, units_all, excl = {}, {"latent": [], "other-fix": []}, Counter()
    for r in REPOS_R:
        snaps, ids_at, info = lives(r)
        cts = [s["ct"] for s in snaps]
        LV[r] = (snaps, ids_at, info, cts)

        def fid_of(path, nm, ct):
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                return None
            for jj in (j, j + 1):
                if jj < len(ids_at):
                    for cand in ((path, nm), (path, nm.split("::")[-1])):
                        if cand in ids_at[jj]:
                            return ids_at[jj][cand]
            return None

        later = defaultdict(lambda: defaultdict(list))
        for (_r, path, nm, ct, klass) in (h for h in hits if h[0] == r):
            f = fid_of(path, nm, ct)
            if f is not None:
                later[f][klass].append(ct)
        for k in ("latent", "other-fix"):
            first = {}
            for x in sorted((x for x in rows if x["r"] == r and x["klass"] == k), key=lambda x: (x["ct"], x["path"])):
                f = fid_of(x["path"], x["name"], x["ct"])
                if f is None:
                    excl[(k, "no function identity")] += 1
                    continue
                first.setdefault(f, x)
            for f, x in first.items():
                if x["missing"]:
                    excl[(k, "not found after the fix")] += 1
                    continue
                inf = info[f]
                death = cts[inf["last_k"] + 1] if inf["last_k"] + 1 < len(cts) else float("inf")
                ct0 = x["ct"]
                end = min(death, last[r], ct0 + HORIZON)
                if end <= ct0:
                    excl[(k, "no follow-up")] += 1
                    continue
                L1 = sorted(c for c in later[f]["latent"] if ct0 < c <= end)
                LA = sorted(c for kk in CLS4 for c in later[f][kk] if ct0 < c <= end)
                units_all[k].append({
                    "r": r, "file": x["path"], "name": x["name"], "fid": f, "ct0": ct0, "scar": bool(x["scar"]),
                    "scar_lines": x["scar"], "words": x["words"], "loc": x["loc"], "edit": x["edit"],
                    "y1": bool(L1), "pt1": ((L1[0] if L1 else end) - ct0) / YEAR,
                    "y2": bool(LA), "pt2": ((LA[0] if LA else end) - ct0) / YEAR,
                    "last_sha": snaps[inf["last_k"]]["sha"], "last_key": inf["key"]})
        log(f"{r}: CVE-fix units {sum(1 for u in units_all['latent'] if u['r'] == r):,}")

    def part_r(U):
        e = np.array([u["scar"] for u in U], float)
        st = np.array([f"{u['r']}|{int(np.floor(np.log10(max(u['loc'], 1)) / 0.25))}|{edit_bin(u['edit'])}" for u in U])
        si, ns = codes(st)
        groups = file_groups(np.array([f"{u['r']}:{u['file']}" for u in U]))
        res = {}
        for o in ("1", "2"):
            y = np.array([u["y" + o] for u in U], float)
            pt = np.array([u["pt" + o] for u in U], float)
            rr = mh_rate_codes(e, y, pt, si, ns)
            b = boot(lambda pk: mh_rate_codes(e[pk], y[pk], pt[pk], si[pk], ns), groups, np.random.default_rng(SEED))
            b = b[np.isfinite(b)]
            res[o] = {"rr": rr, "lo": float(np.quantile(b, ALPHA / 2)), "hi": float(np.quantile(b, 1 - ALPHA / 2)),
                      "ev_s": int((y * e).sum()), "ev_u": int((y * (1 - e)).sum()),
                      "rate_s": (y * e).sum() / (pt * e).sum(), "rate_u": (y * (1 - e)).sum() / (pt * (1 - e)).sum()}
        return e, res

    U = units_all["latent"]
    e_r, R = part_r(U)
    log(f"Part R: units {len(U):,}, scarred {int(e_r.sum())}; R1 {R['1']['rr']:.2f}, R2 {R['2']['rr']:.2f}")

    def call_r(x):
        if min(x["ev_s"], x["ev_u"]) < MIN_EV:
            return "underpowered"
        if x["lo"] > 1:
            return "SUPPORTED: lasting fragility (RR > 1)"
        if x["hi"] < 1:
            return "SUPPORTED: lesson learned (RR < 1)"
        return "not supported"

    # ---------------- Part I (DC-2's births, unchanged)
    ev_i = [x for x in ev if x[0] in REPOS_I]
    hits_i = [h for h in hits if h[0] in REPOS_I]
    UI = []
    for r in REPOS_I:
        snaps, ids_at, info, cts = LV[r]
        first, file_cve = defaultdict(dict), defaultdict(list)
        for (_r, path, nm, ct, klass) in (h for h in hits_i if h[0] == r):
            if klass == "latent":
                file_cve[path].append(ct)
            j = bisect.bisect_right(cts, ct) - 1
            if j < 0:
                continue
            fid = None
            for jj in (j, j + 1):
                if jj < len(ids_at) and fid is None:
                    for cand in ((path, nm), (path, nm.split("::")[-1])):
                        if cand in ids_at[jj]:
                            fid = ids_at[jj][cand]
                            break
            if fid is not None and (klass not in first[fid] or ct < first[fid][klass]):
                first[fid][klass] = ct
        for v in file_cve.values():
            v.sort()
        groups = defaultdict(list)
        for fid, inf in info.items():
            if inf["birth_k"] > 0 and inf["loc"] >= 3:
                groups[(snaps[inf["birth_k"]]["sha"], inf["key"][0])].append(inf["key"][1])
        with multiprocessing.get_context("fork").Pool(8) as p:
            cm = {(rr, sha, path): out for rr, sha, path, out in
                  p.imap_unordered(comment_task, [(r, sha, path, nms) for (sha, path), nms in groups.items()],
                                   chunksize=4)}
        for fid, inf in info.items():
            if inf["birth_k"] == 0 or inf["loc"] < 3:
                continue
            b = cts[inf["birth_k"]]
            death = cts[inf["last_k"] + 1] if inf["last_k"] + 1 < len(cts) else float("inf")
            end = min(death, last[r])
            if end <= b:
                continue
            c = cm.get((r, snaps[inf["birth_k"]]["sha"], inf["key"][0]), {}).get(inf["key"][1])
            if c is None or c[0] < 1:
                continue
            fl = first.get(fid, {}).get("latent")
            fl = fl if fl is not None and b < fl <= end else None
            UI.append({"r": r, "file": inf["key"][0], "name": inf["key"][1], "sha": snaps[inf["birth_k"]]["sha"],
                       "b": b, "lb": int(np.floor(np.log10(inf["loc"]) / 0.1)),
                       "prior": bisect.bisect_left(file_cve.get(inf["key"][0], []), b) > 0, "danger": bool(c[1]),
                       "y": fl is not None, "pt": ((fl if fl is not None else end) - b) / YEAR})
        log(f"{r}: commented births {sum(1 for u in UI if u['r'] == r):,}")
    del ev_i
    prior = np.array([u["prior"] for u in UI], float)
    danger = np.array([u["danger"] for u in UI], float)
    yI = np.array([u["y"] for u in UI], float)
    ptI = np.array([u["pt"] for u in UI], float)
    siI, nsI = codes(np.array([f"{u['r']}|{u['lb']}" for u in UI]))
    gI = file_groups(np.array([f"{u['r']}:{u['file']}" for u in UI]))
    or1 = mh_or_codes(prior, danger, siI, nsI)
    b1 = boot(lambda pk: mh_or_codes(prior[pk], danger[pk], siI[pk], nsI), gI, np.random.default_rng(SEED))
    b1 = b1[np.isfinite(b1)]
    lo1, hi1 = float(np.quantile(b1, ALPHA / 2)), float(np.quantile(b1, 1 - ALPHA / 2))
    v1 = ("SUPPORTED: over-represented in prior-CVE files" if lo1 > 1 else
          "reversed: under-represented in prior-CVE files" if hi1 < 1 else "not supported")
    no = prior == 0
    rr2 = mh_rate_codes(danger[no], yI[no], ptI[no], siI[no], nsI)
    gI_no = file_groups(np.array([f"{u['r']}:{u['file']}" for u, k in zip(UI, no) if k]))
    d_no, y_no, p_no, s_no = danger[no], yI[no], ptI[no], siI[no]
    b2 = boot(lambda pk: mh_rate_codes(d_no[pk], y_no[pk], p_no[pk], s_no[pk], nsI), gI_no,
              np.random.default_rng(SEED))
    b2 = b2[np.isfinite(b2)]
    lo2 = float(np.quantile(b2, ALPHA))
    ev2 = int((d_no * y_no).sum())
    v2 = "underpowered" if ev2 < MIN_EV else ("SUPPORTED" if rr2 > 1 and lo2 > 1 else "not supported")
    yes = prior == 1
    rr_prior = mh_rate_codes(danger[yes], yI[yes], ptI[yes], siI[yes], nsI)
    rr_all = mh_rate(danger, yI, ptI, np.array([f"{u['r']}|{u['lb']}|{u['prior']}" for u in UI]))
    log(f"Part I: births {len(UI):,}; I1 OR {or1:.2f} [{lo1:.2f}, {hi1:.2f}]; I2 RR {rr2:.2f} (lo {lo2:.2f}, {ev2} ev)")

    # ---------------- descriptive
    with multiprocessing.get_context("fork").Pool(8) as p:
        su = [u for u in U if u["scar"]]
        keep = dict(p.imap_unordered(last_task, [(i, u["r"], u["last_sha"], u["last_key"][0], u["last_key"][1],
                                                  u["scar_lines"]) for i, u in enumerate(su)], chunksize=4))
        dgroups = defaultdict(list)
        for u in UI:
            if u["danger"]:
                dgroups[(u["r"], u["sha"], u["file"])].append(u["name"])
        blines = {(rr, sha, path): out for rr, sha, path, out in
                  p.imap_unordered(birth_lines_task, [(r, s, f, n) for (r, s, f), n in dgroups.items()], chunksize=4)}
    still = [v for v in keep.values() if v is not None]
    added = {k: defaultdict(list) for k in ("latent", "other-fix")}
    for x in rows:
        if not x.get("missing") and x["scar"] and x["r"] in REPOS_I:
            for s in x["scar"]:
                added[x["klass"]][(x["r"], s)].append(x["ct"])
    inh = {k: 0 for k in added}
    nd = 0
    for u in UI:
        if not u["danger"]:
            continue
        ls = blines.get((u["r"], u["sha"], u["file"]), {}).get(u["name"])
        if ls is None:
            continue
        nd += 1
        for k in added:
            if any(min(added[k].get((u["r"], s), [np.inf])) < u["b"] for s in ls):
                inh[k] += 1
    e_o, RO = part_r(units_all["other-fix"])
    words = Counter(w for u in U if u["scar"] for w in u["words"])

    L = ["# SCAR — what the danger comments that fixes leave behind mean (SCORED)", "",
         "Registration `docs/scar_hypotheses.md` (owner OK 2026-11-11). Aggregates only. "
         f"File-cluster bootstrap {ITERS}, seed {SEED}; α = 0.01/4.", "",
         "## Part R — do scars mark lasting fragility?", "",
         f"- units (each function's first CVE fix; {', '.join(REPOS_R)}): **{len(U):,}**, scarred "
         f"**{int(e_r.sum())}** ({e_r.mean():.1%}); excluded: "
         + ", ".join(f"{why} {n:,}" for (k, why), n in sorted(excl.items()) if k == "latent"),
         "- follow-up: from the fix to function death, label end or 5 years; MH rate ratio, strata repo × loc "
         "(0.25 decade) × in-function edit size (1–2, 3–8, 9–32, > 32 lines).", "",
         "| id | outcome | scarred: events / rate per fn-year | unscarred: events / rate | RR [99.75% CI] | call |",
         "|---|---|---|---|---|---|"]
    for o, nm in (("1", "later CVE fix"), ("2", "later fix, any class")):
        x = R[o]
        L.append(f"| **SCAR-R{o}** | {nm} | {x['ev_s']} / {x['rate_s']:.3f} | {x['ev_u']:,} / {x['rate_u']:.3f} | "
                 f"**{x['rr']:.2f}** [{x['lo']:.2f}, {x['hi']:.2f}] | **{call_r(x)}** |")
    L += ["", f"Power rule: ≥ {MIN_EV} events among scarred and among unscarred units.", "",
          "## Part I — is DC-2's birth signal inherited scar tissue?", "",
          f"- DC-2's commented births (curl, OpenSSL, nDPI, harfbuzz): **{len(UI):,}**; danger-commented "
          f"{int(danger.sum()):,}; in prior-CVE files {int(prior.sum()):,} ({prior.mean():.1%})",
          f"- reproduces DC-2: whole-cohort danger → first-CVE rate ratio {rr_all:.2f} (DC-2 reported 1.45)", "",
          "| id | claim | result | call |", "|---|---|---|---|",
          f"| **SCAR-I1** | danger-commented births over-represented in prior-CVE files (two-sided) | MH OR "
          f"**{or1:.2f}** [{lo1:.2f}, {hi1:.2f}] (99.75%); danger share {danger[yes].mean():.1%} in prior-CVE files vs "
          f"{danger[no].mean():.1%} elsewhere | **{v1}** |",
          f"| **SCAR-I2** | DC-2's link holds in files with no prior CVE fix (one-sided) | rate ratio **{rr2:.2f}** "
          f"(lower bound {lo2:.2f}, α = 0.0025); first-CVE events danger / plain {ev2} / {int(((1 - d_no) * y_no).sum())} "
          f"| **{v2}** |", "",
          f"Power rule (I2): ≥ {MIN_EV} first-CVE events among danger-commented births in no-prior-CVE files.", "",
          "## Descriptive (no verdicts)", "",
          f"- DC-2's rate ratio inside prior-CVE files: {rr_prior:.2f}; outside (I2): {rr2:.2f}; ratio "
          f"{rr_prior / rr2 if rr2 else float('nan'):.2f}",
          f"- Copied scars: of {nd:,} danger-commented births, {inh['latent']} ({inh['latent'] / max(nd, 1):.1%}) carry a "
          f"danger line whose text an earlier CVE fix had added somewhere in the repo; {inh['other-fix']} "
          f"({inh['other-fix'] / max(nd, 1):.1%}) one an earlier ordinary fix had added",
          f"- Scars still fully present at the function's last snapshot: {sum(still)} of {len(still)} "
          f"({np.mean(still) if still else float('nan'):.0%})",
          f"- Scars left by **ordinary (other-fix)** repairs, same design ({len(units_all['other-fix']):,} units, "
          f"{int(e_o.sum())} scarred): R1 {RO['1']['rr']:.2f} [{RO['1']['lo']:.2f}, {RO['1']['hi']:.2f}] "
          f"({RO['1']['ev_s']} / {RO['1']['ev_u']} events); R2 {RO['2']['rr']:.2f} [{RO['2']['lo']:.2f}, "
          f"{RO['2']['hi']:.2f}] ({RO['2']['ev_s']} / {RO['2']['ev_u']})",
          "- Top scar words (CVE fixes): " + ", ".join(f"{w} {n}" for w, n in words.most_common(10)),
          "- Per repo, CVE-fix units scarred / R1 events (scarred, unscarred): " + "; ".join(
              f"{r} {sum(1 for u in U if u['r'] == r and u['scar'])}/{sum(1 for u in U if u['r'] == r)} "
              f"({sum(1 for u in U if u['r'] == r and u['scar'] and u['y1'])}, "
              f"{sum(1 for u in U if u['r'] == r and not u['scar'] and u['y1'])})" for r in REPOS_R),
          ""]
    # per-repo rows (descriptive; added 2026-11-11 before any output was read, because fix labels are known to
    # mean different things in different repos and the registered tests pool repos into one MH ratio)
    L += ["## Per repo (descriptive, no verdicts; fix labels differ by repo, so read the pooled claims with these)", "",
          "| repo | CVE-fix units (scarred) | R1 RR (events scarred / unscarred) | R2 RR (events) | "
          "I2-style RR, no-prior files (danger / plain first-CVE events) | same, prior-CVE files |",
          "|---|---|---|---|---|---|"]
    for r in REPOS_R:
        Ur = [u for u in U if u["r"] == r]
        cells = [f"{len(Ur):,} ({sum(u['scar'] for u in Ur)})"]
        if Ur:
            er = np.array([u["scar"] for u in Ur], float)
            sr = np.array([f"{int(np.floor(np.log10(max(u['loc'], 1)) / 0.25))}|{edit_bin(u['edit'])}" for u in Ur])
            for o in ("1", "2"):
                y = np.array([u["y" + o] for u in Ur], float)
                pt = np.array([u["pt" + o] for u in Ur], float)
                cells.append(f"{mh_rate(er, y, pt, sr):.2f} ({int((y * er).sum())} / {int((y * (1 - er)).sum())})")
        else:
            cells += ["—", "—"]
        if r in REPOS_I:
            m = np.array([u["r"] == r for u in UI])
            for pr in (0, 1):
                k = m & (prior == pr)
                stk = np.array([str(u["lb"]) for u, kk in zip(UI, k) if kk])
                cells.append(f"{mh_rate(danger[k], yI[k], ptI[k], stk):.2f} "
                             f"({int((danger[k] * yI[k]).sum())} / {int(((1 - danger[k]) * yI[k]).sum())})")
        else:
            cells += ["— (not in DC-2)", "—"]
        L.append(f"| {r} | " + " | ".join(cells) + " |")
    L += ["", "inf / nan = no events on one side within the repo's strata.", "",
          f"Runtime {time.time() - T0:.0f}s · seed {SEED}."]
    (DOCS_DIR / "scar.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
