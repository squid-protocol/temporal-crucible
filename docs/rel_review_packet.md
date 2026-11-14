# REL independent review packet

This packet asks for an independent, critical review of a study design before it is registered. Paste this whole
file into the reviewer, followed by the full text of the draft:
[`docs/rel_hypotheses.md`](rel_hypotheses.md) (raw, public:
`https://raw.githubusercontent.com/squid-protocol/temporal-crucible/rel-registration/docs/rel_hypotheses.md`).

Reviewers so far: Gemini 4 Argon (2026-11-13, PR #184; its fixes and the author's response are in the draft's
"Review log"). Next: a second Claude model, reviewing the current draft without reading Gemini's PR comment. Each
reviewer works without seeing the other reviews.

---

## Your role

You are reviewing a **preregistration draft** for a defensive security study. Nothing has been run. Your job is to
find what is wrong, weak or unfair in the design **before** any data is seen, so the result can be trusted whichever
way it comes out. Be specific and adversarial. Do not soften findings. Where you propose a change, write the
replacement text or formula.

Please do not assume the study should pass. A well-designed study that fails is a good outcome for this program.

## What the study is

GitGalaxy is a static code scanner that reads source text in about 60 languages without compiling or executing it.
For every file and function it records keyword-family signals (branches, loops, I/O, error exits, eval/exec, bitwise
math, decorators, tests, and so on, about 100 in all), plus imports, a call graph and complexity measures. It also
runs regex-based security rules (obfuscation, dynamic execution, disabled safety checks, self-copying code, hidden
Unicode, hard-coded secrets, high-entropy strings).

The study asks: **when an attacker publishes a compromised release of a legitimate npm or PyPI package, does that
release stand out from the package's own recent releases, as measured by GitGalaxy?** It compares each compromised
release with the same package's previous 20 releases, sets an absolute alarm threshold on popular uncompromised
packages, and scores attacks found after registration with the frozen method.

## Background facts you can rely on (with sources)

- **The security layer has no measured detection rate.** An audit of 112 security claims in GitGalaxy's docs found
  5 measured (none about detection), 44 tested only on planted inputs, 10 untested, 39 false, 14 vague
  (gitgalaxy#8426). The pattern rules miss common idioms such as Python `exec(base64.b64decode(...))`, and the engine
  skips minified files and blanks lines of 250+ characters before its security rules (gitgalaxy#8429).
- **Structural risk scores do not predict vulnerabilities.** On curl and nDPI history (about 3,550 snapshots,
  preregistered), a 26-signal structural vector gave AUC 0.479 for CVE/bug-touched files, against 0.531 for lines of
  code; the security-fix structural delta was +0.000 (TOST equivalence). A security-fix vs ordinary-fix gradient did
  not hold at patch level.
- **Code style is identifiable.** Function "shapes" (the set of signals a function uses) form a lattice with
  families. On 60 autonomous-agent programs, the family mix alone picked the authoring model's nearest neighbour 84%
  of the time (chance 28%, permutation p = 0.0005). On GitGalaxy's own history, Gemini-era vs Claude-era functions
  separated at AUC 0.88 (size-matched 0.86; a within-era drift reference gave 0.71).
- **Code is stable.** In GitGalaxy's weekly history, 88% of functions never changed shape; about 3% of
  function-weeks moved. In five C repositories, 71% of functions never changed shape.
- **Lattice change did not predict regressions** beyond churn (LAT-M1 failed: +0.5 points recall@20%).
- **Data.** DataDog's malicious-software-packages-dataset (Apache-2.0) labels compromised versions of legitimate
  packages (`compromised_lib`): about 2,074 npm names with compromised versions in the manifest, and 17 PyPI packages
  with samples. Coverage is mostly 2024 to 2026 (chalk/debug, nx, the Shai-Hulud worm, @solana/web3.js, rspack,
  Ultralytics). The dataset says its samples are mostly GuardDog detections. Older classics (event-stream,
  ua-parser-js, coa, rc, eslint-scope, ctx, xz) have no malicious artifact in it. Malicious versions are deleted from
  npm and PyPI; the clean previous versions remain downloadable.
- **Pre-assessment counts** (metadata only; in the draft's "Pre-assessment" section): 666 eligible packages; 158
  positives after a cap of 10 per campaign, in about 33 date-proxy campaigns, five of which hold 83% of all
  packages; about 8,500 calibration transitions; PyPI has only 11 capped positives. Say how your review would change
  if real payload grouping left 15 or fewer campaigns.

## What to review

Answer each. Cite the draft's section names.

1. **Construct validity.** Do C1 to C5 measure "unlike this package's habits", or something else (release size,
   build-tool changes, a new maintainer, a monorepo restructure, a major version)? Name the ordinary events most
   likely to produce false alarms on each component, especially C4 (a project switching to a bundler would add new
   minified files) and C5 (new dependencies are common in normal development).
2. **The maths.** Check:
   - the percentile definition with ties, and its behaviour for packages with 8 to 19 benign transitions;
   - the binomial chance figure (about 1e-8 for 10 of 20 packages ranking first at p = 1/21);
   - the campaign-clustered bootstrap with about 33 unequal clusters (five dominant): is it reliable, and what should replace it (wild
     cluster bootstrap, exact permutation over campaigns, a different interval)?
   - the robust z-score D with a MAD floor taken from the calibration set: is it well defined, and does averaging
     z-scores across components with very different distributions behave?
   - setting a 1-in-1,000 threshold from about 8,500 calibration transitions (about 8 to 9 exceedances): how uncertain is
     that threshold, and what does that uncertainty do to the recall estimate?
3. **The bars.** Are the pass rules for H-REL-1, H-REL-2 and H-REL-3 too strict, too lenient, or mis-specified?
   Propose alternatives with numbers.
4. **Leakage and forking paths.** Where could knowledge of the attacks, the dataset or the scanner's behaviour leak
   into the design? Is anything still a free choice that should be fixed now (window sizes, which signals count as
   security, normalization of function bodies, import normalization, the campaign rule)?
5. **Independence.** Is campaign assignment by shared payload plus a 3-day window adequate? What happens with
   worms that mutate payloads, or one attacker hitting many unrelated packages on the same day?
6. **Selection bias.** The positives are mostly GuardDog detections. What does a pass or fail on this sample let us
   conclude about attacks that GuardDog misses? Is there a design change that would make the conclusion broader?
7. **Other data.** Suggest additional or replacement datasets, with their licences for commercial research use
   (the operator is an LLC), especially for pre-2023 attacks and for a larger calibration set. Is the prospective
   set (attacks added after registration, through 2027-05-13) likely to be large enough to matter?
8. **The exploratory full-fingerprint model.** Is the campaign split sound? Is anything there likely to mislead a
   reader even though it is labelled exploratory?
9. **Comparators.** Are the install-hook rule and GuardDog the right baselines? What else should be compared, and
   at what alarm rate?
10. **Safety and ethics.** Anything in the handling of live malware samples, or in what is published, that you would
    change?

## Your forecast (please give numbers)

Before any data is seen, give your probability (0 to 100%) that each passes as currently written, and one sentence of
reasoning each:
- H-REL-1 (composite score ranks hacked releases first),
- H-REL-2 (culture-only score),
- H-REL-3 (half caught at a 1-in-1,000 alarm rate),
- the exploratory full-fingerprint model beating the fixed score on both halves.

Also give your best guess of the median within-package percentile for S and for S_culture.

## Answer format

1. **Verdict:** approve / approve with changes / redesign, in one line.
2. **Findings:** numbered, each with severity (blocker, major, minor), the section it concerns, what is wrong, and the
   exact change you propose.
3. **Maths check:** each item from question 2, marked correct or incorrect, with your working.
4. **Forecast:** the numbers above.
5. **Anything we did not ask** that you think matters.
