# Label RECALL — measured for the first time (2026-11-13)

Every audit in this programme measured **precision**: of the commits we call fixes, how many are real. None
measured **recall**: of the real fixes, how many do we catch. This is that measurement.

Method: draw from the commits the label calls **not** a fix (seed 2986, 40 per repo), judge each with the
same rule the precision audits use — *does this commit repair behaviour that was wrong?* — and estimate

    true fixes ≈ P·p + N·q        recall ≈ P·p / (P·p + N·q)

where P is the labelled-fix count, p its audited precision, N the not-fix pool and q the sampled rate of real
fixes inside it. Unlike the precision audits, judging here used the **subject and the body** (`hist_meta.py`),
which is strictly more evidence.

## Result

| repo | q (missed rate) | est. real fixes missed | est. caught | **recall** | 95% CI |
|---|---|---|---|---|---|
| **curl** | 7/40 = 0.175 | 5,844 | 4,100 | **0.41** | [0.30, 0.68] |
| **commons-lang** | 3/40 = 0.075 | 654 | 227 | **0.26** | [0.14, 1.00] |

**The keyword label misses most real fixes.** curl catches roughly four in ten; commons-lang roughly one in
four. The tuning-set figure of ~0.81 that has stood in for recall until now was measured on the set the rules
were built from and does not survive contact with a fresh sample.

## What the missed fixes look like

They are not noise, and that is the problem. From curl's sample, all of these are real repairs the label
rejected:

- `smtp: result of Curl_bufq_cread was not used` — an ignored return value
- `urlapi: avoid derefencing a possible NULL pointer` (Coverity CID 1439134)
- `multi_poll: avoid busy-loop when called without easy handles attached` (Fixes #4594)
- `cyassl: adapt to libraries without TLS 1.0 support built-in`
- `openldap: several minor improvements` — URL syntax checks, a stack-buffer removal

None contains a fix word in the subject. The rule that most raised precision — v3c's rule C, *require a fix
word in the subject* — is precisely the rule that discards these. **Precision was bought with recall, and the
price was never counted until now.**

## Why this matters to the claims

The outcome variable in every file-year model is "was this file fixed in the window". If the label catches
41% of fixes in curl and 26% in commons-lang, that outcome is a **minority sample of the real thing**, and the
missing majority is selected by writing style — which author, which subsystem, which era prefers to say "fix"
in a subject line. That is not plausibly independent of how often a file is touched, so it is not the
benign, effect-attenuating kind of noise.

**Specifically:** the curl re-run reported a surviving lift of **+0.071** on a 0.80-precision label. That
label's recall is ~0.41. The lift is measured against the 41% of fixes whose messages announce themselves, and
nothing in the design rules out that recidivism is partly tracking *which files attract announcement-style
commits*.

## Limits of this measurement

- **n=40 per repo.** The intervals are wide, and commons-lang's upper bound is 1.0 because k=3 puts q's lower
  bound near zero. These are order-of-magnitude numbers: "most fixes are missed", not "recall is 0.41".
- **Judging is mine, from message text.** Borderline calls move the number: curl is 7/40 on an inclusive
  reading and 4/40 on a strict one, which puts recall between **0.41 and 0.55**. Low either way.
- **Measured against the raw label.** v3c keeps ~55% of raw fix commits, so its recall is **lower still** —
  unmeasured, but bounded above by these figures.

## What follows

1. **Stop quoting ~0.81.** It is a tuning-set number and it is wrong on fresh data.
2. **A cascade label is now clearly worth building** — revert links, issue references and CVE ids are already
   harvested for all 11 repos (`hist_meta.py`) and need no keyword at all. They should rank above the keyword
   gate, not below it.
3. **Recall belongs on the LABEL CARD** beside precision, with the same gate discipline. A label at 0.80
   precision and 0.41 recall is not "fit"; it is fit for one thing and unfit for another, and the card should
   say which.
