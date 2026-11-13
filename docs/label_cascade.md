# The cascade fix label — and what it already taught us

The keyword gate was measured at **0.41 recall on curl, 0.26 on commons-lang** (`recall_audit.md`): it misses
most real fixes, and it misses them by *writing style*. The cascade ranks structured evidence above the
keyword, because a revert or a `Fixes #N` does not care how the subject was phrased.

`tools/label_cascade.py`. A commit takes the **highest** tier it matches and the tier travels with the label,
so each rung carries its own precision instead of hiding inside one number.

| tier | evidence | why it ranks there |
|---|---|---|
| **T1** revert | `This reverts commit <sha>` | something was wrong enough to undo; xc audits revert-regression at 0.73–0.87 |
| **T2** fixref | `Fixes #N` / `Resolves #N` | the message *claims a defect*, by verb |
| **T3** cve | a CVE id | rare, near-certain |
| **T4** keyword | the v3c gate | measured: 0.70–0.86 precision, 0.41 recall |
| **T5** bareref | a bare `#N` or `Closes #N` | **mostly workflow noise — normally exclude** |

## The split between T2 and T5 is the first thing this cascade taught us

The first build treated *any* issue reference as one tier. It labelled **14,376** curl commits — four times the
keyword gate — which looked like a huge recall win. Sampling 9 of the commits it added, **only about 2 were
real fixes.** curl writes `Closes #N` on every merged PR: that is a workflow artefact, not a bug signal.

The data showed its own fix. These two lines mean different things:

```
Fixes #8894          <- claims a defect
Closes #8914         <- names the PR
```

Separating them collapses curl's T2 from 14,376 to **2,013** and quarantines 12,247 commits at T5, where a
study can and normally should drop them. **A broader label is not a better one, and the audit is what told
them apart.**

## What the strong tiers recover

T1–T3 only — revert, fix-reference, CVE — against the v3c keyword gate:

| repo | strong (T1–T3) | **missed by the keyword gate** | keyword (v3c) | union |
|---|---|---|---|---|
| curl | 2,241 | **1,930** | 3,570 | 5,500 |
| sphinx | 1,456 | **1,178** | 1,702 | 2,880 |
| postgres | 620 | 486 | 9,156 | 9,642 |
| redis | 262 | 156 | 2,091 | 2,247 |
| commons-lang | 59 | 53 | 389 | 442 |

curl gains **1,930 high-confidence fixes the keyword gate never saw** — a 54% increase on its keyword label,
from evidence that needs no judgement about phrasing. sphinx gains 1,178, a 69% increase.

## Status, stated honestly

**The cascade is not yet a better label — it is a broader one with its tiers separated.** What is still owed:

1. **Per-tier precision audits.** T1, T2 and T3 each need their own sample (`--sample T1 --repo curl
   --new-only`). Only T4 has a measured number today.
2. **Issue resolution.** T2 reads the *verb*, not the issue. Reading the referenced issue's labels through
   the forge API would make it near-ground-truth, and would also rescue the part of T5 that references a real
   bug. This is the single biggest upgrade available and it is not built (`--resolve`).
3. **Recall of the cascade itself**, measured the way `recall_audit.md` measured the keyword gate's.
