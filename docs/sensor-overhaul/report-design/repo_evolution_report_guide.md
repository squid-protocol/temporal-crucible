# Repo evolution report: design guide

Date: 2026-11-19. Status: proposal for the owner to cut down. Companion mock-up: the published page "Repo Evolution Report" (real DPDK numbers; data in `dpdk_report_data.json`, built by `tools/sensor/report_data.py`).

## 1. Stance

GitGalaxy reads **what code is, where it came from, how it lives and where the outside world touches it** (`docs/TAKEHOMES.md`, point 1). Our research found that structure alone does not predict bugs (point 2: "history predicts; structure adds nothing beyond size and churn"). What did hold up everywhere is **description over time**: how work divides into sweeps, organic change and fixes; how fast fixes arrive; where they land; which functions get repaired again. The report therefore:

- **describes and sizes** a repository's past; it does not forecast its bugs;
- uses **history for meaning and structure for place** (the call graph says *where*, the timeline says *when and how much*);
- labels every number with **how much to trust it**;
- ends each section with a plain **"so what"** line, because a description nobody can act on is trivia.

What it must never do: call a keyword-based fix label "the truth", call an unnamed fix "extrinsic" (we cannot see causes outside the history), or forecast a particular change's fate (size is the only per-change predictor that survived: AUC 0.72 to 0.77).

## 2. Your questions, grouped, with a placement for each

I read all 194 of your messages in this session's transcript. They fall into 16 themes. "Core" = on the first version of the report; "Optional" = a collapsed or secondary section; "Park" = keep in research, not in the report. Evidence: S strong (replicated or rule-based), M moderate, E exploratory.

| # | Theme (your words) | What the report shows | Placement | Data | Ev. |
|---|---|---|---|---|---|
| A | **How repos grow**: "if functions are born fully formed, what changes in them over time", "ranges and bounds for how repos tend to change and grow" | Growth timelines (section 3 below), births/deaths, age layers, "born finished" share | Core | scans | S |
| B | **Sweeps and mechanical vs organic**: "we can auto mark things as sweeps, pick out typical behaviors from anomalous" | Share of edits and commits that are sweeps; largest sweeps with subject and size; what followed them | Core | git (+scan for callers) | S |
| C | **Scope of sweep work / migrations**: "would gitgalaxy be helpful for outlining the scope of sweep work" | Per-sweep scope card: functions, files, share of the old name's callers covered, completion | Optional (promising, prior result: a sweep covers ~90% of callers) | scan | M |
| D | **Fix labels: regression, latent, extrinsic**: "we had a model for latent, regressions and extrinsic" | Fix breakdown with the honest label "no findable cause" instead of "extrinsic" | Core (with caveats) | git + blame | M |
| E | **Ceiling for forecasts ("weather model")**: "what is the ceiling for our forecasts", "what is the limit about what we could predict about fixes" | One "what this repo's history can and cannot tell you" panel: lag regime, how often the look-first list is right, size as the only per-change risk | Core (short) | git + scan | M |
| F | **Sensors, not fancy equations**: "non-redundant sensors that add value", tech debt, reach, library exposure, activity, churn and stability | The report links each section to the sensor behind it; sensors keep their own pages | Optional (cross-link) | scan | S |
| G | **Arguments over a function's life; keywords and args vs branches; outliers** | Signature-change rate per quarter; "functions whose arguments grew" | Optional | scan | E |
| H | **Keywords over time** ("as languages evolve so will how building is done"), shared keyword grammar, function shapes | Keyword mix timeline (e.g. rise of `static`, `const`, `goto`) | Optional | scan | E |
| I | **Repair radius / blast radius**: "a localized reach radius... a blast radius of a change causes a fix downstream" | How close fixes land to the change that caused them, in this repo vs other projects; plain A/B/C/D example | Core | scan + git | S |
| J | **Plain-terms example**: "function A, B, C, who calls who, Day 1 there is a bug where" | A fixed explainer box (the repair-radius page and GIF) | Core (one box, links out) | none | S |
| K | **Fix type vs radius; sweeps and radius; 10 buckets**: "does one like regression best fit", "sweeps don't have this right", "three model types" | Table by cause type (feature, restructure, fix, optimization) with same-function share, radius, lag; mechanism class and shape as a collapsed detail | Core (cause type), Optional (mechanism, shape) | git + scan | M |
| L | **Additions and deletions absorb shock**: "when the local call graph loses something... does it need to absorb that" | Radius around new and removed functions (2.2 to 3.1 vs 1.6 to 1.8 for modified) | Optional | scan | M |
| M | **How much work is what**: "of all the changes in a repo, what percentage are sweeps, repair radius, etc", "account for the unaccounted remainders" | The composition bar (sweeps, fixes, mechanical, organic), compared with other projects | Core | git | S/M |
| N | **A typical quarter**: "give me a typical quarter of a repo. Function birth exceeds. Most deletions are from a full file being deleted. Sweeps are planned work" | "Your typical quarter" card: commits, functions edited, births, deaths and how they split | Core | scan | S |
| O | **Repeat spots**: "are there fixes on the same spots" | Share of fixes in functions fixed before; the most-fixed functions | Core | git | S |
| P | **Recency, regimes, self scan**: "is it a label? could we create a system that does a self regime scan?" | The repo's lag distribution and regime (fast or slow), as a reliability badge for the look-first list | Core (small) | git | M |
| Q | **Look-first and triage lists**: "most likely functions suspect if something breaks", bisects | Per-repo track record of the lists (`gitgalaxy backtest`) | Optional section; product feature of its own | git + scan | M |
| R | **Tests and CI**: "tests should be changing and highlighting change", "ci pipeline info" | Test wiring and reach; fix commits that touch tests; `Cc: stable` as a "shipped bug" marker | Optional | scan + trailers | E/M |
| S | **Languages, ports, translations, DOOM lineages**: "multiple languages", "wicked proving ground" | Not a per-repo section. A "how well do the numbers travel" footnote with the cross-language and cross-lineage replications | Park (methods page) | n/a | S |
| T | **Library and platform coupling**: "where the outside world touches it" | Library exposure timeline: which external libraries the code leans on, and when a library change lands | Optional | scan | S |
| U | **GitHub metadata is poorly labeled** | A "label quality" panel: how many commits have messages, trailers, `Fixes:` habit; tells the reader how much to trust the fix counts | Core (small) | git | S |
| V | **Novelty, product value, repowise comparison** | Not in the report; belongs in the positioning note | Park | n/a | n/a |
| W | **Thermodynamics: "low energy state", "stress of the system"** | At most one optional visual: "stress map" of repeatedly repaired functions. The relaxation story was tested and failed | Park (keep the vocabulary out) | scan + git | E |

If you want only one rule for cutting: keep A, B, D, I, M, N, O, P, U for the first version (nine items, mostly git-only) and let the rest earn a place later.

## 3. Report structure (proposed)

0. **Header and at-a-glance**: repository, span, number of commits and functions, scan coverage, label-quality badge.
1. **Growth** (timelines T1 to T4 below).
2. **Where the work goes**: composition over time (T5) and overall; compared with other projects; "your typical quarter".
3. **Sweeps**: timeline (T6) and the largest sweeps; what each touched; whether repairs followed.
4. **Repairs**: how many fixes, how many have a findable cause, lag histogram (T7), cause-type table, repair radius with the A/B/C/D explainer.
5. **Repeat spots**: concentration curve (T9) and the most-fixed functions.
6. **Which changes get repaired**: by size band (the only per-change signal that held), by cause type.
7. **Reliability panel**: lag regime, how often the look-first list found the cause on this repo, what cannot be said.
8. **Method notes**: definitions, label quality, links to the research log.

Every section has: the one question it answers, the chart, one "so what" sentence, a confidence chip (Strong, Moderate, Exploratory), and a "how this was computed" disclosure.

## 4. Timeline graphs for growth and change

All use one x axis (quarters, matching the quarterly scans) so they stack and read together. **Built** means the mock-up draws it from real DPDK data; **Next** means the data exists but the chart is not drawn; **Needs work** means a new computation.

| ID | Chart | Series (exact definition) | What it shows | Status |
|---|---|---|---|---|
| T1 | **Size over time** | functions in the graph per quarter; dots on quarters with a sweep over 1,000 functions | Overall growth and its pace | Built |
| T2 | **Births and deaths** | stacked bars: new code (name not seen before), moved in (name existed elsewhere); negative: removed, moved out | Growth is new code; a third of apparent deletion is reorganisation | Built |
| T3 | **Age layers** | stacked area of present functions by the year they first appeared (oldest at the bottom) | How much of today's code is old; a "layer cake" of the project's history | Built |
| T4 | **Codebase heat** | share of functions edited this quarter; share untouched for four quarters | How much of the code is alive vs frozen | Built |
| T5 | **Work composition** | stacked area of function edits: organic, sweeps, fixes, mechanical (switch to share of edits) | Where effort goes over time | Built |
| T6 | **Sweep timeline** | one mark per sweep: date, functions touched, subject; filled if later cited as the cause of a fix | Planned mechanical work and its aftermath | Built (as a table; chart next) |
| T7 | **Repair lag** | histogram of cause-to-fix lag; median per year as a line | Fast or slow regime, and whether it shifts | Built (histogram); yearly median next |
| T8 | **Fix rate** | fix edits as a share of edits per quarter; share of fixes with a findable cause | Maturity: is the project spending more of its effort repairing? | Next |
| T9 | **Concentration of repairs** | cumulative share of fix edits against functions ranked by number of fixes (Lorenz curve) | How spread or concentrated repeat repairs are | Next |
| T10 | **Hub growth** | fan-in of the ten most-called functions per quarter | Which functions become load-bearing | Needs work (centrality data exists in scans) |
| T11 | **Contributors** | active authors per quarter, share of commits by the top author | Bus factor over time (the activity sensor already stores this) | Next |
| T12 | **Library exposure** | external libraries called per quarter, stacked by library | Where the outside world touches the code | Next (library sensor data) |
| T13 | **Keyword mix** | share of functions using `static`, `const`, `goto`, `inline`, etc. per quarter | How building style changes | Needs work |
| T14 | **Regime strip** | rolling median of the cause's recency rank, coloured fast or slow | Whether the project's detection speed changes (e.g. fuzzing adopted) | Needs work |
| T15 | **Signature churn** | share of edited functions whose argument count changed | When interfaces move (precedes caller-side repairs) | Next |
| T16 | **Test attachment** | share of fix commits that touch a test file; test reach of the call graph | Whether fixes ship with tests | Next |

For "show growth" specifically: T1 plus T2 plus T3 is the compact answer (how big, how it grows, what the growth is made of). T4 and T5 turn growth into activity.

## 5. Examples to show in the report

- **At a glance (DPDK, real):** 55,000 functions; 46,419 commits; about a fifth of function edits are sweeps (under 1% of commits); fixes are 18%; organic change 58%.
- **A typical quarter (DPDK median of last 16):** 776 commits touch 2,368 functions (4%); 1,103 functions born (544 brand-new files, 437 new functions in existing files, 131 moved) against 346 dead (28 with a whole file, 134 removed from a kept file, 128 moved).
- **A sweep card:** "2021-10-22, `ethdev: add namespace`, 1,105 functions; cited as the cause of later fixes."
- **Repair radius, plain terms:** "After you change function B, the next fix is about 1.5 times as likely to land within two calls of B as in a same-sized function in the same file. Fixes of fixes land in the same function three times in four."
- **Repeat spots:** "Functions fixed twice or more hold 60% of fix edits. One in five fix edits lands in a function fixed five times or more."
- **Reliability panel:** "Median cause is the 1,504th most recent change: slow regime. The look-first list put the cause in its top 20 for 79% of DPDK repairs we tested."
- **Cc: stable:** "In DPDK, fixes tagged `Cc: stable` took a median 371 days; untagged fixes took 20 days: the tag marks bugs that reached a release."

## 6. Honesty rules for the page

1. Every figure carries a chip: **Strong** (rule-based, or replicated), **Moderate** (a label with known error), **Exploratory** (one project, no replication).
2. Say "no findable cause", never "extrinsic".
3. Show label quality first: how many commits have a trailer, how many have a `Fixes:` habit, how many fix-like commits have no cause found. DPDK names causes for 36% of commits; Mesa for 6%. A repository with terse messages will look low on fixes.
4. Fixes hidden in the remainder: the keyword rule misses roughly 8 to 20% of organic commits as fixes (hand check of 40 commits per project). The report says so next to the fix share.
5. Comparisons use a **reference set** and are shown as a band, not a verdict. Today the set has two projects with the full partition (DPDK, Mesa) and about fifteen with partial measurements; do not call anything "typical" until the set is published.
6. Do not forecast. The only forward-looking statement is the size band table and the lag regime, both labelled as history.
7. Never show a number without a way to see how it was computed.

## 7. Reference set and comparisons

Needed for "more local than typical": run the git-only partition and the radius on each project in the pool (curl, libxml2, openssl, libgit2, redis, nDPI, harfbuzz, DPDK, Mesa, FreeBSD, Linux subsystems, Python, Go and Java projects), publish the table, and show each repo as a dot on the band. The measured ranges so far: sweeps 18 to 21% of edits, fixes 9 to 18%, radius within two calls 1.4 to 2.0.

## 8. Build phases and commands

1. **Git only** (minutes, any repository): partition, sweeps, lag, repeat spots, label quality, `Cc: stable` and trailer shares. Command idea: `gitgalaxy history --git-only`.
2. **With the quarterly scans** (nDPI 2 minutes, DPDK 15): births and deaths, age layers, heat, radius, test wiring. Reuses the historical call-graph pipeline (`historical-call-graph-gif`).
3. **With the backtest**: the look-first and triage track record per repository, the lag regime, the reliability panel (`gitgalaxy backtest`, planned PR2).
4. **Output**: one self-contained HTML page plus a JSON file of every series (so the numbers can be re-checked), and an optional PDF-friendly view.

## 9. Decisions for you

1. Is the first version git-only (fast, any repo) or does it require scans (richer, slower)?
2. Is the headline the **composition of work** (sweeps, fixes, organic) or **growth** (size, births, age layers)?
3. Do you want the "look-first reliability" panel in the report, or kept as a separate command?
4. Which of themes F to H and L, R, T (keywords, arguments, additions and deletions, tests, libraries) stay as optional sections and which move to separate pages?
5. How hard should the report push on "extrinsic" and "latent" (my advice: do not label them; show "no findable cause" and the unnamed-fix share)?
6. Does the audience include people who will read it without the research behind it? If so the A/B/C/D explainer moves to the top.
