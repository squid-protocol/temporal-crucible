"""The coded and the corrected readings of the three confirmatory tests (second, independent build).

Written from section 2.1 and 2.1a of docs/process/comparison_scorer_part2_spec.md alone.

    coded(tests, gate_valid)     -> {name: words}
    corrected(tests, gate_valid) -> {name: words}

`tests` is a list of mappings in the order B, C, D, each with `name`, `p` (the primary statistic's two-sided
p), `primary`, `residualised` (each "supported", "contradicted", "not detected" or "not fitted") and `control`
("supported" or anything else). Pure: no input, no output, no randomness.
"""

import math

SUPPORTED = "supported"
CONTRADICTED = "contradicted"

HOLM = "not detected (Holm: an earlier test in the family failed)"
NOT_ROBUST = "not robust to the statistic"
DEFECT_SPECIFIC = "supported, defect-specific"
TRACKS_ACTIVITY = "supported, but tracks activity, not defects"
GATE_FAILED = "NO FINDING: the placebo gate failed"


def _p_key(test):
    """The sort key for Holm order: ascending p. A p that is missing or not a number sorts last."""
    p = test["p"]
    if p is None:
        return math.inf
    p = float(p)
    if math.isnan(p):
        return math.inf
    return p


def _read(tests, gate_valid, change1, change2):
    """Section 2.1's rule. `change1` and `change2` switch the two corrections on separately."""
    # sorted() is stable, so ties keep the order given (B, C, D).
    ordered = sorted(tests, key=_p_key)
    words = {}
    still = True
    for test in ordered:
        primary = test["primary"]
        residualised = test["residualised"]
        reading = primary
        holm_reworded = False
        if reading == SUPPORTED and not still:
            reading = HOLM
            holm_reworded = True

        # The step-down: which primary readings stop it.
        if change1:
            if primary not in (SUPPORTED, CONTRADICTED):
                still = False
        else:
            if primary != SUPPORTED:
                still = False

        # Robustness to the statistic, then the control.
        if change2:
            # owner ruling 2026-11-15 (edited by the reviewer): the coded condition stays; the literal extension does
            # not act when either side is "not fitted"
            not_robust = (reading == SUPPORTED and residualised != SUPPORTED) or (
                (not holm_reworded) and primary != residualised and "not fitted" not in (primary, residualised))
        else:
            not_robust = reading == SUPPORTED and residualised != SUPPORTED
        if not_robust:
            reading = NOT_ROBUST
        elif reading == SUPPORTED:
            if test["control"] == SUPPORTED:
                reading = DEFECT_SPECIFIC
            else:
                reading = TRACKS_ACTIVITY

        if not gate_valid:
            reading = GATE_FAILED
        words[test["name"]] = reading
    return words


def coded(tests, gate_valid):
    """The rule as coded: neither change."""
    return _read(tests, gate_valid, change1=False, change2=False)


def corrected(tests, gate_valid):
    """The corrected rule: the coded rule with change 1 and change 2."""
    return _read(tests, gate_valid, change1=True, change2=True)
