# LAWS — closed as a FAILURE, 2026-11-12 (owner)

Owner ruling, 2026-11-12: **the LAWS study is marked a failure.** No law verdict is claimed, no result is
published, and the registered confirmatory programme is abandoned rather than amended again. What follows is the
cause, the data that survives it, the problems in a list, and what a second attempt should do differently. A new
attempt starts from a fresh random batch; it does not inherit this frame, this draw or this panel.

**No statistic of any of the nine laws was ever computed on a panel repository.** Nothing below is a result
about software networks. There is no finding to retract, because none was ever claimed.

## The cause, in one line

**The oracles cannot run on historical snapshots of real repositories.** The engine was never the problem.

| language | engine scan | oracle evaluable | why the oracle failed |
|---|---|---|---|
| C | 6/6 ok | **6/6** | — |
| Go | 4/4 ok | 1/4 | `go: no modules specified` at the 2016 boundaries (pre-modules); syzkaller 2026 is 86% cgo-tainted |
| Java | 4/4 ok | **0/4** | `no recognised build file`, `gradle build not attempted (no offline)`, `mvn rc=1` — the oracle needs a built jar |
| Python | 4/4 ok | **0/4** | PyCG crashes identically on all four: `ImportManagerError: Can't add edge to a non existing node` |

**All 18 engine scans succeeded**, with 81.5%–99.9% of call tokens resolved. Every failure in the column that
matters is an instrument failure, and three of the four are a *build* failure: Java's and Go's oracles must
compile the snapshot, and a decade-old snapshot of a real repository does not build offline.

The primary universality test was pre-registered as a partial conjunction over C, Java, Go and Python needing
**3 of 4**. On these results only C is evaluable, so the maximum reachable is **1 of 4**. (The note on `main`
said 2 of 4 "whatever happens to Java"; `accp_result.json` has Java at 0/4, so even that was optimistic.) The
pre-registered fallback — 5 of up to 7 languages, routing through C#, Kotlin and PHP — rests on oracles that
have **never been run at all**, so it is not a rescue either. That is why this is a failure and not a
descriptive result.

## The problems, listed

1. **Oracle feasibility was never screened before the sample was fixed.** The frame, the fingerprint, the seeded
   draw, the 400- then 2,000-deep records, the seating walk and the licence rule all fixed the sample *before*
   anyone asked whether the oracles could run on the repos drawn. Every later problem is downstream of this one.
2. **Thirteen amendments in four days, and no law statistic.** The amendment process became the work. Each new
   obstacle produced a rule instead of a stop-and-rethink.
3. **Two amendments made after outcome data existed, and both weakened a bar** (11 and 12, both 11-11). The
   registration says so itself in its own honesty note. That is the thing pre-registration exists to prevent.
4. **Two different "Amendment 11" sections existed at once**, for several hours, because two work streams edited
   the registered document in parallel. Resolved on 11-12 by renumbering one to 13 — a numbering fix only.
5. **The one language that cleared the gate did so on repos that are no longer in the panel.** C passed 6/6 on
   `pure-data/pure-data` and `khronosgroup/vulkan-loader` — the two C seats the licence rule vacated the same
   day. The ACC-P pass and the seated panel never agreed with each other.
6. **Feasibility was mis-estimated by about 3.4x, twice, in the same optimistic direction.** The pre-screen put
   the clone-time pass rate at 20%; measured, it is **5.8%** (20 seats in 345 candidates). python was projected
   to need depth 178 and seated at 44; jsts was projected inside 400 and needs about 508.
7. **One bar did 95% of the filtering.** 308 of 325 rejections were "fewer than 2,000 first-parent commits". The
   cheap pre-screen that approximated it used *total* commits, which can exceed first-parent by 3x — so the
   screen both mis-ranked the languages and gave a number nobody should have trusted.
8. **A registered eligibility rule went unenforced for four days.** PANEL listed "OSI licence read from the
   repo" from 11-08; nothing checked it until 11-12. Enforcing it then cost 30% of the seats already taken, and
   removed a repo licensed MIT **or** Apache-2.0 — more permissive, not less — because GitHub reports
   `NOASSERTION` for licences its detector cannot classify.
9. **A frozen instrument froze a defect.** Freezing a harness for reproducibility also freezes its bugs, and the
   split between system-under-test and instrument had to be invented afterwards.

## What the data still supports

These stand on their own and are worth keeping. None is a claim about software laws.

1. **The engine resolves calls across decades of real code.** 18 of 18 snapshots scanned, 2007Q4 to 2026Q4,
   81.5%–99.9% of call tokens resolved, node-merge rate 0%–19.2% — per snapshot, in `docs/accp_result.json`.
   This was meant to be ACC-P's covariate; it is usable as a measurement of the instrument in its own right.
2. **A feasibility map for sampling historical panels**, measured rather than guessed: 81,006 metadata-eligible
   repositories across ten languages, a 5.8% clone-time pass rate, the commit bar as the binding constraint, and
   per-language walk depths (`docs/laws_seating/`).
3. **An oracle-availability map**, which is the single most reusable thing here: C's oracle runs on historical
   snapshots; Java's and Python's do not; Go's works only after modules. Any future study of call graphs over
   time should start from this table instead of rediscovering it.
4. **The estimators themselves** (LAW-1..8, 182 tests passing on simulated data with known answers). They were
   never the weak link and can be reused unchanged.

## What a second attempt should do differently

1. **Screen the oracle first, on a throwaway sample, before fixing anything.** "Does the oracle emit a graph at
   both boundaries?" is a sampling criterion, not a result to be discovered after the draw.
2. **Prefer oracles that do not build the snapshot.** Anything requiring Maven, Gradle or `go mod` against
   decade-old code will fail offline, and that is not a property of the language.
3. **Drive one repository per language end to end — all the way to a law statistic — before sampling anything.**
   A pilot that stops before the last step hides exactly the failure that killed this study.
4. **Register fewer bars, and none that has not been met once end to end.**
5. **Estimate with the real rule or not at all.** A cheap proxy that is wrong in the optimistic direction is
   worse than no estimate.
6. **One editor per registered document.** Parallel edits to a pre-registration produce colliding amendments.
7. **Treat a second amendment in one day as a signal that the design is wrong**, not as a rule to write.

## Kept on disk — do not delete (owner, 2026-11-12)

- **24 engine scan databases**: `/srv/storage_16tb/projects/gitgalaxy/acc-study/engine/<repo>@<quarter>/`
- **Blobless repo pool, 911 MB, ten languages**: `/srv/storage_16tb/projects/laws-seat-pool/`
- **Seating records** (every candidate, verdict and reason): `docs/laws_seating/`
- **Draw records and frame** (2,000-deep seeded order, fingerprints): `docs/laws_draw/`, `docs/laws_frame/`
- **ACC-P outputs**: `docs/accp_result.json`, `accp_prep.json`, `accp_diagnostics.json`, `accp_feasibility.json`
- **Pilot outputs**: `/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot/`

The registration (`docs/laws_hypotheses.md`) stays in the repository, unedited except for the failure notice at
its head and the Amendment 11 renumbering. A failed pre-registration is evidence about how the work went, and
deleting it would be the one genuinely dishonest move available here.
