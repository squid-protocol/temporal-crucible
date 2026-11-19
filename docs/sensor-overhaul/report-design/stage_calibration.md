# Stage label: calibration (2026-11-19, exploratory)

**What the label is.** A name for the *pace of net growth* of a repository, from the number of functions in its quarterly scans: **expanding** (15% a year or more over the last three years), **growing** (5% to 15%), **steady** (-2% to 5%), **shrinking** (below -2%). It is not a product life-cycle claim (a mature project can be expanding; a young one steady). The report also prints the other indicators: edits per function per year, fix share and sweep share of last year's edits, share of older functions untouched for four quarters, project age.

**How the cut points were set.** The report generator was run on 19 repositories with scans (18 in the reference set plus nDPI and DPDK from the mock-ups; C, Go, Python and Rust; ages 8 to 29 years). The table below is the result. The cut points sit at round numbers near gaps in the growth distribution: a gap between sphinx (6.5%) and libgit2/ripgrep (3.9%) supports 5%; 15% separates the three fastest (prometheus, nugget-doom, curl) from harfbuzz (14.1%) and the rest; the only negative case is libxml2 (-3.0%: functions were removed in 2025 and 2026).

```
repository       lang       funcs  growth/yr  edits/fn/yr  fix share  sweep share  untouched  commits
prometheus       go         9,565      22.3%         0.69        15%          21%        69%   13,932
nugget-doom      c          4,155      17.5%         0.78        13%          22%        80%    4,645
curl             c          6,889      15.8%         2.57         7%          49%        40%   40,187
harfbuzz         c          7,314      14.1%         0.57         8%           6%        95%   21,592
redis            c         13,952      13.5%         0.25        14%          35%        88%   11,974
doomretro        c          2,501      12.4%         2.15        15%          14%        49%   21,429
ndpi             c          2,671      10.7%         0.92        10%          48%        51%    5,428
openssl          c         25,942       8.7%         0.91         6%          64%        47%   41,545
expat            c          1,226       7.8%         0.58         5%          18%        73%    4,862
scapy            python     4,790       7.8%         0.02        25%           0%        99%    5,454
dpdk             c         60,091       7.5%         0.20        22%          24%        90%   46,419
sphinx           python     5,972       6.5%         0.28         3%          29%        83%   16,626
ripgrep          rust       1,898       3.9%         0.01         4%           0%        99%    2,241
libgit2          c         11,044       3.9%         0.11         9%          22%        93%   12,535
dsda-doom        c          4,958       2.0%         0.22        21%           8%        90%    9,378
crispy-doom      c          5,914       1.4%         0.05         7%          19%        96%    7,509
sqlmap           python     2,641       1.1%         0.07        22%           0%        96%   10,339
chocolate-doom   c          5,169       0.2%         0.01         5%           0%        99%    4,893
libxml2          c          3,746      -3.0%         0.05        46%           0%        96%    7,831

19 repositories; growth per year: min -3.0%, median 7.8%, max 22.3%
cut points in use: {'expanding': 0.15, 'growing': 0.05, 'steady': -0.02}
```

**Counts under the cut points:** 3 expanding, 9 growing, 6 steady, 1 shrinking.

**Limits (stated plainly).**
- The cut points were chosen by looking at this same set, so the labels agree with it by construction. They have **not** been checked against how maintainers describe their projects; that is the next step (ask five maintainers, or compare with project status pages).
- Growth counts net functions in the scan: scanner coverage changes (for example, directories the scan skips by default, engine issue #8708) and mass moves can shift it.
- Three years of growth is a window, not a trend: a project that paused in the last three years reads "steady".
- Function counts mix product code, tests and examples as the scan sees them.
