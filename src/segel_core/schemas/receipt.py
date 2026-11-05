# SPDX-License-Identifier: MIT
"""Deployment receipt schema (PRD v2.0 §12.0).

After a Receiver applies a release to a unit, it produces a signed
``DeploymentReceipt`` that records the outcome.  This receipt is
distinct from the ``TestPredicate`` (which is the in-toto attestation
predicate used in the test stamp); the receipt is the Receiver's own
signed statement about what happened.

The receipt captures:

* The binding block tying it to the release.
* The unit identity and role (canary or general).
* The deployment result: committed, rolled_back, or failed.
* Pre- and post-state digests for auditing.
* Individual health probe results.
* Monotonic state version counters for replay detection.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from segel_core.schemas.binding import BindingBlock


class DeploymentReceipt(BaseModel):
    """Signed deployment receipt from a Receiver.

    Schema ``segel.receipt/v1`` — enveloped in DSSE and signed with the
    Receiver's key.  The receipt is sent back to the promotion engine
    so it can evaluate canary health.
    """

    schema_version: str = Field(
        default="segel.receipt/v1",
        description="Schema identifier for forward compatibility",
    )
    binding: BindingBlock = Field(
        ...,
        description="Binding block linking this receipt to a release",
    )
    unit_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the deployment target unit",
    )
    unit_role: str = Field(
        ...,
        pattern=r"^(canary|general)$",
        description="Role of the unit: canary or general",
    )
    result: str = Field(
        ...,
        pattern=r"^(committed|rolled_back|failed)$",
        description="Deployment outcome: committed, rolled_back, or failed",
    )
    pre_state_digest: str = Field(
        default="",
        description="SHA-256 digest of the unit state before deployment",
    )
    post_state_digest: str = Field(
        default="",
        description="SHA-256 digest of the unit state after deployment",
    )
    adapter_identity: str = Field(
        default="",
        description="Identity string of the deployment adapter used",
    )
    health_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Individual health probe results (untyped for flexibility)",
    )
    receiver_state_versions: dict[str, int] = Field(
        default_factory=dict,
        description="Monotonic state version counters for replay detection",
    )
    informational_timestamp: str = Field(
        default="",
        description="Informational ISO-8601 timestamp (not trusted for security)",
    )
