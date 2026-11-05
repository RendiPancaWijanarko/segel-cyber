# SPDX-License-Identifier: MIT
"""Adversarial tests (AT-series) per PRD v2.0 §19.

These tests verify that the system correctly rejects forged, modified,
unauthorized, outdated, or otherwise ineligible releases. Each test is
tagged with its AT identifier for traceability.
"""

import json
import copy
import base64
import pytest

from segel_core.canonical import canonical_json
from segel_core.crypto.ed25519 import generate_keypair, export_public_key
from segel_core.crypto.dsse import (
    DSSEEnvelope,
    create_envelope,
    add_signature,
    verify_envelope,
    verify_threshold,
)
from segel_core.crypto.hashing import sha256_hex, merkle_leaf_hash
from segel_core.errors import (
    SignatureError,
    DigestMismatchError,
    ThresholdNotMetError,
    PackageMalformedError,
    SubjectMismatchError,
)
from segel_core.schemas.attestation import PromotionCriteria
from segel_core.schemas.passport import ReleasePassport, LedgerProof
from segel_core.schemas.trust import (
    TrustRoot,
    TrustSnapshot,
    VerificationPolicy,
    KeyRecord,
    RoleThreshold,
    HeldRelease,
    RevokedKey,
)
from segel_core.verification.trust import TrustContext, check_min_epoch
from segel_core.verification.passport import (
    verify_passport,
    EligibilityClass,
    StampStatus,
)

from builder.builder import (
    build_release_package,
    sign_origin,
    sign_manifest,
)
from ledger.ledger import TransparencyLedger
from inspector.inspector import (
    inspect_release,
    create_inspect_attestation,
    sign_inspect,
)
from approver.approver import (
    create_approval_payload,
    approver_sign,
    collect_approvals,
)
from witness.witness import Witness
from passport.assembler import build_candidate_passport
from promotion.controller import evaluate_promotion, CanaryReceipt


# ── Test helper ──────────────────────────────────────────────────────

def _make_lab():
    """Create a quick synthetic lab for adversarial tests."""
    author = generate_keypair()
    builder = generate_keypair()
    inspector = generate_keypair()
    approvers = [generate_keypair() for _ in range(3)]
    ledger_key = generate_keypair()
    witness_key = generate_keypair()
    receiver_key = generate_keypair()

    def kr(kp, role, group="default"):
        return KeyRecord(
            key_id=kp.key_id,
            public_key_b64=export_public_key(kp.public_key_bytes),
            role=role,
            group=group,
        )

    root = TrustRoot(
        root_version=1,
        keys=[
            kr(author, "author"),
            kr(builder, "builder"),
            kr(inspector, "inspector_signer"),
            kr(approvers[0], "approver", "group-0"),
            kr(approvers[1], "approver", "group-1"),
            kr(approvers[2], "approver", "group-0"),
            kr(ledger_key, "ledger"),
            kr(witness_key, "witness"),
            kr(receiver_key, "receiver"),
        ],
        roles=[
            RoleThreshold(role="author", threshold=1),
            RoleThreshold(role="builder", threshold=1),
            RoleThreshold(role="inspector_signer", threshold=1),
            RoleThreshold(role="approver", threshold=2,
                          group_minimums={"group-0": 1, "group-1": 1}),
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
    )

    snapshot = TrustSnapshot(epoch=1)
    trust_ctx = TrustContext(root=root, policy=policy, snapshot=snapshot)

    return {
        "author": author,
        "builder": builder,
        "inspector": inspector,
        "approvers": approvers,
        "ledger_key": ledger_key,
        "witness_key": witness_key,
        "receiver_key": receiver_key,
        "trust_ctx": trust_ctx,
        "root": root,
        "policy": policy,
        "snapshot": snapshot,
    }


# ── AT-001: Invalid signature rejected ───────────────────────────────

@pytest.mark.adversarial
class TestAT001InvalidSignature:
    """AT-001: A release signed with an unknown key is rejected."""

    def test_unknown_key_rejected(self):
        lab = _make_lab()
        rogue = generate_keypair()

        payload = b'{"test": "payload"}'
        env = create_envelope(
            "application/vnd.segel.manifest+json",
            payload,
            [(rogue.key_id, rogue.private_key)],
        )

        author_keys = lab["trust_ctx"].get_keys_for_role("author")
        result = verify_envelope(env, author_keys,
                                 expected_payload_type="application/vnd.segel.manifest+json")
        assert len(result.valid_key_ids) == 0

    def test_truncated_signature_rejected(self):
        lab = _make_lab()
        payload = b'{"test": "data"}'
        env = create_envelope(
            "application/vnd.segel.manifest+json",
            payload,
            [(lab["author"].key_id, lab["author"].private_key)],
        )

        # Truncate the signature
        env_dict = env.to_dict()
        env_dict["signatures"][0]["sig"] = base64.b64encode(b"\x00" * 32).decode()
        tampered = DSSEEnvelope.from_dict(env_dict)

        author_keys = lab["trust_ctx"].get_keys_for_role("author")
        result = verify_envelope(tampered, author_keys,
                                 expected_payload_type="application/vnd.segel.manifest+json")
        assert len(result.valid_key_ids) == 0


# ── AT-002: Modified content detected ────────────────────────────────

@pytest.mark.adversarial
class TestAT002ModifiedContent:
    """AT-002: Tampered release content is detected."""

    def test_single_bit_flip_detected(self):
        lab = _make_lab()
        payload = b'{"release": "original"}'
        env = create_envelope(
            "application/vnd.segel.manifest+json",
            payload,
            [(lab["author"].key_id, lab["author"].private_key)],
        )

        # Flip one bit in the payload
        env_dict = env.to_dict()
        raw_payload = base64.b64decode(env_dict["payload"])
        tampered = bytearray(raw_payload)
        tampered[5] ^= 0x01
        env_dict["payload"] = base64.b64encode(bytes(tampered)).decode()
        tampered_env = DSSEEnvelope.from_dict(env_dict)

        author_keys = lab["trust_ctx"].get_keys_for_role("author")
        result = verify_envelope(tampered_env, author_keys,
                                 expected_payload_type="application/vnd.segel.manifest+json")
        assert len(result.valid_key_ids) == 0

    def test_file_digest_mismatch_detected(self):
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT002", sequence=1, purpose="test",
        )

        from receiver.adapter.baseline import BaselineAdapter
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            adapter = BaselineAdapter(td)
            adapter.preflight(build.manifest)
            tampered_files = {"config/app.yaml": b"port: 9999\n"}
            with pytest.raises(DigestMismatchError):
                adapter.stage(build.manifest, tampered_files)


# ── AT-003: Missing stamps rejected ──────────────────────────────────

@pytest.mark.adversarial
class TestAT003MissingStamps:
    """AT-003: A passport with missing stamps is rejected."""

    def test_missing_record_proof_rejected(self):
        lab = _make_lab()
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT003", sequence=1,
            purpose="test", canary_targets=["canary-1"],
        )
        manifest_env = sign_manifest(build, lab["author"])

        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope=manifest_env.to_dict(),
            origin_envelope=manifest_env.to_dict(),
            inspect_envelope=manifest_env.to_dict(),
            approve_envelope=manifest_env.to_dict(),
            # record_candidate_proof is None
        )

        v = verify_passport(
            passport, lab["trust_ctx"], "canary-1", "canary",
            {"epoch": 1, "highest_sequence": {}},
        )
        assert v.eligibility == EligibilityClass.INELIGIBLE
        assert v.record.status == StampStatus.INVALID


# ── AT-004: Sequence replay blocked ──────────────────────────────────

@pytest.mark.adversarial
class TestAT004SequenceReplay:
    """AT-004: Replaying an old sequence number is blocked."""

    def test_same_sequence_blocked(self):
        lab = _make_lab()
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT004", sequence=5,
            purpose="test", canary_targets=["canary-1"],
        )
        manifest_env = sign_manifest(build, lab["author"])

        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope=manifest_env.to_dict(),
            origin_envelope=manifest_env.to_dict(),
            inspect_envelope=manifest_env.to_dict(),
            approve_envelope=manifest_env.to_dict(),
        )

        v = verify_passport(
            passport, lab["trust_ctx"], "canary-1", "canary",
            {"epoch": 1, "highest_sequence": {"AT004": 5}},
        )
        assert v.eligibility == EligibilityClass.INELIGIBLE
        assert any("anti-rollback" in r for r in v.eligibility_reasons)

    def test_lower_sequence_blocked(self):
        lab = _make_lab()
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT004", sequence=3,
            purpose="test", canary_targets=["canary-1"],
        )
        manifest_env = sign_manifest(build, lab["author"])

        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope=manifest_env.to_dict(),
            origin_envelope=manifest_env.to_dict(),
            inspect_envelope=manifest_env.to_dict(),
            approve_envelope=manifest_env.to_dict(),
        )

        v = verify_passport(
            passport, lab["trust_ctx"], "canary-1", "canary",
            {"epoch": 1, "highest_sequence": {"AT004": 5}},
        )
        assert v.eligibility == EligibilityClass.INELIGIBLE


# ── AT-005-008: Approval attacks ─────────────────────────────────────

@pytest.mark.adversarial
class TestAT005to008ApprovalAttacks:
    """AT-005 to AT-008: Various approval attack vectors."""

    def test_at005_single_approver_insufficient(self):
        """AT-005: One approver doesn't meet threshold of 2."""
        lab = _make_lab()
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT005", sequence=1, purpose="test",
        )
        manifest_env = sign_manifest(build, lab["author"])
        origin_env = sign_origin(build, lab["builder"])
        inspection = inspect_release(files=files, manifest=build.manifest,
                                     manifest_digest=build.manifest_digest)
        inspect_stmt = create_inspect_attestation(
            inspection, build.manifest, build.manifest_digest,
        )
        inspect_env = sign_inspect(inspect_stmt, lab["inspector"])

        _, req = create_approval_payload(
            build.manifest, build.manifest_digest,
            origin_env, inspect_env, inspection.verdict,
        )

        # Only 1 approver
        responses = [approver_sign(req, lab["approvers"][0])]
        approve_env = collect_approvals({}, req, responses)

        approver_keys = lab["trust_ctx"].get_keys_for_role("approver")
        result = verify_envelope(
            approve_env, approver_keys,
            expected_payload_type="application/vnd.segel.approve+json",
        )
        with pytest.raises(ThresholdNotMetError):
            verify_threshold(result, threshold=2,
                             excluded_key_ids={lab["author"].key_id})

    def test_at006_duplicate_signer_counted_once(self):
        """AT-006: Same key signing twice doesn't double-count."""
        lab = _make_lab()
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT006", sequence=1, purpose="test",
        )
        manifest_env = sign_manifest(build, lab["author"])
        origin_env = sign_origin(build, lab["builder"])
        inspection = inspect_release(files=files, manifest=build.manifest,
                                     manifest_digest=build.manifest_digest)
        inspect_stmt = create_inspect_attestation(
            inspection, build.manifest, build.manifest_digest,
        )
        inspect_env = sign_inspect(inspect_stmt, lab["inspector"])

        _, req = create_approval_payload(
            build.manifest, build.manifest_digest,
            origin_env, inspect_env, inspection.verdict,
        )

        # Same approver signs twice
        responses = [
            approver_sign(req, lab["approvers"][0]),
            approver_sign(req, lab["approvers"][0]),
        ]
        approve_env = collect_approvals({}, req, responses)

        approver_keys = lab["trust_ctx"].get_keys_for_role("approver")
        result = verify_envelope(
            approve_env, approver_keys,
            expected_payload_type="application/vnd.segel.approve+json",
        )

        # Should have only 1 distinct key even though there are 2 sigs
        counting = result.valid_key_ids - {lab["author"].key_id}
        assert len(counting) == 1

        with pytest.raises(ThresholdNotMetError):
            verify_threshold(result, threshold=2,
                             excluded_key_ids={lab["author"].key_id})

    def test_at008_author_excluded_from_approval(self):
        """AT-008: Author's key excluded from approval count."""
        lab = _make_lab()
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT008", sequence=1, purpose="test",
        )
        origin_env = sign_origin(build, lab["builder"])
        inspection = inspect_release(files=files, manifest=build.manifest,
                                     manifest_digest=build.manifest_digest)
        inspect_stmt = create_inspect_attestation(
            inspection, build.manifest, build.manifest_digest,
        )
        inspect_env = sign_inspect(inspect_stmt, lab["inspector"])

        _, req = create_approval_payload(
            build.manifest, build.manifest_digest,
            origin_env, inspect_env, inspection.verdict,
        )

        # Author + 1 approver = only 1 non-excluded signer
        responses = [
            approver_sign(req, lab["author"]),     # excluded
            approver_sign(req, lab["approvers"][0]),  # counts
        ]
        approve_env = collect_approvals({}, req, responses)

        approver_keys = lab["trust_ctx"].get_keys_for_role("approver")
        result = verify_envelope(
            approve_env, approver_keys,
            expected_payload_type="application/vnd.segel.approve+json",
        )

        with pytest.raises(ThresholdNotMetError):
            verify_threshold(result, threshold=2,
                             excluded_key_ids={lab["author"].key_id})


# ── AT-009: Epoch enforcement ────────────────────────────────────────

@pytest.mark.adversarial
class TestAT009EpochEnforcement:
    """AT-009: Stale epoch blocks deployment in strict mode."""

    def test_strict_mode_blocks_stale_epoch(self):
        from segel_core.errors import EpochStaleError
        with pytest.raises(EpochStaleError):
            check_min_epoch(
                receiver_epoch=1,
                required_min_epoch=3,
                freshness_mode="strict",
            )

    def test_advisory_mode_allows_stale_epoch(self):
        # Should not raise
        check_min_epoch(
            receiver_epoch=1,
            required_min_epoch=3,
            freshness_mode="advisory",
        )


# ── AT-015-019: Inspection attacks ───────────────────────────────────

@pytest.mark.adversarial
class TestAT015to019InspectionAttacks:
    """AT-015 to AT-019: Inspection-related attacks."""

    def test_at015_privilege_escalation_rejected(self):
        """AT-015: Config requesting root privileges is REJECT."""
        files = {"config/app.yaml": b"run_as_root: true\nport: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT015", sequence=1, purpose="test",
        )
        inspection = inspect_release(
            files=files, manifest=build.manifest,
            manifest_digest=build.manifest_digest,
        )
        assert inspection.verdict == "REJECT"

    def test_at016_credential_reference_warns(self):
        """AT-016: Config referencing credentials triggers WARN."""
        files = {"config/app.yaml": b"password: secret123\nport: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT016", sequence=1, purpose="test",
        )
        inspection = inspect_release(
            files=files, manifest=build.manifest,
            manifest_digest=build.manifest_digest,
        )
        assert inspection.verdict == "WARN"

    def test_at019_ai_failure_recorded(self):
        """AT-019: AI failure is recorded as ai_status=failed."""
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="AT019", sequence=1, purpose="test",
        )
        inspection = inspect_release(
            files=files, manifest=build.manifest,
            manifest_digest=build.manifest_digest,
            ai_enabled=True,  # Will fail since Ollama is not running
        )
        assert inspection.ai_status == "failed"
        assert any(f.capability_id == "AI_FAILURE" for f in inspection.ai_findings)


# ── AT-023: Witness validation ───────────────────────────────────────

@pytest.mark.adversarial
class TestAT023WitnessValidation:
    """AT-023: Witness rejects non-extending checkpoint."""

    def test_witness_rejects_fork(self):
        from segel_core.errors import CheckpointForkError
        from segel_core.schemas.checkpoint import Checkpoint

        witness_key = generate_keypair()
        witness = Witness(witness_key)

        # First checkpoint
        cp1 = Checkpoint(size=5, root_hash="a" * 64)
        witness.cosign_checkpoint(cp1)

        # Forked checkpoint: same size, different root
        cp_fork = Checkpoint(size=5, root_hash="b" * 64)
        with pytest.raises(CheckpointForkError):
            witness.cosign_checkpoint(cp_fork)

    def test_witness_rejects_smaller_checkpoint(self):
        from segel_core.errors import CheckpointForkError
        from segel_core.schemas.checkpoint import Checkpoint

        witness_key = generate_keypair()
        witness = Witness(witness_key)

        cp1 = Checkpoint(size=10, root_hash="a" * 64)
        witness.cosign_checkpoint(cp1)

        cp_smaller = Checkpoint(size=5, root_hash="b" * 64)
        with pytest.raises(CheckpointForkError):
            witness.cosign_checkpoint(cp_smaller)


# ── AT-024-025: Canary failures ──────────────────────────────────────

@pytest.mark.adversarial
class TestAT024CanaryBlocks:
    """AT-024: Failed canary blocks promotion."""

    def test_unhealthy_canary_blocks_promotion(self):
        criteria = PromotionCriteria(
            required_healthy_canary_units=2,
            required_probes=["file_exists"],
        )

        receipts = [
            CanaryReceipt(
                unit_id="canary-1",
                overall_result="healthy",
                health_results=[{"probe": "file_exists", "passed": True}],
                envelope=None,  # Not needed for evaluation
            ),
            CanaryReceipt(
                unit_id="canary-2",
                overall_result="unhealthy",
                health_results=[{"probe": "file_exists", "passed": False}],
                envelope=None,
            ),
        ]

        result = evaluate_promotion(criteria, receipts)
        assert not result.promoted
        assert "canary-2" in result.unhealthy_units

    def test_no_receipts_blocks_promotion(self):
        criteria = PromotionCriteria(required_healthy_canary_units=2)
        result = evaluate_promotion(criteria, [])
        assert not result.promoted


# ── AT-026-030: Deployment security ──────────────────────────────────

@pytest.mark.adversarial
class TestAT026to030DeploymentSecurity:
    """AT-026 to AT-030: Deployment adapter security."""

    def test_at026_path_traversal_blocked(self):
        """AT-026: Path traversal in file names blocked."""
        with pytest.raises(PackageMalformedError, match="traversal"):
            build_release_package(
                files={"../../../etc/passwd": b"root:x:0:0"},
                release_id="AT026", sequence=1, purpose="test",
            )

    def test_at027_absolute_path_blocked(self):
        """AT-027: Absolute paths blocked."""
        with pytest.raises(PackageMalformedError, match="Absolute"):
            build_release_package(
                files={"/etc/hosts": b"127.0.0.1 evil"},
                release_id="AT027", sequence=1, purpose="test",
            )

    def test_at028_executable_blocked(self):
        """AT-028: Executable files blocked."""
        with pytest.raises(PackageMalformedError, match="Forbidden"):
            build_release_package(
                files={"payload.sh": b"#!/bin/bash\nrm -rf /"},
                release_id="AT028", sequence=1, purpose="test",
            )

    def test_at029_empty_release_blocked(self):
        """AT-029: Empty release rejected."""
        with pytest.raises(PackageMalformedError, match="at least one"):
            build_release_package(
                files={}, release_id="AT029", sequence=1, purpose="test",
            )

    def test_at030_null_byte_in_path_blocked(self):
        """AT-030: Null byte in file path blocked."""
        with pytest.raises(PackageMalformedError, match="Null"):
            build_release_package(
                files={"config\x00evil.yaml": b"data"},
                release_id="AT030", sequence=1, purpose="test",
            )


# ── AT-045: Held release blocked ─────────────────────────────────────

@pytest.mark.adversarial
class TestAT045HeldRelease:
    """AT-045: Held release cannot be deployed."""

    def test_held_release_blocked(self):
        lab = _make_lab()
        files = {"config/app.yaml": b"port: 8080\n"}
        build = build_release_package(
            files=files, release_id="HELD-RELEASE", sequence=1,
            purpose="test", canary_targets=["canary-1"],
        )
        manifest_env = sign_manifest(build, lab["author"])

        # Create snapshot with the release held
        snapshot = TrustSnapshot(
            epoch=1,
            held_releases=[HeldRelease(release_id="HELD-RELEASE", sequence=1)],
        )
        trust_ctx = TrustContext(
            root=lab["root"], policy=lab["policy"], snapshot=snapshot,
        )

        passport = ReleasePassport(
            passport_type="candidate",
            manifest_envelope=manifest_env.to_dict(),
            origin_envelope=manifest_env.to_dict(),
            inspect_envelope=manifest_env.to_dict(),
            approve_envelope=manifest_env.to_dict(),
        )

        v = verify_passport(
            passport, trust_ctx, "canary-1", "canary",
            {"epoch": 1, "highest_sequence": {}},
        )
        assert v.eligibility == EligibilityClass.HELD

