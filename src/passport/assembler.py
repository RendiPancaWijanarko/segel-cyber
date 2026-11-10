# SPDX-License-Identifier: MIT
"""Passport Builder — assembles Release Passports from verified evidence.

Per PRD v2.0 §7.10 and TAS §8.7:
- Assembles candidate passports (for canary) and general passports.
- Includes all DSSE-wrapped attestation envelopes.
- Includes Merkle inclusion proofs from the transparency ledger.
- Includes the trust snapshot and epoch bounds.
- The passport is the single artifact a Receiver needs to verify offline.
"""

from __future__ import annotations

from typing import Any

from segel_core.crypto.dsse import DSSEEnvelope
from segel_core.schemas.checkpoint import SignedCheckpoint
from segel_core.schemas.passport import LedgerProof, ReleasePassport


def build_candidate_passport(
    manifest_envelope: DSSEEnvelope,
    origin_envelope: DSSEEnvelope,
    inspect_envelope: DSSEEnvelope,
    approve_envelope: DSSEEnvelope,
    candidate_proof: LedgerProof,
    signed_checkpoint: SignedCheckpoint,
    snapshot: dict[str, Any] | None = None,
    min_epoch: int = 1,
) -> ReleasePassport:
    """Assemble a candidate Release Passport for canary deployment.

    Args:
        manifest_envelope: Signed manifest DSSE.
        origin_envelope: Signed Origin attestation DSSE.
        inspect_envelope: Signed Inspect attestation DSSE.
        approve_envelope: Signed Approve attestation DSSE.
        candidate_proof: Merkle proof for the candidate_recorded event.
        signed_checkpoint: The signed ledger checkpoint.
        snapshot: Trust snapshot dict, if available.
        min_epoch: Minimum receiver epoch required.

    Returns:
        A ReleasePassport of type "candidate".
    """
    if signed_checkpoint is not None and isinstance(candidate_proof, LedgerProof):
        updates_c: dict[str, Any] = {}
        if not candidate_proof.checkpoint_signature and signed_checkpoint.ledger_signature:
            updates_c["checkpoint_signature"] = signed_checkpoint.ledger_signature
        if not candidate_proof.witness_cosignatures and signed_checkpoint.witness_cosignatures:
            updates_c["witness_cosignatures"] = [
                w["signature"] if isinstance(w, dict) else str(w)
                for w in signed_checkpoint.witness_cosignatures
            ]
        if updates_c:
            candidate_proof = candidate_proof.model_copy(update=updates_c)

    return ReleasePassport(
        passport_type="candidate",
        manifest_envelope=manifest_envelope.to_dict(),
        origin_envelope=origin_envelope.to_dict(),
        inspect_envelope=inspect_envelope.to_dict(),
        approve_envelope=approve_envelope.to_dict(),
        record_candidate_proof=candidate_proof,
        snapshot=snapshot,
        min_epoch=min_epoch,
    )


def build_general_passport(
    manifest_envelope: DSSEEnvelope,
    origin_envelope: DSSEEnvelope,
    inspect_envelope: DSSEEnvelope,
    approve_envelope: DSSEEnvelope,
    candidate_proof: LedgerProof,
    test_envelopes: list[DSSEEnvelope],
    promotion_proof: LedgerProof,
    signed_checkpoint: SignedCheckpoint,
    snapshot: dict[str, Any] | None = None,
    min_epoch: int = 1,
) -> ReleasePassport:
    """Assemble a general Release Passport after canary promotion.

    Args:
        manifest_envelope: Signed manifest DSSE.
        origin_envelope: Signed Origin attestation DSSE.
        inspect_envelope: Signed Inspect attestation DSSE.
        approve_envelope: Signed Approve attestation DSSE.
        candidate_proof: Merkle proof for the candidate_recorded event.
        test_envelopes: Signed Test attestation DSSEs (canary receipts).
        promotion_proof: Merkle proof for the release_promoted event.
        signed_checkpoint: The signed ledger checkpoint.
        snapshot: Trust snapshot dict, if available.
        min_epoch: Minimum receiver epoch required.

    Returns:
        A ReleasePassport of type "general".
    """
    if signed_checkpoint is not None:
        if isinstance(candidate_proof, LedgerProof):
            updates_c: dict[str, Any] = {}
            if not candidate_proof.checkpoint_signature and signed_checkpoint.ledger_signature:
                updates_c["checkpoint_signature"] = signed_checkpoint.ledger_signature
            if not candidate_proof.witness_cosignatures and signed_checkpoint.witness_cosignatures:
                updates_c["witness_cosignatures"] = [
                    w["signature"] if isinstance(w, dict) else str(w)
                    for w in signed_checkpoint.witness_cosignatures
                ]
            if updates_c:
                candidate_proof = candidate_proof.model_copy(update=updates_c)

        if isinstance(promotion_proof, LedgerProof):
            updates_p: dict[str, Any] = {}
            if not promotion_proof.checkpoint_signature and signed_checkpoint.ledger_signature:
                updates_p["checkpoint_signature"] = signed_checkpoint.ledger_signature
            if not promotion_proof.witness_cosignatures and signed_checkpoint.witness_cosignatures:
                updates_p["witness_cosignatures"] = [
                    w["signature"] if isinstance(w, dict) else str(w)
                    for w in signed_checkpoint.witness_cosignatures
                ]
            if updates_p:
                promotion_proof = promotion_proof.model_copy(update=updates_p)

    return ReleasePassport(
        passport_type="general",
        manifest_envelope=manifest_envelope.to_dict(),
        origin_envelope=origin_envelope.to_dict(),
        inspect_envelope=inspect_envelope.to_dict(),
        approve_envelope=approve_envelope.to_dict(),
        record_candidate_proof=candidate_proof,
        test_envelopes=[env.to_dict() for env in test_envelopes],
        record_promotion_proof=promotion_proof,
        snapshot=snapshot,
        min_epoch=min_epoch,
    )

