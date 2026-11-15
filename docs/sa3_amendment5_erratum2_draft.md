# SA3 — proposed second erratum to Amendment 5 (DRAFT; not in force)

**2026-11-15.** One phrase of the registration's statistic is ambiguous, and an independent reader took it the
other way from the code. It changes nothing that runs. It cannot be entered while the registration is sealed
(`docs/sa3_seal_run1.json`); it is to be entered with the scoring step's documents, before the seal is
re-taken and before the owner runs `lock`.

**The phrase.** Section 6, item 1 of the consolidated text: "Bands: equal-count on LOC, 10 if the repo has ≥ 300
files, else 5; ties broken by path."

**What the code does.** The band count is chosen from the number of files **in use for that predictor**, after
files with no value for it are dropped (`tools/sa3_score.py`, `design_for`; `tools/sa3_stats.py`, `bands`).

**Corrected wording.** "Bands: equal-count on LOC, 10 if the files in use for that predictor number 300 or
more, else 5; a file's band is floor(its rank × the number of bands ÷ the number of files), ranks by LOC with
ties broken by path in plain string order."

**Evidence.** `docs/process/indep_stat_report.md`: a second builder, reading only the words, chose "the repo's
ranked files"; with that one reading changed, its implementation equals the code bit for bit on 2,000 stress
cases and 66 decoy cells. The remaining six choices the words leave open were read the way the code reads
them; the corrected wording above also pins the remainder rule and the path order, which the first reviewer
found open (defect log 64).
