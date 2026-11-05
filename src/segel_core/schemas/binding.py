# SPDX-License-Identifier: MIT
"""Binding block carried by every attestation (PRD v2.0 §12.0).

The binding block is the critical structure that ties each piece of evidence
(an attestation) to exactly one release identity and one step in the supply-chain
pipeline.  Every attestation MUST contain a binding block so that the verifier
can:

1. Confirm the evidence belongs to the correct release (subject match).
2. Detect replay or rollback (monotonic sequence).
3. Pin the trust root and policy versions used at creation time.
4. Correlate the attestation with its unique evidence ID.

Fields:
    stamp           -- Pipeline stage: origin | inspect | approve | record | test
    subject         -- The release identity triple (release_id, sequence, manifest_sha256)
    trust_root_version -- Version of the TrustRoot active when the attestation was produced
    policy_version  -- Version of the VerificationPolicy active when produced
    evidence_id     -- Random 128-bit hex identifier, unique per attestation
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReleaseSubject(BaseModel):
    """The release identity tuple.

    Uniquely identifies a single version of a release by combining its
    human-readable *release_id*, an ever-increasing *sequence* number,
    and the SHA-256 digest of the canonical manifest bytes.
    """

    release_id: str = Field(
        ...,
        min_length=1,
        description="Release identifier, e.g. 'BASELINE-UNIT-42'",
    )
    sequence: int = Field(
        ...,
        ge=1,
        description="Monotonically increasing sequence number",
    )
    manifest_sha256: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 hex digest of the canonical manifest bytes",
    )


class BindingBlock(BaseModel):
    """Binding block present in every attestation.

    Links a single piece of evidence to one release identity and records
    the trust context (root + policy versions) under which it was created.
    """

    stamp: str = Field(
        ...,
        pattern=r"^(origin|inspect|approve|record|test)$",
        description="Pipeline stamp that produced this attestation",
    )
    subject: ReleaseSubject = Field(
        ...,
        description="Release identity this attestation is bound to",
    )
    trust_root_version: int = Field(
        ...,
        ge=1,
        description="TrustRoot version active when the attestation was created",
    )
    policy_version: int = Field(
        ...,
        ge=1,
        description="VerificationPolicy version active when the attestation was created",
    )
    evidence_id: str = Field(
        ...,
        pattern=r"^[0-9a-f]{32}$",
        description="Random 128-bit hex identifier unique to this attestation",
    )
