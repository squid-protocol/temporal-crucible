# keys/

`blind_pub.pem` is the **public** half of the owner's blinding key (RSA 4096; SHA-256 of its DER form begins
`8b222bdc37b28697`). Study labels are encrypted to it; only the owner, with a passphrase, can decrypt them.
See `docs/process/blinding_spec.md`.

The private key is not in this repository and must never be. It lives outside it, passphrase-protected, and
is used only by the owner, by hand, to run the unblinding and gate jobs.
