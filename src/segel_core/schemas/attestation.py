# SPDX-License-Identifier: MIT
"""in-toto Statement v1 attestations for each pipeline stamp (PRD v2.0 §12.0).

SEGEL uses the `in-toto Statement v1`_ envelope to carry attestations.  Each
stamp in the pipeline (origin → inspect → approve → test) has its own
predicate type and schema:

* **OriginPredicate** — SLSA-aligned build provenance.
* **InspectPredicate** — Deterministic + AI inspection findings.
* **ApprovePredicate** — Multi-party approval with promotion criteria.
* **TestPredicate** — Canary / general deployment receipt with health probes.

These predicates are serialised as the ``predicate`` field inside an
``InTotoStatement`` and then wrapped in a DSSE envelope for signing.

.. _in-toto Statement v1: https://in-toto.io/Statement/v1
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from segel_core.schemas.binding import BindingBlock

# ---------------------------------------------------------------------------
# in-toto v1 statement
# ---------------------------------------------------------------------------

INTOTO_STATEMENT_TYPE: str = "https://in-toto.io/Statement/v1"
"""Canonical ``_type`` value for in-toto Statement v1."""


class InTotoSubject(BaseModel):
    """in-toto subject: a named artifact with a digest map.

    Example::

        InTotoSubject(
            name="release/BASELINE-42",
            digest={"sha256": "abcdef0123456789..."},
        )
    """

    name: str = Field(..., min_length=1, description="Artifact name / identifier")
    digest: dict[str, str] = Field(
        ...,
        description="Digest map, e.g. {'sha256': '<hex>'}",
    )


class InTotoStatement(BaseModel):
    """in-toto Statement v1 — the outer wrapper for all attestation predicates.

    The ``_type`` field uses a Pydantic alias because it starts with an
    underscore, which Pydantic treats specially.  When serialising use
    ``model_dump(by_alias=True)`` to emit ``"_type"``.
    """

    type_: str = Field(
        default=INTOTO_STATEMENT_TYPE,
        alias="_type",
        description="in-toto statement type URI",
    )
    subject: list[InTotoSubject] = Field(
        ...,
        min_length=1,
        description="List of in-toto subjects",
    )
    predicateType: str = Field(  # noqa: N815 — matches in-toto spec casing
        ...,
        description="URI identifying the predicate schema",
    )
    predicate: dict[str, Any] = Field(
        ...,
        description="The predicate payload (stamp-specific)",
    )

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Predicate type URIs
# ---------------------------------------------------------------------------

ORIGIN_PREDICATE_TYPE: str = "https://segel.dev/attestation/origin/v1"
"""Predicate type for the Origin (build provenance) stamp."""

INSPECT_PREDICATE_TYPE: str = "https://segel.dev/attestation/inspect/v1"
"""Predicate type for the Inspect (analysis) stamp."""

APPROVE_PREDICATE_TYPE: str = "https://segel.dev/attestation/approve/v1"
"""Predicate type for the Approve (multi-party authorisation) stamp."""

TEST_PREDICATE_TYPE: str = "https://segel.dev/attestation/test/v1"
"""Predicate type for the Test (deployment receipt) stamp."""


# ---------------------------------------------------------------------------
# Origin stamp
# ---------------------------------------------------------------------------


class OriginPredicate(BaseModel):
    """SLSA-aligned build provenance for the Origin stamp.

    Records *who* built the release, *from what* sources, and *what*
    the output digest is.  ``builder_id`` and ``builder_domain`` identify
    the build system; ``source_ref`` / ``source_digest`` pin the input.
    """

    binding: BindingBlock = Field(
        ...,
        description="Binding block linking this evidence to a release",
    )
    builder_id: str = Field(
        ...,
        min_length=1,
        description="Builder identity string, e.g. 'ci.internal/builder-v3'",
    )
    builder_domain: str = Field(
        ...,
        min_length=1,
        description="Domain of the build system",
    )
    source_ref: str = Field(
        default="",
        description="VCS reference (branch, tag, commit) of the source input",
    )
    source_digest: str = Field(
        default="",
        pattern=r"^([0-9a-f]{64})?$",
        description="SHA-256 digest of the source tree, if available",
    )
    dependencies: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of dependency references (name → digest)",
    )
    build_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Reproducibility-relevant build parameters",
    )
    output_digest: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 digest of the build output",
    )
    packaging_recipe_digest: str = Field(
        default="",
        description="Digest of the packaging recipe, if applicable",
    )


# ---------------------------------------------------------------------------
# Inspect stamp
# ---------------------------------------------------------------------------


class InspectFinding(BaseModel):
    """A single inspection finding (deterministic or AI-generated).

    Findings carry a *severity* of ``pass``, ``warn``, or ``reject`` and
    indicate whether they came from a deterministic rule engine or an AI
    model.
    """

    capability_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the capability / rule that produced this finding",
    )
    severity: str = Field(
        ...,
        pattern=r"^(pass|warn|reject)$",
        description="Finding severity: pass, warn, or reject",
    )
    source: str = Field(
        ...,
        pattern=r"^(deterministic|ai)$",
        description="Whether the finding is deterministic or AI-generated",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Human-readable description of the finding",
    )


class InspectPredicate(BaseModel):
    """Inspection result with deterministic and AI findings.

    The ``verdict`` is the roll-up: ``PASS`` if all findings pass, ``WARN``
    if any findings warn but none reject, ``REJECT`` if any finding rejects.
    """

    binding: BindingBlock = Field(
        ...,
        description="Binding block linking this evidence to a release",
    )
    policy_version: int = Field(
        ...,
        ge=1,
        description="Inspection policy version used for this analysis",
    )
    verdict: str = Field(
        ...,
        pattern=r"^(PASS|WARN|REJECT)$",
        description="Aggregate verdict: PASS, WARN, or REJECT",
    )
    deterministic_findings: list[InspectFinding] = Field(
        default_factory=list,
        description="Findings from deterministic rule checks",
    )
    ai_findings: list[InspectFinding] = Field(
        default_factory=list,
        description="Findings from AI-based analysis",
    )
    ai_status: str = Field(
        default="skipped",
        pattern=r"^(ok|failed|skipped)$",
        description="Status of AI analysis: ok, failed, or skipped",
    )
    ai_error_code: str = Field(
        default="",
        description="Error code if AI analysis failed",
    )
    ai_model_id: str = Field(
        default="",
        description="Identifier of the AI model used, if any",
    )
    ai_model_digest: str = Field(
        default="",
        description="Digest of the AI model from Ollama tags",
    )
    ai_prompt_digest: str = Field(
        default="",
        description="SHA-256 digest of the AI prompt template used",
    )
    ai_class: str = Field(
        default="",
        description="Predicted purpose class (L1..L6)",
    )
    ai_reason: str = Field(
        default="",
        description="Short advisory explanation from the AI model",
    )
    capabilities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Capabilities detected in the release payload",
    )


# ---------------------------------------------------------------------------
# Approve stamp
# ---------------------------------------------------------------------------


class PromotionCriteria(BaseModel):
    """Pre-committed canary promotion criteria.

    Defines the conditions that must be met before a canary release is
    promoted to general availability.
    """

    required_healthy_canary_units: int = Field(
        default=2,
        ge=1,
        description="Minimum number of healthy canary units required",
    )
    required_probes: list[str] = Field(
        default_factory=list,
        description="Health probe names that must all pass",
    )
    observation_window_cycles: int = Field(
        default=1,
        ge=1,
        description="Number of observation cycles before promotion",
    )


class ApprovePredicate(BaseModel):
    """Approval payload binding origin and inspect evidence together.

    The approve stamp is a multi-party authorisation gate.  It references the
    digests of the origin and inspect envelopes and, optionally, an
    acknowledgement digest for any WARN findings that were explicitly accepted.
    """

    binding: BindingBlock = Field(
        ...,
        description="Binding block linking this evidence to a release",
    )
    scope: str = Field(
        default="candidate_authorisation",
        description="Approval scope identifier",
    )
    origin_evidence_digest: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 digest of the DSSE-wrapped Origin attestation",
    )
    inspect_evidence_digest: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 digest of the DSSE-wrapped Inspect attestation",
    )
    acknowledgement_digest: str = Field(
        default="",
        description="Digest of acknowledged WARN findings (empty if none)",
    )
    promotion_criteria: PromotionCriteria = Field(
        default_factory=PromotionCriteria,
        description="Pre-committed criteria for canary → general promotion",
    )
    canary_targets: list[str] = Field(
        default_factory=list,
        description="Unit IDs designated for canary deployment",
    )


# ---------------------------------------------------------------------------
# Test stamp
# ---------------------------------------------------------------------------


class HealthResult(BaseModel):
    """A single health check result from a deployment probe.

    Supported probes: ``file_exists``, ``config_valid``, ``service_active``,
    ``tcp_connect_local``, ``http_get_local``.
    """

    probe: str = Field(
        ...,
        pattern=r"^(file_exists|config_valid|service_active|tcp_connect_local|http_get_local)$",
        description="Health probe type",
    )
    target: str = Field(
        default="",
        description="Probe target (file path, service name, port, URL)",
    )
    expected: str = Field(
        default="",
        description="Expected value or state",
    )
    actual: str = Field(
        default="",
        description="Actual observed value or state",
    )
    passed: bool = Field(
        default=True,
        description="Whether the probe passed",
    )
    evidence_digest: str = Field(
        default="",
        description="SHA-256 digest of probe evidence, if captured",
    )


class TestPredicate(BaseModel):
    """Test stamp: canary or general deployment receipt with health probes.

    Records the outcome of deploying a release to a specific unit, including
    pre/post state digests, adapter identity, and individual health results.
    """

    binding: BindingBlock = Field(
        ...,
        description="Binding block linking this evidence to a release",
    )
    unit_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of the deployment target unit",
    )
    unit_role: str = Field(
        default="canary",
        pattern=r"^(canary|general)$",
        description="Role of the unit: canary or general",
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
    health_results: list[HealthResult] = Field(
        default_factory=list,
        description="Individual health probe results",
    )
    overall_result: str = Field(
        ...,
        pattern=r"^(healthy|unhealthy|error)$",
        description="Aggregate health result: healthy, unhealthy, or error",
    )
    receiver_state_versions: dict[str, int] = Field(
        default_factory=dict,
        description="Monotonic state version counters from the receiver",
    )
