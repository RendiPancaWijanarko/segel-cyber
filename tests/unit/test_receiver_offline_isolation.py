# SPDX-License-Identifier: MIT
"""Adversarial and isolation tests verifying Receiver zero-network requirement.

Per PRD v2.0 §17, TAS §8.10, and NFR-001:
Receiver offline verification and deployment MUST operate with 100% local cryptographic
validation without making ANY socket, DNS, HTTP, or remote RPC calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from approver.approver import (
    approver_sign,
    collect_approvals,
    create_approval_payload,
)
from builder.builder import build_release_package, sign_manifest, sign_origin
from inspector.inspector import create_inspect_attestation, inspect_release, sign_inspect
from ledger.ledger import TransparencyLedger
from passport.assembler import build_candidate_passport
from receiver.receiver import Receiver, ReceiverState
from segel_core.crypto.ed25519 import KeyPair, export_public_key, generate_keypair
from segel_core.schemas.attestation import PromotionCriteria
from segel_core.schemas.passport import LedgerProof
from segel_core.schemas.trust import (
    KeyRecord,
    RoleThreshold,
    TrustRoot,
    TrustSnapshot,
    VerificationPolicy,
)
from segel_core.verification.passport import EligibilityClass
from segel_core.verification.trust import TrustContext
from witness.witness import Witness


def _network_guard(*args: object, **kwargs: object) -> None:
    """Triggered if any network access is attempted."""
    raise PermissionError("Outbound network access strictly forbidden during offline receiver operations")


@pytest.fixture
def block_all_network():
    """Mock and block all standard Python networking calls."""
    with patch("socket.socket", side_effect=_network_guard), \
         patch("socket.create_connection", side_effect=_network_guard), \
         patch("socket.getaddrinfo", side_effect=_network_guard), \
         patch("socket.gethostbyname", side_effect=_network_guard), \
         patch("urllib.request.urlopen", side_effect=_network_guard), \
         patch("http.client.HTTPConnection", side_effect=_network_guard), \
         patch("http.client.HTTPSConnection", side_effect=_network_guard):
        yield


@pytest.fixture
def trust_setup():
    author_key = generate_keypair()
    builder_key = generate_keypair()
    inspector_key = generate_keypair()
    approver_keys = [generate_keypair() for _ in range(3)]
    ledger_key = generate_keypair()
    witness_key = generate_keypair()
    canary_keys = [generate_keypair() for _ in range(2)]
    general_receiver_key = generate_keypair()

    def kr(kp: KeyPair, role: str, group: str = "default") -> KeyRecord:
        return KeyRecord(
            key_id=kp.key_id,
            public_key_b64=export_public_key(kp.public_key_bytes),
            role=role,
            group=group,
        )

    trust_root = TrustRoot(
        root_version=1,
        keys=[
            kr(author_key, "author"),
            kr(builder_key, "builder"),
            kr(inspector_key, "inspector_signer"),
            kr(approver_keys[0], "approver", "group-0"),
            kr(approver_keys[1], "approver", "group-1"),
            kr(approver_keys[2], "approver", "group-0"),
            kr(ledger_key, "ledger"),
            kr(witness_key, "witness"),
            kr(canary_keys[0], "receiver"),
            kr(canary_keys[1], "receiver"),
            kr(general_receiver_key, "receiver"),
        ],
        roles=[
            RoleThreshold(role="author", threshold=1),
            RoleThreshold(role="builder", threshold=1),
            RoleThreshold(role="inspector_signer", threshold=1),
            RoleThreshold(role="approver", threshold=2, group_minimums={"group-0": 1, "group-1": 1}),
            RoleThreshold(role="ledger", threshold=1),
            RoleThreshold(role="witness", threshold=1),
            RoleThreshold(role="receiver", threshold=1),
        ],
    )

    policy = VerificationPolicy(
        policy_version=1,
        approval_threshold=2,
        approval_groups={"group-0": 1, "group-1": 1},
        canary_required_count=2,
        witness_cosignature_count=1,
        freshness_mode="strict",
    )
    snapshot = TrustSnapshot(epoch=1)
    trust_ctx = TrustContext(root=trust_root, policy=policy, snapshot=snapshot)

    return {
        "author_key": author_key,
        "builder_key": builder_key,
        "inspector_key": inspector_key,
        "approver_keys": approver_keys,
        "ledger_key": ledger_key,
        "witness_key": witness_key,
        "canary_keys": canary_keys,
        "general_key": general_receiver_key,
        "trust_root": trust_root,
        "policy": policy,
        "snapshot": snapshot,
        "trust_ctx": trust_ctx,
    }


def test_offline_verification_zero_network(block_all_network, trust_setup, tmp_path: Path) -> None:
    """Verify that complete passport verification and deployment executes with zero network calls."""
    files = {"config/app.yaml": b"server:\n  port: 8080\n", "config/logging.yaml": b"log_level: info\n"}
    build_res = build_release_package(
        files=files,
        release_id="OFFLINE-TEST-01",
        sequence=1,
        purpose="Offline zero-network test",
        canary_targets=["canary-1", "canary-2"],
        general_scope=["canary-1", "canary-2", "unit-3"],
    )

    manifest_env = sign_manifest(build_res, trust_setup["author_key"])
    origin_env = sign_origin(build_res, trust_setup["builder_key"])

    inspection = inspect_release(
        files=files,
        manifest=build_res.manifest,
        manifest_digest=build_res.manifest_digest,
        ai_enabled=False,
    )
    inspect_stmt = create_inspect_attestation(inspection, build_res.manifest, build_res.manifest_digest)
    inspect_env = sign_inspect(inspect_stmt, trust_setup["inspector_key"])

    approve_stmt, approve_req = create_approval_payload(
        build_res.manifest,
        build_res.manifest_digest,
        origin_env,
        inspect_env,
        inspection.verdict,
        canary_targets=["canary-1", "canary-2"],
        promotion_criteria=PromotionCriteria(required_healthy_canary_units=2),
    )

    approvals = [
        approver_sign(approve_req, trust_setup["approver_keys"][0]),
        approver_sign(approve_req, trust_setup["approver_keys"][1]),
    ]
    approve_env = collect_approvals(approve_stmt, approve_req, approvals)

    ledger = TransparencyLedger()
    entry = ledger.append("candidate_recorded", {
        "event_type": "candidate_recorded",
        "release_id": "OFFLINE-TEST-01",
        "sequence": 1,
        "manifest_sha256": build_res.manifest_digest,
    })
    signed_cp = ledger.sign_checkpoint(trust_setup["ledger_key"])
    witness = Witness(trust_setup["witness_key"])
    cosig = witness.cosign_checkpoint(signed_cp.checkpoint)
    ledger.add_witness_cosignature(signed_cp.checkpoint.size, trust_setup["witness_key"].key_id, cosig)

    proof = ledger.inclusion_proof(entry.index)
    ledger_proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=proof.entry_index,
        leaf_hash=proof.leaf_hash,
        inclusion_proof=proof.proof,
        checkpoint_size=proof.checkpoint_size,
        checkpoint_root_hash=proof.checkpoint_root_hash,
        checkpoint_signature=signed_cp.ledger_signature,
        witness_cosignatures=[cosig],
    )

    candidate_passport = build_candidate_passport(
        manifest_envelope=manifest_env,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        approve_envelope=approve_env,
        candidate_proof=ledger_proof,
        signed_checkpoint=signed_cp,
        min_epoch=1,
    )

    # Instantiate Receiver with zero network allowed
    deploy_root = tmp_path / "deploy"
    state_dir = tmp_path / "state"
    state = ReceiverState(unit_id="canary-1", unit_role="canary")
    receiver = Receiver(
        state=state,
        trust_ctx=trust_setup["trust_ctx"],
        receiver_key=trust_setup["canary_keys"][0],
        deploy_root=deploy_root,
        state_dir=state_dir,
    )

    # Execute verify_and_deploy under the block_all_network fixture
    verification, receipt = receiver.verify_and_deploy(candidate_passport, files)

    assert verification.eligibility == EligibilityClass.ELIGIBLE_CANARY
    assert verification.all_stamps_valid
    assert receipt is not None
    assert (deploy_root / "config" / "app.yaml").exists()


def test_offline_rejections_zero_network(block_all_network, trust_setup, tmp_path: Path) -> None:
    """Verify that all invalid release scenarios fail closed without network calls."""
    files = {"config/app.yaml": b"server:\n  port: 8080\n"}
    build_res = build_release_package(
        files=files,
        release_id="OFFLINE-REJECT-01",
        sequence=1,
        purpose="Offline reject test",
        canary_targets=["canary-1"],
        general_scope=["canary-1"],
    )

    # 1. Stale epoch rejection test (receiver epoch 1 < passport min_epoch 5 with validly signed stamps)
    manifest_env = sign_manifest(build_res, trust_setup["author_key"])
    origin_env = sign_origin(build_res, trust_setup["builder_key"])
    inspection = inspect_release(files=files, manifest=build_res.manifest, manifest_digest=build_res.manifest_digest)
    inspect_stmt = create_inspect_attestation(inspection, build_res.manifest, build_res.manifest_digest)
    inspect_env = sign_inspect(inspect_stmt, trust_setup["inspector_key"])
    approve_stmt, approve_req = create_approval_payload(
        build_res.manifest, build_res.manifest_digest, origin_env, inspect_env, inspection.verdict,
        canary_targets=["canary-1"], promotion_criteria=PromotionCriteria(required_healthy_canary_units=1),
    )
    approve_env = collect_approvals(approve_stmt, approve_req, [
        approver_sign(approve_req, trust_setup["approver_keys"][0]),
        approver_sign(approve_req, trust_setup["approver_keys"][1]),
    ])

    ledger = TransparencyLedger()
    entry = ledger.append("candidate_recorded", {
        "event_type": "candidate_recorded",
        "release_id": "OFFLINE-REJECT-01",
        "sequence": 1,
        "manifest_sha256": build_res.manifest_digest,
    })
    signed_cp = ledger.sign_checkpoint(trust_setup["ledger_key"])
    witness = Witness(trust_setup["witness_key"])
    cosig = witness.cosign_checkpoint(signed_cp.checkpoint)
    ledger.add_witness_cosignature(signed_cp.checkpoint.size, trust_setup["witness_key"].key_id, cosig)

    proof = ledger.inclusion_proof(entry.index)
    ledger_proof = LedgerProof(
        event_type="candidate_recorded",
        entry_index=proof.entry_index,
        leaf_hash=proof.leaf_hash,
        inclusion_proof=proof.proof,
        checkpoint_size=proof.checkpoint_size,
        checkpoint_root_hash=proof.checkpoint_root_hash,
        checkpoint_signature=signed_cp.ledger_signature,
        witness_cosignatures=[cosig],
    )

    stale_passport = build_candidate_passport(
        manifest_envelope=manifest_env,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        approve_envelope=approve_env,
        candidate_proof=ledger_proof,
        signed_checkpoint=signed_cp,
        min_epoch=5,
    )

    stale_state = ReceiverState(unit_id="canary-1", unit_role="canary", epoch=1)
    stale_receiver = Receiver(
        state=stale_state,
        trust_ctx=trust_setup["trust_ctx"],
        receiver_key=trust_setup["canary_keys"][0],
        deploy_root=tmp_path / "deploy_stale",
    )

    verification_stale, receipt_stale = stale_receiver.verify_and_deploy(stale_passport, files)
    assert verification_stale.eligibility == EligibilityClass.INELIGIBLE
    assert receipt_stale is None
    assert any("EPOCH_STALE" in r or "stale" in r.lower() for r in verification_stale.eligibility_reasons)

    # 2. Rogue key forgery rejection test (AT-001)
    rogue_key = generate_keypair()
    forged_manifest_env = sign_manifest(build_res, rogue_key)
    forged_passport = build_candidate_passport(
        manifest_envelope=forged_manifest_env,
        origin_envelope=origin_env,
        inspect_envelope=inspect_env,
        approve_envelope=approve_env,
        candidate_proof=ledger_proof,
        signed_checkpoint=signed_cp,
        min_epoch=1,
    )
    normal_state = ReceiverState(unit_id="canary-1", unit_role="canary", epoch=1)
    normal_receiver = Receiver(
        state=normal_state,
        trust_ctx=trust_setup["trust_ctx"],
        receiver_key=trust_setup["canary_keys"][0],
        deploy_root=tmp_path / "deploy_rogue",
    )
    verification, receipt = normal_receiver.verify_and_deploy(forged_passport, files)
    assert verification.eligibility == EligibilityClass.INELIGIBLE
    assert receipt is None
