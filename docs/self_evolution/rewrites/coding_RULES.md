# Intent coding rules (v1, pilot)
You code what a change was MEANT to achieve, from the text only. You never see the code. Text has had code spans, file names, identifiers and
mechanism words masked ([M] marks a masked word); ignore the masking, judge intent from what remains.

Labels (multi-label allowed; give every one that clearly applies):
- fix: corrects wrong output, a crash, a missed or wrong match, an edge case, a false positive/negative, a wrong rule.
- feature: adds or extends a capability: new language/dialect/construct support, new output, new check, wider coverage.
- perf: speed, time-outs, memory, scaling, complexity, "slow", "hang", "linear", measured cost.
- refactor: restructure, extract, rename, simplify, dedupe, cleanup, lint, type hints, no intended behaviour change.
- other: docs, tests only, CI, release, or unreadable.
- unclear: the text does not say what the change is for (use alone).
Also give `primary` (the single best label). A commit text that mentions "fix" in a title of a feature still counts as feature if what is built is new.
Output a JSON array, one object per input item: {"id":..., "labels":[...], "primary":"..."}. No other text.

## v2 tie-breaks (frozen after the 20-item pilot; no further changes)
- fix vs feature: label BOTH when the text frames a gap or wrong result AND builds something new; `primary` follows the title's framing
  (fix = something existing was wrong, missing for an already-supported case; feature = a new construct/dialect/output/check is introduced).
- refactor vs feature: any intended behaviour change (including a changed default) is not refactor-only; add feature or fix.
- perf vs refactor: a stated or measured speed/scaling goal makes it perf, with refactor as a second label if the structure was changed.
- docs or refusal tables that accompany real behaviour: label the behaviour; add `other` only if docs are the whole change.
