# SPDX-License-Identifier: MIT
"""Single derivation module for SEGEL release purpose inspection.

Maps classified purpose (L1..L6) and detected capabilities to InspectFinding objects.
Used by both production release inspection and evaluation scripts.
Per docs/ai_decisions.md (D5, D6, D15, D17):
- Findings come strictly from EXPECTATION_MAP and purpose_class; reasons never influence decisions.
- AI-derived findings have source="ai", severity="warn", and cite instance IDs (<kind>#<n>).
- Vague-L6 rule: every capability instance in diff gets 'purpose too vague to verify (AI class L6)'.
- If purpose_class is None: returns [] (abstains).
"""

from __future__ import annotations

from typing import Any

from inspector.policy.expectations import EXPECTATION_MAP
from segel_core.schemas.attestation import InspectFinding

__all__ = [
    "EXPECTATION_MAP",
    "derive_ai_findings",
    "derive_findings",
]


def _extract_item_ids(c: Any) -> tuple[str, str]:
    """Extract (kind, instance_id) from a capability representation."""
    if isinstance(c, dict):
        kind = str(c.get("capability_id", ""))
        iid = str(c.get("instance_id") or c.get("capability_id") or "")
        return kind, iid
    kind = str(c)
    return kind, kind


def derive_ai_findings(
    purpose_class: str | None,
    capabilities: list[dict[str, Any]] | list[str] | set[str],
) -> list[InspectFinding]:
    """Derive AI advisory inspection findings.

    Args:
        purpose_class: Predicted purpose class ('L1'..'L6') or None (abstain).
        capabilities: Detected capabilities (list of dicts, list of strings, or set of strings).

    Returns:
        List of InspectFinding with source="ai" and severity="warn".
    """
    if purpose_class is None:
        return []

    cap_list = list(capabilities)
    if not cap_list:
        return []

    # Class L6: vague or other -> cite every capability instance
    if purpose_class == "L6":
        findings: list[InspectFinding] = []
        for c in cap_list:
            _, iid = _extract_item_ids(c)
            findings.append(
                InspectFinding(
                    capability_id=iid,
                    severity="warn",
                    source="ai",
                    description="purpose too vague to verify (AI class L6)",
                )
            )
        return findings

    # Classes L1..L5
    allowed = EXPECTATION_MAP.get(purpose_class, set())
    findings = []
    for c in cap_list:
        kind, iid = _extract_item_ids(c)
        if kind not in allowed:
            findings.append(
                InspectFinding(
                    capability_id=iid,
                    severity="warn",
                    source="ai",
                    description=(
                        f"Unexpected capability '{iid}' outside expectation map for "
                        f"purpose class '{purpose_class}'"
                    ),
                )
            )

    return findings


def derive_findings(
    purpose_class: str | None,
    capabilities: list[dict[str, Any]] | list[str] | set[str],
) -> list[InspectFinding]:
    """Derive deterministic inspection findings (for B1/B1b baseline and deterministic layer).

    Deterministic version producing source='deterministic'.
    """
    if purpose_class is None:
        return []

    cap_list = list(capabilities)
    if not cap_list:
        return []

    if purpose_class == "L6":
        return [
            InspectFinding(
                capability_id="L6",
                severity="warn",
                source="deterministic",
                description="purpose too vague to verify",
            )
        ]

    allowed = EXPECTATION_MAP.get(purpose_class, set())
    kinds: set[str] = set()
    for c in cap_list:
        kind, _ = _extract_item_ids(c)
        kinds.add(kind)

    unexpected = sorted(kinds - allowed)
    return [
        InspectFinding(
            capability_id=uid,
            severity="warn",
            source="deterministic",
            description=(
                f"Unexpected capability '{uid}' outside expectation map for "
                f"purpose class '{purpose_class}'"
            ),
        )
        for uid in unexpected
    ]
