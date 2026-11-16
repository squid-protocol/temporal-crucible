# TURN: what actually turns over (functions, wiring, hubs, keywords)

**Status: SUPERSEDED (2026-11-16) by `docs/turn_v3_proposal.md`; see `docs/turn_closeout.md`. Original draft text follows; not registered, not reviewed.** Nothing here may be scored until the two independent design
reviews (checklist item 15a) are reconciled in a dated amendment. Written 2026-11-15.

## Question

Our fix and CVE studies leaned on assumptions about how a repository changes: that a function is the same
function from one snapshot to the next, that structure measured at time *t* still describes the code a year later,
and that the code being fixed is the code that was scanned. Call-graph studies leaned on a picture of change in
which new code is wired into the old network. This study measures those assumptions directly instead of
assuming them, using function births and deaths, wiring changes, hubs and keyword usage over time.

## Prior-work check (done before writing)

| already registered | what it covers | how TURN differs |
|---|---|---|
| LAW-2 preferential attachment | new calls go to well-called functions | H4 asks whether *newborn* targets are over-chosen **beyond** the LAW-2 kernel |
| LAW-3 / LAW-4 / HUB-H1..3 | hubs persist, in-degree inequality grows | H5 asks whether a dead hub's *role* is inherited; not whether the hub's rank persists |
| LIFE-H1..3 (NH) | infant mortality, structural freeze, archetype kept | TURN does not test survival curves. A "bathtub" hazard (death risk rising again in old age) was considered and **dropped**: curl, the discovery repo, gave hazard(≥10 y) / hazard(3-6 y) = 0.96 |
| SIG, CPL (evo) | keyword mix fingerprints a project, drifts in spurts | H6, H7 ask *how* keyword counts change (by birth or by in-place rewriting), not whether the mix is stable |
| FREC, CHG, FWD, HR | function-grain recidivism, change features, forward prediction | H1 and H2 audit the identity and horizon assumptions those rely on |

Literature check owed before registration (programme rule): software-evolution and clone-genealogy work on code
movement and "refactoring-aware" identity (origin analysis), Lehman's laws on growth, and cohort effects in
software ageing. Not yet done; listed so it is not skipped.

## Discovery set and what it may do (checklist 11)

curl, from the existing 2026-09-13 scan database (an older engine build; archetypes were not populated, and the
2026-11-05 rescan database was not available), last snapshot of each year 2004-2026, history disabled, was used on
2026-11-15 for exploratory tables. Those numbers set the thresholds below and nothing else. Two discovery results changed the registration: the
bathtub hazard hypothesis was dropped (it failed on curl), and H7's unit was moved from one year to five (at one
year the effect is 56%, near chance). **curl, nDPI, openssl, harfbuzz and libarchive are
excluded from every confirmatory test** (the programme rule for the heavily studied five).

## Panel and units

* **Panel: the LAWS seated panel** (`docs/laws_seating/`, seed 2982), the repos that pass the registered clone-time
  checks. No selection is made here. 20 seats exist (2 per language); the confirmatory seat count is whatever LAWS
  has seated when scoring starts, frozen by a dated amendment before any outcome is read.
* **Units:** unit files only (`laws_units`): the repo's language, not test, vendored, doc, example or generated
  (checklist 1). A function is a unit-file function.
* **Snapshots:** yearly, the commit nearest 1 January (UTC) from the repo's 1st-percentile commit time (item 7),
  scanned by the LAWS harvester with git history disabled, one engine commit for the whole study.
* **Identity:** (file path, name, nth same name in file). A *birth* at *t* is present at *t* and absent at *t-1*;
  a *death* the reverse; a *move* is a death whose name reappears as a birth at the same *t* in another file.
  Names are an upper bound on moves (common names collide); H1 reports that.

## Hypotheses

Each is tested **per repo** with an interval (item 12); a pooled mean is shown only with the count of repos on each
side. "Supported" needs the interval wholly on the predicted side of the stated bound; otherwise "not detected" or
"contradicted" (item 9).

### Part A: audit the assumptions

| id | claim | estimator | bound | discovery (curl, exploratory) |
|---|---|---|---|---|
| **TURN-H1a** | Moves are a material share of "deaths", so name-and-file identity mislabels code in a way function-grain studies must handle | share of deaths that are moves, over all snapshot pairs; bootstrap over pairs | lower bound **> 0.15** | 26% (1,173 of 4,479) |
| **TURN-H1b** | Moves are bursty: reorganisations, not a steady trickle | share of all moves in the top 10% of snapshot pairs | **≥ 0.40**, lower CI > 0.25 | 47% (2013 and 2026 hold 552 of 1,173) |
| **TURN-H2** | Structure goes stale fastest exactly where fixes happen | within file-size deciles: mean 1-year Jaccard of a file's function set, hot files (top 20% by commits touching them in the prior year) minus other files | difference **< 0**, upper CI < 0 | not measured; direction from "hot files are where everything happens" (HYPOTHESES reflection item 4) |

### Part B: where new code appears and how it is wired

| id | claim | estimator | bound | discovery |
|---|---|---|---|---|
| **TURN-H3** | Growth is mostly new files, not new functions in old files | share of births in files absent at *t-1* (renamed files excluded by a function-overlap rule); repos with ≥ 8 years | lower bound **> 0.50** | 53% (borderline: a real test) |
| **TURN-H4** | Newborn functions are called by other newborn functions more than preferential attachment predicts, across files | per snapshot pair: log(observed share of newborn targets among calls from newborn functions to *other files* / share expected from the LAW-2 kernel fitted on the same repo); median over pairs | **> 0** | median ratio 1.37 against a cruder null (population share), > 1 in 11 of 17 years: genuinely uncertain |
| **TURN-H5** | A dead hub's role is inherited: its surviving callers are re-pointed into newborn code in the same directory | for hubs (≥ 5 surviving callers) that die: share of those callers calling ≥ 1 newborn in the hub's directory at *t*; minus the same share for in-degree-matched surviving hubs | **> 0** | none (pure prediction) |

### Part C: keyword usage over time

Engine keyword families, counted per function. For a family *f* and a snapshot pair, change in the family's total
splits into births, deaths and **drift** (survivors' own count change). Retrofit share
`R_f = |drift| / (births + deaths + |drift|)`.

| id | claim | estimator | bound | discovery |
|---|---|---|---|---|
| **TURN-H6** | Some families change by in-place rewriting (project-wide conventions), others only by turnover | mean `R_f` over the predicted-high families {alloc, cleanup, print, safety_neg, io} **minus** over the predicted-low {branch, pointers, args, macros, def_safety}; **C and C++ seats only** (the vocabulary was calibrated there), other languages reported descriptively | **> 0** | 0.15-0.23 vs 0.00-0.03 |
| **TURN-H7** | Surviving functions drift toward the keyword density of the newest births, slowly | per (family, **5-year window**) with \|born density − survivor density\| ≥ 0.5 per kLOC: share where survivors moved the same direction; sliding windows, bootstrap over start years (windows overlap, so the cell count overstates independence) | **> 0.70** | 83% (203 cells). Window length matters: 56% at 1 year, 65% at 2, 74% at 3, 83% at 5, 82% at 8. A yearly unit would be near chance, so the unit is 5 years |

## Checklist answers (items 1-18)

1. **Rank only what can be positive:** unit files only; no ranking is done, but counts use unit-file functions.
2. **Same label depth:** no labels used, except H2's commit counts, which need git history for every repo or the repo is excluded from H2.
3. **Merges:** H2 uses first-parent commits touching a file; merge share ≥ 0.30 flagged and a merge-removed sensitivity declared.
4. **Scan complete:** unit files in scan ÷ unit files in `git ls-tree` ≥ 0.90 at every snapshot used, else the repo is out.
5. **Instrument per language:** share of unit files with any inbound call reported per repo; languages the engine
   has not been validated on are declared, with a sensitivity removing them.
6. **One language rule:** the LAWS rule, from unit files.
7. **Dating:** 1st-percentile commit time; realised window recorded; repos shorter than their hypothesis needs are flagged.
8. **Tree-wide commits:** a snapshot pair where > 50% of unit files change is a reformat or move event; reported,
   and every hypothesis is also run with such pairs removed.
9. **Direction:** stated for every hypothesis above.
10. **Power:** to be stated before scoring from the per-pair spread in the first seated repos (not curl). OPEN.
11. **Fresh repos only:** curl excluded (above); the heavily studied five excluded; a fresh-only run is the only run.
12. **Per repo with intervals:** yes; pooled means only beside side-counts.
13. **Size:** H2 compares within size deciles; H3, H4 are within-repo ratios; H6, H7 are density-based.
14. **Sensitivities (reported, not gating):** move-aware identity (name + dir); first and last pair removed; repos
    with history < 8 years; reformat-event pairs removed. Verdict gates on the primary run only.
15. **Two independent reviews:** **owed**: design review by two reviewers on different models before any tool is
    written; code review before the scorer runs. Reviewers compute no predictor-outcome association.
16. **Amend in the open:** dated amendments stating how many seats were prepared and scored at the time.
17. **Exclusions listed with reasons:** unprepared, scan incomplete, engine does not resolve calls, no history for
    H2, under the floor, failed. One reason each.
18. **Corrections are opt-in switches** on shared tools.

## Not claimed

No link to CVEs or fixes is tested here. H1 and H2 say *how much* the fix studies' assumptions can be trusted; they
do not re-score those studies. H4 and H5 describe wiring, not quality.

## Open before registration

1. Literature check (above).
2. Power statement from the first seated repos (item 10).
3. Whether H5 needs a harvester that records caller sets per snapshot (the LAWS harvester stores edge lists; to confirm).
4. The two design reviews and their reconciling amendment.
