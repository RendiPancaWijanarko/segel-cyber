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

import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from inspector.ai.client import run_ai_worker
from inspector.baseline import (
    BaselineV1,
    diff_capabilities,
    extract_capabilities_structured,
    parse_baseline_v1,
)
from inspector.policy.expectations import classify_purpose_b1, derive_findings
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
    "_merge_findings_and_verdict",
]

# ── Deterministic capability extraction ──────────────────────────────

# Known capabilities extracted from baseline configuration
# Patterns require identifier boundaries (no letter or digit immediately before keyword).
# Note: A missed key is worse than a false positive in this fail-closed component.
# Negative lookbehind (?<![a-zA-Z0-9]) allows _, -, . to precede keywords
# (e.g. app_port, ssh-port, http.port).
CAPABILITY_RULES = {
    "network_listen": {
        "patterns": [
            r"(?i)(?<![a-zA-Z0-9])listen\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])bind_address\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])port\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])server\s*[:=]",
        ],
        "description": "Configuration opens a network listener",
    },
    "file_write": {
        "patterns": [
            r"(?i)(?<![a-zA-Z0-9])log_file\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])output_path\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])write_dir\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])data_dir\s*[:=]",
        ],
        "description": "Configuration writes to filesystem",
    },
    "external_connect": {
        "patterns": [
            r"(?i)(?<![a-zA-Z0-9])upstream\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])remote_host\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])proxy\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])api_url\s*[:=]",
        ],
        "description": "Configuration connects to external systems",
    },
    "credential_reference": {
        "patterns": [
            r"(?i)(?<![a-zA-Z0-9])(password|secret|token|api_key)\s*[:=]",
            r"(?i)(?<![a-zA-Z0-9])auth\s*[:=]",
        ],
        "description": "Configuration references credentials",
    },
    "privilege_escalation": {
        "patterns": [
            r"(?i)(?<![a-zA-Z0-9])run_as_root\s*[:=]\s*(true|yes)",
            r"(?i)(?<![a-zA-Z0-9])privileged\s*[:=]\s*(true|yes)",
            r"(?i)(?<![a-zA-Z0-9])sudo\s*[:=]",
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
    "PRULE-004": {
        "capability": "privilege_granted",
        "severity": "reject",
        "description": (
            "Elevated privileges granted to account — not allowed in configuration releases"
        ),
    },
}


@dataclass
class InspectionResult:
    """Result of an inspection."""

    verdict: str  # PASS, WARN, REJECT
    deterministic_findings: list[InspectFinding]
    ai_findings: list[InspectFinding]
    ai_status: str  # ok, failed, skipped
    capabilities: list[dict[str, Any]]
    policy_version: int = 1
    ai_error_code: str = ""
    ai_model_id: str = ""
    ai_model_digest: str = ""
    ai_prompt_digest: str = ""
    ai_class: str = ""
    ai_reason: str = ""


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


def _merge_findings_and_verdict(
    deterministic_verdict: str,
    ai_findings: list[InspectFinding],
) -> tuple[str, list[InspectFinding]]:
    """Merge deterministic verdict with AI advisory findings.

    Rules per PRD v2.0 §7.5 and docs/ai_decisions.md (D4, D5, D7):
    - AI findings are advisory: their severity is strictly capped at 'warn'.
    - AI findings are preserved with their original severity (capped at warn),
      NEVER overwritten to match the deterministic verdict (fixes Defect 1).
    - AI can only raise verdict from PASS to WARN (fixes Defect 2).
    - AI can NEVER produce REJECT, escalate to REJECT, or downgrade any verdict.
    """
    capped_ai_findings: list[InspectFinding] = []
    has_ai_warn = False

    for af in ai_findings:
        sev = af.severity
        # Strictly cap AI severity at warn
        if sev == "reject":
            sev = "warn"
        if sev == "warn":
            has_ai_warn = True

        # Copy or update finding with capped severity, preserving other attributes
        if sev != af.severity:
            capped_af = af.model_copy(update={"severity": sev})
        else:
            capped_af = af.model_copy()
        capped_ai_findings.append(capped_af)

    verdict = deterministic_verdict
    if verdict == "PASS" and has_ai_warn:
        verdict = "WARN"

    return verdict, capped_ai_findings


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

    # Step 2b: Deterministic expectation check via B1 classifier (D6)
    purpose = getattr(manifest, "purpose", None)
    b1_class = classify_purpose_b1(purpose)
    if b1_class is not None:
        exp_findings = derive_findings(b1_class, capabilities)
        det_findings.extend(exp_findings)
        if any(f.severity == "reject" for f in exp_findings):
            verdict = "REJECT"
        elif any(f.severity == "warn" for f in exp_findings) and verdict == "PASS":
            verdict = "WARN"

    # Step 3: AI advisory (optional, isolated)
    ai_findings: list[InspectFinding] = []
    ai_status = "skipped"
    ai_error_code = ""
    ai_model_id = ""
    ai_model_digest = ""
    ai_prompt_digest = ""
    ai_class = ""
    ai_reason = ""

    ai_cfg_enabled = os.getenv("SEGEL_AI_ENABLED", "0").lower().strip() in {"1", "true", "yes"}

    if ai_enabled and not ai_cfg_enabled:
        # AI analysis requested but AI subsystem is not enabled in environment config
        ai_status = "failed"
        ai_error_code = "AI_DISABLED"
        ai_findings.append(
            InspectFinding(
                capability_id="AI_FAILURE",
                severity="pass",
                source="ai",
                description="AI analysis failed: AI_DISABLED",
            )
        )
    elif ai_cfg_enabled:
        ai_endpoint = os.getenv("SEGEL_AI_ENDPOINT", "http://127.0.0.1:11434").strip()
        ai_model = os.getenv("SEGEL_AI_MODEL", "qwen3:4b").strip()
        timeout_raw = os.getenv("SEGEL_AI_TIMEOUT_S", "30").strip()
        try:
            ai_timeout_s = float(timeout_raw)
        except ValueError:
            ai_timeout_s = 30.0

        (
            ai_findings,
            ai_status,
            ai_error_code,
            ai_model_id,
            ai_model_digest,
            ai_prompt_digest,
            ai_class,
            ai_reason,
        ) = run_ai_worker(
            purpose=purpose or "",
            capabilities=capabilities,
            endpoint=ai_endpoint,
            model=ai_model,
            timeout_s=ai_timeout_s,
        )

        if ai_status == "failed":
            ai_findings.append(
                InspectFinding(
                    capability_id="AI_FAILURE",
                    severity="pass",
                    source="ai",
                    description=f"AI analysis failed: {ai_error_code}",
                )
            )

        # Merge deterministic verdict and AI advisory findings per D5
        verdict, ai_findings = _merge_findings_and_verdict(verdict, ai_findings)

    return InspectionResult(
        verdict=verdict,
        deterministic_findings=det_findings,
        ai_findings=ai_findings,
        ai_status=ai_status,
        capabilities=capabilities,
        policy_version=policy_version,
        ai_error_code=ai_error_code,
        ai_model_id=ai_model_id,
        ai_model_digest=ai_model_digest,
        ai_prompt_digest=ai_prompt_digest,
        ai_class=ai_class,
        ai_reason=ai_reason,
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
        ai_error_code=result.ai_error_code,
        ai_model_id=result.ai_model_id,
        ai_model_digest=result.ai_model_digest,
        ai_prompt_digest=result.ai_prompt_digest,
        ai_class=result.ai_class,
        ai_reason=result.ai_reason,
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

