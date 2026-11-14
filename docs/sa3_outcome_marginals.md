# SA3 outcome marginals and the frozen list of scored repos (2026-11-13, 9:25 PM Eastern)

**No structural predictor was read to produce this.** It is the output of `tools/sa3_outcomes.py` under the
registration as amended (Amendments 1–3), on the 46 rescans at engine `f71181aae7`. Per-repo detail (file
lists, commits, control pool) is in the study directory; the slim table is `docs/sa3_outcome_marginals.json`.

## Frozen: the repos scored on the primary outcome (HP)

Floor: ≥ 30 positive files from ≥ 20 qualifying commits, no commit supplying > 25% of the positives, ≥ 30
negatives. **This list does not change after any predictor is read.**

- **Drawn (confirmatory), 15:** bun, circuitpython, django, freebsd-src, ghostty, gnupg, go, godot, mediawiki, moby, pandas, rails, scapy, spock, sqlmap
- **Earlier eight (exploratory, reported separately), 5:** curl, libxml2, postgres, prometheus, sphinx

Scored on the keyword outcome (secondary): 31 repos.

## What the list is and is not

- Of the 15 drawn repos, C-family: bun, circuitpython, freebsd-src, ghostty, gnupg, godot. Languages first measured on
  2026-11-13: bun, ghostty, rails.
- **Six repos are still "scan incomplete"** (root, livecode, wrf-fortran, wordpress, pwntools, macports-base) after
  the excluder alignment of the second review and the export-ignore fix. The cause is not traced.
- Repos that fall out because the label is absent, not because nothing was fixed: sqlite, tcpip_historical, effect
  and tigerbeetle have no HP commit at all; kubernetes, discourse, swift and cpython have reverts but almost all
  undo code written after the snapshot, and their fix references live in pull-request text or use a form the
  patterns do not match (cpython writes `gh-NNNN:`).
- django (379 files from 743 commits) and go (910 from 1,279) are, as the first review warned, close to "ordinary
  work that names a ticket".

## Why six repos are "scan incomplete" — traced 2026-11-14, from structure only

The engine records what it refuses in `excluded_artifacts`, and prunes some directories without recording them
at all. Unit files (by this study's rule) that the scan did not read:

| repo | missing | where | the engine's reason |
|---|---|---|---|
| root | 6,446 of 12,225 | `interpreter/` (6,090) | directory never walked — it holds the bundled LLVM and cling |
| livecode | 726 of 1,049 | `engine/` (715) | "System Exclusion, Hidden Directory, or Dynamic Ignored Dir" |
| wrf-fortran | 203 of 950 | `var/` (148), `chem/` (49) | the same, plus a few array-payload and repetition blocks |
| wordpress | 175 of 1,082 | `wp-includes/` (110), `wp-content/` (62) | never walked (101) or ignored dir (69) |
| pwntools | 36 of 176 | `pwnlib/` | never walked (31) |
| macports-base | 128 of 128 | `src/` | never walked |

So the cause is one thing: **the engine's own rule for which directories to skip is wider than this study's
unit rule** (linguist's vendored list plus tests, docs, examples, tutorials). In root the engine is arguably
right — `interpreter/` is third-party code. In livecode it is not: `engine/` is the product. Nothing is changed
here: these six stay excluded and listed, as registered. Aligning the two rules would be a dated amendment and
would need the skipped directories classified one by one, which has not been done.

No minified or opaque-archetype files sit in the scored repos' scans (checked on bun, mediawiki, django, go,
rails, godot, freebsd-src: 0 minified, at most 1 obfuscation flag).

## Table

```
repo              lang     units compl HP files commits   top floor all-rev    KW   pool  inh  status
blast             cpp       6425  0.99        1       1  1.00    no       1   780   3714    0  ok
bugzilla          perl       198   1.0       29      21  0.17    no      29   141     82    0  ok
bun               zig        451 0.991      170     156  0.18   yes     176   201    488    0  ok
circuitpython     c         3130 0.981      393      69  0.14   yes     396    57    262   77  ok
commons-lang      java       250   1.0        3       3  0.33    no       4    36    827    0  ok
cpython           python     903  0.97       12      10  0.17    no      56   188   1359    0  ok
curl              c          450 0.998      264     571  0.16   yes     270   165   1948    0  ok
discourse         ruby      3386 0.999        3       3  0.33    no     113   430   1587    0  ok
django            python     807  0.99      379     743  0.10   yes     379    31    442    0  ok
effect            jsts       899 0.996        0       0  0.00    no       1   130    593    0  ok
fieldtrip         matlab    1676 0.986      154      49  0.29    no     155   160    916    0  ok
freebsd-src       c        37159  0.95      121      83  0.14   yes     161  1525   9351    0  ok
ghostty           zig        485 0.912       80      91  0.14   yes      80    14    199   55  ok
gnupg             c          466 0.991      171     245  0.16   yes     171    89    357    0  ok
go                go        2419 0.949      910    1279  0.04   yes     963   213   2983    0  ok
godot             c         2758 0.999      166     100  0.07   yes     222   336   3309  135  ok
impacket          python      89 0.957        5       8  0.40    no       6    22     80    0  ok
kubernetes        go        5734 0.995       16       9  0.25    no     201   255   2215   65  ok
libxml2           c          153 0.968       49     116  0.14   yes      57    46    815    0  ok
livecode          cpp        323 0.308                                                         scan_incomplete: rescan holds 31% of 1049 unit files in the tree
macports-base     c            0   0.0                                                         scan_incomplete: rescan holds 0% of 128 unit files in the tree
mediawiki         php       1058   0.9      223     297  0.13   yes     227   406    806    0  ok
micropython       c         1833 0.988       10       6  0.50    no      11   178   1006    0  ok
moby              go        1213 0.977       43      22  0.23   yes      46    57    575   28  ok
ndpi              c          312   1.0        8       6  0.50    no      10    57    500    0  ok
opencv            cpp       1574 0.999       61      17  0.67    no      61    39    424   12  ok
pandas            python     317   1.0       68      80  0.21   yes     102   158   2651    0  ok
postgres          c         2063 0.989      382     359  0.06   yes     459   427   2136    0  ok
prometheus        go         332 0.994       51      54  0.12   yes      58    80    550   37  ok
pwntools          python     140 0.795                                                         scan_incomplete: rescan holds 80% of 176 unit files in the tree
racket            racket     667  0.99       18      10  0.28    no      30    94    508    0  ok
rails             ruby      1316 0.992      139     105  0.05   yes     189   129   1636  108  ok
redis             c          165 0.994       35      35  0.34    no      35    62    569    0  ok
root              c         5779 0.473                                                         scan_incomplete: rescan holds 47% of 12225 unit files in the tree
runtime           csharp     257 0.977        4       3  0.75    no       7    49    172    0  ok
scapy             python     319 0.988       32      30  0.19   yes      39    68    277    0  ok
sphinx            python     175 0.989       31      42  0.07   yes      38    70    601    0  ok
spock             java       523 0.996       40      21  0.17   yes      40     8     41    0  ok
sqlite            c          376 0.989        0       0  0.00    no       0    99   1391    0  ok
sqlmap            python     352 0.997       77     253  0.16   yes      77    30    848    0  ok
swift             swift     7435 0.999       19      10  0.37    no      49    63    625   38  ok
tcpip_historical  c         6559 0.996        0       0  0.00    no       0   394   5354    0  ok
tensorflow        cpp       9770 0.995       18      14  0.17    no      28   365   6235    0  ok
tigerbeetle       zig        177   1.0        0       0  0.00    no       2     4    286    2  ok
wordpress         php        907 0.838                                                         scan_incomplete: rescan holds 84% of 1082 unit files in the tree
wrf-fortran       fortran    747 0.786                                                         scan_incomplete: rescan holds 79% of 950 unit files in the tree

clear the HP floor: 20 of 40 built (6 excluded before the label was read)
```
