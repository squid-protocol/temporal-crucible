# INP-H1..H6 — does input-facing code mark where CVEs land? — registered 2026-11-06, before any input-measure statistic

**Mechanism (designed first; the ENV/LIB pattern).**
- **Latent defects are found where untrusted bytes are handled.** Code that *declares* it pulls data in from outside,
  or handles raw bytes with a length, is the input surface.
- **The working idea from ENV and LIB:** explicit, declared dependencies on the outside world mark where outside-driven
  work lands. Here the outside is the input.

**What has been looked at.**
- XC latent labels (curl, nDPI, openssl) and harfbuzz OSV security-fix events.
- SC's finding that no existing file metric finds CVEs beyond size.
- XC's finding that CVE history does.
- **Never computed:** either measure below.

## Repos, snapshots and outcomes

- **Repos:** curl, nDPI, openssl, harfbuzz (C + C++). libarchive is excluded (18 CVE events).
- **Snapshots:** quarterly walks. Candidates: the repo's source extensions. Size: line count (git).
- **Latent outcome.**
  - curl, nDPI, openssl: XC `latent` commits.
  - harfbuzz: `events/harfbuzz.json` security-fix SHAs reachable from the walk head, with touched files from
    `git diff-tree`.
  - A file at t is positive if touched in (t, t + 180 d].
- **Placebo outcomes:** XC `extrinsic` and `other-fix`. For harfbuzz, latent SHAs are removed from them.

## Measures (per line; per-file counts of matching lines ÷ lines)

- **IN (input calls):** lines matching
  `\b(?:recv|recvfrom|recvmsg|read|pread|readv|fread|fgets|getline|fgetc|getc|SSL_read|SSL_read_ex|SSL_peek|BIO_read|BIO_read_ex|BIO_gets|gnutls_record_recv|mbedtls_ssl_read|wolfSSL_read|pcap_next|pcap_next_ex|pcap_dispatch|pcap_loop)\s*\(`
- **BUF (raw byte buffers with a length):** lines matching **either**
  - a byte-pointer parameter followed by a length-named parameter:
    `(?:unsigned\s+char|uint8_t|u_int8_t|u_char|guint8|char|void)\s*(?:const\s*)?\*\s*\w+\s*,\s*(?:const\s+)?(?:size_t|ssize_t|unsigned(?:\s+int|\s+long)?|int|long|uint16_t|uint32_t|u_int16_t|u_int32_t|off_t)\s+\w*len\w*`
  - or a copy driven by a length-named value: `\b(?:memcpy|memmove|strncpy)\s*\([^;]*\b\w*len\w*\b`

## Claims (pooled over evaluable repos; equal weight per repo)

lift(S, K) = recall@20(S on class K) − max(recall@20 by lines-desc, lines-asc), on the same snapshots. Recall@20 follows
EA's rule.

| id | claim | per-snapshot quantity | supported iff |
|---|---|---|---|
| **INP-H1** | IN finds CVE fixes beyond size | lift(IN, latent) | mean > 0, lo > 0 |
| **INP-H2** | BUF finds CVE fixes beyond size | lift(BUF, latent) | mean > 0, lo > 0 |
| **INP-H3** | IN is specific to CVEs | lift(IN, latent) − mean(lift(IN, extrinsic), lift(IN, other-fix)) | mean > 0, lo > 0 |
| **INP-H4** | BUF is specific to CVEs | same for BUF | mean > 0, lo > 0 |
| **INP-H5** | IN finds CVEs where history cannot | lift(IN, latent) restricted to candidates with **no prior latent fix** (≤ t) | mean > 0, lo > 0 |
| **INP-H6** | BUF finds CVEs where history cannot | same for BUF | mean > 0, lo > 0 |

**Tests.**
- Within-repo snapshot bootstrap, 5,000 rounds, seed 2982. Repo means are averaged per round.
- α = 0.01 / 6 one-sided. Equivalence null: 90% CI inside [−0.02, +0.02].
- **Evaluability:** a repo enters with ≥ 20 snapshots having ≥ 1 latent positive. For H5/H6, ≥ 1 latent positive among
  the no-prior candidates.
- H3/H4 use snapshots that have positives in latent and in at least one placebo class.

**Headline.** **"Input-facing code is shown"** iff, for IN or for BUF, its beat-size, specificity and no-history claims
(H1/H3/H5 or H2/H4/H6) are all SUPPORTED.

**Descriptive.** Per-repo lifts; the share of files with any IN or BUF line.

## Priors

- **Overall: uncertain, leaning not shown.** Every snapshot metric so far failed for CVEs, and CVE labels depend on
  the searcher.
- BUF **more likely than IN**: parsers receive buffers, they rarely call `recv` themselves.
- H5/H6 **the most informative**: they ask whether structure sees where history is blind.
