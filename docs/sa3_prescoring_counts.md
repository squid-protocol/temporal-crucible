# SA3 — counts published before scoring (Amendment 5, section 7)

**2026-11-14, about 6:20 PM Eastern.** Produced by `tools/tables/phase_b.py` at commit `e3b4f5e`, run on SA3's
real scans, histories and clones inside a read-only sandbox in which **no outcome file and no link harvest
were present**. No predictor was set against an outcome. SA3 is still unscored.

- 46 repos, 230 stages, all succeeded, in 4 minutes 54 seconds. The before-and-after record of every input
  and of each clone's `.git` directory (6,686 entries: size, modification time, change time) is identical.
- The tables (`repo`, `snapshot`, `file`, `measure` per repo, with hashes) and the full logs are kept at
  `/srv/storage_16tb/projects/temporal-crucible-tables/sa3-phase-b-2026-11-14/`, outside this repository and
  outside the study directory. The machine-readable counts are `docs/sa3_prescoring_counts.json`.
- The count of qualifying commits that qualify only through a lower-case tracker key (Amendment 5 section 7,
  item 5, last part) is **not here**: it needs the link harvest and is produced by the owner-run job.

## What the counts say

**1. The cells whose silence changed in `8fb7fe0`** (Amendment 5 section 7 item 1). Of 1,058 (repo, measure)
cells, 114 are silent under one version of the rule and not the other.

| measure | repos where the two rules differ | kind |
|---|---|---|
| `risk_safety_nonzero` | 45 | the yes/no indicator; disclosed in Amendment 4 |
| `nest_max` | 39 | nesting depth; disclosed in Amendment 4 |
| `state_heat_triggers` | 13 | a count measure, secondary |
| `state_danger` | 12 | a count measure, secondary |
| `def_safety` | 5 | a count measure, secondary |

- **No primary measure's silence changed in any repo**: not `struct_branch`, `risk_safety_score`,
  `amplified_cascading_flux` or `in_degree`. So the narrowing did not change which confirmatory cells are
  scored.
- In the **20 repos scored on the primary outcome**, the three count measures changed in **14 cells** — the
  number defect log 46 recorded — in bun, curl, ghostty, gnupg, libxml2, prometheus, rails, sphinx, spock and
  sqlmap; 8 of the 14 are in the 15 drawn repos. In the 31 repos scored on the keyword outcome they changed in
  20 cells. With the indicator and nesting depth, 54 cells changed in the 20 primary-outcome repos.
- Every one of those cells draws from the shared random stream, so the matched-control draws of every later
  repo differ between the two versions of the code. That is the disclosure of Amendment 5 section 1, now with
  its numbers.
- **Check on the method:** the silence values this job computes for the code as at `8fb7fe0` equal the 80
  values already published in `docs/sa3_placebo.json`.

**2. The window on the 15 drawn repos.** The window start equals the cut in all 15. It differs in seven
repos, all among the eight assessed earlier (commons-lang, curl, libxml2, ndpi, postgres, prometheus, redis),
as Amendment 4 said.

**3. Windows and usable commits.** In all 46 repos the window ends after it starts and usable commits are
above zero (smallest 2,696). The fault of defect log 59 touches no repo; `PU_window_assertion` equals the
frozen run.

**4. Completeness.** The registered measure is under 90% in the six repos already excluded (livecode 0.308,
macports-base 0.0, pwntools 0.795, root 0.473, wordpress 0.838, wrf-fortran 0.786) and in no other.
mediawiki reads 0.9004 and ghostty 0.912. Measured against the tree the numbers are the same to three
places in every repo. On control repositories the two differed only through `export-ignore` paths, which
suggests no real repo uses it to any extent; that reading was not checked further. `PU_new_completeness` therefore drops the same six repos.

**5. First-party files under `cache/`, `dist/`, `extern/`, `env/`** (defect log 55). In the 20 repos scored on
the primary outcome: go 19 (3 with scan rows), freebsd-src 15, postgres 14, mediawiki 13, django 9, rails 7,
moby 4, godot 2 (none scanned), the other twelve none. Outside them: fieldtrip 2,758 and wrf-fortran 710.
**The fault is real and, for SA3's scored repos, small**: at most 19 files in a repo.

**6. Universe files the history cannot touch:** none, in any repo. **`PU_reachable_universe` and
`PU_unreachable_made_reachable` equal the frozen run**; the owner's ruling on them changes nothing in SA3.

**8. Nesting coverage** is 100% of universe files in every repo that has a nesting file. It is absent for
racket (not measured, by design) and for the six scan-incomplete repos. `PU_nesting_floor` equals the frozen
run for the scored repos.

**9. Stored `.gitattributes` text:** the longest is 3,125 characters (bun). None is near the 200,000-character
cut.

**10. How the inputs were made** is recorded per repo in the JSON file.

Two clones are partial (blast, tcpip_historical). Both served the snapshot's tree and the archive listing
without a fetch.

## What this changes

Four of the ten sensitivities of Amendment 5 section 6 are now known to equal the frozen run for the scored
repos: `PU_reachable_universe`, `PU_unreachable_made_reachable`, `PU_window_assertion`, `PU_nesting_floor`.
`PU_new_completeness` drops no additional repo. They stay on the list and are reported as equal.

## The table

| repo | cut | window start = cut | window ends after start | usable commits | registered complete | against tree | generic dirs restorable (with scan rows) | universe untouchable | not regular | nesting share | .gitattributes longest |
|---|---|---|---|---|---|---|---|---|---|---|---|
| blast | 1545328894 | True | True | 104999 | 0.99 | 0.9898 | 28 (28) | 0 | 0 | 1.0 | 0 |
| bugzilla | 1292527579 | True | True | 9536 | 1.0 | 1.0 | 0 (0) | 0 | 0 | 1.0 | 0 |
| bun | 1740614535 | True | True | 14723 | 0.991 | 0.9912 | 0 (0) | 0 | 6 | 1.0 | 3125 |
| circuitpython | 1649260502 | True | True | 10993 | 0.981 | 0.9806 | 0 (0) | 0 | 92 | 1.0 | 931 |
| commons-lang | 1727098502 | False | True | 9564 | 1.0 | 1.0 | 0 (0) | 0 | 0 | 1.0 | 949 |
| cpython | 1587990139 | True | True | 118251 | 0.97 | 0.9699 | 0 (0) | 0 | 0 | 1.0 | 1808 |
| curl | 1711521975 | False | True | 39874 | 0.998 | 0.9978 | 0 (0) | 0 | 0 | 1.0 | 397 |
| discourse | 1694069849 | True | True | 56540 | 0.999 | 0.9985 | 0 (0) | 0 | 14 | 1.0 | 852 |
| django | 1574861786 | True | True | 33792 | 0.99 | 0.9902 | 9 (9) | 0 | 4 | 1.0 | 297 |
| effect | 1726441549 | True | True | 6303 | 0.996 | 0.9956 | 0 (0) | 0 | 2 | 1.0 | 0 |
| fieldtrip | 1554188328 | True | True | 18276 | 0.986 | 0.9859 | 2758 (1139) | 0 | 0 | 1.0 | 0 |
| freebsd-src | 1554637721 | True | True | 302381 | 0.95 | 0.9502 | 15 (15) | 0 | 1 | 1.0 | 348 |
| ghostty | 1757736731 | True | True | 5253 | 0.912 | 0.9117 | 0 (0) | 0 | 0 | 1.0 | 484 |
| gnupg | 1599546882 | True | True | 11033 | 0.991 | 0.9915 | 0 (0) | 0 | 0 | 1.0 | 191 |
| go | 1652752234 | True | True | 65483 | 0.949 | 0.9494 | 19 (3) | 0 | 0 | 1.0 | 639 |
| godot | 1723797256 | True | True | 40799 | 0.999 | 0.9993 | 2 (0) | 0 | 0 | 1.0 | 607 |
| impacket | 1600977554 | True | True | 3598 | 0.957 | 0.957 | 0 (0) | 0 | 0 | 1.0 | 0 |
| kubernetes | 1648129145 | True | True | 57095 | 0.995 | 0.995 | 49 (49) | 0 | 33 | 1.0 | 381 |
| libxml2 | 1703169264 | False | True | 7831 | 0.968 | 0.9684 | 0 (0) | 0 | 0 | 1.0 | 32 |
| livecode | 1494694686 | True | True | 4436 | 0.308 | 0.3079 | 0 (0) | 0 | 4 | 0.0 | 886 |
| macports-base | 1488102502 | True | True | 8910 | 0.0 | 0.0 | 0 (0) | 0 | 4 | None | 106 |
| mediawiki | 1344290553 | True | True | 52546 | 0.9 | 0.9004 | 13 (13) | 0 | 0 | 1.0 | 0 |
| micropython | 1684378296 | True | True | 17743 | 0.988 | 0.9881 | 0 (0) | 0 | 18 | 1.0 | 709 |
| moby | 1652381285 | True | True | 19971 | 0.977 | 0.9774 | 4 (4) | 0 | 5 | 1.0 | 122 |
| ndpi | 1727290163 | False | True | 5428 | 1.0 | 1.0 | 0 (0) | 0 | 58 | 1.0 | 98 |
| opencv | 1627140898 | True | True | 13472 | 0.999 | 0.9994 | 0 (0) | 0 | 0 | 1.0 | 0 |
| pandas | 1666376871 | True | True | 34019 | 1.0 | 1.0 | 0 (0) | 0 | 0 | 1.0 | 229 |
| postgres | 1640009249 | False | True | 65885 | 0.989 | 0.9894 | 14 (14) | 0 | 0 | 1.0 | 1579 |
| prometheus | 1739792897 | False | True | 7926 | 0.994 | 0.994 | 0 (0) | 0 | 0 | 1.0 | 0 |
| pwntools | 1591339295 | True | True | 3724 | 0.795 | 0.7955 | 0 (0) | 0 | 58 | 0.0 | 32 |
| racket | 1448736943 | True | True | 45548 | 0.99 | 0.9896 | 0 (0) | 0 | 0 | 0.0 | 0 |
| rails | 1620115833 | True | True | 45114 | 0.992 | 0.9917 | 7 (7) | 0 | 1 | 1.0 | 63 |
| redis | 1646040762 | False | True | 11956 | 0.994 | 0.994 | 0 (0) | 0 | 0 | 1.0 | 405 |
| root | 1616002819 | True | True | 95218 | 0.473 | 0.4727 | 0 (0) | 0 | 0 | 0.0 | 490 |
| runtime | 1645830550 | True | True | 121194 | 0.977 | 0.9772 | 9 (9) | 0 | 1 | 1.0 | 54 |
| scapy | 1655125979 | True | True | 4115 | 0.988 | 0.9876 | 0 (0) | 0 | 1 | 1.0 | 64 |
| sphinx | 1641798536 | True | True | 16513 | 0.989 | 0.9887 | 0 (0) | 0 | 0 | 1.0 | 0 |
| spock | 1613603490 | True | True | 2696 | 0.996 | 0.9962 | 0 (0) | 0 | 0 | 1.0 | 0 |
| sqlite | 1667841713 | True | True | 29116 | 0.989 | 0.9895 | 0 (0) | 0 | 0 | 1.0 | 0 |
| sqlmap | 1546720732 | True | True | 10339 | 0.997 | 0.9972 | 0 (0) | 0 | 0 | 1.0 | 232 |
| swift | 1670693664 | True | True | 73713 | 0.999 | 0.9993 | 0 (0) | 0 | 7 | 1.0 | 88 |
| tcpip_historical | 714580734 | True | True | 69979 | 0.996 | 0.9957 | 1 (1) | 0 | 0 | 1.0 | 0 |
| tensorflow | 1696422498 | True | True | 177077 | 0.995 | 0.9949 | 3 (3) | 0 | 2 | 1.0 | 0 |
| tigerbeetle | 1742940651 | True | True | 3180 | 1.0 | 1.0 | 0 (0) | 0 | 0 | 1.0 | 0 |
| wordpress | 1593577443 | True | True | 52180 | 0.838 | 0.8383 | 0 (0) | 0 | 0 | 0.0 | 0 |
| wrf-fortran | 1486160998 | True | True | 6664 | 0.786 | 0.7863 | 710 (539) | 0 | 65 | 0.0 | 0 |

## Added 2026-11-15: the last count, the placebo reproduced, and the seal (the owner-run job)

Run by the owner in their own terminal on 2026-11-15 at 6:33 AM Eastern (`tools/owner/prepare.py` at commit
`60fe528`): **PASS**, 409 seconds, no failed stage. This job bound the outcome files and the link harvest; its
public output is a fixed list of counts and verdicts, copied here as `docs/sa3_owner_report_run1.md` and
`.json`, `docs/sa3_seal_run1.json` and `docs/sa3_owner_run_log_run1.json`. No session has opened its
protected directory.

- **Qualifying commits that qualify only through a lower-case tracker key** (Amendment 5 section 7 item 5,
  defect log 61): **2 in the whole study** — one in bun, one in commons-lang — and none in the other 38
  repos. `PU_tracker_keys_case_sensitive` therefore differs from the frozen run by one commit in one scored
  repo (bun); commons-lang is not scored on the primary outcome.
- **The reference outcome builder reproduces the stored outcome file** in all 40 repos (the primary
  outcome's commits, as a set), with no disagreement between the stored links and the reference pattern
  re-applied to the stored messages.
- **The published placebo gate result is reproduced byte for byte** by the reference code on the real inputs
  of the 20 repos scored on the primary outcome. That speaks for the universe, the line counts, the primary
  outcome's file lists and the four primary predictors of those repos.
- **The reference code is unchanged since `8fb7fe0`**: the twelve modules the scorer loads, and `hist_meta`.
- **The external seal is written:** 397 entries; SHA-256 of `seal.json` `c99614eeb089ab52937a91b2082bb49796d5fd780c8fedcc0ce18fc3f7809417`. It holds the nine hashes the
  reference `lock` is expected to write.
- Nothing on disk changed during the run (6,384 entries recorded before and after).

**Amendment 5's order of operations:** steps (a) to (d) and (f) are done; the placebo half of (e) is done.
What remains before the owner runs `lock` and `score`: the comparison scorer and the blind seeded-fault test
of the check as a whole.
