# SPDX-License-Identifier: MIT
"""Approver — air-gapped multi-party approval device.

Per PRD v2.0 §7.7 and TAS §8.5:
- Approvers review the actual approval payload on a separate device.
- The approval payload is transferred via QR code (air-gapped).
- Each approver signs with their own key.
- Author MUST NOT approve their own release (SEC-001).
- Duplicate signatures from one key don't count toward threshold.
- Approval binds origin + inspect evidence digests.
- Pre-committed promotion criteria are included.

The Approver process:
1. Release Desk generates a QR code containing the approval request.
2. Approver scans QR, reviews the payload on their device.
3. Approver confirms with PIN and signs.
4. Approver's device displays a QR code with the signature.
5. Release Desk scans the response QR and collects signatures.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from segel_core.canonical import canonical_json
from segel_core.crypto.dsse import DSSEEnvelope
from segel_core.crypto.dsse import pae as dsse_pae
from segel_core.crypto.ed25519 import KeyPair, generate_evidence_id, sign
from segel_core.crypto.hashing import sha256_hex
from segel_core.schemas.attestation import (
    APPROVE_PREDICATE_TYPE,
    ApprovePredicate,
    InTotoStatement,
    InTotoSubject,
    PromotionCriteria,
)
from segel_core.schemas.binding import BindingBlock, ReleaseSubject
from segel_core.schemas.manifest import Manifest


@dataclass
class ApprovalRequest:
    """Payload sent to an approver for review."""
    release_id: str
    sequence: int
    manifest_digest: str
    purpose: str
    origin_evidence_digest: str
    inspect_evidence_digest: str
    inspect_verdict: str
    canary_targets: list[str]
    promotion_criteria: dict[str, Any]
    # The actual bytes to sign (canonical JSON of the approval predicate)
    payload_to_sign: bytes
    payload_type: str


@dataclass
class ApprovalResponse:
    """Signed response from an approver."""
    approver_key_id: str
    signature_b64: str
    approved: bool


def create_approval_payload(
    manifest: Manifest,
    manifest_digest: str,
    origin_envelope: DSSEEnvelope,
    inspect_envelope: DSSEEnvelope,
    inspect_verdict: str,
    trust_root_version: int = 1,
    policy_version: int = 1,
    canary_targets: list[str] | None = None,
    promotion_criteria: PromotionCriteria | None = None,
) -> tuple[dict[str, Any], ApprovalRequest]:
    """Create the approval attestation payload.

    This creates the in-toto Statement for the Approve stamp.
    It binds the origin and inspect evidence by their digests.

    Args:
        manifest: The release manifest.
        manifest_digest: SHA-256 hex of the manifest bytes.
        origin_envelope: The signed Origin DSSE envelope.
        inspect_envelope: The signed Inspect DSSE envelope.
        inspect_verdict: The inspect verdict (PASS/WARN/REJECT).
        trust_root_version: Current trust root version.
        policy_version: Current policy version.
        canary_targets: Unit IDs for canary deployment.
        promotion_criteria: Pre-committed promotion criteria.

    Returns:
        Tuple of (statement_dict, approval_request).
    """
    # Compute evidence digests
    origin_digest = sha256_hex(canonical_json(origin_envelope.to_dict()))
    inspect_digest = sha256_hex(canonical_json(inspect_envelope.to_dict()))

    binding = BindingBlock(
        stamp="approve",
        subject=ReleaseSubject(
            release_id=manifest.release_id,
            sequence=manifest.sequence,
            manifest_sha256=manifest_digest,
        ),
        trust_root_version=trust_root_version,
        policy_version=policy_version,
        evidence_id=generate_evidence_id(),
    )

    criteria = promotion_criteria or PromotionCriteria()

    predicate = ApprovePredicate(
        binding=binding,
        origin_evidence_digest=origin_digest,
        inspect_evidence_digest=inspect_digest,
        canary_targets=canary_targets or manifest.canary_targets,
        promotion_criteria=criteria,
    )

    in_toto_subject = InTotoSubject(
        name=f"release/{manifest.release_id}@{manifest.sequence}",
        digest={"sha256": manifest_digest},
    )

    statement = InTotoStatement(
        subject=[in_toto_subject],
        predicateType=APPROVE_PREDICATE_TYPE,
        predicate=predicate.model_dump(mode="json"),
    )

    statement_dict = statement.model_dump(by_alias=True, mode="json")
    payload = canonical_json(statement_dict)

    request = ApprovalRequest(
        release_id=manifest.release_id,
        sequence=manifest.sequence,
        manifest_digest=manifest_digest,
        purpose=manifest.purpose,
        origin_evidence_digest=origin_digest,
        inspect_evidence_digest=inspect_digest,
        inspect_verdict=inspect_verdict,
        canary_targets=canary_targets or manifest.canary_targets,
        promotion_criteria=criteria.model_dump(mode="json"),
        payload_to_sign=payload,
        payload_type="application/vnd.segel.approve+json",
    )

    return statement_dict, request


def approver_sign(
    request: ApprovalRequest,
    approver_key: KeyPair,
) -> ApprovalResponse:
    """Sign an approval request with an approver's key.

    This is called on the approver's device after review.

    Args:
        request: The approval request.
        approver_key: The approver's signing key.

    Returns:
        ApprovalResponse with the signature.
    """
    # Sign the PAE of the payload (matching DSSE convention)
    pae_bytes = dsse_pae(request.payload_type, request.payload_to_sign)
    sig = sign(approver_key.private_key, pae_bytes)
    sig_b64 = base64.b64encode(sig).decode("ascii")

    return ApprovalResponse(
        approver_key_id=approver_key.key_id,
        signature_b64=sig_b64,
        approved=True,
    )


def collect_approvals(
    statement_dict: dict[str, Any],
    request: ApprovalRequest,
    responses: list[ApprovalResponse],
) -> DSSEEnvelope:
    """Collect approval signatures into a DSSE envelope.

    Args:
        statement_dict: The in-toto statement dict.
        request: The original approval request.
        responses: List of approval responses from approvers.

    Returns:
        A DSSE envelope with all approver signatures.
    """
    # Build envelope manually with collected signatures
    payload_b64 = base64.b64encode(request.payload_to_sign).decode("ascii")

    signatures = []
    for resp in responses:
        if resp.approved:
            signatures.append({
                "keyid": resp.approver_key_id,
                "sig": resp.signature_b64,
            })

    envelope_dict = {
        "payloadType": request.payload_type,
        "payload": payload_b64,
        "signatures": signatures,
    }

    return DSSEEnvelope.from_dict(envelope_dict)


def generate_qr_request(request: ApprovalRequest) -> str:
    """Generate a compact JSON payload for QR transfer to approver device.

    The QR payload contains enough information for the approver to:
    1. Understand what they're approving.
    2. Sign the exact payload.

    Returns:
        JSON string for QR encoding.
    """
    qr_data = {
        "type": "segel_approve_request",
        "release_id": request.release_id,
        "seq": request.sequence,
        "purpose": request.purpose[:100],  # Truncate for QR
        "manifest_sha256": request.manifest_digest,
        "origin_digest": request.origin_evidence_digest[:16] + "...",
        "inspect_digest": request.inspect_evidence_digest[:16] + "...",
        "verdict": request.inspect_verdict,
        "payload_b64": base64.b64encode(request.payload_to_sign).decode("ascii"),
        "payload_type": request.payload_type,
    }
    return json.dumps(qr_data, separators=(",", ":"))


def parse_qr_response(qr_json: str) -> ApprovalResponse:
    """Parse a QR response from an approver device.

    Returns:
        ApprovalResponse parsed from the QR data.
    """
    data = json.loads(qr_json)
    return ApprovalResponse(
        approver_key_id=data["key_id"],
        signature_b64=data["sig"],
        approved=data.get("approved", True),
    )

