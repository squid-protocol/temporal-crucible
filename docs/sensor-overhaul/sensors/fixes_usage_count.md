# `Fixes: <sha>` usage in candidate repositories (2026-11-18; counts only)

Script `tools/sensor/fixes_usage_count.py`, output `fixes_usage_count_output.txt`. Treeless bare clones (`git clone --bare --filter=tree:0`: commits only, 13 to 117 MB each, under a minute) under `temporal-crucible-pool/_fixes_count`. Pairs = non-merge commits with a `Fixes: <7-40 hex>` line that resolves to an earlier commit (reverts left out). The share of pairs where **both commits touch `.c` or `.h` files**, and where the fix and causing commit **share no file**, is from a random sample of 60 pairs per repository (trees fetched on demand): about plus or minus 10 points.

| repository | non-merge commits | `Fixes:` pairs | share of commits | median lag | within 30 d | a year or more | causing commit from 2019 on | both commits touch .c/.h (sample) | projected C/H pairs | share no file (sample) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **DPDK** | 46,419 | **17,590** | **37.9%** | 333 d | 18% | 48% | 8,712 | 83% | **about 14,700** | 22% |
| **Mesa** | 233,413 | **13,180** | 5.7% | 64 d | 39% | 21% | 10,793 | 73% | **about 9,700** | **30%** |
| QEMU | 127,227 | 5,355 | 4.2% | 247 d | 20% | 45% | 3,972 | 75% | about 4,000 | 18% |
| U-Boot | 101,560 | 3,443 | 3.5% | 234 d | 17% | 41% | 2,623 | 68% | about 2,350 | 20% |
| Xen | 48,450 | 1,723 | 3.6% | 511 d | 24% | 53% | 1,140 | 92% | about 1,580 | 18% |
| Open vSwitch | 20,903 | 1,613 | 7.8% | 239 d | 26% | 43% | 649 | 77% | about 1,240 | 18% |
| libvirt | 54,556 | 748 | 1.4% | 53 d | 40% | 26% | 658 | 83% | about 620 | 17% |
| OpenWrt | 72,925 | 2,419 | 3.4% | 18 d | 55% | 18% | 2,069 | **13%** | about 320 | 30% |
| systemd | 83,403 | 158 | 0.2% | 31 d | 50% | 24% | 116 | not sampled | | |
| Zephyr | 159,821 | 192 | 0.1% | 83 d | 38% | 23% | 179 | not sampled | | |
Reference: the Linux kernel 154,466 trailers, 34,349 pairs in the scanned core subsystems from 2014 (median lag 279 d, 45% a year or more, 11% sharing no file); OpenSSL 261 and FreeBSD 192 pairs.

**Reading.** Three repositories carry kernel-scale or near-kernel-scale numbers of named pairs: **DPDK** (about 14,700 C/H pairs; lags like the kernel's), **Mesa** (about 9,700, faster fixes, the highest share of fixes in a file the cause did not touch, 30%, so about 2,900 cross-file pairs) and **QEMU** (about 4,000); **U-Boot, Xen and Open vSwitch** give 1,200 to 2,400 each (enough for the larger shape cells but not the smallest); libvirt about 600. OpenWrt's pairs are mostly build files (13% C/H), systemd and Zephyr barely use the trailer. Together DPDK, Mesa, QEMU, U-Boot, Xen, Open vSwitch and libvirt would give about 33,000 pairs, as many as the kernel.
**Caveats.** Samples of 60; `.c`/`.h` only (Mesa and QEMU also have C++ and Rust, so the C/H share understates what a C++-aware run could use); trailer adoption varies by year (DPDK's causing commits fall from 2,980 in 2018 to 238 in 2026 because later causes have had less time to be fixed); a repository that mandates the trailer (DPDK) may include fixes that would otherwise go unlabelled, a different selection from the kernel's convention.
**Next, if taken:** full clones of DPDK first (46,000 commits, small), quarterly scans from 2018, `blast_radius.py`, the shape tables against the kernel's; then Mesa and QEMU.
