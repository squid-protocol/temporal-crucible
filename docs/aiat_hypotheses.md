# AIAT-P — can an LLM auditor applying uniform attention be used as a measuring instrument? — registered 2026-11-11

**Type: descriptive (instrument calibration). No verdicts, no law statistic, no p-value is claimed from it.**

**Status: filed 2026-11-11 at the owner's instruction to start the study. Owner OK on this text is still
outstanding — nothing below had been computed when this was committed, and no scoring run starts until the text is
approved.** The cost probe (§7) is the only step that may run before approval, because its purpose is to tell the
owner what the study would cost.

**Repos:** `curl/curl`, `ntop/ndpi` — both in `tools/laws_exclude.py:EXCLUDED_REPOS`, so nothing learned here can
contaminate the LAWS panel or its registration. **Tool:** `tools/aiat_eval.py` (written after this commit).

## 1 · Why this exists

`docs/ceil.md` measured the prediction ceiling on 57,057 file-years and then re-ran it on clean labels:

- out-of-repo recall at a 20%-of-lines review budget: **0.30 achieved · 0.47 attainable with these covariates ·
  0.68 with perfect rate knowledge**;
- cleaning the `other-fix` labels from 0.558 to 0.761 precision bought **3–4 points** of realized performance and
  left the **~22-point** oracle gap untouched — labels are a tax, not the wall;
- dispersion **rose** with cleaner labels (`alpha` 1.281 → 1.378), against the prediction on record. Lint, javadoc
  and formatting commits spread evenly across a codebase and were *diluting* concentration, so label noise was
  **masking** rate heterogeneity rather than manufacturing it.

That forecloses the comfortable reading. The residual is real signal, and only two explanations survive: covariates
that exist and are unused, or the **discovery/attention process** — which files people happen to look at. Historical
data cannot separate them, because every historical fix is the product of someone's attention.

An auditor that applies the **same** attention to every file is the one instrument that can. Before it can measure
anything, it has to be shown to be a ruler and not a second size proxy. **That, and only that, is what AIAT-P does.**

## 2 · Prior work (checked 2026-11-11, before any statistic)

- **Bird, Bachmann, Aune, Duffy, Bernstein, Filkov and Devanbu, "Fair and Balanced? Bias in Bug-Fix Datasets",
  ESEC/FSE 2009, pp. 121–130, doi 10.1145/1595696.1595716.** Found systematic bias in which bug fixes reach
  historical datasets, and argued it threatens both models built on them and hypotheses tested on them. This is the
  canonical statement of the problem AIAT exists to attack: the record reflects attention, not incidence. AIAT's
  difference is that it tries to *measure* the attention channel rather than correct for it statistically.
- **Ding, Steenhoek et al., "Vulnerability Detection with Code Language Models: How Far Are We?", ICSE 2025,
  pp. 1729–1741, doi 10.1109/ICSE55347.2025.00038 (arXiv 2403.18624).** Built PrimeVul (6,968 vulnerable and
  228,800 benign functions) and found code LMs collapse on it — one 7B model fell from ~68% F1 on BigVul to ~3% on
  PrimeVul; GPT-3.5 and GPT-4 were near random in the strictest settings. They also measured up to **18.9% test-set
  leakage** in existing benchmarks and recommended chronological splits. **Consequence for us:** the registered
  expectation is that the auditor is a *weak* instrument. A null is the likely outcome and is not a failure.
- **Steenhoek et al., "To Err is Machine: Vulnerability Detection Challenges LLM Reasoning", arXiv 2403.17218**
  (venue not verified). Best models reached ~54.5% balanced accuracy; better prompts, larger models and fine-tuning
  did not move it much. Reinforces the weak-instrument prior.
- **Riddell, Ni and Cohan, "Quantifying Contamination in Evaluating Code Generation Capabilities of Language
  Models", ACL 2024, pp. 14116–14137.** Measured surface and semantic overlap between benchmarks and pretraining
  corpora and showed models do markedly better on problems whose solutions they have seen. **Consequence for us:**
  contamination must be handled by design (§5), not asserted away.
- **This program.** `docs/ceil.md` (the ceiling and the label re-run), `docs/scar.md` (SCAR-I2: danger comments at
  birth predict first CVE fix at 1.55×, lower bound 1.04, in files with no prior CVE — a scored, confound-controlled
  *human* attention signal on these same repos), `docs/otherfix_audit.md` (the label-precision audit), and the
  AG-H1..H3 self-scan replay, whose n = 1 per arm is the design error this registration exists to avoid repeating.

**Where this sits:** every paper above asks whether a model can *classify* a known-vulnerable function. AIAT-P asks
something weaker and different — whether a model's per-file risk ordering, applied uniformly, carries rate
information that history-based covariates do not. A model can be bad at the first and useful for the second.

## 3 · Frozen inputs

| repo | snapshot (scored tree) | pool_head (outcome window ends) | `.c`/`.h` files at snapshot |
|---|---|---|---|
| curl | `032b15c4342e8eddb51fbe089a9d8ba3ee2070fb` (2026-06-01) | `a0c990c819` (2026-10-22) | 988 |
| nDPI | `7b43393d8a36cf71b61f582093b1185c4ed0b0b9` (2026-06-01) | `2b8c2989f` (2026-10-20) | 426 |

The snapshot is **2026-06-01**, after the auditor's May 2026 knowledge cutoff, so every outcome in the window
post-dates what the model could have memorized. Both SHAs are pinned here before any scoring; the window end is the
pool clone's head, not "today", so it cannot be stretched after seeing results.

**Measured outcomes (2026-11-11, `tools/aiat_eval.py sample`, the registered v3c rule applied through
`fixlike_v2.drop_reason`):**

| repo | commits in window | v3c fix commits | files fixed | positive rate |
|---|---|---|---|---|
| curl | 1,391 | 112 | **85 of 988** | **8.6%** |
| nDPI | 152 | 30 | **35 of 426** | **8.2%** |

**nDPI is declared direction-only in advance** and no nDPI number will be reported as a result in its own right.

**Erratum (2026-11-11, before any scoring).** An earlier draft of this section put curl's positive rate at 30%,
from a subject grep used for sizing. The registered v3c rule is far stricter — it drops 972 of curl's 1,391 window
commits for carrying no fix word in the subject — and the true rate is **8.6%**. The 30% figure was never used for
anything but sizing, and §6 is corrected below accordingly. No outcome had been scored when this was found.

## 4 · The instrument

The auditor sees **one file's source at the snapshot tree and nothing else**: no git history, no commit messages, no
sibling files, no issue text, no file path beyond the basename. It returns a calibrated risk score in [0, 1] for
"this file receives a bug fix in the next six months", with a one-sentence reason. Every file gets the **same**
prompt, the same budget and the same model, in a fixed order. Uniform attention is the whole instrument: the
covariate model sees history and structure, this sees only code.

## 5 · Registered checks, each with its kill criterion

| id | question | method | kill criterion, stated in advance |
|---|---|---|---|
| **AIAT-P1** | is it a size proxy? | Spearman ρ(score, log LOC); recall@20%-of-lines **within** LOC strata (0.25-decade bins) | if the within-stratum ordering adds nothing over LOC, the auditor is a size proxy and the attention design needs a different instrument. **This is the gate; the rest are diagnostics.** |
| **AIAT-P2** | is one run repeatable? | 100 files scored 5× at shipped settings; rank correlation between independent runs, plus ICC | ρ < 0.7 between runs ⇒ no single-run score can carry a verdict, and a panel version needs k replicates per file (k× the cost) |
| **AIAT-P3** | how much does contamination buy? | the same protocol on a **pre-cutoff** window with two auditors of different cutoffs (one clean for that window, one not) | if the contaminated auditor beats the clean one on pre-cutoff fixes **and** matches it post-cutoff, contamination is bounded; if it wins on both, the design is post-cutoff-only forever |
| **AIAT-P4** | is it reading human comments back to us? | score a comment-stripped copy of the same files; correlate scores with SCAR's danger-comment-at-birth signal | ρ ≈ 1 with the comment signal, or collapse when comments are stripped ⇒ it is an echo of human judgment, not an independent channel. ρ ≈ 0 with both predictive is the most interesting outcome available here |
| **AIAT-P5** | does it see anything the covariates don't? | add the score to CEIL's negative-binomial as one covariate, `log(loc)` kept as the exposure offset; report the change in out-of-repo recall@20% and in `alpha` | descriptive only. No claim is made about the ~22-point gap from this pilot |
| **AIAT-P6** | what would it cost at panel scale? | measured tokens and dollars per 1,000 files from the cost probe | sets whether a panel version is 112 repos, 10, or none |

**Reported, never used as a filter:** per-file score distribution, refusal and parse-failure rate, and the
auditor's own stated reasons for the top-ranked files (as text, for a human read).

## 6 · Sampling and power — corrected from the measurement

**The whole snapshot universe is scored, not a sample: curl 988 files, nDPI 426.** Two reasons, both measured
before any scoring:

- At the real 8.6% positive rate, a 400-file sample holds ~34 positives. Spread over ten LOC deciles that is ~3 per
  cell, nowhere near the program's **≥20-positives-per-cell** rule, so the AIAT-P1 gate would have been
  uncomputable as originally written.
- The whole universe costs **$7.86 (curl) + $5.27 (nDPI) = $13.13** through the Batches API — inside the §7 gate —
  so there is no reason to pay sampling error for a saving the budget does not need.

**The AIAT-P1 gate is evaluated over three equal-count LOC bands, not ten deciles.** curl's 85 positives give ~28
per band, which clears the ≥20 rule; deciles would give ~8. Deciles are still reported, descriptively, and any band
holding fewer than 20 positives is printed as **UNDERPOWERED** rather than read as a result. nDPI's 35 positives
give ~12 per band and clear the rule nowhere — exactly why it is direction-only.

`--n` still subsamples, for a cheap smoke run; it is not the registered configuration.

## 7 · Cost gate

The experiment framework requires a stated cost and a 6-month payoff of ≥ 3× cost including slot-hours at $10, with
a $40 ceiling.

**Measured exactly 2026-11-11** with `messages.count_tokens` (free) over every file, `claude-opus-5`, Batches API
at 50% — this replaces the earlier character-based estimate, which was **1.74× optimistic** (C source tokenises
denser than 3.5 chars/token):

| item | files | input tokens | batch cost |
|---|---|---|---|
| curl, whole universe | 988 | **4,330,051** | **$12.31** |
| nDPI, whole universe | 426 | **3,238,793** | **$8.74** |
| AIAT-P2 reliability (100 files × 5 runs) | 500 | ~2.2M | ~$5.50 |
| **total before the P3 contrast** | | | **≈ $26.50** |

That fits the $40 cap but no longer comfortably: the AIAT-P3 contrast run must be sized against what is left,
roughly $13, rather than assumed. If P3 cannot fit, it is deferred and said to be deferred — the cap is not
renegotiated after the fact. Scoring goes through the Batches API because latency is irrelevant to a pilot and it
halves the bill.

## 8 · What this cannot establish

It cannot measure the attention process; it can only say whether the instrument that *would* measure it is a ruler.
It cannot test any LAW. It cannot support a claim about the ceiling gap: AIAT-P5 is descriptive and runs on two
excluded C repos, which are development data by construction. A positive AIAT-P1 is a licence to design the real
study, not a result about software.

## 9 · Decision rule after the pilot

- **AIAT-P1 passes and P2 ≥ 0.7** → design the attention study proper, as a fresh registration, with the auditor's
  measured size bias and replicate count built in from the start.
- **AIAT-P1 fails** → the uniform-attention instrument is a size proxy. Record it, stop, and say in `docs/ceil.md`
  that the headroom's attention explanation remains untestable with this instrument.
- **AIAT-P1 passes, P2 < 0.7** → re-cost with replicates before anything else; a k× cost may fail the framework gate
  on its own, which is a legitimate stopping point.

The window for the real study closes as repo histories fill with AI-found fixes and human discovery stops being
separable. Note that the two clocks run opposite ways: the contamination-free **scoring** window grows with time,
while the human-discovery-only window shrinks. Only the second is the expiry.
