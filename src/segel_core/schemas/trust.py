# SPDX-License-Identifier: MIT
"""Trust metadata schemas: root, policy, snapshot (PRD v2.0 §16.1).

The trust layer defines three versioned, signed documents:

1. **TrustRoot** — The key registry and role thresholds.  Every key is
   identified by ``SHA-256(raw_public_key_bytes)``.  Keys are never deleted;
   they are revoked by setting ``status="revoked"`` and recording the ledger
   index at which revocation took effect.

2. **VerificationPolicy** — Specifies which stamps are required, approval
   thresholds, canary requirements, allowed adapters, and freshness mode.

3. **TrustSnapshot** — An epoch-versioned snapshot of revoked keys and held
   releases, plus a reference to the latest ledger checkpoint.  Receivers use
   the snapshot to detect stale or revoked state without querying the ledger
   directly.

All three documents are versioned monotonically and enveloped in DSSE for
integrity.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Trust Root
# ---------------------------------------------------------------------------


class KeyRecord(BaseModel):
    """A key and its role in the trust root.

    ``key_id`` is always ``SHA-256(raw_public_key_bytes)`` encoded as
    lowercase hex.  ``public_key_b64`` is the base64-encoded 32-byte raw
    Ed25519 public key.

    Supported roles: root, policy, snapshot, author, builder,
    inspector_signer, approver, ledger, witness, receiver.
    """

    key_id: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 of the raw Ed25519 public key bytes",
    )
    public_key_b64: str = Field(
        ...,
        min_length=1,
        description="Base64-encoded 32-byte raw Ed25519 public key",
    )
    role: str = Field(
        ...,
        min_length=1,
        description=(
            "Role: root, policy, snapshot, author, builder, "
            "inspector_signer, approver, ledger, witness, receiver"
        ),
    )
    algorithm: str = Field(
        default="ed25519",
        description="Signing algorithm (only ed25519 is supported)",
    )
    status: str = Field(
        default="active",
        pattern=r"^(active|revoked)$",
        description="Key status: active or revoked",
    )
    revoked_at_index: int | None = Field(
        default=None,
        description="Ledger index at which the key was revoked (None if active)",
    )
    group: str = Field(
        default="default",
        description="Approver group for per-group minimum thresholds",
    )


class RoleThreshold(BaseModel):
    """Threshold requirements for a given role.

    ``threshold`` is the minimum number of distinct signers required.
    ``group_minimums`` optionally sets per-group floors so that no single
    organisational group can unilaterally satisfy the threshold.
    """

    role: str = Field(
        ...,
        min_length=1,
        description="Role name this threshold applies to",
    )
    threshold: int = Field(
        ...,
        ge=1,
        description="Minimum number of distinct signers required",
    )
    group_minimums: dict[str, int] = Field(
        default_factory=dict,
        description="Per-group minimum signer counts",
    )


class TrustRoot(BaseModel):
    """Signed trust root metadata.

    Schema ``segel.root/v1`` — contains all authorised keys and role
    threshold definitions.  ``root_version`` increases monotonically;
    the verifier rejects any root whose version is not strictly greater
    than the previously accepted one.
    """

    schema_version: str = Field(
        default="segel.root/v1",
        description="Schema identifier for forward compatibility",
    )
    root_version: int = Field(
        ...,
        ge=1,
        description="Monotonically increasing trust root version",
    )
    keys: list[KeyRecord] = Field(
        default_factory=list,
        description="All keys registered in the trust root",
    )
    roles: list[RoleThreshold] = Field(
        default_factory=list,
        description="Threshold definitions for each role",
    )


# ---------------------------------------------------------------------------
# Verification Policy
# ---------------------------------------------------------------------------


class AdapterPolicy(BaseModel):
    """Allowed deployment adapter.

    The policy whitelists deployment adapters by their identity digest and
    the payload type they handle.
    """

    adapter_id: str = Field(
        ...,
        min_length=1,
        description="Adapter identity string",
    )
    digest: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 digest of the adapter binary / script",
    )
    payload_type: str = Field(
        ...,
        min_length=1,
        description="Payload type the adapter is allowed to deploy",
    )


def _default_allowed_adapters() -> list[AdapterPolicy]:
    return [
        AdapterPolicy(
            adapter_id="segel-baseline-adapter/v1",
            digest="0" * 64,
            payload_type="baseline/v1",
        )
    ]


class VerificationPolicy(BaseModel):
    """Signed verification policy.

    Schema ``segel.policy/v1`` — controls what evidence is required and
    the minimum quality thresholds.  ``policy_version`` increases
    monotonically; the verifier rejects downgrades.
    """

    schema_version: str = Field(
        default="segel.policy/v1",
        description="Schema identifier for forward compatibility",
    )
    policy_version: int = Field(
        ...,
        ge=1,
        description="Monotonically increasing policy version",
    )
    required_stamps: list[str] = Field(
        default_factory=lambda: ["origin", "inspect", "approve", "record", "test"],
        description="Pipeline stamps that must be present for a valid release",
    )
    approval_threshold: int = Field(
        default=2,
        ge=1,
        description="Minimum number of distinct approver signatures",
    )
    approval_groups: dict[str, int] = Field(
        default_factory=dict,
        description="Per-group minimum approver counts",
    )
    min_inspect_policy_version: int = Field(
        default=1,
        ge=1,
        description="Minimum inspection policy version accepted",
    )
    canary_required_count: int = Field(
        default=2,
        ge=1,
        description="Minimum number of healthy canary units before promotion",
    )
    freshness_mode: str = Field(
        default="advisory",
        pattern=r"^(strict|advisory)$",
        description="Freshness enforcement: strict (reject stale) or advisory (warn)",
    )
    allowed_adapters: list[AdapterPolicy] = Field(
        default_factory=_default_allowed_adapters,
        description="Whitelisted deployment adapters",
    )
    witness_cosignature_count: int = Field(
        default=1,
        ge=0,
        description="Minimum number of witness cosignatures on checkpoints",
    )
    require_warn_acknowledgement: bool = Field(
        default=False,
        description="Whether WARN findings require explicit signed acknowledgement digest",
    )


# ---------------------------------------------------------------------------
# Trust Snapshot
# ---------------------------------------------------------------------------


class RevokedKey(BaseModel):
    """A revoked key entry in a snapshot."""

    key_id: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 of the revoked key's raw public bytes",
    )
    revoked_at_index: int = Field(
        ...,
        ge=0,
        description="Ledger index at which the revocation was recorded",
    )


class HeldRelease(BaseModel):
    """A held release entry in a snapshot.

    Held releases are paused by the trust authority and MUST NOT be
    deployed until the hold is lifted in a subsequent snapshot.
    """

    release_id: str = Field(
        ...,
        min_length=1,
        description="Release identifier of the held release",
    )
    sequence: int = Field(
        ...,
        ge=1,
        description="Sequence number of the held release",
    )


class CheckpointRef(BaseModel):
    """Reference to a ledger checkpoint.

    Contains enough information for a receiver to verify its local
    checkpoint against the authoritative one in the snapshot.
    """

    size: int = Field(
        ...,
        ge=0,
        description="Number of entries in the Merkle log at this checkpoint",
    )
    root_hash: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 Merkle root hash of the log at this size",
    )


class TrustSnapshot(BaseModel):
    """Signed trust snapshot with epoch.

    Schema ``segel.snapshot/v1`` — a point-in-time view of revoked keys
    and held releases, plus the latest checkpoint reference.  ``epoch``
    increases monotonically; receivers reject snapshots with an epoch
    less than or equal to the last accepted one.
    """

    schema_version: str = Field(
        default="segel.snapshot/v1",
        description="Schema identifier for forward compatibility",
    )
    epoch: int = Field(
        ...,
        ge=1,
        description="Monotonically increasing epoch number",
    )
    revoked_keys: list[RevokedKey] = Field(
        default_factory=list,
        description="Keys revoked as of this epoch",
    )
    held_releases: list[HeldRelease] = Field(
        default_factory=list,
        description="Releases that are currently held / paused",
    )
    latest_checkpoint: CheckpointRef | None = Field(
        default=None,
        description="Latest ledger checkpoint known at snapshot time",
    )
