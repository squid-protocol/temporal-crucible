# AIAT-P — the uniform-attention auditor, scored (DESCRIPTIVE)

Registration: [`aiat_hypotheses.md`](aiat_hypotheses.md) (merged before any file was scored; AIAT-P7 and the
two gate corrections registered 2026-11-11, also before scoring). **Descriptive: no verdicts, no law
statistic, no p-value is claimed.** Tool: `tools/aiat_eval.py`. Auditor `claude-opus-5` (May 2026 cutoff,
before the 2026-06-01 snapshot), Batches API. Run 2026-11-11.

**Cost (AIAT-P6): $17.07** — 6,405,532 input and 84,168 output tokens over 1,408 files, batched at 50%.
Against the $40 framework cap and the $21.05 pre-run estimate.

## AIAT-P1 — is it a size proxy? **It passes the gate, and the pooled number hides why**

curl, 988 files, 85 positive (8.6%). Recall at a 20%-of-lines budget, against **the stronger of the two size
orders**:

| | score order | size order | |
|---|---|---|---|
| pooled | 0.176 | 0.141 (small-first) | a thin win |
| **band 0** (828 files, 29 pos) | **0.552** | 0.276 | score, 2× |
| **band 1** (116 files, 28 pos) | **0.286** | 0.250 | score |
| **band 2** (44 files, 28 pos) | **0.250** | 0.214 | score |

**3 of 3 bands, all clearing ≥ 20 positives.** The registered kill criterion was "adds nothing over LOC
within strata"; it is not met, so the gate passes.

The pooled figure is weak because **`spearman(score, log loc) = +0.667`**: the auditor ranks large files
high, and large files eat a line budget. Its discrimination is real but it is *inside* size bands, not across
them. On nDPI the pooled score **loses** outright (0.273 against 0.333) while still beating size in 3 of 3
bands — all underpowered at 11 positives each, so nDPI remains direction-only as registered.

## AIAT-P7 — where the lift lands, predicted before scoring. **Supported**

Registered in advance: *if the auditor measures attention rather than code risk, lift(latent) >
lift(regression)* — largest where a defect must be looked for, near zero where it announces itself.

| class | positives | score | size | **lift** |
|---|---|---|---|---|
| **latent** | 31 | 0.290 | 0.226 | **+0.065** |
| extrinsic | 19 | 0.263 | 0.263 | +0.000 *(underpowered)* |
| **regression** | 31 | 0.226 | 0.258 | **−0.032** |
| other-fix | 284 | 0.077 | 0.331 | −0.254 |

**lift(latent) +0.065 > lift(regression) −0.032.** The ordering is exactly the registered prediction, and the
auditor is *worse than size* on the two classes where attention should not help: self-announcing regressions,
and the `other-fix` residual of lint, typos and refactors.

## The finding that qualifies both results: the auditor is not blind

The prompt withholds the project name. The code does not. **The auditor names the project in 96.7% of its
curl reasons and 82.4% of its nDPI reasons** (measured from the saved `why` strings, at no extra cost).

The May 2026 cutoff protects the **outcome** — no June–October 2026 fix can have been memorised. It does
nothing about the **predictor**: a model that recognises curl can recall which of its files churn, which is
precisely the history signal "uniform attention, no history shown" was built to exclude.

So P1 and P7 are both consistent with two readings that this run cannot separate:

1. the auditor reads the code and sees risk structure; or
2. the auditor recognises the project and recalls its reputation file by file.

Reading 2 explains the +0.667 size correlation and the within-band lift equally well, and it would also
produce the P7 class pattern if memory of a project is richer for the quiet, long-lived files that latent
fixes land on.

## Reading

- **The gate passes.** The auditor is not *merely* a size proxy: inside every size band it beats the stronger
  size ordering, on powered cells.
- **The class prediction, registered before scoring, holds.** That is the result worth keeping, because it
  was falsifiable and could have come out flat.
- **Neither supports scaling up yet.** At 96.7% recognition the instrument measures "what this model knows
  about curl" at least as plausibly as "what uniform attention sees". The next step is an **instrument
  check, not a panel**: score anonymised copies (identifiers and strings rewritten) and see whether the
  within-band lift and the class pattern survive. If they do, the attention reading stands up; if they
  collapse, the auditor was reading its own memory and the whole approach needs a different instrument.
- AIAT-P2 (run-to-run reliability), P3 (cutoff contrast) and P4 (comment-stripped ablation) have **not** been
  run. The anonymisation check above should come first, since it decides whether the others are worth paying
  for.

## What this does not establish

Nothing about the ceiling. AIAT-P5 was not run, and would be descriptive on two excluded development repos
anyway. A passed gate is a licence to design the attention study, not a result about software — and with
recognition at 96.7%, not yet even that.
