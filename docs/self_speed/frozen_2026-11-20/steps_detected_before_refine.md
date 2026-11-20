# Detected steps (plan rule applied; EXPLORATORY)

Thresholds T per corpus (max(10%, 4 x A/A deviation)): keyword-rosetta 13%, cics-crucible 10%, onepl 10%, language-crucible 10%
Points per corpus: {'keyword-rosetta': 300, 'cics-crucible': 300, 'onepl': 300, 'language-crucible': 300}; A/A anchor runs: {'keyword-rosetta': 15, 'cics-crucible': 15, 'onepl': 15, 'language-crucible': 15}
Candidates: 75; unresolved (engine failed): 5 commits; ramps: 0

## Known events: flagged by the sample?
- E1 #3929: index 2937 bracketed by sampled [2925, 2944]; flagged by ['cics-crucible', 'keyword-rosetta', 'onepl']
- E2 #5512: index 3954 bracketed by sampled [3950, 3975]; flagged by ['language-crucible']
- E3 #1234: index 1045 bracketed by sampled [1025, 1050]; flagged by ['language-crucible', 'onepl']

## Candidates (corpus, bracket, dCPU, dFiles)
- keyword-rosetta   2026-03-22..2026-03-26 idx 10-25 dCPU +43% dFiles +0.0%
- keyword-rosetta   2026-03-28..2026-04-01 idx 39-50 dCPU +71% dFiles +23.2%
- keyword-rosetta   2026-04-01..2026-04-04 idx 50-66 dCPU -27% dFiles +0.0%
- keyword-rosetta   2026-04-04..2026-04-12 idx 66-72 dCPU +107% dFiles +0.0%
- keyword-rosetta   2026-04-17..2026-05-10 idx 75-153 dCPU +13% dFiles +0.0% (a failed commit lies in the gap)
- keyword-rosetta   2026-06-27..2026-07-05 idx 227-230 dCPU +1% dFiles +3.2%
- keyword-rosetta   2026-08-06..2026-08-09 idx 975-1000 dCPU +19% dFiles +1.5%
- keyword-rosetta   2026-09-14..2026-09-15 idx 2350-2375 dCPU -16% dFiles +1.5%
- keyword-rosetta   2026-09-15..2026-09-16 idx 2375-2400 dCPU +17% dFiles +0.0%
- keyword-rosetta   2026-09-26..2026-09-27 idx 2850-2875 dCPU +86% dFiles +0.0%
- keyword-rosetta   2026-09-27..2026-09-27 idx 2875-2900 dCPU +24% dFiles +0.0%
- keyword-rosetta   2026-09-27..2026-09-27 idx 2900-2925 dCPU -22% dFiles +0.0%
- keyword-rosetta   2026-09-27..2026-09-27 idx 2925-2944 dCPU +234% dFiles +0.0%
- keyword-rosetta   2026-10-25..2026-10-25 idx 4875-4900 dCPU +17% dFiles +0.0%
- keyword-rosetta   2026-10-25..2026-10-25 idx 4900-4925 dCPU -14% dFiles +0.0%
- cics-crucible     2026-03-22..2026-03-26 idx 10-25 dCPU +14% dFiles +0.0%
- cics-crucible     2026-03-28..2026-04-01 idx 39-50 dCPU +174% dFiles +136.8%
- cics-crucible     2026-04-01..2026-04-04 idx 50-66 dCPU -32% dFiles +0.0%
- cics-crucible     2026-04-04..2026-04-12 idx 66-72 dCPU +52% dFiles +0.0%
- cics-crucible     2026-04-17..2026-05-10 idx 75-153 dCPU +16% dFiles +0.0% (a failed commit lies in the gap)
- cics-crucible     2026-06-27..2026-07-05 idx 227-230 dCPU +1% dFiles +3.4%
- cics-crucible     2026-09-13..2026-09-14 idx 2335-2350 dCPU +21% dFiles +0.0%
- cics-crucible     2026-09-19..2026-09-20 idx 2475-2489 dCPU +5% dFiles +14.1%
- cics-crucible     2026-09-26..2026-09-27 idx 2850-2875 dCPU +18% dFiles +0.0%
- cics-crucible     2026-09-27..2026-09-27 idx 2875-2900 dCPU +11% dFiles +0.0%
- cics-crucible     2026-09-27..2026-09-27 idx 2925-2944 dCPU -10% dFiles +0.0%
- onepl             2026-03-22..2026-03-26 idx 10-25 dCPU +10% dFiles +0.0%
- onepl             2026-03-28..2026-04-01 idx 39-50 dCPU +12% dFiles +0.0%
- onepl             2026-04-04..2026-04-12 idx 66-72 dCPU +392% dFiles +0.0%
- onepl             2026-04-12..2026-04-17 idx 72-75 dCPU -19% dFiles +0.0%
- onepl             2026-04-17..2026-05-10 idx 75-153 dCPU +30% dFiles +0.0% (a failed commit lies in the gap)
- onepl             2026-06-27..2026-07-05 idx 227-230 dCPU -5% dFiles +4.5%
- onepl             2026-07-12..2026-07-14 idx 314-325 dCPU -19% dFiles +0.0%
- onepl             2026-07-17..2026-07-17 idx 375-393 dCPU +13% dFiles +0.0%
- onepl             2026-08-02..2026-08-04 idx 896-900 dCPU +11% dFiles +0.0%
- onepl             2026-08-09..2026-08-10 idx 1017-1025 dCPU -13% dFiles +0.0%
- onepl             2026-08-10..2026-08-10 idx 1025-1050 dCPU +10% dFiles +0.0%
- onepl             2026-08-13..2026-08-13 idx 1250-1275 dCPU +11% dFiles +0.0%
- onepl             2026-08-20..2026-08-20 idx 1575-1600 dCPU -10% dFiles +0.0%
- onepl             2026-08-20..2026-08-20 idx 1600-1625 dCPU +14% dFiles +0.0%
- onepl             2026-08-21..2026-08-22 idx 1700-1725 dCPU -14% dFiles +0.0%
- onepl             2026-08-22..2026-08-22 idx 1725-1750 dCPU +16% dFiles +0.0%
- onepl             2026-08-23..2026-08-23 idx 1800-1824 dCPU -13% dFiles +0.0%
- onepl             2026-08-23..2026-08-24 idx 1824-1825 dCPU +17% dFiles +0.0%
- onepl             2026-09-15..2026-09-16 idx 2375-2400 dCPU +22% dFiles +0.0%
- onepl             2026-09-26..2026-09-27 idx 2850-2875 dCPU +60% dFiles +0.0%
- onepl             2026-09-27..2026-09-27 idx 2875-2900 dCPU +40% dFiles +0.0%
- onepl             2026-09-27..2026-09-27 idx 2925-2944 dCPU +461% dFiles +0.0%
- language-crucible 2026-03-28..2026-04-01 idx 39-50 dCPU +30% dFiles -16.5%
- language-crucible 2026-04-01..2026-04-04 idx 50-66 dCPU -10% dFiles -0.0%
- language-crucible 2026-04-04..2026-04-12 idx 66-72 dCPU +29% dFiles -0.4%
- language-crucible 2026-04-17..2026-05-10 idx 75-153 dCPU +15% dFiles +0.0% (a failed commit lies in the gap)
- language-crucible 2026-06-18..2026-06-27 idx 216-225 dCPU +10% dFiles +0.0%
- language-crucible 2026-06-27..2026-07-05 idx 227-230 dCPU +0% dFiles +7.2%
- language-crucible 2026-07-05..2026-07-10 idx 230-250 dCPU -14% dFiles +0.0%
- language-crucible 2026-07-12..2026-07-12 idx 300-314 dCPU +29% dFiles +0.0%
- language-crucible 2026-07-23..2026-07-24 idx 450-475 dCPU -23% dFiles +0.0%
- language-crucible 2026-08-01..2026-08-02 idx 825-850 dCPU +13% dFiles +0.0%
- language-crucible 2026-08-02..2026-08-02 idx 850-875 dCPU -12% dFiles +0.0%
- language-crucible 2026-08-06..2026-08-09 idx 975-1000 dCPU +13% dFiles +1.6%
- language-crucible 2026-08-10..2026-08-10 idx 1025-1050 dCPU +15% dFiles +0.0%
- language-crucible 2026-08-16..2026-08-16 idx 1450-1475 dCPU +48% dFiles +0.0%
- language-crucible 2026-08-22..2026-08-22 idx 1750-1775 dCPU +85% dFiles +0.0%
- language-crucible 2026-08-22..2026-08-23 idx 1775-1800 dCPU -64% dFiles +0.0%
- language-crucible 2026-08-28..2026-08-29 idx 1975-2000 dCPU +3% dFiles +3.1%
- language-crucible 2026-09-04..2026-09-05 idx 2175-2200 dCPU +46% dFiles +0.0%
- language-crucible 2026-09-14..2026-09-15 idx 2350-2375 dCPU -39% dFiles +0.4%
- language-crucible 2026-09-22..2026-09-23 idx 2525-2550 dCPU +11% dFiles +7.7%
- language-crucible 2026-09-26..2026-09-27 idx 2850-2875 dCPU +82% dFiles +0.0%
- language-crucible 2026-09-27..2026-09-27 idx 2900-2925 dCPU -20% dFiles +0.0%
- language-crucible 2026-10-18..2026-10-18 idx 3925-3950 dCPU +14% dFiles +0.3%
- language-crucible 2026-10-18..2026-10-18 idx 3950-3975 dCPU -72% dFiles -70.8%
- language-crucible 2026-10-18..2026-10-18 idx 3975-4000 dCPU -30% dFiles +0.0%
- language-crucible 2026-10-22..2026-10-22 idx 4425-4450 dCPU -11% dFiles +0.0%
- language-crucible 2026-11-18..2026-11-18 idx 6575-6600 dCPU +12% dFiles +0.0%