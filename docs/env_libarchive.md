# ENV-H1..H3 — platform-conditional density vs fix classes: libarchive (SCORED)

- labels `events/libarchive_xc.json` (rules v2, exts .c,.h): extrinsic 468, regression 104, other-fix 1509
- 72 quarterly snapshots; files with any platform conditional: median 22.0%

| claim | n | mean | lo (α=0.0033) | 90% CI | verdict |
|---|---:|---:|---:|---|---|
| **ENV-H1** | 69 | +0.123 | +0.031 | [+0.067, +0.181] | **SUPPORTED** |
| **ENV-H2** | 34 | +0.296 | +0.045 | [+0.142, +0.450] | **SUPPORTED** |
| **ENV-H3** | 69 | +0.157 | +0.061 | [+0.098, +0.217] | **SUPPORTED** |

Mean lift by class: extrinsic +0.123, regression -0.098, other-fix -0.031

Runtime 2s · bootstrap 5000 rounds over snapshots, seed 2982.
