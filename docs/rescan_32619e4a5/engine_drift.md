# Engine drift: study-of-record scans vs rescan

**Descriptive, not a test.** Same commits, two engine builds. Nothing here is a
hypothesis result; it says how far the instrument moved under the study's data.

- old DB: `/srv/storage_16tb/projects/temporal-crucible/dbs/curl_out/curl_galaxy_master.db` (scanned 2026-09-13)
- new DB: `dbs/curl_out/curl_galaxy_master.db` — engine `32619e4a5e83c3ae7ba6e8969397e6db364ba8cf`
- commits compared: **3547** (old-only, not rescanned: 0)

## Coverage

- file rows: old 2745576, new 2800827, matched on (commit, path) 2712133
- files only in the new scan: 88694; only in the old scan: 33443

New-only files by language: yaml 41265, c 31786, perl 7749, markdown 5214, plaintext 1316, m4 620, makefile 293, xml 109, yacc 101, batch 89

Old-only files by language: plaintext 26186, m4 3645, python 2893, perl 719

## Schema drift

- file_data columns dropped: arch_feature_flags
- file_data columns added (76): arch_sys_config, composition_file_archetype, composition_file_z, declared_names, doc_umbrella, fam_cleanup, fam_concurrency, fam_connectivity, fam_credential, fam_crypto, fam_danger, fam_dead_code, fam_debt, fam_docs, fam_events, fam_guards, fam_io, fam_ipc, fam_memory, fam_ml_ai, fam_mutation, fam_regex, fam_serialization, fam_tests, fam_threat, fam_time, fam_ui, import_libraries, mitigation_telemetry, namespace_imports, pct_fam_cleanup, pct_fam_concurrency, pct_fam_connectivity, pct_fam_credential, pct_fam_crypto, pct_fam_danger, pct_fam_dead_code, pct_fam_debt, pct_fam_docs, pct_fam_events, pct_fam_guards, pct_fam_io, pct_fam_ipc, pct_fam_memory, pct_fam_ml_ai, pct_fam_mutation, pct_fam_regex, pct_fam_serialization, pct_fam_tests, pct_fam_threat, pct_fam_time, pct_fam_ui, pct_vec_api_exposure, pct_vec_churn, pct_vec_cognitive_load, pct_vec_concurrency, pct_vec_dead_code, pct_vec_documentation, pct_vec_safety_score, pct_vec_secrets_risk, pct_vec_spec_match, pct_vec_stability, pct_vec_state_flux, pct_vec_tech_debt, pct_vec_verification, raw_imports, rel_alloc_cleanup, rel_guard_balance, source_decode, source_encoding, threat_api_near_db_sink, threat_db_sinks, wrapped_debug_prints, wrapped_memory_alloc, wrapped_panics_and_aborts, wrapper_facts
- repo_data columns dropped: arch_feature_flags; added: arch_sys_config, copy_member_collisions, copy_member_gaps, missing_dependencies, network_edges_unrecorded, repo_composition_archetype, repo_composition_z, threat_api_near_db_sink, threat_db_sinks, wrapped_debug_prints, wrapped_memory_alloc, wrapped_panics_and_aborts

## Risk vector (file grain, matched files)

| column | pairs | % changed | mean old | mean new | mean abs Δ |
|---|---:|---:|---:|---:|---:|
| risk_safety_score | 2712133 | 62.9 | 51.86 | 40.56 | 12.48 |
| risk_cognitive_load | 2712133 | 37.8 | 25.56 | 23.46 | 2.248 |
| risk_tech_debt | 2712133 | 25.8 | 10.92 | 9.145 | 2.037 |
| risk_dead_code | 2712133 | 20.4 | 2.954 | 0.6256 | 2.363 |
| risk_verification | 2712133 | 12.8 | 14.39 | 14.04 | 0.3495 |
| risk_state_flux | 2712133 | 3.2 | 26.6 | 26.7 | 0.3895 |
| risk_api_exposure | 2712133 | 2.6 | 14.96 | 14.85 | 0.3183 |
| risk_documentation | 2712133 | 2.4 | 51.79 | 51.9 | 0.3468 |
| risk_spec_match | 2712133 | 0.4 | 73.82 | 74.08 | 0.4112 |
| risk_concurrency | 2712133 | 0.1 | 0.8445 | 0.8269 | 0.01752 |
| risk_secrets_risk | 2712133 | 0.0 | 1.396 | 1.398 | 0.00188 |
| risk_stability | 2712133 | 0.0 | 47.18 | 47.18 | 9.218e-05 |
| risk_churn | 2712133 | 0.0 | 0 | 0 | 0 |

## All shared numeric file columns, most-changed first

| column | pairs | % changed | mean old | mean new | mean abs Δ |
|---|---:|---:|---:|---:|---:|
| repo_z_score | 2712133 | 100.0 | 2.276 | 0 | 2.276 |
| pagerank_score | 2712133 | 99.8 | 0.001298 | 0.001258 | 0.0003165 |
| normalized_blast_radius | 2712133 | 99.8 | 1.298 | 1.258 | 0.3165 |
| sec_dead_code | 2712133 | 90.1 | 1.931 | 0.01587 | 1.916 |
| **risk_safety_score** | 2712133 | 62.9 | 51.86 | 40.56 | 12.48 |
| closeness_score | 2712133 | 47.3 | 0.01427 | 0.04473 | 0.03064 |
| internal_dependency_links | 2712133 | 47.0 | 3.41 | 5.741 | 2.339 |
| dependency_density | 2712133 | 47.0 | 0.02314 | 0.0401 | 0.01702 |
| **risk_cognitive_load** | 2712133 | 37.8 | 25.56 | 23.46 | 2.248 |
| cog_raw | 2712133 | 37.8 | 0.5284 | 0.483 | 0.04856 |
| control_flow_ratio | 2712133 | 37.7 | 0.1238 | 0.1004 | 0.02341 |
| struct_branch | 2712133 | 37.7 | 43.37 | 39.13 | 4.245 |
| betweenness_score | 2712133 | 27.2 | 5.188e-05 | 0.000295 | 0.0002588 |
| **risk_tech_debt** | 2712133 | 25.8 | 10.92 | 9.145 | 2.037 |
| structural_mass | 2712133 | 23.6 | 254.1 | 251.3 | 4.408 |
| popularity | 2712133 | 22.3 | 3.41 | 5.77 | 2.368 |
| producer_ratio | 2712133 | 21.7 | 0.228 | 0.2979 | 0.07529 |
| state_graveyard | 2712133 | 20.4 | 0.7921 | 0.175 | 0.622 |
| **risk_dead_code** | 2712133 | 20.4 | 2.954 | 0.6256 | 2.363 |
| func_internal_density | 2712133 | 20.3 | 0.085 | 0.08111 | 0.003901 |
| avg_func_complexity | 2712133 | 20.3 | 4.275 | 4.096 | 0.2025 |
| func_complexity_gini | 2712133 | 17.5 | 0.1927 | 0.1921 | 0.005939 |
| func_z_median | 2712133 | 15.6 | -0.09662 | -0.09387 | 0.01308 |
| func_z_max | 2712133 | 15.4 | 0.8085 | 0.8002 | 0.02316 |
| func_z_mean | 2712133 | 14.8 | 9.04e-07 | 7.615e-07 | 2.013e-05 |
| max_func_complexity | 2712133 | 14.0 | 14.84 | 14.42 | 0.6316 |
| **risk_verification** | 2712133 | 12.8 | 14.39 | 14.04 | 0.3495 |
| pct_z_above_5 | 2712133 | 3.8 | 21.05 | 20.35 | 0.7051 |
| threat_obfuscated | 2712133 | 3.6 | 1.196 | 0.07159 | 1.124 |
| **risk_state_flux** | 2712133 | 3.2 | 26.6 | 26.7 | 0.3895 |
| **risk_api_exposure** | 2712133 | 2.6 | 14.96 | 14.85 | 0.3183 |
| import_count | 2712133 | 2.4 | 4.852 | 4.77 | 0.08474 |
| **risk_documentation** | 2712133 | 2.4 | 51.79 | 51.9 | 0.3468 |
| pct_z_above_15 | 2712133 | 2.3 | 6.528 | 6.138 | 0.3917 |
| struct_macros | 2712133 | 2.1 | 12.57 | 12.59 | 0.03181 |
| state_print_hits | 2712133 | 1.5 | 2.26 | 2.139 | 0.1215 |
| struct_linear | 2712133 | 1.2 | 35.9 | 35.42 | 0.5152 |
| threat_eval_exec | 2712133 | 1.0 | 0.05674 | 0.03653 | 0.02021 |
| coding_loc | 2712133 | 0.9 | 211.6 | 211.7 | 0.2193 |
| doc_loc | 2712133 | 0.9 | 66.18 | 66.11 | 0.2193 |
| state_flux | 2712133 | 0.9 | 33.2 | 33.7 | 0.4997 |
| threat_bypasses | 2712133 | 0.9 | 0.0006279 | 0.01507 | 0.01444 |
| state_unreferenced | 2712133 | 0.8 | 1.256 | 1.285 | 0.0333 |
| struct_args | 2712133 | 0.8 | 10.93 | 10.94 | 0.009138 |
| avg_func_loc | 2712133 | 0.8 | 27.34 | 27.68 | 0.3509 |
| arch_events | 2712133 | 0.5 | 0.1517 | 0.1572 | 0.005544 |
| function_count | 2712133 | 0.5 | 4.941 | 4.953 | 0.01278 |
| threat_network_hooks | 2712133 | 0.4 | 0.05881 | 0.04906 | 0.00975 |
| struct_func_start | 2712133 | 0.4 | 4.95 | 4.956 | 0.0144 |
| **risk_spec_match** | 2712133 | 0.4 | 73.82 | 74.08 | 0.4112 |
| arch_api | 2712133 | 0.3 | 4.77 | 4.776 | 0.007035 |
| state_pointers | 2712133 | 0.3 | 53.28 | 53.31 | 0.02872 |
| state_safety_neg | 2712133 | 0.3 | 1.309 | 1.307 | 0.003707 |
| threat_homoglyphs | 2712133 | 0.3 | 0.004455 | 0 | 0.004455 |
| arch_io | 2712133 | 0.3 | 1.593 | 1.599 | 0.00784 |
| arch_import | 2712133 | 0.2 | 4.888 | 4.89 | 0.002571 |
| bitwise_ops | 2712133 | 0.2 | 2.518 | 2.453 | 0.06504 |
| arch_ipc | 2712133 | 0.2 | 0.5071 | 0.5086 | 0.002164 |
| raw_state_unreferenced | 2712133 | 0.2 | 1.354 | 1.356 | 0.001783 |
| state_heat_triggers | 2712133 | 0.2 | 2.187 | 2.19 | 0.002904 |
| avg_func_args | 2712133 | 0.1 | 1.079 | 1.078 | 0.0006542 |
| def_listeners | 2712133 | 0.1 | 0.3127 | 0.3161 | 0.003347 |
| struct_var_decl | 2712133 | 0.1 | 20.76 | 20.76 | 0.004033 |
| struct_upper_case | 2712133 | 0.1 | 1.949 | 1.953 | 0.004033 |
| raw_arch_api | 2712133 | 0.1 | 4.763 | 4.767 | 0.003924 |
| lit_code_blocks | 2712133 | 0.1 | 0.003009 | 0.005119 | 0.002111 |
| vectorized_math | 2712133 | 0.1 | 0.000903 | 0 | 0.000903 |
| def_safety | 2712133 | 0.1 | 3.36 | 3.363 | 0.002505 |
| **risk_concurrency** | 2712133 | 0.1 | 0.8445 | 0.8269 | 0.01752 |
| arch_concurrency | 2712133 | 0.1 | 0.04065 | 0.03955 | 0.001101 |
| arch_crypto | 2712133 | 0.1 | 0.001833 | 0.004192 | 0.003273 |
| arch_inline_asm | 2712133 | 0.0 | 0.001246 | 0.001746 | 0.0005 |
| state_cast_hits | 2712133 | 0.0 | 2.473 | 2.473 | 0.0007452 |
| arch_regex | 2712133 | 0.0 | 1.455 | 1.455 | 0.0004067 |
| struct_class_start | 2712133 | 0.0 | 5.157 | 5.158 | 0.001209 |
| def_doc | 2712133 | 0.0 | 1.228 | 1.228 | 0.0002887 |
| class_count | 2712133 | 0.0 | 0.6857 | 0.6864 | 0.0006563 |
| arch_scientific | 2712133 | 0.0 | 0.2501 | 0.2503 | 0.0002157 |
| def_encapsulation | 2712133 | 0.0 | 3.414 | 3.414 | 0.0002227 |
| state_memory_alloc | 2712133 | 0.0 | 1.358 | 1.358 | 0.0001338 |
| def_cleanup | 2712133 | 0.0 | 1.313 | 1.313 | 8.222e-05 |
| def_auth | 2712133 | 0.0 | 0 | 4.572e-05 | 4.572e-05 |
| has_credentials | 2712133 | 0.0 | 0.01513 | 0.01515 | 1.88e-05 |
| **risk_secrets_risk** | 2712133 | 0.0 | 1.396 | 1.398 | 0.00188 |
| threat_private_info | 2712133 | 0.0 | 0.07801 | 0.07803 | 1.88e-05 |
| struct_spaces | 2712133 | 0.0 | 165.7 | 165.7 | 1.549e-05 |
| **risk_stability** | 2712133 | 0.0 | 47.18 | 47.18 | 9.218e-05 |
| encapsulation_ratio | 2712133 | 0.0 | 0.829 | 0.829 | 2.459e-07 |
| arch_globals | 2712133 | 0.0 | 1.892 | 1.892 | 7.374e-07 |
| total_loc | 2712133 | 0.0 | 318.9 | 318.9 | 0 |
| ownership_entropy | 2712133 | 0.0 | 0 | 0 | 0 |
| silo_risk | 2712133 | 0.0 | 0 | 0 | 0 |
| raw_churn_freq | 2712133 | 0.0 | 0 | 0 | 0 |
| binary_anomaly | 2712133 | 0.0 | 0 | 0 | 0 |
| obfuscation_flag | 2712133 | 0.0 | 0 | 0 | 0 |
| **risk_churn** | 2712133 | 0.0 | 0 | 0 | 0 |
| state_danger | 2712133 | 0.0 | 0.306 | 0.306 | 0 |
| def_test | 2712133 | 0.0 | 0.3178 | 0.3178 | 0 |
| arch_ui_framework | 2712133 | 0.0 | 0.004503 | 0.004503 | 0 |
| struct_closures | 2712133 | 0.0 | 0.00306 | 0.00306 | 0 |
| struct_decorators | 2712133 | 0.0 | 0.5639 | 0.5639 | 0 |
| struct_generics | 2712133 | 0.0 | 0.1259 | 0.1259 | 0 |
| struct_comprehensions | 2712133 | 0.0 | 0.2169 | 0.2169 | 0 |
| def_ownership | 2712133 | 0.0 | 0.005089 | 0.005089 | 0 |
| state_planned_debt | 2712133 | 0.0 | 0.07442 | 0.07442 | 0 |
| state_fragile_debt | 2712133 | 0.0 | 0.1234 | 0.1234 | 0 |
| def_spec_exposure | 2712133 | 0.0 | 0 | 0 | 0 |
| arch_ssr_boundaries | 2712133 | 0.0 | 0.000643 | 0.000643 | 0 |
| arch_dependency_injection | 2712133 | 0.0 | 0.1679 | 0.1679 | 0 |
| def_telemetry | 2712133 | 0.0 | 0.9603 | 0.9603 | 0 |
| state_bailout_hits | 2712133 | 0.0 | 0.7708 | 0.7708 | 0 |
| state_halt_hits | 2712133 | 0.0 | 0.02876 | 0.02876 | 0 |
| def_sync_locks | 2712133 | 0.0 | 0.02621 | 0.02621 | 0 |
| def_freeze_hits | 2712133 | 0.0 | 4.097 | 4.097 | 0 |
| def_test_skip | 2712133 | 0.0 | 0.0008646 | 0.0008646 | 0 |
| struct_tabs | 2712133 | 0.0 | 0.4231 | 0.4231 | 0 |
| arch_hardware | 2712133 | 0.0 | 0 | 0 | 0 |
| arch_serialization | 2712133 | 0.0 | 0.0003871 | 0.0003871 | 0 |
| arch_time | 2712133 | 0.0 | 0.3545 | 0.3545 | 0 |
| llm_api | 2712133 | 0.0 | 0 | 0 | 0 |
| llm_orchestrator | 2712133 | 0.0 | 0 | 0 | 0 |
| llm_vector_store | 2712133 | 0.0 | 0 | 0 | 0 |
| llm_local_compute | 2712133 | 0.0 | 0 | 0 | 0 |
| ml_traditional | 2712133 | 0.0 | 0 | 0 | 0 |
| dl_frameworks | 2712133 | 0.0 | 0 | 0 | 0 |
| lazy_evaluation | 2712133 | 0.0 | 0.008475 | 0.008475 | 0 |
| struct_camel_case | 2712133 | 0.0 | 0.2643 | 0.2643 | 0 |
| struct_snake_case | 2712133 | 0.0 | 17.65 | 17.65 | 0 |
| struct_pascal_case | 2712133 | 0.0 | 0.04726 | 0.04726 | 0 |
| struct_short_vars | 2712133 | 0.0 | 2.192 | 2.192 | 0 |
| struct_long_vars | 2712133 | 0.0 | 0.1844 | 0.1844 | 0 |
| state_slop_duplicates | 2712133 | 0.0 | 0.009891 | 0.009891 | 0 |
| lit_diagrams | 2712133 | 0.0 | 0 | 0 | 0 |
| lit_headers | 2712133 | 0.0 | 0.0682 | 0.0682 | 0 |
| lit_links | 2712133 | 0.0 | 0.02514 | 0.02514 | 0 |
| threat_env_mutation | 2712133 | 0.0 | 0 | 0 | 0 |
| threat_crypto_math | 2712133 | 0.0 | 0 | 0 | 0 |
| threat_stego_imports | 2712133 | 0.0 | 0 | 0 | 0 |
| threat_extension_mismatch | 2712133 | 0.0 | 0 | 0 | 0 |
| threat_entropy | 2712133 | 0.0 | 0.02077 | 0.02077 | 0 |
| threat_tainted_injection | 2712133 | 0.0 | 0 | 0 | 0 |
| prompt_injection | 2712133 | 0.0 | 0 | 0 | 0 |
| agentic_rce | 2712133 | 0.0 | 0 | 0 | 0 |
| sec_unicode_steganography | 2712133 | 0.0 | 0 | 0 | 0 |
| sec_self_propagation | 2712133 | 0.0 | 0 | 0 | 0 |

## Repo grain

| column | pairs | % changed | mean old | mean new | mean abs Δ |
|---|---:|---:|---:|---:|---:|
| total_files | 3547 | 100.0 | 774.1 | 789.6 | 20.26 |
| total_excluded_artifacts | 3547 | 100.0 | 2276 | 2260 | 20.26 |
| total_loc | 3547 | 100.0 | 2.45e+05 | 2.509e+05 | 7726 |
| total_coding_loc | 3547 | 100.0 | 1.627e+05 | 1.67e+05 | 5685 |
| z_score | 3547 | 100.0 | 2.276 | 0 | 2.276 |
| avg_imports_per_file | 3547 | 100.0 | 4.727 | 4.794 | 0.2191 |
| network_avg_path_length | 3547 | 100.0 | 2.701 | 2.959 | 0.2941 |
| is_zero_dependency_mode | 3547 | 100.0 | 0 | 1 | 1 |
| struct_branch | 3547 | 100.0 | 3.33e+04 | 3.066e+04 | 3145 |
| struct_linear | 3547 | 100.0 | 2.758e+04 | 2.765e+04 | 634.3 |
| state_flux | 3547 | 100.0 | 2.573e+04 | 2.615e+04 | 1007 |
| state_heat_triggers | 3547 | 100.0 | 1678 | 1693 | 25.27 |
| arch_import | 3547 | 100.0 | 3746 | 3852 | 117.3 |
| struct_macros | 3547 | 100.0 | 9609 | 9917 | 307.3 |
| state_print_hits | 3547 | 100.0 | 1730 | 1706 | 49.92 |
| struct_spaces | 3547 | 100.0 | 1.274e+05 | 1.309e+05 | 4779 |
| struct_snake_case | 3547 | 100.0 | 1.358e+04 | 1.384e+04 | 424.4 |
| struct_upper_case | 3547 | 100.0 | 1545 | 1557 | 110.1 |
| threat_network_hooks | 3547 | 100.0 | 45.12 | 38.08 | 7.42 |
| sec_dead_code | 3547 | 100.0 | 1479 | 12.87 | 1466 |
| arch_api | 3547 | 100.0 | 3701 | 3701 | 107.2 |
| network_cyclic_density | 3547 | 99.9 | 0.01447 | 0.08241 | 0.06794 |
| struct_args | 3547 | 99.9 | 8397 | 8531 | 202 |
| state_graveyard | 3547 | 99.9 | 608.3 | 137.3 | 471.3 |
| audit_unknown_packages | 3547 | 99.9 | 3674 | 3696 | 79.37 |
| total_build_files | 3547 | 99.8 | 42.04 | 34.62 | 7.563 |
| network_assortativity | 3547 | 99.7 | -0.2952 | -0.3086 | 0.02174 |
| avg_encapsulation_ratio | 3547 | 99.4 | 0.8357 | 0.8325 | 0.006493 |
| network_modularity | 3547 | 99.4 | 0.4334 | 0.4227 | 0.01603 |
| state_unreferenced | 3547 | 99.3 | 972.1 | 1003 | 51.66 |
| struct_func_start | 3547 | 99.1 | 3825 | 3949 | 204.9 |
| def_safety | 3547 | 99.1 | 2581 | 2613 | 52.66 |
| arch_io | 3547 | 99.1 | 1236 | 1324 | 119.3 |
| arch_events | 3547 | 99.1 | 116.6 | 125.3 | 9.127 |
| bitwise_ops | 3547 | 99.1 | 1932 | 1929 | 51.79 |
| def_cleanup | 3547 | 99.1 | 1007 | 1025 | 22.92 |
| typosquat_hits | 3547 | 98.5 | 3.407 | 0 | 3.407 |
| threat_homoglyphs | 3547 | 98.5 | 3.407 | 0 | 3.407 |
| state_pointers | 3547 | 98.5 | 4.074e+04 | 4.15e+04 | 763.4 |
| total_functions | 3547 | 97.7 | 3818 | 3947 | 203.2 |
| arch_globals | 3547 | 97.6 | 1457 | 1553 | 95.52 |
| state_bailout_hits | 3547 | 97.6 | 597.9 | 605.2 | 22.21 |
| def_doc | 3547 | 97.5 | 939.4 | 995.3 | 56.44 |
| threat_eval_exec | 3547 | 97.2 | 43.38 | 32.52 | 11.4 |
| threat_bypasses | 3547 | 96.9 | 0.4801 | 11.53 | 11.05 |
| state_danger | 3547 | 96.6 | 234.2 | 238.6 | 4.485 |
| threat_obfuscated | 3547 | 96.6 | 934.2 | 54.82 | 879.5 |
| total_doc_files | 3547 | 95.8 | 50.55 | 45.01 | 6.279 |
| arch_regex | 3547 | 94.0 | 1133 | 1129 | 23.41 |
| struct_short_vars | 3547 | 93.5 | 1681 | 1724 | 47.83 |
| arch_ipc | 3547 | 92.8 | 387.8 | 393.4 | 5.674 |
| def_listeners | 3547 | 90.2 | 241 | 244 | 6.233 |
| struct_var_decl | 3547 | 90.2 | 1.611e+04 | 1.629e+04 | 632.7 |
| network_articulation_points | 3547 | 89.9 | 18.72 | 16.17 | 2.97 |
| total_classes | 3547 | 87.9 | 3964 | 4026 | 100.2 |
| struct_class_start | 3547 | 87.9 | 3964 | 4026 | 100.2 |
| state_cast_hits | 3547 | 87.9 | 1898 | 1929 | 43.5 |
| def_encapsulation | 3547 | 87.9 | 2630 | 2649 | 55.48 |
| total_config_files | 3547 | 86.9 | 2.824 | 14.49 | 11.66 |
| state_safety_neg | 3547 | 85.1 | 1012 | 1024 | 34.97 |
| threat_private_info | 3547 | 84.7 | 67.03 | 60.15 | 7.859 |
| def_freeze_hits | 3547 | 81.6 | 3133 | 3196 | 62.81 |
| audit_binary_anomalies | 3547 | 81.4 | 5.092 | 7.882 | 2.79 |
| lit_links | 3547 | 76.6 | 19.22 | 22.94 | 3.717 |
| state_planned_debt | 3547 | 76.5 | 64.6 | 58.74 | 9.526 |
| vectorized_math | 3547 | 69.0 | 0.6904 | 0 | 0.6904 |
| struct_decorators | 3547 | 64.1 | 436.1 | 432.4 | 6.001 |
| def_test | 3547 | 63.0 | 243 | 253.4 | 10.36 |
| struct_comprehensions | 3547 | 61.0 | 167.1 | 167.3 | 2.721 |
| struct_camel_case | 3547 | 55.2 | 280.3 | 205.7 | 81.82 |
| arch_scientific | 3547 | 55.0 | 191.3 | 195.9 | 4.628 |
| arch_crypto | 3547 | 49.6 | 1.994 | 3.205 | 3.096 |
| state_halt_hits | 3547 | 49.3 | 22.06 | 23.3 | 1.384 |
| lit_code_blocks | 3547 | 49.1 | 2.301 | 3.914 | 1.614 |
| arch_concurrency | 3547 | 45.0 | 31.23 | 37.81 | 6.874 |
| state_fragile_debt | 3547 | 42.3 | 95.78 | 97.23 | 4.264 |
| arch_dependency_injection | 3547 | 42.0 | 128.4 | 144.4 | 15.96 |
| arch_inline_asm | 3547 | 38.2 | 0.9529 | 1.335 | 0.3823 |
| struct_pascal_case | 3547 | 36.0 | 49.93 | 36.94 | 14.6 |
| struct_long_vars | 3547 | 33.8 | 157 | 162.7 | 37.71 |
| threat_entropy | 3547 | 33.0 | 15.88 | 20.8 | 4.916 |
| lit_headers | 3547 | 30.8 | 52.15 | 57.72 | 5.571 |
| total_test_files | 3547 | 30.3 | 29.33 | 30.06 | 0.8198 |
| arch_time | 3547 | 26.3 | 272 | 272.8 | 2.488 |
| state_memory_alloc | 3547 | 25.5 | 1038 | 1056 | 18.21 |
| def_test_skip | 3547 | 22.4 | 0.6611 | 20.85 | 20.19 |
| state_slop_duplicates | 3547 | 20.3 | 9.565 | 8.067 | 2.505 |
| def_telemetry | 3547 | 19.7 | 734.3 | 872.2 | 137.9 |
| def_ownership | 3547 | 9.0 | 4.262 | 3.907 | 0.3871 |
| def_sync_locks | 3547 | 8.3 | 20.26 | 20.06 | 0.2478 |
| struct_closures | 3547 | 7.6 | 2.488 | 2.342 | 0.1505 |
| lazy_evaluation | 3547 | 7.4 | 6.629 | 6.48 | 0.1483 |
| struct_tabs | 3547 | 7.2 | 323.6 | 345.4 | 21.89 |
| struct_generics | 3547 | 2.8 | 96.29 | 96.4 | 0.1139 |
| def_auth | 3547 | 1.7 | 0 | 0.03496 | 0.03496 |
| arch_serialization | 3547 | 0.1 | 0.296 | 0.2972 | 0.001128 |
| audit_shadow_apis | 3547 | 0.0 | 0 | 0 | 0 |
| arch_ui_framework | 3547 | 0.0 | 3.443 | 3.443 | 0 |
| def_spec_exposure | 3547 | 0.0 | 0 | 0 | 0 |
| arch_ssr_boundaries | 3547 | 0.0 | 0.4917 | 0.4917 | 0 |
| arch_hardware | 3547 | 0.0 | 0 | 0 | 0 |
| llm_api | 3547 | 0.0 | 0 | 0 | 0 |
| llm_orchestrator | 3547 | 0.0 | 0 | 0 | 0 |
| llm_vector_store | 3547 | 0.0 | 0 | 0 | 0 |
| llm_local_compute | 3547 | 0.0 | 0 | 0 | 0 |
| ml_traditional | 3547 | 0.0 | 0 | 0 | 0 |
| dl_frameworks | 3547 | 0.0 | 0 | 0 | 0 |
| lit_diagrams | 3547 | 0.0 | 0 | 0 | 0 |
| threat_env_mutation | 3547 | 0.0 | 0 | 0 | 0 |
| threat_crypto_math | 3547 | 0.0 | 0 | 0 | 0 |
| threat_stego_imports | 3547 | 0.0 | 0 | 0 | 0 |
| threat_extension_mismatch | 3547 | 0.0 | 0 | 0 | 0 |
| threat_tainted_injection | 3547 | 0.0 | 0 | 0 | 0 |
| prompt_injection | 3547 | 0.0 | 0 | 0 | 0 |
| agentic_rce | 3547 | 0.0 | 0 | 0 | 0 |
| sec_unicode_steganography | 3547 | 0.0 | 0 | 0 | 0 |
| sec_self_propagation | 3547 | 0.0 | 0 | 0 | 0 |
