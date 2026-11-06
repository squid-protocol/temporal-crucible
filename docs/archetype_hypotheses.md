# ARCH — are GitGalaxy's archetypes stable, and are they useful? — registered 2026-11-06, before any archetype × outcome statistic

**Why this battery.** GitGalaxy labels every function and file with an archetype: a nearest-centroid k-means label
from a frozen "brain". The program has never asked two questions about them on real history:

- **Stability.** Does a file keep its label while its code barely changes?
- **Usefulness.** Does the label tell a reviewer anything about where fixes land that file size does not already
  tell them?

This repo has hundreds of scanned snapshots per repository, so it can answer both.

**What has been looked at before this entry.**
- No archetype column has been related to any outcome in this repo, on any branch. This was checked with
  `git grep -i archetype` over `docs/` and `tools/` on `main`, `forward/history-asof` and `frec/function-recidivism`;
  the only hits are schema-drift notes.
- Before writing this entry, the author looked only at:
  - label value counts at curl's last study commit;
  - the `file_fingerprint` format;
  - the engine's classifier source.
- The brains were trained unsupervised on the gitgalaxy population corpus. No outcome label entered training.
- **All three repos are therefore unseen for every claim below.**

## The instrument

Three per-row labels are in scope. The repo-level label (`repo_composition_archetype`) is `Unvalidated` on every
snapshot of every DB here (withheld by gitgalaxy#4100), so it is out of scope.

| label | column | model | inputs |
|---|---|---|---|
| file cluster | `file_data.file_archetype` (`file_cluster_0..17`) | `GENERAL_FILE_INFERENCE_MODEL`, k = 18, RobustScaler with frozen medians/IQRs | file-local: size, within-file function z-stats, function-archetype mix, signal densities |
| composition file | `file_data.composition_file_archetype` (13 named) | `file_archetype_brain.json` | function-archetype mix + frozen-quantile ranks of size, imports, and **pagerank / blast radius** (repo-graph features) |
| function | `function_data.func_archetype` (13 named) | `GENERAL_FUNCTION_INFERENCE_MODEL`, k = 14, frozen scaler | function-local |

The brains are byte-identical across every engine build used below: `55c471d10`, `e246915aa`, `32619e4a5` and
`da852aa54` (checked by hashing the brain definitions at each SHA). Every analysis reads one DB, so one engine.

## Data

| part | curl | nDPI | openssl |
|---|---|---|---|
| stability (dense snapshots) | rescan DB, 3,547 study commits, engine `32619e4a5` | frec DB, 555 study commits, `32619e4a5` | 110 quarterly, `da852aa54` |
| file usefulness (U1–U3) | 105 quarterly as-of snapshots, `e246915aa` (the FWD/EA walk) | 43 quarterly, `e246915aa` | 110 quarterly, `da852aa54` |
| function usefulness (U4) | FREC event set: rescan DB | FREC event set: frec DB | not evaluable (no event-parent scans) |

Snapshots are ordered by git committer time. "Unchanged" means the git blob ID at the path is identical in both
snapshots (`git ls-tree -r`), read from the pool clone.

## Part S — stability

S1 is a binding instrument gate. S2–S5 are registered measurements with a pre-stated bar, not hypothesis tests.

| id | measure | pre-stated bar |
|---|---|---|
| **S1** (gate) | Consecutive snapshot pairs, C files with an unchanged blob: share keeping the same `file_archetype`. Functions inside unchanged blobs, matched by (path, name, start_line): share keeping the same `func_archetype`. | ≥ 0.999 on each repo, else the label is non-deterministic: an engine bug, filed before any usefulness verdict is read. |
| **S2** | Changed C files between consecutive snapshots: label retention by relative edit size \|Δcoding_loc\| / coding_loc in bins {0, (0, 1%], (1, 5%], (5, 20%], > 20%}, with Cohen's κ against the snapshot's own label marginals. | "Trackable" iff retention ≥ 0.90 in the (0, 5%] bins combined. |
| **S3** | Long horizon: C files present at t and at the first snapshot ≥ t + 365 d. Label agreement and κ; per-file count of distinct labels over its life (files with ≥ 10 snapshots). | Descriptive. |
| **S4** | Composition-label changes on unchanged blobs (S1's population): the context sensitivity that the graph features imply. | Descriptive. Reported beside S1, not gated. |
| **S5** | Changed files: flip rate by decile of the nearest-centroid margin d₂ − d₁ at t (from `file_fingerprint`). | Descriptive: is a low margin a usable "unstable" flag? |

Population drift (descriptive): the Jensen–Shannon divergence of each snapshot's C-file label distribution from the
previous snapshot and from the first.

## Part U — usefulness

**Unit and outcome (U1–U3).** Candidates are the C files (`language = 'c'`) of each quarterly snapshot t. A file is
positive if an on-master `security-fix` event, dated (committer time) in (t, t + 180 d], touches it (parent- or
child-side path). This is EA's outcome, verbatim.

**The archetype score is learned forward only.** At snapshot t, the training rows are the (file, snapshot s) rows of
every earlier snapshot whose outcome window has closed: s + 180 d ≤ t. Every training label is therefore known at t.
For each label a:

- P_a = positive training rows with label a;
- L_a = their summed `total_loc`;
- D = ΣP / ΣL, the global density;
- d(a) = (P_a + D · 50,000) / (L_a + 50,000): positives per line, shrunk toward D with a 50,000-line pseudo-mass.
- A label with no training rows gets D.

A snapshot is scored iff it has ≥ 1 positive and its training set has ≥ 1 positive.

| id | claim | score | statistic | supported iff |
|---|---|---|---|---|
| **U1** | The file-cluster label finds fixed files per line reviewed | d(`file_archetype`) | recall@20 (EA's rule: rank, ties by smaller `total_loc` then path; whole files while cumulative LOC ≤ 20%) | mean per-snapshot lift > 0 against **both** LOC-desc and LOC-asc, each with a one-sided snapshot-bootstrap lower bound > 0 |
| **U2** | Same, composition label | d(`composition_file_archetype`) | recall@20 | as U1 |
| **U3** | The file-cluster label adds to size | `total_loc` × d(`file_archetype`): expected positives under a per-line rate that depends on the label | per-snapshot AUC(score) − AUC(`total_loc`), ties = ½ | mean lift > 0, one-sided bootstrap lower bound > 0 |
| **U4** | The function label adds to size inside a fixed file | `loc` × d_f(`func_archetype`) | FREC's within-event AUC lift over function `loc` | mean lift > 0, one-sided event-bootstrap lower bound > 0 |

**U4's set-up is FREC's, verbatim (`tools/frec_eval.py`).**
- Events: curl `security-fix` + bug classes; nDPI `security-fix`.
- Candidates: the functions of touched C files at the parent, in files with ≥ 2 functions.
- Positive: span overlaps parent-side changed lines.
- Scored: events after the median event date, with ≥ 1 positive and ≥ 1 negative.
- d_f is learned from strictly earlier events' candidates (same-timestamp events never see each other), with a
  5,000-line pseudo-mass.

**Tests.**
- 5,000 bootstrap rounds, seed 2982. U1–U3 resample snapshots; U4 resamples events.
- α = 0.01 / 4 = 0.0025 one-sided, per (claim, repo).
- Fewer than 20 scored units makes a (claim, repo) *not evaluable*.
- *Replicated null* is claimed only by equivalence: the two-sided 90% CI of the lift against the stronger baseline
  lies inside [−0.02, +0.02]. Otherwise *not supported (inconclusive)*.

**Headline rule.** An archetype is **useful as a risk prior** iff its claim is SUPPORTED on every evaluable repo. It is
**repo-specific** if SUPPORTED on some. It is **not useful for this outcome** if none.

**Secondary (descriptive, no verdicts).**
- Recall@10/30.
- Per-label training density table at the last snapshot.
- U1–U3 with all fix classes on curl.
- Whether a label flip in the prior 365 d marks future fixes among files that changed in that window.

**Decision rule.**
- (a) U1 or U2 supported everywhere: open a gitgalaxy issue to surface the label's per-line fix density in the
  review-budget ranking. Any score weight still needs one more unseen repo.
- (b) Only U3/U4 supported: archetypes carry size-adjusted information but not enough to rank effort-aware. Record it
  as a feature for a combined model, not a ranking.
- (c) S1 fails: file the engine bug first; verdicts from that label stand only once it is fixed.
- (d) Nothing supported: archetypes stay a descriptive vocabulary in this program, and that is said plainly in
  `EXPERIMENTS.md`.

**Priors on record.**
- S1 **expected to pass** (both models are file- or function-local).
- S2 **uncertain**: the k = 18 file model has many neighbouring clusters.
- U1/U2 **leaning not supported**: every static structural score so far has tied or lost to LOC effort-aware (RW-H1).
- U3 **uncertain**.
- U4 **leaning not supported**: FREC showed function size is hard to beat.
