# SPDX-License-Identifier: MIT
"""Standalone Approver Signer Service — SEC-004 / Decision D1.

Per SEC-004 & PRD §7.7:
Approver private keys reside in an isolated signer process/service.
The Release Desk communicates with the Approver Signer only via
structured approval requests (ApprovalRequest) and receives signed
ApprovalResponses.
"""

from __future__ import annotations

from approver.approver import (
    ApprovalRequest,
    ApprovalResponse,
    approver_sign,
)
from segel_core.crypto.ed25519 import KeyPair, export_public_key, generate_keypair
from segel_core.schemas.trust import KeyRecord


class StandaloneApproverSigner:
    """Isolated signing service holding approver private keys."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset and generate 3 fresh approver keys."""
        self._keys: list[KeyPair] = [generate_keypair() for _ in range(3)]
        self._groups: list[str] = ["group-0", "group-1", "group-0"]

    def get_public_key_records(self) -> list[KeyRecord]:
        """Export public key records for the trust root."""
        records = []
        for kp, group in zip(self._keys, self._groups, strict=False):
            records.append(
                KeyRecord(
                    key_id=kp.key_id,
                    public_key_b64=export_public_key(kp.public_key_bytes),
                    role="approver",
                    group=group,
                )
            )
        return records

    def sign_approval_request(
        self,
        request: ApprovalRequest,
        count: int = 2,
    ) -> list[ApprovalResponse]:
        """Sign an approval request with up to `count` approver keys from different groups.

        Args:
            request: The ApprovalRequest payload to review and sign.
            count: Number of distinct signatures to provide.

        Returns:
            List of ApprovalResponse objects with valid signatures.
        """
        responses: list[ApprovalResponse] = []
        for i in range(min(count, len(self._keys))):
            resp = approver_sign(request, self._keys[i])
            responses.append(resp)
        return responses

