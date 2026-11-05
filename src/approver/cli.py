#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""CLI for the SEGEL Approver device.

Usage:
    segel-approver review <qr-data.json> --key <approver-key.json>
    segel-approver scan <qr-image.png> --key <approver-key.json>
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="segel-approver",
        description="SEGEL Approver — review and sign approval payloads.",
    )
    sub = parser.add_subparsers(dest="command")

    # review command
    review_cmd = sub.add_parser("review", help="Review and sign an approval request")
    review_cmd.add_argument("qr_data", help="Path to QR data JSON file")
    review_cmd.add_argument("--key", required=True, help="Path to approver key JSON")
    review_cmd.add_argument("--auto-approve", action="store_true",
                            help="Skip interactive review (demo mode)")

    args = parser.parse_args()

    if args.command == "review":
        _do_review(args)
    else:
        parser.print_help()
        sys.exit(1)


def _do_review(args: argparse.Namespace) -> None:
    """Review an approval request and sign it."""
    from segel_core.crypto.dsse import pae as dsse_pae
    from segel_core.crypto.ed25519 import import_private_key, sign

    # Load QR data
    qr_data = json.loads(Path(args.qr_data).read_text(encoding="utf-8"))

    # Display for review
    print("=" * 60)
    print("  SEGEL APPROVAL REQUEST")
    print("=" * 60)
    print(f"  Release ID:    {qr_data.get('release_id', '?')}")
    print(f"  Sequence:      {qr_data.get('seq', '?')}")
    print(f"  Purpose:       {qr_data.get('purpose', '?')}")
    print(f"  Manifest:      {qr_data.get('manifest_sha256', '?')[:32]}...")
    print(f"  Origin digest: {qr_data.get('origin_digest', '?')}")
    print(f"  Inspect:       {qr_data.get('inspect_digest', '?')}")
    print(f"  Verdict:       {qr_data.get('verdict', '?')}")
    print("=" * 60)

    if not args.auto_approve:
        response = input("\nApprove this release? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("Approval DECLINED.")
            sys.exit(1)

    # Load approver key
    key_data = json.loads(Path(args.key).read_text(encoding="utf-8"))
    key_pair = import_private_key(bytes.fromhex(key_data["private_key_hex"]))

    # Sign the payload
    payload_b64 = qr_data["payload_b64"]
    payload_bytes = base64.b64decode(payload_b64)
    payload_type = qr_data["payload_type"]

    pae_bytes = dsse_pae(payload_type, payload_bytes)
    sig = sign(key_pair.private_key, pae_bytes)
    sig_b64 = base64.b64encode(sig).decode("ascii")

    # Output response for QR encoding
    response_data = {
        "type": "segel_approve_response",
        "key_id": key_pair.key_id,
        "sig": sig_b64,
        "approved": True,
    }

    response_json = json.dumps(response_data, indent=2)
    print(f"\nApproval signed with key: {key_pair.key_id[:16]}...")
    print("\nResponse (for QR encoding):")
    print(response_json)

    # Write to file
    out_path = Path(args.qr_data).with_suffix(".response.json")
    out_path.write_text(response_json, encoding="utf-8")
    print(f"\nResponse written to: {out_path}")


if __name__ == "__main__":
    main()

