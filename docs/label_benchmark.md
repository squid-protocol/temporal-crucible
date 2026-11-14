# Our labellers against external ground truth (2026-11-13)

Every precision number in this programme was self-reported: we drew our own sample and judged it ourselves.
This is the first score against ground truth **somebody else validated**, on **repositories we have never
touched and never tuned on**.

Corpus: König et al. (arXiv:2609.21616), `github.com/Raubkatz/BugFixCommitLabelling`, `evaluation_data/`.
**35,167 commits across 39 SmartSHARK repositories, 7,554 real bug-fixes (21%)** — the only public corpus
with manually validated **negatives** as well as positives, which is what makes recall measurable at all.
No MongoDB restore needed: the evaluation data ships as CSV.

| labeller | precision | recall | **F1** |
|---|---|---|---|
| their mistral-small3.2:24b | 0.544 | 0.752 | **0.631** |
| their qwen3.6:35b | 0.511 | 0.782 | 0.618 |
| their qwen3.5:122b | 0.481 | 0.808 | 0.603 |
| their qwen3-coder:30b | 0.467 | 0.823 | 0.596 |
| their gemma4:12b | 0.453 | 0.819 | 0.583 |
| their codestral:22b | 0.339 | 0.911 | 0.495 |
| **OURS v2** | 0.425 | 0.397 | **0.411** |
| **OURS keyword gate** | 0.398 | 0.406 | **0.402** |
| their stemming baseline | 0.407 | 0.385 | 0.396 |
| their codegemma:7b | 0.230 | 0.984 | 0.373 |
| **OURS v3c (our "cleaned" label)** | 0.454 | 0.290 | **0.354** |

*(Our rule A — "all touched files are test/doc paths" — cannot fire here: the corpus ships messages, no file
lists. What is scored is our message rules, which is most of the gate and exactly the part the recall audit
indicted.)*

## Three things this settles

**1. We are exactly at the keyword baseline, and last overall.** Our gate scores F1 0.402 against their
stemming baseline's 0.396 — statistically the same thing. Our recall of **0.406 here** matches the 0.41 we
measured by hand on curl, from a completely different corpus and judge. The measurement was right. **Every
LLM in the table beats every keyword method.**

**2. v3c, our "improvement", is a net loss by F1.** It buys precision (0.398 → 0.454) at a brutal recall cost
(0.406 → 0.290) and lands **below the baseline we started from**. On our own self-audit v3c looked like a
clear win, because we only ever measured the half it improves. Measured on both halves against external truth,
it is the worst of our three labellers.

This does not retract the HR-1b result — a higher-precision label was the right instrument for asking whether
recidivism's effect was housekeeping. But "v3c is the better label" was never true in general, and we could
not have known that from inside our own data.

**3. The gap is recall, and LLMs close it.** The best model gets **0.752 recall at 0.544 precision** — nearly
double our recall at better precision. This is the one technique that reads the *diff* rather than the prose,
and it is the only thing in the literature that addresses our actual failure mode.

## Caveat on the precision numbers

Our self-audits put v3c at 0.70–0.86 precision; here it scores 0.454. The populations differ — our audits
sampled `other-fix` events in our own repos and judged from subjects; this corpus is issue-linked
SmartSHARK ground truth over different projects. The **recall** figures agree closely across both, so the
recall story is the robust one; treat the precision gap as a reminder that precision is defined against a
population, not in the abstract.
