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

## The anonymisation check (run the same evening, after the above)

If the auditor is recognising curl rather than reading it, removing the project's identity should remove the
lift. `tools/aiat_eval.py score --anon` rewrites identifiers, field names and types to opaque tokens (stdlib
names kept, since they are part of what a C function *is*), replaces string contents, and drops comments.

**42% of the anonymised files were refused.** 417 of 988 returned `stop_reason: refusal`, category `cyber`,
with zero output tokens: opaque identifiers make benign C look like obfuscated malware to the safety
classifier. That is a property of the instrument, not an outage, and it means the survivors are **not a random
sample**. The comparison below is therefore restricted to the **571 files scored in both runs**, so each run
faces the same files and the same positives.

| | plain | anonymised |
|---|---|---|
| beats the stronger size order, within bands | **2 / 3** | **2 / 3** |
| band 0 — 459 files, 25 pos | 0.400 vs 0.200 | **0.320** vs 0.200 |
| band 1 — 77 files, 24 pos | 0.375 vs 0.250 | **0.292** vs 0.250 |
| band 2 — 35 files, 24 pos | 0.208 vs 0.250 | 0.208 vs 0.250 |
| names the project | 96.7% | **44.5%** |
| mean score | 0.305 | 0.283 |
| `spearman(score, log loc)` | +0.667 | **+0.868** |

**The lift survives.** The same bands are won and the same band is lost, with the magnitude attenuated about
20%. The two runs' per-file scores correlate at **r = +0.829**. With recognition more than halved, the
instrument did not collapse — which was the live alternative and the reason for running this.

### What it does not settle

1. **Recognition was halved, not removed.** The anonymiser does not rewrite include paths, so
   `#include <curl/curl.h>` survives verbatim — which is why 44.5% of reasons still name the project. A
   one-line fix, and the next arm should carry it.
2. **The 42% refusal rate biases the surviving set**, in an unknown direction. Both runs share the same 571
   files, so the *comparison* holds; the *generalisation to curl* does not.
3. **Comments were stripped along with identity**, so this is a combined ablation. AIAT-P4 (comment-only)
   separates the two and has not been run.
4. **The attenuation is consistent with recognition contributing part of the lift** — 0.400 → 0.320 and
   0.375 → 0.292 are not nothing. It is also consistent with the loss of comments. Nothing here separates
   those two.

**Status: the attention reading survived its hardest test so far, and is not established.**

## Reading

- **The gate passes.** The auditor is not *merely* a size proxy: inside every size band it beats the stronger
  size ordering, on powered cells.
- **The class prediction, registered before scoring, holds.** That is the result worth keeping, because it
  was falsifiable and could have come out flat.
- **The anonymisation check was run, and the lift survived** (section above): 2 of 3 bands either way on the
  571 files both runs scored, attenuated ~20%, scores correlated at r = +0.829, with recognition down from
  96.7% to 44.5%. That removes the simplest deflationary reading, and does not establish the attention one —
  recognition was halved rather than removed, and 42% of files were refused as `cyber`.
- **The next arm is still an instrument check, not a panel**: anonymise include paths too (the leak that kept
  recognition at 44.5%), and reframe the prompt to defuse the cyber classifier, or expect to lose 40% of the
  sample again.
- AIAT-P2 (run-to-run reliability), P3 (cutoff contrast) and P4 (comment-stripped ablation) have **not** been
  run. The anonymisation check above should come first, since it decides whether the others are worth paying
  for.

## What this does not establish

Nothing about the ceiling. AIAT-P5 was not run, and would be descriptive on two excluded development repos
anyway. A passed gate is a licence to design the attention study, not a result about software — and with
recognition at 96.7%, not yet even that.
