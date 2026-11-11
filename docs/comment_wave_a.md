# Comment-extraction Wave A: instrument checks (EXPLORATORY)

**Status: exploratory, 2026-11-10.** No hypothesis, no p-values. These are checks of the instruments that any
comment hypothesis (Gemini's proposed COM-H1..H4) would read. They tell us which of those instruments can be used
as they are.

**Already known, not redone here:** CMT-G (`dc_hypotheses.md`) checked the engine's positional comment *lines*
against tree-sitter comment nodes. C scored precision 99.9% and recall 98.0%; C++ scored 100% and 99.4%. Wave A
checks the layers built on top of those lines:
- comment prose in patch scoring;
- documentation flags;
- attribution of comments to functions;
- the commented-out-code rule.

**Engine.** `main` at gitgalaxy 313ca6a75 (with #8200), plus the open PRs #8240 (`has_header_comment` and the curl
follow-ups), #8244 (the banner guard for 13 more languages) and #8245 (jcl positional comments), merged locally.
**Data.** curl pinned at `04bfe8fbbf` (the events' `pool_head`), a full clone. Scorer:
[`tools/comment_wave_a.py`](../tools/comment_wave_a.py).

## COM-E1: how much of the hunk-grain grammar is comment prose?

Every event's `git diff -U0` patch (1,756 events, of which 1,364 touch kept `.c`/`.h` files) was scored three
ways with `hunk_grammar.py`'s own parsing and the engine's C rules:
- **raw:** the diff text as it is. This is what the committed `hunk_grammar.md` measured before #109.
- **code:** the current Prism strip (#109, #116).
- **comments:** only the comment text that strip removes.

| class | n | fix-shaped: raw | code | comments | added branch hits: raw | code | comments |
|---|---|---|---|---|---|---|---|
| security-fix | 181 | 57% | 56% | 24% | 1,203 | 1,056 | 147 |
| regression | 238 | 49% | 47% | 14% | 883 | 753 | 130 |
| bugfix-bug | 209 | 49% | 48% | 21% | 822 | 692 | 130 |
| bugfix-fixes | 365 | 56% | 55% | 21% | 2,662 | 2,340 | 322 |
| control | 147 | 39% | 36% | 16% | 973 | 846 | 127 |
| introduced | 134 | 28% | 28% | 57% | 11,103 | 9,472 | 1,631 |
| revert | 77 | 10% | 10% | 14% | 472 | 343 | 129 |
| cve-followup | 13 | 23% | 23% | 0% | 11 | 10 | 1 |

- **The raw column reproduces the committed `hunk_grammar.md` exactly** (57/49/49/56/39/28/10/23%). That confirms
  the setup.
- **Comment prose was 14.4% of all added branch hits** (2,617 of 18,129): `if`, `for` and `while` inside comments.
- **It does not drive the gradient.** With comments stripped, every class moves by 3 points or fewer, and the
  security-fix minus control gap widens from 18 to 20 points. The fix-shaped gradient is code.
- **`docs/hunk_grammar.md` is not regenerated here.** Its hunk-grain rows regenerate correctly from nyx. But its
  file-grain alloc/cast columns read `dbs/keyword_pools_cache.json`, which exists only on melek, and they come out
  `n/a` without it. Regenerate it on melek with `python tools/hunk_grammar.py`. `hunk_grammar.py`'s cache file name
  now carries a strip version, so a cache from before #109/#116 is not silently reused.

## COM-E2: documentation flags on real C

`scan` over curl at the pinned head (500 C files outside tests/docs, 4,412 functions):

| per-function field | functions | share |
|---|---|---|
| `is_documented` (formal markup: Doxygen `/**`, `///`, tags) | 49 | 1.1% |
| `has_header_comment` (any explanatory comment block directly above) | 1,195 | 27.1% |
| `docstring` non-empty | 1,211 | 27.4% |

Before #8200, `is_documented` read 168 on the same code: 81% of those came from banner false positives. 624
docstrings held `#include`/`#if`/`#endif` lines; that is now 0.

**A hand audit of a random sample (seed 11):**
- **20 functions with `has_header_comment = 1`: 19 correct.** The miss is the tail of a trailing comment on a
  `#define` (`10-chars proto names. */`), which read as a header for the next function.
- **20 functions with a comment nearby but `has_header_comment = 0`: 17 correct.** They are `#endif /* X */` lines,
  struct-member comments and one-word `@unittest N` tags. The 3 misses are one curl idiom: a doc comment, then a
  `UNITTEST` prototype, then the definition. The walk stops at the prototype's `;`.

Both misses have a narrow engine fix: a header block must open with a comment marker, and the walk should step over
the function's own prototype. Those fixes are a gitgalaxy follow-up to #8240. **Reading: `has_header_comment` is
about 95% precise, with roughly 15% of the near-miss negatives recoverable. It is usable for C.**
`is_documented` is precise but nearly empty on traditional C, so it cannot carry a C documentation study.

## COM-E3: where do comment signals live?

| signal | file-level hits | in function bodies | share |
|---|---|---|---|
| `state_graveyard` (commented-out code) | 48 | 6 | 12.5% |
| `state_planned_debt` (TODO) | 16 | 7 | 43.8% |
| `state_fragile_debt` (FIXME/HACK/XXX) | 41 | 24 | 58.5% |
| `def_doc` | 322 | 55 | 17.1% |
| `def_ownership` | 1 | 0 | 0% |

**The attribution is correct.** Every one of the 42 `state_graveyard` hits not in a function body is outside every
function span, checked match by match. Before #8200, all of these columns were 0 at function grain.

**But `state_graveyard` itself is mostly not commented-out code.** Listing all 48 matches (`scan --src`):

| what the matched comment is | count |
|---|---|
| real commented-out code (`/* while(*p) */`, `/* j = ERR_R_ASN1_LIB; */`) | 2 |
| prototype notes (`/* int send(int, char *, int, int); */`) | 7 |
| prose: `/* for offsetof() */` include notes (33), `/* if a "head"-like request ... */`, `/* return the position after %time{} */` | 39 |

On curl the rule is about 4% precise. It fires on a keyword (`for`, `if`, `return`) followed by a call shape, and
curl annotates every `#include` with `/* for foo() */`.

## What this means for Wave B

- **COM-H1 (comment co-change by fix class) can use the code/comment split.** The hunk-grain prose contamination is
  real but small and does not bias the class gradient.
- **COM-H2 (TODO/FIXME at function grain) is now measurable**, because attribution works. The C counts are small,
  though: 16 TODOs and 41 FIXMEs in all of curl's C at one snapshot. It needs the whole event panel or more repos.
- **COM-H3 (commented-out code) must not run on `state_graveyard` as it is.** The earlier `signal_anatomy.md`
  result (a +10-point pre-event percentile gap) and nDPI's p = 0.054 most likely measure include-comment style, not
  dead code. Fix the C-family `dead_code` rule first: the keyword arm needs code shape (`for (`, `if (`, `x = y;`),
  not prose plus a call. Then re-measure precision here before any registration.
- **COM-H4 (comment drift) should use `has_header_comment` and `docstring`, not `is_documented`.**

Every Wave B study needs re-scans of the event pairs with the fixed engine: about 3,500 scans for curl alone. Each is
registered in `HYPOTHESES.md` before its scorer runs.
