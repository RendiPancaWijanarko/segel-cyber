# SPDX-License-Identifier: MIT
"""Release Passport schema — the bundle of evidence accompanying a release.

The Release Passport is the single artefact that a Receiver verifies before
applying a release.  It bundles:

* The DSSE-wrapped manifest.
* DSSE-wrapped attestation envelopes for every stamp (origin, inspect,
  approve, test).
* Merkle inclusion proofs from the transparency ledger (candidate_recorded
  and release_promoted events).
* The trust snapshot at assembly time plus epoch bounds.

Two passport types exist:

* ``candidate`` — delivered to canary targets; contains origin, inspect,
  approve envelopes plus the ``record_candidate_proof``.
* ``general`` — delivered after canary promotion; additionally contains
  test envelopes and the ``record_promotion_proof``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LedgerProof(BaseModel):
    """A Merkle inclusion proof from the transparency ledger.

    Allows offline verification that a specific event (identified by
    ``leaf_hash``) is included in the log at the given checkpoint.
    """

    event_type: str = Field(
        ...,
        min_length=1,
        description="Event type: 'candidate_recorded' or 'release_promoted'",
    )
    entry_index: int = Field(
        ...,
        ge=0,
        description="Zero-based index of the entry in the Merkle log",
    )
    leaf_hash: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 hash of the leaf (0x00 || data)",
    )
    inclusion_proof: list[str] = Field(
        default_factory=list,
        description="Hex-encoded sibling hashes forming the Merkle proof",
    )
    checkpoint_size: int = Field(
        ...,
        ge=1,
        description="Log size at the checkpoint this proof is relative to",
    )
    checkpoint_root_hash: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="Merkle root hash at the checkpoint",
    )
    checkpoint_signature: str = Field(
        default="",
        description="Base64-encoded ledger signer signature over the checkpoint",
    )
    witness_cosignatures: list[str] = Field(
        default_factory=list,
        description="Base64-encoded witness cosignatures over the checkpoint",
    )


class ReleasePassport(BaseModel):
    """The Release Passport — all evidence for a release.

    Schema ``segel.passport/v1`` — assembled by the Passport Assembler and
    verified by Receivers.  The verifier checks every envelope, every proof,
    cross-references bindings, and enforces the policy before allowing
    deployment.
    """

    schema_version: str = Field(
        default="segel.passport/v1",
        description="Schema identifier for forward compatibility",
    )
    passport_type: str = Field(
        ...,
        pattern=r"^(candidate|general)$",
        description="Passport type: candidate (canary) or general (full rollout)",
    )
    manifest_envelope: dict[str, Any] = Field(
        ...,
        description="DSSE envelope containing the signed manifest",
    )
    origin_envelope: dict[str, Any] = Field(
        ...,
        description="DSSE envelope containing the Origin attestation",
    )
    inspect_envelope: dict[str, Any] = Field(
        ...,
        description="DSSE envelope containing the Inspect attestation",
    )
    approve_envelope: dict[str, Any] = Field(
        ...,
        description="DSSE envelope containing the Approve attestation (threshold signatures)",
    )
    record_candidate_proof: LedgerProof | None = Field(
        default=None,
        description="Merkle proof for the 'candidate_recorded' ledger event",
    )
    test_envelopes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="DSSE envelopes of canary/general deployment receipts (Test stamps)",
    )
    record_promotion_proof: LedgerProof | None = Field(
        default=None,
        description="Merkle proof for the 'release_promoted' ledger event",
    )
    snapshot: dict[str, Any] | None = Field(
        default=None,
        description="Trust snapshot at passport assembly time",
    )
    min_epoch: int = Field(
        default=1,
        ge=1,
        description="Minimum epoch the receiver must be at to accept this passport",
    )
    valid_until_epoch: int | None = Field(
        default=None,
        description="Optional upper-bound epoch after which this passport is stale",
    )
