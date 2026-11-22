# Lattice-position stability of GitGalaxy's engine functions (EXPLORATORY; plan `docs/self_lattice_and_radius_plan.md` section A, declared before these numbers; 2026-11-20)

Position = the function's 37-dimensional vector in the scanner's reference frame (z-scored lens vectors from the lineage ledger over 180 daily scans). Displacement = Euclidean distance between a function's position at birth and at the first snapshot at least k days later, for engine functions (3+ lines) born after the first snapshot and still alive.
Scale for reading distances (final snapshot): median distance from a function to its nearest other function 0.11; between two random functions 2.79.

| age | all | Gemini era | Claude era | fleet era |
|---|---|---|---|---|
| 7 days: did not move at all | 86% (n 3,659) | 82% | 85% | 87% |
| 30 days: did not move at all | 71% (n 2,873) | 66% | 62% | 75% |
| 90 days: did not move at all | 32% (n 203) | 26% | 52% (n 40) | - |
| 30 days: movers' median displacement | 0.37 (n 845) | | | |
| 90 days: movers' median displacement | 0.36 (n 138) | | | |
| 30 days: p90 of displacement | 0.66 | 0.77 | 0.72 | 0.63 |

## Against the declared hypotheses
- **L1 (settles early; median displacement at 30 days at least 70% of that at 90 days; refuted below 50%).** By the declared statistic the answer is degenerate: the median displacement is 0.00 at 7 and 30 days (most functions do not move) and 0.17 at 90 days, so the ratio is 0.00, which the rule reads as refuted. The rule was badly chosen for data in which most functions never move. A movers-only version (added after seeing the numbers, so post hoc): movers' median displacement is 0.37 at 30 days and 0.36 at 90 days (ratio 1.02): a function that moves relocates once, by about three nearest-neighbour spacings, and does not keep drifting. The 90-day group is small (n = 203, mostly Gemini era).
- **L2 (larger functions move more).** Supported in direction in every era: rank correlation of 30-day displacement with lines at birth +0.32 (Gemini, n 142), +0.23 (Claude, n 927), +0.32 (fleet, n 1,782). Partly mechanical: the frame includes size-related dimensions and a longer function has more that can change.
- **L3 (more movement in the Gemini era than the fleet era).** Direction supported and modest: 66% did not move at 30 days in the Gemini era, 75% in the fleet era; p90 0.77 against 0.63. The Claude era has the most movers (62% stayed).

## Reading
On the lattice, most functions sit still after birth; the ones that move make one jump of local size (about 0.4 against a 2.8 distance between random functions) and then stay. Larger functions move more. This agrees with the identical-to-birth shares in `findings.md` and adds that movement is a step, not a drift. Not tested: whether the movers are the functions later repaired (deferred, plan section A), and whether 30 days is the right window for a young repo.
