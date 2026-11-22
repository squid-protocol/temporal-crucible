"""The unblinding job (blinding_spec.md, "Unblinding: one job, run by the owner").

    python tools/blind/score.py --study STUDY_DIR --key ~/.../blind_key.pem [--rerun REASON]
    python tools/blind/score.py --study STUDY_DIR --dry-run

Run by the owner in their own terminal; it asks for the passphrase there. It verifies the seal (seal.py),
decrypts the labels into memory only, runs the sealed scorer named in study.json once, writes only the
declared outputs to result/result.json and records the run in result/unblinding.json. A second run for the
same seal needs --rerun REASON. --dry-run runs the scorer on every scrambled copy instead (no key) and writes
dry_run/score.NOT_A_RESULT.json, every output stamped NOT A RESULT. All logic is in jobcore.py.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import jobcore  # noqa: E402


def run(study_dir, private_key=None, key_path=None, rerun=None, dry_run=False):
    return jobcore.run("score", study_dir, private_key=private_key, key_path=key_path, rerun=rerun,
                       dry_run=dry_run)


def main(argv=None) -> int:
    return jobcore.cli("score", argv)


if __name__ == "__main__":
    raise SystemExit(main())
