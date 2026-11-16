# Sensor design: <name>

**Status:** idea | design | prototype | validated | shipped. **Replaces / splits:** `<risk_* column or new>`.

## 1. The question it answers
One sentence a person would ask. If two sensors answer the same question, merge them.

## 2. Construct and unit
What single thing is measured; plain units (counts, per-kLOC, callers, years); how it is referenced (repo's own history, role, percentile).

## 3. Inputs
Engine columns, call graph, git history, lineage ledger. Say which are already persisted and which are missing.

## 4. Drill-down
The ranked list behind the number: what it shows (file, line, function, age, owner, activity), ranking key, and the action it suggests.

## 5. Evidence
Research findings that shape it (with source docs), and prototype results.

## 6. What it does not claim
In particular: no risk or defect claim.

## 7. Acceptance checklist (GUIDE section 5)
| Test | Status |
|---|---|
| Not degenerate | |
| Construct validity (rank correlation with an independent measure) | |
| Not redundant | |
| Not just a keyword density | |
| Stable (if a trait) | |
| Discriminates a stated role | |
| Actionable (ranked list) | |
| Outcome relation reported, not claimed | |
| Replicates on the master-database sample | |

## 8. Engine work
Persisted fields, history needs, "not measured" cases.

## 9. Open questions
