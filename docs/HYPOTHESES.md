# The hypothesis ledger

## The plain-language summary (read this first)

**What we did:** validated GitGalaxy's measurements against real defect ground truth,
pre-registering every prediction before looking: curl's 25-year CVE history (fix +
introducing commits), a second repository (nDPI, OSS-Fuzz-found CVEs), and 1,107 of curl's
own bug-fix / regression commits — ~3,550 repository snapshots scanned, every verdict
published either way.

**What we learned, in plain terms (updated 2026-09-13, after the full program):**

1. **Two predictors survive honest evaluation; both are history, neither is structure.**
   - **Recidivism** — the file that had the last fix gets the next one — beats every static
     ranking, decisively, on both repositories (p<1e-4). The strongest and most replicated
     result of the program.
   - **Change entropy (Hassan HCM, `HCM1_LD_30`)** — was this file changed during periods
     when edits were scattered chaotically across the codebase? Selected on CVE labels,
     then **validated frozen on fresh bug labels**: AUC 0.868 vs a line count's 0.830
     (lift +0.038, bound +0.021). The only *feature* to beat a line count out-of-selection.
2. **Everything structural reduces to file size.** Keyword counts, danger vocabulary,
   complexity, per-file risk totals — pooled, density-normalized, length-matched, or
   banded — none beats a line count (nulls equivalence-confirmed, two repos). The same
   size-confound wall was independently reported by repowise-bench on ordinary bug labels;
   we reproduced it on CVE labels. Nobody's per-file structural score clears it.
3. **The fix "grammar" is real but narrow.** curl's security fixes have a recognizable
   shape (branch/pointer adds without new allocations) — it survives fix-size controls but
   **does not travel**: nDPI's fuzzer-found one-line fixes carry no signature. It is a
   property of *human-reported* CVE fixes in curl, not a law.
4. **Centrality is not the small-file answer.** With proper power (28/42 positives),
   PageRank in ≤22-line files is *inverted* (AUC 0.26), and the once-beautiful monotone
   size story failed in 5,000/5,000 bootstrap resamples. The surviving candidate is an
   **inverted U** — centrality lifts only in mid-size files (49–108 LOC: +0.14, robust) —
   registered for repo #3, not yet claimed.
5. **The guards did the finding.** Pre-registration killed post-hoc stories (the monotone
   shape, the best-of-36 HCM selection); the ≥20-positive power rule stopped an AUC-0.999
   "result" built on one positive; equivalence tests turned "not significant" into
   "confirmed near-zero"; and the instrument audit caught a real engine determinism bug
   (gitgalaxy#2988). More predictions died than lived — that is the record working.

**What this points at:** ship history (recidivism + change entropy) as the predictive
layer; let structure do what it actually does — describe, explain, and localize, across
59 languages. The open questions now live in repo #3 (openssl, fixed-side): does the
grammar return on human-reported fixes elsewhere, is mid-band centrality real, does HCM
replicate, and the CWE-matched specificity battery that curl and nDPI could not power.


This is the temporal crucible's register of record — every confirmatory claim this program
makes lives here, with its registration date, its registered direction and threshold, and
its verdict **whatever that verdict was**. It is the sibling of keyword-rosetta's deviation
ledger: there, no manifest number exists without a validated entry; here, **no finding
exists without a pre-registration**.

## The protocol (the rule this repo runs on)

1. **Hypothesis first.** A confirmatory claim is registered — on gitgalaxy#2982 or here —
   with its direction, its test, and its α **before** the analysis that could confirm it
   runs. The registration text is quoted verbatim in the report that evaluates it.
2. **Verdicts are published either way.** A dead hypothesis stays in this ledger forever
   with its autopsy. Three of our first five died; that is the record working.
3. **Exploratory is labeled exploratory.** Descriptive tables (prevalence shares, gap
   rankings) claim no p-values and are marked in-place. An exploratory observation may
   *become* a hypothesis — registered for **data it has not seen** (the next repo, the next
   label class), never re-tested on the data that suggested it.
4. **Every test carries its guards**: size-matched controls, length-matched pairs where
   grain is the function, temporal ablation (churn/stability frozen so events cannot
   predict themselves), rename tracking, and multiple-comparison correction on any table
   wider than one registered claim.

## Scope of validation to date

**curl** (C, ~39.7k commits, 25 years): 186 CVE-fix + 137 CVE-introducing commits (OSV GIT
ranges, 0 unresolvable) + 185 size-matched controls + 147 wave-1 (reverts/follow-ups) +
1,107 bug-label events (Fixes#/Bug:/regression, seeded sample). **nDPI** (C/C++): 121
fix + 73 introducing (OSS-Fuzz-bisected) + 111 controls. **~3,550 snapshots scanned in
total** across both repos; ~3.4M per-function measurements on curl alone.
**Repo #2 (nDPI) has now run** (see "Repo #2 (nDPI) replication — RESULTS" below): of curl's
positives, **only recidivism (RW-H2) replicated**; every structural signature (H3
`safety_score`, the fix-shaped grammar, R2-H1 danger density) **failed to replicate**, while
every structural null held. So the cross-repo standing is: recidivism is real; structural
exposure is a size proxy whose fix-signatures are repo/discovery-specific. Still two C-family
repos — no cross-*language* or cross-ecosystem claim yet.

## Register

> **Looking for "what have we tried to correlate"?** That view — the predictor × outcome
> matrix and the full hypothesis → `tc#` → doc crosswalk (including the N-/S-/HV-/C-/B-/X-
> families that live in the prose sections below) — is [`EXPERIMENTS.md`](EXPERIMENTS.md).
> This table below is the confirmatory record; `EXPERIMENTS.md` is the index over it. If the
> two disagree, this table wins.

| id | hypothesis (registered direction) | registered | verdict | evidence | tc# |
|---|---|---|---|---|---|
| H1 | Security fixes reduce aggregate structural exposure vs matched controls | 2026-09-12, pre-batch | **✗ not supported (final)** — p=0.77, n=182/168 | exposure_history_report.md | — |
| H2 | Introducing commits raise it | same | **✗ not supported** — direction right (+0.007 vs +0.000), p=0.023 vs α=0.01 | exposure_history_report.md | — |
| H3 | Per-vector table names the carriers | same | **✓ `safety_score` p=0.0072** — the one vector moving its assumed direction; `tech_debt` p=0.0011 diagnosed as a density-denominator artifact | exposure_history_report.md, commit anatomy | — |
| D-H1 | Vulnerable functions are under-guarded relative to danger (guard rate < length-matched siblings) | 2026-09-12, pre-analysis | **✗ not supported** — metric degenerate (median 0.000 both sides: C carries no `def_safety` vocabulary at function grain) | signal_anatomy.md Phase D | — |
| D-H2 | The fix closes the deficit | same | **✗ not supported** — same degeneracy | signal_anatomy.md Phase D | — |
| M-H1..M-H3 | Multi-label signatures (classes distinguishable; security-fix vs `Fixes #` differ; follow-up-corrected fixes differ) | 2026-09-12, pre-batch | **pending** — batch not yet run | gitgalaxy#2982 Phase M | tc#1 |
| D-H1′ | Branch-per-danger guard deficit (the C idiom) — implicated < length-matched siblings; the fix raises it | 2026-09-12, for **repo #2 only** (post-hoc on curl) | **✗ not supported** — nDPI: implicated 0.634 vs sibling 0.600 (*wrong* direction, p=0.75); fix doesn't raise it (D-H2′ p=0.999). Non-degenerate → a real no. | ndpi_stage2.md | — |
| RW-H1 | Structural exposure beats LOC at ordering a 20%-LOC review budget (effort-aware, from repowise's Popt result) | 2026-09-12, pre-analysis | **✗ not supported** — 52W/48L/82T, p=0.38; exposure ≈ LOC even at ordering, on CVE labels | rw_hypotheses.md | — |
| RW-H2 | Prior CVE-fix count beats any static ranking (recall@budget + AUC) | 2026-09-12, pre-analysis | **✓ SUPPORTED decisively** — median recall .444 vs .000; 77W/27L vs exposure, 71W/10L vs LOC, both p<1e-4. **Recidivism is the rung-7 baseline to beat.** | rw_hypotheses.md | tc#28 |
| R2-H1 | Danger density marks the vulnerable function: at equal length, more pointer/danger/alloc/cast constructs than siblings | 2026-09-12, for **repo #2** (curl read p=0.032, below α — suggestive only) | **✗ not supported** — nDPI: implicated 19.0 vs sibling 20.0, p=0.47. The curl suggestion did not replicate. | ndpi_signal_anatomy.md | — |
| W1-H1 | Reverts are net-removal: grammar-signal deltas predominantly negative (where other classes are net-positive); median event net-LOC < 0 | 2026-09-12, pre-batch | **✓ SUPPORTED** — net-LOC median −1.0 (60 events <0 / 24 >0, sign p=5.4e-05) vs +2.0..+6.5 for every other class; net-grammar median −1.0 (57/23, p=9.2e-05); revert < control 1-sided MW p<1e-4. A clean instrument sanity check. | wave1_hypotheses.md | tc#1 |
| W1-H2 | Fixes that later needed a follow-up carry the fix-shaped composite at a LOWER rate than fixes that stuck (one-sided) | 2026-09-12, pre-batch | **✗ not supported** — direction wrong: needs-follow-up 0.71 (10/14) vs stuck 0.65 (110/168), Fisher p=0.77. Incomplete fixes are not structurally thinner. | wave1_hypotheses.md | tc#1 |
| W1-H3 | CVE-fix follow-ups carry the fix grammar (branch/pointer adds) at a rate closer to fixes than to controls | 2026-09-12, pre-batch | **✗ not supported** — follow-ups are THIN: loose (branch/ptr+) rate 0.20 (3/15), below controls (0.45) and fixes (0.71). The follow-ups are administrative (build/cmake/test), not added security logic; n=15 small. | wave1_hypotheses.md | tc#1 |
| ARCH-S1..S5, ARCH-U1..U4 | Archetype stability (S1 determinism gate ≥ 0.999 on unchanged code; S2 ≥ 0.90 retention under ≤ 5% edits) and usefulness (forward-learned per-line fix density of the file-cluster / composition label beats both LOC orders at recall@20; label-adjusted size beats size by AUC at file and function grain) | 2026-11-06, before any archetype × outcome statistic (all three repos unseen) | **stability ✓ (S1 PASS 3/3, S2 trackable 3/3); usefulness ✗ (U1–U4 not supported on every repo; U3 openssl + U4 curl/nDPI replicated null)** — archetypes describe code stably but find no fixes beyond size | archetype_hypotheses.md | — |
| ARCH-Z1..Z4 | Archetype atypicality (composition fit z / file-cluster centroid distance) finds fixed files: recall@20 beats both LOC orders (Z1, Z2); size-stratified AUC > 0.5 (Z3, Z4) | 2026-11-06, before any z × outcome statistic (all three repos unseen) | **✗ not supported on any repo** — direction inconsistent (curl/openssl atypical ≈ slightly riskier; nDPI *typical* riskier, stratified AUC 0.35) | archetype_hypotheses.md | — |
| NM-F, NM-G | Screen of the untested engine metrics (fam_* families, guard balance, alloc/cleanup, wrappers, mitigation tallies; function fan-in/out, pagerank, public, documented): size-stratified AUC ≠ 0.5, same sign on every repo, Bonferroni within family | 2026-11-06, before any NM × outcome statistic | **0 file SIGNALs; 3 LEADs + function fan_out SIGNAL, all but one shown (exploratory) to be leftover size from coarse strata. Survivor: `amplified_cascading_flux` (state mutation inside branches) beats size on nDPI + openssl, not curl → AMP-H1 owed on an unseen repo** | newmetrics_hypotheses.md | — |
| XC-H1..H6 | Fix classes have distinct causes: regressions ← change entropy (H1) and specifically (H2); extrinsic fixes ← external-include surface (H3, H4); history is class-specific (H5, H6). EA recall@20 lift over the stronger LOC baseline | 2026-11-06, before any harvest or statistic; label precision gate ≥ 0.70 (extrinsic rule amended once, re-audited 0.90–1.00) | **MIXED** — H1/H2 (entropy → regressions, specifically) openssl only; H3/H4 ✗ everywhere; H5 reversed (regressions follow general fix activity, never recur in place); H6 (extrinsic recur on their own history) curl + openssl. Fix classes have distinct *histories*; no snapshot metric sees the class | xc_hypotheses.md | — |
| ENV-H1..H3 | Platform/compiler/arch conditional density finds extrinsic fixes beyond size (H1) and more than regressions (H2) / other fixes (H3), on unseen harfbuzz + libarchive | 2026-11-06, before either repo is cloned | **PARTLY REPLICATED** — H1 (+0.173 / +0.123) and H3 SUPPORTED on both unseen repos; H2 SUPPORTED on harfbuzz, withheld on libarchive (regression labels failed the audit). First static measure to beat size on unseen data | env_hypotheses.md | — |
| LV-H1..H4 | Latent defects are found at the search frontier: files whose OSS-Fuzz line coverage just grew carry the next latent fixes beyond size (H1), specifically (H2); reach beats unreach (H3); conditional H4 = fuzz-covered but CI-uncovered code (nDPI) | 2026-11-06, before any coverage × outcome join | **H1–H3 not supported on nDPI** (all in the predicted direction; H2 +0.143 and H3 +0.088 exclude 0 at 90% but not at α). nDPI fuzz coverage is ~96% saturated, so the test is weak there; replication owed on curl/openssl. H4 (CI coverage) feasible, not run | lv_hypotheses.md | — |
| LV-R (curl) | LV-H1..H3 replicated verbatim on curl's OSS-Fuzz coverage history and XC labels (human-reported CVEs: weaker frontier effect expected) | 2026-11-06, before any curl coverage download | **✗ not supported** — frontier marks curl CVE files worse than size (H1 −0.195, CI [−0.300, −0.095]); with nDPI directional only, "discovery is exploration" is not supported across repos. Consistent with a searcher-specific reading (curl CVEs are human-reported); a reporter-split test is owed | lv_hypotheses.md | — |
| INP-H1..H6 | Input-facing code marks where CVEs land: input-API calls (IN) and raw byte-buffer + length handling (BUF), per line, beat size (H1/H2), are CVE-specific vs extrinsic/other fixes (H3/H4), and find CVEs in files with no CVE history (H5/H6); curl, nDPI, openssl, harfbuzz | 2026-11-06, before any input-measure statistic | **✗ not shown** — IN and BUF lose to size on curl, openssl, harfbuzz (pooled −0.092 / −0.054); positive on nDPI only (fuzzer-found parser CVEs). BUF leans CVE-specific (+0.032, n.s.) | inp_hypotheses.md | — |
| CEN-H1 / H2 | Mid-band (49–108 LOC) centrality finds bug-fix files beyond size: PageRank (H1), popularity (H2); the B-H context cells, run at last on unseen openssl, harfbuzz, libarchive | 2026-11-06, before any centrality statistic on these repos | **✗ not supported** — PageRank −0.044 / −0.051 / +0.035 (none passes); popularity passes openssl only (+0.061) and fails harfbuzz (−0.072) and libarchive (0.000). Centrality closed as a predictive lead | cen_hypotheses.md | — |
| DYN-H1 / H2 | Per-file dynamism (function-like `#define`, `goto`): beats LOC within bands (H1); rate ratio > 1 at equal size + evidence (H2). Registered 2026-10-23, scored 2026-11-06 | 2026-10-23 (tc#41) | **H1 ✗; H2 ✓ SUPPORTED** — 2.03 nDPI / 2.33 openssl; robust to 50–100 LOC strata (1.8–2.2). First snapshot property with a replicated association with security fixes beyond size | cen_hypotheses.md | tc#41 |
| KF-H1..H4 | Construct split of DYN: `goto` alone (H1) and function-like macros alone (H2) raise the security-fix rate at equal size; keyword → specific fault: `goto` ↔ lifetime faults (H3), macros ↔ bounds faults (H4); nDPI + openssl pooled | 2026-11-06, before any construct-split or fault-type statistic | **H1 ✓ (goto 1.59), H2 ✓ (macro 1.34), H3 ✓ goto ↔ lifetime faults (ratio 7.1, lo 2.77; 26 lifetime events; 50-bin ratio ≈ 5.3), H4 ✗.** First keyword → specific-fault result. curl (context) does not show it; replication owed | kf_hypotheses.md | — |
| LIFE-H1..H3, HUB-H1..H3 | Natural history: infant mortality of functions (LIFE-H1), structural freeze with age (H2), archetypes persist through edits (H3); include-graph hubs stable (HUB-H1), rich get richer (H2), hubs a frozen core at equal size (H3); 5 repos quarterly | 2026-11-06, before any lifecycle or hub statistic | **5 of 6 SUPPORTED**: infant mortality (young functions die 2.9× faster), structural freeze (0.46×), archetypes persist through edits (88%), hubs stable (92–100% after 1 y), rich-get-richer but sub-linear (slope 0.2–0.5). **HUB-H3 reversed**: hubs change *more* (RR 1.12) | nh_hypotheses.md | — |
| GG-H1..H3 | GitGalaxy's own history, Gemini era (< 2026-07-06) vs Claude era (≥ 2026-07-22, switch fixed from commit trailers): Claude-born functions structurally distinguishable beyond within-era drift (H1); a drastic change point at the switch (H2); Gemini code rewritten faster after the switch (H3) | 2026-11-06, before any scan | **H1 ✓ eras structurally distinguishable** (AUC 0.877 vs within-era placebos 0.73/0.67; Claude: small, typed, branch-dense helpers; Gemini: large many-arg workhorses with prints). **H2 ✗**: the biggest break is the Oct scale-up (2026-10-12), not the switch. **H3 ✗** reversed: Gemini code died less after the switch. Era ≈ model + tooling + workflow, not model alone | gg_hypotheses.md | — |
| FLT-H1..H3 | GitGalaxy repo, Claude era from 2026-09-27: functions written by the autonomous fleet (churn/, fleet/ branches) vs interactive Claude sessions (same weeks) are distinguishable beyond within-group drift (H1), even inside gitgalaxy/tools/ (H2); fleet code concentrates in tools/ (H3) | 2026-11-06, before any attribution statistic | **✗ all three**: fleet vs interactive AUC 0.640 is below the within-group placebos (~0.70), also inside tools/; the fleet wrote *less* in tools/ (54% vs 71%). The fleet writes Claude code: the signature tracks the model and regime, not human-in-the-loop. Corrects GG's exploratory "fleet → tools" note | flt_hypotheses.md | — |
| AGE-H1..H4 | Age signature of fix classes (git blame of the lines each fix changes): regressions change younger code than generic fixes (H1), CVE fixes older (H2), CVEs older than regressions (H3), extrinsic no age signature (H4). Regression labels restricted to the age-independent regression-word rule | 2026-11-06, before any blame statistic | **✗ no pooled age signature** (H1–H4 not supported). Exploratory: CVE age splits by searcher. Human-found CVEs (curl, openssl) change code ×1.6–2.8 older than generic fixes; fuzzer-found (nDPI, harfbuzz) ×0.3–0.8 younger. Registered split owed | age_hypotheses.md | — |
| SRCH-H1..H3 | Searcher split: fuzzer-found CVE fixes change younger code than ordinary commits on unseen libxml2, file, libexif (H1); within openssl, fuzz-credited CVEs younger than human-credited (H2); CVE/ordinary age ratio lower in fuzzer-regime repos than human-regime (H3) | 2026-11-06, before any statistic on the new splits | **✗ refuted**: fuzzer-found CVE fixes on unseen libxml2 and file change code 2–3× OLDER than ordinary commits (H1 +0.42), like human-found ones; H2 not evaluable (7 measurable); H3 ✗. CVE fixes mostly change older-than-typical code whoever finds them (×2.1–3.7), except nDPI and harfbuzz | srch_hypotheses.md | — |
| SFS-H1..H4 | Structural fingerprint scanner (sfs) on yearly snapshots: fingerprints are stable project identities (H1); name-free twin retention agrees with name-based survival (H2); structural turnover goes with regression share (H3) and not with CVE share (H4) | 2026-11-06, before any sfs statistic on these repos | **H1 ✓ sfs fingerprints identify a project across eras 99.0%**; H2 ✗ (ρ 0.49): names persist 95–100%/y but only 59–72% of functions keep a structural twin; H3/H4 ✗: yearly turnover does not track regression share | sfs_hypotheses.md | — |
| CHG-H1..H5 | 5 C/C++ repos, function × quarter: a fingerprint change (archetype/complexity) is followed by more regression-word fixes in 180 d vs untouched (H1) and vs same-shape edits (H2), specifically regressions (H3); young (<1 y) vs old (≥3 y) functions get more regression fixes (H4) and a higher regression share of their fixes (H5) | 2026-11-06, before any fix-to-function statistic (gate amended A1 after run 1 failed, before claims) | **H1 ✓ RR 2.88, H2 ✓ 1.42 (lo 1.02), H3 ✓ 1.47**: shape change → regression fixes, beyond editing, regression-specific. **H4 ✗ H5 ✗**: young code is busy, not deficient (share 1.7% vs 2.4% old; harfbuzz exception) | chg_hypotheses.md | — |
| CHG2-H1..H2 | 5 C/C++ repos: churn + engine change features (shape/archetype change, Δcomplexity, 32 signal deltas, fan-in) beat a churn-only model at effort-aware recall@20% LOC of regression-word fixes, forward in time (train < 2020) (H1) and leave-one-repo-out (H2) | 2026-11-06, before any CHG-2 fit | **✗ both**: churn alone catches 41% (forward) / 37% (LORO) of regressions in 20% of LOC; adding engine change features gives −2.6 / −2.9 points. Regression ranking = churn; the engine's value is coupling, identity, provenance, natural history | chg2_hypotheses.md | — |
| KW-H1..H3 | Keyword grammar on the language-crucible (pinned engine, functions ≥3 loc, languages ≥500 functions): size-stratified signal co-occurrence (MH log OR) is shared across languages beyond a label-permutation null with mean r ≥ 0.30 (H1), also across signal families only (H2); signals form stable k=6 modules across languages (ARI vs null, H3) | 2026-11-06, before any co-occurrence statistic | **✗ H1/H2**: cross-language r 0.17 beats the shuffle null but not the pre-registered size-only placebo (0.24): apparent universal grammar is mostly function size. **✓ H3 weak** (ARI 0.083). Exploratory beyond-size residual still shared (r 0.12): guards+branches, cleanup+guards; API surface avoids branching; mutation avoids early exits. Confirm on a population scan. **KW-R** (function-level stoichiometric log-ratios): ✗ H1 (placebo r 0.221, ratios don't remove size on sparse function counts), ✗ H2 (+0.026 beyond placebo). Grammar must be measured placebo-corrected and at file level | kw_hypotheses.md | — |
| GR-H1..H4 | Crucible-learned keyword grammar (consensus pairs, continuous-size O/E) holds in curl/OpenSSL/harfbuzz/nDPI/libarchive (sign agreement, H1); grammar-atypical functions (bottom quintile of fit within repo × loc × signal-count strata) attract latent (H2) and regression (H3) fixes in 180 d; edits that drop grammar fit precede regressions (H4) | 2026-11-06, before any GR statistic | **✓ H1**: crucible grammar signs hold in 69% of pairs in the 5 C repos (p 0.0006). **✗ H2 reversed**: atypical functions get *fewer* CVE fixes (RR 0.66; CVEs land in grammatical defensive-control code). ✗ H3 (0.95). H4 not evaluable (threshold too large vs weights). Edits don't drift toward the grammar | gr_hypotheses.md | — |
| FORT-H1..H3 | Fix × function, pre vs post body (tree-sitter guard clauses: else-less if → return/goto/break/continue), 5 C repos: CVE fixes add guards more than other fixes (H1); among guard-adding fixes, CVE-fixed functions were already guarded more often (incompleteness) or less (exposure) (H2); regression fixes add guards less than other fixes (H3) | 2026-11-06, before any FORT statistic | **✓ H1**: CVE fixes add guard clauses 1.88× ordinary fixes (20% vs 11%) and remove them more (8% vs 5%): defences get restructured. **H2 inconclusive** (1.00 [0.91, 1.10]: ~70% of touched functions already guarded, any class). **✗ H3 reversed**: regression fixes add guards 1.56× (a change broke or missed a case) | fort_hypotheses.md | — |
| FORTV-H1, FIXK-H1..H3 | FORT-V: new guards in already-guarded functions extend an existing guarded variable more for CVE fixes than ordinary fixes (incompleteness) or less (exposure). FIXK: engine C rules (54) on each fix's added vs removed lines, per class vs other-fix (CMH by repo × patch size, BH q<0.01, RR ≥1.25/≤0.8): CVE signature beyond known defensive rules (H1), regression signature exists (H2), they differ (H3) | 2026-11-06, before either ran | **FORTV inconclusive** (tight 1.04: ~80–84% of new guards extend an already-guarded variable, every class). **FIXK ✓✓✓**: CVE fixes = branches + exits + size_t/-> + new #define limits; regression fixes = new functions (2×), globals (2.5×), static/const/state/alloc (restructuring); signatures differ (Jaccard 0.17); extrinsic = macros/asm/imports | fort_hypotheses.md | — |
| SIL-H1..H2 | Silent patches: an L2 model on FIXK change signatures (51 engine C rules gain/loss + size), leave-one-repo-out over curl/OpenSSL/nDPI/harfbuzz, ranks advisory-linked CVE fixes whose subjects have no security words above ordinary fixes better than patch size (AUC, H1) and concentrates them in the top 10% (enrichment lo > 1.5, H2); candidates private | 2026-11-06, before any SILENT fit | **H1 ✓ weak**: held-out AUC 0.569 vs size 0.507 (defensive rules alone 0.572). **H2 ✗** (top-10% enrichment 1.51×, lo 1.09). Change signatures are population tendencies, not a silent-patch detector; next: combine where (recidivism) + how | silent_hypotheses.md | — |
| WH-H1..H3 | Where + how: adding pre-commit location history (prior CVE fixes and prior fixes in the touched files, guard density of touched functions) to SILENT's change signature improves held-out silent-CVE AUC (H1), the signature adds beyond location (H2), and top-10% enrichment lo > 1.5 (H3) | 2026-11-06, before any WH fit | **✓ H1** (+0.111), **✗ H2** (signature lowers AUC −0.039), **✓ H3** (top-10% 2.93×, lo 2.37). Location alone (prior CVE fixes + fix activity + guard density) gives held-out AUC 0.720 vs change signature 0.569: recidivism finds silent security fixes, structure of the change doesn't | silent_hypotheses.md | — |
| INT-H1..H2 | Were the authors right? Functions written defensively at birth (top vs bottom third of safety+negative-safety+bailout density, within repo × loc × file-prior-CVE strata) get more CVE fixes within 2 years (H1), more than they get ordinary fixes (H2); curl/OpenSSL/nDPI/harfbuzz | 2026-11-06, before any INT statistic | **inconclusive** (H1 RR 0.97 [0.46, 1.72]; H2 0.99): only 106 CVE hits within 2 y of birth. CVEs surface years later (SRCH), so a whole-life survival design is needed; repos split (OpenSSL 1.45, harfbuzz 2.86 vs nDPI 0.52, curl 0.88) | int_hypotheses.md | — |
| INTS-H1..H2 | Whole-life INT: first-CVE-fix rate per function-year from birth to first event, death or label end, high vs low defence-at-birth third (repo × loc × file-prior-CVE strata, MH rate ratio): higher (authors right, H1); CVE-specific vs other fixes (H2) | 2026-11-06, before INT-S ran | **✗ both, a fairly tight null**: whole-life first-CVE rate ratio 0.96 [0.73, 1.28] (562 events, 126k function-years); CVE-specific 0.90. Defensive-at-birth code neither predicts nor prevents later CVEs; repos disagree (OpenSSL 1.38, curl 0.79, nDPI 0.64). History, not initial defensiveness, predicts | int_hypotheses.md | — |
| UT-H1..H3 | Unpatched twins: sfs structural twins (no names/text) of OpenSSL CVE-fixed functions (192 post-2014 fixes, pre-fix snapshot) in BoringSSL and LibreSSL heads are real copies (H1, ≥80% Jaccard ≥0.5), include renamed copies (H2), and include audited-unpatched copies (H3; public files aggregate-only) | 2026-11-06, before any fork scan | **✗**: only 21 twins (H1 not evaluable), 0 renamed copies (H2 ✗), 0 of 4 audited unpatched (H3 ✗). Twin recall on name-found copies 12.5%, 0 in C++-rewritten BoringSSL: the coarse fingerprint is too coarse for copy-finding; motivates a layered (calls/shape) fingerprint benchmark | ut_hypotheses.md | — |
| LIBR-H1..H3, LIBE-H1..H2 | LIB replicated unchanged on fresh PostgreSQL + libgit2 (R); and LIB with the engine's calls_out_to as the coupling measure on the original repos: beats size (E1), non-inferior to the regex within 0.05 (E2). Records that LIB's outcome is library-named work, not security fixes | 2026-11-06, before any coupling score | **LIB-R ✓ replicated** (14 units: +0.44 / +0.49 / +0.18 over size / placebo / names). **LIB-E**: engine call graph +0.34 over size ✓, but −0.06 vs regex (non-inferiority ✗; misses #include and COM-method coupling) | librep_hypotheses.md | — |
| LAY-H1..H3 | Layered fingerprint on UT's OpenSSL→fork copies (104 name-identified, truth by token Jaccard ≥ 0.5): call-set L2 beats coarse L1 at recall@1 (H1); fused L1+L2+L3 (control-flow skeleton) beats L1 (H2), including on C++ BoringSSL at recall@10 (H3). Port traceability out of scope (owner) | 2026-11-06, before any L2/L3 feature | **✓ all three**: recall@1 coarse 46% → call set 69% → fused 80%; BoringSSL C++ copies @1 29% → 94%. Layered fingerprint finds copies the coarse one cannot confirm | lay_hypotheses.md | — |
| VZ-H1..H3 | Vendored zlib in 12 hosts, 7 CVE fix commits: layered fingerprint beats coarse at recall@1 out of sample (H1), finds renamed copies names miss (H2, zlib-ng PREFIX()), code-line patch check agrees with host zlib version ≥ 80% (H3); public aggregates only | 2026-11-06, before any zlib/host scan | **H1 ✓** fused 91% vs coarse 68% @1 (same-name 98%, no names used). **H2** not evaluable (13 "renamed", but 11 are an artefact of `_tr_tally` becoming a macro; only 2 real zlib-ng renames). **H3 ✓** 90% vs version; all 14 misses = rsync's documented backports → 137/137. No unpatched copy present, so detection is untested. Engine skips vendored version-named dirs by default | vz_hypotheses.md | — |
| VZT-H1..H2 | Vendored zlib history (12 hosts, every state of the vendored dir): code-line patch check detects unpatched copies (sensitivity ≥ 90%, H1) and doesn't false-alarm (specificity ≥ 90%, H2) against verbatim-upstream truth; code-vs-version disagreements audited and exposure windows descriptive; public aggregates only | 2026-11-06, before reading host histories | **✗ as registered** (sens 81.5%, spec 72.9%), **but 0 wrong calls in 1,229 decided verbatim cases**: all misses are abstentions. Audit of 20 code-vs-version disagreements: 13 check right (backports, stale labels), 7 check wrong (zlib-ng fixed CVE-2022-37434 differently). Line matching needs a semantic layer for independent fixes. Median exposure windows 49–266 days | vzt_hypotheses.md | — |
| SEM-H1..H3 | Semantic "fixed differently" patch check (fix guard-condition fragments, then line rule) on VZ-T units: no new errors on verbatim truth (H1, ≤1%), meets VZ-T bars (H2), beats the line check on a fresh hand-audited sample of 20 disagreements recorded before SEM verdicts (H3); designed after the zlib-ng example, which is excluded | 2026-11-06, before running on any host state | **SEM-1 ✗ H1** (227 false-"patched" on verbatim-unpatched: non-new guard fragments), ✗ H2, ✓ H3 (17/20 vs 12/20). SEM-1 unusable. **SEM-2** (new fragments only): **✓ H1** 0/1,552 wrong, ✗ H2 (abstentions unchanged), **✓ H3** 19/20 vs line 15/20 on a third held-out audit | sem_hypotheses.md | — |
| CMB-H1..H3 | zlib + expat (43 Changes-mapped fixes, 6 hosts incl. Poco's renamed .cpp copy): SEM-2 no new errors on expat verbatim truth (H1); SEM-2 beats a closest-version matcher (H2) and OSV-scanner (H3, owner approval) on blind-audited modified-copy disagreements; SQLite/libpng dropped pre-data (no metadata CVE→fix mapping) | 2026-11-06, before any expat host history | **✗ H1** (expat: code-line checks wrong on ~25% of verbatim units, false "patched"; closest-version 0). **✗ H2** pooled (31/56 vs 25/56, p 0.25), split by library: zlib modified copies SEM-2 30/30 vs CV 0/30, expat 1/26 vs 25/26. H3 skipped (owner). The code-reading edge is real but conditional on surgical fixes; next: new-to-file added lines | cmb_hypotheses.md | — |
| S3-H1..H2 | SEM-3 (added lines/fragments new to the whole pre-fix file; removed lines gone from the whole post-fix file) on CMB units: no new errors on verbatim truth in zlib and expat each (H1); beats closest-version on a fresh blind audit of disagreements, seed 2986 (H2) | 2026-11-06, before SEM-3 ran | **✗ H1** (expat 74/1,509 wrong, down from 687; zlib 0/1,258). **✗ H2** (31/59 vs 28/59): zlib 30/30 vs CV 0/30 again, expat 1/29 vs 28/29. Code reading works for surgical-fix libraries only; use closest-version for refactoring libraries | sem3_hypotheses.md | — |
| KF-R / KF-L | Replicate goto ↔ lifetime faults on unseen libxml2, libtiff, libpng, libexif, file (KFR-H1, KFR-H3); localize: lifetime fixes land in goto-containing functions, beyond function size (KFL-H1) and more than bounds fixes (KFL-H2). Gates: engine spans vs tree-sitter/ctags ≥ 95%, construct regex vs tree-sitter ≥ 98% | 2026-11-06, before any new repo is cloned | **KFR-H1 ✓ goto raises the security-fix rate on 5 unseen repos (RR 2.80, lo 1.12); KFR-H3 ✗ goto ↔ lifetime does NOT replicate (0.54); KFL-H1/H2 ✗** (function-level lifetime RR 2.07, lo 0.77; not lifetime-specific). goto is a general security-risk marker, not a fault-type fingerprint | kfr_hypotheses.md | — |
| SIG-H1..H3, CPL-H1..H3 | Keyword mix over time: stable project fingerprint (SIG-H1), changes in spurts (H2), files keep their profile (H3). Coupling surface over time: centralises with age (CPL-H1), footprint share shrinks (H2), concentrated coupling makes later dependency work touch fewer files (H3) | 2026-11-06, before any time-series statistic | **SIG ✓✓✓**: a project's keyword mix is a fingerprint (95.9% identification across eras), it changes in spurts (top 10% of quarters carry 45–89% of drift; spurts = architecture events), files keep their profile. **CPL ✗✗✗**: coupling centralises in curl but spreads in libarchive. Abstraction over time is project-specific | evo_hypotheses.md | — |
| REG-H1 / H2 | Commit-level regressions: a commit that leaves strong co-change partners untouched (history-only co-change model) is more often later named as regression-inducing, beyond commit size (H1) and beyond merely touching coupled files (H2); curl, openssl, harfbuzz, nDPI | 2026-11-06, before any co-change statistic; inducing-link audit gate ≥ 0.70 (passed 0.77–0.87) | **✗ not shown** — H1 −0.012 (CI spans 0); H2 replicated null (equivalence): omission = touching coupled files. Commit size stays the best predictor (AUC 0.70 curl, 0.64 openssl) | reg_hypotheses.md | — |
| LIB-H1..H3 | Library-coupling surface: a file's per-line coupling to dependency D (includes + API calls) finds where D-named work lands beyond size (H1), beats other libraries' coupling (H2, placebo) and beats a file-name lookup (H3); curl, libarchive, nDPI, harfbuzz | 2026-11-06, before any dependency-work count | **✓ SHOWN** — H1 +0.397, H2 +0.462, H3 +0.220 (all lo > 0; 21 units on 4 repos, 20/21 beat size); OpenSSL 3 migration in curl: 93% of touched files in the top-20% coupling set | lib_hypotheses.md | — |
| SC (protocol) | Two-stage screen: does any GitGalaxy file metric find one fix class (latent / extrinsic / regression / other) at equal size? Discovery on curl/nDPI/openssl with a frozen selection rule; confirmation on unseen harfbuzz + libarchive scans | 2026-11-06, protocol before discovery; stage 2 registered before the holdout join | **Only `platform_cond /line` → extrinsic CONFIRMED** (harfbuzz +0.154, libarchive +0.102). Of 225 metric forms: no metric finds CVEs beyond size; churn → regression passed discovery but failed holdout; churn → other-fix 1/2 | sc_protocol.md | — |
| BURST-H1..H3 | Extrinsic share of fixes rises in the 90 d after GCC (H1) / Clang (H2) major releases; compiler-named extrinsic fixes respond to their own compiler (H3); pooled over curl, nDPI, openssl, harfbuzz, libarchive | 2026-11-06, shock calendar frozen from upstream tags before any join | **✗ not supported** — GCC +0.002, Clang +0.009 Δ share (CIs span 0; placebo as large); bursts are real but not timed to compiler releases. Only the *where* of the extrinsic surface is predictable | burst_hypotheses.md | — |

## What one repo taught us (the reflection)

1. **The engine's premise survived contact with ground truth.** Commit classes have
   distinct, robust structural signatures in the engine's own keyword vocabulary — the
   security-fix grammar (pointers p=0.0001, branches p=0.0004), the class-discriminating
   prevalence profiles, and one formula tracking events at p=0.007. *Structural keywords
   carry security semantics* — the correlative validation of the whole instrument, which
   matters more than any single finding's novelty.
2. **Formula shape decides temporal validity.** The one vector that moved its assumed
   direction (`safety_score`) is a credit/debit **net** over unlike-signed inputs; every
   **density** either stayed flat or produced an artifact (`tech_debt`'s denominator).
   Direct, event-grounded evidence for the score-contract program's thesis.
3. **Aggregates hide opposing physics.** Fixes add complexity (guards) while removing
   debt-density; the sum washes out. Per-vector is the layer where meaning lives.
4. **Hot files are where everything happens** — security-changed files are *not* hotter
   than ordinarily-changed files (86.2 vs 86.5 percentile, clean null). File-level
   exposure predicts activity; the discriminating questions are conditional and finer-grained.
5. **The emerging function-level profile of CVE-corrected code** (curl; the repo-#2
   prediction, not yet a claim): the functions that undergo CVE fixes are the **long**
   ones (length dominates; complexity adds nothing at equal length), **danger-dense at
   equal length** (more pointer/danger constructs per function, suggestive), in files
   where change concentrates generally; and the *corrections* arrive as **branch+pointer
   additions without new allocations or casts** — while the commits that *introduce*
   vulnerabilities are large feature additions carrying new allocs, casts, and debt
   markers. Vulnerabilities lurk a median **4.5 years** between those two moments.
6. **The guards did their job.** Two artifacts (tech_debt's denominator, the function
   length bias) were caught by the instrument's own controls before either became a slide.

## Current verdict, one sentence

After two repositories and three label families: **history predicts (recidivism,
replicated; change entropy, validated out-of-selection) and structure describes** —
every structural signal reduces to file size, the fix grammar is curl-/human-report-
specific, small-file centrality is dead and mid-band centrality is the registered
candidate — with repo #3 (openssl, fixed-side) carrying every remaining open question.

## Repo #2 (nDPI) replication battery — pre-registered 2026-09-12

Registered **while the nDPI scan was in flight (~[228]/610 commits) and before any nDPI
delta, grammar, ranking, or function-grain result had been computed** — no nDPI analysis
artifact existed at registration (epic gitgalaxy#2982, comment 5648589175). Dataset:
`events/ndpi.json` — 121 security-fix, 73 introduced (OSS-Fuzz-bisected), 111 size-matched
control; `pool_head 7787711`. nDPI uses the original three classes, so
`delta_report`/`signal_anatomy`/`rw_analyses` run unchanged.

**Correction & reporting.** Each lettered claim is one registered test at α=0.01; within a
multi-cell (per-vector) table, Bonferroni across cells; a battery-wide Bonferroni
(α=0.01/k) is reported alongside as a sensitivity. Verdicts published either way. Directions
are pre-set to curl's observed direction (legitimate — registered for unseen nDPI data).

| id | maps to (curl) | registered nDPI direction | test / α | for nulls: equivalence δ |
|---|---|---|---|---|
| **N-H3** | H3 ✓ | fixes' `risk_safety_score` Δ below controls (curl direction) | 1-sided MW, α=0.01 | — |
| **N-GRAM** | grammar ✓ | fixes net-add `struct_branch` **and** `state_pointers` vs controls | 1-sided MW ×2, Bonferroni | — |
| **N-FIXSHAPE** | fix-shaped 66/38/40 ✓ | security-fix fix-shaped rate > control **and** > introduced | 1-sided Fisher ×2, Bonferroni | — |
| **N-RW2** | RW-H2 ✓ | prior-CVE-fix count beats exposure- and LOC-ranking at recall@20%LOC + AUC | 1-sided, α=0.01 | — |
| **D-H1′** | repo-#2 reg. | implicated functions' branch-guard rate `branch/(ptr+danger+alloc+cast+1)` < loc-matched siblings; fix raises it | 1-sided MW pairs, α=0.01 | — |
| **R2-H1** | repo-#2 reg. (curl p=0.032) | at equal length, implicated functions carry more pointer/danger/alloc/cast than siblings | 1-sided MW, α=0.01 | — |
| **N-FIRST** | repo-#2 reg. | pre-event structural exposure separates first-CVE files from age/size-matched non-CVE files | AUC, α=0.01 | — |
| **N-H1** | H1 ✗ (p=0.77) | fixes' event-median structural Δ < controls | 1-sided MW, α=0.01 + effect-size CI | ±0.10 exposure units |
| **N-H2** | H2 ✗ (p=0.023) | introduced > controls | 1-sided MW, α=0.01 + effect-size CI | ±0.10 exposure units |
| **N-RW1** | RW-H1 ✗ | exposure recall@20%LOC > LOC recall@budget | 1-sided, α=0.01 + effect-size CI | ±0.05 recall |

**Null-replication rule (N-H1/N-H2/N-RW1):** "null replicated" is declared only if BOTH
(a) non-significant at α=0.01 in curl's direction AND (b) the effect's 95% CI lies within δ
(TOST/equivalence) — a repeated p>α on nDPI's smaller n is otherwise just lower power. A
**flip to significant is reported as a new signal**, not hidden.

**Explicitly NOT a clean replication on nDPI** (reported as contrast, not pass/fail):
dwell time (nDPI median lurk ≈ weeks under continuous fuzzing vs curl's 4.5 years — a
different discovery population); **D-H1 verbatim** (degenerate at C function grain — subsumed
by D-H1′); **Phase M / wave-1 classes** (revert, cve-followup — no such labels in the
OSS-Fuzz set).

## Mechanism-matched specificity battery — pre-registered 2026-09-12 (for unseen data)

The engine's exposure vectors are named for what they *should* mark (crypto, IO, concurrency,
memory-danger…). The stronger claim than "exposure ≈ CVEs" is **specificity**: the *right*
vector marks the *right* failure type, and it does so **beyond a line count**. These are
registered from curl's *exploratory* CWE×vector table, so — per protocol rule 3 — they are
**never scored on curl's full table that suggested them**. They evaluate on **unseen data**:
a CWE-labeled repo #3 (below), or a held-out curl temporal split (register on pre-2020 CVEs,
test on post-2020). curl's failure supply (323 CWE-labeled events) gives the families power;
the two named vectors that curl *can't* test are called out.

Each signal set is the engine's raw keyword columns. Metric = **defect-lift beyond size**:
AUC(signal | matched controls) and, one-sided, AUC(signal) > AUC(LOC) — the bar
gitgalaxy#2987 sets for a signal to earn a gated formula slot. α=0.01, Bonferroni across the
family.

| id | failure family (example CWEs) | matched signal set | registered direction |
|---|---|---|---|
| **S-H1** | memory-safety (126/416/122/125/415/121/124/787) | `state_pointers + state_memory_alloc + state_cast_hits + state_danger` | memory-CVE functions carry more, at equal length, than matched non-CVE siblings **and** than non-memory CVE functions; AUC > LOC |
| **S-H2** | cert/auth (295/297/305/294/299) | `arch_crypto + def_auth` | cert/auth-CVE files carry more than matched controls **and** than non-auth CVE files; AUC > LOC |
| **S-H3** | info-leak (200/201/319/488/522) | `arch_io + api_exposure` | leak-CVE files carry more egress surface than matched controls **and** than non-leak CVE files; AUC > LOC |
| **S-H4** | concurrency (362/367) — *repo-#3 dependent* | `arch_concurrency + def_sync_locks` | race/TOCTOU-CVE functions carry more than matched controls; AUC > LOC. **Untestable on curl** (single-threaded, ~0 such CVEs) — requires a concurrency-bearing repo |
| **S-H0** | *the discriminant* | all four sets | the family→best-matched-signal **confusion matrix is diagonal** — each family's own set ranks its own failures above other families'. This is the real specificity claim: the vectors are specific, not one undifferentiated "danger" blob |

Failure verdicts published either way. A vector that lifts *generally* but is **not** specific
(S-H0 off-diagonal) is itself a finding — it would mean "danger" is one blob, not a set of
mechanism-specific signals, and it caps what the score-contract program can gate.

### Repo-#3 selection criteria (this battery drives them)
Beyond the repo-#2 hard criteria (OSV GIT ranges with introduced+fixed, ≥50 events,
GitGalaxy-supported language, full history), repo #3 must add what curl and nDPI each lack:
- **CWE labels on the vulnerability data** — *required* for any mechanism-matched test.
  nDPI's OSS-Fuzz feed has none, so nDPI runs the general battery only, never S-H*.
- **Concurrency-bearing with real race/TOCTOU CVEs** — for S-H4 (curl has ~none).
- **Mixed network / non-network CVEs** — so S-H3's IO test has a contrast (curl is
  all-network: no non-IO group to separate against).
Candidates to weigh against these: redis, postgres, nginx (concurrency + mixed surface),
a managed-language service; openssl only if its `CHANGES.md` CVE→PR trail is parsed to real
fix commits (its OSV SHAs are version-tag proxies — see docs/repo2_survey.md).

### Held-out curl result — 2026-09-12 (split at median fix-date 2022-06-25; test half only)

Full detail: `docs/specificity_curl_heldout.md` (tool: `tools/specificity_split.py`).

| id | verdict | evidence |
|---|---|---|
| **S-H1** memory ↔ danger cluster | **✗ not supported (genuine null)** — signal well-populated (state_pointers 70% nonzero) yet AUC ties LOC (0.588 vs 0.590); no defect-lift out-of-sample | specificity_curl_heldout.md |
| **S-H3** info-leak ↔ arch_io/arch_api | **✗ not supported (genuine null)** — populated; AUC 0.54 vs LOC 0.57; no lift | specificity_curl_heldout.md |
| **S-H2** cert/auth ↔ arch_crypto/def_auth | **⚠ degenerate — no verdict** — `def_auth` is 0 across all 1.05M rows, `arch_crypto` 0.1%; the matched signal is absent (D-H1-class vocabulary gap), AUC pins at 0.509. Untestable on curl; deferred to a repo with live crypto/auth vocabulary | specificity_curl_heldout.md |
| **S-H0** the discriminant (diagonal?) | **✗ not supported** (caveat: cert/auth column dead) — among the *live* signal-sets the **memory** set ranks highest even for info-leak's positives; the populated "danger" signals read as a general code-mass proxy, not mechanism-specific | specificity_curl_heldout.md |

**Reading.** Predicting *which* file gets *which* CVE from pre-event structural *standing*
does not work on curl (coheres with H1/RW-H1: standing ≈ LOC) — the real security signal is
in the fix **delta/grammar**, not standing. cert/auth couldn't be tested (dead vocabulary),
which is itself an engine signal: `def_auth`/`arch_crypto` under-fire on C (cf.
gitgalaxy#2984/#2979). This is a *within-curl temporal* result; the independent cross-repo
test remains repo #3 — and it must carry live crypto/auth + concurrency vocabulary.

## Repo #2 (nDPI) replication — RESULTS (2026-09-12)

Ran the pre-registered nDPI battery (epic gitgalaxy#2982, comment 5648589175) on the fresh
nDPI scan (112 security-fix / 68 introduced / 96 control usable events; 555 snapshots).
Reports: `docs/ndpi_exposure_report.md`, `docs/ndpi_signal_anatomy.md`, `docs/ndpi_rw.md`.

| id | curl | nDPI | cross-repo verdict |
|---|---|---|---|
| N-H1 aggregate exposure | null (0.77) | null (**0.70**) | ✅ null replicates |
| N-H2 introduced raises | null (0.023) | null (**0.37**) | ✅ null replicates |
| N-RW1 exposure > LOC @budget | null | null (**0.60**, W/L/T 8/8/96) | ✅ null replicates |
| N-H3 `safety_score` tracks | ✓ (0.0072) | **✗ (0.71)**, all vectors flat | ❌ **fails to replicate** |
| N-GRAM fix grammar (branch/ptr adds) | ✓ (0.0004/0.0001) | **✗** (struct_branch 0.28, state_pointers 0.079) | ❌ **fails** |
| N-FIXSHAPE fix-shaped signature | ✓ 66/38/40 differential | **✗ 58/59/59** (no differential) | ❌ **fails** |
| R2-H1 danger density (equal length) | suggestive (0.032) | **✗ (0.47)**, implicated 19 vs sibling 20 | ❌ **fails** |
| D-H1/D-H2 guard deficit | degenerate | degenerate (**0.70**) | ➖ degeneracy replicates |
| N-RW2 recidivism beats static | ✓✓ | **✓✓ (p<1e-4 vs exposure and vs LOC)** | ✅ **replicates** |

**The verdict after two repositories:** the only *positive* that replicates is **recidivism**
(N-RW2) — a file's prior-CVE-fix count beats every structural ranking, decisively, on both
repos. Every **structural** signature curl showed — the `safety_score` vector (H3), the
fix-shaped branch/pointer grammar (N-GRAM/N-FIXSHAPE), and the danger-density function
profile (R2-H1) — **fails to replicate on nDPI.** And every structural **null** (aggregate
exposure, exposure-vs-LOC) holds on both.

**Why the structural signatures collapsed:** nDPI's CVEs are OSS-Fuzz-discovered, and its
fixes are *tiny* — median event net-LOC **+1** vs curl's +6 — minimal bounds-checks that
barely move any signal (function-grain values are non-degenerate: implicated functions
n=243, complexity 22 vs 3, so the DB is populated; the fixes simply don't add branch/pointer
*grammar* the way curl's user-reported-CVE fixes did). This is the pre-registered
discovery-population contrast made real: **curl's fix-shaped grammar was a property of
user-reported CVE fixes, not a cross-repo law.** The emerging function profile (register
reflection #5) is therefore **withdrawn as a cross-repo claim** — length dominates on nDPI
too (length-bias gate: complexity 17 vs 15, p=0.39), but danger-density does not separate.

Stage-2 items still owed (need new code, verdicts pending): D-H1′ (branch-guard variant),
N-FIRST (first-CVE AUC), and the equivalence/TOST CIs formalizing the three replicated
nulls. Given the grammar collapsed, D-H1′ and N-FIRST are expected null; they will be
evaluated and published regardless.

**What this sharpens:** structural exposure is a general size/activity proxy whose
event-signatures are repo- and discovery-specific; the durable, cross-repo predictive law is
**recidivism** (history beats structure). That is the rung-7 baseline, now confirmed twice.

### Stage-2 (D-H1′, N-FIRST, equivalence CIs) — 2026-09-12

Detail: `docs/ndpi_stage2.md` (tool: `tools/ndpi_stage2.py`).

- **D-H1′ / D-H2′ (branch-per-danger guard deficit, nDPI): ✗ not supported.** Guard rate
  `struct_branch/(ptr+danger+alloc+cast+1)` — implicated functions 0.634 vs siblings 0.600
  (p=0.75, *wrong* direction); the fix doesn't raise it (D-H2′ null). Non-degenerate this time
  (branch-guards exist where `def_safety` didn't), so a real "no", not a vocabulary artifact.
- **Equivalence (TOST) on the three replicated nulls (nDPI): all ✓ EQUIVALENT-NULL.** N-H1
  effect 0.000, 95% CI [0, 0.0008] ⊂ ±0.10; N-H2 0.000, CI [−0.011, 0.039] ⊂ ±0.10; N-RW1
  0.000, CI [0, 0] ⊂ ±0.05. The nulls are **confirmed near-zero**, not merely underpowered —
  the structural nulls genuinely replicate.
- **N-FIRST (first-CVE profile, nDPI): ✓ SUPPORTED — but the mechanism is CENTRALITY, not
  fine structure.** Structural exposure separates first-CVE files from size-matched clean files
  (AUC 0.755). Orchestrator verification: that raw AUC is inflated — the [0.66,1.5]× LOC match
  is loose (positives +25 LOC larger within the band) and AUC(LOC)≈0.50 is forced by matching,
  so the "+0.25 over LOC" is circular. Dividing size out, a real component survives
  (**AUC(density) 0.624, density-win 78%**) — carried by *total* exposure (`api_exposure`/
  **centrality**) against *peripheral* never-CVE files: the hot-files effect (reflection #4)
  that also drives recidivism, **not** the fine danger-structure the density/specificity tests
  killed (memory density-win 43%). curl context far weaker (density-win 62%). So the file that
  gets its *first* bug is a **central/hot** one — a genuine but coarse signal, to be cleanly
  separated from residual size + activity by tighter matching + a per-vector decomposition,
  **registered for repo #3.**

**Net after Stage 2:** the two-repo picture is unchanged and now airtight — recidivism is the
lone replicated positive; aggregate/fine-structural exposure is size (the three nulls are
*equivalence-confirmed*); and the only "structure predicts the first bug" signal that survives
is **centrality**, which is the same hot-files axis, not a new structural predictor.

### G-H1 / G-H2 — the LOC-floor grammar re-test (2026-09-12)

Registered on gitgalaxy#2982 (comment 5649412476) **before any floor-restricted statistic was
computed**; only the fix-size distributions were inspected to set the floors. The question:
the cross-repo grammar failure was confounded with fix size (nDPI fixes median net-LOC +1 vs
curl +6) — a one-line bounds-check cannot express a structural signature. Restricting BOTH
repos to fixes above a churn floor de-confounds them. Detail: `docs/grammar_floor.md`
(tool: `tools/grammar_floor.py`).

| id | verdict | evidence |
|---|---|---|
| **G-H2** curl's grammar survives the floor | **✓ SUPPORTED** | persists at ≥5 (branch p=0.0001) and ≥10 (p=0.0008, n=115/108); fix-shaped composite 72%/39% and 69%/37%; thins only at ≥20 where n=72 halves power. **Not** an artifact of tiny commits. |
| **G-H1** the grammar returns on nDPI under a size floor | **✗ not supported** | no floor revives it — at ≥10 (n=50/46) branch p=0.44, `state_pointers` p=0.93 (*wrong* direction), fix-shaped composite **68% fix vs 67% control** (no differential). |

**This is pre-registered outcome (b): fix size is NOT the explanation.** The grammar is
**genuinely curl-specific** — a property of *human-reported CVE fixes*, not a consequence of
nDPI's small commits. Conservative detail: nDPI's controls are *larger* than its fixes at
every floor (median net-LOC 3.0 vs 4.8 at ≥10), so the fixes were not size-handicapped.

**What remains open.** With size eliminated, the surviving explanation for the curl↔nDPI
divergence is **discovery process** (human-reported vs fuzzer-found). That cannot be tested by
comparing repos — repo is confounded with language, era, and team — it requires **both
provenance classes inside one repository** (e.g. curl commits fixing OSS-Fuzz/ASAN findings vs
curl commits fixing human-reported CVEs, labeled from commit-message provenance). Registered
as the next experiment; until it runs, the fix-grammar stands as **single-repo, single-
discovery-process, and explicitly not general**.

## HCM variant sweep + centrality bands — results (2026-09-12/13)

**HV-H1/HV-H2 — the Hassan HCM family** (registered epic comment 5649866008; detail
`docs/hcm_variants.md`). 36 variants (attribution × decay × period) + repowise's flavour,
evaluated size-orthogonally on curl CVE labels:

| id | verdict | evidence |
|---|---|---|
| **HV-H1** a variant clears the size wall (≥3/4 LOC bands) | **✗ not supported** — best variant `HCM1_LD_30` clears 2/4 (Q3 0.771, Q4 0.803); same monotone wall shape as repowise's | hcm_variants.md |
| **HV-H2** best variant beats LOC pooled | **⚠ supported-as-computed (lift +0.0238, lo +0.0050) but DISCOUNTED — selected best-of-36 and tested on the same data**; out-of-selection validation registered as B-H3 | hcm_variants.md |

Robust family pattern regardless of the winner: all top-8 are HCM1 (share-weighted), 30-day
periods beat 90/180d, and HCM2/HCM3 at 180d are *worse than a line count* (−0.10..−0.15).
repowise's shipped shape was near-optimal (rank ~6, lift +0.0192) — their choice was sound.

**C-H1/C-H2 — centrality in the small-file regime** (registered 5650157545; per-cell
checkpoint cache, full doc regenerating):

| id | verdict | evidence |
|---|---|---|
| **C-H1** centrality beats LOC in small bands | **⚠ NOT EVALUABLE on curl** — the small bands are unpowered by the data itself: ≤22-LOC has **1** CVE positive, 23–48 has **4**; the ≥20-positive rule refuses verdicts (without it we'd quote AUC 0.999 off one positive) | centrality cache / centrality_bands.md |
| **C-H2** lift monotone-decreasing with size | **suggestive, no verdict** — PageRank lift +0.458 → +0.320 → +0.154 → **−0.271**, perfectly monotone (repowise's shape), but the small end is unpowered | same |

Solid negative within this: **in >108-LOC files (433 positives) PageRank is far worse than a
line count** (0.525 vs 0.796) — centrality is not a large-file ranking signal.

## Overnight bug-label expansion (B-H1..B-H3) — registered 2026-09-13, batch in flight

Mirror of epic comment 5651082895 (registered **before the sample was drawn**). Purpose:
power the small-file bands with labels that actually land in small files (CVE fixes don't),
and provide selection-free validation data. Sample (seed 2982): ALL `regression` commits +
500 uniform from `Fixes #` + 300 from `Bug:`; SHAs already scanned excluded; multi-label
kept. Drawn: **1,107 unique events** (307 regression / 500 fixes / 300 bug; census after
exclusions 1,915 / 1,195 / 307 — the registration's parenthetical "(census 154)" for
regression was a case-sensitive undercount; the registered case-insensitive rule stands).
Batch: `dbs/bugs_batch.log`, ≤2,214 scans ≈ 6.4 h, resumable by construction.

| id | claim (α=0.01; ≥20-positives power rule) | status |
|---|---|---|
| **B-H1** | on bug-label positives, ≥1 centrality measure beats LOC (AUC>0.5, lift lo>0) within each powered small band (≤22, 23–48); Bonferroni 5×bands | **pending scans** |
| **B-H2** | PageRank lift decreases across all four bands in ≥99% of 5,000 event-bootstraps | **pending** |
| **B-H3** | `HCM1_LD_30` (frozen from the CVE-label selection) has pooled lift>0 over LOC on bug labels — fresh labels, no selection problem | **pending** |

Priors registered in advance: B-H1 uncertain (the live lead), B-H2 expected supported,
B-H3 expected shrunken-but-positive. Exploratory alongside (no verdicts): per-class grammar
profiles (CVE vs Fixes# vs Bug: vs regression — the Phase-M question).

## B-H1..B-H3 — results (2026-09-13; registration epic comment 5651082895)

957 usable bug-label events, 767,591 pooled files, 1,900 positives; **both small bands
powered** (28 / 42 positives). Detail: `docs/bh_eval.md` (tool `tools/bh_eval.py`,
numpy-parallel, per-cell checkpointed).

| id | verdict | evidence |
|---|---|---|
| **B-H1** small-file centrality | **✗ not supported** — with real power the small-file story dies: PageRank ≤22 *inverted* (AUC 0.259); 23–48 n.s. | bh_eval.md |
| **B-H2** monotone lift shape | **✗ not supported, decisively** — frac_monotone 0.0000/5000; the true shape is an **inverted U** (lifts −0.047 / +0.017 / +0.145 / −0.253). The CVE-label "perfect monotone" was an unpowered-band artifact | bh_eval.md |
| **B-H3** HCM selection-free validation | **✓ SUPPORTED** — `HCM1_LD_30` frozen from the CVE selection, fresh bug labels: AUC 0.868 vs LOC 0.830, lift **+0.0379** (lo +0.0211). **The second genuine positive after recidivism**, and the first *feature* to beat a line count out-of-selection | bh_eval.md |

**Exploratory (context cells, outside the registered family — registered for repo #3, not
claimed):** the 49–108 mid-band carries two robust centrality cells (PageRank lift +0.145
lo +0.020; popularity +0.132 lo +0.025). Mid-band, not small-file, is the surviving
centrality candidate.

**Program standing after the bug-label expansion:** surviving predictors = **recidivism**
(replicated, 2 repos) + **change entropy (HCM1_LD_30)** (selection-free, single-repo until
repo #3). Centrality small-file: dead. Structure/keywords as predictors: size, everywhere.

## Repo-#3 survey — 2026-09-13 (docs/repo3_survey.md)

No candidate clears all five criteria. **Primary: openssl, fixed-side-only** — CWE joinable
via NVD (5/5), human-reported fixes (median ≈+13 net LOC), confirmed race CVEs (S-H4
testable at last), mixed network/non-network surface (S-H3 contrast); introduced-side 0%.
Its CHANGES/commit trail is parseable (9/10 sampled resolve to diff-verified fix commits) —
reversing repo-2's future-work flag. **Version-proxy diff-check failed** nginx, sqlite,
systemd, imagemagick, netty, tensorflow-partially, and **vim** (worst mode found yet:
real-looking SHAs pointing at *unrelated* commits). Sleeper lead: **kernel subsystem-scoped
harvest** (net/ ≈43s/scan, fs/ ≈32s) — the only gold-standard introduced-side at tractable
cost; unexplored.

## X-H1 / X-H2 — registered 2026-09-13 from the keyword-pools exploration (unseen data only)

Mirror of epic comment 5653744144. Both derive from `docs/keyword_pools_explore.md`
(post-hoc) and are therefore never scored on curl.

| id | claim (α=0.01) | evaluates on |
|---|---|---|
| **X-H1** | "Unpaired allocation" (net-add `state_memory_alloc` with `def_cleanup` delta ≤ 0) is enriched among vulnerability-**introducing** commits vs paired-allocation commits; one-sided Fisher | a genuine introduced-side corpus (kernel-subsystem harvest, tc#27) |
| **X-H2** | The fix-grammar **gradient** replicates: fix-shaped rate orders security-fix > ordinary bug-fix > control (two one-sided Fishers, Bonferroni ×2) | openssl (repo #3, tc#26) |

Motivation on record: the `state_memory_alloc`+`def_cleanup` pair co-moves at ρ=0.85 while
nearly size-independent (ρ=0.25 vs net-LOC) — breaking the pairing is the anomaly; and the
8-class table orders 66/53/48/46/38/20/13, replacing the retired binary "grammar is
CVE-specific" claim with a gradient.

## What precisely was falsified — the scoping statement (2026-09-13)

The program's negative results share four assumptions, and the falsification applies to
their **conjunction**, not to "structure relates to risk" in general:

> risk as a property of a **file**, in **isolation**, as a standing **level**, scored by
> marker **abundance**.

Every dead test instantiated all four (pooled, density-normalized, length-matched, banded,
multivariate, and trajectory variants alike). What was **validated** at the same time: the
markers annotate *activity* (the x-ray — what a function is involved in), and marker
*changes* characterize *events* (fix-vs-nonfix at patch grain; allocation-at-introduction
51% vs 5–10%). Analogy on record: protein domains annotate function, not pathology;
pathology is dosage, context, and interaction partners — we scored domain counts per gene
and called the count a disease score.

**What remains untested — hypothesis 3 restated one level up (tc#37):** risk as a *system*
property — module-level dosage/thresholds (SYS-1), marker *dispersion* across files
(SYS-2), system-level discipline trajectories (SYS-3), cross-file responsibility splits
(INT-1), marker×process conjunctions (INT-3), and neighborhood/graph interactions (INT-2,
blocked on edge persistence, gitgalaxy#2992). Mandatory guard carried forward: module-LOC
controls in every SYS design, since aggregation can re-manufacture the size confound one
level up. Engine-side consequence tracked as gitgalaxy#2991 (descriptive-layer reform +
separate gated predictive layer).
## Hunk-grain grammar (tc#34, 2026-09-13) — and an honest pre-annotation on X-H2

`docs/hunk_grammar.md` (exploratory, patch-lines only, engine C rules, bystanders excluded):

- **The file-grain gradient largely collapses at patch grain.** Fix-shaped rate: security-fix
  66→57%, bugfix-fixes 53→56%, bugfix-bug 48→49%, regression 46→49%, control 38→39%, revert
  13→10%. Scoring only what the developer typed, **an ordinary C bug fix looks structurally
  like a CVE fix** — what survives is a *fix-vs-nonfix* separation (~50–57% vs 39% vs 10%),
  not a security-specific grammar. The file-grain security-vs-ordinary spread reads as
  bystander/dilution artifact.
- **X-H2 annotation, recorded BEFORE openssl runs:** X-H2's registered claim (security-fix >
  ordinary bug-fix > control) stands as registered, but this hunk-grain evidence predicts its
  FIRST inequality may fail at patch grain. Updated expectation on record: the second
  inequality (fix-classes > control) is the likely survivor. The registered test is unchanged;
  only the stated prior is revised.
- **The allocation table — the sharpest single-keyword class separation of the program:**
  share of patches ADDING any allocation / any cast: **introduced 51% / 46%** vs security-fix
  10%/8%, control 5%/14%, regression 5%/6%, bugfix-bug 9%/6%, bugfix-fixes 6%/14%. Half of
  vulnerability-introducing patches add allocations; ~1-in-15 fixes do. The "no new
  allocations" veto works against *introductions*, not for distinguishing security fixes from
  controls — the strongest support yet for the X-H1 family (allocation marks where risk is
  born; evaluates on an introduced-side corpus, tc#27).
- Method caveat on record: rules run over raw diff text (comments/strings not stripped —
  `branch` matches the English word "for" in comments); same instrument limits as everywhere.

## DYN-H1 / DYN-H2 — registered 2026-10-23 from the gitgalaxy outcome-label pilot (unseen data only)

Mirror of epic comment 6368357162 (gitgalaxy#2982, 2026-10-23T15:23Z); tracked in tc#41. Derived from gitgalaxy#2720,
which was **not** pre-registered, so neither claim is ever scored on curl or another pilot repo.

Registered **2026-10-23, before any dynamism statistic is computed on the evaluation data.** Source: gitgalaxy's outcome-label pilot (#2720; `docs/research/outcome_label_pilot.md`, memo on #2716). The pilot found per-file dynamism associated with more later fix commits at equal size and evidence: pooled MH rate ratio 1.27 (1.06–1.50), 1.20 (0.98–1.50) with the bulk-commit guard. The ratio shrank as LOC was held tighter (1.81 at 3×3 strata, 1.39 at 6×6, 1.27 at 10×4), and curl and redis carried it. That result is **exploratory** (not pre-registered), so it is never scored on the data that suggested it.

**Predictor.** `state_heat_triggers`, the `file_data` column of the `reflection_metaprogramming` signal: the per-file dynamism count that gitgalaxy#2719's risk term reads. In C (all evaluation repos below) the signal is the union of function-like `#define` and `goto`:
`^#\s*define\s+[ID_START][ID_CONTINUE]*\([^)]*\)|\bgoto\b` (gitgalaxy `languages/c.py`). If the C pattern differs from this at the scan's engine SHA, the run stops and the registration is amended before any statistic is computed.

**Data (unseen for this predictor).** nDPI security-fix events (`events/ndpi.json`, 121), then openssl (repo #3, tc#26) once harvested. **Excluded from scoring:** curl (it carried the pilot estimate) and every other pilot repo. curl may appear as labelled context only.

**Unit and leakage guard.** Every file in each event's first-parent snapshot (T0) is a candidate. A positive is a T0 file the event commit touches (rename-tracked, the B-H1 join). Every feature is read at T0. Every T0 snapshot is scanned at one engine SHA, recorded in the result doc, under `SCAN_ENV` (`GITGALAXY_DISABLE_GIT_HISTORY=1`).

| id | claim (α=0.01) | supported iff |
|---|---|---|
| **DYN-H1** | Dynamism beats LOC at ranking fix-touched files **within size bands** (the gitgalaxy#2987 defect-lift-over-LOC bar) | In ≥1 powered absolute-NLOC band (≤22, 23–48, 49–108, >108; the B-H1 scheme): lift = AUC(`state_heat_triggers`) − AUC(`total_loc`) > 0 with its one-sided event-bootstrap lower bound (5,000 rounds) > 0, Bonferroni α = 0.01 / (number of powered bands) |
| **DYN-H2** | The pilot's estimand replicates: files with any dynamism are touched by fixes at a higher rate at equal size and evidence | Mantel-Haenszel rate ratio (exposed = `state_heat_triggers` > 0; strata = event × LOC decile × evidence quartile, edges per T0 snapshot; evidence = sum of `EVIDENCE_COLUMNS` in gitgalaxy `tests/tools/outcome_pilot.py` @ `3e3347c`, dynamism excluded) has a one-sided event-bootstrap lower bound (5,000 rounds, α=0.01) > 1.0 |

**Nulls.** A *replicated null* is claimed only by equivalence: DYN-H2's 90% CI inside [0.80, 1.25]; DYN-H1's two-sided 90% CI for the lift inside [−0.02, +0.02] in every powered band. Anything else not supported is *inconclusive*, not null. A band or repo below 20 positives is *not evaluable*.

**Repos.** The verdict is published per repo: nDPI first, openssl added when tc#26 lands. A claim is supported overall iff it is supported on every evaluable repo.

**Decision rule (registered with the claims).**
- (a) Neither claim supported on any evaluable repo, or both equivalence-null: open a gitgalaxy issue to set the per-file dynamism weight (the #2719 term) to zero, the same rule that zeroed the strictness weight.
- (b) DYN-H2 supported, DYN-H1 not: keep the current modest weight as a correction; no increase.
- (c) DYN-H1 supported: keep it, and treat it as a ranking-layer candidate. Before any weight increase, it needs a third-repo replication registered separately.

**Exploratory alongside (no verdicts):** a C construct split (`goto` vs function-like `#define`, counted separately from T0 source), security-fix vs size-matched control context, and curl pre-pin history as context.

**Priors on record:** DYN-H1 expected **not supported** (every structural signal so far reduced to size); DYN-H2 **uncertain** (the pilot's ratio shrank under tighter size control).

## FWD-H1..FWD-H3 — forward prediction from engine-native, as-of history (tc#29) — registered 2026-11-05 (unseen data only)

Registered **2026-11-05, before any forward-prediction statistic is computed from as-of scans.** Until now every
scan in this program ran with history ablated (`GITGALAXY_DISABLE_GIT_HISTORY=1`, correct for causal deltas), so the
program's two surviving predictors (recidivism, change entropy) were only ever computed ad hoc from git. gitgalaxy#7818
adds `GITGALAXY_HISTORY_ASOF=1`: history measured as of the scanned commit (window ends at its commit time, whole
window read, out-of-window files dated by their last ancestor commit). The question is whether the **engine's own**
history columns, read at time t, predict which files get fixed after t, beyond file size.

**Why curl is not scored.** curl supplied the evidence these claims rest on (IV pooled churn AUC 0.859; walk churn
proxy 0.855; HCM selected and validated on curl). curl runs the identical pipeline as **instrument check +
labelled exploratory context only**.

**Data.** nDPI (`events/ndpi.json`, `security-fix` class, 121 events). openssl is added when tc#26 lands.

**Unit, snapshots and outcome (identical on every repo).**
- Snapshot t: the newest first-parent commit on the default branch dated before each calendar-quarter boundary
  (Jan/Apr/Jul/Oct 1 UTC), from the first quarter with ≥50 C files through the last quarter whose outcome window
  closes before the event harvest's end date.
- Candidates: every C file (`language = 'c'`) in snapshot t. Positive: a candidate that a fix-class event dated in
  (t, t+180 days] touches (rename-tracked; the walk_trajectories touched-file harvest).
- Every snapshot is scanned at one engine SHA (recorded in the result doc) with `GITGALAXY_HISTORY_ASOF=1`,
  `--spec-alignment`, history **enabled**. All features are read from that scan, so nothing after t enters.

| id | claim (α=0.01) | supported iff |
|---|---|---|
| **FWD-H1** | Engine churn ranks future-fixed files above LOC **within size bands** | In ≥1 powered absolute-NLOC band (≤22, 23–48, 49–108, >108; the B-H1 scheme): lift = AUC(`raw_churn_freq`) − AUC(`total_loc`) > 0, with a one-sided snapshot-cluster bootstrap (5,000 rounds, seed 2982) lower bound > 0 at Bonferroni α = 0.01 / (number of powered bands) |
| **FWD-H2** | Engine ownership entropy does the same | As FWD-H1 with `ownership_entropy` |
| **FWD-H3** | Engine change entropy does the same | As FWD-H1 with the engine's change-entropy column. **Scored only if** the engine implements exactly `HCM1_LD_30` (30-day periods over the 365-day window; HCM1 share-weighted attribution; linear decay max(0, 1 − age/365)), and on every scored snapshot its per-file values have Spearman ≥ 0.99 against `tools/hcm_variants.py`'s `HCM1_LD_30` from the same commit's git log. Otherwise FWD-H3 is *not evaluable* until the registration is amended. |

**Instrument gate (binding, checked before any FWD statistic).** On every scored snapshot, Spearman ≥ 0.95 between
the engine's `raw_churn_freq` and an independent count (`git log --no-merges` over [t − 365 d, t], `.git-blame-ignore-revs`
excluded) for C files with ≥1 commit in the window. If any snapshot fails, the run stops and the instrument is fixed
before anything is scored.

**Nulls.** A *replicated null* is claimed only by equivalence: the two-sided 90% CI for the lift inside
[−0.02, +0.02] in every powered band. Any other non-support is *inconclusive*. A band or repo with fewer than 20
positives is *not evaluable*.

**Decision rule (registered with the claims).**
- (a) Any FWD claim supported on every evaluable repo: open a gitgalaxy issue to promote that history column into the
  predictive layer (the #2991 disposition "promote history family"), with a separate third-repo replication registered
  before any weight is set.
- (b) None supported, or all equivalence-null: history columns stay descriptive. tc#29's as-of mode is kept as
  infrastructure; there is no predictive claim.

**Exploratory alongside (no verdicts):** the same pipeline on curl (quarterly snapshots and the 219-release walk);
`silo_risk` and `risk_stability`; and the security-fix vs bug-fix label split on curl.

**Priors on record:** FWD-H1 **uncertain** (on curl, pooled churn sat below LOC: walk 0.855 vs 0.907). FWD-H3
**leaning supported** (the one feature that beat LOC out-of-selection). FWD-H2 **expected not supported**.

### FWD amendment 1 — 2026-11-05, before any nDPI (scored) statistic

**What prompted it.** The binding instrument gate failed on curl, which is exploratory (44/105 snapshots at
Spearman ≥ 0.95). Diagnosis found two errors **in the registration's gate, not in the instrument**:

1. The gate called `raw_churn_freq` a commit count. The engine's documented column is a recency-weighted rate,
   `commits_in_window / sqrt(max(weeks since the file last changed, 1))` (gitgalaxy `signal_processor._calc_raw_temporal_signals`).
   Reconstructed independently from git (no-merges window count over [t − 365 d, t] by committer time, blame-ignore
   revs excluded, last change = newest author time of a qualifying commit at or before t), it matches the engine
   **exactly on every C file** of the five curl snapshots checked (74/74, 112/112, 334/334, 597/597, 822/822; rho 1.0000).
2. The registration did not handle snapshots where the engine reports **no usable history** (#4548: single-commit
   span or shallow clone gives every file neutral stability 50 and churn 0). curl's first quarterly snapshot is its
   one-commit 1999 import. The correlation there is undefined, and there is no history to predict from.

**Amended (applies to every repo; the predictors, outcome, bands, bootstrap and decision rule are unchanged):**
- The gate compares `raw_churn_freq` with that independent reconstruction of the same formula, still at Spearman ≥ 0.95 on
  every evaluated snapshot.
- A snapshot whose every C file has `risk_stability = 50` and `raw_churn_freq = 0` (engine-reported unusable
  history) is excluded from the gates and from all FWD scoring. The number excluded is reported.

No outcome-linked statistic on nDPI was computed before this amendment. curl's exploratory pooled AUCs had already
been printed by the failed run; curl is unscored, so they bear on no verdict.

## FWD-H1..FWD-H3 — RESULTS (2026-11-05; registration + amendment 1 above)

Engine `e246915aa` (gitgalaxy#7818: as-of history + persisted change entropy), `--spec-alignment`, history
enabled as of each snapshot. Reports: `docs/fwd_ndpi.md` (scored), `docs/fwd_curl.md` (exploratory).

**Gates (binding).** On nDPI, the churn reconstruction passed 43/43 snapshots (min rho 0.991) and HCM parity
passed 43/43 (min 0.995). On curl both passed 104/104 at rho 1.0000, with one one-commit snapshot excluded under
amendment 1. The engine's history columns are what git says they are, and its change entropy is the validated
`HCM1_LD_30`.

**nDPI (scored).** 43 quarterly snapshots, 10,018 (snapshot, C file) rows, 452 positives. Powered bands: 49–108
(136 positives) and >108 (313). Bonferroni α = 0.005.

| claim | 49–108 lift [one-sided lo] | >108 lift [one-sided lo] | verdict |
|---|---|---|---|
| **FWD-H1** churn | −0.260 [−0.362] | −0.003 [−0.066] | **not supported** (inconclusive) |
| **FWD-H2** ownership entropy | −0.153 [−0.335] | −0.046 [−0.086] | **not supported** (inconclusive) |
| **FWD-H3** change entropy | −0.083 [−0.284] | +0.023 [−0.042] | **not supported** (inconclusive) |

Pooled AUCs: total_loc 0.700, change entropy 0.667, ownership 0.598, churn 0.595. None of the nulls is an
equivalence null; the CIs are too wide on 43 snapshots. A claim needs every evaluable repo, so none can be
supported overall whatever openssl shows.

**Decision rule (b) applies.** History columns stay descriptive. The as-of mode stays as infrastructure for causal
and forward work. No predictive promotion.

**Priors vs outcome.** FWD-H3 was "leaning supported" and is not; H1 "uncertain", H2 "expected not supported".

**Exploratory, no verdicts.**
- curl: churn and change entropy show positive point lifts over size in the 23–48 and 49–108 bands (+0.02 to
  +0.06), but every lower bound is below 0, and pooled size wins (0.84). Change entropy's within-band edge on curl
  does not carry to nDPI's fuzzer-found fixes.
- nDPI 49–108: churn and ownership rank strongly *inverted* (AUC 0.28 / 0.39). This is plausibly a few mass
  fuzzer-fix commits dominating the band. Worth a snapshot-level look before any reading.
- Recency: `risk_stability` (high = long unchanged) has AUC 0.21 on curl. Inverted, "changed recently" is 0.60–0.78
  in the small bands against size's 0.50–0.56. That makes it a pre-registration candidate for an unseen repo, not a
  finding (on nDPI it is 0.42, i.e. 0.58 inverted, against size 0.70 pooled).

## FREC-H1 / FREC-H2 — function-grain recidivism (tc#28) — registered 2026-11-05, before any function-grain statistic

**Background.** File-grain recidivism is the program's only cross-repo replicated predictor (RW-H2: curl, then nDPI,
p < 1e-4 against exposure and LOC). The question is whether, **within the files a fix touches**, the function that
was fixed before is where the next fix lands, better than function size predicts. A line count has no memory, so it
cannot imitate this. No function-grain recidivism statistic has been computed on any repository before this entry.
curl hosted the file-grain discovery, so it is scored only under the temporal split below.

**Data.**
- curl: `security-fix` (events/curl.json) ∪ `bugfix-fixes`, `bugfix-bug`, `regression` (events/curl_bugs.json),
  deduplicated by sha.
- nDPI: `security-fix` (events/ndpi.json).
- Snapshots are each event's parent and child, scanned at engine `32619e4a5` (history ablated, `--spec-alignment`;
  the PR #50 rescan for curl, and the same engine for nDPI).

**Unit and labels.**
- Event date = the fix commit's committer time.
- Candidates for event e: every `function_data` row with `start_line` and `loc` in each C file e touches, read at
  e's parent; only files with ≥ 2 such functions.
- Positive: a candidate whose span [start_line, start_line + loc) overlaps e's parent-side changed lines
  (`git diff -U0 parent..child`, the signal_anatomy pass-2 mapping).
- An event qualifies if it has ≥ 1 positive and ≥ 1 negative candidate.

**Predictor (leakage-free by construction).**
- prior(f, e) = the number of fix-class events of the same repo with committer time strictly before e's whose
  positives included the same (parent-side file path, function name).
- History accumulates over **all** events. Renames break lineage, which handicaps the predictor.

**Temporal split.** Only events dated after the median date of the repo's fix-class events are scored. The earlier
half only builds history.

| id | claim (α = 0.01 / 2 claims = 0.005, one-sided) | supported iff |
|---|---|---|
| **FREC-H1** | Prior function-fix count ranks fixed functions above function size, within touched files | mean over scored qualifying events of [AUC_e(prior) − AUC_e(loc)] > 0, with event-bootstrap lower bound (5,000 rounds, seed 2982) > 0. AUC_e is the within-event Mann-Whitney AUC, ties ½ |
| **FREC-H2** | Memory adds to size: prior count, ties broken by size, beats size alone | the same, with score = (prior, loc) ranked lexicographically |

**Repos.** Verdicts are published per repo. A claim is supported overall iff it is supported on curl **and** nDPI.
A repo with < 20 scored qualifying events is *not evaluable*.

**Nulls.** A *replicated null* is claimed only by equivalence: the two-sided 90% CI of the mean lift inside
[−0.02, +0.02]. Otherwise it is *inconclusive*.

**Decision rule.**
- (a) FREC-H2 supported overall: open a gitgalaxy issue for a function-precise "prior fixes here" line in the
  function dossier. An openssl replication is registered before it becomes any score input.
- (b) Only FREC-H1 supported: the same, flagged as a standalone ranking, not an additive one.
- (c) Neither: the dossier's predictive line stays file-grain.

**Exploratory alongside (no verdicts):** split by label class (security vs bug); recall@1 (is the top-ranked
function a fixed one); the share of scored events where every candidate has prior = 0.

**Priors on record.** FREC-H1 **uncertain**: most functions will have prior 0, so ties pull AUC toward ½ while size
does not tie. FREC-H2 **leaning supported**.

## FREC-H1 / FREC-H2 — RESULTS (2026-11-05; registration above)

Engine `32619e4a5`, history ablated. Reports: `docs/frec_curl.md`, `docs/frec_ndpi.md`. Lift = mean within-event
AUC(score) − AUC(function loc) over scored events (the later half by date); event bootstrap; α = 0.005 one-sided.

| repo | scored events | FREC-H1 prior count | FREC-H2 (prior, then loc) | size AUC |
|---|---:|---|---|---:|
| curl | 435 | −0.126 [lo −0.155] **not supported** | −0.023, 90% CI [−0.032, −0.015] **not supported** | 0.792 |
| nDPI | 51 | −0.170 [lo −0.251] **not supported** | −0.008, 90% CI [−0.022, +0.007] **not supported** (inconclusive; just outside the ±0.02 equivalence band) | 0.865 |

**Decision rule (c) applies.** The function dossier's predictive line stays file-grain.

**Reading.** Function memory carries signal on its own (within-event AUC 0.67 on curl, 0.69 on nDPI; chance is 0.5),
but function size carries more. Within a touched file, the long function is where the fix lands, and putting prior
fixes ahead of size makes the ranking worse on curl (CI entirely below 0). Ties are not the cause: only 34/435 curl
and 8/51 nDPI events had every candidate at prior 0. File-grain recidivism replicated because it separates files that
differ hugely in size and history. Inside one file, size-by-area dominates.

**Priors vs outcome.** FREC-H1 "uncertain": not supported. FREC-H2 "leaning supported": not supported.

**Exploratory.**
- recall@1 (is the top-ranked function a fixed one?): curl 0.27 with memory first vs 0.41 for size alone; nDPI
  0.37 vs 0.33.
- The lift is negative in every curl label class (security, regression, both bug labels).
- An untested candidate: memory **per line of function** (prior fixes / loc) as a density, so that size is not
  simply re-ranked. It belongs to an unseen repo (openssl) and would need registering first.

## EA-H1..EA-H5 — effort-aware history ranking on openssl (repo #3) — registered 2026-11-05, before any openssl scan

**Why this battery.** Every recent claim lost to file size (FWD-H1..H3, FREC-H1/H2) when scored by AUC, which rewards
finding big files. The one replicated positive, file recidivism (RW-H2), was scored effort-aware: recall when
reviewing a fixed share of lines. There, prior fixes beat LOC 71–10 on curl even though LOC had the higher AUC. A
reviewer's cost is lines read, so this battery asks whether history features find fixed files **per line reviewed**.
openssl is unseen for every claim below: no openssl scan or statistic exists before this entry. The data is
`events/openssl.json` (harvest/openssl `10e6d33`; engine validated in `docs/engine_validation.md`).

**Snapshots and scans.**
- Snapshots are quarterly first-parent `origin/master` commits (`tools/fwd_snapshots.py`), from the first quarter
  with ≥ 50 C files to the last whose outcome window closes before the harvest's pool head.
- Scans use engine `e246915aa` (gitgalaxy#7818: as-of history plus persisted change entropy), `--spec-alignment`,
  and `GITGALAXY_HISTORY_ASOF=1`.
- Snapshots whose every C file reports unusable history are excluded (FWD amendment 1's rule).
- The instrument gates are binding and are checked before any EA statistic: churn reconstruction Spearman ≥ 0.95
  and HCM parity ≥ 0.99 on every snapshot, as in FWD.

**Unit and outcome.**
- Candidates are the C files (`language = 'c'`) of snapshot t.
- A file is positive if a `security-fix` event with `on_master = true`, dated (committer time) in (t, t+180 d],
  touches it (parent- or child-side path).
- Branch-only fixes are excluded: master may not carry the bug.

**Predictors (all read at t from the as-of scan, or from events strictly before t).**

| id | predictor | score (higher = review first) |
|---|---|---|
| **EA-H1** | change entropy | `change_entropy` (HCM1_LD_30) |
| **EA-H2** | churn | `raw_churn_freq` |
| **EA-H3** | recency | −`risk_stability` (within a snapshot, monotone in time since the file last changed) |
| **EA-H4** | file recidivism | number of on-master security-fix events dated ≤ t that touched the file |
| **EA-H5** | recidivism density | EA-H4 count / `total_loc` |

**Primary statistic: recall at 20% of lines reviewed.**
- Per snapshot, rank C files by the score (ties: smaller `total_loc` first, then path).
- Take whole files while cumulative `total_loc` ≤ 20% of the snapshot's total C LOC.
- recall@20 = covered positives / all positives. Only snapshots with ≥ 1 positive count.

**Baselines (a claim must beat both).**
- **LOC-desc**: largest files first, RW-H2's comparison.
- **LOC-asc**: smallest files first, the strong effort-aware baseline.

| claim | supported iff |
|---|---|
| each EA-Hk | mean over scored snapshots of [recall@20(score) − recall@20(baseline)] > 0 **against both baselines**, each with a one-sided snapshot-cluster bootstrap lower bound > 0 (5,000 rounds, seed 2982) at α = 0.01 / 5 = 0.002 |

This is an intersection-union test: both comparisons must hold, and no further correction is needed.

**Power.** Fewer than 20 scored snapshots makes the battery *not evaluable*.

**Nulls.** A *replicated null* is claimed only by equivalence: the two-sided 90% CI against the stronger baseline lies
inside [−0.02, +0.02]. Otherwise *inconclusive*.

**Secondary (descriptive, no verdicts).**
- Pooled and banded AUC against `total_loc`, as in FWD.
- recall@10 and recall@30.
- The same pipeline on curl and nDPI as labelled context: these features have been seen there.

**Decision rule.**
- (a) Any EA claim supported: open a gitgalaxy issue for an effort-aware "review budget" ranking on that feature.
  A further unseen-repo replication is registered before any score weight.
- (b) None supported, or all equivalence-null: per-file history ranking is closed as a predictive direction for this
  program. It stays descriptive.

**Priors on record.**
- EA-H4 (recidivism) **leaning supported**: it replicated effort-aware on curl and nDPI.
- EA-H3 (recency) **leaning supported**: curl exploratory.
- EA-H1, EA-H2 **uncertain**.
- EA-H5 **uncertain**: density can favour tiny files, which LOC-asc already exploits.

### EA instrument record — 2026-11-05: gate failure, engine fix, rescan (no change to any claim)

- **What happened.** The first scored run (engine `e246915aa`) failed both binding gates on openssl: churn
  reconstruction passed 108/110 snapshots (min rho 0.564) and HCM parity 107/110, on pre-2014-10, pre-2015-01 and
  pre-2015-04. As registered, all five verdicts were **withheld**.
- **I saw those withheld numbers before the fix.** For the record: prior fixes had the highest recall@20, every
  feature beat LOC-asc, and EA-H1/H4/H5 beat LOC-desc with lower bounds above 0. None of this decided anything below.
- **Cause (an engine defect, independent of any outcome).** A Latin-1 byte in openssl's 2014 commit metadata raised
  `UnicodeDecodeError` inside the chronometer's `git log` stream. The stream was abandoned and every later commit
  was silently dropped: on pre-2014-10 the window kept 333 of about 860 commits, and 194 of 325 active files read
  zero churn.
- **Fix.** gitgalaxy#7818 commit `da852aa54` decodes every git subprocess with `errors="replace"`. Its regression test
  fails on the old code.
- **The registered path ("the run stops and the instrument is fixed before anything is scored").** Every snapshot is
  rescanned at the fixed engine and the gates are rerun. Claims, statistic, baselines, α and decision rule are
  unchanged. The scored result is whatever the fixed instrument gives, including if a gate still fails.
- **Other studies.** FWD and FREC on curl and nDPI passed these gates at rho ≥ 0.99, so their history windows were
  intact. The ablated-history studies never ran the stream.

## EA-H1..EA-H5 — RESULTS on openssl (2026-11-05; registration and instrument record above)

Engine `da852aa54` (gitgalaxy#7818 with the UTF-8 fix). **Gates pass on all 110 snapshots** (churn reconstruction
min rho 0.9998, HCM parity min 0.9989). 75 snapshots have ≥ 1 positive; 252 on-master security fixes. Report:
`docs/ea_openssl.md`.

| claim | recall@20 | vs LOC-desc (0.271): lift [one-sided lo] | vs LOC-asc (0.128): lift [lo] | verdict |
|---|---:|---|---|---|
| **EA-H1** change entropy | 0.343 | +0.072 [+0.013] | +0.215 [+0.096] | **SUPPORTED** |
| **EA-H2** churn | 0.321 | +0.050 [−0.053] | +0.193 [+0.078] | not supported (inconclusive) |
| **EA-H3** recency | 0.304 | +0.032 [−0.103] | +0.176 [+0.062] | not supported (inconclusive) |
| **EA-H4** prior security fixes | 0.451 | +0.180 [+0.047] | +0.323 [+0.202] | **SUPPORTED** |
| **EA-H5** prior fixes per line | 0.451 | +0.180 [+0.054] | +0.323 [+0.204] | **SUPPORTED** |

**Robustness (post hoc, labelled as such).**
- **H5 adds nothing to H4 at the registered budget.** In 63 of 75 snapshots every file with a prior fix fits inside
  20% of lines, so both rankings select the same files. They differ at 10% (0.311 vs 0.288).
- **Not split-fix mechanics.** Only 4 of 663 positive (snapshot, file) pairs are the same CVE fixed on both sides of
  t. Removing them leaves EA-H4's lift at +0.180 (lo +0.056).
- **EA-H1's margin over LOC-desc is narrow** (lower bound +0.013).

**The size wall, re-read.** Under plain AUC, LOC still ranks best: 0.816 pooled, against change entropy 0.751,
churn 0.734, recency 0.696 and prior fixes 0.639. AUC rewards finding the big files; recall per line reviewed
rewards finding fixed files cheaply. On openssl, file history wins the second question while losing the first. That
is consistent with RW-H2 on curl and nDPI, and it says this program's earlier AUC nulls answered a different
question than a reviewer asks.

**Priors vs outcome.**
- EA-H4: leaning supported → supported.
- EA-H3: leaning supported → not supported.
- EA-H1: uncertain → supported.
- EA-H2: uncertain → not supported.
- EA-H5: uncertain → supported, but redundant with EA-H4.

**Decision rule (a) applies.** Open a gitgalaxy issue for an effort-aware "review budget" ranking on prior security
fixes and change entropy. A further unseen-repo replication is registered before either feeds any score weight.
