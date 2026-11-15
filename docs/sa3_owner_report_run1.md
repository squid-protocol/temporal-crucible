PASS

# The owner-run preparation job

Target: real. Started 2026-11-15 11:33 UTC (epoch 1794742399); took 409 s. It does not score SA3. Failed stages: 0.

PASS means: every repo on the frozen list has a determined count, A equals the stored file, and zero pattern disagreements; the placebo verdict is bytes_equal or numbers_equal; the seal was written; every module the reference scorer loaded, and hist_meta, is unchanged since 8fb7fe0 (checked with git); the manifests are unchanged. Anything else is FAIL.

## 1. Tracker-key count (Amendment 5 section 7, item 5)

| repo | determined | reason | count | A equals the stored file | pattern disagreements |
|---|---|---|---:|---|---:|
| blast | yes | none | 0 | yes | 0 |
| bugzilla | yes | none | 0 | yes | 0 |
| bun | yes | none | 1 | yes | 0 |
| circuitpython | yes | none | 0 | yes | 0 |
| commons-lang | yes | none | 1 | yes | 0 |
| cpython | yes | none | 0 | yes | 0 |
| curl | yes | none | 0 | yes | 0 |
| discourse | yes | none | 0 | yes | 0 |
| django | yes | none | 0 | yes | 0 |
| effect | yes | none | 0 | yes | 0 |
| fieldtrip | yes | none | 0 | yes | 0 |
| freebsd-src | yes | none | 0 | yes | 0 |
| ghostty | yes | none | 0 | yes | 0 |
| gnupg | yes | none | 0 | yes | 0 |
| go | yes | none | 0 | yes | 0 |
| godot | yes | none | 0 | yes | 0 |
| impacket | yes | none | 0 | yes | 0 |
| kubernetes | yes | none | 0 | yes | 0 |
| libxml2 | yes | none | 0 | yes | 0 |
| mediawiki | yes | none | 0 | yes | 0 |
| micropython | yes | none | 0 | yes | 0 |
| moby | yes | none | 0 | yes | 0 |
| ndpi | yes | none | 0 | yes | 0 |
| opencv | yes | none | 0 | yes | 0 |
| pandas | yes | none | 0 | yes | 0 |
| postgres | yes | none | 0 | yes | 0 |
| prometheus | yes | none | 0 | yes | 0 |
| racket | yes | none | 0 | yes | 0 |
| rails | yes | none | 0 | yes | 0 |
| redis | yes | none | 0 | yes | 0 |
| runtime | yes | none | 0 | yes | 0 |
| scapy | yes | none | 0 | yes | 0 |
| sphinx | yes | none | 0 | yes | 0 |
| spock | yes | none | 0 | yes | 0 |
| sqlite | yes | none | 0 | yes | 0 |
| sqlmap | yes | none | 0 | yes | 0 |
| swift | yes | none | 0 | yes | 0 |
| tcpip_historical | yes | none | 0 | yes | 0 |
| tensorflow | yes | none | 0 | yes | 0 |
| tigerbeetle | yes | none | 0 | yes | 0 |

The count is the number of commits under the primary outcome when the reference outcome builder runs on the inputs as they are, and not when it runs on a copy of the link harvest without its lower-case tracker keys (a fix-reference value with a hyphen and a lower-case letter, such as "fix x86-64 build"). A key written in capitals ("Fix UTF-8 decoding") matches the registered pattern with or without case and is not in this count (docs/sa3_amendment5_erratum_draft.md).

## 2. The placebo output reproduced (Amendment 5 section 9, layer 2)

Verdict: **bytes_equal** (the code and inputs reproduce the published gate result exactly: proceed). Stage code: none. Repos in the stage: 20.

Largest absolute difference among numbers: 0.0; numbers beyond 1e-9: 0; integer fields equal: yes.

A pass speaks for the universe, LOC, the primary outcome's file lists and the four primary predictors of the repos that clear the primary floor; not for the other outcomes, the commit lists, the pool or the secondary predictors.

Versions now: python 3.12.3, numpy 1.26.4, scipy 1.11.4, git 2.43.0, tar 1.35; linear algebra: libblas.so.3.12.0, libgfortran.so.5.0.0, liblapack.so.3.12.0. The committed placebo file was produced at 8fb7fe0 with versions that were not recorded.

## 3. The seal

seal.json written: yes; entries: 397; expected `lock` hashes: 9.

Modules the reference scorer loaded (import recorder around the placebo stage): _engine, fixlike_v2, hist_fixlabel, hist_replicate, label_card, label_cascade, laws_history, laws_units, mod1_lift, sa3_outcomes, sa3_score, sa3_stats. Unchanged since 8fb7fe0: yes.

Label-side manifest, before and after: unchanged yes; entries 6384. The manifest itself stays in the protected directory.

Do not paste anything from the protected directory into a session. Do not re-run to see if it passes.
