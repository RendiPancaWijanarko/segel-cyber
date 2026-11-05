# SPDX-License-Identifier: MIT
"""Phase C Hardening Gap Tests: C2 — FR-051 / SEC-016 Ledger Self-Verification of Evidence.

Requirement: PRD FR-051 & SEC-016:
- The Transparency Ledger MUST verify candidate and promotion evidence before inclusion.
- The Ledger MUST NOT append entries without verifying DSSE signatures, stamp bindings,
  and policy thresholds.
- Appending invalid candidate evidence or unverified promotion receipts MUST be refused
  with appropriate error codes, maintaining ledger state immutability.

Tests:
1. test_c2_fr051_positive_control_valid_candidate_recorded: Valid candidate evidence
   passes ledger verification and is appended.
2. test_c2_fr051_red_tampered_signature_rejected_by_ledger: Evidence with an invalid
   signature is rejected by ledger self-verification and NOT appended.
3. test_c2_fr051_red_subject_mismatch_rejected_by_ledger: Evidence with binding mismatch
   is rejected by ledger self-verification and NOT appended.
4. test_c2_fr051_red_unverified_promotion_rejected_by_ledger: Promotion record with
   unmet canary thresholds is rejected by ledger self-verification and NOT appended.
"""

from __future__ import annotations

import copy
import pytest

from builder.builder import build_release_package, sign_origin
from ledger.ledger import TransparencyLedger
from segel_core.errors import ErrorCode, SegelError, SignatureError, SubjectMismatchError
from tests.adversarial.test_at_NNN import SyntheticLab, _build_valid_candidate


def _assemble_candidate_payload(lab: SyntheticLab) -> dict:
    files, _, passport, _ = _build_valid_candidate(lab, release_id="REL-GAP-051", sequence=1)
    return {
        "manifest_envelope": passport.manifest_envelope,
        "origin_envelope": passport.origin_envelope,
        "inspect_envelope": passport.inspect_envelope,
        "approve_envelope": passport.approve_envelope,
    }


@pytest.mark.gap
def test_c2_fr051_positive_control_valid_candidate_recorded() -> None:
    """Positive control: Valid candidate payload is verified and recorded."""
    lab = SyntheticLab()
    ledger = TransparencyLedger()
    payload = _assemble_candidate_payload(lab)

    initial_size = ledger.size
    entry = ledger.append("candidate_recorded", payload)
    assert entry.index == initial_size
    assert ledger.size == initial_size + 1


@pytest.mark.gap
def test_c2_fr051_red_tampered_signature_rejected_by_ledger() -> None:
    """RED TEST: Candidate evidence with tampered signature MUST be rejected by ledger.

    Per FR-051 / SEC-016: The ledger MUST self-verify DSSE envelope signatures before inclusion.
    Appending an entry with an invalid signature must raise SignatureError or SegelError(SIG_INVALID)
    and leave ledger size unchanged.
    """
    lab = SyntheticLab()
    ledger = TransparencyLedger()
    payload = _assemble_candidate_payload(lab)

    # Tamper with origin signature
    payload["origin_envelope"]["signatures"][0]["sig"] = "AAAA" + payload["origin_envelope"]["signatures"][0]["sig"][4:]

    initial_size = ledger.size

    # Per FR-051, record_candidate or append with verification must refuse invalid evidence
    with pytest.raises((SignatureError, SegelError)) as exc_info:
        if hasattr(ledger, "record_candidate"):
            ledger.record_candidate(payload, lab.trust_ctx)
        else:
            # If ledger only has append(), append() must enforce self-verification per FR-051
            ledger.append("candidate_recorded", payload, trust_ctx=lab.trust_ctx)

    assert exc_info.value.code == ErrorCode.SIG_INVALID.value or "SIG_INVALID" in str(exc_info.value)
    assert ledger.size == initial_size, "Ledger state must remain unchanged when evidence is rejected!"


@pytest.mark.gap
def test_c2_fr051_red_subject_mismatch_rejected_by_ledger() -> None:
    """RED TEST: Candidate evidence with subject binding mismatch MUST be rejected by ledger.

    Per FR-051: The ledger MUST verify subject binding consistency before recording candidate.
    """
    lab = SyntheticLab()
    ledger = TransparencyLedger()
    payload = _assemble_candidate_payload(lab)

    # Transplant an origin envelope from a different release
    other_build = build_release_package(
        files={"test.bin": b"other"},
        release_id="REL-DIFFERENT",
        sequence=99,
        purpose="different",
    )
    other_origin = sign_origin(other_build, lab.builder_key)
    payload["origin_envelope"] = other_origin.to_dict()

    initial_size = ledger.size

    with pytest.raises((SubjectMismatchError, SegelError)) as exc_info:
        if hasattr(ledger, "record_candidate"):
            ledger.record_candidate(payload, lab.trust_ctx)
        else:
            ledger.append("candidate_recorded", payload, trust_ctx=lab.trust_ctx)

    assert ledger.size == initial_size, "Ledger state must remain unchanged when subject mismatch occurs!"


@pytest.mark.gap
def test_c2_fr051_red_unverified_promotion_rejected_by_ledger() -> None:
    """RED TEST: Promotion record with unmet criteria MUST be rejected by ledger.

    Per FR-051: The ledger MUST verify canary test receipts meet pre-committed criteria
    before appending release_promoted.
    """
    lab = SyntheticLab()
    ledger = TransparencyLedger()
    payload = _assemble_candidate_payload(lab)

    # Attempt to record promotion with 0 canary receipts (policy requires 2)
    promotion_payload = {
        "candidate_entry_index": 0,
        "release_id": "REL-GAP-051",
        "sequence": 1,
        "receipts": [],  # Empty receipts!
    }

    initial_size = ledger.size

    with pytest.raises(SegelError) as exc_info:
        if hasattr(ledger, "record_promotion"):
            ledger.record_promotion(promotion_payload, lab.trust_ctx)
        else:
            ledger.append("release_promoted", promotion_payload, trust_ctx=lab.trust_ctx)

    assert exc_info.value.code in (
        ErrorCode.PROMOTION_CRITERIA_UNMET,
        ErrorCode.CANARY_RECEIPT_MISSING,
        ErrorCode.THRESHOLD_NOT_MET,
    )
    assert ledger.size == initial_size, "Ledger state must remain unchanged on invalid promotion!"
