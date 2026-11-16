"""Encrypt a label table to the owner's public key; decrypt it into memory only (blinding_spec.md, layer 1).

Construction (DECISIONS.md 1): hybrid encryption, as the specification states it --
  * a fresh random 256-bit data key and 96-bit nonce per file (os.urandom);
  * the table, as canonical JSON padded with spaces to a power-of-two length (at least 4096 bytes), encrypted
    with AES-256-GCM; the file's header (format, version, algorithm, key fingerprint, repo) is the GCM
    associated data, so a change to any of it, or to the ciphertext, fails authentication;
  * the data key wrapped with RSA-OAEP (SHA-256, MGF1-SHA-256) to the public key.
It is done with the `cryptography` package the system interpreter already has (/usr/lib/python3/dist-packages),
not the `openssl` command line: `openssl enc` refuses AEAD ciphers ("enc: AEAD ciphers not supported", OpenSSL
3.0.13), so AES-256-GCM cannot be done with the command line alone, and an unauthenticated substitute is not
acceptable. No plaintext ever leaves the process: nothing is written to a file, an argument or the
environment, and no error message carries table content.

File format, version 1: one JSON object (ASCII), keys
  format "tc-blind-labels", version 1, alg, key_fingerprint (SHA-256 hex of the public key's DER
  SubjectPublicKeyInfo, the fingerprint keys/README.md quotes), repo, wrapped_key, nonce, ciphertext
  (base64; the ciphertext includes the 16-byte GCM tag).

Two ways to get a private key (DECISIONS.md 2):
  * owner_private_key(path)  -- the owner-facing path the jobs' command lines use. Refuses a key file that
    is not passphrase-protected, and asks for the passphrase on the terminal (/dev/tty via getpass; refuses
    rather than falling back to reading standard input). There is no command-line option or environment
    variable for a passphrase.
  * Tests never call it with a real key: they generate a throwaway key in pytest's tmp_path and hand the key
    OBJECT to the jobs' Python entry points (score.run / gates.run), or exercise this function with a
    throwaway passphrase-protected key and a monkeypatched _prompt_passphrase.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import warnings

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT = "tc-blind-labels"
VERSION = 1
ALG = "RSA-OAEP(SHA-256,MGF1-SHA-256)+AES-256-GCM"
MIN_PAD = 4096
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PUBLIC_KEY = os.path.join(os.path.dirname(os.path.dirname(HERE)), "keys", "blind_pub.pem")


class BlindCryptoError(Exception):
    """Raised with a fixed message that never contains table content."""


def _oaep():
    return padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def fingerprint(public_key) -> str:
    der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest()


def load_public_key(path=DEFAULT_PUBLIC_KEY):
    with open(path, "rb") as fh:
        key = serialization.load_pem_public_key(fh.read())
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
        raise BlindCryptoError("public key must be RSA, at least 2048 bits")
    return key


def _header(key_fp, repo):
    return {"format": FORMAT, "version": VERSION, "alg": ALG, "key_fingerprint": key_fp, "repo": repo}


def _pad(data: bytes) -> bytes:
    size = MIN_PAD
    while size < len(data) + 1:
        size *= 2
    return data + b" " * (size - len(data))


def encrypt_table(table, public_key, repo: str) -> bytes:
    """The encrypted file's bytes. `table` is any JSON-serialisable object."""
    hdr = _header(fingerprint(public_key), repo)
    data_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    ct = AESGCM(data_key).encrypt(nonce, _pad(canonical(table)), canonical(hdr))
    wrapped = public_key.encrypt(data_key, _oaep())
    del data_key
    out = dict(hdr)
    out.update({"wrapped_key": base64.b64encode(wrapped).decode("ascii"),
                "nonce": base64.b64encode(nonce).decode("ascii"),
                "ciphertext": base64.b64encode(ct).decode("ascii")})
    return (json.dumps(out, sort_keys=True, indent=1) + "\n").encode("ascii")


def read_header(blob: bytes) -> dict:
    """The header of an encrypted file (no key needed). Raises BlindCryptoError on a malformed file."""
    try:
        obj = json.loads(blob.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise BlindCryptoError("not an encrypted label file (not ASCII JSON)") from None
    if not isinstance(obj, dict) or obj.get("format") != FORMAT:
        raise BlindCryptoError("not an encrypted label file (format field)")
    if obj.get("version") != VERSION:
        raise BlindCryptoError(f"unsupported encrypted label file version {obj.get('version')!r}")
    if obj.get("alg") != ALG:
        raise BlindCryptoError("unsupported algorithm field")
    for k in ("key_fingerprint", "repo", "wrapped_key", "nonce", "ciphertext"):
        if not isinstance(obj.get(k), str):
            raise BlindCryptoError(f"encrypted label file lacks {k}")
    return obj


def decrypt_table(blob: bytes, private_key):
    """Decrypt into memory and return the table. Refuses a file made for another key before any RSA
    operation; any modification of header, wrapped key, nonce or ciphertext fails authentication."""
    obj = read_header(blob)
    if fingerprint(private_key.public_key()) != obj["key_fingerprint"]:
        raise BlindCryptoError("this file was encrypted to a different public key (fingerprint mismatch); "
                               "refusing")
    try:
        wrapped = base64.b64decode(obj["wrapped_key"], validate=True)
        nonce = base64.b64decode(obj["nonce"], validate=True)
        ct = base64.b64decode(obj["ciphertext"], validate=True)
    except ValueError:
        raise BlindCryptoError("encrypted label file: bad base64") from None
    try:
        data_key = private_key.decrypt(wrapped, _oaep())
    except ValueError:
        raise BlindCryptoError("could not unwrap the data key (modified file or wrong key)") from None
    if len(data_key) != 32 or len(nonce) != 12:
        raise BlindCryptoError("encrypted label file: bad key or nonce length")
    try:
        plain = AESGCM(data_key).decrypt(nonce, ct, canonical(_header(obj["key_fingerprint"], obj["repo"])))
    except InvalidTag:
        raise BlindCryptoError("authentication failed: the encrypted label file was modified") from None
    finally:
        del data_key
    try:
        return json.loads(plain.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise BlindCryptoError("decrypted content is not a label table") from None


# ------------------------------------------------------------------------------------------------- keys
def _prompt_passphrase() -> bytes:
    """Ask on the terminal. getpass reads /dev/tty; if there is none it would fall back to standard input
    with a warning -- that warning is made an error, so a passphrase can never be piped in."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            pw = getpass.getpass("Passphrase for the blinding key: ")
        except getpass.GetPassWarning:
            raise BlindCryptoError("no terminal to ask for the passphrase on; run this job by hand in your own "
                                   "terminal") from None
    return pw.encode("utf-8")


def owner_private_key(path):
    """The owner-facing path. Loads a passphrase-protected PEM private key, asking for the passphrase on the
    terminal. Refuses an unprotected key file (the protection is what makes the file useless to a session)."""
    with open(path, "rb") as fh:
        pem = fh.read()
    try:
        serialization.load_pem_private_key(pem, password=None)
    except TypeError:
        pass                                     # encrypted, as required
    except ValueError:
        raise BlindCryptoError("not a PEM private key") from None
    else:
        raise BlindCryptoError("the private key file is not passphrase-protected; refusing to use it")
    pw = _prompt_passphrase()
    try:
        key = serialization.load_pem_private_key(pem, password=pw)
    except (ValueError, TypeError):
        raise BlindCryptoError("could not open the private key (wrong passphrase?)") from None
    finally:
        del pw
    if not isinstance(key, rsa.RSAPrivateKey):
        raise BlindCryptoError("private key must be RSA")
    return key


def main(argv=None) -> int:
    """Read-only helpers. Deliberately no decrypt command: decrypted content has nowhere to go but the
    terminal or a file, and both are disk or logs."""
    import argparse
    ap = argparse.ArgumentParser(description="Inspect blinding files (no decryption here).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fingerprint", help="SHA-256 fingerprint of a public key")
    f.add_argument("--pub", default=DEFAULT_PUBLIC_KEY)
    h = sub.add_parser("header", help="print an encrypted label file's header")
    h.add_argument("file")
    a = ap.parse_args(argv)
    if a.cmd == "fingerprint":
        print(fingerprint(load_public_key(a.pub)))
    else:
        with open(a.file, "rb") as fh:
            hdr = read_header(fh.read())
        print(json.dumps({k: hdr[k] for k in ("format", "version", "alg", "key_fingerprint", "repo")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
