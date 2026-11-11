#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""The LAWS fix-label audit (methods review M6; docs/laws_audit.md): draw the sample, build the rater requests,
score the returned labels. No statistic of any law is computed here.

    python tools/laws_audit.py draw  --out DIR --repo NAME --language c     -> DIR/audit/<repo>.sample.json
    python tools/laws_audit.py build --out DIR --repo NAME                  -> DIR/audit/<repo>.requests.jsonl
    python tools/laws_audit.py score --out DIR                              -> DIR/audit/audit.json

`build` only writes the batch file; it sends nothing. Submitting it spends money, so that is a separate,
deliberate step (`submit`, which needs ANTHROPIC_API_KEY or an `ant auth login` profile).

The prompts, the model id and the effort are NOT in this file: they are read out of docs/laws_audit.md by
heading, and every request records that document's sha256. A prompt edited after labels exist therefore shows up
as a hash mismatch in `score` rather than silently changing the audit.

Strata (docs/laws_audit.md): `fix` and `not-fix` give the rule's precision and specificity; `recall` is a
separate, disjoint draw from the same pool as `not-fix`, so the recall estimate does not reuse the commits that
produced the precision estimate. Recall is a stratified estimate, not a sample proportion: the rule's false
negatives live in the (large) not-fix pool, so the sample shares are reweighted by the pool sizes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from laws_osv import _git  # noqa: E402

DOC = Path(__file__).resolve().parent.parent / "docs" / "laws_audit.md"
MODEL = "claude-opus-5-5"
EFFORT = "low"
MAX_TOKENS = 1024
MAX_DIFF_LINES = 400
PER_STRATUM = 50
SEED = 2982
STRATA = ("fix", "not-fix", "recall")
RATERS = ("A", "B")


def prompts(doc: Path = DOC) -> dict[str, str]:
    """The three prompts, read from docs/laws_audit.md by heading, with the document's sha256."""
    text = doc.read_text()
    out = {"sha256": hashlib.sha256(text.encode()).hexdigest()}
    for key, heading in (("system", "Prompt: system"), ("A", "Prompt: rater A user message"),
                         ("B", "Prompt: rater B user message")):
        m = re.search(rf"^## {re.escape(heading)}\s*\n+```\n(.*?)\n```", text, re.S | re.M)
        if not m:
            raise SystemExit(f"{doc}: no fenced block under '## {heading}'")
        out[key] = m.group(1).strip()
    return out


def pools(history: Path) -> dict[str, list[str]]:
    """The two pools the strata are drawn from, oldest first. `not-fix` is restricted to commits that touch a
    unit source file, so the rater is never shown a commit the rule could not have labelled either way."""
    con = sqlite3.connect(f"file:{history}?mode=ro", uri=True)
    fix = [s for (s,) in con.execute("SELECT sha FROM commit_ WHERE fix = 1 ORDER BY ct")]
    other = [s for (s,) in con.execute(
        "SELECT sha FROM commit_ WHERE fix = 0 AND n_units > 0 AND bot = 0 ORDER BY ct")]
    con.close()
    return {"fix": fix, "not-fix": other}


def draw(history: Path, seed: int = SEED, per: int = PER_STRATUM) -> dict:
    """The seeded, disjoint sample. `not-fix` and `recall` are two halves of one draw from the same pool."""
    p = pools(history)
    rng = np.random.default_rng(seed)
    take = lambda xs, n: [xs[i] for i in sorted(rng.choice(len(xs), min(n, len(xs)), replace=False))]  # noqa: E731
    both = take(p["not-fix"], 2 * per)
    return {"strata": {"fix": take(p["fix"], per), "not-fix": both[:per], "recall": both[per:]},
            "pool_sizes": {k: len(v) for k, v in p.items()}, "seed": seed, "per_stratum": per}


def render(repo: Path, sha: str, rater: str, prompt: dict, max_lines: int = MAX_DIFF_LINES) -> dict:
    """One rater's user message for one commit, plus what was shown."""
    message = _git(repo, "show", "--format=%s%n%n%b", "--no-patch", sha).strip()
    diff = _git(repo, "-c", "diff.renameLimit=0", "show", "--format=", "-M", sha)
    files = [r.split("\t")[-1] for r in _git(repo, "show", "--name-only", "--format=", sha).splitlines() if r.strip()]
    lines = diff.splitlines()
    cut = len(lines) > max_lines
    body = "\n".join(lines[:max_lines])
    text = prompt[rater].format(message=message, diff=body, n_files=len(files), files=", ".join(files[:50]),
                                truncated=f" (truncated to the first {max_lines} lines)" if cut else "")
    return {"text": text, "truncated": cut, "diff_lines": len(lines), "n_files": len(files)}


def build(repo: Path, sample: dict, prompt: dict, max_lines: int = MAX_DIFF_LINES) -> list[dict]:
    """Batch requests: one per (commit, rater). `custom_id` carries the stratum, so a result needs no join."""
    out = []
    for stratum, shas in sample["strata"].items():
        for sha in shas:
            for rater in RATERS:
                r = render(repo, sha, rater, prompt, max_lines)
                out.append({"custom_id": f"{repo.name}|{stratum}|{sha}|{rater}",
                            "params": {"model": MODEL, "max_tokens": MAX_TOKENS,
                                       "output_config": {"effort": EFFORT},
                                       "system": prompt["system"],
                                       "messages": [{"role": "user", "content": r["text"]}]},
                            "shown": {k: r[k] for k in ("truncated", "diff_lines", "n_files")}})
    return out


def kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa for two raters over the same items, two categories."""
    cats = sorted(set(a) | set(b))
    n = len(a)
    if n == 0 or len(cats) < 2:
        return float("nan")
    obs = sum(x == y for x, y in zip(a, b)) / n
    exp = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return float((obs - exp) / (1 - exp)) if exp < 1 else float("nan")


def rates(labels: dict[str, dict[str, str]], pool_sizes: dict[str, int], rater: str) -> dict:
    """The rule's precision and recall from one rater's labels.

    precision = share of the `fix` stratum the rater also calls a fix.
    recall    = TP / (TP + FN), where TP = |fix pool| * precision and FN = |not-fix pool| * (share of the
                `recall` stratum the rater calls a fix). Reweighting by the pool sizes is what makes this a
                recall rather than a sample proportion: the pools differ by one to two orders of magnitude.
    """
    share = {}
    for stratum in STRATA:
        got = [v[rater] for k, v in labels.items() if v.get("stratum") == stratum and rater in v]
        share[stratum] = (sum(g == "fix" for g in got) / len(got)) if got else float("nan")
        share[f"{stratum}_n"] = len(got)
    tp = pool_sizes["fix"] * share["fix"]
    fn = pool_sizes["not-fix"] * share["recall"]
    return {"precision": share["fix"], "specificity": 1 - share["not-fix"],
            "false_negative_share": share["recall"],
            "recall": float(tp / (tp + fn)) if tp + fn > 0 else float("nan"),
            "n": {s: share[f"{s}_n"] for s in STRATA}}


def score(labels: dict[str, dict], pool_sizes: dict[str, int], doc_sha: str | None = None) -> dict:
    """Both raters' rates, their agreement, and the interval the two of them span."""
    items = sorted(k for k, v in labels.items() if all(r in v for r in RATERS))
    out = {"items": len(items), "rated_by_both": len(items),
           "kappa": kappa([labels[k]["A"] for k in items], [labels[k]["B"] for k in items]),
           "raters": {r: rates(labels, pool_sizes, r) for r in RATERS}}
    for metric in ("precision", "recall"):
        vals = [out["raters"][r][metric] for r in RATERS]
        out[metric] = {"low": float(min(vals)), "high": float(max(vals))}
    if doc_sha:
        mismatched = sorted({v["prompt_sha256"] for v in labels.values()
                             if v.get("prompt_sha256") and v["prompt_sha256"] != doc_sha})
        out["prompt_sha256"] = doc_sha
        out["prompt_mismatch"] = mismatched or None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("draw", "build", "score"))
    ap.add_argument("--out", type=Path, required=True, help="the study directory")
    ap.add_argument("--repo", help="a clone under the pool, or a path (draw, build)")
    ap.add_argument("--language", help="recorded with the sample (draw)")
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    d = a.out / "audit"
    d.mkdir(parents=True, exist_ok=True)
    if a.step == "draw":
        from laws_osv import POOL_DIR
        repo = Path(a.repo) if Path(a.repo).is_dir() else POOL_DIR / a.repo
        s = draw(a.out / "history" / f"{repo.name}.db", a.seed)
        s.update(repo=repo.name, language=a.language)
        (d / f"{repo.name}.sample.json").write_text(json.dumps(s, indent=1) + "\n")
        print(f"{repo.name}: " + ", ".join(f"{k} {len(v)}" for k, v in s["strata"].items())
              + f" (pools: {s['pool_sizes']})")
    elif a.step == "build":
        from laws_osv import POOL_DIR
        repo = Path(a.repo) if Path(a.repo).is_dir() else POOL_DIR / a.repo
        s = json.loads((d / f"{repo.name}.sample.json").read_text())
        p = prompts()
        reqs = build(repo, s, p)
        f = d / f"{repo.name}.requests.jsonl"
        f.write_text("".join(json.dumps({**r, "prompt_sha256": p["sha256"]}) + "\n" for r in reqs))
        trunc = sum(r["shown"]["truncated"] for r in reqs)
        print(f"{repo.name}: {len(reqs)} requests ({trunc} truncated diffs), prompts {p['sha256'][:12]} -> {f}")
        print("nothing was sent; `submit` spends money and is a separate step")
    else:
        labels = json.loads((d / "labels.json").read_text())
        sizes = json.loads((d / "pool_sizes.json").read_text())
        rec = score(labels, sizes, prompts()["sha256"])
        (d / "audit.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(json.dumps({k: v for k, v in rec.items() if k != "raters"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
