# BANK STATUS — what is fit to carry an analysis

Measured by `tools/bank_status.py`, not asserted. **Good standing** = every layer present **and** a
fix label whose precision on that repo clears 0.70.

| repo | lang | tier | walk | commits | deltas | events | best label | standing | missing |
|---|---|---|---|---|---|---|---|---|---|
| libxml2 | c | development | 106 | 7,831 | 42,900 | 3,160 | 0.86 | **GOOD** | — |
| prometheus | go | development | 55 | 8,753 | 70,338 | 2,576 | 0.83 | **GOOD** | — |
| ripgrep | rust | development | 32 | 2,241 | 5,328 | 319 | 0.82 | **GOOD** | — |
| sphinx | python | development | 69 | 16,626 | 66,773 | 3,624 | 0.78 | **GOOD** | — |
| postgres | c | development | 121 | 65,885 | 327,547 | 17,690 | 0.77 | **GOOD** | — |
| redis | c | development | 65 | 11,974 | 32,371 | 3,409 | 0.75 | **GOOD** | — |
| commons-lang | java | development | 97 | 9,919 | 27,206 | 1,083 | 0.70 | **GOOD** | — |
| libgit2 | c | development | 66 | 3,972 | 65,471 | 2,562 | 0.63 | not yet | label<0.70 |
| ndpi | c | pilot | — | — | — | 1,519 | 0.67 | not yet | walk, history, deltas, label<0.70 |
| curl | c | pilot | — | — | — | 8,352 | 0.63 | not yet | walk, history, deltas, label<0.70 |
| openssl | c | reserved | — | — | — | 8,996 | 0.50 | not yet | walk, history, deltas, label<0.70 |

**7 of 11 repos in good standing**, covering 5 languages: c, go, java, python, rust.


## Read this before planning an analysis

**Every repo in good standing is in the development tier — deliberately spent.** Nothing here can carry a
fresh confirmatory claim; it can show breadth or falsify. The confirmatory tier is currently **empty**:
openssl is reserved but has no walk, no history and no line deltas, so it cannot be opened for anything yet.
**The bank has no confirmatory capacity today.** That is the most important line in this file.

**The language mix will not support per-language claims.** Of the 7 in good standing, 3 are C and the other
four languages have exactly **one repo each**. A random-effects pool needs at least 2, and the sizing from the
development runs says LAW-2 needs ~2 repos per language and LAW-1 needs ~5. So today only **C** can carry a
pooled per-language statement; Go, Java, Python and Rust are single studies wearing a language label.

**Depth varies by 4x.** ripgrep has 32 quarterly snapshots against postgres's 121. Tests needing pairs five
years apart, or a split-half of history, are not available at the short end — ripgrep fell under HR's
positives floor twice for exactly this reason.

## What to build, in order of what it unlocks per unit of work

1. **Run FIXLIKE v3c on curl, nDPI and openssl.** Cheap — the rules exist, the events exist. On the CGR eight
   it moved pooled precision 0.38 → 0.77. If it does the same here it fixes the label on all three repos that
   carry the programme's founding claims. **Highest value per hour on this list.**
2. **A better label for libgit2** (0.63 raw, 0.60 v3c). It has every other layer; one label is all that stands
   between it and good standing.
3. **A second repo per non-C language.** The unlock for any cross-language claim. Four repos, chosen by rule
   rather than convenience, each needing walk + history + deltas + a carded label.
4. **Walks, history and line deltas for curl and nDPI.** Expensive, but they carry the founding claims and
   currently cannot be re-analysed at all — only their event files exist.
5. **Recall, not just precision.** The card publishes precision only; recall is known from the tuning set
   (~0.81) and was never measured on a fresh sample. A claim that depends on *not missing* fixes has no number
   to cite.
6. **OSV / CVE tables.** Only libxml2 had one in the HR runs, so LAW-9 was evaluable exactly once. Security
   outcomes need this layer and it does not exist for the bank.
7. **Seal a confirmatory tier.** Draw it by rule, give it every layer, and do not touch it until a hypothesis
   is registered against it.
