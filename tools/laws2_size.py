#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""LAWS2 stage `sizing`: how many repos PER LANGUAGE each law needs, from the pilot's own variance.

    python tools/laws2_size.py --run <laws_run_*.json> --out docs/laws2/panel_sizes.json [--md -]

LAWS 1 chose one panel size for every law (12, then 16) before any variance was known. The pilot's numbers say
that is the wrong shape of decision: the between-repo spread differs by an order of magnitude between laws, so
one size is simultaneously wasteful for some laws and hopeless for others.

Method. For each law, over the repos where it is evaluable: tau^2 = max(0, var(effects) - mean(se^2)) -- the
between-repo variance left after the within-repo noise the estimator already reports. The precision of a
k-repo random-effects pool is then ~ sqrt((tau^2 + se_bar^2) / k), and `n` is the smallest k whose 95% half
width falls under the target. Default target is half the observed mean effect; `--sesoi` sets it directly, and
that is what the registration should carry.

Read the output as an ORDER OF MAGNITUDE. With a handful of pilot repos, mostly one per language, tau^2 is
itself estimated from very few points and mixes between-repo with between-language variation. It is a planning
number, to be recomputed from the pilot of the study it sizes -- not a result.
"""
from __future__ import annotations

import argparse, json, math, statistics as st
from pathlib import Path

LAWS = ("LAW-1", "LAW-2", "LAW-3", "LAW-4", "LAW-6", "LAW-8")
READ = {"LAW-1": "heavy tails", "LAW-2": "preferential attachment", "LAW-3": "hub persistence",
        "LAW-4": "centralisation", "LAW-6": "in-cycle defects", "LAW-8": "network metrics in prediction"}
MAXK = 400


def cells(run: dict, law: str):
    out = []
    for v in run["repos"]:
        d = v.get(law) or {}
        if d.get("evaluable") and d.get("effect") is not None and d.get("se"):
            out.append((v["repo"], v["language"], float(d["effect"]), float(d["se"])))
    return out


def need(tau2: float, se_bar: float, target: float) -> int | None:
    if target <= 0:
        return None
    for k in range(2, MAXK + 1):
        if 1.96 * math.sqrt((tau2 + se_bar ** 2) / k) <= target:
            return k
    return None


def size(run: dict, sesoi: dict[str, float] | None) -> dict:
    rows = {}
    for law in LAWS:
        c = cells(run, law)
        if len(c) < 2:
            rows[law] = {"repos_used": len(c), "why": "needs >= 2 evaluable repos to estimate a spread"}
            continue
        eff = [x[2] for x in c]
        ses = [x[3] for x in c]
        mean, sd = st.mean(eff), st.stdev(eff)
        tau2 = max(0.0, sd ** 2 - st.mean([s ** 2 for s in ses]))
        se_bar = st.median(ses)
        target = (sesoi or {}).get(law, abs(mean) / 2)
        n = need(tau2, se_bar, target)
        rows[law] = {"reading": READ[law], "repos_used": len(c),
                     "languages": sorted({x[1] for x in c}),
                     "mean_effect": round(mean, 5), "between_repo_sd": round(sd, 5),
                     "tau": round(math.sqrt(tau2), 5), "median_se": round(se_bar, 5),
                     "target_half_width": round(target, 5),
                     "repos_per_language": n, "capped_at": None if n else MAXK,
                     "note": ("tau is 0: the spread is within estimator noise at this k" if tau2 == 0 else None)}
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sesoi", type=Path, help="JSON {law: smallest effect worth detecting}")
    ap.add_argument("--md", type=Path, help="also write a markdown table ('-' for stdout)")
    a = ap.parse_args()
    run = json.loads(a.run.read_text())
    sesoi = json.loads(a.sesoi.read_text()) if a.sesoi else None
    rows = size(run, sesoi)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"source": a.run.name, "repos": len(run["repos"]),
                                 "sesoi": sesoi, "laws": rows}, indent=1) + "\n")
    L = [f"Panel size per law, from {a.run.name} ({len(run['repos'])} repos: "
         + ", ".join(f"{v['repo']}({v['language']})" for v in run["repos"]) + ")", "",
         "| law | repos used | mean effect | between-repo SD | tau | median SE | target half-width | "
         "**repos per language** |", "|---|---|---|---|---|---|---|---|"]
    for law, r in rows.items():
        if "repos_per_language" not in r:
            L.append(f"| {law} | {r['repos_used']} | — | — | — | — | — | *{r['why']}* |"); continue
        n = r["repos_per_language"]
        L.append(f"| {law} {r['reading']} | {r['repos_used']} | {r['mean_effect']:+.4f} | "
                 f"{r['between_repo_sd']:.4f} | {r['tau']:.4f} | {r['median_se']:.4f} | "
                 f"{r['target_half_width']:.4f} | **{n if n else f'>{MAXK}'}** |")
    L += ["", "Order of magnitude, not a result: tau is estimated from very few repos and mixes between-repo "
              "with between-language variation. Recompute from the pilot of the study it sizes."]
    text = "\n".join(L) + "\n"
    if a.md:
        print(text) if str(a.md) == "-" else a.md.write_text(text)
    print(f"panel sizes -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
