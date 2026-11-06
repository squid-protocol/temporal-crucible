# NM-F — untested file metrics vs future security fixes, at equal size (SCORED)

- quarterly snapshots: curl 105, ndpi 43, openssl 110; strata = 10 equal-count `total_loc` bins per snapshot
- entered the screen: **9** metrics → two-sided α = 0.01/9 = 0.00111
- failed the entry rule (≥ 5% non-zero and ≥ 3 distinct values in every repo): fam_cleanup, fam_concurrency, fam_io, fam_ipc, fam_time, fam_events, fam_tests, fam_docs, fam_credential, fam_threat, fam_ml_ai, rel_alloc_cleanup, doc_umbrella, wrapped_debug_prints, wrapped_memory_alloc, wrapped_panics_and_aborts, threat_db_sinks, threat_api_near_db_sink, amplified_exfiltration, amplified_race_conditions, mitigated_danger, mitigated_memory_allocs

Lift = size-stratified AUC − 0.5 (positive = higher value, more fixes at equal size). Brackets: the Bonferroni CI.

| metric | curl | nDPI | openssl | verdict |
|---|---|---|---|---|
| `amplified_cascading_flux` | +0.045 [-0.019, +0.118] | +0.204 [+0.133, +0.282] | +0.144 [+0.077, +0.206] | **LEAD** (higher = riskier) |
| `fam_mutation` | +0.055 [-0.001, +0.119] | +0.186 [+0.085, +0.280] | +0.112 [+0.049, +0.179] | **LEAD** (higher = riskier) |
| `fam_dead_code` | +0.044 [-0.026, +0.117] | +0.122 [+0.043, +0.214] | +0.077 [+0.023, +0.137] | **LEAD** (higher = riskier) |
| `fam_connectivity` | +0.052 [-0.017, +0.125] | +0.168 [+0.074, +0.267] | +0.047 [-0.008, +0.105] | no signal |
| `fam_memory` | +0.061 [-0.011, +0.150] | +0.133 [+0.050, +0.228] | +0.053 [-0.005, +0.110] | no signal |
| `fam_guards` | +0.061 [-0.008, +0.128] | +0.175 [+0.080, +0.269] | -0.039 [-0.100, +0.014] | no signal |
| `fam_debt` | -0.011 [-0.067, +0.052] | +0.138 [+0.058, +0.225] | +0.047 [-0.003, +0.100] | no signal |
| `fam_danger` | -0.003 [-0.063, +0.066] | +0.126 [+0.051, +0.209] | +0.027 [-0.028, +0.081] | no signal |
| `rel_guard_balance` | +0.045 [-0.030, +0.114] | +0.072 [-0.000, +0.142] | -0.044 [-0.095, +0.006] | no signal |

Runtime 20s · bootstrap 5000 rounds over snapshots, seed 2982.
