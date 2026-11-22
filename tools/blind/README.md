# tools/blind/ — blinding, build phase A

Built to `docs/process/blinding_spec.md` (Revision 3), section "Build phase A": layer 1 (true labels encrypted
to a key only the owner can use), layer 2 (sessions develop on scrambled labels) and the two owner-run jobs,
complete except for the study scorer, against the control repository. Every choice the specification did not
make is in `DECISIONS.md`.

## Files

| file | what |
|---|---|
| `crypt.py` | encrypt a label table to `keys/blind_pub.pem`; decrypt into memory only; the owner's key path (asks on the terminal). RSA-OAEP-SHA256 key wrap + AES-256-GCM, via the system `cryptography` package (`openssl enc` has no GCM). No decrypt command. |
| `scramble.py` | released copies permuted **within the LOC band only** [r3], k copies (default 20) from `random.SystemRandom`, the per-repo report, the 2% rule; and the Revision 2 directory cells (minimum 20, 80% rule), for the gates job only |
| `build_labels.py` | label table in; `labels/<repo>.enc`, `<repo>.scrambled.json` (band-only copies), `<repo>.marginals.json`, `<repo>.scramble_report.json` out. No plaintext output and no directory-preserving copies exist. |
| `seal.py` | writes / verifies `seal.json` (SHA-256 of the job's code, the specification, sealed documents, scans, encrypted labels) |
| `score.py` | the unblinding job |
| `gates.py` | the gates-on-real-labels job |
| `jobcore.py` | what the two jobs share: seal, in-memory decryption, the guard, declared outputs, run-once ledger, dry run |
| `registry.py` | scorers and gates by name; phase A holds the REFERENCE scorer (within-size-decile rank correlation of a measure with the positive flag) and three reference gates, for tests only: size surrogate, hash placebo, and the null spread (band-only beside directory-preserving copies, made in memory in the gates job, never written) |

## Use

Building labels (any session; writes only ciphertext and non-identifying files):

```
python3 tools/blind/build_labels.py --manifest DIR/manifest.json --repo NAME --labels-dir STUDY/labels
```

A study directory:

```
STUDY/study.json          study_id, repos, key_fingerprint, scorer {name, params, outputs}, gates [...],
                          sealed_documents [...], sealed_code [...]
STUDY/scans/<repo>.json   {"repo", "files": [{"path", "loc", "measures": {...}}]}
STUDY/labels/...          from build_labels.py
STUDY/seal.json           python3 tools/blind/seal.py --study STUDY
```

Developing (any session): `python3 tools/blind/score.py --study STUDY --dry-run` runs the scorer on every
scrambled copy and writes `STUDY/dry_run/score.NOT_A_RESULT.json`; every output is stamped `NOT A RESULT`.

Unblinding (the owner, by hand, in their own terminal):

```
python3 tools/blind/score.py --study STUDY --key ~/…/blind_key.pem      # asks for the passphrase
python3 tools/blind/gates.py --study STUDY --key ~/…/blind_key.pem
```

**When a study scorer is registered, every module it loads that is not in `tools/blind/` must be listed in
study.json's `sealed_code`** (paths relative to the repository root). `seal.py` hashes them, and a change to
any of them stops both jobs. `tools/blind/*.py` is always sealed.

Marginals: `largest_commit_share` is the largest qualifying commit's number of positive files divided by the
number of positive files.

Each verifies the seal, decrypts in memory, runs once, writes `result/result.json` (or `result/gates.json`)
with only the declared outputs and records the run in `result/unblinding.json` (`result/gates_unblinding.json`).
On completion it prints one line, `<job> seal <hash> time <time> <result> sha256 <hash>`; keep it somewhere
other than this machine (the ledger holds the same line, but a session could delete the ledger). A second
run for the same seal needs `--rerun REASON`. Every file is written under a temporary name and renamed.

## Tests

```
cd /srv/storage_16tb/projects/temporal-crucible-wt-seat && python3 -m pytest tests/test_blind.py
```

Throwaway keys only, generated in the test. About 31 seconds, with no expected failures (DECISIONS.md 22). The
[r3] test runs over eight control repositories (DECISIONS.md 24).
