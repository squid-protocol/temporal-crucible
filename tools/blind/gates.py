"""The gates-on-real-labels job (blinding_spec.md, "Checks that need real labels before unblinding").

    python tools/blind/gates.py --study STUDY_DIR --key ~/.../blind_key.pem [--rerun REASON]
    python tools/blind/gates.py --study STUDY_DIR --dry-run

Same key, seal, in-memory decryption, guard and run-once rule as score.py. Runs each gate the specification
declares (study.json "gates": name, registry gate, params, outputs), and writes only each gate's declared
summary to result/gates.json; the run is recorded in result/gates_unblinding.json. A gate belongs in the
registry only after it has been qualified on synthetic data and on scrambled labels (checks/ledger.md); the
phase-A registry holds two REFERENCE gates for tests only. All logic is in jobcore.py.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import jobcore  # noqa: E402


def run(study_dir, private_key=None, key_path=None, rerun=None, dry_run=False):
    return jobcore.run("gates", study_dir, private_key=private_key, key_path=key_path, rerun=rerun,
                       dry_run=dry_run)


def main(argv=None) -> int:
    return jobcore.cli("gates", argv)


if __name__ == "__main__":
    raise SystemExit(main())
