# The LAWS sampling frame (M9), search phase

Built 2026-11-11, 8:39 to 10:17 AM Eastern, by `tools/laws_frame.py search --confirm --no-share`.
**Nothing has been drawn.** These files and their `SHA256SUMS` are the commitment M9 requires: "The SHA-256 of
the candidate file is committed and pushed **before** the draw."

GitHub search sliced by `created:` month windows with
`stars:>=500 fork:false archived:false language:"<L>"`, every window's pages fetched, and any window at the
1,000-result cap split and re-queried until none is truncated.

| language | frame size | windows | search calls | complete |
|---|---|---|---|---|
| kotlin | 1,840 | 226 | 226 | yes |
| php | 2,681 | 226 | 226 | yes |
| csharp | 3,466 | 226 | 226 | yes |
| rust | 4,126 | 226 | 226 | yes |
| c | 4,623 | 226 | 226 | yes |
| cpp | 6,191 | 226 | 226 | yes |
| go | 6,283 | 226 | 226 | yes |
| java | 6,513 | 226 | 226 | yes |
| python | 21,844 | 226 | 226 | yes |
| jsts | 23,493 | 452 | 452 | yes |

**81,060 candidates, 2,486 search calls, and not one truncated window**, so every frame is complete in M9's
sense. `jsts` takes twice the windows because the `language:` filter is primary-language only: JavaScript and
TypeScript are searched separately and unioned, and the >= 60% combined-bytes share is checked per candidate
later.

## These are ceilings, not eligible counts

A frame size is every repo at >= 500 stars created in that window with the language as its primary. The >= 60%
byte share and the history rules (>= 2,000 first-parent commits; >= 20 quarters with >= 50 source files; a commit
in >= 75% of quarters) all cut it, and the history rules need a clone. **No thin pools, though:** the smallest
frame, kotlin at 1,840, is 115 times the 16 repos a confirmatory language needs, so the risk this phase was run
to surface -- a language that cannot supply 16 -- does not appear.

## Why the share check is not in this phase

Checking all 81,060 candidates against the languages API would be about **16 hours of core quota**, shared with
churn and the shepherd. M9 does not ask for it: the draw permutes the candidates and takes "eligible repos in
that order until N pass the clone-time checks", so eligibility is evaluated **lazily, in draw order, and stops**.
`laws_frame.shortlist` does that -- it walks the permutation, keeps what clears the share bar, and stops at
`want x buffer`, a `--limit`, or the core-quota floor. At a plausible one-in-ten pass rate that is a few hundred
calls per language rather than tens of thousands.

An earlier version of the `search` step walked the whole frame. That was wrong, and the frame sizes above are
what made it obvious.
