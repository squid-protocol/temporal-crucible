# BANK STATUS — what is fit to carry an analysis

Measured by `tools/bank_status.py`, not asserted. **Good standing** = every layer present **and** a
fix label whose precision on that repo clears 0.70.

| repo | lang | tier | walk | commits | deltas | events | best label | standing | missing |
|---|---|---|---|---|---|---|---|---|---|
| libxml2 | c | development | 106 | 7,831 | 42,900 | 3,160 | 0.86 | **GOOD** | — |
| prometheus | go | development | 55 | 8,753 | 70,338 | 2,576 | 0.83 | **GOOD** | — |
| ripgrep | rust | development | 32 | 2,241 | 5,328 | 319 | 0.82 | **GOOD** | — |
| sphinx | python | development | 69 | 16,626 | 66,773 | 3,624 | 0.78 | **GOOD** | — |
| postgres | c | development | 121 | 65,885 | 327,547 | 17,690 | 0.77 | **GOOD** | — |
| redis | c | development | 65 | 11,974 | 32,371 | 3,409 | 0.75 | **GOOD** | — |
| commons-lang | java | development | 97 | 9,919 | 27,206 | 1,083 | 0.70 | **GOOD** | — |
| libgit2 | c | development | 66 | 3,972 | 65,471 | 2,562 | 0.63 | not yet | label<0.70 |
| curl | c | pilot | — | — | — | 8,352 | 0.80 | not yet | walk, history, deltas |
| ndpi | c | pilot | — | — | — | 1,519 | 0.68 | not yet | walk, history, deltas, label<0.70 |
| openssl | c | reserved | — | — | — | 8,996 | 0.80 | not yet | walk, history, deltas |

**7 of 11 repos in good standing**, covering 5 languages: c, go, java, python, rust.

