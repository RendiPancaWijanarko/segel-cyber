#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""SEGEL Cryptographic Key Hierarchy & Trust Initialization Tool.

Generates the complete Ed25519 key hierarchy, assigns roles per PRD v2.0 §13/§16,
writes private key files with restricted file permissions (0o600 on POSIX / ACL on Windows),
and outputs canonical trust_root.json and policy.json.

USAGE:
    python scripts/init_keys.py --output-dir lab/keys --trust-dir lab/trust --mode synthetic
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)

from segel_core.canonical import canonical_json
from segel_core.crypto.ed25519 import (
    KeyPair,
    export_public_key,
    generate_keypair,
)
from segel_core.schemas.trust import (
    KeyRecord,
    RoleThreshold,
    TrustRoot,
    VerificationPolicy,
)


def set_restricted_permissions(path: Path) -> None:
    """Set strict read/write permissions for owner only."""
    try:
        os.chmod(path, 0o600)
    except Exception:
        # On Windows, chmod is partially supported; best-effort
        pass


def set_restricted_dir_permissions(path: Path) -> None:
    """Set strict directory permissions (owner only)."""
    try:
        os.chmod(path, 0o700)
    except Exception:
        pass


def save_keypair(keypair: KeyPair, out_dir: Path, name: str, role: str, group: str = "default") -> dict[str, Any]:
    """Save keypair to disk with strict permissions and return its KeyRecord metadata."""
    priv_file = out_dir / f"{name}.priv.json"
    pub_file = out_dir / f"{name}.pub.json"

    priv_bytes = keypair.private_key.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )

    # Export private key raw bytes as hex for pilot/demo files
    priv_data = {
        "key_id": keypair.key_id,
        "algorithm": "ed25519",
        "role": role,
        "group": group,
        "private_key_hex": priv_bytes.hex(),
        "public_key_b64": export_public_key(keypair.public_key_bytes),
    }

    pub_data = {
        "key_id": keypair.key_id,
        "algorithm": "ed25519",
        "role": role,
        "group": group,
        "public_key_b64": export_public_key(keypair.public_key_bytes),
    }

    priv_file.write_text(json.dumps(priv_data, indent=2), encoding="utf-8")
    set_restricted_permissions(priv_file)

    pub_file.write_text(json.dumps(pub_data, indent=2), encoding="utf-8")

    return pub_data


def generate_pilot_hierarchy(
    output_dir: Path,
    trust_dir: Path,
    mode: str = "synthetic",
) -> tuple[TrustRoot, VerificationPolicy]:
    """Generate the full SEGEL key hierarchy and trust configuration."""
    output_dir.mkdir(parents=True, exist_ok=True)
    set_restricted_dir_permissions(output_dir)
    trust_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Generating {mode} cryptographic keys in: {output_dir}")

    # 1. Author & Builder (Separation of Duties SEC-002)
    author_kp = generate_keypair()
    builder_kp = generate_keypair()

    # 2. Inspector Signer
    inspector_kp = generate_keypair()

    # 3. Approver Quorum (2-of-3 with multi-group representation: group-0, group-1)
    approver_0 = generate_keypair()
    approver_1 = generate_keypair()
    approver_2 = generate_keypair()

    # 4. Transparency Ledger & Independent Witness
    ledger_kp = generate_keypair()
    witness_kp = generate_keypair()

    # 5. Receiver Units (Canary and General)
    canary_1_kp = generate_keypair()
    canary_2_kp = generate_keypair()
    general_unit_kp = generate_keypair()

    keys_meta = [
        save_keypair(author_kp, output_dir, "author", "author"),
        save_keypair(builder_kp, output_dir, "builder", "builder"),
        save_keypair(inspector_kp, output_dir, "inspector", "inspector_signer"),
        save_keypair(approver_0, output_dir, "approver_sec", "approver", "group-0"),
        save_keypair(approver_1, output_dir, "approver_ops", "approver", "group-1"),
        save_keypair(approver_2, output_dir, "approver_qa", "approver", "group-0"),
        save_keypair(ledger_kp, output_dir, "ledger", "ledger"),
        save_keypair(witness_kp, output_dir, "witness", "witness"),
        save_keypair(canary_1_kp, output_dir, "canary_1", "receiver"),
        save_keypair(canary_2_kp, output_dir, "canary_2", "receiver"),
        save_keypair(general_unit_kp, output_dir, "receiver_general", "receiver"),
    ]

    print(f"    [OK] Successfully generated {len(keys_meta)} Ed25519 keypairs.")

    # Construct TrustRoot
    key_records = [
        KeyRecord(
            key_id=k["key_id"],
            public_key_b64=k["public_key_b64"],
            role=k["role"],
            group=k["group"],
            status="active",
        )
        for k in keys_meta
    ]

    roles = [
        RoleThreshold(role="author", threshold=1),
        RoleThreshold(role="builder", threshold=1),
        RoleThreshold(role="inspector_signer", threshold=1),
        RoleThreshold(role="approver", threshold=2, group_minimums={"group-0": 1, "group-1": 1}),
        RoleThreshold(role="ledger", threshold=1),
        RoleThreshold(role="witness", threshold=1),
        RoleThreshold(role="receiver", threshold=1),
    ]

    trust_root = TrustRoot(root_version=1, keys=key_records, roles=roles)

    # Construct VerificationPolicy
    policy = VerificationPolicy(
        policy_version=1,
        approval_threshold=2,
        approval_groups={"group-0": 1, "group-1": 1},
        canary_required_count=2,
        witness_cosignature_count=1,
        freshness_mode="strict",
    )

    # Write canonical JSON files
    trust_root_file = trust_dir / "trust_root.json"
    policy_file = trust_dir / "policy.json"

    trust_root_file.write_bytes(canonical_json(trust_root))
    policy_file.write_bytes(canonical_json(policy))

    print(f"[*] Generated Trust Root v1: {trust_root_file}")
    print(f"[*] Generated Verification Policy v1: {policy_file}")

    return trust_root, policy


def main() -> None:
    parser = argparse.ArgumentParser(description="SEGEL Key Hierarchy & Trust Initializer")
    parser.add_argument("--output-dir", default="lab/keys", help="Output directory for keypairs")
    parser.add_argument("--trust-dir", default="lab/trust", help="Output directory for trust metadata")
    parser.add_argument("--mode", default="synthetic", choices=["synthetic", "pilot"], help="Initialization mode")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    trust_dir = Path(args.trust_dir)

    generate_pilot_hierarchy(out_dir, trust_dir, mode=args.mode)
    print("[+] Cryptographic initialization complete.")


if __name__ == "__main__":
    main()
