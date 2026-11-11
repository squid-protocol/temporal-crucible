#!/usr/bin/env python3
"""AIAT-P: the uniform-attention LLM auditor as a measuring instrument (docs/aiat_hypotheses.md).

    python tools/aiat_eval.py sample   --repo curl              # frozen sample + v3c outcomes; NO API
    python tools/aiat_eval.py prompt                            # the frozen auditor prompt and its hash
    python tools/aiat_eval.py estimate --repo curl --n 25        # local cost estimate; --count-tokens uses the API
    python tools/aiat_eval.py score    --repo curl --limit 25    # the cost probe (SPENDS MONEY; --confirm required)
    python tools/aiat_eval.py metrics  --repo curl               # AIAT-P1 / P2; NO API

Everything the registration froze is a constant here, not a flag: the snapshot commits, the window
end (the pool clone head), the seed, the auditor model and the prompt. A flag that could move one of
them would make the pre-registration decorative.

**Uniform attention is the instrument.** The auditor sees one file's source at the snapshot tree and
nothing else -- no history, no commit messages, no sibling files, no path beyond the basename. The
covariate model in docs/ceil.md sees history and structure; this sees only code. That is the whole
point, so the prompt is frozen and hashed, and `score` records the hash beside every score.

**Contamination.** The auditor is `claude-opus-5`, whose knowledge cutoff (May 2026) precedes the
2026-06-01 snapshot, so every outcome in the window post-dates what it could have memorised.
AIAT-P3 contrasts it with CONTRAST_MODEL, a later-cutoff model, on a pre-cutoff window; that
contrast is the only reason a second model appears here.

**Cost.** Scoring goes through the Message Batches API (50% of standard rates; latency does not
matter for a pilot) and every result is written to the cache as it lands, so a killed run loses
nothing and a re-run costs nothing for what it already has -- the flake_history.py pattern.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixlike_v2  # noqa: E402  -- the registered v3c label rule; never reimplemented here

# ---------------------------------------------------------------- frozen inputs (docs/aiat_hypotheses.md § 3)
POOL = Path(os.environ.get("TC_POOL", "/srv/storage_16tb/projects/temporal-crucible-pool"))
SNAPSHOT = {"curl": "032b15c4342e8eddb51fbe089a9d8ba3ee2070fb",
            "ndpi": "7b43393d8a36cf71b61f582093b1185c4ed0b0b9"}
POOL_HEAD = {"curl": "a0c990c819", "ndpi": "2b8c2989f"}
EXTS = (".c", ".h")
SEED = 2982
# Measured 2026-11-11: the v3c positive rate is 8.6% (curl) / 8.2% (ndpi), not the ~30% a subject
# grep suggested, so a 400-file sample holds ~34 positives -- far too few for a per-cell power rule.
# Scoring the WHOLE universe costs ~$8 (curl) / ~$3 (ndpi) batched, inside the $40 gate, and removes
# sampling error as well. `--n` still subsamples, for a cheap smoke run.
TARGET_N = {"curl": None, "ndpi": None}  # None = the whole snapshot universe
DECILES = 10

AUDITOR_MODEL = "claude-opus-5"      # cutoff May 2026, before the 2026-06-01 snapshot
CONTRAST_MODEL = "claude-opus-5-5"   # AIAT-P3 only: a later cutoff, deliberately
PRICES = {"claude-opus-5": (5.0, 25.0), "claude-opus-5-5": (4.0, 20.0)}  # $/MTok in, out
BATCH_DISCOUNT = 0.5
MAX_FILE_BYTES = 200_000  # a file above this is recorded as oversized and left unscored, never truncated

PROMPT = """You are auditing one source file from a C codebase. You are shown the file's complete \
contents and nothing else: no version history, no commit messages, no other files, no project name.

Estimate the probability that this file will receive at least one bug-fix commit during the next six \
months of the project's development.

Judge only from the code in front of you. Spend the same effort on every file you are given.

Reply with JSON only: {"p": <number between 0 and 1>, "why": "<one sentence>"}"""

SCHEMA = {"type": "object",
          "properties": {"p": {"type": "number"}, "why": {"type": "string"}},
          "required": ["p", "why"], "additionalProperties": False}


def prompt_sha() -> str:
    return hashlib.sha256(PROMPT.encode()).hexdigest()


# ---------------------------------------------------------------- git helpers
def git(repo: str, *args: str) -> str:
    """Bytes in, str out, with undecodable bytes replaced.

    Real C trees carry latin-1 copyright signs and binary test fixtures, so `text=True` raises
    UnicodeDecodeError on a handful of files (nDPI, 2026-11-11). Replacing is right here: the
    auditor reads source as text, and a file whose bytes are not text is not a file it can judge.
    """
    r = subprocess.run(["git", "-C", str(POOL / repo), *args], capture_output=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)[:60]}: {r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout.decode("utf-8", "replace")


def snapshot_files(repo: str) -> list[str]:
    snap = SNAPSHOT[repo]
    return sorted(p for p in git(repo, "ls-tree", "-r", "--name-only", snap).split("\n")
                  if p.endswith(EXTS))


def file_loc(repo: str, path: str) -> int:
    try:
        blob = git(repo, "show", f"{SNAPSHOT[repo]}:{path}")
    except RuntimeError:
        return 0
    return blob.count("\n") + (0 if blob.endswith("\n") or not blob else 1)


def window_fix_files(repo: str) -> tuple[set[str], dict]:
    """The v3c-labelled fix set over the registered window, and its provenance.

    Every commit from the snapshot to the pool head is offered to fixlike_v2.drop_reason as an
    `other-fix` event; the ones it keeps are the outcome. The rule is imported, never restated, so a
    change to the registered rule changes this too.
    """
    snap, head = SNAPSHOT[repo], POOL_HEAD[repo]
    raw = git(repo, "log", "--first-parent", "--no-merges", f"{snap}..{head}",
              "--format=%x00%H%x1f%s", "--name-only")
    kept, seen, dropped = set(), 0, {}
    for chunk in raw.split("\x00")[1:]:
        head_line, _, rest = chunk.partition("\n")
        sha, _, subject = head_line.partition("\x1f")
        files = [f for f in rest.split("\n") if f.strip()]
        c_files = [f for f in files if f.endswith(EXTS)]
        seen += 1
        why = fixlike_v2.drop_reason({"class": fixlike_v2.AUDITED_CLASS, "subject": subject,
                                      "c_files": c_files}, rules="v3c")
        if why:
            dropped[why.split(":")[0]] = dropped.get(why.split(":")[0], 0) + 1
            continue
        kept.update(c_files)
    return kept, {"commits_in_window": seen, "dropped_by_rule": dropped,
                  "rule": "fixlike_v2.drop_reason(rules='v3c')"}


# ---------------------------------------------------------------- sampling
def stratify(locs: dict[str, int], bins: int = DECILES) -> dict[str, int]:
    """Each file's LOC-decile index over the snapshot universe (equal-count bins, ties kept together)."""
    order = sorted(locs, key=lambda p: (locs[p], p))
    n = len(order)
    out = {}
    for i, p in enumerate(order):
        out[p] = min(bins - 1, i * bins // n) if n else 0
    return out


def draw_sample(paths: list[str], strata: dict[str, int], want: int, seed: int = SEED) -> list[str]:
    """`want` paths, spread evenly over the strata, seeded. Deterministic and reproducible."""
    by = {}
    for p in sorted(paths):
        by.setdefault(strata[p], []).append(p)
    rng = random.Random(seed)
    per = max(1, want // max(1, len(by)))
    picked = []
    for s in sorted(by):
        pool = sorted(by[s])
        picked += rng.sample(pool, min(per, len(pool)))
    rest = sorted(set(paths) - set(picked))
    rng.shuffle(rest)
    return sorted(picked + rest[:max(0, want - len(picked))])


def sample_path(repo: str) -> Path:
    return Path("data/aiat") / f"{repo}_sample.json"


def scores_path(repo: str, model: str) -> Path:
    return Path("data/aiat") / f"{repo}_scores_{model.replace('.', '-')}.json"


def cmd_sample(a) -> int:
    repo = a.repo
    paths = snapshot_files(repo)
    locs = {p: file_loc(repo, p) for p in paths}
    paths = [p for p in paths if locs[p] > 0]
    strata = stratify({p: locs[p] for p in paths})
    fixed, prov = window_fix_files(repo)
    want = a.n or TARGET_N[repo] or len(paths)
    sample = sorted(paths) if want >= len(paths) else draw_sample(paths, strata, want)
    rec = {"repo": repo, "snapshot": SNAPSHOT[repo], "pool_head": POOL_HEAD[repo], "seed": SEED,
           "universe": len(paths), "sample_n": len(sample), "prompt_sha256": prompt_sha(),
           "outcome": prov,
           "universe_positives": sum(1 for p in paths if p in fixed),
           "sample_positives": sum(1 for p in sample if p in fixed),
           "files": [{"path": p, "loc": locs[p], "stratum": strata[p], "fixed": int(p in fixed)}
                     for p in sample]}
    sample_path(repo).parent.mkdir(parents=True, exist_ok=True)
    sample_path(repo).write_text(json.dumps(rec, indent=1) + "\n")
    base = rec["universe_positives"] / len(paths)
    print(f"{repo}: universe {len(paths)} files, {rec['universe_positives']} fixed in window "
          f"({base:.1%}); sample {len(sample)} files, {rec['sample_positives']} fixed "
          f"({rec['sample_positives'] / len(sample):.1%})")
    print(f"  commits in window {prov['commits_in_window']}, dropped by v3c {prov['dropped_by_rule']}")
    print(f"  -> {sample_path(repo)}  (prompt {prompt_sha()[:12]})")
    return 0


# ---------------------------------------------------------------- cost
def cmd_estimate(a) -> int:
    rec = json.loads(sample_path(a.repo).read_text())
    files = rec["files"][: a.n] if a.n else rec["files"]
    chars = sum(len(git(a.repo, "show", f"{SNAPSHOT[a.repo]}:{f['path']}")) for f in files)
    local = chars / 3.5  # ~3.5 chars/token for C; replaced by count_tokens with --count-tokens
    tokens = local
    how = "local estimate (~3.5 chars/token)"
    if a.count_tokens:
        client = _client()
        tokens = 0
        for f in files:
            body = git(a.repo, "show", f"{SNAPSHOT[a.repo]}:{f['path']}")
            tokens += client.messages.count_tokens(
                model=a.model, system=PROMPT,
                messages=[{"role": "user", "content": body}]).input_tokens
        how = "measured with messages.count_tokens"
    pin, pout = PRICES[a.model]
    out_tokens = len(files) * 120
    full = (tokens / 1e6) * pin + (out_tokens / 1e6) * pout
    print(f"{a.repo}: {len(files)} files, {tokens:,.0f} input tokens ({how})")
    print(f"  standard ${full:.2f}   batch (50%) ${full * BATCH_DISCOUNT:.2f}   model {a.model}")
    whole = len(rec["files"]) / len(files)
    print(f"  whole sample of {len(rec['files'])}: batch ~${full * BATCH_DISCOUNT * whole:.2f}")
    return 0


# ---------------------------------------------------------------- scoring
def _client():
    try:
        import anthropic
    except ImportError:
        sys.exit("the anthropic SDK is not installed: pip install anthropic")
    return anthropic.Anthropic()


def load_scores(repo: str, model: str) -> dict:
    p = scores_path(repo, model)
    return json.loads(p.read_text()) if p.exists() else {}


def save_scores(repo: str, model: str, scores: dict) -> None:
    p = scores_path(repo, model)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(scores, indent=1, sort_keys=True) + "\n")
    tmp.replace(p)


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return {"p": float(d["p"]), "why": str(d.get("why", ""))[:300]}
    except (ValueError, KeyError, TypeError):
        return None


def cmd_score(a) -> int:
    rec = json.loads(sample_path(a.repo).read_text())
    if rec["prompt_sha256"] != prompt_sha():
        return _die("the prompt changed since the sample was built: rebuild the sample or restore it")
    scores = load_scores(a.repo, a.model)
    todo = [f for f in rec["files"] if f["path"] not in scores][: a.limit] if a.limit \
        else [f for f in rec["files"] if f["path"] not in scores]
    if not todo:
        print(f"{a.repo}: nothing to do, {len(scores)} already scored")
        return 0
    if not a.confirm:
        print(f"{len(todo)} files would be scored on {a.model} ({'batch' if a.batch else 'live'}).\n"
              f"This SPENDS MONEY. Run `estimate` first, then re-run with --confirm.")
        return 1
    client = _client()
    bodies = {}
    for f in todo:
        body = git(a.repo, "show", f"{SNAPSHOT[a.repo]}:{f['path']}")
        if len(body.encode()) > MAX_FILE_BYTES:
            scores[f["path"]] = {"error": "oversized", "bytes": len(body.encode())}
            continue
        bodies[f["path"]] = body
    save_scores(a.repo, a.model, scores)
    if a.batch:
        n = _score_batch(client, a, bodies, scores)
    else:
        n = _score_live(client, a, bodies, scores)
    print(f"{a.repo}: {n} scored this run, {len([v for v in scores.values() if 'p' in v])} total "
          f"-> {scores_path(a.repo, a.model)}")
    return 0


def _request_kwargs(model: str, body: str) -> dict:
    return {"model": model, "max_tokens": 1024, "system": PROMPT,
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content": body}]}


def _score_live(client, a, bodies: dict, scores: dict) -> int:
    done = 0
    for path, body in bodies.items():
        r = client.messages.create(**_request_kwargs(a.model, body))
        text = next((b.text for b in r.content if b.type == "text"), "")
        got = _parse(text)
        scores[path] = {**(got or {"error": "unparseable", "raw": text[:200]}),
                        "model": a.model, "prompt_sha256": prompt_sha(),
                        "usage": {"in": r.usage.input_tokens, "out": r.usage.output_tokens}}
        save_scores(a.repo, a.model, scores)  # after every file: a kill loses nothing
        done += 1
        if a.budget_s and done % 10 == 0 and time.monotonic() - _START > a.budget_s:
            print(f"budget of {a.budget_s}s reached; {done} done, the rest stays for the next run")
            break
    return done


def _score_batch(client, a, bodies: dict, scores: dict) -> int:
    from anthropic.types.messages.batch_create_params import Request
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    ids = {f"f{i}": p for i, p in enumerate(bodies)}
    batch = client.messages.batches.create(requests=[
        Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**_request_kwargs(a.model, bodies[p])))
        for cid, p in ids.items()])
    print(f"batch {batch.id} submitted with {len(ids)} requests; polling")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        time.sleep(20)
    done = 0
    for res in client.messages.batches.results(batch.id):
        path = ids.get(res.custom_id)
        if path is None:
            continue
        if res.result.type != "succeeded":
            scores[path] = {"error": res.result.type}
            continue
        msg = res.result.message
        got = _parse(next((bl.text for bl in msg.content if bl.type == "text"), ""))
        scores[path] = {**(got or {"error": "unparseable"}), "model": a.model,
                        "prompt_sha256": prompt_sha(),
                        "usage": {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}}
        done += 1
        save_scores(a.repo, a.model, scores)
    return done


# ---------------------------------------------------------------- metrics
def recall_at_budget(items: list[tuple[float, int, int]], frac: float = 0.20) -> float:
    """Share of positives inside the top-ranked files whose LOC sum reaches `frac` of all LOC.

    `items` is (score, loc, positive). This is docs/ceil.md's recall@20%-of-lines, so the pilot's
    number lands on the ceiling ladder instead of beside it.
    """
    total_loc = sum(l for _, l, _ in items)
    total_pos = sum(y for _, _, y in items)
    if not total_loc or not total_pos:
        return float("nan")
    budget, got, used = total_loc * frac, 0, 0
    for _, loc, y in sorted(items, key=lambda t: -t[0]):
        if used + loc > budget:
            break
        used += loc
        got += y
    return got / total_pos


def loc_baseline(items: list[tuple[float, int, int]]) -> tuple[float, str]:
    """The STRONGER of the two size orderings, which is the baseline the auditor must beat.

    At a line budget, big-files-first spends the budget on few files and small-files-first reviews
    many. Which wins depends on how the positives are distributed, so neither is "the size order":
    picking one in advance can hand the instrument a baseline it beats for free. A random ranking
    beat big-files-first on curl (0.212 vs 0.129) in a smoke test before any real score existed,
    which is exactly the trap. The program's own convention elsewhere is lift over the *stronger*
    size order (ENV-H1..H3), and that is what is used here.
    """
    desc = recall_at_budget([(float(l), l, y) for _s, l, y in items])
    asc = recall_at_budget([(-float(l), l, y) for _s, l, y in items])
    return (desc, "big-first") if desc >= asc else (asc, "small-first")


def positive_bands(items: list[tuple[float, int, int]], bands: int = 3) -> dict[int, int]:
    """Index -> band, cutting on LOC so each band holds a comparable number of POSITIVES.

    Equal-count bands put 1, 10 and 74 of curl's 85 positives in the three bands, because positives
    concentrate in large files, leaving the gate evaluable in one band only. Cut points are fixed
    from LOC and the outcome, never from any score, so they cannot favour the auditor over LOC.
    """
    order = sorted(range(len(items)), key=lambda i: items[i][1])
    total_pos = sum(y for _s, _l, y in items)
    if not total_pos:
        return {i: 0 for i in range(len(items))}
    per = total_pos / bands
    out, seen, b = {}, 0, 0
    for i in order:
        out[i] = b
        seen += items[i][2]
        if seen >= per * (b + 1) and b < bands - 1:
            b += 1
    return out


def spearman(xs: list[float], ys: list[float]) -> float:
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")



# ---------------------------------------------------------------- AIAT-P7: class split
XC_HARVEST_END = "2026-09-11"  # events/<repo>_xc.json stops here; P7 runs on this sub-window only


def class_labels(repo: str) -> dict[str, set[str]]:
    """class -> files touched by a fix of that class between the snapshot and the xc harvest's end.

    Registered as AIAT-P7. These are the harvester's audited classes, not the v3c approximation the
    primary outcome uses, and they cover a SHORTER window, so P7 is a secondary on a subset. The
    primary outcome is not recomputed here.
    """
    f = Path("events") / f"{repo}_xc.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text())
    ev = d["events"] if isinstance(d, dict) and "events" in d else d
    snap_ct = int(subprocess.run(["git", "-C", str(POOL / repo), "show", "-s", "--format=%ct",
                                  SNAPSHOT[repo]], capture_output=True).stdout.decode().strip() or 0)
    out: dict[str, set[str]] = {}
    for e in ev:
        if not e.get("ct") or int(e["ct"]) < snap_ct:
            continue
        out.setdefault(e.get("class") or "?", set()).update(e.get("c_files") or [])
    return out


def cmd_metrics(a) -> int:
    rec = json.loads(sample_path(a.repo).read_text())
    scores = load_scores(a.repo, a.model)
    rows = [(scores[f["path"]]["p"], f["loc"], f["fixed"], f["stratum"], f["path"])
            for f in rec["files"] if f["path"] in scores and "p" in scores[f["path"]]]
    if not rows:
        return _die("no scores yet: run `score` first")
    print(f"{a.repo}: {len(rows)} scored, {sum(y for _, _, y, _st, _pa in rows)} positive "
          f"({sum(y for _, _, y, _st, _pa in rows) / len(rows):.1%}), model {a.model}")
    by_score = [(p, l, y) for p, l, y, _st, _pa in rows]
    by_loc = [(float(l), l, y) for p, l, y, _st, _pa in rows]
    print("\nAIAT-P1 -- is it a size proxy?")
    print(f"  spearman(score, log loc)      {spearman([p for p, _, _, _st, _pa in rows], [math.log(l) for _, l, _, _st, _pa in rows]):+.3f}")
    base, which = loc_baseline(by_score)
    print(f"  recall@20% lines, score order {recall_at_budget(by_score):.3f}")
    print(f"  recall@20% lines, LOC order   {base:.3f}  (the STRONGER size order: {which})")
    print(f"    both size orders: big-first {recall_at_budget(by_loc):.3f}, "
          f"small-first {recall_at_budget([(-float(l), l, y) for _p, l, y, _st, _pa in rows]):.3f}")
    print("  within LOC bands (the gate -- the pooled line is confounded by size).")
    print("  Three EQUAL-POSITIVE LOC bands: equal-count bands hold 1/10/74 of curl's positives,")
    print("  since positives concentrate in large files. Cut points come from LOC and the outcome,")
    print("  never from a score, so they cannot favour the auditor over size.")
    wins = tot = 0
    band = positive_bands(by_score, 3)
    for s in (0, 1, 2):
        sub = [(rows[i][0], rows[i][1], rows[i][2]) for i in band if band[i] == s]
        subl = sub  # loc_baseline derives both size orders from the same rows
        if sum(y for _, _, y in sub) < 1 or len(sub) < 5:
            continue
        rs, (rl, _w) = recall_at_budget(sub), loc_baseline(sub)
        tot += 1
        wins += rs > rl
        under = sum(y for _, _, y in sub) < 20
        print(f"    stratum {s}: n={len(sub):3} pos={sum(y for _, _, y in sub):3}  "
              f"score {rs:.3f} vs LOC {rl:.3f}  {'score' if rs > rl else 'LOC'}"
              f"{'  UNDERPOWERED (<20 positives)' if under else ''}")
    if tot:
        print(f"  score beats LOC in {wins}/{tot} evaluable bands "
              f"-- the registered kill criterion is 'adds nothing over LOC within strata'")

    # AIAT-P7, registered before scoring: lift must be largest for latent, near zero for regression
    classes = class_labels(a.repo)
    if classes:
        print(f"\nAIAT-P7 -- where does the lift land by fix class? "
              f"(classes from events/{a.repo}_xc.json, sub-window to {XC_HARVEST_END})")
        print("  registered prediction: lift(latent) > lift(regression); a flat lift undermines the")
        print("  attention reading and looks like a second size proxy.")
        print(f"    {'class':11} {'pos':>4} {'score':>7} {'LOC':>7} {'lift':>7}")
        lifts = {}
        for cls in ("latent", "extrinsic", "regression", "other-fix"):
            paths = classes.get(cls) or set()
            items = [(p_, l, int(pa in paths)) for p_, l, _y, _st, pa in rows]
            pos = sum(y for _, _, y in items)
            if pos < 1:
                continue
            rs = recall_at_budget(items)
            rl, _which = loc_baseline(items)
            lifts[cls] = rs - rl
            flag = "" if pos >= 20 else "  UNDERPOWERED"
            print(f"    {cls:11} {pos:4} {rs:7.3f} {rl:7.3f} {rs - rl:+7.3f}{flag}")
        if "latent" in lifts and "regression" in lifts:
            verdict = ("SUPPORTS the attention reading" if lifts["latent"] > lifts["regression"]
                       else "UNDERMINES it (regression >= latent)")
            print(f"  lift(latent) {lifts['latent']:+.3f} vs lift(regression) "
                  f"{lifts['regression']:+.3f}  ->  {verdict}")
    if a.replicate_model:
        other = load_scores(a.repo, a.replicate_model)
        both = [(scores[p]["p"], other[p]["p"]) for p in scores
                if p in other and "p" in scores[p] and "p" in other[p]]
        if both:
            print(f"\nAIAT-P2/P3 -- {a.model} vs {a.replicate_model} on {len(both)} shared files: "
                  f"spearman {spearman([x for x, _ in both], [y for _, y in both]):+.3f} "
                  f"(P2 floor is 0.70 between runs of the SAME model)")
    return 0


def _die(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


_START = time.monotonic()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("step", choices=("sample", "prompt", "estimate", "score", "metrics"))
    ap.add_argument("--repo", choices=sorted(SNAPSHOT), default="curl")
    ap.add_argument("--n", type=int, help="sample/estimate: how many files (default: the registered target)")
    ap.add_argument("--limit", type=int, help="score: stop after this many NEW files (the cost probe)")
    ap.add_argument("--model", default=AUDITOR_MODEL, help=f"default {AUDITOR_MODEL}")
    ap.add_argument("--replicate-model", help="metrics: a second score file to correlate against")
    ap.add_argument("--count-tokens", action="store_true", help="estimate: measure instead of guessing")
    ap.add_argument("--batch", action="store_true", default=True, help="score via the Batches API (50%% cost)")
    ap.add_argument("--live", dest="batch", action="store_false", help="score with live calls instead")
    ap.add_argument("--budget-s", type=int, help="score --live: stop after this many seconds")
    ap.add_argument("--confirm", action="store_true", help="score: required, because it spends money")
    a = ap.parse_args()
    if a.step == "prompt":
        print(PROMPT)
        print(f"\nsha256 {prompt_sha()}\nauditor {AUDITOR_MODEL}  contrast (P3 only) {CONTRAST_MODEL}")
        return 0
    return {"sample": cmd_sample, "estimate": cmd_estimate,
            "score": cmd_score, "metrics": cmd_metrics}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
