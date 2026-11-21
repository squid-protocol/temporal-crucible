<!-- input snapshot hash fb9a176c82 -->
# Step events (one row per commit named by a LOCALISED refinement)

Refinements: 75 of 75 candidates (COMPLETE); pass 1 75, pass 2 30 (pass 2 supersedes), 8 changed class between passes. Events: 35. Dates are US Eastern commit dates.
Sizes: size_cpu = largest |boundary_rel| of CPU-metric corpora; size_files = file-count change (files mapped), never mixed with CPU. '(files)' marks a files_mapped figure. 'pair' = the original sampled-pair dCPU. Direction is by the CPU boundary pairs (files-only events: by files).
Core funcs = engine Python functions in core files touched (diff cache). Buckets: a standards (no core), b core <=3 funcs, c core >3 funcs, d only tools/tests/docs/other, e no files, gap = core commit absent from the diff cache (function count unknown).
Lines are against the first parent (merges included). PR = last '(#N)' in the subject that is a known PR.

## 2026-03-25  idx 21  c031a46994  bucket (c)  up  CPU 20% / files n/a
- Subject: feat: implement Domain Ontologies and Context-Aware Security Profiles
- PR: none found
- Corpora: keyword-rosetta +20% (pair +43%); cics-crucible +11% (pair +14%)
- Files by kind: core 11, standards 2, translator_tools 0, tests 0, docs 0, other 1 (total 14); core funcs touched 15; lines +10893 -10687

## 2026-04-01  idx 50  5381dfe037  bucket (b)  up  CPU 125% / files n/a
- Subject: add photos for readme again
- PR: none found
- Corpora: keyword-rosetta +75% (pair +71%); cics-crucible +87% (pair +174%); language-crucible +125% (pair +30%)
- Files by kind: core 2, standards 0, translator_tools 0, tests 0, docs 9, other 1 (total 12); core funcs touched 2; lines +490 -152

## 2026-04-04  idx 65  3b2408dbbe  bucket (c)  down  CPU 34% / files n/a
- Subject: Update docs, site core, and add keyword fingerprinting
- PR: none found
- Corpora: keyword-rosetta -26% (pair -27%); cics-crucible -34% (pair -32%); language-crucible -11% (pair -10%)
- Files by kind: core 4, standards 1, translator_tools 0, tests 0, docs 6, other 1 (total 12); core funcs touched 4; lines +494 -289

## 2026-04-08  idx 68  42ce7110f3  bucket (c)  up  CPU 237% / files n/a
- Subject: security updates
- PR: none found
- Corpora: keyword-rosetta +85% (pair +107%); cics-crucible +54% (pair +52%); onepl +237% (pair +392%)
- Files by kind: core 7, standards 1, translator_tools 0, tests 0, docs 58, other 2 (total 68); core funcs touched 9; lines +757 -469

## 2026-04-12  idx 71  6d4138bf29  bucket (c)  up  CPU 14% / files n/a
- Subject: temporal & sec upgrades
- PR: none found
- Corpora: language-crucible +14% (pair +29%)
- Files by kind: core 16, standards 1, translator_tools 0, tests 0, docs 0, other 21 (total 38); core funcs touched 43; lines +12680 -12318

## 2026-06-27  idx 220  21f84abe4a  bucket (gap)  up  CPU 13% / files n/a
- Subject: Merge pull request #87 from squid-protocol/feature/clarity_updates_5
- PR: none found
- Corpora: language-crucible +13% (pair +10%)
- Files by kind: core 22, standards 4, translator_tools 28, tests 27, docs 16, other 1 (total 98); core funcs touched 0 (cache gap); lines +6001 -7950

## 2026-07-04  idx 229  8bfb80ddc8  bucket (a)  up  CPU n/a / files 7% (files)
- Subject: feat(ci): Implement Deterministic Golden Crucible Regression Pipeline
- PR: none found
- Corpora: keyword-rosetta +3% (files) (pair +1%); cics-crucible +3% (files) (pair +1%); onepl +4% (files) (pair -5%); language-crucible +7% (files) (pair +0%)
- Files by kind: core 0, standards 1, translator_tools 0, tests 30, docs 1, other 2 (total 34); core funcs touched 0; lines +369584 -70812

## 2026-07-06  idx 231  92dae57c58  bucket (gap)  down  CPU 12% / files n/a
- Subject: Merge pull request #122 from squid-protocol/feature/121-minified-fallback-screen
- PR: none found
- Corpora: language-crucible -12% (pair -14%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 1, docs 0, other 0 (total 2); core funcs touched 0 (cache gap); lines +163 -24

## 2026-07-12  idx 305  45807f575b  bucket (c)  up  CPU 30% / files n/a
- Subject: feat(sarif): inject exact LOC precision into security dashboard alerts
- PR: none found
- Corpora: language-crucible +30% (pair +29%)
- Files by kind: core 3, standards 0, translator_tools 0, tests 2, docs 0, other 0 (total 5); core funcs touched 4; lines +117 -13

## 2026-07-24  idx 470  1a70f72940  bucket (c)  down  CPU 24% / files n/a
- Subject: Fix prism.py's comment-family taxonomy -- comment/code separation was completely broken for all 58 languages (#386) (#389)
- PR: #389 Fix prism.py's comment-family taxonomy -- comment/code separation was broken for all 58 languages (#386) []
- Corpora: language-crucible -24% (pair -23%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 2, docs 0, other 0 (total 3); core funcs touched 4; lines +113 -28

## 2026-08-02  idx 849  55b3ed0c0b  bucket (a)  up  CPU 12% / files n/a
- Subject: fix(extraction): Harden Dart syntax extraction (#969)
- PR: #969 fix(extraction): Harden Dart syntax extraction []
- Corpora: language-crucible +12% (pair +13%)
- Files by kind: core 0, standards 1, translator_tools 0, tests 4, docs 1, other 1 (total 7); core funcs touched 0; lines +101214 -103420

## 2026-08-02  idx 851  522de4a672  bucket (a)  down  CPU 11% / files n/a
- Subject: Extraction hardening: php (#968)
- PR: #968 Extraction hardening: php []
- Corpora: language-crucible -11% (pair -12%)
- Files by kind: core 0, standards 1, translator_tools 0, tests 9, docs 3, other 2 (total 15); core funcs touched 0; lines +93442 -88571

## 2026-08-07  idx 990  23e43bd5e8  bucket (b)  up  CPU 22% / files n/a
- Subject: fix(core): give core_var_decl/design_* naming-convention signatures real producers (#1151)
- PR: #1151 fix(core): give core_var_decl/design_* naming-convention signatures real producers []
- Corpora: keyword-rosetta +22% (pair +19%); language-crucible +16% (pair +13%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 5, docs 0, other 0 (total 6); core funcs touched 2; lines +39365 -38885

## 2026-08-10  idx 1045  89d86da58a  bucket (b)  up  CPU 13% / files n/a
- Subject: fix(core): prevent Prism from swallowing code due to quotes in comments (fixes #1222) (#1234)
- PR: #1234 fix(core): prevent Prism from swallowing code due to quotes in comments (fixes #1222) []
- Corpora: language-crucible +13% (pair +15%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 3, docs 0, other 0 (total 4); core funcs touched 3; lines +564542 -440297

## 2026-08-13  idx 1252  2fc593a0a2  bucket (d)  up  CPU 12% / files n/a
- Subject: docs: auto-update tree-sitter accuracy data (#1475)
- PR: #1475 docs: auto-update tree-sitter accuracy data []
- Corpora: onepl +12% (pair +11%)
- Files by kind: core 0, standards 0, translator_tools 0, tests 0, docs 2, other 0 (total 2); core funcs touched 0; lines +36 -5

## 2026-08-16  idx 1457  f3e84f765f  bucket (c)  up  CPU 40% / files n/a
- Subject: Save current state before TS diagnostics
- PR: none found
- Corpora: language-crucible +40% (pair +48%)
- Files by kind: core 2, standards 1, translator_tools 0, tests 4, docs 0, other 0 (total 7); core funcs touched 20; lines +2297 -2869

## 2026-08-22  idx 1770  5b8e2c3f2e  bucket (b)  up  CPU 81% / files n/a
- Subject: Fix #2051: C# args regex truncation (#2147)
- PR: #2147 Fix #2051: C# args regex truncation []
- Corpora: language-crucible +81% (pair +85%)
- Files by kind: core 1, standards 1, translator_tools 0, tests 3, docs 4, other 0 (total 9); core funcs touched 1; lines +989 -943

## 2026-08-23  idx 1779  7e2808c964  bucket (a)  down  CPU 64% / files n/a
- Subject: fix(regex): resolve ReDoS timeout in typescript args extraction (#2156)
- PR: #2156 fix(regex): resolve ReDoS timeout in typescript args extraction []
- Corpora: language-crucible -64% (pair -64%)
- Files by kind: core 0, standards 1, translator_tools 0, tests 2, docs 0, other 0 (total 3); core funcs touched 0; lines +17 -17

## 2026-08-29  idx 2000  c42ed21ec3  bucket (b)  up  CPU n/a / files 3% (files)
- Subject: fix(#2415): anchor aperture infra_path_pattern to a real left boundary (#2418)
- PR: #2418 fix(#2415): anchor aperture infra_path_pattern to a real left boundary []
- Corpora: language-crucible +3% (files) (pair +3%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 5, docs 2, other 0 (total 8); core funcs touched 1; lines +455362 -444028

## 2026-09-05  idx 2183  f8d1077413  bucket (c)  up  CPU 31% / files n/a
- Subject: fix(core-engine): the orphan census counts references, not name repetitions (#2727, #2728) (#2754)
- PR: #2754 fix(core-engine): the orphan census counts references, not name repetitions (#2727, #2728) [rosetta:rebless-owed]
- Corpora: language-crucible +31% (pair +46%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 3, docs 0, other 0 (total 4); core funcs touched 4; lines +117341 -117093

## 2026-09-14  idx 2339  55ccc7b52f  bucket (b)  up  CPU 18% / files n/a
- Subject: fix(#2978): run the security lens on inert data formats (#3009)
- PR: #3009 fix(#2978): run the security lens on inert data formats []
- Corpora: cics-crucible +18% (pair +21%)
- Files by kind: core 2, standards 2, translator_tools 0, tests 7, docs 2, other 0 (total 13); core funcs touched 2; lines +291 -72

## 2026-09-14  idx 2353  46a6aff44c  bucket (c)  down  CPU 34% / files n/a
- Subject: perf: kill ReDoS + O(N^2) splice hot paths behind v2.7.0 speed outliers (#3043)
- PR: #3043 perf: kill ReDoS + O(N^2) splice hot paths behind v2.7.0 speed outliers []
- Corpora: language-crucible -34% (pair -39%)
- Files by kind: core 1, standards 2, translator_tools 0, tests 0, docs 0, other 0 (total 3); core funcs touched 4; lines +124 -9

## 2026-09-15  idx 2372  68ff0c3885  bucket (b)  down  CPU 16% / files n/a
- Subject: perf(detector): skip =-less lines before the var-decl backtracking regex (#3063)
- PR: #3063 perf(detector): skip =-less lines before the var-decl backtracking regex []
- Corpora: keyword-rosetta -16% (pair -16%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 0, docs 0, other 0 (total 1); core funcs touched 1; lines +15 -1

## 2026-09-15  idx 2378  115f265465  bucket (c)  up  CPU 23% / files n/a
- Subject: perf(detector): required-literal prefilter for the shared coding_analysis rule pass (#3070)
- PR: #3070 perf(detector): required-literal prefilter for the shared coding_analysis rule pass []
- Corpora: keyword-rosetta +23% (pair +17%); onepl +13% (pair +22%)
- Files by kind: core 2, standards 0, translator_tools 0, tests 2, docs 0, other 0 (total 4); core funcs touched 4; lines +911 -11

## 2026-09-20  idx 2487  22545ca562  bucket (c)  up  CPU n/a / files 14% (files)
- Subject: feat(mainframe): capture the CICS transaction map (#3211-followup, epic #3122) (#3251)
- PR: #3251 feat(mainframe): capture the CICS transaction map (#3211-followup, PR1 of 2) []
- Corpora: cics-crucible +14% (files) (pair +5%)
- Files by kind: core 5, standards 3, translator_tools 1, tests 7, docs 2, other 0 (total 18); core funcs touched 11; lines +1924 -49

## 2026-09-26  idx 2864  5f150b9d6c  bucket (c)  up  CPU 79% / files n/a
- Subject: #3814 (part 1): UAX #31 names for Python, Java, JavaScript and TypeScript (#3847)
- PR: #3847 #3814 (part 1): UAX #31 names for Python, Java, JavaScript and TypeScript []
- Corpora: keyword-rosetta +73% (pair +86%); cics-crucible +13% (pair +18%); onepl +37% (pair +60%); language-crucible +79% (pair +82%)
- Files by kind: core 3, standards 6, translator_tools 0, tests 2, docs 0, other 0 (total 11); core funcs touched 8; lines +459 -105

## 2026-09-27  idx 2892  0bbdc137b6  bucket (c)  up  CPU 19% / files n/a
- Subject: #3814 (part 5): UAX #31 names for Rust, Swift, Dart, PHP and Ruby (#3877)
- PR: #3877 #3814 (part 5): UAX #31 names for Rust, Swift, Dart, PHP and Ruby []
- Corpora: onepl +19% (pair +40%)
- Files by kind: core 1, standards 6, translator_tools 0, tests 2, docs 0, other 0 (total 9); core funcs touched 4; lines +523 -145

## 2026-09-27  idx 2909  6f9c449ae0  bucket (a)  down  CPU 22% / files n/a
- Subject: #3814: identifier classes stay cheap on a miss (astral gaps filled) (#3900)
- PR: #3900 #3814: identifier classes stay cheap on a miss (astral gaps filled) []
- Corpora: keyword-rosetta -22% (pair -22%); language-crucible -20% (pair -20%)
- Files by kind: core 0, standards 1, translator_tools 0, tests 1, docs 0, other 0 (total 2); core funcs touched 0; lines +120 -14

## 2026-09-27  idx 2932  5998bd8d40  bucket (c)  down  CPU 12% / files n/a
- Subject: Claude/fork precompile (#3931)
- PR: #3931 Claude/fork precompile [core-engine,performance]
- Corpora: cics-crucible -12% (pair -10%)
- Files by kind: core 2, standards 0, translator_tools 0, tests 2, docs 0, other 0 (total 4); core funcs touched 9; lines +90 -21

## 2026-09-27  idx 2937  6b604f91a7  bucket (b)  up  CPU 487% / files n/a
- Subject: #3929: pre-compile before a fork only for scans of 500+ files (small scans keep #3923's 30% win) (#3939)
- PR: #3939 #3929: pre-compile before a fork only for scans of 500+ files (small scans keep #3923's 30% win) [core-engine,performance]
- Corpora: keyword-rosetta +230% (pair +234%); onepl +487% (pair +461%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 3, docs 0, other 0 (total 4); core funcs touched 2; lines +34 -5

## 2026-10-18  idx 3947  c89492d92d  bucket (b)  up  CPU 11% / files n/a
- Subject: aperture: payload guards keep files with function definitions beside a data table (Part of #5460) (#5493)
- PR: #5493 aperture: payload guards keep files with function definitions beside a data table (Part of #5460) [shepherd:merge]
- Corpora: language-crucible +11% (pair +14%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 365, docs 0, other 0 (total 366); core funcs touched 1; lines +175 -2

## 2026-10-18  idx 3954  14fc9c7a55  bucket (c)  down  CPU 72% / files n/a
- Subject: aperture: vendored trees under any name -- third_party_* prefixes, *_libs containers, foreign-license directories (Part of #5464) (#5512)
- PR: #5512 aperture: vendored trees under any name (third_party_*, *_libs, foreign-license dirs) (Part of #5464) [shepherd:merge]
- Corpora: language-crucible -72% (pair -72%)
- Files by kind: core 3, standards 0, translator_tools 0, tests 1, docs 0, other 0 (total 4); core funcs touched 8; lines +91 -18

## 2026-10-18  idx 3976  c1f9502b5a  bucket (b)  down  CPU 30% / files n/a
- Subject: Fix the three red legs of the Full Suite Gate on main (Part of #5531) (#5534)
- PR: #5534 Fix the three red legs of the Full Suite Gate on main (Part of #5531) [shepherd:merge]
- Corpora: language-crucible -30% (pair -30%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 4, docs 0, other 0 (total 5); core funcs touched 1; lines +111 -9

## 2026-10-22  idx 4445  2a70f9ac86  bucket (b)  down  CPU 12% / files n/a
- Subject: perf: X-Ray and the vault scan run only the signatures they read (Part of #5500) (#6105)
- PR: #6105 perf: X-Ray and the vault scan run only the signatures they read (Part of #5500) [shepherd:merge]
- Corpora: language-crucible -12% (pair -11%)
- Files by kind: core 1, standards 0, translator_tools 2, tests 1, docs 0, other 0 (total 4); core funcs touched 1; lines +52 -13

## 2026-11-18  idx 6576  e8d000f7ce  bucket (b)  up  CPU 12% / files n/a
- Subject: security: every one-line signature reads lines of 250+ chars in chunks (Part of #8429) (#8615)
- PR: #8615 security: every one-line signature reads lines of 250+ chars in chunks (Part of #8429) [shepherd:merge]
- Corpora: language-crucible +12% (pair +12%)
- Files by kind: core 1, standards 0, translator_tools 0, tests 7, docs 2, other 0 (total 10); core funcs touched 2; lines +106 -19

## UNCONFIRMED / UNEVALUABLE candidates (counted, not analysed as steps)

- UNCONFIRMED (pass 2) keyword-rosetta 2026-04-17..2026-05-10 pair dCPU +13%; metric cpu_s; bisect named f4201a683a; boundary rel -0.032
- UNCONFIRMED (pass 2) keyword-rosetta 2026-09-27..2026-09-27 pair dCPU +24%; metric cpu_s; bisect named 5ae444b0ef; boundary rel 0.107
- UNCONFIRMED (pass 2) keyword-rosetta 2026-10-25..2026-10-25 pair dCPU +17%; metric cpu_s; bisect named 3e2b565e58; boundary rel -0.011
- UNCONFIRMED (pass 2) keyword-rosetta 2026-10-25..2026-10-25 pair dCPU -14%; metric cpu_s; bisect named 1736419084; boundary rel -0.002
- UNCONFIRMED (pass 2) cics-crucible 2026-04-17..2026-05-10 pair dCPU +16%; metric cpu_s; bisect named f4201a683a; boundary rel -0.007
- UNCONFIRMED (pass 2) cics-crucible 2026-09-27..2026-09-27 pair dCPU +11%; metric cpu_s; bisect named 0bbdc137b6; boundary rel 0.04
- UNCONFIRMED (pass 2) onepl 2026-03-22..2026-03-26 pair dCPU +10%; metric cpu_s; bisect named 42c7cd7903; boundary rel 0.016
- UNCONFIRMED (pass 2) onepl 2026-03-28..2026-04-01 pair dCPU +12%; metric cpu_s; bisect named e8d7c14240; boundary rel 0.014
- UNCONFIRMED (pass 2) onepl 2026-04-12..2026-04-17 pair dCPU -19%; metric cpu_s; bisect named 0bd618b7b6; boundary rel -0.034
- UNCONFIRMED (pass 2) onepl 2026-04-17..2026-05-10 pair dCPU +30%; metric cpu_s; bisect named f4201a683a; boundary rel -0.02
- UNCONFIRMED (pass 2) onepl 2026-07-12..2026-07-14 pair dCPU -19%; metric cpu_s; bisect named 746cb311f5; boundary rel 0.013
- UNCONFIRMED (pass 2) onepl 2026-07-17..2026-07-17 pair dCPU +13%; metric cpu_s; bisect named f467c44bc6; boundary rel 0.028
- UNCONFIRMED (pass 2) onepl 2026-08-02..2026-08-04 pair dCPU +11%; metric cpu_s; bisect named 9b0614c409; boundary rel 0.063
- UNCONFIRMED (pass 2) onepl 2026-08-09..2026-08-10 pair dCPU -13%; metric cpu_s; bisect named 87d71d9ebd; boundary rel -0.034
- UNCONFIRMED (pass 2) onepl 2026-08-10..2026-08-10 pair dCPU +10%; metric cpu_s; bisect named 7566d91f30; boundary rel 0.016
- UNCONFIRMED (pass 2) onepl 2026-08-20..2026-08-20 pair dCPU -10%; metric cpu_s; bisect named e403d3e652; boundary rel 0.096
- UNCONFIRMED (pass 2) onepl 2026-08-20..2026-08-20 pair dCPU +14%; metric cpu_s; bisect named 0b6da5f168; boundary rel 0.002
- UNCONFIRMED (pass 2) onepl 2026-08-21..2026-08-22 pair dCPU -14%; metric cpu_s; bisect named 48ccff57f9; boundary rel -0.029
- UNCONFIRMED (pass 2) onepl 2026-08-22..2026-08-22 pair dCPU +16%; metric cpu_s; bisect named 0e3e9b9bd3; boundary rel -0.038
- UNCONFIRMED (pass 2) onepl 2026-08-23..2026-08-23 pair dCPU -13%; metric cpu_s; bisect named e334dc10cc; boundary rel 0.084
- UNCONFIRMED (pass 2) onepl 2026-08-23..2026-08-24 pair dCPU +17%; metric cpu_s; bisect named fe966a2170; boundary rel 0.073
- UNCONFIRMED (pass 2) language-crucible 2026-04-17..2026-05-10 pair dCPU +15%; metric cpu_s; bisect named f4201a683a; boundary rel 0.006
- UNCONFIRMED (pass 2) language-crucible 2026-09-22..2026-09-23 pair dCPU +11%; metric cpu_s; bisect named 091ab9d411; boundary rel 0.085

## Candidates not yet refined

- none

## Unresolved crash commits (20 failed timed runs)

- keyword-rosetta idx 92 2026-04-19 0972ff99ad
- keyword-rosetta idx 100 2026-04-21 0d9a511550
- keyword-rosetta idx 125 2026-04-22 01ef284c38
- keyword-rosetta idx 141 2026-04-25 1790ae7e03
- keyword-rosetta idx 150 2026-05-01 1a326044c4
- cics-crucible idx 92 2026-04-19 0972ff99ad
- cics-crucible idx 100 2026-04-21 0d9a511550
- cics-crucible idx 125 2026-04-22 01ef284c38
- cics-crucible idx 141 2026-04-25 1790ae7e03
- cics-crucible idx 150 2026-05-01 1a326044c4
- onepl idx 92 2026-04-19 0972ff99ad
- onepl idx 100 2026-04-21 0d9a511550
- onepl idx 125 2026-04-22 01ef284c38
- onepl idx 141 2026-04-25 1790ae7e03
- onepl idx 150 2026-05-01 1a326044c4
- language-crucible idx 92 2026-04-19 0972ff99ad
- language-crucible idx 100 2026-04-21 0d9a511550
- language-crucible idx 125 2026-04-22 01ef284c38
- language-crucible idx 141 2026-04-25 1790ae7e03
- language-crucible idx 150 2026-05-01 1a326044c4
