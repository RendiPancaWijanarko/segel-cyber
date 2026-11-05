# SPDX-License-Identifier: MIT
"""Unit tests for Passport Assembler and Promotion Controller."""

import pytest

from passport.assembler import build_candidate_passport, build_general_passport
from promotion.controller import evaluate_promotion, CanaryReceipt, PromotionCriteria, PromotionResult
from segel_core.crypto.dsse import DSSEEnvelope
from segel_core.schemas.passport import LedgerProof
from segel_core.schemas.checkpoint import Checkpoint, SignedCheckpoint


def _make_dummy_envelope():
    return DSSEEnvelope(
        payload_type="application/vnd.segel.test+json",
        payload=b"{}",
        signatures=[],
    )


def test_build_candidate_passport():
    dummy_env = _make_dummy_envelope()
    proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=0,
        leaf_hash="a" * 64,
        checkpoint_size=1,
        checkpoint_root_hash="b" * 64,
        checkpoint_signature="sig1",
        inclusion_proof=[],
    )
    signed_cp = SignedCheckpoint(
        checkpoint=Checkpoint(origin="segel", size=1, root_hash="b" * 64),
        ledger_key_id="key1",
        ledger_signature="sig1",
    )

    passport = build_candidate_passport(
        manifest_envelope=dummy_env,
        origin_envelope=dummy_env,
        inspect_envelope=dummy_env,
        approve_envelope=dummy_env,
        candidate_proof=proof,
        signed_checkpoint=signed_cp,
    )

    assert passport.passport_type == "candidate"
    assert passport.record_candidate_proof.checkpoint_size == 1
    assert passport.min_epoch == 1
    assert passport.test_envelopes == []


def test_build_general_passport():
    dummy_env = _make_dummy_envelope()
    candidate_proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=0,
        leaf_hash="a" * 64,
        checkpoint_size=1,
        checkpoint_root_hash="b" * 64,
        checkpoint_signature="sig1",
        inclusion_proof=[],
    )
    promo_proof = LedgerProof(
        event_type="release_promoted",
        entry_index=1,
        leaf_hash="a" * 64,
        checkpoint_size=2,
        checkpoint_root_hash="b" * 64,
        checkpoint_signature="sig1",
        inclusion_proof=[],
    )
    signed_cp = SignedCheckpoint(
        checkpoint=Checkpoint(origin="segel", size=2, root_hash="b" * 64),
        ledger_key_id="key1",
        ledger_signature="sig1",
    )

    passport = build_general_passport(
        manifest_envelope=dummy_env,
        origin_envelope=dummy_env,
        inspect_envelope=dummy_env,
        approve_envelope=dummy_env,
        candidate_proof=candidate_proof,
        test_envelopes=[dummy_env, dummy_env],
        promotion_proof=promo_proof,
        signed_checkpoint=signed_cp,
    )

    assert passport.passport_type == "general"
    assert len(passport.test_envelopes) == 2
    assert passport.record_promotion_proof is not None


def test_evaluate_promotion_success():
    criteria = PromotionCriteria(required_healthy_canary_units=2)
    receipts = [
        CanaryReceipt(unit_id="canary-1", overall_result="healthy", health_results=[], envelope=_make_dummy_envelope()),
        CanaryReceipt(unit_id="canary-2", overall_result="healthy", health_results=[], envelope=_make_dummy_envelope()),
    ]
    res = evaluate_promotion(criteria, receipts)
    assert res.promoted is True
    assert set(res.healthy_units) == {"canary-1", "canary-2"}


def test_evaluate_promotion_insufficient_units():
    criteria = PromotionCriteria(required_healthy_canary_units=2)
    receipts = [
        CanaryReceipt(unit_id="canary-1", overall_result="healthy", health_results=[], envelope=_make_dummy_envelope()),
        CanaryReceipt(unit_id="canary-2", overall_result="unhealthy", health_results=[], envelope=_make_dummy_envelope()),
    ]
    res = evaluate_promotion(criteria, receipts)
    assert res.promoted is False
    assert res.healthy_units == ["canary-1"]
    assert res.unhealthy_units == ["canary-2"]


def test_evaluate_promotion_required_probes():
    criteria = PromotionCriteria(
        required_healthy_canary_units=1,
        required_probes=["file_exists", "config_valid"],
    )
    # Unit with passing probes
    receipt_good = CanaryReceipt(
        unit_id="canary-1",
        overall_result="healthy",
        health_results=[
            {"probe": "file_exists", "passed": True},
            {"probe": "config_valid", "passed": True},
        ],
        envelope=_make_dummy_envelope(),
    )
    # Unit with failing probe
    receipt_bad = CanaryReceipt(
        unit_id="canary-2",
        overall_result="healthy",
        health_results=[
            {"probe": "file_exists", "passed": True},
            {"probe": "config_valid", "passed": False},
        ],
        envelope=_make_dummy_envelope(),
    )

    res = evaluate_promotion(criteria, [receipt_good, receipt_bad])
    assert res.promoted is True
    assert res.healthy_units == ["canary-1"]
    assert res.unhealthy_units == ["canary-2"]
