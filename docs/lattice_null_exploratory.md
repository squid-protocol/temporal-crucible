# EXPLORATORY — is the fingerprint lattice sparser than chance? (population DB v2.12.0-b64f42bf)

- random sample of 1,999,874 functions (loc ≥ 3); 61 signals ever present per function (28 never are: see gitgalaxy#8012)
- null = every signal independent, with a per-language probability that depends on function size (the KW size placebo), one simulated draw for the same functions

| | observed | independent-signals null | ratio |
|---|---:|---:|---:|
| distinct shapes | 149,312 | 235,222 | 0.63 |
| shapes seen once | 93,318 | 163,201 | 0.57 |
| share covered by the 200 commonest | 49.7% | 41.1% | |

## By number of signals present (k)

| k | possible combinations C(m,k) | functions | distinct shapes observed | null | observed / null |
|---:|---:|---:|---:|---:|---:|
| 0 | 1 | 1,406 | 1 | 1 | 1.00 |
| 1 | 61 | 9,810 | 28 | 36 | 0.78 |
| 2 | 1,830 | 45,135 | 159 | 233 | 0.68 |
| 3 | 35,990 | 137,752 | 653 | 1,120 | 0.58 |
| 4 | 521,855 | 250,606 | 1,908 | 3,586 | 0.53 |
| 5 | 5,949,147 | 340,153 | 4,711 | 8,675 | 0.54 |
| 6 | 55,525,372 | 351,212 | 9,241 | 17,036 | 0.54 |
| 7 | 436,270,780 | 296,467 | 15,023 | 28,255 | 0.53 |
| 8 | 2,944,827,765 | 237,089 | 20,258 | 38,354 | 0.53 |
| 9 | 17,341,763,505 | 153,338 | 22,736 | 42,395 | 0.54 |
| 10 | 90,177,170,226 | 85,057 | 21,885 | 38,016 | 0.58 |
| 11 | 418,094,152,866 | 43,590 | 18,690 | 27,977 | 0.67 |
| 12 | 1,742,058,970,275 | 22,824 | 13,479 | 16,403 | 0.82 |
| 13 | 6,566,222,272,575 | 11,877 | 8,723 | 7,947 | 1.10 |
| 14 | 22,512,762,077,400 | 6,179 | 5,240 | 3,285 | 1.60 |
| 15 | 70,539,987,842,520 | 3,322 | 2,908 | 1,205 | 2.41 |
| 16 | 202,802,465,047,245 | 1,767 | 1,602 | 406 | 3.95 |
| 17 | 536,830,054,536,825 | 972 | 882 | 149 | 5.92 |
| 18 | 1,312,251,244,423,350 | 526 | 472 | 63 | 7.49 |
| 19 | 2,969,831,763,694,950 | 309 | 279 | 26 | 10.73 |
| 20 | 6,236,646,703,759,395 | 176 | 165 | 20 | 8.25 |
| 21 | 12,176,310,231,149,295 | 98 | 96 | 13 | 7.38 |
| 22 | 22,138,745,874,816,900 | 51 | 51 | 5 | 10.20 |
| 23 | 37,539,612,570,341,700 | 55 | 50 | 7 | 7.14 |
| 24 | 59,437,719,903,041,025 | 26 | 20 | 7 | 2.86 |
| 25 | 87,967,825,456,500,717 | 24 | 17 | 2 | 8.50 |
| 26 | 121,801,604,478,231,762 | 12 | 11 | 0 | nan |
| 27 | 157,890,968,768,078,210 | 15 | 9 | 0 | nan |
| 28 | 191,724,747,789,809,255 | 14 | 3 | 0 | nan |
| 29 | 218,169,540,588,403,635 | 2 | 2 | 0 | nan |
| 30 | 232,714,176,627,630,544 | 3 | 3 | 0 | nan |
| 31 | 232,714,176,627,630,544 | 3 | 3 | 0 | nan |
| 32 | 218,169,540,588,403,635 | 1 | 1 | 0 | nan |
| 33 | 191,724,747,789,809,255 | 1 | 1 | 0 | nan |
| 34 | 157,890,968,768,078,210 | 1 | 1 | 0 | nan |
| 35 | 121,801,604,478,231,762 | 1 | 1 | 0 | nan |

## Signal pairs (both ≥ 0.5% prevalent: 820 pairs)

- pairs seen less than 1/10 as often as the null predicts (expected ≥ 200): 0; more than 10×: 0

**Holes** — combinations chance predicts often but code (almost) never builds:

| pair | observed | null expects | obs/exp |
|---|---:|---:|---:|
| Public / Exported Surface + Private Scope | 44,854 | 205,789 | 0.218 |
| Test Assertions + Private Scope | 12,599 | 52,152 | 0.242 |
| Test Assertions + Structured Logging | 910 | 2,865 | 0.318 |
| Error Exits + Mocks, Stubs & Skipped Tests | 398 | 1,160 | 0.343 |
| Private Scope + Mocks, Stubs & Skipped Tests | 727 | 1,920 | 0.379 |
| Test Assertions + Error Exits | 9,406 | 24,473 | 0.384 |
| Decorators, Annotations & Attributes + Private Scope | 18,935 | 41,771 | 0.453 |
| Comprehensions & Collection Pipelines + Mocks, Stubs & Skipped Tests | 474 | 975 | 0.486 |
| Branches & Conditionals + Test Assertions | 68,291 | 136,218 | 0.501 |
| Class / Struct Declarations + UI Components | 789 | 1,562 | 0.505 |
| UI Components + Regex & String Matching | 614 | 1,167 | 0.526 |
| UI Components + Error Exits | 1,342 | 2,535 | 0.529 |
| Class / Struct Declarations + Comprehensions & Collection Pipelines | 1,727 | 3,225 | 0.536 |
| Class / Struct Declarations + Regex & String Matching | 163 | 274 | 0.596 |
| Branches & Conditionals + Mocks, Stubs & Skipped Tests | 3,731 | 6,221 | 0.600 |
| UI Components + Private Scope | 1,642 | 2,711 | 0.606 |
| Decorators, Annotations & Attributes + Event Emitters | 2,624 | 4,269 | 0.615 |
| UI Components + Bitwise Operations | 1,188 | 1,894 | 0.627 |
| Class / Struct Declarations + Structured Logging | 645 | 1,003 | 0.643 |
| Branches & Conditionals + Decorators, Annotations & Attributes | 56,567 | 87,498 | 0.646 |

**Attractions** — combinations built far more often than chance:

| pair | observed | null expects | obs/exp |
|---|---:|---:|---:|
| Event Emitters + Event Listeners & Handlers | 8,275 | 828 | 10.0 |
| Process Exit, Eval & Shell Execution + Processes, IPC & RPC | 2,367 | 251 | 9.4 |
| Process Exit, Eval & Shell Execution + Error Exits | 13,715 | 1,492 | 9.2 |
| Async & Concurrency + Locks & Synchronization | 6,456 | 1,205 | 5.4 |
| Manual Memory Allocation + Resource Cleanup | 13,486 | 2,666 | 5.1 |
| Process Exit, Eval & Shell Execution + Print / Console Output | 5,120 | 1,012 | 5.1 |
| Event Emitters + Processes, IPC & RPC | 378 | 84 | 4.5 |
| Bitwise Operations + Regex & String Matching | 6,691 | 1,605 | 4.2 |
| File & Network I/O + Processes, IPC & RPC | 2,880 | 784 | 3.7 |
| Resource Cleanup + Processes, IPC & RPC | 1,760 | 535 | 3.3 |
| File & Network I/O + Resource Cleanup | 8,165 | 2,525 | 3.2 |
| Async & Concurrency + Dependency Injection | 4,019 | 1,260 | 3.2 |
| Dependency Injection + Mocks, Stubs & Skipped Tests | 225 | 75 | 3.0 |
| Resource Cleanup + Time & Date Logic | 2,419 | 815 | 3.0 |
| Class / Struct Declarations + Imports & Includes | 9,743 | 3,324 | 2.9 |

## One-step neighbourhood of the 200 commonest shapes

- each shape has 61 neighbours (add or drop one signal): 12,200 neighbour slots. **66%** of them exist in real code; 73% exist in the null population.

Caveats: one null draw (no CI); presence only; function-weighted; rules as of b64f42bf (before #8010/#8011/#8016); a size-only null ignores language idiom beyond per-language rates.
