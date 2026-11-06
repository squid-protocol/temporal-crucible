# GG gate G-PY — engine Python functions vs tree-sitter-python (head snapshot, `gitgalaxy/` package)

- tree-sitter functions 3,145; engine functions 3,136
- (file, name, start line): recall **99.71%**, precision **100.00%** → **G-PY PASS** (gate ≥ 95% each)
- (file, name) only: recall 99.77%, precision 100.00%

Samples: tree-sitter-only `gitgalaxy/core/ebcdic_codecs.py:52 _codec_info`; `gitgalaxy/core/ebcdic_codecs.py:67 decode`; `gitgalaxy/core/ebcdic_codecs.py:71 decode`; `gitgalaxy/core/ebcdic_codecs.py:64 encode`; `gitgalaxy/core/ebcdic_codecs.py:75 encode`; `gitgalaxy/core/ebcdic_codecs.py:97 java_charset_name` · engine-only 
