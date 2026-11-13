# Proposal: a repo bank with one validated instrument, and two tiers

**The problem, stated precisely.** The work has been ping-ponging, but not because we jump from repo to
repo. On 2026-11-13 the conclusion reversed on the **same eight repos, same code, same cut** — only the fix
label changed, and pooled lift went from +0.082 ("breadth shown") to +0.009 ("not shown"). A fixed repo bank
would not have prevented that.

**What actually went wrong** is that three measurement stacks were built over the same repositories and never
shared:

| stack | what it built | its fix label |
|---|---|---|
| `xc_harvest` | events, and an **audited** label (2026-11-11) | FIXLIKE v1 / v3c |
| LAWS | quarterly structural walks | the history DB's `fix` flag |
| HR (11-13) | line deltas and hunk ranges | the same `fix` flag |

They were discovered to agree 98–100% **by accident, on 11-13**. The audit saying commons-lang's label is
**0.27 precise** predated HR-1 by two days; nothing required reading it, so nobody did, and a number went out
that reversed the next day.

The inventory shows the same fragmentation: **34 clones in the pool, 8 with walks, 8 with history, 8 with
line deltas, 13 with xc events.** The only repo set with a complete stack got it by accident, because LAWS
adopted the CGR eight as its development set.

## 1. The label card — done, and binding

`docs/LABEL_CARD.md` + `label_card.json` publish fix-label precision per repo for both labels, with their
sample sizes, the audit that measured them, and the basis on which that audit transfers to the LAWS flag.

**The rule: no study may use a fix label whose precision on that repo is unpublished, and a label under the
0.70 gate is descriptive or unused.**

It is enforced, not advertised. `tools/label_card.py --assert <repo> <label>` exits non-zero with a reason,
and `hist_replicate.py` now records `label_fit` per repo and **excludes unfit repos from the pool by default**.
Re-running HR-1's raw column under the card drops it from k=6 "breadth shown" to k=3 "not shown", with
commons-lang, prometheus and sphinx excluded by name. The old behaviour is still reachable with
`--allow-unfit`, so the published raw column stays reproducible — it just cannot be claimed any more.

This is the cheap half and the half that prevents recurrence.

## 2. Instrument v1 — freeze what the eight already have

Walks + history + line deltas + a carded label, versioned together with a manifest, so a study consumes the
instrument rather than rebuilding it. The eight already have every layer; what is missing is the version pin
and the manifest. LAWS2's frame (`tools/laws2.py`) is the **process** half of this — gates, controls,
registered parameters — and the bank is its **data** half.

## 3. Two tiers, or the bank destroys what it is for

A single bank mined forever makes every finding "seen", and in a year nothing produced can be confirmatory.
That is already true of the eight: tonight's work could only ever be replication.

- **Development tier** — freely reusable, deliberately spent, for building, debugging and exploration. The
  CGR eight are this and should be labelled as such.
- **Confirmatory tier** — drawn by rule, sealed, each repo spent **once** per registered hypothesis family,
  opened only when the hypothesis is registered and the instrument is frozen. openssl is already reserved.
- A repo moves development → spent, never back.

This is the thing LAWS got right in principle (exclusions, a holdout) and wrong in practice: it drew its panel
before checking the instrument could run on it.

## 4. Backfill, in cost order

1. **Carded labels for the repos that already carry studies** — curl, nDPI, openssl. They have events, no
   published precision of their own in this card.
2. **Walks for the 13 repos with events but no structural history.** That is the expensive step and the one
   that makes trajectory questions possible beyond the eight.
3. **libgit2's label.** It fails both gates (0.63 raw, 0.60 v3c) and is the one repo HR could not evaluate at
   all. One better label recovers a data point.

## What this does not fix

Pre-registration already worked: registering HR-1/2/3 before running them is what *caught* the reversal
rather than publishing it. The discipline is not what is broken, and a bank will not improve it. What a bank
fixes is the waste of measuring the same thing three times and the specific failure of a study not knowing
what an earlier study had already measured about its own inputs.
