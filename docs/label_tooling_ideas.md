# Tools worth building to fix our labels — ranked by value per hour

Context: the keyword gate catches ~41% of curl's real fixes and ~26% of commons-lang's. The cascade
(`label_cascade.md`) recovers some of that from evidence already harvested. These are the next levers, in the
order I would build them.

## A. Cheap, and we already hold the inputs

**1. Resolve issue references through the forge API.** *The single biggest upgrade available.* T2 currently
reads the **verb** (`Fixes #N`) and never the issue. Resolving `#N` to its labels, type and state turns T2
into near-ground-truth, and rescues the slice of T5 that points at a genuine bug instead of a PR. Rate-limited
but trivially cacheable, and the numbers are already extracted for all 11 repos.

**2. Use the strong tiers as a free recall estimator, per repo.** Of the commits T1–T3 identify as fixes, what
share does the keyword gate also catch? That ratio is a per-repo "announcement rate" — how often this project
says *fix* when it fixes something — and it costs nothing to compute, where the manual recall audit costs an
hour per repo. **Caveat that must travel with it:** reverts and CVE fixes are a biased slice of all fixes and
probably announce themselves *less* than average, so this under-estimates recall. Use it to rank repos, not as
the number.

**3. Mine revert pairs for bug-INTRODUCING commits.** A revert names the sha it undoes, so that sha is a
defect-introducing commit at near-certain precision. 123–282 per repo, already extracted. This is a label we
simply do not have today, and it opens "what kind of change causes bugs" rather than only "what gets fixed".

**4. JIRA / Bugzilla key resolution.** commons-lang's messages carry `LANG-NNNN` — Apache JIRA keys that
resolve to an issue **type** (Bug vs Improvement vs Task). commons-lang is the worst label in the bank at 0.27
raw, and this would likely fix it outright. libxml2 and curl have their own trackers. Repo-specific work, high
certainty per repo.

**5. OSV / CVE → fixing-commit join.** `tools/laws_osv.py` already exists and currently yields a table for
exactly one repo. Running it across the bank gives a security-fix gold set, and LAW-9 becomes evaluable more
than once.

## B. Moderate effort, high scientific value

**6. SZZ-style blame linking.** From a fix's changed lines, blame backwards to the commit that introduced
them. We already harvest hunk ranges, which is most of the input. This is the standard MSR instrument and we
have never had it; it turns every fix into a (fix, inducer) pair.

**7. Release-note and changelog mining.** curl keeps `RELEASE-NOTES`, postgres publishes per-release bug
lists, often with commit references. Where it exists this is *curated human ground truth* — better than any
heuristic we can write — and it doubles as a validation set for everything else.

**8. Test-adjacency as evidence.** A commit that changes source **and** adds a test in the same breath is very
likely a fix. We have per-commit file paths and hunk ranges, so this is a query, not a model. Would recover
exactly the kind of commit the keyword gate misses (`smtp: result of Curl_bufq_cread was not used`).

**9. Diff-shape fix grammar.** The programme already found curl-specific fix shapes (added bounds checks, null
guards, no new allocation). Generalising that into a tier gives evidence from the *code* rather than the
*prose* — the only tier that would be immune to writing style.

## C. Where an LLM actually earns its cost

**10. Classify from the DIFF, not the subject.** Every audit so far judged from message text. An LLM reading
the diff would see the NULL check being added. Run it cheaply at scale, escalate only disagreements with the
cascade to a stronger model, and **validate against the samples we have already judged** so it inherits a
measured error rate instead of asserting one.

**11. Calibrate, don't replace.** Use the model to *estimate q* (the missed-fix rate) on thousands of
not-fix commits rather than the 40 I read by hand. That directly shrinks the widest interval we have — curl's
recall is 0.41 with a 95% band of [0.30, 0.68] purely because n=40.

## D. Design changes, not tools

**12. Keep the label multi-valued.** Store tier + evidence per commit, never a single boolean. Then a study
can run "T1–T3 only" and "T1–T4" and report both, which is a sensitivity analysis the programme cannot do
today because the label is one bit.

**13. Put recall on the LABEL CARD beside precision**, with its own gate. A label at 0.80 precision and 0.41
recall is not "fit" — it is fit for one purpose and unfit for another, and the card should say which.

**14. Measure per-repo announcement style as a covariate.** If the probability that a fix says "fix" varies by
project, era and author — and the recall audit says it does — then any cross-repo comparison that ignores it
is comparing writing conventions as much as code.
