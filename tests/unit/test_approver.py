# SPDX-License-Identifier: MIT
"""Unit tests for Approver component.

Tests approval payload construction, offline signing, QR generation/parsing,
and signature collection into DSSE envelopes.
"""

import json
import base64
import pytest

from approver.approver import (
    create_approval_payload,
    approver_sign,
    collect_approvals,
    generate_qr_request,
    parse_qr_response,
    ApprovalRequest,
    ApprovalResponse,
)
from builder.builder import build_release_package, sign_manifest, sign_origin
from inspector.inspector import inspect_release, create_inspect_attestation, sign_inspect
from segel_core.crypto.ed25519 import generate_keypair, PublicKeyInfo, verify
from segel_core.crypto.dsse import pae as dsse_pae, verify_envelope
from segel_core.schemas.attestation import PromotionCriteria, APPROVE_PREDICATE_TYPE


@pytest.fixture
def sample_envelopes():
    files = {"config/app.yaml": b"server:\n  port: 8080\n"}
    builder_res = build_release_package(
        files=files, release_id="APP-TEST-1", sequence=1,
        purpose="testing approver", canary_targets=["canary-1", "canary-2"],
        general_scope=["canary-1", "canary-2", "unit-3"],
    )
    author_key = generate_keypair()
    manifest_env = sign_manifest(builder_res, author_key)

    builder_key = generate_keypair()
    origin_env = sign_origin(builder_res, builder_key)

    inspect_res = inspect_release(files, builder_res.manifest, builder_res.manifest_digest)
    inspect_stmt = create_inspect_attestation(inspect_res, builder_res.manifest, builder_res.manifest_digest)
    inspector_key = generate_keypair()
    inspect_env = sign_inspect(inspect_stmt, inspector_key)

    return builder_res, manifest_env, origin_env, inspect_env, inspect_res.verdict


def test_create_approval_payload(sample_envelopes):
    builder_res, manifest_env, origin_env, inspect_env, verdict = sample_envelopes
    criteria = PromotionCriteria(required_healthy_canary_units=2)

    stmt_dict, req = create_approval_payload(
        manifest=builder_res.manifest,
        manifest_digest=builder_res.manifest_digest,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        inspect_verdict=verdict,
        canary_targets=["canary-1", "canary-2"],
        promotion_criteria=criteria,
    )

    assert stmt_dict["_type"] == "https://in-toto.io/Statement/v1"
    assert stmt_dict["predicateType"] == APPROVE_PREDICATE_TYPE
    assert req.release_id == "APP-TEST-1"
    assert req.sequence == 1
    assert req.canary_targets == ["canary-1", "canary-2"]
    assert req.payload_type == "application/vnd.segel.approve+json"


def test_approver_sign_and_verify(sample_envelopes):
    builder_res, manifest_env, origin_env, inspect_env, verdict = sample_envelopes
    stmt_dict, req = create_approval_payload(
        manifest=builder_res.manifest,
        manifest_digest=builder_res.manifest_digest,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        inspect_verdict=verdict,
    )

    approver_key = generate_keypair()
    resp = approver_sign(req, approver_key)

    assert resp.approved is True
    assert resp.approver_key_id == approver_key.key_id

    # Verify signature over PAE
    pae_bytes = dsse_pae(req.payload_type, req.payload_to_sign)
    raw_sig = base64.b64decode(resp.signature_b64)
    verify(approver_key.public_key, raw_sig, pae_bytes)


def test_collect_approvals_into_envelope(sample_envelopes):
    builder_res, manifest_env, origin_env, inspect_env, verdict = sample_envelopes
    stmt_dict, req = create_approval_payload(
        manifest=builder_res.manifest,
        manifest_digest=builder_res.manifest_digest,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        inspect_verdict=verdict,
    )

    app1_key = generate_keypair()
    app2_key = generate_keypair()
    resp1 = approver_sign(req, app1_key)
    resp2 = approver_sign(req, app2_key)

    env = collect_approvals(stmt_dict, req, [resp1, resp2])
    assert len(env.signatures) == 2

    # Verify DSSE envelope with both keys
    pub1 = PublicKeyInfo(key_id=app1_key.key_id, public_key=app1_key.public_key, public_key_bytes=app1_key.public_key_bytes)
    pub2 = PublicKeyInfo(key_id=app2_key.key_id, public_key=app2_key.public_key, public_key_bytes=app2_key.public_key_bytes)

    vr = verify_envelope(env, [pub1, pub2], expected_payload_type="application/vnd.segel.approve+json")
    assert len(vr.valid_key_ids) == 2


def test_qr_request_and_response_roundtrip(sample_envelopes):
    builder_res, manifest_env, origin_env, inspect_env, verdict = sample_envelopes
    _, req = create_approval_payload(
        manifest=builder_res.manifest,
        manifest_digest=builder_res.manifest_digest,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        inspect_verdict=verdict,
    )

    qr_str = generate_qr_request(req)
    qr_data = json.loads(qr_str)
    assert qr_data["type"] == "segel_approve_request"
    assert qr_data["release_id"] == "APP-TEST-1"

    # Simulate response QR
    dummy_response_json = json.dumps({
        "key_id": "test-key-id",
        "sig": "dGVzdC1zaWduYXR1cmU=",
        "approved": True,
    })
    parsed = parse_qr_response(dummy_response_json)
    assert parsed.approver_key_id == "test-key-id"
    assert parsed.signature_b64 == "dGVzdC1zaWduYXR1cmU="
    assert parsed.approved is True

