#!/usr/bin/env python3
# ==============================================================================
# temporal-crucible
# Copyright (c) 2026 Joe Esquibel
# Licensed under the PolyForm Noncommercial License 1.0.0 (see LICENSE).
# ==============================================================================
"""How much does a noisy fix label SHRINK a real structural effect? (the mirror of hr1_bias.py)

    python tools/attenuation.py --repo curl --reps 300

hr1_bias.py asked: when predictor and outcome come from the SAME noisy label, how much lift does the noise
manufacture? Answer: a lot, and positive. That governs the history predictors.

Structural predictors are the opposite case. Structure (centrality, coupling, complexity) is measured by the
engine and does not depend on how anyone writes a commit message, so its error is independent of the label's.
Classical theory then says the association is **attenuated toward the null** -- real effects look smaller, and
a true effect can vanish entirely.

That matters because most of this programme's structural claims are NEGATIVE: "exposure reduces to size",
"centrality adds nothing", TOST equivalence results. A null measured through a 0.41-sensitivity outcome is
weak evidence of absence, and this quantifies how weak.

Method: plant a structural predictor with a KNOWN true lift over LOC, apply the measured label error
(sensitivity 0.41, specificity 0.83), and report the lift that survives.
"""
from __future__ import annotations

import argparse, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hist_replicate import auc  # noqa: E402
from hr1_bias import repo_frame  # noqa: E402


def run(frame, b, sens, spec, rnd, alpha=1.0):
    """Truth depends on SIZE and on an independent STRUCTURAL factor; `b` sets how much the structural
    factor really matters. The predictor is that factor. We then observe the label through the measured
    error and compare the lift over LOC on truth versus on the observed label."""
    import math
    locs = [f[1] for f in frame]
    mu = sum(math.log(l + 1) for l in locs) / len(locs)
    struct, truth, obs, L = [], [], [], []
    for _p, loc, _nb, _na in frame:
        s_i = rnd.random()                                  # the structural factor, independent of size
        z = 0.9 * (math.log(loc + 1) - mu) + b * (s_i - 0.5) * 6.0 - 1.2
        is_def = 1 if rnd.random() < 1 / (1 + math.exp(-z)) else 0
        seen = 1 if (is_def and rnd.random() < sens) or (not is_def and rnd.random() > spec) else 0
        struct.append(s_i); truth.append(is_def); obs.append(seen); L.append(loc)
    if sum(truth) < 20 or sum(obs) < 20:
        return None, None
    true_a = (auc(struct, truth) or 0) - (auc(L, truth) or 0)
    obs_a = (auc(struct, obs) or 0) - (auc(L, obs) or 0)
    return true_a, obs_a


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="curl")
    ap.add_argument("--reps", type=int, default=300)
    ap.add_argument("--sens", type=float, default=0.41)
    ap.add_argument("--spec", type=float, default=0.83)
    a = ap.parse_args()
    frame = repo_frame(a.repo)
    print(f"{a.repo}: {len(frame):,} files; label sensitivity {a.sens}, specificity {a.spec}\n")
    print(f"{'planted true lift':>19}{'observed lift (median)':>26}{'surviving fraction':>21}")
    for s in (0.0, 0.3, 0.6, 1.0, 1.5):
        rnd = random.Random(2982 + int(s * 100))
        pairs = [run(frame, s, a.sens, a.spec, rnd) for _ in range(a.reps)]
        pairs = [(t, o) for t, o in pairs if t is not None]
        if not pairs:
            print(f"{s:>19.2f}   (no replicate reached the floor)"); continue
        ts = sorted(t for t, _o in pairs)
        os_ = sorted(o for _t, o in pairs)
        tmed, omed = ts[len(ts) // 2], os_[len(os_) // 2]
        frac = (omed / tmed) if abs(tmed) > 1e-6 else float("nan")
        print(f"{tmed:>19.4f}{omed:>26.4f}{(f'{frac:.0%}' if frac == frac else '   --'):>21}")
    print("\nA structural effect is measured THROUGH the label, so its association is attenuated.")
    print("The surviving fraction is how much of a real effect would still be visible to us.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
