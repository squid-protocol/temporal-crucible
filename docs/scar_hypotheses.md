# SCAR — what do the danger comments that fixes leave behind mean? — registered 2026-11-11 (owner OK), before any statistic

**Status: registered (owner OK 2026-11-11).** Nothing below had been computed when this was committed. The scorer
is written after this commit and follows it as written.

**Why.**
- **CF-H1 (2026-11-06, supported):** CVE fixes add danger-worded comments 1.61× as often as ordinary fixes (8.8% vs
  5.4%, commit grain, patch-size strata). So fixes leave **scars**: warnings written into the code at repair time.
- **DC-2:** functions *born* with danger comments reach a first CVE fix 1.45× as often as plain-commented ones.
- **Two questions follow, and the owner asked for both (2026-11-11):**
  - **(R) Do scars mark lasting fragility?** After a CVE fix, is a function whose fix added a danger comment more,
    or less, likely to need another fix? "More" means the warning flags code that stays fragile. "Less" means the
    lesson stuck.
  - **(I) Is DC-2's birth signal partly inherited scar tissue?** Danger comments at birth may echo the file's past
    CVE fixes rather than foresight. If DC-2's link holds in files with **no** prior CVE fix, the authors' warnings
    carry information beyond history.
- DCS (2026-11-11) found that nothing structural separates the danger-commented functions that get CVEs. Scars and
  history are what is left to examine.

## Prior work

- **This program.**
  - CF-H1: CVE fixes add danger comments, at commit grain.
  - DC-2 / DC-R: danger comments at birth predict first CVE fix; not replicated on unseen repos (inconclusive).
  - COM-H4: drifted headers had *fewer* CVEs (0.67, wrong direction), which looks like edits following security
    attention.
  - DCS: no birth-time code signature within the danger cohort.
- **Fluri, Würsch and Gall, "Do Code and Comments Co-Evolve? On the Relation between Source Code and Comment
  Changes", WCRE 2007, doi 10.1109/WCRE.2007.21.** Across ArgoUML, Azureus and JDT Core, 97% of comment changes
  happened in the same revision as the code change, and new code was rarely commented. Comments written at fix time
  are therefore the norm, not noise.
- **Ibrahim, Bettenburg, Adams and Hassan, "On the relationship between comment update practices and software
  bugs", JSS 85(10), 2012, doi 10.1016/j.jss.2011.09.019.** In FreeBSD, PostgreSQL and Eclipse, comment-update
  practices helped explain future bug fixes at subsystem grain.
- **Díaz Ferreyra et al., "What Can Self-Admitted Technical Debt Tell Us About Security? A Mixed-Methods Study",
  MSR 2024.** Developers leave security pointers in comments to flag fragile code (201 security-SATD observations,
  nine disclosure motives). Neither this study nor the next tracks what happens to such code afterwards.
- **Li and Paxson, "A Large-Scale Empirical Study of Security Patches", CCS 2017.** Security patches are smaller and
  more localized than other bug fixes. That is why edit size is a stratum here.
- **This study's difference:** function grain; the scar is tied to a specific CVE repair; the outcome is the same
  function's *later* fixes. It **extends** Ibrahim et al. (comment changes → later bugs) to security repairs, and
  **tests** Díaz Ferreyra et al.'s "flagging fragile code" motive prospectively.

Checked 2026-11-11 against the published records (titles, venues, the claims quoted). The result doc re-checks any
claim it leans on.

## Common definitions

- **Comment lines of a function version:** DC's span (`dc_eval.comment_task`): engine positional comment lines inside
  the function plus the block directly above. Whitespace-normalised; ≥ 3 characters (CFIX's normalisation).
- **Danger line:** a comment line with ≥ 1 match of DC's fixed lexicon `dc_eval.DANGER` (unchanged).
- **Fix events and mapping:** `chg_eval.fix_events` / `map_fix`. Classes: latent (CVE), other-fix, regression,
  extrinsic. Function identity over time: `ints_eval.lives` (rename-by-unique-name tracking).
- **File-cluster bootstrap:** 2,000 rounds, seed 2982, resampling files.
- **α = 0.01/4** for the four claims below (Bonferroni).

## Part R — do scars mark lasting fragility?

**Units.** Each function's **first CVE fix** (latent) in curl, OpenSSL, nDPI, harfbuzz and libarchive. The function
must be found by name in both the parent and the fix commit.
- Units whose function cannot be located after the fix are excluded and counted.
- The first CVE fix only: one unit per function.

**Exposure, the scar.** The fix commit's version of the function has ≥ 1 danger line whose normalised text is
absent from the parent version.

**Outcomes** (follow-up from the fix, ends at function death, label end, or 5 years, whichever comes first):
- **R1:** a later CVE fix to the same function.
- **R2:** a later fix of any class (latent, other-fix, regression, extrinsic) to the same function.

**Test.** MH rate ratio (events ÷ person-time) of scarred vs unscarred units (`ints_eval.mh_rate`). Strata:
- repo;
- log₁₀ loc of the function before the fix (0.25-decade bins);
- edit size: lines the fix changed inside the function (bins 1–2, 3–8, 9–32, > 32).

| id | claim (two-sided) | bar |
|---|---|---|
| **SCAR-R1** | a scarred CVE fix is followed by a later CVE fix at a different rate than an unscarred one | 99.75% bootstrap CI of the RR excludes 1. Direction named in the verdict: > 1 lasting fragility, < 1 lesson learned |
| **SCAR-R2** | the same for a later fix of any class | same |

**Power rule:** ≥ 15 outcome events among scarred units *and* among unscarred units. Otherwise the claim is
**underpowered**, not a verdict.

**Descriptive:**
- the same RRs for scars left by *other-fix* repairs (are CVE scars special?);
- the share of scars still present at the function's last snapshot;
- the top 10 scar words.

## Part I — is DC-2's birth signal inherited scar tissue?

**Units.** DC-2's births, unchanged: curl, OpenSSL, nDPI and harfbuzz; born after the first snapshot; loc ≥ 3;
≥ 1 comment line at birth. Danger-commented vs plain-commented as in DC-2.

**History.** "Prior-CVE file" = the file had a CVE fix before the birth (DC-2's stratum variable).

| id | claim | test | bar |
|---|---|---|---|
| **SCAR-I1** | danger-commented births are over-represented in prior-CVE files | MH OR of danger (vs plain) in prior-CVE vs other files, strata repo × log₁₀ loc (0.1 decade), two-sided | 99.75% CI excludes 1; direction named |
| **SCAR-I2** | DC-2's link holds without history: among births in files with **no** prior CVE fix, danger-commented functions reach a first CVE fix more often than plain-commented ones | DC-2's MH rate ratio restricted to prior-CVE = no, strata repo × loc bin, whole life as in DC-2, one-sided | lower bound (α = 0.0025) > 1 |

- **Power rule (I2):** ≥ 15 first-CVE events among danger-commented births in no-prior-CVE files.
- **Reading:**
  - I2 supported: the warnings carry foresight beyond inherited history.
  - I2 not supported but the whole-cohort DC-2 estimate holds: the signal lives in files with a past.
  - I1 says how much danger wording simply clusters where CVEs already happened.

**Descriptive:**
- DC-2's rate ratio in prior-CVE files (the complement of I2) and the ratio of the two;
- **textual inheritance:** the share of danger-commented births with a danger line whose normalised text matches a
  danger line *added by an earlier CVE fix* anywhere in the same repo (copied scars).

## Data honesty

- **Part I reuses DC-2's sample.** The split by prior-CVE file has not been computed. DC-2's code adds `prior` only
  as a stratum, and its report prints no per-stratum rate. Part R uses functions and outcomes not analysed before at
  this grain. CF-H1 was at commit grain and had no follow-up.
- No statistic in this document has been computed. Wave A, CMR, COM-H4 and DCS read neither the scar exposure nor
  the follow-up fixes.

## Priors

- **R1, a coin flip with a lean to > 1.** COM-H4's wrong-direction drift result suggests that comment edits follow
  security attention. A scar marks code the maintainers know is delicate, so later CVEs (variants, incomplete fixes)
  are plausible.
- **R2 likely > 1, but edit size absorbs much of it.** Bigger repairs are both more commented and more often
  followed by fixes.
- **I1 likely > 1.** I2 is the informative one, and it may be **underpowered**: DC-2 had 144 first-CVE events among
  danger-commented births in all files.
- **Part R power is the main risk.** About 9% of CVE fixes leave a scar (CF-H1), so scarred units may number only in
  the tens. The power rules make "underpowered" an honest outcome.

## Known limits

- Scars are detected by DC's lexicon. A scar written without those words is missed; that biases toward the null.
- Function identity across the fix uses names. Functions renamed by the fix are excluded (counted).
- Edit size is measured inside the function only. Fixes that span many functions are not otherwise distinguished.
