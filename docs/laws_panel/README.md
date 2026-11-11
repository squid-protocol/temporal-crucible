# The LAWS eligible list (M9), post-exclusion

Built 2026-11-11 by `tools/laws_exclude.py`, from the committed raw frame in
[`../laws_frame`](../laws_frame/README.md). **Nothing has been drawn.** This directory and its
`SHA256SUMS` are what M9 and Amendment 8 item 1 require to be committed and pushed **before** the draw:
the list the seeded draw actually samples from, not the raw search output.

`<lang>_eligible.json` carries that language's post-exclusion candidates, every removal by name, and
**which rule removed it**, so the draw record is auditable repo by repo.

| language | candidates in | eligible out | removed | per-language fingerprint |
|---|---|---|---|---|
| kotlin | 1,840 | **1,839** | 1 | `3065d66b77813b3a…` |
| php | 2,681 | **2,680** | 1 | `a9ceae79171307e0…` |
| csharp | 3,466 | **3,465** | 1 | `a87ae2eb789df30a…` |
| rust | 4,126 | **4,121** | 5 | `c5cba65f17e08de2…` |
| c | 4,623 | **4,605** | 18 | `2dc5b93cb3c63628…` |
| cpp | 6,191 | **6,185** | 6 | `5dfbaf030f9f36af…` |
| go | 6,283 | **6,279** | 4 | `bdadc1c2f83c52e8…` |
| java | 6,513 | **6,507** | 6 | `5a2378c8a2859a15…` |
| python | 21,844 | **21,839** | 5 | `e891ff0beb8b3d73…` |
| jsts | 23,493 | **23,486** | 7 | `d2d79e95abdd14b3…` |

**81,060 candidates in, 81,006 eligible out, 54 removed.**

**M9 combined fingerprint:** `12e03a147f8b62b0c7a890aba5bd2c336f207c4e8145caff0cbec759ede56451`

(sha256 over '<lang>:<per-language digest>\n' for languages in sorted order)

## What was removed, and under which rule

| source | what it covers |
|---|---|
| registration PANEL Excluded | the named upstreams of every repo used in a temporal-crucible study |
| Amendment 1 item 3 | the 20-repo engine-tuning set, and the engine call-graph gate corpus (35 of 42 entries at engine `b873edc5b`, i.e. all but those flagged `callgraph: false`) |
| Amendment 2 item 6 | the three language-admission survey repos |
| operator decision 2026-11-11 | 2 of the 14 bare-name collisions, the ones carrying studied source — see [`../laws_collision_decisions.json`](../laws_collision_decisions.json) |

## Reproducibility

This list is derivable from committed inputs alone: the raw frame in `../laws_frame`, the exclusion
sources above (all in `tools/laws_exclude.py` and the register), and
`../laws_collision_decisions.json`. Re-running the tool on the same inputs reproduces the
fingerprint, so the commitment is checkable rather than merely recorded.

## Name collisions

`name_collisions.json` lists the 12 surviving candidates that share a bare name with an
excluded project. They are **kept** deliberately: dropping eligible repos that were never studied biases
the frame exactly as much as keeping repos that were. The two that carried studied source were excluded
by the operator decision above, with the evidence recorded.
