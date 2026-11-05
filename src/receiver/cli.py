#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""CLI for the SEGEL Offline Receiver.

Usage:
    segel-receiver verify <passport.json> --trust-root <trust.json>
                          --key <key.json> --deploy-to <dir>
    segel-receiver status --state-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="segel-receiver",
        description="SEGEL Offline Receiver — verify passports and deploy releases.",
    )
    sub = parser.add_subparsers(dest="command")

    # verify command
    verify_cmd = sub.add_parser("verify", help="Verify a Release Passport and deploy")
    verify_cmd.add_argument("passport", help="Path to passport JSON file")
    verify_cmd.add_argument("--trust-root", required=True, help="Path to trust root JSON")
    verify_cmd.add_argument("--key", required=True, help="Path to receiver key JSON")
    verify_cmd.add_argument("--deploy-to", required=True, help="Deployment target directory")
    verify_cmd.add_argument("--unit-id", required=True, help="This receiver's unit ID")
    verify_cmd.add_argument("--unit-role", default="general", choices=["canary", "general"])
    verify_cmd.add_argument("--files-dir", help="Directory containing release files")

    # status command
    status_cmd = sub.add_parser("status", help="Show receiver state")
    status_cmd.add_argument("--state-dir", required=True, help="Path to state directory")

    args = parser.parse_args()

    if args.command == "verify":
        _do_verify(args)
    elif args.command == "status":
        _do_status(args)
    else:
        parser.print_help()
        sys.exit(1)


def _do_verify(args: argparse.Namespace) -> None:
    """Verify a passport and deploy."""
    # Deferred imports to avoid import errors when just showing help
    from receiver.receiver import Receiver, ReceiverState
    from segel_core.schemas.passport import ReleasePassport
    from segel_core.schemas.trust import TrustRoot, TrustSnapshot, VerificationPolicy
    from segel_core.verification.trust import TrustContext

    # Load passport
    passport_data = json.loads(Path(args.passport).read_text(encoding="utf-8"))
    passport = ReleasePassport(**passport_data)

    # Load trust root
    trust_data = json.loads(Path(args.trust_root).read_text(encoding="utf-8"))
    root = TrustRoot(**trust_data["root"])
    policy = VerificationPolicy(**trust_data["policy"])
    snapshot = TrustSnapshot(**trust_data.get("snapshot", {"epoch": 1}))
    trust_ctx = TrustContext(root=root, policy=policy, snapshot=snapshot)

    # Load receiver key
    from segel_core.crypto.ed25519 import import_private_key
    key_data = json.loads(Path(args.key).read_text(encoding="utf-8"))
    receiver_key = import_private_key(bytes.fromhex(key_data["private_key_hex"]))

    # Load files
    files = {}
    if args.files_dir:
        files_dir = Path(args.files_dir)
        for f in files_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(files_dir)).replace("\\", "/")
                files[rel] = f.read_bytes()

    # Create receiver
    state = ReceiverState(unit_id=args.unit_id, unit_role=args.unit_role)
    receiver = Receiver(
        state=state,
        trust_ctx=trust_ctx,
        receiver_key=receiver_key,
        deploy_root=args.deploy_to,
    )

    # Verify and deploy
    verification, receipt = receiver.verify_and_deploy(
        passport=passport, files=files,
    )

    # Output results
    print(f"Eligibility: {verification.eligibility.value}")
    print(verification.summary())

    if receipt:
        receipt_path = Path(args.deploy_to) / "deployment_receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(receipt.to_dict(), indent=2),
            encoding="utf-8",
        )
        print(f"\nReceipt written to: {receipt_path}")

    sys.exit(0 if receipt else 1)


def _do_status(args: argparse.Namespace) -> None:
    """Show receiver state."""
    state_path = Path(args.state_dir) / "receiver_state.json"
    if not state_path.exists():
        print("No receiver state found.")
        sys.exit(1)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()

