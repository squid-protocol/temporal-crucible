# Blinding — specification (owner decision 2026-11-14: a key the owner holds, plus scrambled labels)

**Status: specification, nothing built.** It goes to the same build-and-review as everything else.

**Revision 2, 2026-11-14.** The scramble's cells are changed (marked **[r2]**): the first version leaked. Found
by the design review of the research-codebase specification and reproduced on the control repository.

## What it protects against, and what it cannot

**Protects against the failure that actually happened** (defect log 26): an analysis or review session joining
real structural measures to real outcome labels, on purpose or while debugging. After this, the true labels of
a study are ciphertext on disk, and no session can read them.

**It cannot make the labels unknowable.** The labels are computed from public git history that sits on the same
disk, by code in this repo. A session could rebuild them. So:

- For repos already on disk, this is a **guard against accidents and shortcuts**, with an audit trail: the only
  way to see true labels is to re-run the label builder outside the blinded path, which is a visible,
  deliberate act and is forbidden by rule.
- **Real blinding needs data that is not here.** Confirmation repos are not cloned to this machine until the
  study is sealed (the third layer below).

Both statements go in every study's `seen.md`.

## Three layers

### 1. True labels are encrypted to a key only the owner can use

- The owner creates a key pair **once, in their own terminal, with a passphrase** (commands below). The
  private key is passphrase-protected, so the file alone is useless to a session even though sessions run as
  the same user. The public key is committed at `keys/blind_pub.pem`.
- The label builder, when run for a blinded study, writes **only** `labels/<repo>.enc` (encrypted to the public
  key) and the scrambled labels of layer 2. It never writes plaintext labels, counts per file, or lists of
  positive files. It may write **marginals that do not identify files**: number of positive files, number of
  qualifying commits, largest commit's share — what floors and feasibility need.
- Encryption is hybrid with standard tools already on the machine (`openssl`): a random 256-bit key per file,
  AES-256-GCM for the data, the key wrapped with RSA-OAEP to the public key. No new dependency.

### 2. Sessions develop on scrambled labels

- Alongside each encrypted file the builder writes `labels/<repo>.scrambled.json`: the same structure, with
  the positive labels **re-assigned among files**. The permutation uses fresh operating-system randomness that
  is never stored, so it cannot be inverted by anyone.
- **What the scramble preserves:** the number of positives, and their distribution over the scramble's cells
  (labels are permuted within a cell), so size and, where the repo is large enough, directory behave as in the
  real data. **What it destroys:** any link between a file's own structure and its outcome.
- **[r2] The cells, and why they are not simply LOC band × directory.** A file alone in its cell keeps its
  label, and a positive that is positive in every copy is a known positive. Measured on the default control
  repository (306 unit files, 33 directories, 10 bands): with band × full directory, **25% of files are alone
  in a cell and 36–38% of the true positives are positive in all 20 copies**; with band × top-level directory,
  6% and 12–16%; with band alone, 0%. So:
  1. Cells start as LOC band × full directory.
  2. Any cell with fewer than **8** files is merged with its siblings by shortening the directory one level at
     a time, down to the band alone. This uses the file table only; no label is read.
  3. The builder writes, per repo, the share of files in each cell-size class and the depth each cell ended at.
  4. Inside the builder (which sees true labels), any cell that is still more than 80% positive is merged up
     one more level, and only the count of such merges is written.
  5. The builder reports one number per repo: the share of true positives that are positive in all copies. It
     must be under **2%**; if it is not, the repo's scrambles are not released and the reason is written.
- The price: in a small repo the scramble no longer preserves directory, so its null is the null of size
  alone. The per-repo report of step 3 says which repos that is.
- So the whole pipeline — statistic, controls, gates, scorer — runs end to end on real measurements, and **any
  structural effect it reports on scrambled labels is false by construction.** That is a real-data negative
  control, run on every repo, for free. It is recorded in the study's `controls.md` with its result.
- Several independent scrambles (default 20) are written, so the spread of a null result on real data is
  measured, not assumed.
- Scrambled files carry `"scrambled": true`. The scorer refuses to write a result file from scrambled input
  unless called in `--dry-run`, and stamps every dry-run output `NOT A RESULT`.

### 3. Confirmation repos are held back

Named in the registration by a selection rule and a seed, not by a list anyone has looked through. Cloned and
scanned only after the seal. Until then nothing about them exists on this machine.

## Unblinding: one job, run by the owner

```
python tools/blind/score.py --study <id> --key ~/…/blind_key.pem
```

run **by the owner in their own terminal**; it prompts for the passphrase. The job:

1. Verifies the seal: the hashes of the scorer, statistics, label builder, definitions, specification, power
   statement, review record, every scan and every encrypted label file match `seal.json`. Any mismatch: stop.
2. Decrypts labels **into memory only**. Nothing decrypted is written to disk.
3. Runs the sealed scorer once.
4. Writes `result/result.json` — only the pre-declared outputs listed in the specification — and
   `result/unblinding.json`: time, seal hash, who ran it.
5. Refuses to run a second time for the same seal unless given `--rerun REASON`, which is recorded.

**What the job may output is part of the specification.** Per-file values joined to outcomes, lists of
positive files, and per-commit effects are not outputs unless the registration says so.

## Checks that need real labels before unblinding

Some gates must see real outcomes: hash placebos, size surrogates and non-structural benchmarks against the
true labels. They run **inside a second owner-run job**, `tools/blind/gates.py`, under the same key, which
outputs only each gate's pre-declared summary. A gate is added to that job only after it has been qualified on
synthetic data and on scrambled labels (`checks/ledger.md`). **No session debugs a failed gate against real
labels**; it is reproduced on the control repository or on scrambled labels.

## Rules

- Sessions and reviewers never run the label builder in plaintext mode on a study's repos, never decrypt, and
  never ask the owner for the passphrase or for decrypted files.
- The plaintext label files that exist today for SA3 (`<pilot>/sa3_outcomes/`) predate this and were already
  used. They are recorded in SA3's `seen.md`; SA3 is the test case, not a blinded study.
- Any output of an owner-run job that turns out to reveal more than declared is logged as an unblinding.

## One-time setup by the owner (in your own terminal, not through a session)

```
mkdir -p ~/.blind && chmod 700 ~/.blind
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -aes-256-cbc -out ~/.blind/blind_key.pem
openssl pkey -in ~/.blind/blind_key.pem -pubout -out ~/.blind/blind_pub.pem
```

The first command asks you to choose a passphrase; the second asks for it once. Keep the passphrase somewhere
that is not this machine. Then tell the session the public key is at `~/.blind/blind_pub.pem`; it is safe to
share and gets committed. If the passphrase is lost, encrypted labels are rebuilt from git — nothing is lost
but the audit trail.

## Deliverables for the builder

```
tools/blind/
  crypt.py      encrypt to the public key; decrypt (prompts; memory only)
  scramble.py   permutation within LOC band × directory, k copies, never stored
  score.py      the unblinding job
  gates.py      the gates-on-real-labels job
  README.md
tests/test_blind.py   round-trip with a throwaway key; scramble preserves the stated margins and breaks a
                      planted association; the scorer refuses scrambled input; the job refuses a broken seal
                      and a second run
                      [r2] on a control repository with a planted effect: the share of true positives positive
                      in all copies is under 2%, the effect on scrambled labels is under 10% of the true one,
                      and the first version's cells (band x full directory) FAIL both -- the test must be able
                      to see the leak
```

Tested end to end on the control repository, where the true labels are known: the unblinded result must equal
the result computed directly from the manifest.

## Open

- A session that can run arbitrary code as the owner's user could read the decrypted labels out of the
  scoring job's memory, or replace the job. The seal covers the job's own hash, and the owner runs it by hand,
  but this is a deterrent, not a wall. A separate system account for the job would close it; that needs
  administrator setup.
- Whether per-repo marginals leak anything that matters in very small repos.
