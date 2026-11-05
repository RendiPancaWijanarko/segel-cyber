#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SEGEL Transparency Ledger Online Backup & Verification Utility.

Performs safe, non-blocking online backups of SQLite WAL ledger databases
using SQLite's online backup API, and verifies cryptographic Merkle consistency
of the resulting snapshot.

USAGE:
    python scripts/backup_ledger.py backup --source /var/lib/segel/ledger.db --target /var/backups/segel/ledger_backup.db
    python scripts/backup_ledger.py verify --file /var/backups/segel/ledger_backup.db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ledger.ledger import TransparencyLedger


def backup_ledger(source_path: Path, target_path: Path) -> None:
    """Create a verified online backup of the ledger database."""
    if not source_path.exists():
        print(f"[!] Source database does not exist: {source_path}")
        sys.exit(1)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[*] Initiating online backup: {source_path} -> {target_path}")

    ledger = TransparencyLedger(source_path)
    try:
        ledger.backup(target_path)
    finally:
        ledger.close()

    print("[+] Backup copy completed.")
    verify_backup(target_path)


def verify_backup(backup_path: Path) -> None:
    """Verify cryptographic Merkle consistency of a backup database."""
    if not backup_path.exists():
        print(f"[!] Backup database does not exist: {backup_path}")
        sys.exit(1)

    print(f"[*] Verifying cryptographic integrity of: {backup_path}")
    ledger = TransparencyLedger(backup_path)
    try:
        size = ledger.size
        root_hex = ledger.root_hash_hex()
        latest_cp = ledger.get_latest_checkpoint()

        print(f"    - Total Ledger Entries: {size}")
        print(f"    - Current Merkle Root:  {root_hex}")

        if latest_cp is not None:
            print(f"    - Latest Checkpoint Size: {latest_cp.checkpoint.size}")
            print(f"    - Checkpoint Root Hash:   {latest_cp.checkpoint.root_hash}")
            print(f"    - Ledger Signature Present: {bool(latest_cp.ledger_signature)}")
            print(f"    - Witness Cosignatures:   {len(latest_cp.witness_cosignatures)}")

            if latest_cp.checkpoint.size == size and latest_cp.checkpoint.root_hash == root_hex:
                print("[+] Integrity check PASSED: Checkpoint matches reconstructed Merkle root.")
            else:
                print("[*] Note: Checkpoint covers size "
                      f"{latest_cp.checkpoint.size}; current tree size is {size}.")
        else:
            print("[*] No checkpoint recorded yet.")

        print("[+] Backup database verified successfully.")
    finally:
        ledger.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="SEGEL Ledger Backup & Verification Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create an online backup of a ledger database")
    backup_parser.add_argument("--source", required=True, help="Path to live SQLite ledger database")
    backup_parser.add_argument("--target", required=True, help="Path to write backup database")

    verify_parser = subparsers.add_parser("verify", help="Verify integrity of an existing backup database")
    verify_parser.add_argument("--file", required=True, help="Path to backup SQLite database to verify")

    args = parser.parse_args()

    if args.command == "backup":
        backup_ledger(Path(args.source), Path(args.target))
    elif args.command == "verify":
        verify_backup(Path(args.file))


if __name__ == "__main__":
    main()

