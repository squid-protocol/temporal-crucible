# ENV-H1..H3 — platform-conditional density vs fix classes: harfbuzz (SCORED)

- labels `events/harfbuzz_xc.json` (rules v2, exts .c,.h,.cc,.hh,.cpp,.hpp): extrinsic 155, regression 480, other-fix 3662
- 62 quarterly snapshots; files with any platform conditional: median 4.8%

| claim | n | mean | lo (α=0.0033) | 90% CI | verdict |
|---|---:|---:|---:|---|---|
| **ENV-H1** | 57 | +0.173 | +0.028 | [+0.085, +0.261] | **SUPPORTED** |
| **ENV-H2** | 56 | +0.269 | +0.092 | [+0.166, +0.379] | **SUPPORTED** |
| **ENV-H3** | 57 | +0.193 | +0.045 | [+0.106, +0.278] | **SUPPORTED** |

Mean lift by class: extrinsic +0.173, regression -0.093, other-fix -0.018

Runtime 2s · bootstrap 5000 rounds over snapshots, seed 2982.
