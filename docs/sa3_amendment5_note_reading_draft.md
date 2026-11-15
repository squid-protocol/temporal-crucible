# SA3 — dated note to Amendment 5: the corrected reading rule (ACCEPTED by the owner 2026-11-15; not yet entered)

**Owner rulings of 2026-11-15**, made after the point estimates were partly seen, closing choices the
registration and Amendment 5 left open. To be entered into `docs/sa3_registration.md` with the second erratum,
as the first act of the scoring step, before the seal is re-taken.

1. **Defect 42.** The Holm step-down stops at the first test, in Holm order, whose primary statistic reads
   neither "supported" nor "contradicted". A contradicted test does not stop it. Nothing else in the step-down
   changes: a test after a stop that would read "supported" reads "not detected (Holm: an earlier test in the
   family failed)", as coded; every other test keeps its coded words.
2. **Defect 43, read literally.** A test reads "not robust to the statistic" whenever its primary and its
   residualised statistic read differently, whatever the primary reads — except a test already reworded by the
   Holm step. No new reading word is introduced.
3. **How it is checked.** The rule is built twice by different models and compared on every input, and the full
   table of coded against corrected readings is published (`docs/process/reading_rule_table.md`) for the owner
   to read.
4. **Counted beforehand**, over 729 combinations (three tests, three readings for each statistic): defect 42's
   change alters the reading in 135 and gives more "supported" in 51; defect 43's alters it in 604 and never
   gives more "supported"; together, 631 and 51. With every statistic "not detected", the two rules agree.

These are printed beside the coded reading, which remains the confirmatory one (Amendment 5 section 2).
