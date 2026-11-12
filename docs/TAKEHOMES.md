# Take-homes: what this program has learned

The short version of everything in the [experiment journal](journal/README.md). The **curated** part below is
edited by hand when a result shifts the big picture. The **full list** is generated from the journal entries
(`python tools/journal.py build`).

Evidence levels:
- **replicated:** passed on repositories chosen after the original result;
- **supported:** registered and passed;
- **mixed:** passed in some arms;
- **not supported:** failed the registered test;
- **exploratory:** descriptive, no confirmatory claim.

The register of record is [`HYPOTHESES.md`](HYPOTHESES.md). If anything here disagrees with it, the register wins.

## The big picture (curated, 2026-11-07)

**1. GitGalaxy is good at what code *is*, where it *came from*, how it *lives*, and where the outside world
*touches* it.**
- **Library and platform coupling** mark where outside change lands. *Replicated.*
- **A layered fingerprint finds copies** across forks, C to C++ rewrites and vendoring (80–94%). *Supported.*
- **Code reading can check patch status**, for surgical-fix libraries (zlib). *Supported.*
- **Codebase natural history** (infant mortality, structural freeze, persistent archetypes) and **regime marks** are
  visible. *Supported.*

**2. It is not a bug or regression predictor.**
- History predicts: recidivism, change entropy, and the location of past fixes.
- Structure adds nothing beyond size and churn: per-file scores, change shape, centrality, archetypes, atypicality,
  defensive code at birth.
- The few structural signals that survive are narrow:
  - `goto` raises the security-fix rate (*replicated*);
  - danger comments at birth (*supported once, replication inconclusive*).

**3. Code has a shared keyword grammar.**
- Functions are built by the same rules across 22 languages and inside 97% of projects, beyond size. *Replicated at
  population scale.*
- Breaking the grammar does not mark interesting code (outliers are mostly ordinary).

**4. Functions come in shapes, and the shapes form a lattice.** *Exploratory.*
- **Shared bricks:** a few hundred combinations cover half of all functions.
- **Growth:** shapes grow one keyword family at a time.
- **Families:**
  - a public/OO ladder used everywhere;
  - a private-C ladder concentrated in operating-system repos.
- **Constraint:** real code builds about half the mid-size shapes chance would.
- **LAT (scored):**
  - fix kinds land on different families beyond size, modestly (regression fixes hit simpler, lower-rung
    functions);
  - lattice moves add nothing to regression prediction beyond churn;
  - 71% of functions never change shape. *Supported / not supported.*

**5. Read signals by what their rules match, not by their column names.**
- The engine now carries display names: `struct_linear` = structural keywords, `state_safety_neg` = unsafe
  constructs.
- Several rule leaks are fixed (gitgalaxy#8024). Kernel and Windows vocabulary gaps are open (gitgalaxy#8016).

**6. AI models leave a structural handwriting, until a shared codebase launders it.** *Exploratory, plus registered GG / FLT / WILD.*
- **Lab:** two independent lenses find each model in the lab 83–84% of the time; Sonnet vs Haiku is as separable as
  Claude vs Codex.
- **GitGalaxy:** the eras separate at AUC 0.88.
- **Habits that repeat between settings:** private helpers, small call-heavy functions, cleaner grammar, no trivial
  functions.
- **Inside one codebase and era (WILD, registered):** Sonnet vs Opus functions are barely distinguishable (AUC 0.57,
  within the commit-permutation null), as FLT found.
- **Next test:** fresh whole programs (round 3). Synthesis:
  [journal](journal/2026-11-07-model-handwriting-synthesis.md).

**7. Declared AI assistance changes structure a little and defect outcomes not at all (so far).** *Exploratory,
2026-11-11; plus prospective AIC and the living ARG.*
- **Dependencies:** within the same author, AI-declared commits add more new callees than that author's own
  changes of the same size (median +0.28 per modified function, 11 of 13 people). Function *shape* moves no more
  often — structure stays put. Registered prospectively as AIC, scored only on commits made after 2026-11-11.
- **Comments:** declared-AI commits do not change how much code is commented on average, because tools pull
  opposite ways — Claude-assisted commits comment about twice as much as Codex-assisted ones.
- **Defect outcome: nothing.** Code in a declared-AI commit is followed by a fix **no more often than the same
  author's own code of the same size**: 0.984×, CI 0.87–1.11, on 339 events, stable under tighter strata and a
  doubled window. The crude gap people would quote (58% vs 46%) is **composition** — one maintainer supplies 387
  of 583 AI-marked commits in the corpus.
- **And the obvious trend argument fails:** the regression-fix share nearly doubled since 2018 (9.98% → 19.90%),
  but the rise was well under way in 2020–2024 when AI-marked commits were exactly zero.
- **The method lesson, which outlives the result:** on this question the crude number, the per-repo number and the
  within-repo number all disagree with the within-author number, and only the last one controls *who*. Quote the
  within-author contrast or quote nothing.
- **Limit:** the exposure is declared-only — a floor and a project convention (harfbuzz marks 11.6% of commits,
  curl 0.3%) — and confounding by indication survives a within-author contrast. ARG carries the prospective looks.

**Corrections to keep in mind when quoting older summaries:** see [`SYNTHESIS_2026-11-06.md`](SYNTHESIS_2026-11-06.md) § 3
(LIB's outcome is library-named work, SRCH refuted the searcher-age story, CHG's 2.9× was mostly churn, and others).

## Every take-home, by theme (generated from the journal)

<!-- journal:begin (generated by tools/journal.py build; do not edit by hand) -->

### Identity, copies and provenance

- **A COBOL program's paragraph call network survives mechanical translation and alone finds a port's own source 24% of the time (sfs 2.4%, chance 0.7%), but GitGalaxy cannot read it through the translator's dispatcher, which half the ports use.** — mixed, 2026-11-08 · [journal](journal/2026-11-08-cobol-java-call-networks.md)
- **A project's keyword mix (95.9%) and its sfs structural fingerprint (99.0%) identify it across eras five or more years apart, and its mix changes in spurts at architecture events; but turnover does not track regressions, and whether coupling centralises with age is project-specific.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-project-identity-fingerprints.md)
- **Code-reading patch checks work for libraries whose security fixes are surgical (zlib: 0 of 1,229 wrong, 30/30 on modified copies) and fail for refactoring-fix libraries (expat).** — mixed, 2026-11-06 · [journal](journal/2026-11-06-patch-status-by-reading-code.md)
- **A layered fingerprint (call set + control-flow skeleton + profile) finds copies the coarse one misses: fork copies 46% to 80%, C to C++ BoringSSL 29% to 94%, vendored zlib 91%.** — supported, 2026-11-06 · [journal](journal/2026-11-06-finding-copies-of-code.md)

### Where the outside world touches code

- **Files that call a library's API receive the work that names that library (replicated, +0.44 over size), and platform conditionals mark where extrinsic fixes land.** — replicated, 2026-11-06 · [journal](journal/2026-11-06-library-and-platform-coupling.md)
- **Extrinsic (platform, compiler, dependency) work is bursty, but the bursts are not timed to GCC or Clang major releases (share change +0.002 and +0.009, with a placebo just as large); only where extrinsic work lands is predictable, not when.** — not-supported, 2026-11-06 · [journal](journal/2026-11-06-compiler-release-bursts.md)

### How code lives: natural history and regimes

- **One sentence a newcomer can quote. Write it once the study is scored; keep it honest about evidence level.** — pending, 2026-11-08 · [journal](journal/2026-11-08-software-network-laws-many-labs.md)
- **Call networks are static most quarters and change in jumps, but the jumps mostly track code volume; CVE fixes rewire calls more than other fixes (extrinsic fixes least), and rewired files attract more later fixes beyond churn and partly beyond size.** — mixed, 2026-11-08 · [journal](journal/2026-11-08-call-networks-over-time.md)
- **Hubs are a stable skeleton that grows rich-get-richer; networks centralise and drift toward more cross-file wiring rather than optimising; files in call cycles or with heavy coupling get more later fixes beyond size, churn and their own fix history.** — mixed, 2026-11-08 · [journal](journal/2026-11-08-call-network-shape.md)
- **Across eight new repos in five languages, hubs persist and attract new calls, and rewiring, coupling and cycles each mark files needing later fixes (jointly, beyond size, churn and prior fixes); but the jumps picture, centralisation and several C findings do not carry, concurrency code is central outside C, and pointer-rich hubs are a C property.** — mixed, 2026-11-08 · [journal](journal/2026-11-08-call-network-replication.md)
- **Models have a strong structural handwriting when they write whole programs alone (83–84% identification in the lab, independent lenses agree; eras of a codebase separate at AUC 0.88), but inside one shared codebase it nearly vanishes (WILD: AUC 0.57, within chance): conventions launder it.** — mixed, 2026-11-07 · [journal](journal/2026-11-07-model-handwriting-synthesis.md)
- **Inside GitGalaxy's shared codebase, Sonnet- and Opus-written functions are barely distinguishable (AUC 0.57, inside the commit-permutation null): the lab's strong model handwriting mostly vanishes under a codebase's conventions.** — not-supported, 2026-11-07 · [journal](journal/2026-11-07-model-handwriting-in-the-wild.md)
- **Gemini-era GitGalaxy functions were long, nested, inline-commented and public; Claude-era ones are short, call-heavy and twice as often private helpers (as in the lab). Functions rarely change shape (88% never; 2.8% of weeks), and when they do it is one signal at a time, mostly growing.** — exploratory, 2026-11-07 · [journal](journal/2026-11-07-gitgalaxy-eras-and-lattice-movement.md)
- **Development regimes leave a structural mark (Gemini-era vs Claude-era AUC 0.877), but the autonomous fleet does not write measurably differently from interactive sessions.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-eras-and-authorship.md)
- **No fix class has a pooled age signature, and the exploratory idea that the searcher (fuzzer vs human) sets CVE age was refuted on unseen repos; descriptively, CVE fixes mostly change code 2.1–3.7× older than ordinary commits, whoever finds them.** — not-supported, 2026-11-06 · [journal](journal/2026-11-06-cve-age-and-who-finds-it.md)
- **Code has a natural history: young functions die 2.9× faster than mid-aged ones, shape change slows to 0.46× with age, 88% of edited functions keep their archetype, and include hubs are stable and grow sub-linearly, but hubs change more than other files, not less.** — supported, 2026-11-06 · [journal](journal/2026-11-06-codebase-natural-history.md)

### Predicting fixes, regressions and CVEs

- **Fitted on one repo and scored on the other, a commit's edit-type vector separates message-labelled fixes from non-fixes at AUC only 0.57-0.59 (size alone 0.54-0.55) and regressions not at all, but recognises extrinsic fixes at 0.67-0.71 through preprocessor and type edits; the labelling claim was withdrawn before registration and the hand-judged samples were not spent.** — exploratory, 2026-11-12 · [journal](journal/2026-11-12-etyp-label.md)
- **Against non-fix commits of the same size and magnitude, a fix edits conditions and operators in place or adds a branch and does not rewire (LOGIC 1.18 and 1.28, WIRING 0.81 and 0.67 in curl and libarchive), and extrinsic fixes are marked by TYPE and PREPROC edits in both repos; as a forward signal the type of an edit moves the one-year fix rate only about 1.1x after size, history and magnitude; exploratory and uncorrected.** — exploratory, 2026-11-12 · [journal](journal/2026-11-12-etyp-fix-vectors.md)
- **Classifying what each new condition tests covers every case but adds nothing to recognising a fix (AUC gain +0.000 and +0.005 across curl and libarchive); the one clean replication is that fixes add variable-to-variable relational conditions at 1.8x the rate of size-matched non-fix commits, and the null-check kinds turn out to be house style rather than meaning; the stop rule set in advance was met and the line is closed.** — exploratory, 2026-11-12 · [journal](journal/2026-11-12-econd-condition-content.md)
- **The never-audited other-fix class carries 85-97% of the outcome mass and was 0.73 precise on C but 0.38 outside it, because Go, Java, Python and Rust projects say "fix" for lint, mypy, javadoc and typos; requiring the fix word in the commit SUBJECT rather than the body, plus test/doc path and refactor/prose exclusions, lifts it to 0.76 pooled and 7 of 8 repos over the gate, and closes the language gap (C 0.75 vs non-C 0.77).** — exploratory, 2026-11-11 · [journal](journal/2026-11-11-otherfix-precision.md)
- **A file-year fix model reaches recall@20%-of-lines 0.30 out of repo against an attainable 0.47 and a perfect-rate ceiling of 0.68; M1's three network terms all survive author and change-coupling controls with file-clustered SEs (1.29/1.49/1.31) and author count is the strongest term at 2.06; fixing the labels buys 3-4 points and closes the C/non-C gap but leaves the 22-point unmeasured-rate wall untouched, and raises dispersion rather than lowering it, so the headroom is real signal and not label noise.** — exploratory, 2026-11-11 · [journal](journal/2026-11-11-error-prediction-ceiling.md)
- **Code in declared-AI commits is followed by a fix no more often than the same author's own code of the same size (0.984×, CI 0.87–1.11, 339 events); the striking crude gap (58% vs 46%) is composition — one maintainer supplies 387 of 583 AI-marked commits — and the regression-fix share nearly doubled since 2018 but the rise predates AI entirely.** — inconclusive, 2026-11-11 · [journal](journal/2026-11-11-ai-adoption-fixes.md)
- **Of the engine's newer metrics, the screen's leads were almost all leftover size; the one survivor is amplified_cascading_flux (state writes inside branches), which beats size on nDPI and openssl but not curl, so it needs its own test on an unseen repo (AMP-H1).** — mixed, 2026-11-06 · [journal](journal/2026-11-06-untested-engine-metrics-screen.md)
- **Of 225 GitGalaxy file-metric forms, only platform-conditional density per line finds one fix class (extrinsic) at equal size on unseen repos (+0.154 harfbuzz, +0.102 libarchive); no metric finds CVEs beyond size, and the churn candidates for regressions and other fixes failed holdout.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-the-225-metric-screen.md)
- **To find unannounced security fixes, history (where past CVE fixes and fix activity were) beats the change signature: AUC 0.720, top-10% enrichment 2.93×.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-silent-patches.md)
- **Files that call input APIs or handle raw byte buffers with a length lose to size at finding CVE fixes on curl, openssl and harfbuzz (pooled −0.092 and −0.054); only nDPI, with its fuzzer-found parser CVEs, is positive.** — not-supported, 2026-11-06 · [journal](journal/2026-11-06-input-facing-code.md)
- **Files containing goto get security fixes more often at equal size (1.59 on nDPI + openssl, 2.80 on five unseen repos), but the goto-to-lifetime-fault link (7.1×) did not replicate: goto is a general security-risk marker, not a fault-type fingerprint.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-goto-macros-and-fault-types.md)
- **Code that OSS-Fuzz has just started reaching does not carry the next CVE fixes beyond size: directional only on nDPI, where fuzz coverage is about 96% saturated, and worse than size on curl (−0.195).** — not-supported, 2026-11-06 · [journal](journal/2026-11-06-fuzz-frontier.md)
- **CVE fixes add guard clauses 1.88× as often as ordinary fixes, and the three fix kinds have distinct keyword signatures: CVE = branch + pointers + `#define`; regression = new functions, globals, state; extrinsic = macros, asm, imports.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-fortification-and-fix-signatures.md)
- **Fix classes have distinct histories (CVEs recur in place, extrinsic fixes recur on an environment-facing set of files, regressions follow general fix activity and never recur in place), but no snapshot metric sees the class.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-fix-classes-have-different-histories.md)
- **Functions born with more defensive code get CVE fixes at the same rate as others (whole-life rate ratio 0.96, a fairly tight null).** — not-supported, 2026-11-06 · [journal](journal/2026-11-06-defensive-code-at-birth.md)
- **A commit that skips files that usually change with the ones it touches is not more often regression-inducing once commit size is controlled (−0.012), and omission is equivalent to merely touching well-coupled files; commit size stays the best predictor.** — not-supported, 2026-11-06 · [journal](journal/2026-11-06-co-change-omission.md)
- **Shape change looked like a 2.9× regression signal, but it is edit size: engine change features lower churn's recall (41.3% to 38.7%).** — not-supported, 2026-11-06 · [journal](journal/2026-11-06-change-shape-vs-regressions.md)
- **Scored by AUC, the engine's own history columns lose to file size on nDPI and function memory loses to function size, but scored per line reviewed on unseen openssl, prior security fixes (recall@20 0.451 vs 0.271) and change entropy beat both size orders.** — mixed, 2026-11-05 · [journal](journal/2026-11-05-history-forward-and-effort-aware.md)
- **Files with function-like macros or goto get security fixes about twice as often as files of the same size (2.03 nDPI, 2.33 openssl; replicated), though as a ranking this does not beat size; mid-size-file centrality fails on unseen repos and is closed as a lead.** — mixed, 2026-10-23 · [journal](journal/2026-10-23-centrality-and-dynamism.md)
- **On 957 fresh curl bug-label events, change entropy (HCM1_LD_30, frozen from the CVE selection) beat a line count out of selection (AUC 0.868 vs 0.830), while small-file centrality died (PageRank inverted, AUC 0.259) and the monotone lift shape failed in 5,000 of 5,000 bootstraps.** — mixed, 2026-09-13 · [journal](journal/2026-09-13-bug-label-expansion.md)
- **The file that had the last security fix is where the next one lands: prior-fix count beats both structural exposure and a line count at a 20%-of-lines review budget on curl and nDPI (p<1e-4), while structural exposure ties a line count.** — replicated, 2026-09-12 · [journal](journal/2026-09-12-recidivism-and-review-budget.md)
- **On nDPI, recidivism replicated and every structural null held (equivalence-confirmed), but every structural positive from curl (safety_score, the fix grammar, the fix-shaped signature, danger density) failed; the one surviving structure signal for the first CVE was centrality, the hot-files axis.** — mixed, 2026-09-12 · [journal](journal/2026-09-12-ndpi-replication-battery.md)
- **On curl's held-out later CVEs, the memory-danger and IO vectors do not beat a line count for their own CWE families, and the vectors are not specific (the memory set ranks highest even for info leaks); cert/auth vocabulary is dead on C and concurrency was untestable.** — not-supported, 2026-09-12 · [journal](journal/2026-09-12-mechanism-specificity.md)
- **curl's security fixes have a recognisable shape (branch and pointer additions without new allocations) that is not a fix-size artifact, but it does not travel to nDPI's fuzzer-found fixes at any size floor; reverts read as net removal, a clean instrument check.** — mixed, 2026-09-12 · [journal](journal/2026-09-12-fix-shape-and-fix-grammar.md)
- **History predicts fixes (recidivism, change entropy); per-file structural scores reduce to file size.** — not-supported, 2026-09-12 · [journal](journal/2026-09-12-first-validation-program.md)
- **On curl, security fixes do not lower aggregate structural exposure (p=0.77) and introducing commits do not raise it; only the safety_score vector moved its assumed way (p=0.0072, curl only), and the function-level guard-deficit and danger-density ideas did not hold.** — mixed, 2026-09-12 · [journal](journal/2026-09-12-curl-exposure-deltas-and-signal-anatomy.md)
- **Among 36 change-entropy (Hassan HCM) variants, none clears the size wall in 3 of 4 LOC bands; the best, HCM1_LD_30, beat a line count only as a discounted best-of-36 result; small-file centrality could not be evaluated on CVE labels (1 and 4 positives).** — inconclusive, 2026-09-12 · [journal](journal/2026-09-12-change-entropy-and-centrality-bands.md)

### The keyword grammar of functions

- **A closed set of 26 named edit types covers 99% of function edits in curl (54,890 edits) and libarchive (16,746), about 15 family combinations cover 80%, and a function's next edit resembles its last at 1.70x and 1.96x a size-matched null; outcome-blind, so nothing here is about defects yet.** — exploratory, 2026-11-12 · [journal](journal/2026-11-12-etyp-edit-types.md)
- **The crucible's keyword grammar holds across 2.9M functions in 22 languages and inside 97% of individual repos, well beyond size (r 0.235 vs size placebo −0.006).** — replicated, 2026-11-07 · [journal](journal/2026-11-07-keyword-grammar-at-population-scale.md)
- **Functions that break the grammar are mostly ordinary code (55% vs 64% for controls). They concentrate in test directories, but a "weirdness detector" would not find interesting code.** — mixed, 2026-11-07 · [journal](journal/2026-11-07-grammar-outliers.md)
- **The rules code follows are pairwise. Of 2,791 three-signal combinations, only one is avoided beyond what its pairs explain, and it is not universal; the lattice's missing middle is pair constraints (role conflicts, paired constructs) multiplied out.** — exploratory, 2026-11-07 · [journal](journal/2026-11-07-constrained-middle.md)
- **A keyword grammar exists beyond size in the curated crucible (32 consensus pairs, signs hold in 69% of C-repo pairs), but breaking it does not mark CVE-prone code.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-keyword-grammar-in-the-crucible.md)

### Function fingerprints and the shape lattice

- **Hubs are public, decision-dense entry points and workhorses, not simple utilities; callers of many are straight-line glue; the periphery is private, low-level code; and only extrinsic fixes map onto the network, landing in peripheral files that host hubs.** — mixed, 2026-11-08 · [journal](journal/2026-11-08-what-sits-where-in-call-networks.md)
- **Fix kinds sit in different shape families beyond size, modestly (V 0.07; regression fixes hit simpler, lower-rung functions), but lattice moves add nothing to regression prediction beyond churn; 71% of functions never change shape.** — mixed, 2026-11-07 · [journal](journal/2026-11-07-lattice-fix-families-and-moves.md)
- **Code is built from a few hundred keyword combinations plus a long tail. The commonest are tiny universal "bricks" (one-step, public one-step, public setter) and C dialect shapes (driver functions, static pointer helpers) concentrated in a few OS repos.** — exploratory, 2026-11-07 · [journal](journal/2026-11-07-function-fingerprints-and-archetypes.md)
- **Common shapes grow one keyword family at a time (196 of 199 tree edges), and real code builds about half the mid-size shapes chance would: role conflicts are the holes, paired constructs the attractions.** — exploratory, 2026-11-07 · [journal](journal/2026-11-07-fingerprint-lattice.md)
- **AI coding agents skip the tiny "brick" functions humans write (0% bare one-step vs 5–8%), the Claude models write far more private helpers, Codex fits the human grammar worst, and a program's lattice family mix alone identifies its model 84% of the time (chance 28%).** — exploratory, 2026-11-07 · [journal](journal/2026-11-07-agent-code-on-the-lattice.md)
- **Archetype labels are deterministic and track how much code changes (about 98% kept under small edits), but neither the label nor how atypical a file is for its label finds fixes beyond file size on curl, nDPI or openssl.** — mixed, 2026-11-06 · [journal](journal/2026-11-06-archetypes-stable-not-useful.md)

### What comments say

- **Danger comments at birth predict CVE fixes even in files with no CVE history (1.55×), so they are foresight rather than inherited scars; whether the warnings that CVE fixes leave behind mark lasting fragility is still underpowered.** — mixed, 2026-11-11 · [journal](journal/2026-11-11-scar-fix-scars.md)
- **Fix commits repay TODO/FIXME debt less often than other commits (0.77×, replicated on four unseen repos), but only because fixes are small; at equal size they repay just as often.** — mixed, 2026-11-11 · [journal](journal/2026-11-11-drp-debt-repayment.md)
- **In nine C projects about three quarters of TODO/FIXME/XXX comments are eventually removed, but projects range from 38% to 98% and from months to decades; about half are repaid by their own author, and debt is repaid in clean-ups rather than fixes (fix commits repay it at about half their share of commits).** — exploratory, 2026-11-11 · [journal](journal/2026-11-11-debt-lifecycle.md)
- **After gitgalaxy#8255, the engine's commented-out-code rule is about 93% precise across 5 repos' fix-event files (Wave A's 4% was a curl include-comment artefact), so COM-H3 can use it, run directly on git blobs.** — exploratory, 2026-11-11 · [journal](journal/2026-11-11-dead-code-panel.md)
- **A file's comment profile adds nothing to predicting its next-year fixes or CVE fixes beyond size, churn and history (replicated nulls); in four unseen repos it adds a statistically real but negligible +0.003 AUC.** — mixed, 2026-11-11 · [journal](journal/2026-11-11-cpf-comment-profiles-fixes.md)
- **Commenting is a property of systems and files more than of functions; nine C projects differ several-fold in density and header coverage, files keep their commenting culture for years, and danger wording grew in most projects; outcome-blind, so nothing yet says which culture is riskier.** — exploratory, 2026-11-11 · [journal](journal/2026-11-11-comment-profiles.md)
- **Look 1 (2026-11-11): within the same developers and at matched size, declared-AI commits are blamed for later fixes about as often as their other commits (0.96, CI 0.51–1.49); no verdict until a later look.** — pending, 2026-11-11 · [journal](journal/2026-11-11-arg-ai-regressions.md)
- **Registered prospectively; scored only on commits made after 2026-11-11.** — pending, 2026-11-11 · [journal](journal/2026-11-11-aic-ai-callees.md)
- **Declared-AI commits change function shape no more and no less often than other commits (structure stays put), but within the same authors they add more new callees (11 of 13 people), and Codex-assisted changes move shapes more than Claude-assisted ones.** — exploratory, 2026-11-11 · [journal](journal/2026-11-11-ai-structure.md)
- **Declared-AI commits don't change how much code is commented on average, because tools pull opposite ways (in harfbuzz and OpenSSL, Claude-assisted commits comment about twice as much as Codex-assisted ones, either side of human commits); what AI consistently changes is style, with longer, more sentence-like comments.** — exploratory, 2026-11-11 · [journal](journal/2026-11-11-ai-comments.md)
- **Among danger-commented functions, nothing the engine measures at birth (telemetry, lattice family, call-graph position) beat size + repo + prior-CVE-file at telling which got a CVE fix within 5 years; the discovery signature did not survive held-out functions.** — not-supported, 2026-11-10 · [journal](journal/2026-11-10-dcs-danger-comment-signature.md)
- **Comment prose is 14% of hunk-grain branch hits but does not drive the fix gradient; the new header-comment flag is about 95% precise on curl; but the commented-out-code signal is about 4% precise on curl (mostly "/* for foo() */" include notes), so no study should read it until the rule is fixed.** — exploratory, 2026-11-10 · [journal](journal/2026-11-10-comment-extraction-wave-a.md)
- **A header comment left untouched while the code keeps changing does not mark CVE risk; if anything those functions got fewer CVE fixes (0.67, CI 0.42–1.06, inconclusive).** — not-supported, 2026-11-10 · [journal](journal/2026-11-10-com-h4-comment-drift.md)
- **Comments sit by call-graph role (hubs explained more, the periphery less but with more warnings), but no role changes what a danger comment predicts.** — mixed, 2026-11-10 · [journal](journal/2026-11-10-cmr-comments-by-role.md)
- **Functions born with danger-language comments get CVE fixes 1.45× as often [1.08, 1.89]; the replication on unseen repos was inconclusive (1.13), and CVE fixes themselves add such comments (1.61×).** — mixed, 2026-11-06 · [journal](journal/2026-11-06-danger-comments.md)

### Engine findings (GitGalaxy itself)

- **The engine's own resolver fixes Java hubs on an unseen repo (Jaccard 0.67 vs 0.26 name-based) but not on overload-heavy commons-lang; C passes again; Go and Python remain unevaluated, so the many-labs gate admits only C for now.** — mixed, 2026-11-08 · [journal](journal/2026-11-08-resolved-call-graph-accuracy.md)
- **GitGalaxy's compile-free C call graphs agree with libclang well enough for network science (hubs, ranks and coupling survive), but Java hubs do not survive name-only node identity, and Go and Python were not evaluable in this run.** — mixed, 2026-11-08 · [journal](journal/2026-11-08-call-graph-accuracy.md)
- **Eleven signal names misdescribed their rules (struct_linear counts return/def/void keywords, not linear code), several tokens were counted by two rules, and 36 function columns are always zero. Display names and rule fixes went into the engine.** — engine-finding, 2026-11-07 · [journal](journal/2026-11-07-signal-names-and-rule-fixes.md)

<!-- journal:end -->
