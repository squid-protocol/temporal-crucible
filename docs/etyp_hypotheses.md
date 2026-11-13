# ETYP: does a function's edit-type history predict fixes? (DRAFT, drafted 2026-11-12)

**Status: DRAFT. Not approved by the owner. Nothing below has been computed.** No scorer exists. The
taxonomy and its exploratory, outcome-blind measurement are in [`etyp.md`](etyp.md); the tool
`tools/edit_types.py` reads no outcome and a test pins that.

Open items for the owner are marked **DECIDE**.

**Unit:** a function at a quarterly snapshot. **Tool:** `tools/etyp_eval.py` (to be written against the
approved text). **Taxonomy:** `tools/edit_types.py` as committed with this draft, frozen by file hash at
approval.

## 1. Why

- `docs/ceil.md`: recall at a 20%-of-lines budget is 0.30 achieved, 0.47 attainable with current
  covariates, 0.68 with perfect rate knowledge. The gap is rate heterogeneity we do not measure.
- `docs/kwnest.md`, `docs/rew.md`: structure is near-constant over a function's life, and rewiring beats
  edit count (+0.115) but loses to size.
- `docs/etyp.md`: 99% of function edits take one of 26 named types, and a function's next edit resembles
  its last at 1.70x (curl) and 1.96x (libarchive) a size-matched null.

Edit count treats every edit alike. If the kind of edit a function attracts is a stable property, the
count of *behaviour-changing* edits may carry rate information that the raw count dilutes with comments,
renames and message strings.

## 2. Prior work (**DECIDE: to be checked against the sources before approval; listed from memory**)

- Fluri, Wursch, Pinzger, Gall, "Change Distilling", IEEE TSE 2007: a tree-differencing taxonomy of
  fine-grained source changes.
- Giger, Pinzger, Gall, "Comparing fine-grained source code changes and code churn for bug prediction",
  MSR 2011: reported that fine-grained change counts outperform line churn. This is the closest prior
  result; ETYP-H1 would be a replication at function grain under a line budget.
- Falleri et al., GumTree, ASE 2014: the standard AST differ.
- Pan, Kim, Whitehead, "Toward an understanding of bug fix patterns", ESE 2009: fix patterns by syntax.
- Hassan, "Predicting faults using the complexity of code changes", ICSE 2009: change entropy.

## 3. Definitions

- **Behavioural edit:** an edit whose primary family is STRUCTURE or LOGIC.
- **Inert edit:** an edit whose primary family is COSMETIC or NAMING.
- **Predictors at snapshot t**, each over the function's edits in the trailing 8 quarters:
  `beh` = behavioural edits; `inert` = inert edits; `edits` = all edits.
- **Outcome:** a `fixlike_v2` v3c fix commit edits the function in (t, t+4 quarters].
- **Metric:** recall of outcome functions at a 20%-of-lines review budget, as in REW and CEIL.
- **Baselines:** the stronger of the two size orders; `edits`; REW's rewiring measure.
- **Margin:** the programme's standing delta = 0.02.

## 4. Claims

| id | claim | supported if |
|---|---|---|
| ETYP-H1 | `beh` ranks better than `edits` | lift over `edits` > 0.02, 90% CI excluding 0.02, in the primary repo and the same sign in the replication |
| ETYP-H2 | `beh` ranks better than the stronger size order | lift over size > 0.02, same rule |
| ETYP-H3 | negative control: `inert` does **not** rank better than `edits` | lift of `inert` over `edits` <= 0.02 |
| ETYP-H4 | guard: results are reported with and without edits flagged `err` (ERROR-node parses) | a verdict that flips between the two is recorded as inconclusive |

H2 is the bar nothing in this programme has cleared at function grain. H1 passing with H2 failing would
repeat REW's result with a different measure and is still worth knowing.

## 5. Repos

curl and libarchive were used to develop the taxonomy and are **not** eligible. **DECIDE:** primary
openssl, replication nDPI (both C, both with walk databases and v3c labels). harfbuzz is excluded until
the tool has a C++ lane.

## 6. Guards

Size control in every table; power stated before scoring (cells under 20 positives print UNDERPOWERED);
rename tracking as in the tool; no outcome joined before approval; the scorer is committed before it is
run.

## 7. What would change

- H1 and H2 hold: edit type is the first function-grain measure to beat size, and the per-type split
  (which atoms carry it) becomes the next exploratory study, on data this one has not seen.
- H1 holds, H2 fails: type sharpens history but size still wins; record it beside REW.
- H1 fails: the kind of edit adds nothing to the count of edits, and the unmeasured rate lies elsewhere.

## 8. Note added 2026-11-12, after the exploratory join (`etyp_fix.md`)

The join was run on curl and libarchive only, which were already ineligible here. It bears on this draft:

- LOGIC edits carry no forward signal (0.99 and 1.00 relative fix rate within a year); STRUCTURE carries a
  small one (1.05 and 1.14). The "behavioural edit" predictor in section 3 mixes the two and would be
  diluted. **DECIDE:** redefine the predictor as growth edits (BRANCH_ADD or STMT_ADD) before approval,
  or drop H1/H2 in favour of the labelling question below.
- The effect size seen is about 1.1x. A registration should state the power to detect that on openssl and
  nDPI before it is approved.
- A different claim looks better supported: that the type vector recognises fix class (extrinsic by TYPE
  and PREPROC) and separates fixes from non-fixes without reading the message. That would be registered
  against a hand-labelled sample, as `docs/otherfix_audit.md` was, not against a ranking metric.

## 9. Note added 2026-11-12, after the labelling check (`etyp_label.md`)

The third bullet of section 8 is withdrawn for fix-vs-non-fix: fitted on one burned repo and scored on the
other, the type vector reaches AUC 0.57-0.59 against the message label (size alone 0.54-0.55). Only the
extrinsic class is recognisable (0.67-0.71). No labelling claim should be registered on that basis, and
the hand-judged samples in `docs/otherfix_audit.md` were not scored.
