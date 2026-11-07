# CMT-G — engine comment stream vs tree-sitter comment nodes (language-crucible)

- pooled over 35 languages with ≥ 200 reference comment lines: precision **97.5%**, recall **80.3%**
- C: P 99.9% / R 98.0%; C++: P 100.0% / R 99.4%
- **CMT-G FAIL** (pooled and C/C++ each ≥ 90%)

| language | precision | recall | engine lines | reference lines |
|---|---:|---:|---:|---:|
| cobol | 99.6% | 27.6% | 16,643 | 60,009 |
| typescript | 100.0% | 100.0% | 36,392 | 36,393 |
| php | 98.0% | 100.0% | 20,065 | 19,668 |
| dart | 100.0% | 100.0% | 15,423 | 15,423 |
| rust | 100.0% | 100.0% | 13,704 | 13,704 |
| c | 99.9% | 98.0% | 12,236 | 12,467 |
| zig | 99.7% | 89.0% | 8,916 | 9,995 |
| go | 100.0% | 99.2% | 8,781 | 8,848 |
| shell | 97.4% | 96.1% | 7,306 | 7,409 |
| perl | 65.2% | 99.9% | 10,052 | 6,560 |
| javascript | 99.5% | 99.9% | 6,017 | 5,994 |
| ada | 100.0% | 72.8% | 4,054 | 5,570 |
| python | 98.2% | 97.6% | 5,458 | 5,491 |
| fortran | 96.6% | 100.0% | 4,809 | 4,647 |
| powershell | 99.9% | 72.2% | 3,071 | 4,249 |
| csharp | 100.0% | 100.0% | 3,854 | 3,854 |
| cpp | 100.0% | 99.4% | 3,237 | 3,254 |
| groovy | 98.8% | 98.6% | 3,105 | 3,110 |
| lua | 98.6% | 97.5% | 2,830 | 2,861 |
| tcl | 89.3% | 99.9% | 3,142 | 2,807 |
| scala | 100.0% | 100.0% | 1,841 | 1,841 |
| scheme | 100.0% | 93.8% | 1,714 | 1,827 |
| java | 100.0% | 99.2% | 1,577 | 1,590 |
| matlab | 99.9% | 100.0% | 1,380 | 1,378 |
| swift | 100.0% | 100.0% | 1,362 | 1,362 |
| ruby | 100.0% | 92.0% | 861 | 936 |
| objective-c | 100.0% | 100.0% | 776 | 776 |
| solidity | 100.0% | 100.0% | 745 | 745 |
| makefile | 85.0% | 100.0% | 447 | 380 |
| yaml | 85.7% | 100.0% | 420 | 360 |
| css | 100.0% | 99.4% | 326 | 328 |
| kotlin | 100.0% | 100.0% | 321 | 321 |
| dockerfile | 98.0% | 100.0% | 255 | 250 |
| proto | 100.0% | 100.0% | 238 | 238 |
| apex | 100.0% | 100.0% | 212 | 212 |
| sqlite | 25.0% | 100.0% | 676 | 169 |
| html | 60.2% | 95.0% | 191 | 121 |
| mlir | 100.0% | 100.0% | 109 | 109 |
| haskell | 23.5% | 98.9% | 400 | 95 |
| nix | 96.2% | 100.0% | 53 | 51 |
| json | 100.0% | 100.0% | 46 | 46 |
| batch | 100.0% | 100.0% | 31 | 31 |

Skipped files: {'no grammar: binary_threat': 2, 'no grammar: td': 4, 'no grammar: postgresql': 2, 'no grammar: rexx': 25, 'no grammar: pli': 13, 'no grammar: livecode': 98, 'no grammar: jcl': 185, 'no grammar: hlo': 3, 'no grammar: hlasm': 20, 'no grammar: embedded_python': 14, 'no grammar: db2_sql': 8, 'no grammar: csd': 6, 'no grammar: m4': 8, 'no grammar: yacc': 5, 'no grammar: bms': 10, 'no grammar: blp': 5, 'no grammar: assembly': 227, 'no grammar: agc_assembly': 10, 'no grammar: plaintext': 106, 'no grammar: abap': 7}
Timed out (> 60 s per file; excluded, amendment): 14 ['cobol/cobrix/test5d_copybook.cob', 'cobol/cobrix/test5_copybook.cob', 'cobol/cobrix/test4_copybook.cob', 'cobol/cobrix/test2_copybook.cob', 'cobol/cobrix/test1a_copybook.cob', 'cobol/cobrix/test1_copybook.cob', 'cobol/cobrix/test15_copybook.cob', 'cobol/cobrix/test14_copybook.cob', 'cobol/cobrix/test13b_vrl_file_headers.cob', 'cobol/cobrix/test11_copybook.cob']
