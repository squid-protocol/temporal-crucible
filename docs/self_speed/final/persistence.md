<!-- input snapshot hash fb9a176c82 -->
# Persistence of CPU steps (Amendment 2 rule)

Pre = median CPU of the 3 timed commits before the step commit; post = median of the first 3 timed commits at or after it. A step is evaluated only if post > pre x (1+T) and at least 6 timed commits lie at or after it. REVERSED = a later run of 3 consecutive timed commits (starting after the post window) whose median is <= pre x (1+T) (within T of pre, or beyond it: overshoot counts). ELEVATED AT TIP = median of the last 3 timed commits > pre x (1+T), independent of REVERSED. 'Removed by named DOWN' = a localised DOWN step on the same corpus lies between the last non-reversed commit and the end of the reversal window. OVERLAPPING = another localised CPU step on the same corpus lies inside the pre/post window span; excluded from pooled figures. Dates are US Eastern commit dates. One step per (corpus, found commit); files-only localisations are not evaluated.

## Summary (non-overlapping evaluable UP steps)

Overlapping steps excluded from the pooled rows: 12.

| group | UP steps | reversed (share; 95% CI) | of which removed by a named DOWN | median days / commits to reversal | Kaplan-Meier share reversed by end / median commits (right-censoring) | not reversed | elevated at tip |
|---|---|---|---|---|---|---|---|
| cics-crucible | 2 | 2 (100%; 16% to 100%) | 1 | 2 / 83 | 100% / 80 | 0 (median follow-up n/a commits) | 2 (100%) |
| keyword-rosetta | 1 | 0 (0%; 0% to 98%) | 0 | n/a / n/a | 0% / n/a | 1 (median follow-up 5709 commits) | 1 (100%) |
| language-crucible | 5 | 5 (100%; 48% to 100%) | 5 | 11 / 318 | 100% / 318 | 0 (median follow-up n/a commits) | 0 (0%) |
| onepl | 2 | 0 (0%; 0% to 84%) | 0 | n/a / n/a | 0% / n/a | 2 (median follow-up 5476 commits) | 2 (100%) |
| pooled, per (corpus, commit) | 10 | 7 (70%; 35% to 93%) | 6 | 9 / 167 | 70% / 318 | 3 (median follow-up 5709 commits) | 5 (50%) |

Pooled per commit (deduped across corpora): 9 commits; reversed in all corpora that saw them 6, in none 2, mixed 1; elevated at the tip in all corpora 4.
Right-censoring: a step not yet reversed at the tip is censored, not 'persistent for ever'; the plain share reversed is therefore a lower bound and the Kaplan-Meier column treats unreversed steps as censored at their follow-up.

## Every evaluated UP step

| corpus | date | idx | commit | pre CPU s | post CPU s | size (medians) | reversed | days | commits | removed by named DOWN | overshoot | elevated at tip | tip vs pre | overlapping |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cics-crucible | 2026-04-01 | 50 | 5381dfe037 | 1.51 | 4.14 | +174% | no |  |  |  |  | yes | +757% | c031a46994(up), 3b2408dbbe(down), 42ce7110f3(up) |
| cics-crucible | 2026-04-08 | 68 | 42ce7110f3 | 2.83 | 4.29 | +52% | no |  |  |  |  | yes | +357% | 5381dfe037(up), 3b2408dbbe(down) |
| cics-crucible | 2026-09-14 | 2339 | 55ccc7b52f | 6.68 | 8.06 | +21% | yes | 3 | 86 |  |  | yes | +94% |  |
| cics-crucible | 2026-09-26 | 2864 | 5f150b9d6c | 8.60 | 10.46 | +22% | yes | 1 | 80 | 5998bd8d40 |  | yes | +50% |  |
| keyword-rosetta | 2026-04-01 | 50 | 5381dfe037 | 1.17 | 2.02 | +73% | no |  |  |  |  | yes | +3671% | c031a46994(up), 3b2408dbbe(down), 42ce7110f3(up) |
| keyword-rosetta | 2026-04-08 | 68 | 42ce7110f3 | 1.48 | 3.07 | +107% | no |  |  |  |  | yes | +2881% | 5381dfe037(up), 3b2408dbbe(down) |
| keyword-rosetta | 2026-08-07 | 990 | 23e43bd5e8 | 3.54 | 4.36 | +23% | no |  |  |  |  | yes | +1146% |  |
| keyword-rosetta | 2026-09-26 | 2864 | 5f150b9d6c | 5.82 | 10.97 | +88% | no |  |  |  |  | yes | +658% | 6f9c449ae0(down) |
| keyword-rosetta | 2026-09-27 | 2937 | 6b604f91a7 | 10.97 | 36.42 | +232% | no |  |  |  |  | yes | +302% | 6f9c449ae0(down) |
| language-crucible | 2026-04-01 | 50 | 5381dfe037 | 92.79 | 120.56 | +30% | yes | 200 | 3900 | 14fc9c7a55 |  | no | +1% | 3b2408dbbe(down), 6d4138bf29(up) |
| language-crucible | 2026-04-12 | 71 | 6d4138bf29 | 108.03 | 139.84 | +29% | yes | 189 | 3879 | 14fc9c7a55 | yes | no | -13% | 5381dfe037(up), 3b2408dbbe(down) |
| language-crucible | 2026-07-12 | 305 | 45807f575b | 132.85 | 171.36 | +29% | yes | 11 | 145 | 1a70f72940 |  | no | -29% |  |
| language-crucible | 2026-08-07 | 990 | 23e43bd5e8 | 131.41 | 151.26 | +15% | yes | 72 | 2960 | 14fc9c7a55 | yes | no | -29% |  |
| language-crucible | 2026-08-10 | 1045 | 89d86da58a | 151.26 | 172.75 | +14% | yes | 36 | 1330 | 46a6aff44c |  | no | -38% |  |
| language-crucible | 2026-08-16 | 1457 | f3e84f765f | 173.62 | 260.19 | +50% | yes | 6 | 318 | 7e2808c964 |  | no | -46% |  |
| language-crucible | 2026-09-05 | 2183 | f8d1077413 | 182.99 | 267.63 | +46% | yes | 9 | 167 | 46a6aff44c |  | no | -49% |  |
| language-crucible | 2026-09-26 | 2864 | 5f150b9d6c | 183.97 | 336.33 | +83% | yes | 22 | 1086 | 14fc9c7a55 | yes | no | -49% | 6f9c449ae0(down) |
| onepl | 2026-04-08 | 68 | 42ce7110f3 | 0.36 | 1.77 | +392% | no |  |  |  |  | yes | +10331% |  |
| onepl | 2026-09-15 | 2378 | 115f265465 | 1.98 | 2.49 | +26% | no |  |  |  |  | yes | +1796% |  |
| onepl | 2026-09-26 | 2864 | 5f150b9d6c | 2.59 | 5.33 | +106% | no |  |  |  |  | yes | +1350% | 0bbdc137b6(up) |
| onepl | 2026-09-27 | 2892 | 0bbdc137b6 | 2.59 | 5.82 | +125% | no |  |  |  |  | yes | +1350% | 5f150b9d6c(up), 6b604f91a7(up) |
| onepl | 2026-09-27 | 2937 | 6b604f91a7 | 5.33 | 30.60 | +474% | no |  |  |  |  | yes | +605% | 0bbdc137b6(up) |

## DOWN steps (size = boundary pair, never median levels)

| corpus | date | idx | commit | boundary CPU s (parent -> commit) | boundary rel | timed commits after |
|---|---|---|---|---|---|---|
| cics-crucible | 2026-04-04 | 65 | 3b2408dbbe | 4.02 -> 2.645 | -34% | 290 |
| cics-crucible | 2026-09-27 | 2932 | 5998bd8d40 | 10.655000000000001 -> 9.434999999999999 | -12% | 157 |
| keyword-rosetta | 2026-04-04 | 65 | 3b2408dbbe | 2.0199999999999996 -> 1.495 | -26% | 290 |
| keyword-rosetta | 2026-09-15 | 2372 | 68ff0c3885 | 5.0 -> 4.220000000000001 | -16% | 181 |
| keyword-rosetta | 2026-09-27 | 2909 | 6f9c449ae0 | 13.89 -> 10.855 | -22% | 158 |
| language-crucible | 2026-04-04 | 65 | 3b2408dbbe | 119.1 -> 105.61 | -11% | 290 |
| language-crucible | 2026-07-06 | 231 | 92dae57c58 | 149.75 -> 132.135 | -12% | 276 |
| language-crucible | 2026-07-24 | 470 | 1a70f72940 | 171.035 -> 130.89 | -24% | 265 |
| language-crucible | 2026-08-02 | 851 | 522de4a672 | 151.44 -> 134.105 | -11% | 248 |
| language-crucible | 2026-08-23 | 1779 | 7e2808c964 | 491.66999999999996 -> 176.435 | -64% | 208 |
| language-crucible | 2026-09-14 | 2353 | 46a6aff44c | 290.69 -> 192.0 | -34% | 181 |
| language-crucible | 2026-09-27 | 2909 | 6f9c449ae0 | 366.04999999999995 -> 292.515 | -20% | 158 |
| language-crucible | 2026-10-18 | 3954 | 14fc9c7a55 | 339.485 -> 95.74 | -72% | 114 |
| language-crucible | 2026-10-18 | 3976 | c1f9502b5a | 95.75999999999999 -> 67.05 | -30% | 113 |
| language-crucible | 2026-10-22 | 4445 | 2a70f9ac86 | 69.42 -> 60.955 | -12% | 94 |

## UP steps not evaluated

- cics-crucible 2026-03-25 idx 21 c031a46994: fewer than 3 timed commits before or after
- keyword-rosetta 2026-03-25 idx 21 c031a46994: fewer than 3 timed commits before or after
- keyword-rosetta 2026-09-15 idx 2378 115f265465: post-level median within T of the pre level (step not visible at 3-commit medians)
- language-crucible 2026-06-27 idx 220 21f84abe4a: post-level median within T of the pre level (step not visible at 3-commit medians)
- language-crucible 2026-08-02 idx 849 55b3ed0c0b: post-level median within T of the pre level (step not visible at 3-commit medians)
- language-crucible 2026-08-22 idx 1770 5b8e2c3f2e: post-level median within T of the pre level (step not visible at 3-commit medians)
- language-crucible 2026-10-18 idx 3947 c89492d92d: post-level median within T of the pre level (step not visible at 3-commit medians)
- language-crucible 2026-11-18 idx 6576 e8d000f7ce: fewer than 6 timed commits after the step (right-censored)
- onepl 2026-08-13 idx 1252 2fc593a0a2: post-level median within T of the pre level (step not visible at 3-commit medians)
- keyword-rosetta 8bfb80ddc8: localised on files_mapped only (persistence is defined on CPU)
- cics-crucible 8bfb80ddc8: localised on files_mapped only (persistence is defined on CPU)
- onepl 8bfb80ddc8: localised on files_mapped only (persistence is defined on CPU)
- language-crucible 8bfb80ddc8: localised on files_mapped only (persistence is defined on CPU)
- language-crucible c42ed21ec3: localised on files_mapped only (persistence is defined on CPU)
- cics-crucible 22545ca562: localised on files_mapped only (persistence is defined on CPU)

Notes: steps are not netted against each other; a localised step whose neighbours sit inside its windows is marked overlapping and left out of pooled rows. Pre levels are sensitive to the sparse early sampling.
