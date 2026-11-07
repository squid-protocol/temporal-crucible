# CF-H1..H2 — comment changes of fixes; silent-patch detection (SCORED; aggregates only)

- commits 19,088; CVE 613 (silent 451); ordinary (no security words) 17,392

| claim | result | verdict |
|---|---|---|
| **CF-H1** CVE fixes add danger-language comments more than ordinary fixes | adds-danger: CVE 8.8% vs ordinary 5.4%; MH RR **1.61** (lo 1.10) | **SUPPORTED** |
| **CF-H2** comments add to WHERE for silent patches | AUC WHERE 0.720 → WHERE+CMT **0.707** (-0.013, lo -0.022); CMT alone 0.462 | **not supported** |

## Descriptive

- adds any comment line: CVE 44.2% vs ordinary 38.0%; MH RR 1.11
- silent CVE fixes that add danger comments: 8.4%
- top-10% enrichment: WHERE 3.15×, WHERE+CMT 2.86×

Runtime 226s · seed 2982.
