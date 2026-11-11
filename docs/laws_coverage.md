# Call-resolution coverage: what the number means, and which laws it moves

Development data, never panel results. Tools: `tools/laws_run.py --thin`. Numbers:
`.../laws-study/pilot/laws_run_pilot.json` (full) and `.../laws_run_thin57.json` (thinned).
Background: `docs/laws_driver_pilot.md`.

The end-to-end run reported `share_confident_of_repo_links` of 99% for the two C repos and 56 to 60% for Java,
Go and Python. Two questions follow: is that number measuring what it appears to, and does it move any law.

## 1. The number is a floor, not a coverage rate

`share_confident_of_repo_links = conf / (conf + amb + unresolved)`, and the three terms are not scoped alike
(`laws_net.network`):

- **conf** and **amb** count only edges where **both** endpoints are unit functions: the target language,
  non-test, non-generated, at least `MIN_LOC` lines. An edge is `conf` when its resolution step is in
  `CONFIDENT_STEPS` and `amb` otherwise.
- **unresolved** is `SELECT step, SUM(n) FROM unresolved WHERE commit_hash = ? AND kind = 'call'`. The table is
  `(commit_hash, step, kind, n)` -- **it has no file column**, so it cannot be restricted to unit files. Calls
  from test files, from generated files and from files of other languages all land in the denominator.

So a repo with a large test suite or a second language is penalised in the denominator while contributing nothing
to the numerator. Java, Go and Python repos have both far more often than a C library does. **The true intra-repo
coverage is therefore higher than the reported share, by an amount the recorded data cannot determine.** Reporting
the figure as a coverage rate overstates the gap; it should be described as a floor until the scanner records the
file alongside each unresolved call, which is a one-column change.

That said, the gap is mostly real and not an accounting artefact. The dominant unresolved step is `receiver` -- a
method call whose receiver type could not be inferred -- with roughly 42k occurrences in commons-lang, 32k in
sphinx, 22k in prometheus, 2.4k in libxml2 and **none at all** in libgit2. That is genuine dynamic-dispatch
failure, and it is the thing C does not have.

A related correction: `links_ambiguous_not_used` is **not** a discarded candidate set. Those edges are resolved to
one specific intra-repo target, by a step outside `CONFIDENT_STEPS` (`receiver`, `tie`, `nearest`). Admitting them
lowers a confidence threshold; it does not fan a virtual call out to every implementation, so it carries no
fan-out inflation of in-degree. It does risk systematically resolving to the wrong target, and `tie` and
`nearest` are guesses, so it belongs as a run-both-ways sensitivity rather than a new default.

## 2. Which laws move when a C repo is measured as badly as a Java one

`--thin 0.57` keeps 57% of each network's edges -- the Java share -- and re-runs LAW-1 to LAW-5.

**The mask has to follow the edge, not the snapshot.** Coverage failure is a property of the call site: an
`obj.method()` whose receiver cannot be inferred is unresolved at *every* snapshot. The first version of this
sensitivity drew independently per snapshot, which dropped an edge at t and kept it at t + 1 -- LAW-2 read that
as a newly created edge and its choice count rose from 16,593 to 121,112 on libgit2 and from 10,746 to 235,931 on
libxml2, with LAW-3's persistence pairs and LAW-4's replay corrupted the same way. Those numbers were discarded.
The mask is now a keyed hash of the edge identity, and the choice count falls to 9,408 and 6,133 -- 56.7% and
57.1%, as it should. LAW-1 was unaffected either way, because it reads one snapshot.

| law | libgit2 full → thinned | libxml2 full → thinned | shift (SEs) | reading |
|---|---|---|---|---|
| LAW-1 heavy tails | +0.184 → +0.177 | +0.062 → +0.063 | −0.2, 0.0 | **robust** |
| LAW-2 attachment | +1.310 → +1.365 | +1.272 → +1.335 | +1.8, +1.7 | robust in sign and size, small **upward** bias |
| LAW-3 hub persistence | +0.013 → +0.017 | evaluable → **not evaluable** | +0.4, — | robust where it survives; **drops out** |
| LAW-4 centralisation | +0.004 → +0.003 | +0.026 → **+0.018** | −0.6, −2.4 | **attenuates ~30%** |
| LAW-5 decay | direction fails | direction fails | — | unchanged |

Four findings, each with a different consequence:

1. **LAW-1 is robust.** Losing 43% of edges moves it by a fifth of a standard error. Heavy tails survive bad
   measurement, so the coverage gap is not a threat to LAW-1 and no engine work is needed for it.
2. **LAW-2 is robust in sign and magnitude but carries a small upward bias** -- +0.055 and +0.063, the same
   direction in both repos. Lower coverage *inflates* α slightly. Against α values of 1.24 to 1.79 that changes
   no qualitative conclusion, but a between-language comparison of α carries a coverage-driven offset of roughly
   +0.06 in favour of the worse-measured language. It biases towards finding attachment, not away, which is worth
   stating plainly in the paper.
3. **LAW-3's failure mode is dropout, not bias.** Where it survives it barely moves (+0.4 SE), but thinned
   libxml2 becomes *not evaluable* -- "the null does not move", the ceiling the estimator already documents for
   repos with dominant hubs. So low-coverage languages will lose repos from LAW-3 non-randomly. The methods
   review's not-evaluable-dropout item covers the concept but not this cause, and LAW-3's evaluable count per
   language should be reported at matched coverage.
4. **LAW-4 attenuates by about 30%** in libxml2 (+0.026 → +0.018, −2.4 SE): observed and replayed Gini both fall,
   and the gap between them narrows. Against an effect of only 0.004 to 0.026 that is material. A between-language
   LAW-4 comparison at 99% against 57% coverage is biased **against** the worse-measured language, and the
   thinning run supplies the correction factor directly.

Uniform thinning is a lower bound on the damage. Real failures concentrate on dynamically dispatched calls rather
than falling evenly, so a selective null would hurt more. It is not modelled here and should be, if LAW-4's
between-language comparison is going to be load-bearing.

## 3. What to do about it

**Make coverage-matched thinning a standard part of every panel run.** Report each law twice: at the repo's own
coverage and at the panel's minimum coverage for that law's languages. It is a flag, it cost 247 seconds for two
repos, and it converts the coverage gap from an unquantified threat into a measured correction. That is a better
return than engine work for every law here.

**Engine work is not the lever for this study.** LAW-1 and LAW-2 do not need it. LAW-3 and LAW-4 need the
difference *reported*, and raising Java from 56% to even 75% would narrow rather than close the gap -- the
remainder is dynamic dispatch and standard-library calls, the first hard and the second not part of the
intra-repo network at all. Coverage work has a real product case on its own schedule, and it cannot touch the
pinned panel engine before the draw without re-pinning under Amendment 1.

**Owed before the freeze:** the scanner's file column on `unresolved` (so the coverage figure becomes a rate), the
amendment registering matched-coverage reporting, and -- if LAW-4 is to carry a between-language claim -- a
selective rather than uniform thinning null.

## The matched-coverage pass, run end to end on five repos

`laws_run_matched.json` (`--matched-coverage`): both passes over all nine laws, 10 repo-runs, **0 failures,
2,080 s**. `matched_share` chose **0.556** -- java's median, the worst-measured language -- and every network in
the second pass was thinned to it with the edge-persistent mask.

| repo | LAW-1 | LAW-2 excess | LAW-3 | LAW-4 |
|---|---|---|---|---|
| commons-lang (java) | +0.113 → +0.100 (−0.2) | +0.059 → **+0.258** (+2.7) | evaluable → **not** | +0.025 → +0.029 (+1.1) |
| prometheus (go) | +0.088 → +0.065 (−1.3) | +0.221 → +0.259 (+0.2) | +0.044 → +0.023 (−0.7) | +0.015 → +0.017 (+0.6) |
| sphinx (python) | +0.100 → +0.094 (−0.3) | +0.429 → +0.511 (+1.0) | +0.124 → +0.084 (−0.9) | −0.005 → −0.005 (0.0) |
| libgit2 (c) | +0.184 → +0.178 (−0.1) | +0.221 → +0.227 (+0.2) | +0.013 → +0.033 (+1.8) | +0.004 → +0.004 (+0.1) |
| libxml2 (c) | +0.062 → +0.055 (−0.2) | +0.133 → +0.164 (+0.8) | evaluable → **not** | +0.026 → **+0.018** (−2.5) |

Shifts are in SEs of the full-coverage estimate. Four readings, each extending what the two-repo test found:

1. **LAW-1 is robust in all five repos**, not just the two C ones: −1.3 to −0.1 SE after losing 44% of edges.
2. **LAW-2's excess is robust but biased UPWARD by coverage loss** -- every shift is positive (+0.2 to +2.7 SE).
   commons-lang's excess goes from +0.059 ± 0.074 (0.8 SE, not established) to +0.258 ± 0.104 (2.5 SE). So the
   earlier finding that low coverage inflates alpha carries through to the excess. The consequence matters for
   the paper: a worse-measured language's LAW-2 excess is biased **up**, so matched-coverage comparison equalises
   that bias rather than removing it, and the absolute excess at matched coverage is an over-estimate. The
   full-coverage figure remains the one to quote per repo.
3. **LAW-3's dropout is confirmed and is not C-specific.** commons-lang and libxml2 both become not evaluable at
   matched coverage -- 3 of 5 evaluable instead of 5 of 5 -- so a worse-measured language loses LAW-3 repos
   non-randomly, in java as well as C. This is the differential-dropout Amendment 5 item 4 asks to be reported.
4. **LAW-4's attenuation is repo-specific, not uniform.** libxml2 loses 2.5 SE (+0.026 → +0.018, the ~30% seen
   before) while the other four move by at most 1.1 SE. Against effects of 0.004 to 0.029 that is still enough to
   make a between-language claim unsafe, which is why Amendment 5 makes it descriptive -- but the attenuation is
   not a constant factor that could simply be corrected for.
