# SPDX-License-Identifier: MIT
"""Release manifest schema (PRD v2.0 §12.0).

The manifest is the canonical description of what a release contains.  It lists
every file (subject) with its path, SHA-256 digest, and size.  The SHA-256 of
the manifest's canonical JSON serialisation becomes the *manifest_sha256* that
appears in every ``ReleaseSubject``.

The manifest also carries optional deployment-scope information:

* ``canary_targets`` — unit IDs that should receive the release first (canary).
* ``general_scope`` — unit IDs in the general rollout.

Both are informational and non-authoritative; the binding in the Approve stamp
is what the verifier checks.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SubjectDigest(BaseModel):
    """A single file within the release bundle.

    Each subject records the relative *path* inside the package, the
    expected SHA-256 hex digest, and the file size in bytes.
    """

    path: str = Field(
        ...,
        min_length=1,
        description="Relative path of the file inside the release package",
    )
    sha256: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 hex digest of the file contents",
    )
    size: int = Field(
        ...,
        ge=0,
        description="File size in bytes",
    )


class Manifest(BaseModel):
    """The signed description of a release.

    Schema ``segel.manifest/v1`` — enveloped in a DSSE wrapper with the
    ``payloadType`` set to ``application/vnd.segel.manifest+json``.
    """

    schema_version: str = Field(
        default="segel.manifest/v1",
        description="Schema identifier for forward compatibility",
    )
    release_id: str = Field(
        ...,
        min_length=1,
        description="Release identifier matching the binding block",
    )
    sequence: int = Field(
        ...,
        ge=1,
        description="Monotonically increasing sequence number",
    )
    payload_type: str = Field(
        default="baseline/v1",
        description="Type of release payload",
    )
    purpose: str = Field(
        ...,
        max_length=300,
        description="Plain-text purpose / description of the release",
    )
    subjects: list[SubjectDigest] = Field(
        ...,
        min_length=1,
        description="At least one file subject must be declared",
    )
    canary_targets: list[str] = Field(
        default_factory=list,
        description="Unit IDs designated as canary recipients",
    )
    general_scope: list[str] = Field(
        default_factory=list,
        description="Unit IDs in the general rollout scope",
    )
    created_at: str = Field(
        default="",
        description="Informational ISO-8601 timestamp (not used for security decisions)",
    )
