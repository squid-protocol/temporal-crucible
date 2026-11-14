# Study defect log — what has been wrong, who found it, and what would have caught it sooner

Started 2026-11-14 from the record of 2026-11-13/14 (MOD-1, the HR re-runs, SA3, SA3-CH). It is the history
that a study-design scaffold and its reviewer roles should be built from: every entry is a fault that
actually occurred in this repo, not a hypothetical.

**How to read an entry.** *Class* is what kind of thing was wrong. *Found by* is who caught it. *Passed* is how
many independent reviews of that artefact had already missed it. *Earliest catch* is the cheapest check that
would have found it before it cost anything.

**Who is who.** *Author* = the session that designed and built the studies. *R1, R2, R3* = independent Claude
sessions, read-only, forbidden to compute outcomes (R1 reviewed MOD-1, then SA3's and SA3-CH's designs; R3
reviewed the whole built system). *G* = Gemini 4 Argon, on the pull requests.

## The log

| # | study | class | the fault | found by | passed | earliest catch |
|---|---|---|---|---|---|---|
| 1 | MOD-1 | instrument | Language called by raw extension counts; 10 of 38 repos measured on bundled side code | author, checking inputs before a run | 0 | print each repo's language mix before drawing |
| 2 | MOD-1 | universe | Ranked every scanned file; only source files of one language could ever be positive | R1 | 0 | assert: ranked set = set that can be positive |
| 3 | MOD-1 | label | Label's top tiers read an input that existed for 11 of 46 repos; the rest silently fell back to keywords | R1 | 0 | per-repo table of label inputs present |
| 4 | MOD-1 | unit of analysis | Merges are the labelled unit in merge-workflow repos, and were filtered out | R1 | 0 | per-repo count of commits kept vs dropped |
| 5 | MOD-1 | exclusion | A repo whose source was never scanned was reported as "under the floor" | R1 | 0 | one reason per exclusion, computed from structure |
| 6 | MOD-1 | universe | C and C++ split: a C++ repo could never have a header fixed | R1 | 0 | per-repo share of files by extension that can be positive |
| 7 | MOD-1 | inference | A directional hypothesis read two-sided; a null printed as "age is not the moderator" | R1 | 0 | reading rule written as a truth table |
| 8 | MOD-1 | spec vs code | The registered re-dating rule was a no-op in the code | R1 | 0 | rule-to-code table |
| 9 | MOD-1 | inference | Repos that suggested the hypothesis pooled into its confirmation; the motivating sentence was false under the registered cut | R1 | 0 | list which repos were seen before registration |
| 10 | MOD-1 | power | No statement of the smallest detectable effect | R1 | 0 | required slot |
| 11 | MOD-1, HR | label | A licence change and a lint rule touching most of a repo were counted as fixes; they made the two strongest positive results | author, after the result (a repo with every file positive) | 1 | largest labelled commit's share of positives, per repo |
| 12 | HR-1/2/3 | universe | The programme's one "replicated" predictor (+0.082) was the universe fault of #2 | author, re-running under the checklist | — (published) | #2's assertion |
| 13 | SA3 | statistic | The registered statistic scored pure noise as "contradicted" in 97% of simulated studies | R1 and G, independently | 0 | simulate the statistic on a null before registering |
| 14 | SA3 | control | Negative control was "touched at all", not matched; contained commits with `Fixes:` trailers | R1 (matching), R1 and G (trailers) | 0 | simulate a pure-activity predictor through the gate |
| 15 | SA3 | control | **Reviewer-introduced.** G's replacement control was conditioned on the outcome; a pure-activity predictor passed it in 100% of simulated studies | author, reconciling the two reviews by simulation | 0 | same |
| 16 | SA3 | label | The revert tier marked code written after the snapshot (93% of resolvable reverts) | R1 | 0 | for each tier, read 20 examples |
| 17 | SA3 | spec | Merge inheritance was one sentence; the open choices moved positives severalfold | R1 | 0 | every rule stated so that two builders would write the same code |
| 18 | SA3 | power | Power taken from a placebo with no directory structure | R1 | 0 | — |
| 19 | SA3 | floor | Floor counted files; 30 positive files could come from 18 commits | R1 | 0 | floors in the unit the evidence comes in |
| 20 | SA3 | process | **Reviewer-introduced.** A reviewer rewrote the registration in place; the original survived only in git | author | — | rule: reviews are comments, changes are amendments |
| 21 | SA3 | spec | **Reviewer-introduced.** A new predictor described as a table column; it lives in a JSON blob | author, reconciling | 0 | open the data before naming a field |
| 22 | SA3 | code | Merge search ran through bot commits; fix-carrying merges fell into the control pool; completeness measured against the wrong file list | G, code review | 0 | synthetic repo with a known answer |
| 23 | SA3 | instrument | Nesting depth: an else-if chain read as depth N in C-family languages and 1 in Python | G | 0 | self-test with known-depth snippets per construct, per language |
| 24 | SA3 | record | Clock times written into three amendments were estimates, up to two hours ahead | author | 2 | take times from the commit, never from memory |
| 25 | SA3 | gate | **Reviewer-proposed, author-adopted, never simulated.** The block-permutation placebo fails a correct pipeline 71% of the time | the gate itself, then R3 | 2 | simulate every gate under a null and under an effect |
| 26 | SA3 | **blinding** | Diagnosing #25, the author printed two numbers per predictor from which the confirmatory point estimates can be recovered (real ≈ 4 × permutation − 3 × shift) | R3 | 0 | no diagnostic touches real outcomes; failures are debugged on synthetic data |
| 27 | SA3 | power | Power ignored between-repo spread: stated 0.032, really about 0.05 to 0.08 | R3 | 3 | compute the test's own null width from non-structural attributes |
| 28 | SA3 | statistic | The primary statistic lets +0.002 to +0.006 of size through; the registration said exactly zero | R3 | 3 | a size-only surrogate through the pipeline |
| 29 | SA3 | universe | mediawiki's merges all flagged as bot; half of freebsd-src is imported third-party code; swift is mostly compiler test fixtures | R3 | 3 | per-repo page: top directories, bot share, file kinds |
| 30 | SA3 | label | Sampled precision 73–81%; "fix" means "has a ticket" in django and mediawiki | R3 (R1 had warned) | 3 | label audit as a required slot with a threshold |
| 31 | SA3 | code | Control filled missing values with zero; a rule silenced two registered measures everywhere; the lock was three file names; about ten registered outputs not coded | R3 | 1 | rule-to-code table; end-to-end synthetic run |
| 32 | SA3 | process | Four amendments on an edited body; the scorer disagreed with the text in nine places | R3 | — | one consolidated spec, regenerated after every amendment |
| 33 | SA3 | tests | No test for any SA3 tool; the self-test's tolerance was five times the gate's | R3 | — | tests are part of the deliverable |
| 34 | SA3-CH | confound | Four activity groups left the activity confound in: 33–37% false "supported"; a pure lines-changed predictor passed every gate | R1 and G | 0 | simulate the confound; benchmark predictor as a gate |
| 35 | SA3-CH | definition | "Prior year" by calendar missed a quarter to a half of the commits actually between the two snapshots | R1 | 0 | compare the two counts per repo |
| 36 | SA3-CH | measure | A per-line rate changes whenever the file's length does | R1 and G | 0 | list every way the number can move without the construct moving |
| 37 | SA3-CH | instrument | "Zero unless the file was edited" was false: the engine's risk score depends on the file's path and its folder's dominant language | R1, reading the engine | 0 | read how the instrument computes the number |
| 38 | SA3-CH | measure | A bounded score cannot rise from the top; raw change ranks persistently risky files low | G | 0 | — |
| 39 | SA3-CH | code | Preparation skipped merge commits (7,832 changed files with no counted commit in one repo); rename-following built a map and never read it | R3 | 0 | unused-variable check; reconcile two counts that should agree |
| 40 | all | process | No prior-work check before SA3, SA3-CH or the WCC draft, against the owner's standing rule | author, on reflection | — | required slot, filled before design |
| 41 | all | controls | Placebos (must show nothing) but no positive control (a known effect the pipeline must recover); a null cannot tell "no effect" from "cannot see effects" | author, on reflection | — | required slot |
| 42 | SA3 | inference / code | Holm step-down treats a "contradicted" primary as a failure, so two later primaries with intervals wholly above zero read "not detected"; the registration does not say that, and the consolidated text hid the difference | R4 (pre-scoring code review), by an end-to-end synthetic run | 3 | end-to-end synthetic run with one effect planted negative |
| 43 | SA3 | spec vs code | "Not robust to the statistic" fires only when the primary statistic reads "supported"; the rule says whenever the two differ | R4 | 3 | reading rule as a truth table, tested cell by cell |
| 44 | SA3 | seal | The seal covers the scorer but not the labels, the scans, the universe rule or the governing registration; three drawn repos' outcome files were rewritten after the leak and only a side calculation could show they were unchanged | R4 | 1 | seal every input the result depends on |
| 45 | SA3 | reproducibility | One random stream shared across repos and predictors: a change to which secondary measures are scored moved the specificity mean by up to 0.0013 and a per-repo value by 0.011 | R4 | 1 | one stream per repo and purpose |
| 46 | SA3 | disclosure | The amendment said a rule change affected two measures; it also un-silenced three count measures in 14 repo cells | R4 | 0 | diff the scored-cell table before and after any rule change |
| 47 | SA3 | output | Outside the three confirmatory tests the output still says "supported" at an unadjusted 95%, including for the exploratory measure and when the gate has failed | R4 | 1 | one vocabulary for confirmatory readings, another for everything else |
| 48 | SA3 | code | The "tracks reverted changes" reading compares 18 repos against 15 | R4 | 1 | every comparison names its repo set |
| 49 | all | process / safety | A read-only reviewer changed a corpus clone: `git ls-tree -l` on a blobless partial clone (`blast`) fetched missing blobs from upstream and triggered an automatic gc; 39 packs added, HEAD reflog emptied; HEAD, branches, tags and working tree unchanged | the reviewer, self-reported | — | every agent runs git with `GIT_NO_LAZY_FETCH=1` and `gc.auto=0`; partial clones listed in the brief |
| 50 | WCC draft | estimand | "Fix sets minus ordinary sets = 0" is not the null: on the real sets a file's byte count reads −0.020 (interval excludes zero); in simulation a null predictor is "contradicted" in 90% or "supported" in 99% of studies depending on which kind of commit is more selective | R5 (WCC design review), real non-structural attributes + simulation | 0 | run non-structural attributes through the design before registering it |
| 51 | WCC draft | gate | The activity-benchmark gate fails a correct study when the hypothesis is true (the study reports nothing in 59% of simulated cases) | R5 | 0 | simulate every gate under an effect as well as under a null — the draft said it would, and had not yet |
| 52 | WCC draft | power / feasibility | 9 of 40 development repos clear the draft's floor; the proposed confirmation set would yield about 5 to 8 usable repos; two of its "C" repos are Dart and one is the engine's own repo | R5 | 0 | count what clears the floor before writing the design around it |
| 53 | WCC draft | matching | Ordinary commits matched only on files touched; unmatched directory and timing give 21–48% false readings in simulation | R5 | 0 | — |
| 54 | SA3 | spec vs code | The consolidated text says tainted merges are "in no outcome and no control"; `sa3_outcomes.py` counts a merge that inherits a fix reference as a positive and uses the tainted set only for the keyword outcome and the control pool. Read literally the text also contradicts its own inheritance rule | the control repository's builder (the contradiction) and its reviewer (what the code does) | 4 | a generated repo with merges and a known answer |

## What the log says

**By class** (first 41 entries): label 5 · universe 5 · code 4 · control or gate 4 · statistic 2 · power 3 · measure
or instrument 6 · inference 2 · spec 3 · process, record, tests 6 · blinding 1.

**Nothing here is exotic.** The same few questions would have caught most of it:

1. *Can everything I am ranking actually be positive?* (2, 6, 12, 29)
2. *Is the label the same thing in every repo, and is it what I say it is?* (3, 11, 16, 30)
3. *What does this number do when there is no effect — and when the only thing present is size, or activity?*
   (13, 14, 15, 25, 28, 34) — every one of these was found by simulation, never by reading.
4. *How does the instrument compute this, and what else moves it?* (1, 23, 36, 37, 38)
5. *Does the code do what the text says, rule by rule?* (8, 22, 31, 39)
6. *What have I already seen, and what can I still claim?* (9, 26)

**Reviews did not converge.** The artefact reviewed most (SA3) had three faults found on its third review
that each of the first two had passed (27, 28, 29), plus one the first review itself introduced (25).

**Reviewers add faults.** Four entries (15, 20, 21, 25) came from a reviewer's proposal. A reviewer's fix needs
the same test as the author's design.

**The most expensive fault was a debugging habit, not a design choice** (26). When a gate failed, the author
investigated on real data. Nothing in the checklist said not to.

**Two faults were found by nobody for the whole programme until this week** (11, 12), and both had already
produced published results.

**Fourth review, same artefact (entries 42–48).** R4 reviewed SA3's code after three reviews and a round of
fixes, and still found one blocker and six lesser faults. Its blocker was found the way every statistic and gate
fault here has been found: by running the whole thing on synthetic data with a known answer.

**Entry 54 ruled by the owner, 2026-11-14:** the code governs (a tainted merge that inherits a fix reference is
a positive); the text is corrected in SA3's next amendment.

**First fault found by the control repository (entry 54),** before any pipeline had been run on it: writing
down the expected label for a generated merge forced a choice the text does not make.

## Still open

- No estimate of how many faults remain in SA3 as it stands. A fresh review of the already-reviewed system and
  a seeded-fault test are proposed, not run.
- This log holds only faults that were found. It says nothing about the kinds nobody here knows to look for,
  which is what a prior-work review is for.
