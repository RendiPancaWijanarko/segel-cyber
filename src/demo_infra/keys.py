# SPDX-License-Identifier: MIT
"""Synthetic demo key generator for MVP demonstration harness."""

from __future__ import annotations

from dataclasses import dataclass

from segel_core.crypto.ed25519 import KeyPair, export_public_key, generate_keypair
from segel_core.schemas.trust import KeyRecord


@dataclass
class DemoKeyBundle:
    author_key: KeyPair
    builder_key: KeyPair
    inspector_key: KeyPair
    ledger_key: KeyPair
    witness_key: KeyPair
    canary_keys: list[KeyPair]
    general_receiver_key: KeyPair

    def make_key_records(self) -> list[KeyRecord]:
        def kr(kp: KeyPair, role: str, group: str = "default") -> KeyRecord:
            return KeyRecord(
                key_id=kp.key_id,
                public_key_b64=export_public_key(kp.public_key_bytes),
                role=role,
                group=group,
            )

        return [
            kr(self.author_key, "author"),
            kr(self.builder_key, "builder"),
            kr(self.inspector_key, "inspector_signer"),
            kr(self.ledger_key, "ledger"),
            kr(self.witness_key, "witness"),
            kr(self.canary_keys[0], "receiver"),
            kr(self.canary_keys[1], "receiver"),
            kr(self.general_receiver_key, "receiver"),
        ]


def generate_demo_bundle() -> DemoKeyBundle:
    return DemoKeyBundle(
        author_key=generate_keypair(),
        builder_key=generate_keypair(),
        inspector_key=generate_keypair(),
        ledger_key=generate_keypair(),
        witness_key=generate_keypair(),
        canary_keys=[generate_keypair() for _ in range(2)],
        general_receiver_key=generate_keypair(),
    )
