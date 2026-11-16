# tools/blind/ — decisions the specification did not make

Against `docs/process/blinding_spec.md`, Revision 3, "Build phase A", and the review
`docs/process/reviews/blinding_review_fable.md`. Numbered so tests and code can cite them. The Revision 3
changes are 24–28. Entries 3, 5 and 7 describe the Revision 2 cells, which are no longer released: they now
serve only the gates job's directory-preserving scramble (25) and the test that shows them leaking.

## Encryption

**1. Construction, and why not the `openssl` command line.** The spec asks for `openssl`, a random 256-bit
key per file, AES-256-GCM for the data and RSA-OAEP key wrap. The installed OpenSSL 3.0.13 command line
cannot do the AES-256-GCM part: `openssl enc -aes-256-gcm` answers "enc: AEAD ciphers not supported". The
remaining command-line routes were worse: `openssl cms -encrypt -aes-256-gcm` wants an X.509 certificate for
the recipient, which would mean making one from a public key with a throwaway signing key, and it adds a
second container format; replacing GCM with `enc -aes-256-cbc` would drop authentication, which is required.
So the whole construction uses the `cryptography` package the system interpreter already has
(`/usr/lib/python3/dist-packages/cryptography`, 41.0.7). No new dependency: the spec allows "what the test
environment already has". Exactly:
- data key: 32 bytes from `AESGCM.generate_key(256)` (os.urandom); nonce: 12 bytes from `os.urandom`. Both
  are fresh for every file.
- plaintext: canonical JSON of the table (sorted keys, no spaces, ASCII), padded with spaces to a power of
  two, at least 4096 bytes. JSON ignores the trailing spaces. The padding means the file's length shows only
  the rough size of the table, not the total length of the positive paths.
- AES-256-GCM, with the canonical JSON of the header `{format, version, alg, key_fingerprint, repo}` as
  associated data. A change to any header field, or to the nonce or the ciphertext, fails authentication.
- wrapped key: RSA-OAEP, SHA-256 and MGF1-SHA-256, no label, to the public key.
- the file: one ASCII JSON object, `format: "tc-blind-labels"`, `version: 1`,
  `alg: "RSA-OAEP(SHA-256,MGF1-SHA-256)+AES-256-GCM"`, `key_fingerprint` (SHA-256 hex of the public key's DER
  SubjectPublicKeyInfo, the fingerprint `keys/README.md` quotes: `8b222bdc37b28697…`), `repo`, and
  `wrapped_key`, `nonce`, `ciphertext` in base64 (the ciphertext carries the 16-byte tag).
- decryption checks the format and version, then compares the private key's fingerprint with the header and
  refuses on a mismatch before any RSA operation. It then unwraps the key and decrypts with the header as
  associated data. Every failure raises `BlindCryptoError` with a fixed message; the `from None` keeps
  library exception text out of it.

Plaintext stays off disk because nothing is ever piped to a subprocess and nothing goes into a temporary
file. The table exists as Python objects and bytes in the job's own memory and nowhere else.

**2. The owner's key path and the test path.**
- *Owner path* (`crypt.owner_private_key`; the only key route on the `score.py` and `gates.py` command
  lines): it reads the PEM file and refuses one that is not passphrase-protected. It then asks for the
  passphrase with `getpass` on `/dev/tty`. If there is no terminal, getpass's fallback to standard input is
  turned into an error, so a passphrase can never be piped in (tested with `start_new_session=True`). There
  is no command-line option for a passphrase and no environment variable is read (both tested).
- *Test path*: the jobs' Python entry points `score.run(..., private_key=KEY)` and `gates.run(...)` take a
  key **object**. The command line never passes one. Tests generate throwaway RSA-2048 keys in memory or in
  `tmp_path`. The owner path is tested in two ways. First, with a throwaway passphrase-protected key and
  `crypt._prompt_passphrase` monkeypatched to return a fixed test passphrase. Second, with a throwaway key
  made by `openssl genpkey … -aes-256-cbc -pass pass:throwaway-test-passphrase` in `tmp_path`: the same
  format as the owner's key, made with a test-only passphrase on the command line.

**19. No decrypt command.** `crypt.py`'s command line only prints a fingerprint or a file header. Decrypted
content would have nowhere to go but a terminal or a file.

## Scramble

**3. How a small cell merges** (now: the directory-preserving cells of the gates job only, minimum 20 there;
Revision 2's minimum of 8 is kept as `R2_MIN_CELL` for the leak test). The spec says: "merged with its siblings by shortening the directory one
level at a time, down to the band alone". I implemented the narrower reading. The deepest cell under 8 files
(ties broken by band, then directory) shortens its directory by one level and joins whatever sits in the
same band at the parent directory. Siblings with 8 or more files keep their own cells. This repeats until no
cell under 8 files has a directory left. The wider reading, where a whole sibling subtree collapses whenever
one sibling is small, was built first and measured: on the default control repository it collapsed every
band to `src/`, leaving 10 cells and no directory information. The narrower reading leaves 24 cells, and
89% of files keep at least their top-level directory (measured: 312 files, cell depths 0 to 4).
A residual case remains: a band's band-alone cell (key `""`) can end with fewer than 8 files while the band
has other cells. Then the whole band collapses into one cell. Afterwards a cell has fewer than 8 files only
if it is its entire band (the test checks this). I chose the conservative option; merging the remainder
into the band's smallest cell would keep more directory information, but the spec does not name that
operation.

**4. LOC bands.** `band = floor(10 × (number of files with strictly smaller loc) / n)`: rank deciles in which
tied files always share a band. A band can be empty or uneven. The reference scorer uses the same deciles.

**5. The 80% rule (rule 4)** (now: gates job only, in memory; nothing about it is written [r3]). "More than 80%" is strict: `positives > 0.8 × size`. It is a single pass over
the rule-2 cells, deepest first. "Merged up one more level" means the cell's sibling subtree collapses into
one cell at the parent directory; otherwise a cell with no other cell at its parent would only be renamed.
A dense cell that an earlier collapse has already absorbed is not collapsed again. A dense cell that is
already its whole band has no level above it: it is counted as `dense_cells_at_band_alone_unmergeable` and
left to the 2% rule. Under Revision 2 the two counts were written; under Revision 3 they are not written at
all, because the released copies do not use these cells.

**6. The 2% rule (rule 5).** "Under 2%" is strict, and it is checked per outcome on the 20 band-only copies
actually released [r3]. If any outcome fails, no `scrambled.json` is written for the repository. The report says why and
gives the exact share, and the `.enc` is still written, because unblinding needs it. If the rule passes, the
report says only `"< 0.02"`. The set of files positive in all copies is visible in the released copies, and
the exact count of true positives in that set would tell which of them are positive: all of them when the
count equals the set's size, none when it is 0.

**7. (History: Revision 2's 10% rule. Superseded by 24.) The 10% rule: how it is measured, and where it
fails.** "The effect on scrambled labels" is measured
as the exact expectation of the reference statistic over the scramble's permutations
(`registry.expected_under_scramble`). Cells nest in bands and keep their positive count, so each band's flag
variance is fixed and only the numerator varies. Its expectation replaces each file's flag with its cell's
positive share. This takes the Monte Carlo noise out of the comparison: at 312 files the mean of 20 copies
alone varies by ±10–15% of a true effect of about 0.12. The test checks that a 400-copy mean agrees with the
exact value to 0.02. The 20-copy numbers are reported too.
**Result: the specified cells do not meet the 10% rule on every default-size control repository.** With
planted branch-density β = 1.0 and seeds 1–5, the share of the true effect that survives is 0.5%, 16.2%,
10.6%, 11.6% and 4.7%. The surviving part is the cell-level association, which does not depend on any
file's own label. In expectation it is about (cells − bands) / (files − bands), roughly 5% here, plus a part
specific to each repository. With a minimum cell of 8 the worst case is about 1/8, which is above 10%, so
the spec's two numbers cannot both be guaranteed. The test asserts the rule as written. Seed 1 passes. Seeds
2, 3 and 4 were `xfail(strict=True)` in the first build; under Revision 3 those tests are gone and no xfail
remains. The first version's cells fail
the rule on every seed (22–70% survives) and the 2% rule too (25–40%), and the tests show both.

**8. The label table, and what counts as qualifying.** In memory:
`{"schema": 1, "rows": [{"outcome", "path"}], "outcomes": {name: {"qualifying_commits",
"largest_commit_share", "ambiguous_commits"}}}`; the encrypted copy adds `repo`. From the control manifest
there is one outcome, `HP`: the positives are the snapshot's unit files (`path_at_snapshot`) touched by any
commit with `counted: true`. `qualifying_commits` counts every `counted: true` commit, including ones that
touch no unit file present at the snapshot. `largest_commit_share` is the largest such commit's number of
positive files divided by the number of positive files. The spec left the denominator open; the review
adopted this definition.
`ambiguous_commits` counts `counted: null`. The file table is the snapshot's unit files with their
snapshot `loc`.

## What each output can reveal (check 3)

**9. Per output, what I concluded.**
- `<repo>.enc`: ciphertext. Its header names the repo and the key fingerprint, and its length shows only a
  power-of-two size class (1).
- `<repo>.scrambled.json` [r3]: copies permuted within the LOC band only. From any one copy one can read the
  number of positives in each size band, and nothing finer: no directory's fix rate, and no cell of known
  negatives unless a whole band has no positive. That is the relation of fixes to size, which no hypothesis
  is about (spec r3, point 2). A band that is almost entirely positive is the remaining risk; the 2% rule
  withholds such a repository (seen on 2 of 3 small-profile repositories). Rows are sorted by path, so their
  order carries nothing. (Revision 2's cells revealed each directory cell's fix rate, and their rule-4 merges
  could be detected across copies; that is why they were withdrawn.)
- `<repo>.marginals.json`: the number of files and of positive files (both readable from the copies anyway),
  the number of qualifying commits, the largest commit's share and the number of ambiguous commits. No file
  is named. The largest commit's share times the positive count gives the number of files one commit
  touched; anyone with the public git history could look for that commit, but that is rebuilding the labels
  from git, which the spec says cannot be prevented here.
- `<repo>.scramble_report.json` [r3]: the rule text ("permuted within the LOC band only"), and the cell
  report of the band-only cells (number of cells, shares of files by cell-size class, depth 0,
  `null_is_size_only: true`), computed from the file table alone. Per outcome it holds only the release
  decision, which carries an exact share only when the scrambles are withheld (6). No label-derived count
  (dense merges) is written. The test checks that two different label tables give the identical cell
  report.
- console output of `build_labels.py`: the names of the files written, and whether scrambles were released.
- the jobs: `result.json` holds only declared outputs; `unblinding.json` holds time, seal hash, who, the
  rerun reason, a status, the files written and the receipt line (27). Status texts are composed by the job: declared names,
  counts, exception type names and audit-event names, never content (17).
The tests check that no output of the builder other than the scrambled copies contains a path, a basename
or a `/` outside the fixed rule text, and, through an audit hook, that the builder opens for writing only
temporary names in the labels directory, each then renamed onto one of its four outputs (26). Nothing else
is opened for writing.

**10. Refusing beside plaintext labels.** In the labels directory, these count as a plaintext label file for
repo `R` (case-insensitive): a file named `R`, any `R.*` that is not one of the builder's four outputs, and
`R_label*`, `R-label*`, `R_outcome*`, `R-outcome*`, `R_positive*`, `R-positive*`. Repo names must match
`[A-Za-z0-9][A-Za-z0-9_-]*` with no `.`, so `R.` names belong to `R` alone, and other repos' files are left
alone (tested). The command line also refuses when its input manifest, which holds plaintext labels, sits
inside the labels directory. Existing outputs need `--replace`. The builder also refuses to encrypt a table
marked `scrambled` as true labels.

## The jobs

**11. The seal.** Defined in `seal.py`: `seal.json` = `{seal_version: 1, algorithm: "sha256", created,
code, study}`.
- `code` holds the SHA-256 of every `.py` file in `tools/blind/` (scorer registry, statistics, label
  builder, crypto, scramble, jobs), keyed `tools/blind/<name>`, and of every path in study.json's
  `sealed_code` list (28).
- `study` holds the SHA-256 of `study.json` (scorer, parameters, declared outputs, gates, key fingerprint),
  of every path listed in its `sealed_documents` (definitions, power statement, review record), of every
  `scans/*.json` and of every `labels/*.enc`.
- Each hash is SHA-256 over the file's bytes; the seal hash is SHA-256 over `seal.json`'s bytes.
- Verification fails on a changed file, a missing file, or an unsealed extra `.py`, scan or `.enc`.
- The job re-hashes the very bytes it then uses (scans, `.enc`), so a file cannot change between the check
  and its use.
- `seal.py` refuses to overwrite an existing seal.
- Tested: a changed scorer (a copy of `tools/blind` is sealed and its `registry.py` edited; the copy's own job
  stops), and a changed `.enc`, scan, `study.json` or sealed document, an extra scan, an extra `.enc` and a
  missing seal. Each stops both jobs with nothing written.
- Hashing the code does not prove the code that runs is the code on disk; the spec's "Open" section already
  says the job is a deterrent, not a wall.

**12. The study directory** (`README.md`): `study.json`, `scans/<repo>.json`, `labels/`, `seal.json`,
`result/`, `dry_run/`. Scans hold `{"repo", "files": [{"path", "loc", "measures": {…}}]}`.

**13. Run once.**
- The ledger (`result/unblinding.json`, and `result/gates_unblinding.json` for the gates) is a JSON list.
  An entry with status `started` is written before the scorer runs and is updated to `completed` or
  `stopped: …`.
- A second run is refused without `--rerun REASON` when any ledger entry carries the same seal hash,
  whatever its status: a stopped or crashed attempt still saw the labels. It is also refused when the
  result file exists, so deleting the seal and sealing again does not give a silent second run.
- `--rerun` needs a non-blank reason. The reason is recorded, and the earlier result is kept as
  `result.superseded-<i>.json`.
- Refusals before decryption (seal, key, fingerprint, scrambled input) write nothing and are not ledger
  entries.
- The time is local ISO-8601 with its UTC offset, and "who" is `user@host`.
- The two jobs keep separate ledgers.

**14. The guard (stopping a scorer that writes more).** The scorer runs in the job's own process, under a
guard:
- an audit hook (installed once, active only during the call) blocks: opening files for writing (by mode
  `w a x +`, or by write, create, append or truncate flags); rename, remove, mkdir, link, chmod and the
  like; process creation; sockets; `ctypes`; `shutil`; `tempfile`; `sqlite3`; `mmap`; network clients;
  `sys.addaudithook`.
- `sys.stdout` and `sys.stderr` are replaced by objects that refuse writes.
- `logging.Logger.handle` refuses every record. pytest's in-memory log handler showed why that is needed.
- file descriptors 1 and 2 point at a pipe whose bytes are counted and thrown away unseen.
- bytecode writing is off.
A violation is recorded even if the scorer catches the exception (tested). The job then stops, records
`stopped`, and writes nothing else. Tested: undeclared extra outputs, a list value, a long string, `open(w)`,
`os.open`, `print`, `os.write(1)`, `subprocess`, logging, a swallowed write error, and an exception whose
message holds a path.
**Limits:** this is not a sandbox. A hostile scorer could write through a file descriptor that was already
open, through a C extension, or from a thread that outlives the call. It guards against an honest mistake;
a separate account (spec, "Open") would be the wall.

**15. Declared outputs.** The scorer must return exactly the declared names: nothing extra, nothing missing.
Each value must be a scalar: a finite number, a bool, null, or a string of at most 64 characters. A list or a
long string could carry per-file values. The names of undeclared outputs are never printed, only counted,
because they could be paths.

**16. Scrambled input and dry runs.**
- Scrambled input is refused at three points: the builder will not encrypt a table marked scrambled, the
  job refuses a decrypted table marked `scrambled`, and `jobcore.call_scorer`, which every scorer and gate
  call goes through, refuses scrambled data unless `dry_run`.
- `--dry-run` needs no key and does not touch `result/` or the ledger. It runs the scorer (or each gate) on
  every scrambled copy and writes `dry_run/<job>.NOT_A_RESULT.json`.
- In that file, `"stamp": "NOT A RESULT"` appears at the top, on every copy and on every spread summary
  (mean, sd, min, max across the copies).
- The seal is checked and its status recorded, but a dry run does not require one: sessions develop before
  the seal.
- A repository whose scrambles were withheld cannot be dry-run.

**17. Messages.** Nothing the job prints or records can carry label content. A scorer's exception is
reported by type name only; bytes it wrote to stdout or stderr are counted, never shown. Tests check that the
captured output and the ledger contain no `src/` path, and comparisons of label content in tests go through
digests. The manifest fixture's repr is masked because pytest prints fixture values in tracebacks.

**18. The reference scorer and gates.** Reference scorer: the sum over LOC deciles d of n_d·ρ_d, divided by
the sum of n_d, taken over the deciles where both the measure and the flag vary. ρ_d is Spearman's rho: the
Pearson correlation of the measure's average ranks with the 0/1 flag. Files are taken in path order and sums
use `math.fsum`, so the value is reproducible to the last digit. The end-to-end test compares `repr` of the
unblinded result with the same function applied to positives read from the manifest by independent test
code. Outputs, per repo: `rho`, `n_files`, `n_positive`, `n_deciles_used`. The two reference gates (the rank
correlation of loc with the flag, and the reference statistic with a hash of the path as the measure) are
for tests only; neither is qualified (`checks/ledger.md`).

**20. Extra modules.** `registry.py`, `jobcore.py` and `seal.py` are not in the deliverables list. The
registry, the shared job logic and the seal needed homes, and the seal must cover them, which it does since
it hashes every `.py` here. `crypt.py` is loaded by file path under the module name `blind_crypt`
(`build_labels.load_crypt`), because Python 3.12 still ships a deprecated stdlib `crypt` module and a plain
`import crypt` could pick up the wrong one.

**21. Keys in tests.** Throwaway RSA-2048 keys, for speed; the committed key is RSA-4096. One test encrypts
to the committed `keys/blind_pub.pem`, checks its fingerprint prefix and size, and checks that a throwaway key
cannot open the result. That public key is the only real key material any test reads.

**22. Runtime.** `python3 -m pytest tests/test_blind.py`: 71 passed, no xfail, in about 29 s (29.1 s on the
development machine, one process). Most of that is generating eight default-profile control repositories
with `--years 10`, about 3.3 s each, plus a few subprocess runs.

**23. Manifest schema: validate fields, not the version number.** `table_from_manifest` accepts any
`schema_version` that is an integer of at least 2, and then checks the fields it reads. Those fields are:
- `files[].is_unit` and `files[].path_at_snapshot`;
- `files[].properties.snapshot.loc`, for unit files present at the snapshot;
- `expected_labels[].counted`;
- `expected_labels[].positives[].path_at_snapshot`, on counted labels.

A missing field is refused with a message that names it, for example `files[12].properties.snapshot.loc`.
The message gives an index, never a path. The manifest's schema number is carried as the label table's
`source_schema` and written to the marginals as `source_manifest_schema`.

Meaning checked against the generator's README and DECISIONS (51, 52, 57) for schemas 3 and 4. Schema 3 adds
the owner ruling on tainted merges. Schema 4 adds the `jira_fixword` and `jira_bare` fix conventions and
`unruled_readings`. A `jira_bare` label, and a merge whose unruled readings differ, is **decided**: `counted`
is true or false by the ruled reading, and the alternatives sit beside it marked `ruled: false`. Only
`counted: null` means ambiguous, so `ambiguous_commits` counts only those. A test adds an unruled alternative
to a `counted: false` label and checks that the count does not change.

Seed 1, `--years 10`, schema 4: 103 counted, 495 not counted (5 of them with `unruled_readings`),
2 ambiguous. None of the fields read changed meaning between schemas 2 and 4. The Revision 2 measurements
were taken on schema 2, and the [r3] table on schema 3; the schema 4 labels can differ for `jira_bare`
commits.

## Revision 3

**24. Released scrambles are band only; how the [r3] test measures them.** `scramble.released_cells` gives one
cell per LOC band, and `build_labels.py` releases only those copies. It has no option, and no code path, for
directory-preserving copies; the test checks that its source names none of those functions, and that across
released copies a band's count is constant while counts per (band, directory) vary.
- *Exact expectation.* For band-only cells the expected scrambled effect is exactly zero by algebra: each
  file's expected flag is its band's mean, so the expected numerator in every band is zero. The test checks
  the spec's "under 5% in every repository" and also `|exact| < 1e-12`. Measured: 0 in all 8 repositories.
- *Mean over repositories within three standard errors of zero.* An exact zero has no standard error, so this
  part is checked on what sessions actually get: the mean of the reference statistic over the 20 released
  copies, as a share of the true effect, in each repository. The standard error of the mean over
  repositories is `sqrt(sum of per-repository variances) / n`, each variance being the copies' variance / 20
  / true². Using the copies' own spread gives about 150 degrees of freedom rather than 7, so a correct
  scramble fails this check about 0.3% of the time (|z| > 3). The value differs from run to run because the
  copies use fresh OS randomness; one run gave z = +1.78.
- *No file in a cell without positives unless its whole band has none*: true by construction for band-only
  cells, and checked anyway.
- *The Revision 2 cells (minimum 8) fail the 5% rule in at least one repository*: they do in 5 of 8 (exact
  share kept up to 22%).
- *The first version* fails both the 5% rule and the 2% rule in every repository.
- *The 8 repositories*: default profile, seeds 1–8, `--years 10`, branches = 1.0. The reviewer also used
  `--files 1200`; I did not add those to the tests, because each takes about 13 s to generate.

**25. The directory-preserving scramble, gates job only.** `scramble.directory_cells(file_table, positives,
min_cell=20)` builds the Revision 2 cells at a minimum of 20 files, with the 80% rule. Only the reference
gate `reference_null_spread` (registry.py) calls it, inside the gates job, under the guard, in memory. The
gate returns five declared scalars per repo: `band_only_mean`, `band_only_sd`, `directory_mean`,
`directory_sd` (the reference statistic over k = 20 copies of each kind), and `directory_cells` (a count).
- The test checks that the gates job adds only `gates.json` and its ledger, and that nothing else is written
  or renamed.
- **Measured:** at default size (about 310 files, about 31 per band) a minimum of 20 collapses every band to
  a single cell, so the directory-preserving scramble equals the band-only one: 10 cells in all 8
  repositories. It preserves directory only in larger repositories. A synthetic test (3 directories × 25
  files) shows that it does keep directories when they are large enough. Like every phase-A gate, this one
  is a reference gate and not qualified.

**26. Atomic writes (review finding 4).** `seal.write_atomic` writes to `.<name>.tmp-<pid>-<random>` in the
same directory, with `open(..., "xb")` and an fsync, then calls `os.replace`; the temporary file is removed
if anything fails. The temporary file holds exactly the final bytes. It is used for every output: the
builder's four files, `seal.json`, the result files, the ledgers and the dry-run files. Tested: a failed
fsync leaves the old file intact and no temporary file behind.

**27. The receipt line (review finding 3).** On a completed run each job prints
`keep this line somewhere other than this machine: <job> seal <seal hash> time <time> <result path>
sha256 <SHA-256 of the result file's bytes>`, and stores the same text (without the prefix) as the ledger
entry's `receipt`. Tested on the score job: the line matches the file's hash and the ledger.

**28. Code outside `tools/blind/` (review finding 2).** study.json may list `sealed_code`: paths relative to
the repository root (the directory two levels above `tools/blind/`; absolute paths and `..` are refused).
Each listed file is hashed into `code`; a changed or missing one stops both jobs. Tested on a copy of the
tree under tmp_path: an extra module outside `tools/blind` is sealed, and changing it stops the copy's job,
as does removing it. README: when a study scorer is registered, every module it loads that is not in
`tools/blind/` must be listed there.

**Deliverables wording.** The spec's deliverables list still says `scramble.py` permutes "within LOC band ×
directory". As built, `scramble.py` releases copies permuted within the LOC band only. The directory cells
exist for the gates job alone.

## Measurements [r3] (8 repositories, default profile, `--years 10`, branches = 1.0)

| seed | true effect | band only: exact expected (ratio) | band only: 20-copy mean / true | minimum 8: exact expected (ratio) | minimum 20: cells |
|---|---|---|---|---|---|
| 1 | +0.1280 | 0 (0) | +0.078 | +0.0011 (+0.8%) | 10 |
| 2 | +0.1596 | 0 (0) | −0.032 | +0.0353 (**+22.1%**) | 10 |
| 3 | +0.1924 | 0 (0) | −0.002 | +0.0064 (+3.3%) | 10 |
| 4 | +0.1920 | 0 (0) | +0.008 | +0.0263 (**+13.7%**) | 10 |
| 5 | +0.2719 | 0 (0) | +0.029 | +0.0078 (+2.9%) | 10 |
| 6 | +0.1404 | 0 (0) | +0.354 | −0.0132 (**−9.4%**) | 10 |
| 7 | +0.3347 | 0 (0) | −0.036 | +0.0248 (**+7.4%**) | 10 |
| 8 | +0.1801 | 0 (0) | −0.024 | +0.0350 (**+19.4%**) | 10 |

Across the 8 repositories the band-only 20-copy share averaged +0.047, standard error 0.026, z = +1.78. The
20-copy numbers are one draw: seed 6's +0.354 is copy noise around an exact expectation of 0. The first
version kept 34–62% of the effect, and 31–40% of files sat in cells with no positives.

## Measurements, Revision 2 (history; development machine, 2026-11-14)

Planted branch density β = 1.0 unless marked negative. "All copies" is the share of true positives positive
in all 20 copies (10 repeats: min/median/max). "Kept" is the exact expected scrambled effect as a fraction of
the true one; the 20-copy mean's median is in brackets.

| repo | files | cells v1 → r2 | alone v1 / r2 | all copies v1 | all copies r2 | kept v1 | kept r2 |
|---|---|---|---|---|---|---|---|
| default seed 1 | 312 | 148 → 24 | 29.2% / 0 | 28.7% | 0 / 0 / 0 | 34.8% (34.6) | 0.5% (4.2) |
| default seed 2 | 310 | 128 → 26 | 22.3% / 0 | 25.0% | 0 | 22.3% | **16.2%** (15.4) |
| default seed 3 | 308 | 135 → 23 | 27.6% / 0 | 32.1% | 0 | 70.1% | **10.6%** (11.6) |
| default seed 4 | 311 | 150 → 28 | 32.5% / 0 | 33.0% | 0 | 40.6% | **11.6%** (9.6) |
| default seed 5 | 302 | 128 → 23 | 25.5% / 0 | 39.6% | 0 | 44.8% | 4.7% (6.0) |
| `--files 1200` seed 1 | 946 | 370 → 70 | 25.6% / 0 | 29.6% | 0 / 0 / 0.4% | 31.2% (30.0) | 4.9% (4.8) |
| `--files 1200` seed 1, negative | 946 | 370 → 70 | 25.6% / 0 | 33.1% | 0 / 0.2% / 0.9% | true effect 0.007: ratio meaningless | |
| small seed 1 | 41 | 24 → 10 | 26.8% / 0 | 55.6% | 0 | 28.6% | 0.0% |
| small seeds 2, 3 | 39, 40 | 25 → 10 | 41%, 35% / 0 | 62%, 46% | **30.8%: withheld** | | 0.0% |

On a small repository every r2 cell is a whole band, so the scramble keeps size alone and the expected effect
kept is exactly 0. When one band is more than 80% positive with no level above it, the 2% rule withholds the
scrambles.
