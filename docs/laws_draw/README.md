# The LAWS seeded draw

Run 2026-11-11 by `tools/laws_frame.py draw`, from the committed post-exclusion eligible list in
[`../laws_panel`](../laws_panel/README.md). **Seed 2982**, as registered.

The draw order is `random.Random(2982).sample` over each language's lower-cased, de-duplicated,
byte-sorted eligible candidates (M9). It depends only on the candidate SET, so it is reproducible from
the committed list: re-running the tool reproduces these records byte for byte, which was checked.

**What a draw order is.** It is not the panel. Per M9 and Amendment 2 item 2, the clone-time checks are
walked in this order and the panel is the first 16 (confirmatory language) or 8 (descriptive) that pass.
A candidate failing a clone-time check is replaced by **the next in this order**, never by a re-draw,
and each replacement is logged. Confirmatory status is decided by ACC-P on draws 1 and 2, so it is not
known yet and does not need to be.

| language | eligible | removed by the exclusion | list fingerprint | first in draw order |
|---|---|---|---|---|
| jsts | 23,486 | 7 | `d2d79e95abdd…` | `prem-k-r/materialyounewtab` |
| python | 21,839 | 5 | `e891ff0beb8b…` | `royalvane/clan` |
| java | 6,507 | 6 | `5a2378c8a285…` | `wenmingvs/androidprocess` |
| go | 6,279 | 4 | `bdadc1c2f83c…` | `weibaohui/k8m` |
| cpp | 6,185 | 6 | `5dfbaf030f9f…` | `xiaomi/mace` |
| c | 4,605 | 18 | `2dc5b93cb3c6…` | `trish0x2a/project-box` |
| rust | 4,121 | 5 | `c5cba65f17e0…` | `zhuowei/nft_ptr` |
| csharp | 3,465 | 1 | `a87ae2eb789d…` | `tastsong/crazycar` |
| php | 2,680 | 1 | `a9ceae791713…` | `spatie/crawler` |
| kotlin | 1,839 | 1 | `3065d66b7781…` | `sosauce/chocola` |

**81,006 eligible candidates across 10 languages; 54 removed by the registered exclusion before drawing.**

## Verification run at draw time

- **Reproducible:** re-running the draw reproduced a record identical byte for byte.
- **No excluded repo was drawn:** all 400 repos in the ten draw-order heads were checked against the 79
  excluded names (PANEL, Amendment 1 item 3 including the call-graph gate corpus, Amendment 2 item 6,
  and the two operator-decided collisions). None appeared.
- Each language's record carries the eligible file's SHA-256 **and** the list fingerprint, so the draw
  is tied to the exact committed list it came from.

## Why the draw reads this list and not the raw frame

The draw step previously read `frame/<language>.json`, the raw GitHub search output, and verified *that*
file's hash. Amendment 8 item 1 found the registered exclusion was implemented nowhere and that every
excluded repo still sat in the raw output, so the commitment check would have passed while the guard
failed silently. The draw now reads the post-exclusion list and verifies it against
`../laws_panel/SHA256SUMS`.
