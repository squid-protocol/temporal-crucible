# SA3 — proposed erratum to Amendment 5 (DRAFT; not in force until the owner accepts it)

**2026-11-14.** Two sentences of Amendment 5 are wrong as written. Neither changes what the confirmatory run
does. Both were found by the independent review of the owner-run job's specification
(`docs/process/reviews/owner_job_spec_review_claude.md`, M7 and M8).

**1. Section 5, the example for defect log 61.** The amendment says: "Case is ignored, so 'Fix UTF-8 decoding'
and 'fix x86-64 build' are fix references." The first example is right for a different reason: `UTF-8` is in
capitals and matches the tracker-key pattern as the registration writes it, with or without regard to case.
Only the second ("x86-64"), and forms like "sha-1", depend on case being ignored.

Proposed wording: "Case is ignored, so 'fix x86-64 build' and 'Fixed sha-1 fallback' are fix references
(defect log 61). Separately, a capitalised token of the same shape that is not a tracker key — 'Fix UTF-8
decoding', 'Fix SHA-1 fallback' — also matches, and did under the registration's own pattern; no sensitivity
removes those."

Consequence: `PU_tracker_keys_case_sensitive` removes lower-case keys only. The count published before scoring
(Amendment 5 section 7 item 5) is of commits that qualify only through a lower-case key.

**2. Section 9, the test of the check.** The amendment says five faulty copies and five clean copies are run
and "all three layers must flag each faulty copy and none of the clean ones". A fault seeded into the scorer
can only be seen by the third layer (the comparison scorer); the first two look at inputs and at the placebo
stage.

Proposed wording: "the check as a whole must flag each faulty copy and none of the clean ones, and for each
faulty copy the layer that is expected to catch it is written down before the test is run."

**Also for the record, no change of wording needed:** the first layer as section 9 describes it compares
tables with the files they were built from and so cannot fail; it is built together with the comparison
scorer, where it has something to compare.
