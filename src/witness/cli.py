#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""CLI for the SEGEL Witness process.

Usage:
    segel-witness cosign --key <witness-key.json> --checkpoint <checkpoint.json>
    segel-witness status --state-file <state.json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="segel-witness",
        description="SEGEL Witness — cosign ledger checkpoints.",
    )
    sub = parser.add_subparsers(dest="command")

    # cosign command
    cosign_cmd = sub.add_parser("cosign", help="Cosign a ledger checkpoint")
    cosign_cmd.add_argument("--key", required=True, help="Path to witness key JSON")
    cosign_cmd.add_argument("--checkpoint", required=True, help="Path to checkpoint JSON")
    cosign_cmd.add_argument("--consistency-proof", help="Path to consistency proof JSON")
    cosign_cmd.add_argument("--state-file", help="Path to witness state file")

    # status command
    status_cmd = sub.add_parser("status", help="Show witness state")
    status_cmd.add_argument("--state-file", required=True, help="Path to state file")

    args = parser.parse_args()

    if args.command == "cosign":
        _do_cosign(args)
    elif args.command == "status":
        _do_status(args)
    else:
        parser.print_help()
        sys.exit(1)


def _do_cosign(args: argparse.Namespace) -> None:
    """Cosign a checkpoint."""
    from segel_core.crypto.ed25519 import import_private_key
    from segel_core.schemas.checkpoint import Checkpoint
    from witness.witness import Witness, WitnessState

    # Load key
    key_data = json.loads(Path(args.key).read_text(encoding="utf-8"))
    key_pair = import_private_key(bytes.fromhex(key_data["private_key_hex"]))

    # Load checkpoint
    cp_data = json.loads(Path(args.checkpoint).read_text(encoding="utf-8"))
    checkpoint = Checkpoint(**cp_data)

    # Load state if exists
    state = WitnessState()
    if args.state_file:
        state_path = Path(args.state_file)
        if state_path.exists():
            s = json.loads(state_path.read_text(encoding="utf-8"))
            state = WitnessState(
                last_checkpoint_size=s.get("last_checkpoint_size", 0),
                last_checkpoint_root_hash=s.get("last_checkpoint_root_hash", ""),
            )

    # Load consistency proof if provided
    consistency_proof = None
    if args.consistency_proof:
        proof_data = json.loads(Path(args.consistency_proof).read_text(encoding="utf-8"))
        consistency_proof = [bytes.fromhex(h) for h in proof_data]

    # Cosign
    witness = Witness(key_pair, state=state)
    cosig = witness.cosign_checkpoint(checkpoint, consistency_proof=consistency_proof)

    # Output
    print(f"Checkpoint cosigned by witness {key_pair.key_id[:16]}...")
    print(f"Size: {checkpoint.size}")
    print(f"Root: {checkpoint.root_hash}")
    print(f"Cosignature: {cosig[:32]}...")

    result = {
        "key_id": key_pair.key_id,
        "signature": cosig,
        "checkpoint_size": checkpoint.size,
    }
    print(json.dumps(result, indent=2))

    # Save state
    if args.state_file:
        state_path = Path(args.state_file)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({
            "last_checkpoint_size": witness.state.last_checkpoint_size,
            "last_checkpoint_root_hash": witness.state.last_checkpoint_root_hash,
        }, indent=2), encoding="utf-8")
        print(f"\nState saved to: {state_path}")


def _do_status(args: argparse.Namespace) -> None:
    """Show witness state."""
    state_path = Path(args.state_file)
    if not state_path.exists():
        print("No witness state found.")
        sys.exit(1)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()

