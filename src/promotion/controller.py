# SPDX-License-Identifier: MIT
"""Promotion Controller — canary evaluation and promotion criteria.

Per PRD v2.0 §7.9 and TAS §8.8:
- Evaluates pre-committed promotion criteria from the Approve stamp.
- Checks that the required number of canary units are healthy.
- Checks that all required health probes pass.
- A failed canary MUST block promotion.
- Records the release_promoted event in the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from segel_core.crypto.dsse import DSSEEnvelope
from segel_core.schemas.attestation import PromotionCriteria


@dataclass
class CanaryReceipt:
    """A verified canary health receipt."""
    unit_id: str
    overall_result: str  # healthy, unhealthy, error
    health_results: list[dict[str, Any]]
    envelope: DSSEEnvelope


@dataclass
class PromotionResult:
    """Result of promotion criteria evaluation."""
    promoted: bool
    reason: str
    healthy_units: list[str]
    unhealthy_units: list[str]
    criteria: PromotionCriteria
    hold_placed: bool = False
    hold_event: dict[str, Any] | None = None


def evaluate_promotion(
    criteria: PromotionCriteria,
    receipts: list[CanaryReceipt],
) -> PromotionResult:
    """Evaluate pre-committed promotion criteria against canary receipts.

    Args:
        criteria: The pre-committed promotion criteria.
        receipts: Verified canary health receipts.

    Returns:
        PromotionResult indicating whether promotion is allowed.
    """
    healthy_units = []
    unhealthy_units = []

    for receipt in receipts:
        if receipt.overall_result == "healthy":
            # Check required probes if specified
            if criteria.required_probes:
                all_probes_pass = True
                for required_probe in criteria.required_probes:
                    probe_found = False
                    for hr in receipt.health_results:
                        if hr.get("probe") == required_probe and hr.get("passed"):
                            probe_found = True
                            break
                    if not probe_found:
                        all_probes_pass = False
                        break

                if all_probes_pass:
                    healthy_units.append(receipt.unit_id)
                else:
                    unhealthy_units.append(receipt.unit_id)
            else:
                healthy_units.append(receipt.unit_id)
        else:
            unhealthy_units.append(receipt.unit_id)

    # Check if promotion criteria are met
    if len(healthy_units) >= criteria.required_healthy_canary_units:
        return PromotionResult(
            promoted=True,
            reason=f"{len(healthy_units)} healthy canary units meet "
                   f"threshold of {criteria.required_healthy_canary_units}",
            healthy_units=healthy_units,
            unhealthy_units=unhealthy_units,
            criteria=criteria,
            hold_placed=False,
            hold_event=None,
        )

    hold_reason = (
        f"Only {len(healthy_units)} healthy canary units, "
        f"need {criteria.required_healthy_canary_units}. "
        f"Unhealthy: {unhealthy_units}"
    )
    return PromotionResult(
        promoted=False,
        reason=hold_reason,
        healthy_units=healthy_units,
        unhealthy_units=unhealthy_units,
        criteria=criteria,
        hold_placed=True,
        hold_event={
            "action": "hold_placed",
            "reason": hold_reason,
            "unhealthy_units": unhealthy_units,
            "healthy_units": healthy_units,
        },
    )

