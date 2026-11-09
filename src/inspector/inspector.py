# SPDX-License-Identifier: MIT
"""Inspector — deterministic capability extraction and policy evaluation.

Per PRD v2.0 §7.5 and TAS §8.4:
- Deterministic capability extraction from configuration files.
- Versioned policy engine producing PASS/WARN/REJECT findings.
- Optional AI advisory analysis via Ollama (isolated sandbox).
- AI MUST NOT downgrade a deterministic REJECT.
- AI failures are recorded explicitly (ai_status="failed").
- Inspector Signer signs the attestation (separate key).

Supported payload type: baseline/v1 (YAML configuration).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from inspector.baseline import (
    BaselineV1,
    diff_capabilities,
    extract_capabilities_structured,
    parse_baseline_v1,
)
from segel_core.canonical import canonical_json
from segel_core.crypto.dsse import DSSEEnvelope, create_envelope
from segel_core.crypto.ed25519 import KeyPair, generate_evidence_id
from segel_core.schemas.attestation import (
    INSPECT_PREDICATE_TYPE,
    InspectFinding,
    InspectPredicate,
    InTotoStatement,
    InTotoSubject,
)
from segel_core.schemas.binding import BindingBlock, ReleaseSubject
from segel_core.schemas.manifest import Manifest

__all__ = [
    "BaselineV1",
    "CAPABILITY_RULES",
    "InspectionResult",
    "POLICY_RULES_V1",
    "create_inspect_attestation",
    "diff_capabilities",
    "evaluate_policy",
    "extract_capabilities",
    "extract_capabilities_structured",
    "inspect_release",
    "parse_baseline_v1",
    "sign_inspect",
]

# ── Deterministic capability extraction ──────────────────────────────

# Known capabilities extracted from baseline configuration
CAPABILITY_RULES = {
    "network_listen": {
        "patterns": [
            r"(?i)listen\s*[:=]",
            r"(?i)bind_address\s*[:=]",
            r"(?i)port\s*[:=]",
            r"(?i)server\s*[:=]",
        ],
        "description": "Configuration opens a network listener",
    },
    "file_write": {
        "patterns": [
            r"(?i)log_file\s*[:=]",
            r"(?i)output_path\s*[:=]",
            r"(?i)write_dir\s*[:=]",
            r"(?i)data_dir\s*[:=]",
        ],
        "description": "Configuration writes to filesystem",
    },
    "external_connect": {
        "patterns": [
            r"(?i)upstream\s*[:=]",
            r"(?i)remote_host\s*[:=]",
            r"(?i)proxy\s*[:=]",
            r"(?i)api_url\s*[:=]",
        ],
        "description": "Configuration connects to external systems",
    },
    "credential_reference": {
        "patterns": [
            r"(?i)(password|secret|token|api_key)\s*[:=]",
            r"(?i)auth\s*[:=]",
        ],
        "description": "Configuration references credentials",
    },
    "privilege_escalation": {
        "patterns": [
            r"(?i)run_as_root\s*[:=]\s*(true|yes)",
            r"(?i)privileged\s*[:=]\s*(true|yes)",
            r"(?i)sudo\s*[:=]",
        ],
        "description": "Configuration requests elevated privileges",
    },
}

# ── Policy rules ─────────────────────────────────────────────────────

POLICY_RULES_V1 = {
    "PRULE-001": {
        "capability": "privilege_escalation",
        "severity": "reject",
        "description": "Privilege escalation is not allowed in configuration releases",
    },
    "PRULE-002": {
        "capability": "credential_reference",
        "severity": "warn",
        "description": "Configuration references credentials — review required",
    },
    "PRULE-003": {
        "capability": "external_connect",
        "severity": "warn",
        "description": "Configuration connects to external systems — verify endpoint",
    },
}


@dataclass
class InspectionResult:
    """Result of an inspection."""
    verdict: str  # PASS, WARN, REJECT
    deterministic_findings: list[InspectFinding]
    ai_findings: list[InspectFinding]
    ai_status: str  # ok, failed, skipped
    ai_model_id: str
    capabilities: list[dict[str, Any]]
    policy_version: int


def extract_capabilities(
    files: dict[str, bytes],
) -> list[dict[str, Any]]:
    """Extract capabilities from configuration files.

    Performs structured Baseline v1 extraction when files parse as Baseline v1 JSON;
    falls back to deterministic pattern matching (regex) for non-JSON or legacy files.

    Args:
        files: Dict of relative_path -> file_contents.

    Returns:
        List of detected capabilities with locations and instance IDs.
    """
    detected: list[dict[str, Any]] = []
    kind_counts: dict[str, int] = defaultdict(int)

    for path, content in sorted(files.items()):
        # Try structured Baseline v1 extraction first
        is_baseline = False
        try:
            parse_baseline_v1(content)
            is_baseline = True
        except Exception:
            is_baseline = False

        if is_baseline:
            structured_caps = extract_capabilities_structured({path: content})
            for sc in structured_caps:
                cid = sc["capability_id"]
                kind_counts[cid] += 1
                sc["instance_id"] = f"{cid}#{kind_counts[cid]}"
                detected.append(sc)
            continue

        # Fallback to regex pattern matching
        try:
            text = content.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            continue

        for cap_id, cap_def in CAPABILITY_RULES.items():
            for pattern in cap_def["patterns"]:
                matches = list(re.finditer(pattern, text))
                if matches:
                    for m in matches:
                        line_num = text[:m.start()].count("\n") + 1
                        kind_counts[cap_id] += 1
                        detected.append({
                            "capability_id": cap_id,
                            "instance_id": f"{cap_id}#{kind_counts[cap_id]}",
                            "file": path,
                            "line": line_num,
                            "match": m.group(0).strip(),
                            "description": cap_def["description"],
                            "destination": None,
                            "port": None,
                            "proto": None,
                            "account": None,
                            "setting": None,
                            "value": None,
                        })

    return detected


def evaluate_policy(
    capabilities: list[dict[str, Any]],
    policy_version: int = 1,
) -> tuple[str, list[InspectFinding]]:
    """Evaluate policy rules against detected capabilities.

    Args:
        capabilities: Output from extract_capabilities.
        policy_version: The policy version to apply.

    Returns:
        Tuple of (verdict, findings).
    """
    findings: list[InspectFinding] = []
    cap_ids = {c["capability_id"] for c in capabilities}

    for rule_id, rule in POLICY_RULES_V1.items():
        if rule["capability"] in cap_ids:
            findings.append(InspectFinding(
                capability_id=rule_id,
                severity=rule["severity"],
                source="deterministic",
                description=rule["description"],
            ))
        else:
            findings.append(InspectFinding(
                capability_id=rule_id,
                severity="pass",
                source="deterministic",
                description=f"No {rule['capability']} detected",
            ))

    # Compute verdict
    if any(f.severity == "reject" for f in findings):
        verdict = "REJECT"
    elif any(f.severity == "warn" for f in findings):
        verdict = "WARN"
    else:
        verdict = "PASS"

    return verdict, findings


def inspect_release(
    files: dict[str, bytes],
    manifest: Manifest,
    manifest_digest: str,
    trust_root_version: int = 1,
    policy_version: int = 1,
    ai_enabled: bool = False,
) -> InspectionResult:
    """Perform a full inspection of a release.

    Args:
        files: Dict of relative_path -> file_contents.
        manifest: The release manifest.
        manifest_digest: SHA-256 hex of the manifest bytes.
        trust_root_version: Current trust root version.
        policy_version: Current policy version.
        ai_enabled: Whether to attempt AI advisory analysis.

    Returns:
        InspectionResult with verdict and findings.
    """
    # Step 1: Extract capabilities
    capabilities = extract_capabilities(files)

    # Step 2: Evaluate policy
    verdict, det_findings = evaluate_policy(capabilities, policy_version)

    # Step 3: AI advisory (optional, isolated)
    ai_findings: list[InspectFinding] = []
    ai_status = "skipped"
    ai_model_id = ""

    if ai_enabled:
        try:
            ai_findings, ai_model_id = _run_ai_advisory(files, capabilities)
            ai_status = "ok"

            # SEC-013: AI MUST NOT downgrade a deterministic REJECT
            if verdict == "REJECT":
                # Filter out any AI findings that would lower severity
                for af in ai_findings:
                    if af.severity != "reject":
                        af.severity = "reject"  # Force to match deterministic
            else:
                # AI can escalate (warn→reject) but not downgrade
                for af in ai_findings:
                    if af.severity == "reject" and verdict != "REJECT":
                        verdict = "REJECT"
                    elif af.severity == "warn" and verdict == "PASS":
                        verdict = "WARN"
        except Exception as e:
            ai_status = "failed"
            ai_findings.append(InspectFinding(
                capability_id="AI_FAILURE",
                severity="pass",  # AI failure does not block
                source="ai",
                description=f"AI analysis failed: {e}",
            ))

    return InspectionResult(
        verdict=verdict,
        deterministic_findings=det_findings,
        ai_findings=ai_findings,
        ai_status=ai_status,
        ai_model_id=ai_model_id,
        capabilities=capabilities,
        policy_version=policy_version,
    )


def create_inspect_attestation(
    result: InspectionResult,
    manifest: Manifest,
    manifest_digest: str,
    trust_root_version: int = 1,
    policy_version: int = 1,
) -> dict[str, Any]:
    """Create the in-toto Statement for the Inspect attestation.

    Args:
        result: The inspection result.
        manifest: The release manifest.
        manifest_digest: SHA-256 hex of manifest bytes.
        trust_root_version: Current trust root version.
        policy_version: Current policy version.

    Returns:
        Dict of the in-toto statement (ready for DSSE signing).
    """
    binding = BindingBlock(
        stamp="inspect",
        subject=ReleaseSubject(
            release_id=manifest.release_id,
            sequence=manifest.sequence,
            manifest_sha256=manifest_digest,
        ),
        trust_root_version=trust_root_version,
        policy_version=policy_version,
        evidence_id=generate_evidence_id(),
    )

    predicate = InspectPredicate(
        binding=binding,
        policy_version=result.policy_version,
        verdict=result.verdict,
        deterministic_findings=result.deterministic_findings,
        ai_findings=result.ai_findings,
        ai_status=result.ai_status,
        ai_model_id=result.ai_model_id,
        capabilities=result.capabilities,
    )

    in_toto_subject = InTotoSubject(
        name=f"release/{manifest.release_id}@{manifest.sequence}",
        digest={"sha256": manifest_digest},
    )

    statement = InTotoStatement(
        subject=[in_toto_subject],
        predicateType=INSPECT_PREDICATE_TYPE,
        predicate=predicate.model_dump(mode="json"),
    )

    return statement.model_dump(by_alias=True, mode="json")


def sign_inspect(
    statement_dict: dict[str, Any],
    inspector_key: KeyPair,
) -> DSSEEnvelope:
    """Sign the Inspect attestation with the Inspector Signer's key.

    Args:
        statement_dict: The in-toto statement dict.
        inspector_key: The Inspector Signer's key pair.

    Returns:
        A DSSE envelope wrapping the signed Inspect attestation.
    """
    payload = canonical_json(statement_dict)
    return create_envelope(
        payload_type="application/vnd.segel.inspect+json",
        payload=payload,
        signers=[(inspector_key.key_id, inspector_key.private_key)],
    )


def _run_ai_advisory(
    files: dict[str, bytes],
    capabilities: list[dict[str, Any]],
) -> tuple[list[InspectFinding], str]:
    """Run AI advisory analysis (Ollama).

    This is an optional, isolated analysis. The AI has no signing keys
    and cannot modify verdicts — it can only ADD findings.

    Returns:
        Tuple of (findings, model_id).
    """
    # MVP: AI advisory is optional and may be unavailable
    # When Ollama is available, this sends the capability summary
    # for additional analysis. For now, return empty.
    raise NotImplementedError("AI advisory requires Ollama — skipped for MVP")

