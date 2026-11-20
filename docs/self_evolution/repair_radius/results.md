# V1/V2 repair radius results (Amendment 2)

## Counts

- merged PRs: 6487
- fix PRs (title prefix fix/bugfix/fixes/fixed, or label bug): 626
-   by title: 574
-   by bug label: 76
- fix PRs mapped to a first-parent commit: 615
- fix commits present in the diff cache: 590
- fix commits with >=1 Python engine function: 379
-   engine function touches summed over those commits: 1169
- pairs (A, later fix B within 30 d), both with engine functions: 39285

### Pair-level accounting (V1)

- B functions touched by A as well (not outside): 3399
- A functions touched (summed over used+dropped pairs): 106890
- A functions dropped (not in scan graph): 3073
- pairs used: 31830
- outside functions used: 79567
- outside B functions dropped (not in scan graph): 37707
-   ...file absent from scan (new/renamed/deleted file): 23456
- pairs dropped: no outside B function in scan: 6698
- outside functions with no file-mate (excluded from null-B rows): 129
-   ...file present, function absent (new/renamed/deleted function): 14251
- pairs dropped: A has no function in scan: 757
- share of pairs with lag <= 2 d: 0.10
- graphs used: {'n_scans': 80, 'median_nodes': 340.0, 'median_edges': 342.0, 'median_isolated_share': 0.12627986348122866}

### V1 stratum all, null A (repo-wide, same size decile)

outside B functions: 79567 (in 372 B commits)

| relation | observed | null | ratio | 95% interval |
|---|---|---|---|---|
| same_file | 26.5% | 12.0% | 2.21 | [1.90, 2.52] |
| callers1 | 3.5% | 1.4% | 2.45 | [2.07, 2.86] |
| callees1 | 3.7% | 2.3% | 1.60 | [1.37, 1.85] |
| either1 | 6.9% | 3.6% | 1.91 | [1.66, 2.16] |
| callers2 | 6.0% | 2.4% | 2.56 | [2.17, 2.96] |
| callees2 | 6.9% | 4.4% | 1.56 | [1.34, 1.81] |
| either2 | 12.6% | 6.6% | 1.91 | [1.66, 2.17] |
| callers3 | 7.2% | 2.9% | 2.50 | [2.12, 2.88] |
| callees3 | 8.1% | 5.6% | 1.45 | [1.24, 1.67] |
| either3 | 15.0% | 8.3% | 1.80 | [1.57, 2.03] |

### V1 stratum all, null B (file-mates)

outside B functions: 79438 (in 372 B commits)

| relation | observed | null | ratio | 95% interval |
|---|---|---|---|---|
| same_file | 26.6% | 26.6% | 1.00 | [1.00, 1.00] |
| callers1 | 3.5% | 1.5% | 2.25 | [1.95, 2.58] |
| callees1 | 3.7% | 3.5% | 1.05 | [0.94, 1.17] |
| either1 | 6.9% | 4.9% | 1.40 | [1.29, 1.50] |
| callers2 | 6.1% | 2.3% | 2.58 | [2.25, 2.95] |
| callees2 | 6.9% | 7.6% | 0.91 | [0.83, 0.99] |
| either2 | 12.6% | 9.7% | 1.29 | [1.21, 1.37] |
| callers3 | 7.2% | 2.6% | 2.75 | [2.35, 3.17] |
| callees3 | 8.1% | 9.0% | 0.90 | [0.83, 0.98] |
| either3 | 15.0% | 11.5% | 1.31 | [1.22, 1.40] |

### V1 stratum lag<=2d, null A (repo-wide, same size decile)

outside B functions: 11820 (in 360 B commits)

| relation | observed | null | ratio | 95% interval |
|---|---|---|---|---|
| same_file | 26.3% | 10.0% | 2.62 | [2.32, 2.93] |
| callers1 | 3.1% | 1.0% | 3.09 | [2.58, 3.65] |
| callees1 | 4.5% | 1.9% | 2.38 | [1.96, 2.85] |
| either1 | 7.5% | 2.8% | 2.64 | [2.26, 3.06] |
| callers2 | 5.1% | 1.7% | 2.91 | [2.46, 3.39] |
| callees2 | 7.8% | 3.6% | 2.19 | [1.83, 2.61] |
| either2 | 12.7% | 5.2% | 2.44 | [2.12, 2.79] |
| callers3 | 5.6% | 2.2% | 2.59 | [2.22, 3.00] |
| callees3 | 9.2% | 4.8% | 1.90 | [1.60, 2.25] |
| either3 | 14.6% | 6.9% | 2.13 | [1.87, 2.41] |

### V1 stratum lag<=2d, null B (file-mates)

outside B functions: 11795 (in 360 B commits)

| relation | observed | null | ratio | 95% interval |
|---|---|---|---|---|
| same_file | 26.4% | 26.4% | 1.00 | [1.00, 1.00] |
| callers1 | 3.1% | 1.4% | 2.30 | [1.91, 2.75] |
| callees1 | 4.5% | 3.6% | 1.24 | [1.08, 1.41] |
| either1 | 7.5% | 4.9% | 1.53 | [1.38, 1.69] |
| callers2 | 5.1% | 2.1% | 2.38 | [1.99, 2.84] |
| callees2 | 7.8% | 7.6% | 1.03 | [0.91, 1.14] |
| either2 | 12.7% | 9.6% | 1.32 | [1.21, 1.44] |
| callers3 | 5.6% | 2.4% | 2.38 | [2.00, 2.80] |
| callees3 | 9.2% | 9.2% | 1.00 | [0.90, 1.11] |
| either3 | 14.7% | 11.4% | 1.28 | [1.18, 1.39] |

### V1 stratum lag>2d, null A (repo-wide, same size decile)

outside B functions: 67747 (in 360 B commits)

| relation | observed | null | ratio | 95% interval |
|---|---|---|---|---|
| same_file | 26.6% | 12.4% | 2.15 | [1.85, 2.47] |
| callers1 | 3.5% | 1.5% | 2.37 | [1.97, 2.79] |
| callees1 | 3.6% | 2.4% | 1.50 | [1.25, 1.76] |
| either1 | 6.8% | 3.8% | 1.81 | [1.57, 2.07] |
| callers2 | 6.2% | 2.5% | 2.52 | [2.11, 2.95] |
| callees2 | 6.7% | 4.5% | 1.48 | [1.25, 1.72] |
| either2 | 12.5% | 6.8% | 1.84 | [1.60, 2.10] |
| callers3 | 7.5% | 3.0% | 2.48 | [2.08, 2.90] |
| callees3 | 8.0% | 5.8% | 1.38 | [1.18, 1.62] |
| either3 | 15.1% | 8.6% | 1.76 | [1.54, 1.99] |

### V1 stratum lag>2d, null B (file-mates)

outside B functions: 67643 (in 360 B commits)

| relation | observed | null | ratio | 95% interval |
|---|---|---|---|---|
| same_file | 26.6% | 26.6% | 1.00 | [1.00, 1.00] |
| callers1 | 3.5% | 1.6% | 2.24 | [1.89, 2.60] |
| callees1 | 3.6% | 3.5% | 1.02 | [0.90, 1.14] |
| either1 | 6.8% | 5.0% | 1.38 | [1.26, 1.49] |
| callers2 | 6.2% | 2.4% | 2.62 | [2.25, 2.99] |
| callees2 | 6.7% | 7.6% | 0.89 | [0.80, 0.97] |
| either2 | 12.5% | 9.8% | 1.29 | [1.20, 1.37] |
| callers3 | 7.5% | 2.7% | 2.80 | [2.40, 3.26] |
| callees3 | 8.0% | 9.0% | 0.89 | [0.81, 0.96] |
| either3 | 15.1% | 11.5% | 1.31 | [1.22, 1.42] |

## V1-R3 callers vs callees ([point, lo, hi])

- all k1: {'raw_callers_over_callees': [0.9342372881355933, 0.7782974060818088, 1.1209905348068867], 'excess_ratio_nullB_callers_over_callees': [2.1387911659214076, 1.7743903202378282, 2.5664873239649446]}
- all k2: {'raw_callers_over_callees': [0.882428466617755, 0.7300867351873329, 1.0624183951243436], 'excess_ratio_nullB_callers_over_callees': [2.851091712431525, 2.375829195018369, 3.4287266893700323]}
- all k3: {'raw_callers_over_callees': [0.8887685643564357, 0.7333858237169539, 1.0773300434070865], 'excess_ratio_nullB_callers_over_callees': [3.0426873164041757, 2.5191156903111773, 3.6698628365397]}
- lag<=2d k1: {'raw_callers_over_callees': [0.7039848197343453, 0.5736497665162548, 0.8689108527131783], 'excess_ratio_nullB_callers_over_callees': [1.8514301386204939, 1.460848379173516, 2.359288636557022]}
- lag<=2d k2: {'raw_callers_over_callees': [0.6504329004329005, 0.5242685721502586, 0.808613399714327], 'excess_ratio_nullB_callers_over_callees': [2.323293345894903, 1.8363778972358777, 2.940799243894621]}
- lag<=2d k3: {'raw_callers_over_callees': [0.6138248847926268, 0.49683033148112665, 0.756890024992895], 'excess_ratio_nullB_callers_over_callees': [2.3778584870219275, 1.8855166808327783, 2.9847381589850195]}
- lag>2d k1: {'raw_callers_over_callees': [0.9843169624432522, 0.7909565601912205, 1.2016606759911184], 'excess_ratio_nullB_callers_over_callees': [2.2025614470076413, 1.7702820322521047, 2.688543644062501]}
- lag>2d k2: {'raw_callers_over_callees': [0.9297703180212014, 0.75907270541932, 1.1275026313440193], 'excess_ratio_nullB_callers_over_callees': [2.9543857683295047, 2.4202333462998653, 3.5668196252526085]}
- lag>2d k3: {'raw_callers_over_callees': [0.9442275515895148, 0.7615927843787696, 1.161039242506149], 'excess_ratio_nullB_callers_over_callees': [3.166758468071096, 2.5833925842184415, 3.832168124801309]}

## Sanity 1: permutation (B shuffled across A within lag bins)

- rep 0: outside functions 71274
  - nullA: same_file 2.17 [1.93,2.43], either1 1.81 [1.60,2.02], either2 1.86 [1.66,2.06], either3 1.80 [1.61,2.00], callers2 2.33 [2.04,2.63], callees2 1.58 [1.37,1.82]
  - nullB: same_file 1.00 [1.00,1.00], either1 1.46 [1.35,1.56], either2 1.33 [1.25,1.41], either3 1.34 [1.26,1.42], callers2 2.75 [2.44,3.07], callees2 0.93 [0.86,1.00]
- rep 1: outside functions 71140
  - nullA: same_file 2.15 [1.90,2.42], either1 1.78 [1.58,1.98], either2 1.83 [1.64,2.03], either3 1.79 [1.62,1.97], callers2 2.26 [1.98,2.55], callees2 1.59 [1.39,1.82]
  - nullB: same_file 1.00 [1.00,1.00], either1 1.46 [1.36,1.56], either2 1.33 [1.26,1.41], either3 1.34 [1.27,1.42], callers2 2.72 [2.42,3.04], callees2 0.95 [0.88,1.02]
- rep 2: outside functions 71506
  - nullA: same_file 2.16 [1.90,2.43], either1 1.83 [1.63,2.03], either2 1.86 [1.66,2.07], either3 1.82 [1.64,2.02], callers2 2.31 [2.04,2.61], callees2 1.62 [1.39,1.87]
  - nullB: same_file 1.00 [1.00,1.00], either1 1.47 [1.37,1.58], either2 1.32 [1.25,1.40], either3 1.35 [1.27,1.43], callers2 2.73 [2.42,3.06], callees2 0.95 [0.88,1.01]

## Sanity 2: file size

- B outside functions: {'share in file with >=50 functions': 0.17929543655032865, '>=100': 0.03177196576470145, '>=200': 2.5136048864478993e-05, 'median functions in file': 26.0, 'share with <=5 file-mates': 0.17470810763256123}
- A functions: {'A_total_distinct_A_commits_funcs': 1131, 'in file >=50': 313, 'in file >=100': 87, 'in file >=200': 2}

## V2 (descriptive, n=10 pairs)

### issue 3929: cause PR 3923 -> fix PR 3939
```
{
 "cause_commit": "34fc2dc9839e6b8b43063705e280a7ff75f98e20",
 "fix_commit": "6b604f91a731a1c7a257db8ffb29f350f370fefb",
 "lag_days": 0.11,
 "scan": "2026-09-27",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [
  "gitgalaxy/core/detector.py::__init__",
  "gitgalaxy/core/detector.py::_active_coding_rules",
  "gitgalaxy/core/detector.py::_function_slice",
  "gitgalaxy/core/detector.py::_is_synthetic_satellite_name",
  "gitgalaxy/core/detector.py::coding_analysis",
  "gitgalaxy/core/detector.py::comment_analysis",
  "gitgalaxy/core/detector.py::splice"
 ],
 "fix_funcs_engine": [
  "gitgalaxy/galaxyscope.py::_active_languages",
  "gitgalaxy/galaxyscope.py::_extract_features_parallel"
 ],
 "cause_funcs_non_engine": 8,
 "fix_funcs_non_engine": 4,
 "same_function_overlap": [],
 "same_file_overlap": [],
 "cause_funcs_in_scan": 7,
 "outside_fix_funcs": 2,
 "outside_fix_funcs_in_scan": 2,
 "outside_relations": [
  {
   "func": "gitgalaxy/galaxyscope.py::_active_languages",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/galaxyscope.py::_extract_features_parallel",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  }
 ]
}
```
### issue 1193: cause PR 698 -> fix PR 1197
```
{
 "cause_commit": "864cfbc3cca81f5e6dbd6466b1a4ad5c2c779dd8",
 "fix_commit": "3dd93d2e658aec68f6e9923dbc0b57e9fa035423",
 "lag_days": 12.54,
 "scan": "2026-07-28",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [
  "gitgalaxy/core/prism.py::__init__",
  "gitgalaxy/core/prism.py::_compile_regex_matrix",
  "gitgalaxy/core/prism.py::_strip_single_line_comments"
 ],
 "fix_funcs_engine": [
  "gitgalaxy/core/prism.py::__init__",
  "gitgalaxy/core/prism.py::_compile_regex_matrix",
  "gitgalaxy/core/prism.py::_compile_single_line_delimiter_pattern",
  "gitgalaxy/core/prism.py::_guard_metadata_signal",
  "gitgalaxy/core/prism.py::_strip_segment_comments",
  "gitgalaxy/core/prism.py::_strip_single_line_comments"
 ],
 "cause_funcs_non_engine": 1,
 "fix_funcs_non_engine": 2,
 "same_function_overlap": [
  "gitgalaxy/core/prism.py::__init__",
  "gitgalaxy/core/prism.py::_compile_regex_matrix",
  "gitgalaxy/core/prism.py::_strip_single_line_comments"
 ],
 "same_file_overlap": [
  "gitgalaxy/core/prism.py"
 ],
 "cause_funcs_in_scan": 3,
 "outside_fix_funcs": 3,
 "outside_fix_funcs_in_scan": 3,
 "outside_relations": [
  {
   "func": "gitgalaxy/core/prism.py::_compile_single_line_delimiter_pattern",
   "same_file": true,
   "callers1": false,
   "callees1": true,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/core/prism.py::_guard_metadata_signal",
   "same_file": true,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/core/prism.py::_strip_segment_comments",
   "same_file": true,
   "callers1": true,
   "callees1": false,
   "callers2": true,
   "callees2": false,
   "callers3": true,
   "callees3": false
  }
 ]
}
```
### issue 3909: cause PR 3866 -> fix PR 3935
```
{
 "cause_commit": "786f6e3cd7cebd2d758a6b66564fc1f76240bf6a",
 "fix_commit": "69ba8dfcce319e8ed9be535ee2e2604067a25df3",
 "lag_days": 0.41,
 "scan": "2026-09-27",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [
  "gitgalaxy/cobol_refractor_controller.py::process_payload",
  "gitgalaxy/cobol_to_java_controller.py::main",
  "gitgalaxy/core/aperture.py::_load_gitignore_patterns",
  "gitgalaxy/core/guidestar_lens.py::_parse_makefile",
  "gitgalaxy/core/guidestar_lens.py::_parse_package_json",
  "gitgalaxy/core/guidestar_lens.py::_parse_toml_style_manifest",
  "gitgalaxy/core/guidestar_lens.py::_scan_gitattributes",
  "gitgalaxy/core/guidestar_lens.py::_scan_gitignore_evasion",
  "gitgalaxy/core/source_text.py::_utf16_without_bom",
  "gitgalaxy/core/source_text.py::decode_source",
  "gitgalaxy/core/source_text.py::read_source",
  "gitgalaxy/core/state_rehydrator.py::load_state",
  "gitgalaxy/galaxyscope.py::_process_file_worker",
  "gitgalaxy/galaxyscope.py::main",
  "gitgalaxy/metrics/chronometer.py::_load_ignored_revs",
  "gitgalaxy/metrics/tensor_scanner.py::_parse_gguf",
  "gitgalaxy/recorders/audit_recorder.py::generate_report",
  "gitgalaxy/recorders/llm_recorder.py::_macro",
  "gitgalaxy/recorders/llm_recorder.py::pct",
  "gitgalaxy/recorders/record_keeper.py::_seq_base",
  "gitgalaxy/recorders/record_keeper.py::record_mission",
  "gitgalaxy/recorders/sbom_recorder.py::_scan_single_file",
  "gitgalaxy/security/manifest_parser.py::_parse_gradle",
  "gitgalaxy/security/manifest_parser.py::_parse_package_json",
  "gitgalaxy/security/manifest_parser.py::_parse_package_lock",
  "gitgalaxy/security/manifest_parser.py::_parse_pip_conf",
  "gitgalaxy/security/manifest_parser.py::_parse_pyproject_toml",
  "gitgalaxy/security/manifest_parser.py::_parse_requirements_txt",
  "gitgalaxy/security/manifest_parser.py::_parse_yarn_lock",
  "gitgalaxy/security/manifest_parser.py::slice_manifest",
  "gitgalaxy/tools/cobol_to_cobol/cics_transaction_reader.py::_add",
  "gitgalaxy/tools/cobol_to_cobol/cobol_compiler_forge.py::flatten_copybooks",
  "gitgalaxy/tools/cobol_to_cobol/cobol_compiler_forge.py::main",
  "gitgalaxy/tools/cobol_to_cobol/cobol_dag_architect.py::extract_lineage",
  "gitgalaxy/tools/cobol_to_cobol/cobol_etl_unpacker.py::unpack_ebcdic_file",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::find_copybook",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::replacer",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::x_ray_dead_code",
  "gitgalaxy/tools/cobol_to_cobol/cobol_jcl_auditor.py::parse_jcl_intent",
  "gitgalaxy/tools/cobol_to_cobol/cobol_jcl_forge.py::analyze_cobol_intent",
  "gitgalaxy/tools/cobol_to_cobol/cobol_lexical_patcher.py::patch_lexical_traps",
  "gitgalaxy/tools/cobol_to_cobol/cobol_microservice_slicer.py::slice_business_logic",
  "gitgalaxy/tools/cobol_to_cobol/cobol_schema_forge.py::forge_schemas",
  "gitgalaxy/tools/cobol_to_cobol/cobol_system_limits_reporter.py::scan_system_limits",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::_systsin_member_text",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_guardrail.py::_project_java",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::_source_text",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_worklist.py::java_todos",
  "gitgalaxy/tools/cobol_to_java/port_runner.py::_read",
  "gitgalaxy/tools/network_auditing/full_api_network_map.py::auto_discover_swagger",
  "gitgalaxy/tools/network_auditing/full_api_network_map.py::map_physical_codebase",
  "gitgalaxy/tools/supply_chain_security/vault_sentinel.py::main",
  "gitgalaxy/tools/terabyte_log_scanning/pii_leak_hunter.py::_mask_validated",
  "gitgalaxy/tools/terabyte_log_scanning/pii_leak_hunter.py::main",
  "gitgalaxy/tools/terabyte_log_scanning/terabyte_log_scanner.py::main"
 ],
 "fix_funcs_engine": [
  "gitgalaxy/cobol_refractor_controller.py::main",
  "gitgalaxy/cobol_refractor_controller.py::process_payload",
  "gitgalaxy/cobol_to_java_controller.py::main",
  "gitgalaxy/core/ebcdic_codecs.py::register",
  "gitgalaxy/tools/cobol_to_cobol/cobol_dag_architect.py::code_view",
  "gitgalaxy/tools/cobol_to_cobol/cobol_dag_architect.py::extract_lineage",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::find_copybook",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::replacer",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::resolve_copybooks",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::shared",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::x_ray_dead_code",
  "gitgalaxy/tools/cobol_to_cobol/cobol_jcl_forge.py::analyze_cobol_intent",
  "gitgalaxy/tools/cobol_to_cobol/cobol_microservice_slicer.py::slice_business_logic",
  "gitgalaxy/tools/cobol_to_cobol/cobol_schema_forge.py::data_entries",
  "gitgalaxy/tools/cobol_to_cobol/cobol_schema_forge.py::forge_schemas",
  "gitgalaxy/tools/cobol_to_cobol/cobol_system_limits_reporter.py::scan_system_limits",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::_int",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::_systsin_member_text",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::load_galaxy_ir",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::runner_runs",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_decoder_forge.py::generate_decoder_util",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::_source_text",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::build_ticket",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::trim_ticket",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::write_port_tickets"
 ],
 "cause_funcs_non_engine": 3,
 "fix_funcs_non_engine": 1,
 "same_function_overlap": [
  "gitgalaxy/cobol_refractor_controller.py::process_payload",
  "gitgalaxy/cobol_to_java_controller.py::main",
  "gitgalaxy/tools/cobol_to_cobol/cobol_dag_architect.py::extract_lineage",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::find_copybook",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::replacer",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::x_ray_dead_code",
  "gitgalaxy/tools/cobol_to_cobol/cobol_jcl_forge.py::analyze_cobol_intent",
  "gitgalaxy/tools/cobol_to_cobol/cobol_microservice_slicer.py::slice_business_logic",
  "gitgalaxy/tools/cobol_to_cobol/cobol_schema_forge.py::forge_schemas",
  "gitgalaxy/tools/cobol_to_cobol/cobol_system_limits_reporter.py::scan_system_limits",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::_systsin_member_text",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::_source_text"
 ],
 "same_file_overlap": [
  "gitgalaxy/cobol_refractor_controller.py",
  "gitgalaxy/cobol_to_java_controller.py",
  "gitgalaxy/tools/cobol_to_cobol/cobol_dag_architect.py",
  "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py",
  "gitgalaxy/tools/cobol_to_cobol/cobol_jcl_forge.py",
  "gitgalaxy/tools/cobol_to_cobol/cobol_microservice_slicer.py",
  "gitgalaxy/tools/cobol_to_cobol/cobol_schema_forge.py",
  "gitgalaxy/tools/cobol_to_cobol/cobol_system_limits_reporter.py",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py"
 ],
 "cause_funcs_in_scan": 54,
 "outside_fix_funcs": 13,
 "outside_fix_funcs_in_scan": 13,
 "outside_relations": [
  {
   "func": "gitgalaxy/cobol_refractor_controller.py::main",
   "same_file": true,
   "callers1": true,
   "callees1": false,
   "callers2": true,
   "callees2": false,
   "callers3": true,
   "callees3": false
  },
  {
   "func": "gitgalaxy/core/ebcdic_codecs.py::register",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_cobol/cobol_dag_architect.py::code_view",
   "same_file": true,
   "callers1": false,
   "callees1": true,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::resolve_copybooks",
   "same_file": true,
   "callers1": false,
   "callees1": true,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_cobol/cobol_graveyard_finder.py::shared",
   "same_file": true,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/tools/cobol_to_cobol/cobol_schema_forge.py::data_entries",
   "same_file": true,
   "callers1": false,
   "callees1": true,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::_int",
   "same_file": true,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::load_galaxy_ir",
   "same_file": true,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::runner_runs",
   "same_file": true,
   "callers1": true,
   "callees1": false,
   "callers2": true,
   "callees2": false,
   "callers3": true,
   "callees3": false
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_decoder_forge.py::generate_decoder_util",
   "same_file": false,
   "callers1": false,
   "callees1": true,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::build_ticket",
   "same_file": true,
   "callers1": true,
   "callees1": false,
   "callers2": true,
   "callees2": true,
   "callers3": true,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::trim_ticket",
   "same_file": true,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::write_port_tickets",
   "same_file": true,
   "callers1": true,
   "callees1": true,
   "callers2": true,
   "callees2": true,
   "callers3": true,
   "callees3": true
  }
 ]
}
```
### issue 5525: cause PR 5512 -> fix PR 5590
```
{
 "cause_commit": "14fc9c7a55cd5d980e3008e586195046057b97c2",
 "fix_commit": "6af200ef0a0c85445beb5f9bffb33a6fa3a8b0f0",
 "lag_days": 0.64,
 "scan": "2026-10-18",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [
  "gitgalaxy/core/aperture.py::__init__",
  "gitgalaxy/core/aperture.py::_check_ignore_rules",
  "gitgalaxy/core/aperture.py::_license_texts",
  "gitgalaxy/core/aperture.py::_probe",
  "gitgalaxy/core/aperture.py::is_candidate_name",
  "gitgalaxy/core/aperture.py::looks_like_virtualenv",
  "gitgalaxy/core/guidestar_lens.py::_calculate_documentation_coverage",
  "gitgalaxy/metrics/chronometer.py::_determine_commit_bounds"
 ],
 "fix_funcs_engine": [
  "gitgalaxy/core/aperture.py::_has_foreign_license",
  "gitgalaxy/core/aperture.py::_has_root_license",
  "gitgalaxy/core/aperture.py::_license_family",
  "gitgalaxy/core/aperture.py::looks_like_virtualenv"
 ],
 "cause_funcs_non_engine": 1,
 "fix_funcs_non_engine": 1,
 "same_function_overlap": [
  "gitgalaxy/core/aperture.py::looks_like_virtualenv"
 ],
 "same_file_overlap": [
  "gitgalaxy/core/aperture.py"
 ],
 "cause_funcs_in_scan": 7,
 "outside_fix_funcs": 3,
 "outside_fix_funcs_in_scan": 3,
 "outside_relations": [
  {
   "func": "gitgalaxy/core/aperture.py::_has_foreign_license",
   "same_file": true,
   "callers1": true,
   "callees1": true,
   "callers2": true,
   "callees2": true,
   "callers3": true,
   "callees3": true
  },
  {
   "func": "gitgalaxy/core/aperture.py::_has_root_license",
   "same_file": true,
   "callers1": true,
   "callees1": true,
   "callers2": true,
   "callees2": true,
   "callers3": true,
   "callees3": true
  },
  {
   "func": "gitgalaxy/core/aperture.py::_license_family",
   "same_file": true,
   "callers1": false,
   "callees1": true,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  }
 ]
}
```
### issue 4758: cause PR 4740 -> fix PR 4761
```
{
 "cause_commit": "d207e3586a873b7c86e69230ca852b32892d0f32",
 "fix_commit": "a497a304f49010737210b9faf1ebd0e1d50fca19",
 "lag_days": 0.2,
 "scan": "2026-10-08",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [],
 "fix_funcs_engine": [],
 "cause_funcs_non_engine": 7,
 "fix_funcs_non_engine": 10,
 "same_function_overlap": [],
 "same_file_overlap": [],
 "cause_funcs_in_scan": 0,
 "outside_fix_funcs": 0,
 "outside_fix_funcs_in_scan": 0
}
```
### issue 3946: cause PR 3887 -> fix PR 3951
```
{
 "cause_commit": "0fa306dfdee5d697c49a900d1cfc2bc8d3d73135",
 "fix_commit": "42d503cef2a08f92381971bdab523caf4a026b5b",
 "lag_days": 0.47,
 "scan": "2026-09-27",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [
  "gitgalaxy/core/mainframe_boundary.py::extract_boundary",
  "gitgalaxy/core/state_rehydrator.py::load_state",
  "gitgalaxy/galaxyscope.py::_process_file_worker",
  "gitgalaxy/recorders/audit_recorder.py::_mainframe_facts_block",
  "gitgalaxy/recorders/llm_recorder.py::_root",
  "gitgalaxy/recorders/record_keeper.py::_seq_base",
  "gitgalaxy/recorders/record_keeper.py::record_mission",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::is_program",
  "gitgalaxy/tools/cobol_to_cobol/galaxy_ir.py::load_galaxy_ir",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_db2_forge.py::__init__",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_db2_forge.py::named",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_db2_forge.py::repository_source",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_db2_forge.py::sources",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::build_ticket",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_port_tickets.py::ticket_markdown",
  "gitgalaxy/tools/cobol_to_java/java_target.py::load_target",
  "gitgalaxy/tools/cobol_to_java/port_runner.py::_read"
 ],
 "fix_funcs_engine": [
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_db2_forge.py::db2_dates_source",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_decoder_forge.py::generate_decoder_util",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::_codec_put",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::_service_methods",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::entity_source",
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::key_source"
 ],
 "cause_funcs_non_engine": 5,
 "fix_funcs_non_engine": 9,
 "same_function_overlap": [],
 "same_file_overlap": [
  "gitgalaxy/tools/cobol_to_java/cobol_to_java_db2_forge.py"
 ],
 "cause_funcs_in_scan": 17,
 "outside_fix_funcs": 6,
 "outside_fix_funcs_in_scan": 6,
 "outside_relations": [
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_db2_forge.py::db2_dates_source",
   "same_file": true,
   "callers1": false,
   "callees1": true,
   "callers2": false,
   "callees2": true,
   "callers3": false,
   "callees3": true
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_decoder_forge.py::generate_decoder_util",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::_codec_put",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::_service_methods",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::entity_source",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  },
  {
   "func": "gitgalaxy/tools/cobol_to_java/cobol_to_java_repository_forge.py::key_source",
   "same_file": false,
   "callers1": false,
   "callees1": false,
   "callers2": false,
   "callees2": false,
   "callers3": false,
   "callees3": false
  }
 ]
}
```
### issue 2827: cause PR 2734 -> fix PR 2914
```
{
 "cause_commit": "860d091b013fa8740e386647c7c72aefcc2c3a84",
 "fix_commit": "d098b6ce04ccd0c2ead01e71df9e69fa2e9ff944",
 "lag_days": 4.48,
 "scan": "2026-09-04",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [
  "gitgalaxy/core/detector.py::splice",
  "gitgalaxy/galaxyscope.py::_calculate_risk_exposures"
 ],
 "fix_funcs_engine": [
  "gitgalaxy/core/detector.py::splice"
 ],
 "cause_funcs_non_engine": 2,
 "fix_funcs_non_engine": 1,
 "same_function_overlap": [
  "gitgalaxy/core/detector.py::splice"
 ],
 "same_file_overlap": [
  "gitgalaxy/core/detector.py"
 ],
 "cause_funcs_in_scan": 2,
 "outside_fix_funcs": 0,
 "outside_fix_funcs_in_scan": 0,
 "outside_relations": []
}
```
### issue 4859: cause PR 4843 -> fix PR 4860
```
{
 "cause_commit": "ad14a1ad9c6a50baf1c3246c35d4f48b037ae9f6",
 "fix_commit": "b6112c4fc3c93f2834fe60cd2fe77ca0bba582a0",
 "lag_days": 0.38,
 "scan": "2026-10-10",
 "cause_in_cache": false,
 "fix_in_cache": true,
 "cause_funcs_engine": [],
 "fix_funcs_engine": [],
 "cause_funcs_non_engine": 0,
 "fix_funcs_non_engine": 0,
 "same_function_overlap": [],
 "same_file_overlap": [],
 "cause_funcs_in_scan": 0,
 "outside_fix_funcs": 0,
 "outside_fix_funcs_in_scan": 0
}
```
### issue 5208: cause PR 4705 -> fix PR 5210
```
{
 "cause_commit": "2018d6b9157fa668f8bf2aa313e7e1c823b51622",
 "fix_commit": "3481f78710f1e8cda84b8989d7cf3e8f7cc5ec5c",
 "lag_days": 6.98,
 "scan": "2026-10-08",
 "cause_in_cache": true,
 "fix_in_cache": true,
 "cause_funcs_engine": [],
 "fix_funcs_engine": [],
 "cause_funcs_non_engine": 6,
 "fix_funcs_non_engine": 2,
 "same_function_overlap": [],
 "same_file_overlap": [],
 "cause_funcs_in_scan": 0,
 "outside_fix_funcs": 0,
 "outside_fix_funcs_in_scan": 0
}
```
### issue 2204: cause PR 1975 -> fix PR 2205
```
{
 "cause_commit": null,
 "fix_commit": "7efcc7299d7268cdcacaaaf89398b713bc7e301f",
 "note": "PR has no first-parent commit"
}
```

## POST HOC (exploratory; added after seeing the permutation result; not pre-declared; nothing above altered)

Null C: 200 draws per observed outside B function from functions touched by any fix commit in the 30 days before B (fallback: all fix commits, if <20 distinct nodes in A's scan), weighted by touch count, in A's scan, excluding the A set.

Concentration: {'distinct functions touched': 428, 'total touches': 1169, 'share on top 5%': 0.30367835757057315, 'share on top 20%': 0.5851154833190761, 'share of outside B functions touched by an earlier fix before A': 0.5616147397790542, 'rows using the all-time fallback pool': 0.0033807985722724243, 'rows': 79567}

### null C, stratum all (79567 functions, 372 B commits)

| relation | observed | null C | ratio | 95% |
|---|---|---|---|---|
| same_file | 26.5% | 30.6% | 0.87 | [0.74, 1.00] |
| callers1 | 3.5% | 3.9% | 0.88 | [0.74, 1.04] |
| callees1 | 3.7% | 4.3% | 0.86 | [0.73, 1.00] |
| either1 | 6.9% | 8.0% | 0.87 | [0.75, 0.99] |
| callers2 | 6.0% | 6.5% | 0.94 | [0.78, 1.10] |
| callees2 | 6.9% | 8.3% | 0.82 | [0.70, 0.97] |
| either2 | 12.6% | 14.3% | 0.88 | [0.75, 1.00] |
| callers3 | 7.2% | 7.4% | 0.97 | [0.81, 1.15] |
| callees3 | 8.1% | 10.1% | 0.81 | [0.69, 0.94] |
| either3 | 15.0% | 17.0% | 0.88 | [0.76, 1.01] |

### null C, stratum lag<=2d (11820 functions, 360 B commits)

| relation | observed | null C | ratio | 95% |
|---|---|---|---|---|
| same_file | 26.3% | 20.0% | 1.32 | [1.18, 1.46] |
| callers1 | 3.1% | 2.8% | 1.11 | [0.92, 1.32] |
| callees1 | 4.5% | 3.2% | 1.41 | [1.16, 1.68] |
| either1 | 7.5% | 5.9% | 1.27 | [1.11, 1.46] |
| callers2 | 5.1% | 4.8% | 1.07 | [0.88, 1.27] |
| callees2 | 7.8% | 6.1% | 1.29 | [1.08, 1.54] |
| either2 | 12.7% | 10.5% | 1.21 | [1.05, 1.38] |
| callers3 | 5.6% | 5.5% | 1.02 | [0.85, 1.20] |
| callees3 | 9.2% | 7.5% | 1.22 | [1.03, 1.44] |
| either3 | 14.6% | 12.7% | 1.15 | [1.01, 1.30] |

### null C, stratum lag>2d (67747 functions, 360 B commits)

| relation | observed | null C | ratio | 95% |
|---|---|---|---|---|
| same_file | 26.6% | 32.4% | 0.82 | [0.70, 0.95] |
| callers1 | 3.5% | 4.1% | 0.85 | [0.70, 1.01] |
| callees1 | 3.6% | 4.5% | 0.80 | [0.66, 0.94] |
| either1 | 6.8% | 8.4% | 0.82 | [0.70, 0.94] |
| callers2 | 6.2% | 6.8% | 0.92 | [0.76, 1.09] |
| callees2 | 6.7% | 8.7% | 0.77 | [0.64, 0.91] |
| either2 | 12.5% | 15.0% | 0.84 | [0.72, 0.96] |
| callers3 | 7.5% | 7.8% | 0.97 | [0.80, 1.15] |
| callees3 | 8.0% | 10.5% | 0.76 | [0.64, 0.90] |
| either3 | 15.1% | 17.8% | 0.85 | [0.73, 0.97] |

### permutation vs null C (B shuffled within lag bins)
- rep 0: same_file 0.96 [0.83,1.09], either1 0.94 [0.81,1.07], either2 0.96 [0.84,1.10], either3 0.97 [0.85,1.10], callers2 0.99 [0.85,1.14], callees2 0.92 [0.79,1.08]
- rep 1: same_file 0.94 [0.81,1.08], either1 0.92 [0.80,1.04], either2 0.95 [0.83,1.07], either3 0.97 [0.85,1.09], callers2 0.95 [0.81,1.11], callees2 0.94 [0.81,1.09]
- rep 2: same_file 0.95 [0.82,1.08], either1 0.94 [0.82,1.07], either2 0.97 [0.84,1.10], either3 0.99 [0.87,1.12], callers2 0.98 [0.84,1.13], callees2 0.95 [0.81,1.11]
